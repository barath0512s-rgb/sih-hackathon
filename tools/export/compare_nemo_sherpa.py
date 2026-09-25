"""F1 Phase A: does the sherpa-onnx export transcribe like NeMo?

    pip install sherpa-onnx soundfile jiwer
    python tools/export/compare_nemo_sherpa.py --model-dir models/indicconformer-120m-sherpa --threads 2

`--model-dir` holds what `indicconformer_sherpa_export.py` wrote (out/<lang>/:
model.int8.onnx, model.onnx, tokens.txt, nemo_transcripts.json). For each
language and each model file, every Phase P public clip is decoded with
sherpa-onnx (CTC, greedy). The result is compared with NeMo's own transcript
(exact-match rate, WER sherpa vs NeMo) and with the reference (WER, CER).
Writes bench/results/sherpa_vs_nemo.md. Laptop timings, `--threads` threads.
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model-dir", required=True, type=Path)
    ap.add_argument("--manifest", default=ROOT / "bench/clips/public/manifest.json", type=Path)
    ap.add_argument("--threads", type=int, default=2)
    a = ap.parse_args()

    import jiwer
    import sherpa_onnx
    import soundfile as sf

    clips = json.loads(a.manifest.read_text(encoding="utf-8"))
    lines = ["# sherpa-onnx export vs NeMo (IndicConformer 120M, CTC)", "",
             f"Laptop, {a.threads} threads, greedy CTC. Clips: `{a.manifest.relative_to(ROOT).as_posix()}`. "
             "NeMo transcripts from the export notebook (same clips, NeMo CTC).", "",
             "| Lang | Model | n | Same as NeMo | WER vs NeMo | WER vs ref | CER vs ref | NeMo WER vs ref | "
             "Median ms | Size MB |", "|---|---|---|---|---|---|---|---|---|---|"]
    for lang in ("hi", "sat"):
        d = a.model_dir / lang
        if not d.exists():
            print(f"{lang}: {d} missing, skipped")
            continue
        nemo = json.loads((d / "nemo_transcripts.json").read_text(encoding="utf-8"))
        cl = [c for c in clips if c["lang"] == lang and c["file"] in nemo]
        refs = [c["reference"] for c in cl]
        for mf in ("model.int8.onnx", "model.onnx"):
            if not (d / mf).exists():
                continue
            rec = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(
                model=str(d / mf), tokens=str(d / "tokens.txt"), num_threads=a.threads,
                decoding_method="greedy_search")
            hyps, ms = [], []
            for c in cl:
                x, sr = sf.read(str(ROOT / c["file"]), dtype="float32")
                if x.ndim > 1:
                    x = x.mean(axis=1)
                t0 = time.perf_counter()
                s = rec.create_stream()
                s.accept_waveform(sr, x)
                rec.decode_stream(s)
                hyps.append(s.result.text.strip())
                ms.append((time.perf_counter() - t0) * 1000)
            ne = [nemo[c["file"]] for c in cl]
            same = sum(h == n for h, n in zip(hyps, ne))
            lines.append(f"| {lang} | {mf} | {len(cl)} | {same}/{len(cl)} | "
                         f"{100 * jiwer.wer(ne, hyps):.1f}% | {100 * jiwer.wer(refs, hyps):.1f}% | "
                         f"{100 * jiwer.cer(refs, hyps):.1f}% | {100 * jiwer.wer(refs, ne):.1f}% | "
                         f"{statistics.median(ms):.0f} | {(d / mf).stat().st_size / 1e6:.0f} |")
            print(lines[-1], flush=True)
    out = ROOT / "bench/results/sherpa_vs_nemo.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    sys.exit(main())
