"""A3: round-trip check. Does back-translation find the worst Hindi -> Santali translations?

    python eval/roundtrip_flag.py            # back-translates IN22-Conv (resumable), tunes, writes results
    python eval/roundtrip_flag.py --score-only

For every IN22-Conv sentence (1503, CC BY 4.0; never training data):
  forward   the app's Hindi -> Santali (data/eval/hyp_in22-conv_hin_Deva-sat_Olck.txt,
            onnx-fp32, written by eval/eval_benchmarks.py)
  back      that Santali translated back to Hindi by the same model
            (data/eval/hyp_in22-conv_roundtrip_back.txt; git-ignored like the other hyps)
  quality   sentence chrF of forward against the reference Santali
  roundtrip sentence chrF of back against the Hindi source
(sacrebleu sentence_chrf, chrF defaults: character 6-grams, no word n-grams.)
"Worst" = quality below the 25th percentile of the tune half. Halves: a random
split of the sentence indices with a fixed seed (SEED), made before any scoring. The flag is roundtrip < threshold; the threshold maximises F1
for "worst" on the tune half; precision and recall are reported on the test half.
Writes eval/results/roundtrip_flag.md and .json.
"""

import argparse
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

HYPS = ROOT / "data" / "eval"
FWD = HYPS / "hyp_in22-conv_hin_Deva-sat_Olck.txt"
BACK = HYPS / "hyp_in22-conv_roundtrip_back.txt"
PARQUET = ROOT / "data/public/ai4bharat__IN22-Conv/data/train-00000-of-00001.parquet"
OUT = ROOT / "eval" / "results" / "roundtrip_flag"
SEED = 20260927


def pairs():
    import pandas as pd
    df = pd.read_parquet(PARQUET)
    return list(zip(df["hin_Deva"].tolist(), df["sat_Olck"].tolist()))


def half(s):
    return "test" if int(hashlib.sha1(s.encode("utf-8")).hexdigest(), 16) % 2 else "tune"


def back_translate(fwd):
    import pipeline
    pl = pipeline.VaaniSetuPipeline()
    done = BACK.read_text(encoding="utf-8").split("\n") if BACK.exists() else []
    done = [d for d in done][: len(fwd)]
    if done and done[-1] == "":
        done = done[:-1]
    t0 = time.time()
    with open(BACK, "a", encoding="utf-8", newline="\n") as f:
        for i in range(len(done), len(fwd)):
            out, _ = pl._nmt(fwd[i], "sat_Olck", "hin_Deva")
            f.write(out.replace("\n", " ") + "\n")
            f.flush()
            if i % 100 == 0:
                print(i, f"{time.time() - t0:.0f} s", flush=True)
    return pl.nmt_backend


def pr(rows, t):
    flagged = [r for r in rows if r["rt"] < t]
    bad = [r for r in rows if r["bad"]]
    tp = sum(r["bad"] for r in flagged)
    p = tp / len(flagged) if flagged else 1.0
    rec = tp / len(bad) if bad else 0.0
    return {"threshold": t, "precision": p, "recall": rec, "f1": 2 * p * rec / (p + rec) if p + rec else 0.0,
            "flagged": len(flagged), "worst": len(bad), "caught": tp, "n": len(rows)}


def main():
    from sacrebleu.metrics import CHRF
    ap = argparse.ArgumentParser()
    ap.add_argument("--score-only", action="store_true")
    a = ap.parse_args()
    P = pairs()
    fwd = FWD.read_text(encoding="utf-8").split("\n")[: len(P)]
    engine = "onnx-fp32 (config.NMT_BACKEND at the time of the forward run; see eval/results/benchmarks.md)"
    if not a.score_only:
        engine = back_translate(fwd)
    back = BACK.read_text(encoding="utf-8").split("\n")[: len(P)]
    assert len(back) == len(P), f"{len(back)} back-translations for {len(P)} sentences: run without --score-only"
    chrf = CHRF()
    import random
    order = list(range(len(P)))
    random.Random(SEED).shuffle(order)
    tune_idx = set(order[: len(P) // 2])
    rows = [{"i": i, "hi": hi, "half": "tune" if i in tune_idx else "test", "q": chrf.sentence_score(f, [ref]).score,
             "rt": chrf.sentence_score(b, [hi]).score} for i, ((hi, ref), f, b) in enumerate(zip(P, fwd, back))]
    tune = [r for r in rows if r["half"] == "tune"]
    test = [r for r in rows if r["half"] == "test"]
    cut = statistics.quantiles([r["q"] for r in tune], n=4)[0]           # 25th percentile of the tune half
    for r in rows:
        r["bad"] = r["q"] < cut
    grid = [round(x * 0.5, 1) for x in range(20, 161)]                   # 10.0 .. 80.0
    best = max((pr(tune, t) for t in grid), key=lambda s: (s["f1"], -s["threshold"]))
    thr = best["threshold"]
    res_test = pr(test, thr)

    def spearman(x, y):
        rx = {v: i for i, v in enumerate(sorted(range(len(x)), key=lambda k: x[k]))}
        ry = {v: i for i, v in enumerate(sorted(range(len(y)), key=lambda k: y[k]))}
        n = len(x)
        return 1 - 6 * sum((rx[i] - ry[i]) ** 2 for i in range(n)) / (n * (n * n - 1))
    rho = spearman([r["rt"] for r in test], [r["q"] for r in test])
    curve = [pr(test, t) for t in (20.0, 30.0, 40.0, 50.0, 60.0)]
    L = ["# Round-trip check (A3): does back-translation find the worst translations?", "",
         "- IN22-Conv, 1503 Hindi–Santali pairs (CC BY 4.0), never used for training. Forward: the app's model "
         f"(`hyp_in22-conv_hin_Deva-sat_Olck.txt`); back-translation by the same model ({engine}).",
         "- Sentence chrF (sacrebleu defaults). **Worst** = forward chrF against the reference below the tune "
         f"half's 25th percentile ({cut:.1f}). Flag = round-trip chrF against the Hindi source below the threshold.",
         f"- Halves: a random split of the 1503 sentences with a fixed seed ({SEED}): tune {len(tune)}, test {len(test)}. "
         "The 'worst' cut and the threshold come from the tune half only; the test half is scored once.",
         "- An earlier version split by a hash of the Hindi sentence (tune 765, test 738): threshold 34.5, test precision "
         "0.446, recall 0.558. The seeded split is the one reported.", "",
         f"**Threshold {thr:.1f}. Test half: precision {res_test['precision']:.3f}, recall {res_test['recall']:.3f}** "
         f"({res_test['caught']} of {res_test['worst']} worst translations flagged; {res_test['flagged']} of "
         f"{res_test['n']} sentences flagged). Tune half: precision {best['precision']:.3f}, recall {best['recall']:.3f}.", "",
         f"- Spearman correlation between round-trip chrF and forward chrF on the test half: {rho:.3f}.",
         "- The flag cannot see errors the model makes the same way in both directions (a wrong word translated "
         "back to the right Hindi word); it is a warning, not a quality score.", "",
         "| Threshold (test half) | Precision | Recall | Flagged |", "|---|---|---|---|"]
    L += [f"| {s['threshold']:.1f} | {s['precision']:.3f} | {s['recall']:.3f} | {s['flagged']} |" for s in curve]
    OUT.with_suffix(".md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    OUT.with_suffix(".json").write_text(json.dumps({"threshold": thr, "worst_cut": round(cut, 2), "tune": best,
                                                    "test": res_test, "spearman_test": round(rho, 3), "curve": curve},
                                                   indent=1), encoding="utf-8", newline="\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
