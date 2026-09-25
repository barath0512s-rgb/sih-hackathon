"""ASR choices, measured: RNN-T vs CTC decoding, with and without silence trimming.

    python bench/asr_decoding.py [--clips bench/clips/synthetic/manifest.json] [--label synthetic]
    python bench/asr_decoding.py --label public --rescore      # rebuild the report from the saved .jsonl

Runs every clip through IndicConformer four ways and reports median ASR time
and, per language, **raw WER** (reference and hypothesis exactly as written) and
**normalised WER and CER** (textnorm.normalize_for_wer on both sides; dataset
annotation tags such as <unintelligible> are removed from the REFERENCE only,
and counted; rules in bench/README.md), so the decoder and silence trimming can
be chosen per language on evidence. Every table gives n (clips) and n_distinct
(distinct reference sentences: FLEURS has several readers per sentence).
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
from textnorm import normalize_for_wer, normalize_key, strip_reference_tags  # noqa: E402

VARIANTS = [("rnnt", False), ("rnnt", True), ("ctc", False), ("ctc", True)]
# Where the Santali numbers come from, printed wherever they appear (docs/sources.md#indicvoices).
SAT_CAVEAT = ("Santali clips: IndicVoices validation split (no public Santali test split); "
              "may overlap model-development data.")


def score(rows):
    """Corpus scores for one (language, decoding, trim) group of jsonl rows."""
    import jiwer
    refs, removed = [], 0
    for r in rows:
        text, n = strip_reference_tags(r["reference_raw"])
        refs.append(normalize_for_wer(text)); removed += n
    hyps = [normalize_for_wer(r["hypothesis_raw"]) for r in rows]
    ms = sorted(r["asr_ms"] for r in rows)
    return {
        "n": len(rows), "n_distinct": len({normalize_key(r["reference_raw"]) for r in rows}),
        "median_ms": statistics.median(ms), "p90_ms": ms[max(0, -(-len(ms) * 90 // 100) - 1)],
        "wer_raw": jiwer.wer([r["reference_raw"] for r in rows], [r["hypothesis_raw"] for r in rows]),
        "wer_norm": jiwer.wer(refs, hyps), "cer_norm": jiwer.cer(refs, hyps),
        "cer_median": statistics.median(jiwer.cer(a, b) if a else 0.0 for a, b in zip(refs, hyps)),
        "tags_removed": removed,
    }


def report(label, rows, clips_path, synthetic, public):
    lines = [f"# ASR decoding and silence trimming ({label})", "",
             f"{len({r['clip'] for r in rows})} clips; ASR only (audio already decoded to WAV); times in ms.", ""]
    if synthetic:
        lines += ["> Synthetic clips. CER compares the variants on identical audio; it is not",
                  "> ASR accuracy on real speech.", ""]
    if public:
        lines += ["> **Public dataset, adult speech.** Child speech: NOT MEASURED. Sources and",
                  f"> licences per clip: `{clips_path}`. Laptop, offline.",
                  "> WER and CER are corpus-level (all errors / all reference words or characters).",
                  f"> {SAT_CAVEAT}", ""]
    lines += ["Raw = texts exactly as written. Normalised = `textnorm.normalize_for_wer` on both sides, after",
              "removing dataset tags (`<unintelligible>`) from the references only (bench/README.md,",
              "\"WER normalisation\"). n = clips, n_distinct = distinct reference sentences.", "",
              "| Language | Decoding | Trim silence | n | n_distinct | ASR median ms | ASR p90 ms | WER raw | "
              "WER normalised | CER normalised | CER median per clip | Tags removed from references |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for lang in ("hi", "sat"):
        for dec, trim in VARIANTS:
            g = [r for r in rows if r["lang"] == lang and r["decoding"] == dec and r["trim"] == trim]
            if not g:
                continue
            s = score(g)
            lines.append(f"| {lang} | {dec} | {'yes' if trim else 'no'} | {s['n']} | {s['n_distinct']} | "
                         f"{s['median_ms']:.0f} | {s['p90_ms']:.0f} | {s['wer_raw']:.3f} | {s['wer_norm']:.3f} | "
                         f"{s['cer_norm']:.3f} | {s['cer_median']:.3f} | {s['tags_removed']} |")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", default=str(ROOT / "bench/clips/synthetic/manifest.json"))
    ap.add_argument("--label", default="synthetic")
    ap.add_argument("--rescore", action="store_true", help="rebuild the report from the saved jsonl, no ASR")
    a = ap.parse_args()
    raw = ROOT / "bench" / "results" / f"asr_decoding_{a.label}.jsonl"
    manifest = json.loads(Path(a.clips).read_text(encoding="utf-8")) if not a.rescore else []

    if not a.rescore:
        import pipeline
        from indicconformer_asr import IndicConformerASR
        asr = IndicConformerASR()
        to_wav = pipeline.VaaniSetuPipeline._to_wav
        wavs = [(c, to_wav(str(ROOT / c["file"]))) for c in manifest]   # decode once, outside the timing
        asr.transcribe(wavs[0][1], lang="hi", decoding="rnnt")          # warm up
        rows = []
        for dec, trim in VARIANTS:
            for c, wav in wavs:
                t0 = time.perf_counter()
                hyp = asr.transcribe(wav, lang=c["lang"], decoding=dec, trim=trim)
                rows.append({"clip": c["file"], "lang": c["lang"], "decoding": dec, "trim": trim,
                             "asr_ms": round((time.perf_counter() - t0) * 1000, 1),
                             "reference_raw": c["reference"].strip(), "hypothesis_raw": (hyp or "").strip()})
            print(f"  done: {dec} trim={trim}")
        # Raw per-clip results first, so nothing is lost if the report fails.
        raw.parent.mkdir(parents=True, exist_ok=True)
        with open(raw, "w", encoding="utf-8", newline="\n") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    rows = [json.loads(l) for l in raw.read_text(encoding="utf-8").splitlines() if l.strip()]
    kinds = " ".join(c.get("kind", "") for c in manifest) or ("public" if "public" in a.label else "synthetic")
    clips_path = Path(a.clips).resolve().relative_to(ROOT).as_posix() if not a.rescore else \
        "bench/clips/public/manifest.json" if "public" in a.label else Path(a.clips).resolve().relative_to(ROOT).as_posix()
    lines = report(a.label, rows, clips_path, "synthetic" in kinds, "public" in kinds)
    out = ROOT / "bench" / "results" / f"asr_decoding_{a.label}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
