"""Write tests/data/orf_vectors.json from orf.py (the reference for Orf.kt, C1).

    python tools/android/make_orf_vectors.py
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "tests" / "data" / "orf_vectors.json"


def build():
    import orf
    passages = json.loads((ROOT / "content" / "orf_passages.json").read_text(encoding="utf-8"))["passages"]
    rnd = random.Random(7)
    cases = []
    for p in passages:
        w = p["text"].split()
        readings = [p["text"], " ".join(w[: len(w) // 2]), " ".join(x for i, x in enumerate(w) if i % 5 != 2),
                    " ".join(rnd.choice(w) if i % 7 == 3 else x for i, x in enumerate(w)) + " और", ""]
        for r in readings:
            for secs in (30.0, 45.5):
                s = orf.score(p["text"], r, secs)
                cases.append({"passage": p["text"], "spoken": r, "seconds": secs, "grade": p["grade"],
                              "statuses": [x["status"] for x in s["words"]], "correct": s["correct"], "errors": s["errors"],
                              "attempted": s["attempted"], "wcpm": s["wcpm"], "extra": s["extra"],
                              "nipun": orf.nipun_band(p["grade"], s["wcpm"])})
    return json.dumps({"note": "orf.py reference for Orf.kt", "cases": cases}, ensure_ascii=False, indent=0) + "\n"


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8", newline="\n")
    print("wrote", OUT.relative_to(ROOT))
