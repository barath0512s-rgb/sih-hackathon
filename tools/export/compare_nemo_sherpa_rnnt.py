"""F1 Phase A: the sherpa-onnx transducer export vs NeMo's own RNN-T, and the empty /
hallucinated-output check (sherpa-onnx issue #3267, docs/sources.md#sherpa-hotwords).

    python tools/export/compare_nemo_sherpa_rnnt.py --model-dir models/indicconformer-120m-sherpa --threads 2

For each language, fp32 and int8, and three decoding set-ups:
  greedy                 greedy_search
  beam                   modified_beam_search, 4 active paths, no hotwords (issue #3267's case)
  beam+hotwords          the same with a hotwords file of the lessons' accepted answers in
                         that language (score 1.5): does unrelated biasing change the output?
every public clip is decoded and compared with NeMo's own RNN-T transcript:
  same as NeMo, WER vs NeMo, WER vs the reference (normalised; tags removed from
  references only), empty outputs (NeMo's non-empty), and "hallucinated" outputs:
  non-empty, WER >= 0.5 against NeMo's transcript, where NeMo itself had WER < 0.5
  against the reference (so the clip was not simply hard).
Writes bench/results/sherpa_vs_nemo_rnnt.md. Laptop (WSL2), --threads threads.
"""

import argparse
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAT_CAVEAT = ("Santali clips: IndicVoices validation split (no public Santali test split); "
              "may overlap model-development data.")


def hotwords(lang):
    """The accepted answers of every lesson step in `lang` (hi or sat), one per line."""
    sys.path.insert(0, str(ROOT))
    from lesson_engine import NIPUN_LESSONS
    words = set()
    for g in NIPUN_LESSONS.values():
        for lesson in g.values():
            for st in lesson["steps"]:
                for w in (st.get("accept_answers") or {}).get(lang, []):
                    if w.strip():
                        words.add(w.strip())
    return sorted(words)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model-dir", required=True, type=Path)
    ap.add_argument("--manifest", default=ROOT / "bench/clips/public/manifest.json", type=Path)
    ap.add_argument("--threads", type=int, default=2)
    a = ap.parse_args()

    import jiwer
    import sherpa_onnx
    import soundfile as sf
    sys.path.insert(0, str(ROOT))
    from textnorm import normalize_for_wer as nw, strip_reference_tags

    clips = json.loads(a.manifest.read_text(encoding="utf-8"))
    lines = ["# sherpa-onnx transducer vs NeMo RNN-T (IndicConformer 120M)", "",
             f"Laptop (WSL2, Ubuntu), {a.threads} threads. Public clips (`{a.manifest.relative_to(ROOT).as_posix()}`); "
             "WER/CER normalised (bench/README.md; tags removed from references only). "
             "NeMo = the fork's own RNN-T transcripts from the export script. "
             "Hallucinated = non-empty, WER vs NeMo >= 0.5 where NeMo's own WER vs the reference < 0.5. "
             "Beam = modified_beam_search, 4 paths; hotwords score 1.5.",
             f"{SAT_CAVEAT}", "",
             "| Lang | Model | Decoding | n | n_distinct | Same as NeMo | WER vs NeMo | WER vs ref | NeMo WER vs ref | "
             "Empty (NeMo non-empty) | Hallucinated | Changed by hotwords | Median ms |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for lang in ("hi", "sat"):
        d = a.model_dir / lang / "rnnt"
        if not (d / "nemo_rnnt_transcripts.json").exists():
            print(f"{lang}: no export in {d}, skipped"); continue
        nemo_map = json.loads((d / "nemo_rnnt_transcripts.json").read_text(encoding="utf-8"))
        cl = [c for c in clips if c["lang"] == lang and c["file"] in nemo_map]
        refs = [nw(strip_reference_tags(c["reference"])[0]) for c in cl]
        n_distinct = len({r for r in refs})
        nemo = [nw(nemo_map[c["file"]]) for c in cl]
        nemo_wer_each = [jiwer.wer(r, h) if r else 0.0 for r, h in zip(refs, nemo)]
        audio = []
        for c in cl:
            x, sr = sf.read(str(ROOT / c["file"]), dtype="float32")
            audio.append((x.mean(axis=1) if x.ndim > 1 else x, sr))
        hw_file = Path(tempfile.mkdtemp()) / "hotwords.txt"
        hw_file.write_text("\n".join(hotwords(lang)) + "\n", encoding="utf-8")
        for suffix in (".int8", ""):
            files = {p: str(d / f"{p}{suffix}.onnx") for p in ("encoder", "decoder", "joiner")}
            outs = {}
            for mode in ("greedy", "beam", "beam+hotwords"):
                kw = dict(num_threads=a.threads, model_type="nemo_transducer",
                          decoding_method="greedy_search" if mode == "greedy" else "modified_beam_search",
                          max_active_paths=4)
                if mode == "beam+hotwords":
                    kw.update(hotwords_file=str(hw_file), hotwords_score=1.5, modeling_unit="bpe",
                              bpe_vocab=str(d / "bpe.vocab"))
                rec = sherpa_onnx.OfflineRecognizer.from_transducer(tokens=str(d / "tokens.txt"), **files, **kw)
                hyps, ms = [], []
                for x, sr in audio:
                    t0 = time.perf_counter()
                    s = rec.create_stream(); s.accept_waveform(sr, x); rec.decode_stream(s)
                    hyps.append(nw(s.result.text)); ms.append((time.perf_counter() - t0) * 1000)
                outs[mode] = hyps
                empty = sum(1 for h, n in zip(hyps, nemo) if not h and n)
                halluc = sum(1 for h, n, nwer in zip(hyps, nemo, nemo_wer_each)
                             if h and n and nwer < 0.5 and jiwer.wer(n, h) >= 0.5)
                changed = (sum(x != y for x, y in zip(hyps, outs["beam"])) if mode == "beam+hotwords" else "")
                lines.append(
                    f"| {lang} | {'int8' if suffix else 'fp32'} | {mode} | {len(cl)} | {n_distinct} | "
                    f"{sum(h == n for h, n in zip(hyps, nemo))}/{len(cl)} | "
                    f"{100 * jiwer.wer(nemo, hyps):.1f}% | {100 * jiwer.wer(refs, hyps):.1f}% | "
                    f"{100 * jiwer.wer(refs, nemo):.1f}% | {empty} | {halluc} | {changed} | {statistics.median(ms):.0f} |")
                print(lines[-1], flush=True)
        lines.append(f"| {lang} | | hotwords file | | | {len(hotwords(lang))} accepted answers from the lessons | | | | | | | |")
    out = ROOT / "bench/results/sherpa_vs_nemo_rnnt.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
