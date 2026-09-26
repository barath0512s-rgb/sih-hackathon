"""A1: tune and score the lesson-line matcher (lesson_match.py) on the laptop.

    python bench/lesson_match_tune.py            # synthesise clips, recognise, tune, write results
    python bench/lesson_match_tune.py --score-only   # re-tune from the saved transcripts

Clips (all written to dist/lesson_match/clips/, 16 kHz mono; manifest clips.json):
  positives, per direction, every line of the newest content pack:
    Hindi lines (translations hi-to-sat) and Santali lines (the Santali text of every
    pack translation), three versions each: the pack's own audio (Piper, as the
    tablet plays it), Piper at length_scale 0.85 (faster), and Piper at 1.2
    (slower) with white noise at 15 dB SNR. SYNTHETIC speech, one voice.
  negatives (not lesson lines):
    real speech: the 80 public clips per language (FLEURS hi, IndicVoices sat;
    bench/clips/public), and conversational sentences from IN22-Conv (first 200 hi,
    first 100 sat) spoken by the same Piper voice. A negative whose text is itself a
    pack line (normalize_key equal) is dropped.
  near-miss negatives (added after the first tuning, when a unit test showed an
  everyday sentence matching an unrelated lesson line at 0.51): every pack line of
  3+ words with one word replaced by another word from the pack's lines, and every
  line with a number with that number changed. These are the sentences where a
  wrong translation would be served. Same Piper voice; in the same split as the
  line they came from.
Recognition: the tablet's models and settings on the laptop, sherpa-onnx 1.13.8
int8: Hindi NeMo CTC greedy (no trimming), Santali NeMo transducer greedy (silence
trimmed, as config.ASR_TRIM_SILENCE). Transcripts: bench/results/lesson_match_transcripts_laptop.json
(the device's are compared with these: A1 parity).
Split: every clip is in "tune" or "test" by a hash of its line (positives) or its
id (negatives), so no line is in both. The threshold is the lowest at which the tune
half has precision >= 0.98; precision and recall are then reported on the test half.
  accepted  = best candidate score >= threshold
  correct   = accepted and the best candidate is the clip's own line, or a line that is
              the same utterance once numbers are written as words ("4" and "चार")
  precision = correct / accepted   (a wrong line or an accepted negative is an error)
  recall    = correct / positives
"""

import argparse
import glob
import hashlib
import io
import json
import sys
import time
import wave
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from lesson_match import best, canonical, number_tokens  # noqa: E402
from textnorm import normalize_key  # noqa: E402

OUT = ROOT / "dist" / "lesson_match"
CLIPS = OUT / "clips"
TRANSCRIPTS = ROOT / "bench" / "results" / "lesson_match_transcripts_laptop.json"
RESULT = ROOT / "bench" / "results" / "lesson_match.md"
SHERPA = config.MODELS_DIR / "indicconformer-120m-sherpa"
PRECISION_TARGET = 0.98
SEED = 20260926


def h(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def split_of(key):
    return "test" if int(h(key), 16) % 2 else "tune"


def to16k(x, sr):
    import librosa
    x = x.astype(np.float32)
    return librosa.resample(x, orig_sr=sr, target_sr=16000) if sr != 16000 else x


def write16(path, x):
    import soundfile as sf
    sf.write(str(path), np.clip(x, -1, 1), 16000, subtype="PCM_16")


def pack_lines():
    pack = sorted(glob.glob(str(ROOT / "dist" / "packs" / "content-pack-*.zip")))[-1]
    z = zipfile.ZipFile(pack)
    tr = json.loads(z.read("translations.json"))
    audio = json.loads(z.read("audio/index.json"))
    hi = {k: v["text"] for k, v in tr["hi-to-sat"].items()}                    # hi key -> sat text
    sat = {normalize_key(v): k for k, v in hi.items()}                         # sat key -> hi key
    sat.update({k: normalize_key(v["text"]) for k, v in tr["sat-to-hi"].items()})
    return pack, z, audio, hi, sat


def synthesise(voice, text, length_scale):
    from piper import SynthesisConfig
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        voice.synthesize_wav(text, wf, syn_config=SynthesisConfig(length_scale=length_scale))
    buf.seek(0)
    with wave.open(buf) as wf:
        x = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        return x, wf.getframerate()


def add_noise(x, snr_db, rng):
    p = float(np.mean(x ** 2)) or 1e-8
    return x + rng.normal(0, np.sqrt(p / 10 ** (snr_db / 10)), size=x.shape).astype(np.float32)


def make_clips():
    import soundfile as sf
    from piper import PiperVoice
    import pandas as pd
    from translit.olchiki import to_devanagari
    voice = PiperVoice.load(str(config.PIPER_DIR / f"{config.PIPER_VOICES['hindi']}.onnx"))
    pack, z, audio, hi, sat = pack_lines()
    CLIPS.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    clips = []

    def add(cid, lang, kind, variant, key, text, x):
        write16(CLIPS / f"{cid}.wav", x)
        clips.append({"id": cid, "lang": lang, "kind": kind, "variant": variant, "line": key,
                      "text": text, "split": split_of(key if kind == "pos" else cid)})

    speak = {"hi": lambda t: t, "sat": lambda t: to_devanagari(t, digits="spoken")}
    for lang, lines, index in (("hi", {k: k for k in hi}, audio["hi"]), ("sat", {k: k for k in sat}, audio["sat"])):
        by_key = {normalize_key(t): f for t, f in index.items()}
        for key in lines:
            f = by_key.get(key)
            base = f"{lang}_{h(key)[:12]}"
            if f:
                x, sr = sf.read(io.BytesIO(z.read(f"audio/{f}")), dtype="float32")
                add(f"{base}_pack", lang, "pos", "pack audio", key, key, to16k(x, sr))
            text = speak[lang](key)
            x, sr = synthesise(voice, text, 0.85)
            add(f"{base}_fast", lang, "pos", "piper 0.85", key, key, to16k(x, sr))
            x, sr = synthesise(voice, text, 1.2)
            add(f"{base}_slow_noise", lang, "pos", "piper 1.2 + noise 15 dB", key, key, add_noise(to16k(x, sr), 15, rng))
        print(lang, "positives", sum(c["lang"] == lang for c in clips), flush=True)

    man = json.loads((ROOT / "bench/clips/public/manifest.json").read_text(encoding="utf-8"))
    for c in man:
        x, sr = sf.read(str(ROOT / c["file"]), dtype="float32")
        x = x.mean(axis=1) if x.ndim > 1 else x
        if normalize_key(c["reference"]) in (hi if c["lang"] == "hi" else sat):
            continue
        add(f"{c['lang']}_neg_{h(c['file'])[:12]}", c["lang"], "neg", "real speech (public clip)", None,
            c["reference"], to16k(x, sr))
    conv = pd.read_parquet(ROOT / "data/public/ai4bharat__IN22-Conv/data/train-00000-of-00001.parquet")
    for lang, col, n in (("hi", "hin_Deva", 200), ("sat", "sat_Olck", 100)):
        for s in conv[col].tolist()[:n]:
            k = normalize_key(s)
            if k in (hi if lang == "hi" else sat):
                continue
            x, sr = synthesise(voice, speak[lang](s), 1.0)
            add(f"{lang}_conv_{h(s)[:12]}", lang, "neg", "IN22-Conv, piper", None, s, to16k(x, sr))
    (OUT / "clips.json").write_text(json.dumps({"pack": Path(pack).name, "clips": clips}, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
    print(len(clips), "clips", flush=True)


def recognizers(threads=2):
    import sherpa_onnx
    hi = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(
        model=str(SHERPA / "hi/model.int8.onnx"), tokens=str(SHERPA / "hi/tokens.txt"),
        num_threads=threads, decoding_method="greedy_search")
    d = SHERPA / "sat/rnnt"
    sat = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=str(d / "encoder.int8.onnx"), decoder=str(d / "decoder.int8.onnx"), joiner=str(d / "joiner.int8.onnx"),
        tokens=str(d / "tokens.txt"), num_threads=threads, model_type="nemo_transducer", decoding_method="greedy_search")
    return {"hi": hi, "sat": sat}


def trim(x):
    from indicconformer_asr import trim_silence
    return trim_silence(x[None, :])[0]


def make_near_miss():
    import random
    from piper import PiperVoice
    from translit.olchiki import to_devanagari
    from textnorm import normalize_key as nk
    clips_path = OUT / "clips.json"
    data = json.loads(clips_path.read_text(encoding="utf-8"))
    if any(c["variant"].startswith("near-miss") for c in data["clips"]):
        return
    voice = PiperVoice.load(str(config.PIPER_DIR / f"{config.PIPER_VOICES['hindi']}.onnx"))
    _, _, _, hi, sat = pack_lines()
    rnd = random.Random(SEED)
    speak = {"hi": lambda t: t, "sat": lambda t: to_devanagari(t, digits="spoken")}
    numbers = {"hi": ["एक", "दो", "तीन", "चार", "पांच", "छह", "सात", "आठ", "नौ", "दस"],
               "sat": [nk(w) for w in ("ᱢᱤᱫ", "ᱵᱟᱨ", "ᱯᱮ", "ᱯᱩᱱ", "ᱢᱚᱬᱮ", "ᱛᱩᱨᱩᱭ", "ᱮᱭᱟᱭ", "ᱤᱨᱟᱹᱞ", "ᱟᱨᱮ", "ᱜᱮᱞ")]}
    added = 0
    for lang, lines in (("hi", sorted(hi)), ("sat", sorted(sat))):
        keys = {canonical(k, lang) for k in lines}
        nums = set(numbers[lang])
        vocab = sorted({w for k in lines for w in k.split() if len(w) >= 2 and w not in nums})
        for key in lines:
            words = key.split()
            variants = []
            content = [i for i, w in enumerate(words) if w not in nums and len(w) >= 2]
            if len(words) >= 3 and content:
                i = rnd.choice(content)
                w = rnd.choice([v for v in vocab if v != words[i]])
                variants.append(("near-miss: word swap", " ".join(words[:i] + [w] + words[i + 1:])))
            ni = number_tokens_words(words, lang, nums)
            if ni:
                i = ni[0]
                w = rnd.choice([n for n in numbers[lang] if n != words[i]])
                variants.append(("near-miss: number swap", " ".join(words[:i] + [w] + words[i + 1:])))
            for variant, text in variants:
                if canonical(text, lang) in keys:
                    continue
                x, sr = synthesise(voice, speak[lang](text), 1.0)
                cid = f"{lang}_near_{h(text)[:12]}"
                write16(CLIPS / f"{cid}.wav", to16k(x, sr))
                data["clips"].append({"id": cid, "lang": lang, "kind": "neg", "variant": variant, "line": None,
                                      "text": text, "from_line": key, "split": split_of(key)})
                added += 1
    clips_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("near-miss negatives:", added, flush=True)


def number_tokens_words(words, lang, nums):
    """Positions (as a list of indexes, via enumerate in the caller) of number words."""
    return [i for i, w in enumerate(words) if w in nums]


def transcribe_all():
    import soundfile as sf
    clips = json.loads((OUT / "clips.json").read_text(encoding="utf-8"))
    rec = recognizers()
    out = json.loads(TRANSCRIPTS.read_text(encoding="utf-8"))["transcripts"] if TRANSCRIPTS.exists() else {}
    t0 = time.time()
    for i, c in enumerate(clips["clips"]):
        if c["id"] in out:
            continue
        x, sr = sf.read(str(CLIPS / f"{c['id']}.wav"), dtype="float32")
        if config.ASR_TRIM_SILENCE[c["lang"]]:
            x = trim(x)
        s = rec[c["lang"]].create_stream()
        s.accept_waveform(sr, x)
        rec[c["lang"]].decode_stream(s)
        out[c["id"]] = s.result.text.strip()
        if i % 200 == 0:
            print(i, f"{time.time() - t0:.0f} s", flush=True)
    TRANSCRIPTS.write_text(json.dumps({"pack": clips["pack"], "engine": "sherpa-onnx 1.13.8 int8, 2 threads, laptop",
                                       "transcripts": out}, ensure_ascii=False, indent=1), encoding="utf-8")


def score(rows, thr):
    acc = [r for r in rows if r["score"] >= thr and r["agree"]]
    correct = [r for r in acc if r["kind"] == "pos" and r["same"]]
    pos = [r for r in rows if r["kind"] == "pos"]
    p = len(correct) / len(acc) if acc else 1.0
    return {"threshold": thr, "precision": p, "recall": len(correct) / len(pos) if pos else 0.0,
            "accepted": len(acc), "correct": len(correct), "positives": len(pos),
            "negatives_accepted": sum(r["kind"] == "neg" for r in acc),
            "wrong_line": sum(r["kind"] == "pos" and not r["same"] for r in acc)}


def tune():
    clips = json.loads((OUT / "clips.json").read_text(encoding="utf-8"))
    tr = json.loads(TRANSCRIPTS.read_text(encoding="utf-8"))["transcripts"]
    _, _, _, hi, sat = pack_lines()
    cands = {"hi": list(hi), "sat": list(sat)}
    grid = [round(0.30 + 0.01 * i, 2) for i in range(66)]
    report, chosen = {}, {}
    for lang in ("hi", "sat"):
        rows = []
        for c in clips["clips"]:
            if c["lang"] != lang:
                continue
            line, s = best(tr[c["id"]], cands[lang], lang)
            same = line is not None and c["line"] is not None and canonical(line, lang) == canonical(c["line"], lang)
            agree = line is not None and number_tokens(tr[c["id"]], lang) == number_tokens(line, lang)
            rows.append(dict(c, best=line, score=s, same=same, agree=agree, transcript=tr[c["id"]]))
        tune_rows = [r for r in rows if r["split"] == "tune"]
        ok = [t for t in grid if score(tune_rows, t)["precision"] >= PRECISION_TARGET]
        thr = min(ok) if ok else max(grid)
        test_rows = [r for r in rows if r["split"] == "test"]
        report[lang] = {"threshold": thr, "tune": score(tune_rows, thr), "test": score(test_rows, thr),
                        "test_by_variant": {v: score([r for r in test_rows if r["variant"] == v or r["kind"] == "neg"], thr)
                                            for v in sorted({r["variant"] for r in rows if r["kind"] == "pos"})},
                        "negatives_accepted_by_kind": {v: sum(1 for r in test_rows if r["variant"] == v and r["score"] >= thr and r["agree"])
                                                       for v in sorted({r["variant"] for r in rows if r["kind"] == "neg"})},
                        "negatives_by_kind": {v: sum(1 for r in test_rows if r["variant"] == v)
                                              for v in sorted({r["variant"] for r in rows if r["kind"] == "neg"})},
                        "n_candidates": len(cands[lang]),
                        "counts": {k: sum(1 for r in rows if r["kind"] == k[:3] and r["split"] == k[4:])
                                   for k in ("pos_tune", "pos_test", "neg_tune", "neg_test")},
                        "test_curve": [score(test_rows, t) for t in (0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9)]}
        chosen[lang] = thr
    return clips["pack"], report, chosen


def write(pack, report):
    L = ["# Lesson-line matching (A1): threshold tuned on synthetic lesson clips", "",
         f"- Pack: `{pack}`. Clips and definitions: `bench/lesson_match_tune.py` docstring. Speech recognition: "
         "sherpa-onnx 1.13.8 int8 on the laptop, the tablet's models and settings (Hindi CTC, Santali transducer "
         "with silence trimming), 2 threads.",
         "- **Positives are synthetic** (Piper, one voice: the pack's own audio, faster, slower + noise). Negatives: "
         "real speech (80 public clips per language, FLEURS / IndicVoices) and IN22-Conv sentences in the same Piper voice. "
         "Children's and teachers' real voices: **NOT MEASURED**.",
         f"- Threshold = the lowest with tune precision >= {PRECISION_TARGET}; scored on the held-out test half "
         "(different lines). The rule was fixed before the first scoring; the test half had been seen when the "
         "near-misses and the number rule below were added.",
         "- A match needs the same numbers as the line (`lesson_match.number_tokens`), and the negatives include "
         "near-misses (a lesson line with one word or one number changed). **Both were added after the first tuning**, "
         "when a unit test showed an everyday sentence matching an unrelated lesson line at 0.51 (first tuning: "
         "Hindi threshold 0.41, test precision 0.970, recall 0.871, without near-misses).",
         "- A line and the same line written with digits (\"4\" / \"चार\") count as the same line (numbers are "
         "compared as words; `lesson_match.canonical`). Added after the first scoring showed these as 'wrong line'.",
         "- Errors no threshold removes: one-word lines misheard as another one-word line score 1.0 "
         "(e.g. Santali ᱜᱮᱞ recognised as ᱯᱮ).", ""]
    for lang, r in report.items():
        name = "Hindi (teacher's lesson line → Santali)" if lang == "hi" else "Santali (line → Hindi)"
        t = r["test"]
        L += [f"## {name}", "",
              f"- Candidates: {r['n_candidates']} pack lines. Clips: {r['counts']}.",
              f"- **Threshold {r['threshold']:.2f}.** Test half: **precision {t['precision']:.3f}, recall {t['recall']:.3f}** "
              f"({t['correct']} of {t['positives']} positives matched to their own line; accepted {t['accepted']}; "
              f"negatives accepted {t['negatives_accepted']}; wrong line {t['wrong_line']}). "
              f"Tune half: precision {r['tune']['precision']:.3f}, recall {r['tune']['recall']:.3f}.", "",
              "| Test half, positives of one version + all negatives | Precision | Recall |", "|---|---|---|"]
        for v, s in r["test_by_variant"].items():
            L.append(f"| {v} | {s['precision']:.3f} | {s['recall']:.3f} |")
        L += ["", "| Test half, negatives of one kind | Accepted / total |", "|---|---|"]
        for v, n in r["negatives_by_kind"].items():
            L.append(f"| {v} | {r['negatives_accepted_by_kind'][v]} / {n} |")
        L += ["", "| Threshold (test half) | Precision | Recall | Negatives accepted |", "|---|---|---|---|"]
        for s in r["test_curve"]:
            L.append(f"| {s['threshold']:.2f} | {s['precision']:.3f} | {s['recall']:.3f} | {s['negatives_accepted']} |")
        L.append("")
    RESULT.write_text("\n".join(L), encoding="utf-8", newline="\n")
    (ROOT / "bench" / "results" / "lesson_match.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--score-only", action="store_true")
    a = ap.parse_args()
    if not a.score_only:
        if not (OUT / "clips.json").exists():
            make_clips()
        make_near_miss()
        transcribe_all()
    pack, report, chosen = tune()
    write(pack, report)
    print("chosen", chosen)


if __name__ == "__main__":
    main()
