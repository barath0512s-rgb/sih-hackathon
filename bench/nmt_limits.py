"""Does sizing max_new_tokens to the input speed up NMT, and does it change output?

    python bench/nmt_limits.py

Translates every reference line in the benchmark manifest twice: with the fixed
limit (config.NMT_MAX_TOKENS) and with a limit sized to the input. A smaller
limit only saves time when the model would otherwise run on, and it must not
cut real translations short, so the report counts changed outputs.
Writes bench/results/nmt_limits.md.
"""

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402

FACTOR, MARGIN = 3, 10          # sized limit = min(fixed, FACTOR * input tokens + MARGIN)


def main():
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    from IndicTransToolkit.processor import IndicProcessor
    tok = AutoTokenizer.from_pretrained(str(config.NMT_DIR), trust_remote_code=True)
    mdl = AutoModelForSeq2SeqLM.from_pretrained(str(config.NMT_DIR), trust_remote_code=True).eval()
    ip = IndicProcessor(inference=True)
    manifest = json.loads((ROOT / "bench/clips/synthetic/manifest.json").read_text(encoding="utf-8"))

    def run(text, src, tgt, limit):
        b = ip.preprocess_batch([text], src_lang=src, tgt_lang=tgt)
        enc = tok(b, truncation=True, padding="longest", return_tensors="pt")
        n_in = enc["input_ids"].shape[1]
        lim = limit(n_in)
        t0 = time.perf_counter()
        with torch.no_grad():
            out = mdl.generate(**enc, num_beams=1, max_new_tokens=lim,
                               no_repeat_ngram_size=config.NMT_NO_REPEAT_NGRAM)
        ms = (time.perf_counter() - t0) * 1000
        n_out = out.shape[1]
        txt = ip.postprocess_batch(tok.batch_decode(out, skip_special_tokens=True), lang=tgt)[0]
        return txt, ms, n_in, n_out, lim

    fixed = lambda n: config.NMT_MAX_TOKENS
    sized = lambda n: min(config.NMT_MAX_TOKENS, FACTOR * n + MARGIN)
    run("आज हम जोड़ना सीखेंगे।", "hin_Deva", "sat_Olck", fixed)        # warm up

    rows = []
    for c in manifest:
        src, tgt = ("hin_Deva", "sat_Olck") if c["lang"] == "hi" else ("sat_Olck", "hin_Deva")
        a = run(c["reference"], src, tgt, fixed)
        b = run(c["reference"], src, tgt, sized)
        rows.append({"lang": c["lang"], "fixed_ms": a[1], "sized_ms": b[1], "in": a[2],
                     "out_fixed": a[3], "limit_sized": b[4], "hit_fixed_limit": a[3] - 1 >= config.NMT_MAX_TOKENS,
                     "changed": a[0] != b[0]})

    changed = sum(r["changed"] for r in rows)
    hit = sum(r["hit_fixed_limit"] for r in rows)
    lines = ["# NMT decode limit", "",
             f"{len(rows)} reference lines; greedy; fixed limit {config.NMT_MAX_TOKENS} vs "
             f"sized limit min({config.NMT_MAX_TOKENS}, {FACTOR} x input tokens + {MARGIN}).", "",
             "| Language in | Fixed median ms | Sized median ms | Longest output (tokens) |",
             "|---|---|---|---|"]
    for lang in ("hi", "sat"):
        d = [r for r in rows if r["lang"] == lang]
        lines.append(f"| {lang} | {statistics.median(r['fixed_ms'] for r in d):.0f} | "
                     f"{statistics.median(r['sized_ms'] for r in d):.0f} | {max(r['out_fixed'] for r in d)} |")
    lines += ["", f"Outputs that reached the fixed limit (runaway generation): {hit} of {len(rows)}.",
              f"Outputs changed by the sized limit: {changed} of {len(rows)}."]
    (ROOT / "bench/results/nmt_limits.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
