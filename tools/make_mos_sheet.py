"""A6: the MOS-lite listening sheet for native Santali listeners, with blind A/B clips.

    python tools/make_mos_sheet.py

Ten pack lines (fixed seed), each in the live Piper voice and in Indic Parler-TTS,
written to docs/samples/voices/ as <n>_A.wav / <n>_B.wav with the voice order
shuffled per line; which voice is A or B is in docs/samples/voices/key.json (for
the team, not for listeners). docs/samples/mos_lite_sheet.md is the sheet. Scores
stay NOT MEASURED until native listeners fill it in.
"""
import glob
import io
import json
import random
import zipfile
from pathlib import Path

import librosa
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "samples" / "voices"


def main():
    pack = sorted(glob.glob(str(ROOT / "dist" / "packs" / "content-pack-*.zip")))[-1]
    z = zipfile.ZipFile(pack)
    index = json.loads(z.read("audio/index.json"))["sat"]
    pidx = json.loads((ROOT / "content_audio" / "parler" / "index.json").read_text(encoding="utf-8"))
    lines = sorted(t for t in index if t in pidx and 2 <= len(t.split()) <= 10)
    rnd = random.Random(20260926)
    chosen = rnd.sample(lines, 10)
    OUT.mkdir(parents=True, exist_ok=True)
    key, rows = [], []
    for n, text in enumerate(chosen, 1):
        clips = {"piper": sf.read(io.BytesIO(z.read(f"audio/{index[text]}")), dtype="float32"),
                 "parler": sf.read(str(ROOT / "content_audio" / "parler" / pidx[text]["file"]), dtype="float32")}
        order = ["piper", "parler"]
        rnd.shuffle(order)
        for label, voice in zip("AB", order):
            x, sr = clips[voice]
            if sr != 22050:
                x = librosa.resample(x, orig_sr=sr, target_sr=22050)
            sf.write(str(OUT / f"{n:02d}_{label}.wav"), x, 22050, subtype="PCM_16")
        key.append({"n": n, "text": text, "A": order[0], "B": order[1]})
        rows.append(f"| {n} | {text} | `{n:02d}_A.wav` | | | `{n:02d}_B.wav` | | | |")
    (OUT / "key.json").write_text(json.dumps({"pack": Path(pack).name, "lines": key}, ensure_ascii=False, indent=1),
                                  encoding="utf-8", newline="\n")
    sheet = ["# Santali voice: listening sheet (MOS-lite)", "",
             "For a native Santali speaker. For each line, listen to clip A and clip B (in `docs/samples/voices/`).",
             "Score each clip from 1 to 5:", "",
             "- **Clear**: 1 = cannot understand, 3 = understandable with effort, 5 = completely clear",
             "- **Natural**: 1 = very unnatural, 3 = acceptable, 5 = sounds like a person",
             "", "Then say which one a child should hear (A, B, or neither). Please do not look at `key.json`.", "",
             "Listener: ____________  Home area / variety of Santali: ____________  Date: ________", "",
             "| # | Line (Ol Chiki) | Clip A | A clear | A natural | Clip B | B clear | B natural | Better (A / B / neither) |",
             "|---|---|---|---|---|---|---|---|---|"] + rows + [
             "", "Scores: **NOT MEASURED** until this sheet is filled in. The automatic comparison (ASR round trip) is in "
             "`bench/results/voice_compare.md`."]
    (ROOT / "docs" / "samples" / "mos_lite_sheet.md").write_text("\n".join(sheet) + "\n", encoding="utf-8", newline="\n")
    print("wrote", OUT, "and docs/samples/mos_lite_sheet.md")


if __name__ == "__main__":
    main()
