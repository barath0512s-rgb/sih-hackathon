"""ASR choices, measured: RNN-T vs CTC decoding, with and without silence trimming.

    python bench/asr_decoding.py [--clips bench/clips/synthetic/manifest.json]

Runs every clip through IndicConformer four ways and reports median ASR time
and median CER per language, so the default decoder can be chosen per language
on evidence. Writes bench/results/asr_decoding_<label>.md.
With synthetic clips, the CER compares variants on the same audio; it is not
a measure of accuracy on real classroom speech.
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402,F401  (offline environment)
from textnorm import normalize_key  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", default=str(ROOT / "bench/clips/synthetic/manifest.json"))
    ap.add_argument("--label", default="synthetic")
    a = ap.parse_args()
    manifest = json.loads(Path(a.clips).read_text(encoding="utf-8"))

    import jiwer
    import pipeline
    from indicconformer_asr import IndicConformerASR
    asr = IndicConformerASR()
    to_wav = pipeline.VaaniSetuPipeline._to_wav

    wavs = []
    for c in manifest:                       # decode webm once, outside the timing
        wavs.append((c, to_wav(str(ROOT / c["file"]))))
    asr.transcribe(wavs[0][1], lang="hi", decoding="rnnt")      # warm up

    variants = [("rnnt", False), ("rnnt", True), ("ctc", False), ("ctc", True)]
    res = {}
    for dec, trim in variants:
        for c, wav in wavs:
            t0 = time.perf_counter()
            hyp = asr.transcribe(wav, lang=c["lang"], decoding=dec, trim=trim)
            ms = (time.perf_counter() - t0) * 1000
            cer = jiwer.cer(normalize_key(c["reference"]), normalize_key(hyp))
            res.setdefault((c["lang"], dec, trim), []).append((ms, cer))
        print(f"  done: {dec} trim={trim}")

    synthetic = any("synthetic" in c.get("kind", "") for c in manifest)
    lines = [f"# ASR decoding and silence trimming ({a.label})", "",
             f"{len(manifest)} clips; ASR only (audio already decoded to WAV); times in ms.", ""]
    if synthetic:
        lines += ["> Synthetic clips. CER compares the variants on identical audio; it is not",
                  "> ASR accuracy on real speech.", ""]
    lines += ["| Language | Decoding | Trim silence | ASR median ms | ASR p90 ms | CER median | CER mean |",
              "|---|---|---|---|---|---|---|"]
    for lang in ("hi", "sat"):
        for dec, trim in variants:
            v = res.get((lang, dec, trim))
            if not v:
                continue
            ms = sorted(x for x, _ in v)
            cers = [y for _, y in v]
            p90 = ms[max(0, -(-len(ms) * 90 // 100) - 1)]
            lines.append(f"| {lang} | {dec} | {'yes' if trim else 'no'} | {statistics.median(ms):.0f} | "
                         f"{p90:.0f} | {statistics.median(cers):.3f} | {statistics.mean(cers):.3f} |")
    out = ROOT / "bench" / "results" / f"asr_decoding_{a.label}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
