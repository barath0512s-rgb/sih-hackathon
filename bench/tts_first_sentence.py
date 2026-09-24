"""Would playing the first sentence early save meaningful time?

    python bench/tts_first_sentence.py

Early playback means synthesising and sending the first sentence while the
rest is still being synthesised. The most it can save is the TTS time of the
sentences after the first. This measures that ceiling on the benchmark lines:
TTS time for the whole reply vs for its first sentence only (empty cache).
Writes bench/results/tts_first_sentence.md.
"""

import json
import re
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402

SPLIT = re.compile(r"(?<=[।॥᱾?!.])\s+")


def main():
    import pipeline
    config.TTS_CACHE_DIR = Path(tempfile.mkdtemp(prefix="tts_first_"))
    pl = pipeline.VaaniSetuPipeline()
    manifest = json.loads((ROOT / "bench/clips/synthetic/manifest.json").read_text(encoding="utf-8"))
    out = Path(tempfile.mkdtemp()) / "x.wav"

    rows = []
    for i, c in enumerate(manifest):
        direction = "hi-to-sat" if c["lang"] == "hi" else "sat-to-hi"
        reply = pl.translate(c["reference"], direction)["text"]
        speak = pl.santali_tts if direction == "hi-to-sat" else pl.hindi_tts
        parts = [p for p in SPLIT.split(reply.strip()) if p.strip()]
        # A unique suffix defeats the TTS cache, so every call is real synthesis.
        t0 = time.perf_counter(); speak(reply + " " * (i % 7), str(out)); full = time.perf_counter() - t0
        t0 = time.perf_counter(); speak(parts[0] + " " * (i % 7 + 7), str(out)); first = time.perf_counter() - t0
        rows.append({"sentences": len(parts), "full_ms": full * 1000, "first_ms": first * 1000})

    multi = [r for r in rows if r["sentences"] > 1]
    saving = [r["full_ms"] - r["first_ms"] for r in multi]
    lines = ["# Early playback: the most it could save", "",
             f"{len(rows)} replies; {len(multi)} have more than one sentence.", "",
             f"- TTS for the whole reply, median over all replies: {statistics.median(r['full_ms'] for r in rows):.0f} ms",
             f"- Upper bound on the saving, multi-sentence replies only: median "
             f"{statistics.median(saving):.0f} ms, max {max(saving):.0f} ms" if saving else
             "- No multi-sentence replies, so early playback could save nothing.",
             f"- Share of replies that could benefit at all: {len(multi)} of {len(rows)}"]
    (ROOT / "bench/results/tts_first_sentence.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
