"""ASR choices, measured: RNN-T vs CTC decoding, with and without silence trimming.

    python bench/asr_decoding.py [--clips bench/clips/synthetic/manifest.json]

Runs every clip through IndicConformer four ways and reports median ASR time
and, per language, **raw WER** (reference and hypothesis exactly as written) and
**normalised WER and CER** (textnorm.normalize_for_wer on both sides: punctuation
including ᱾, digits, whitespace and dataset tags; rules in bench/README.md), so
the decoder and silence trimming can be chosen per language on evidence.
Writes bench/results/asr_decoding_<label>.{md,jsonl}.
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
from textnorm import normalize_for_wer, normalize_key  # noqa: E402


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
            ref, h = normalize_for_wer(c["reference"]), normalize_for_wer(hyp)
            cer = jiwer.cer(ref, h) if ref else 0.0
            wer = jiwer.wer(ref, h) if ref else 0.0
            res.setdefault((c["lang"], dec, trim), []).append(
                (ms, cer, wer, ref, h, c["reference"].strip(), (hyp or "").strip()))
        print(f"  done: {dec} trim={trim}")

    # Raw per-clip results first, so nothing is lost if the report fails.
    raw = ROOT / "bench" / "results" / f"asr_decoding_{a.label}.jsonl"
    raw.parent.mkdir(parents=True, exist_ok=True)
    with open(raw, "w", encoding="utf-8") as f:
        for (lang, dec, trim), v in res.items():
            for c_, (ms, cer, wer, ref, h, rraw, hraw) in zip([c for c, _ in wavs if c["lang"] == lang], v):
                f.write(json.dumps({"clip": c_["file"], "lang": lang, "decoding": dec, "trim": trim,
                                    "asr_ms": round(ms, 1), "cer_norm": round(cer, 4), "wer_norm": round(wer, 4),
                                    "reference_raw": rraw, "hypothesis_raw": hraw,
                                    "reference_norm": ref, "hypothesis_norm": h,
                                    "reference_key": normalize_key(rraw), "hypothesis_key": normalize_key(hraw)},
                                   ensure_ascii=False) + "\n")
    synthetic = any("synthetic" in c.get("kind", "") for c in manifest)
    public = any("public" in c.get("kind", "") for c in manifest)
    lines = [f"# ASR decoding and silence trimming ({a.label})", "",
             f"{len(manifest)} clips; ASR only (audio already decoded to WAV); times in ms.", ""]
    if synthetic:
        lines += ["> Synthetic clips. CER compares the variants on identical audio; it is not",
                  "> ASR accuracy on real speech.", ""]
    if public:
        lines += ["> **Public dataset, adult speech.** Child speech: NOT MEASURED. Sources and",
                  f"> licences per clip: `{Path(a.clips).resolve().relative_to(ROOT).as_posix()}`. Laptop, offline.",
                  "> WER and CER are corpus-level (all errors / all reference words or characters).", ""]
    lines += ["Raw = texts exactly as written. Normalised = `textnorm.normalize_for_wer` on both sides",
              "(bench/README.md, \"WER normalisation\").", "",
              "| Language | Decoding | Trim silence | ASR median ms | ASR p90 ms | WER raw | WER normalised | "
              "CER normalised | CER median per clip |",
              "|---|---|---|---|---|---|---|---|---|"]
    for lang in ("hi", "sat"):
        for dec, trim in variants:
            v = res.get((lang, dec, trim))
            if not v:
                continue
            ms = sorted(x[0] for x in v)
            cers = [x[1] for x in v]
            refs, hyps = [x[3] for x in v], [x[4] for x in v]
            raw_refs, raw_hyps = [x[5] for x in v], [x[6] for x in v]
            p90 = ms[max(0, -(-len(ms) * 90 // 100) - 1)]
            lines.append(f"| {lang} | {dec} | {'yes' if trim else 'no'} | {statistics.median(ms):.0f} | "
                         f"{p90:.0f} | {jiwer.wer(raw_refs, raw_hyps):.3f} | {jiwer.wer(refs, hyps):.3f} | "
                         f"{jiwer.cer(refs, hyps):.3f} | {statistics.median(cers):.3f} |")
    out = ROOT / "bench" / "results" / f"asr_decoding_{a.label}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
