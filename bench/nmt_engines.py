"""Phase L1: translation engines compared on the same sentences.

    python bench/nmt_engines.py

Engines (IndicTrans2 indic-indic-dist-320M, greedy, the app's no-repeat and
length settings):
  torch-fp32-t14   PyTorch as the app ran before Phase L (all 14 physical cores)
  torch-fp32-t4    PyTorch, 4 threads
  torch-int8-t4    PyTorch with dynamic int8 Linear layers (L1c), 4 threads
  onnx-fp32-t6     ONNX Runtime fp32 (L1b), 6 threads   <- the app now
  onnx-int8-t6     ONNX Runtime dynamic int8 (L1b), 6 threads
CTranslate2 (L1a) is not in the list: its converters do not support this
model (docs/sources.md#ctranslate2).

Sentences: FLEURS Hindi references (public, long) and the Hindi lesson lines
(short), timed by word-count bin. "same" = token IDs identical to
torch-fp32-t14. Accuracy against human references needs IN22/FLORES: NOT
MEASURED here. Writes bench/results/nmt_engines.md.
"""

import copy
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402

BINS = ((0, 11), (12, 17), (18, 23), (24, 999))


def main():
    import torch
    from IndicTransToolkit import IndicProcessor
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    import nmt_onnx

    tok = AutoTokenizer.from_pretrained(str(config.NMT_DIR), trust_remote_code=True)
    fp32 = AutoModelForSeq2SeqLM.from_pretrained(str(config.NMT_DIR), trust_remote_code=True).eval()
    q8 = torch.ao.quantization.quantize_dynamic(copy.deepcopy(fp32), {torch.nn.Linear}, dtype=torch.qint8)
    ip = IndicProcessor(inference=True)

    def torch_engine(model, threads):
        def run(s):
            torch.set_num_threads(threads)
            b = ip.preprocess_batch([s], src_lang="hin_Deva", tgt_lang="sat_Olck")
            enc = tok(b, truncation=True, padding="longest", return_tensors="pt")
            lim = min(config.NMT_MAX_TOKENS, config.NMT_LIMIT_FACTOR * enc["input_ids"].shape[1] + config.NMT_LIMIT_MARGIN)
            with torch.no_grad():
                return model.generate(**enc, num_beams=1, max_new_tokens=lim,
                                      no_repeat_ngram_size=config.NMT_NO_REPEAT_NGRAM)[0].tolist()
        return run

    def onnx_engine(int8, threads):
        eng = nmt_onnx.OnnxNMT(tok, IndicProcessor(inference=True), int8=int8, threads=threads)
        return lambda s: eng.translate(s, "hin_Deva", "sat_Olck")[1]

    engines = {"torch-fp32-t14": torch_engine(fp32, 14), "torch-fp32-t4": torch_engine(fp32, 4),
               "torch-int8-t4": torch_engine(q8, 4), "onnx-fp32-t6": onnx_engine(False, 6),
               "onnx-int8-t6": onnx_engine(True, 6)}

    pub = [(c["reference"], "public") for c in json.loads(
        (ROOT / "bench/clips/public/manifest.json").read_text(encoding="utf-8")) if c["lang"] == "hi"]
    les = [(c["reference"], "lesson") for c in json.loads(
        (ROOT / "bench/clips/synthetic/manifest.json").read_text(encoding="utf-8")) if c["lang"] == "hi"]
    sents = pub + les

    res = {}
    for name, run in engines.items():
        run("नमस्ते बच्चो")                                       # warm-up
        rows = []
        for s, kind in sents:
            t0 = time.perf_counter(); ids = run(s); ms = (time.perf_counter() - t0) * 1000
            rows.append((kind, len(s.split()), ms, ids))
        res[name] = rows
        print(f"{name}: done", flush=True)

    ref = res["torch-fp32-t14"]
    lines = ["# Translation engines, same sentences (Phase L1)", "",
             "IndicTrans2 indic-indic-dist-320M, hin_Deva → sat_Olck, greedy, the app's settings. Laptop, offline.",
             "Median ms per sentence. \"same\" = token IDs identical to PyTorch fp32 (14 threads).",
             "public = FLEURS Hindi references (long); lesson = Hindi lesson lines (short).", "",
             "| Engine | public 0-11 | 12-17 | 18-23 | 24+ | public all | lesson all | same as PyTorch |",
             "|---|---|---|---|---|---|---|---|"]
    for name, rows in res.items():
        cells = []
        for lo, hi in BINS:
            v = [r[2] for r in rows if r[0] == "public" and lo <= r[1] <= hi]
            cells.append(f"{statistics.median(v):.0f}" if v else "-")
        allp = statistics.median([r[2] for r in rows if r[0] == "public"])
        alll = statistics.median([r[2] for r in rows if r[0] == "lesson"])
        same = sum(a[3] == b[3] for a, b in zip(rows, ref))
        lines.append(f"| {name} | {' | '.join(cells)} | {allp:.0f} | {alll:.0f} | {same} of {len(rows)} |")
    out = ROOT / "bench" / "results" / "nmt_engines.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
