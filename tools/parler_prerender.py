"""B1: pre-render the content packs' Santali lines with Indic Parler-TTS (background job).

    python tools/parler_prerender.py                   # newest dist/packs/*.zip + the Android test pack
    python tools/parler_prerender.py --threads 4 --limit 3

Renders every Santali text in the packs' audio/index.json (lesson steps, flashcard
words, worksheet prompts: every Santali line the pack speaks) to
content_audio/parler/<sha1 of the text>.wav, and records it in
content_audio/parler/index.json ({text: {file, seconds, render_s}}). Resumable: a
text whose file exists is skipped, so the job can be stopped (e.g. before a latency
benchmark) and started again. Runs at idle priority with capped threads so the
laptop stays usable. Output is audio only: nothing ships until A6 compares voices.

Model card (docs/sources.md#indic-parler-tts): Apache-2.0, Santali listed, but no
recommended Santali speaker, so a fixed generic description and a fixed seed are used.
"""

import argparse
import glob
import hashlib
import json
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "content_audio" / "parler"
MODEL = "ai4bharat/indic-parler-tts"
DESCRIPTION = ("A female speaker delivers a slightly expressive and animated speech with a moderate speed "
               "and pitch. The recording is of very high quality, with the speaker's voice sounding clear "
               "and very close up.")
SEED = 1234


def key(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def pack_texts():
    texts = []
    packs = sorted(glob.glob(str(ROOT / "dist" / "packs" / "content-pack-*.zip")))
    if packs:
        with zipfile.ZipFile(packs[-1]) as z:
            texts += list(json.loads(z.read("audio/index.json").decode("utf-8")).get("sat", {}))
    test_ix = ROOT / "android" / "app" / "src" / "test" / "resources" / "pack" / "audio" / "index.json"
    if test_ix.exists():
        texts += list(json.loads(test_ix.read_text(encoding="utf-8")).get("sat", {}))
    seen, out = set(), []
    for t in texts:
        if t.strip() and t not in seen:
            seen.add(t)
            out.append(t)
    return out, (packs[-1] if packs else None)


def lower_priority():
    try:
        import psutil
        p = psutil.Process()
        p.nice(psutil.IDLE_PRIORITY_CLASS if sys.platform == "win32" else 19)
    except Exception as e:  # noqa: BLE001
        print("could not lower priority:", e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    lower_priority()
    import numpy as np
    import soundfile as sf
    import torch
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer
    torch.set_num_threads(a.threads)

    texts, pack = pack_texts()
    OUT.mkdir(parents=True, exist_ok=True)
    ix_path = OUT / "index.json"
    index = json.loads(ix_path.read_text(encoding="utf-8")) if ix_path.exists() else {}
    todo = [t for t in texts if not (OUT / f"{key(t)}.wav").exists()]
    if a.limit:
        todo = todo[: a.limit]
    print(f"pack {pack}: {len(texts)} Santali lines, {len(texts) - len(todo)} done, {len(todo)} to render", flush=True)
    if not todo:
        return

    model = ParlerTTSForConditionalGeneration.from_pretrained(MODEL).eval()
    tok = AutoTokenizer.from_pretrained(MODEL)
    desc_tok = AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)
    sr = model.config.sampling_rate
    d = desc_tok(DESCRIPTION, return_tensors="pt")
    for i, text in enumerate(todo, 1):
        t0 = time.perf_counter()
        torch.manual_seed(SEED)
        p = tok(text, return_tensors="pt")
        with torch.inference_mode():
            audio = model.generate(input_ids=d.input_ids, attention_mask=d.attention_mask,
                                   prompt_input_ids=p.input_ids, prompt_attention_mask=p.attention_mask)
        wav = audio.cpu().numpy().squeeze().astype(np.float32)
        f = OUT / f"{key(text)}.wav"
        tmp = f.with_suffix(".tmp.wav")
        sf.write(tmp, wav, sr, subtype="PCM_16")
        tmp.replace(f)                                   # a stopped job never leaves half a file
        dt = time.perf_counter() - t0
        index[text] = {"file": f.name, "seconds": round(len(wav) / sr, 2), "render_s": round(dt, 1)}
        ix_path.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[{i}/{len(todo)}] {f.name} {len(wav) / sr:.1f} s audio in {dt:.1f} s", flush=True)
    meta = {"model": MODEL, "description": DESCRIPTION, "seed": SEED, "sampling_rate": sr,
            "threads": a.threads, "pack": Path(pack).name if pack else None}
    (OUT / "render_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
