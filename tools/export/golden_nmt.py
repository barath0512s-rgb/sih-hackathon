"""Golden test: ONNX translation vs the PyTorch model, token for token.

    python tools/export/golden_nmt.py --n 300 [--int8] [--threads 2] [--src sat]

Hindi sentences (default): the Hindi lesson lines, the team's lesson lines and
the public FLEURS Hindi references (bench/clips/public/manifest.json), then
IN22-Conv Hindi sentences in dataset order up to --n. Santali (--src sat): the
IN22-Conv Santali sentences in order. IN22-Conv is an evaluation set: only
match statistics are written here, never its sentences. For each, the
greedy token IDs from PyTorch (pipeline._nmt settings) and from nmt_onnx must
be identical. Reports the identical rate (target >= 98%), chrF++ of the ONNX
output against the PyTorch output, and median time per sentence for both
(4 threads each). Writes bench/results/golden_nmt_<fp32|int8>.md.
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import config  # noqa: E402


def in22_conv(col):
    import pyarrow.parquet as pq
    f = next((ROOT / "data" / "public" / "ai4bharat__IN22-Conv").rglob("*.parquet"), None)
    if f is None:
        return []
    t = pq.read_table(f)
    name = next(c for c in t.schema.names if c == col or c.endswith(col) or c.startswith(col))
    return [x.strip() for x in t.column(name).to_pylist() if x and x.strip()]


def sentences(n, src="hi"):
    if src == "sat":
        return in22_conv("sat_Olck")[:n]
    from lesson_engine import NIPUN_LESSONS
    s = [st["hindi"] for g in NIPUN_LESSONS.values() for l in g.values() for st in l["steps"]]
    team = json.loads((ROOT / "content" / "team_lessons.json").read_text(encoding="utf-8"))
    s += [x["hindi"] for L in team["lessons"] for x in L["lines"]]
    pub = ROOT / "bench" / "clips" / "public" / "manifest.json"
    if pub.exists():
        s += [c["reference"] for c in json.loads(pub.read_text(encoding="utf-8")) if c["lang"] == "hi"]
    s += in22_conv("hin_Deva")
    seen, out = set(), []
    for x in s:
        if x not in seen:
            seen.add(x); out.append(x)
    return out[:n]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--int8", action="store_true")
    ap.add_argument("--variant", help="file suffix, e.g. int8pc (per-channel int8)")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--src", choices=("hi", "sat"), default="hi")
    a = ap.parse_args()
    sl, tl = ("hin_Deva", "sat_Olck") if a.src == "hi" else ("sat_Olck", "hin_Deva")

    import sacrebleu
    import torch
    from IndicTransToolkit import IndicProcessor
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    import nmt_onnx

    torch.set_num_threads(a.threads)
    tok = AutoTokenizer.from_pretrained(str(config.NMT_DIR), trust_remote_code=True)
    mdl = AutoModelForSeq2SeqLM.from_pretrained(str(config.NMT_DIR), trust_remote_code=True).eval()
    ip = IndicProcessor(inference=True)
    eng = nmt_onnx.OnnxNMT(tok, IndicProcessor(inference=True), int8=a.int8, threads=a.threads, variant=a.variant)
    sents = sentences(a.n, a.src)
    same, t_pt, t_ox, hyp_pt, hyp_ox = 0, [], [], [], []
    for s in sents:
        b = ip.preprocess_batch([s], src_lang=sl, tgt_lang=tl)
        enc = tok(b, truncation=True, padding="longest", return_tensors="pt")
        limit = min(config.NMT_MAX_TOKENS, config.NMT_LIMIT_FACTOR * enc["input_ids"].shape[1] + config.NMT_LIMIT_MARGIN)
        t0 = time.perf_counter()
        with torch.no_grad():
            ref = mdl.generate(**enc, num_beams=1, max_new_tokens=limit,
                               no_repeat_ngram_size=config.NMT_NO_REPEAT_NGRAM)[0].tolist()
        t_pt.append((time.perf_counter() - t0) * 1000)
        dec = tok.batch_decode([ref], skip_special_tokens=True, clean_up_tokenization_spaces=True)
        hyp_pt.append(ip.postprocess_batch(dec, lang=tl)[0])
        t0 = time.perf_counter()
        out, seq = eng.translate(s, sl, tl)
        t_ox.append((time.perf_counter() - t0) * 1000)
        hyp_ox.append(out)
        same += ref == seq
    chrf = sacrebleu.corpus_chrf(hyp_ox, [hyp_pt], word_order=2).score
    kind = a.variant or ("int8" if a.int8 else "fp32")
    lines = [f"# Golden test: ONNX {kind} vs PyTorch, IndicTrans2 indic-indic-dist-320M", "",
             (f"- {len(sents)} Hindi sentences (lesson lines, team lessons, FLEURS references, then IN22-Conv); "
              if a.src == "hi" else f"- {len(sents)} Santali sentences (IN22-Conv, in order); ") + f"{sl} -> {tl};",
             f"  greedy, no-repeat {config.NMT_NO_REPEAT_NGRAM}-gram, the app's length cap. {a.threads} threads each. Laptop, offline.",
             "", "| Measure | Result |", "|---|---|",
             f"| Identical token IDs | {same} of {len(sents)} ({100 * same / len(sents):.1f}%) |",
             f"| chrF++ of ONNX output vs PyTorch output | {chrf:.1f} |",
             f"| Median time per sentence, PyTorch | {statistics.median(t_pt):.0f} ms |",
             f"| Median time per sentence, ONNX {kind} | {statistics.median(t_ox):.0f} ms |"]
    tag = "" if (a.threads == 4 and a.src == "hi" and len(sents) <= 176) else f"_t{a.threads}_{a.src}{len(sents)}"
    out_md = ROOT / "bench" / "results" / f"golden_nmt_{kind}{tag}.md"
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
