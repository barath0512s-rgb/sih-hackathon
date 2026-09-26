"""C2: character accuracy of photo import (ocr.py) on the team's ten test pages.

    python bench/ocr_eval.py

For each page in docs/samples/ocr_pages/ (page_NN.txt = the printed text):
  photos    data/ocr_photos/page_NN.jpg (or .jpeg / .png), taken by the team with a phone
            (the result that counts);
  rendered  the PDF rendered to a 200 dpi image (a clean upper bound; not a photo).
CER = character error rate against the page text, after NFC and collapsing whitespace
(line breaks count as spaces), with jiwer. Also the share of lines read exactly.
Writes bench/results/ocr_eval.md / .json.
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import ocr  # noqa: E402

PAGES = ROOT / "docs" / "samples" / "ocr_pages"
PHOTOS = ROOT / "data" / "ocr_photos"
OUT = ROOT / "bench" / "results" / "ocr_eval"


def norm(t):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", t)).strip()


def score(truth, got):
    import jiwer
    tl = [norm(l) for l in truth.splitlines() if norm(l)]
    gl = {norm(l) for l in got.splitlines() if norm(l)}
    return {"cer": round(jiwer.cer(norm(truth), norm(got)), 4), "lines_exact": sum(l in gl for l in tl), "lines": len(tl)}


def main():
    import pymupdf
    rows = []
    for txt in sorted(PAGES.glob("page_*.txt")):
        truth = txt.read_text(encoding="utf-8")
        pdf = txt.with_suffix(".pdf")
        png = pymupdf.open(str(pdf))[0].get_pixmap(dpi=200).tobytes("png")
        r = {"page": txt.stem, "rendered": score(truth, ocr.recognise(png))}
        photo = next((p for ext in (".jpg", ".jpeg", ".png", ".JPG") for p in [PHOTOS / (txt.stem + ext)] if p.exists()), None)
        if photo:
            r["photo"] = score(truth, ocr.recognise(photo.read_bytes()))
        rows.append(r)
        print(r, flush=True)
    import statistics as st

    def summ(kind):
        R = [r[kind] for r in rows if kind in r]
        if not R:
            return None
        return {"pages": len(R), "cer_mean": round(st.mean(x["cer"] for x in R), 4),
                "cer_median": round(st.median(x["cer"] for x in R), 4),
                "lines_exact": sum(x["lines_exact"] for x in R), "lines": sum(x["lines"] for x in R)}
    res = {"engine": "Tesseract, hin, psm 4", "rendered": summ("rendered"),
           "photo": summ("photo"), "rows": rows}
    L = ["# Photo import (C2): character accuracy on the team's ten test pages", "",
         "- Pages: `docs/samples/ocr_pages/` (the team's own Hindi; printed text in `page_NN.txt`). OCR: Tesseract with "
         "`hin.traineddata` on the laptop hub (`ocr.py`). CER after NFC and collapsing whitespace.", ""]
    for kind, name in (("photo", "**Phone photos of the printed pages**"), ("rendered", "Rendered PDF images (clean upper bound, not photos)")):
        s = res[kind]
        if s:
            L.append(f"- {name}: {s['pages']} pages, **CER mean {s['cer_mean'] * 100:.1f} %**, median {s['cer_median'] * 100:.1f} %; "
                     f"lines read exactly: {s['lines_exact']} of {s['lines']}.")
        else:
            L.append(f"- {name}: **NOT MEASURED** (no photos in data/ocr_photos/ yet).")
    L += ["", "| Page | Photo CER | Rendered CER |", "|---|---|---|"]
    for r in rows:
        L.append(f"| {r['page']} | {r['photo']['cer'] * 100:.1f} % |" if "photo" in r else f"| {r['page']} | — |")
        L[-1] += f" {r['rendered']['cer'] * 100:.1f} % |"
    OUT.with_suffix(".md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    OUT.with_suffix(".json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
