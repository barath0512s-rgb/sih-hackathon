"""C1: how well does the reading-fluency aligner mark words? Public adult Hindi read speech.

    python bench/orf_validate.py

Data: the 80 public FLEURS Hindi clips (read speech; the speaker read the reference
sentence) and the app's saved transcripts of them (bench/results/asr_decoding_public.jsonl,
Hindi CTC without trimming = the app's setting). No new recognition is run.
  1. Passage = the reference. The reading was correct, so every word "correct" is
     right: false-error rate = words wrongly marked error/omitted.
  2. Misreadings simulated on the passage side: in each passage, 10 % of the words
     (at least one) are replaced by a word from another sentence, so the speaker
     "misread" exactly those. Error detection: precision / recall.
Both with the near-spelling rule (orf.NEAR) and with exact matching.
Adults reading well-formed sentences: children's reading is NOT MEASURED.
Writes bench/results/orf_validation.md / .json.
"""

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import orf  # noqa: E402

OUT = ROOT / "bench" / "results" / "orf_validation"


def main():
    rows = [json.loads(l) for l in (ROOT / "bench/results/asr_decoding_public.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r["lang"] == "hi" and r["decoding"] == "ctc" and not r["trim"]]
    rnd = random.Random(20260926)
    vocab = sorted({w for r in rows for w in r["reference_raw"].split()})
    res = {}
    for near_name, near in (("near spelling", orf.NEAR), ("exact", None)):
        fe = n = 0
        tp = fp = fn = 0
        for r in rows:
            ref, hyp = r["reference_raw"], r["hypothesis_raw"]
            s = orf.score(ref, hyp, 10.0, near=near)
            fe += sum(w["status"] in ("error", "omitted") for w in s["words"])
            n += len(s["words"])
            words = ref.split()
            k = max(1, len(words) // 10)
            idx = set(rnd.sample(range(len(words)), k))
            passage = [rnd.choice([v for v in vocab if v != w]) if i in idx else w for i, w in enumerate(words)]
            s2 = orf.score(" ".join(passage), hyp, 10.0, near=near)
            marked = {i for i, w in enumerate(s2["words"]) if w["status"] in ("error", "omitted")}
            tp += len(marked & idx); fp += len(marked - idx); fn += len(idx - marked)
        res[near_name] = {"clips": len(rows), "words": n, "false_errors": fe, "false_error_rate": round(fe / n, 4),
                          "misread_precision": round(tp / (tp + fp), 3), "misread_recall": round(tp / (tp + fn), 3),
                          "misread_n": tp + fn}
    L = ["# Oral reading fluency (C1): alignment check on public adult read speech", "",
         f"- FLEURS Hindi, {res['exact']['clips']} clips, the app's saved Hindi transcripts (CTC, no trimming); "
         "no new recognition. Adults reading; **children's reading: NOT MEASURED**.",
         "- (1) Passage = the sentence read: every word should be correct. (2) 10 % of each passage's words replaced "
         "(seeded), so exactly those were 'misread': detection precision / recall.", "",
         "| Matching | Words wrongly marked (1) | Misreadings found: precision / recall (2) |", "|---|---|---|"]
    for k, r in res.items():
        L.append(f"| {k} | {r['false_errors']} of {r['words']} ({r['false_error_rate'] * 100:.1f} %) | "
                 f"{r['misread_precision']:.3f} / {r['misread_recall']:.3f} (n = {r['misread_n']}) |")
    L += ["", f"- The app uses near-spelling matching (character similarity ≥ {orf.NEAR}): recognisers spell some "
          "correctly read words differently, which exact matching counts as errors."]
    OUT.with_suffix(".md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    OUT.with_suffix(".json").write_text(json.dumps(res, indent=1), encoding="utf-8", newline="\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
