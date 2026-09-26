"""C2: ten printable test pages of team-written Hindi, with their exact text, for the OCR check.

    python tools/make_ocr_pages.py        # -> docs/samples/ocr_pages/page_NN.pdf + page_NN.txt + README.md

The text is the team's own (content/team_lessons.json lines and content/orf_passages.json
passages), not a textbook. Print the PDFs, photograph each page with a phone, and
put the photos in data/ocr_photos/page_NN.jpg; bench/ocr_eval.py scores them.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "samples" / "ocr_pages"


def pages():
    lessons = json.loads((ROOT / "content" / "team_lessons.json").read_text(encoding="utf-8"))["lessons"]
    passages = json.loads((ROOT / "content" / "orf_passages.json").read_text(encoding="utf-8"))["passages"]
    out = [(L["title"], [x["hindi"] for x in L["lines"]]) for L in lessons[:7]]
    for p in passages:
        sents = [s.strip() + "।" for s in p["text"].split("।") if s.strip()]
        out.append((p["title"], sents))
    return out[:10]


def main():
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    from worksheet import P, ps
    OUT.mkdir(parents=True, exist_ok=True)
    H = ps("OH", 20, True)
    B = ps("OB", 16, False, leading=1.6)
    for i, (title, lines) in enumerate(pages(), 1):
        doc = SimpleDocTemplate(str(OUT / f"page_{i:02d}.pdf"), pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                                topMargin=2.2 * cm, bottomMargin=2.2 * cm)
        doc.build([P(title, H), Spacer(1, 0.4 * cm)] + [P(l, B) for l in lines])
        (OUT / f"page_{i:02d}.txt").write_text("\n".join([title] + lines) + "\n", encoding="utf-8", newline="\n")
    (OUT / "README.md").write_text("""# OCR test pages (C2)

Ten pages of the team's own Hindi (lessons in `content/team_lessons.json`, passages in
`content/orf_passages.json`); `page_NN.txt` is the exact text of `page_NN.pdf`.

To test photo import:
1. Print the ten PDFs (A4, black and white is fine).
2. Photograph each page with a phone: the whole page in the frame, in daylight or a lit room,
   held roughly straight (no need to be perfect: that is what is being tested).
3. Save the photos as `data/ocr_photos/page_01.jpg` … `page_10.jpg` on the laptop (not in git).
4. Run `python bench/ocr_eval.py`: character error rate per page, in `bench/results/ocr_eval.md`.
""", encoding="utf-8", newline="\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
