"""Translation benchmark: chrF++ and BLEU for Hindi <-> Santali on public test sets.

    python eval/eval_benchmarks.py                       # every set you have access to
    python eval/eval_benchmarks.py --sets flores --limit 50

Test sets (all gated on Hugging Face: accept the terms on each page and log in):
  in22-gen    ai4bharat/IN22-Gen    1024 sentences, CC BY 4.0
  in22-conv   ai4bharat/IN22-Conv   1503 sentences, CC BY 4.0
  flores      facebook/flores       FLORES-200 devtest, 1012 sentences, CC BY-SA 4.0

What is measured: the translation model alone, exactly as the app runs it when
no teacher correction, glossary sentence or cache answers (pipeline._nmt: greedy,
same pre- and post-processing, plus the label clean-up the app applies to
Santali output). Metrics with sacrebleu: chrF++ (word_order=2) and BLEU (the
default 13a tokenizer; the IndicTrans2 paper tokenises Indic text differently,
so compare chrF++, not BLEU, with the paper).

Outputs:
  eval/results/benchmarks.md     scores, with the dataset revisions
  eval/results/benchmarks.json   the same, for tools/deck_numbers.py
  data/eval/hyp_<set>_<dir>.txt  the translations (git-ignored: the test sets'
                                 terms do not allow republishing them)
It also writes eval/test_set_hashes.json: SHA-256 of every normalised test
sentence, so training scripts can refuse any test sentence (eval/leakage.py).
These sets are for evaluation only; never train or tune on them.
"""

import argparse
import datetime
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "0"         # downloading the test sets; the model runs from disk

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

RESULTS = ROOT / "eval" / "results"
HYPS = ROOT / "data" / "eval"
CACHE = ROOT / "data" / "public"
HASHES = ROOT / "eval" / "test_set_hashes.json"

SETS = {
    "in22-gen": {"repo": "ai4bharat/IN22-Gen", "files": ["data/train-00000-of-00001.parquet"],
                 "license": "CC BY 4.0", "url": "https://huggingface.co/datasets/ai4bharat/IN22-Gen"},
    "in22-conv": {"repo": "ai4bharat/IN22-Conv", "files": ["data/train-00000-of-00001.parquet"],
                  "license": "CC BY 4.0", "url": "https://huggingface.co/datasets/ai4bharat/IN22-Conv"},
    "flores": {"repo": "facebook/flores",
               "files": ["data/language/hin_Deva/devtest-00000-of-00001.parquet",
                         "data/language/sat_Olck/devtest-00000-of-00001.parquet"],
               "license": "CC BY-SA 4.0", "url": "https://huggingface.co/datasets/facebook/flores"},
}
# The IndicTrans2 paper (TMLR 2023, arXiv 2305.16307v3) reports, for the
# distilled M2M model we use (IT2-Dist-M2M), chrF++ AVERAGED over all Indic
# source languages into Santali (xx-sat) and from Santali into all (sat-xx).
# Not the Hindi pair itself: a plausibility range only. docs/sources.md#indictrans2-paper
PAPER = {"flores": (26.1, 31.5), "in22-gen": (30.0, 35.8), "in22-conv": (30.4, 33.8)}


def _col(names, lang):
    for n in names:
        if n == lang or n.endswith(lang) or n.startswith(lang):
            return n
    for n in ("sentence", "text"):
        if n in names:
            return n
    raise SystemExit(f"no column for {lang} in {names}")


def load(name):
    """[(hindi, santali)] for a test set, and the dataset revision."""
    import pyarrow.parquet as pq
    from huggingface_hub import HfApi, hf_hub_download
    s = SETS[name]
    rev = HfApi().dataset_info(s["repo"]).sha
    paths = [hf_hub_download(s["repo"], f, repo_type="dataset", revision=rev,
                             local_dir=str(CACHE / s["repo"].replace("/", "__"))) for f in s["files"]]
    if len(paths) == 1:                           # IN22: one n-way parallel table
        t = pq.read_table(paths[0])
        hi, sat = _col(t.schema.names, "hin_Deva"), _col(t.schema.names, "sat_Olck")
        rows = t.to_pylist()
        pairs = [(r[hi], r[sat]) for r in rows]
    else:                                         # FLORES: one table per language, same order
        th, ts = (pq.read_table(p) for p in paths)
        ch, cs = _col(th.schema.names, "sentence"), _col(ts.schema.names, "sentence")
        rh, rs = th.to_pylist(), ts.to_pylist()
        if "id" in th.schema.names and "id" in ts.schema.names:
            by = {r["id"]: r[cs] for r in rs}
            pairs = [(r[ch], by[r["id"]]) for r in rh]
        else:
            pairs = [(a[ch], b[cs]) for a, b in zip(rh, rs)]
    return [(h.strip(), s_.strip()) for h, s_ in pairs if h and s_], rev


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sets", nargs="+", choices=sorted(SETS), default=sorted(SETS))
    ap.add_argument("--limit", type=int, help="first N sentences only (a quick check, not a result)")
    a = ap.parse_args()

    import sacrebleu
    from eval.leakage import normalise_for_hash

    data, skipped = {}, []
    for name in a.sets:
        try:
            data[name] = load(name)
        except Exception as e:
            skipped.append(f"{name}: {type(e).__name__} (accept the terms at {SETS[name]['url']})")
    for s in skipped:
        print("skipped", s)
    if not data:
        sys.exit("No test set available.")

    # The hash list covers every test sentence we can see, loaded or not by --limit.
    hashes = json.loads(HASHES.read_text(encoding="utf-8")) if HASHES.exists() else {}
    for name, (pairs, rev) in data.items():
        hashes[name] = {"revision": rev, "sha256": sorted({
            hashlib.sha256(normalise_for_hash(t).encode("utf-8")).hexdigest()
            for p in pairs for t in p})}
    HASHES.write_text(json.dumps(hashes, indent=0) + "\n", encoding="utf-8")

    os.environ["HF_HUB_OFFLINE"] = "1"            # the model must not reach the Hub
    import pipeline
    pl = pipeline.VaaniSetuPipeline()
    HYPS.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    out = {"date": datetime.date.today().isoformat(), "model": "ai4bharat/indictrans2-indic-indic-dist-320M",
           "engine": pl.nmt_backend,
           "model_revision": pipeline.config.NMT_REVISION, "decoding": f"greedy (beams={pipeline.config.NMT_NUM_BEAMS})",
           "limit": a.limit, "results": []}
    for name, (pairs, rev) in data.items():
        pairs = pairs[:a.limit] if a.limit else pairs
        for direction, (src_i, tgt_i, sl, tl) in {"hin_Deva-sat_Olck": (0, 1, "hin_Deva", "sat_Olck"),
                                                  "sat_Olck-hin_Deva": (1, 0, "sat_Olck", "hin_Deva")}.items():
            t0, hyps = time.perf_counter(), []
            for p in pairs:
                h, _ = pl._nmt(p[src_i], sl, tl)          # the app's engine
                hyps.append(pl._apply_domain_glossary(h, "sat_Olck") if tl == "sat_Olck" else h)
            secs = time.perf_counter() - t0
            refs = [p[tgt_i] for p in pairs]
            chrf = sacrebleu.corpus_chrf(hyps, [refs], word_order=2).score
            bleu = sacrebleu.corpus_bleu(hyps, [refs]).score
            (HYPS / f"hyp_{name}_{direction}.txt").write_text("\n".join(hyps) + "\n", encoding="utf-8")
            paper = PAPER[name][0 if tl == "sat_Olck" else 1]
            out["results"].append({"set": name, "dataset_revision": rev, "direction": direction,
                                   "n": len(pairs), "chrf++": round(chrf, 1), "bleu": round(bleu, 1),
                                   "seconds": round(secs, 1), "paper_avg_chrf++": paper})
            print(f"{name:10} {direction}  n={len(pairs)}  chrF++ {chrf:.1f}  BLEU {bleu:.1f}  "
                  f"(paper, all-source average: {paper})  {secs:.0f} s")

    tag = "_limit" if a.limit else ""
    (RESULTS / f"benchmarks{tag}.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    lines = ["# Translation benchmark: Hindi <-> Santali", "",
             f"- Date: {out['date']}; model {out['model']} @ {out['model_revision'][:10]}, {out['decoding']};",
             "  the model alone (no teacher corrections, glossary or cache). Laptop, offline.",
             "- chrF++ = sacrebleu corpus_chrf(word_order=2); BLEU = sacrebleu corpus_bleu (13a).",
             "- **Paper column:** IndicTrans2 paper (arXiv 2305.16307v3, Tables 19-21), IT2-Dist-M2M, chrF++",
             "  averaged over ALL Indic languages into Santali (for hin→sat) or from Santali (for sat→hin).",
             "  It is not the Hindi pair itself: a plausibility range, not a like-for-like comparison.",
             "- These test sets are for evaluation only. eval/test_set_hashes.json lets training scripts",
             "  refuse any of their sentences (eval/leakage.py).", ""]
    if a.limit:
        lines += [f"> **Quick check on the first {a.limit} sentences only. Not a result.**", ""]
    if skipped:
        lines += ["Not run (no access yet): " + "; ".join(skipped), ""]
    lines += ["| Test set | Direction | n | chrF++ | BLEU | Paper chrF++ (all-source avg) | Time |",
              "|---|---|---|---|---|---|---|"]
    for r in out["results"]:
        lines.append(f"| {r['set']} ({SETS[r['set']]['license']}) | {r['direction']} | {r['n']} | "
                     f"{r['chrf++']} | {r['bleu']} | {r['paper_avg_chrf++']} | {r['seconds']:.0f} s |")
    (RESULTS / f"benchmarks{tag}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
