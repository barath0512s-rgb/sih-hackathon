"""Worksheet v2 and cut-out flashcards (A2): bilingual student exercises with pictures.

    python worksheet_v2.py --grade 2 --topic addition      # writes docs/samples/…

One PDF per lesson:
  student pages   header (lesson title, grade, NIPUN Lakshya IDs, date, name line), then
                  the exercises the lesson's content allows:
                    1 count and write      pictures of a card (n copies, or the card's
                                           "🥭🥭 ➕ 🥭" sum) and a box for the number
                    2 match picture to word (pictures ↔ Santali / Hindi words, shuffled)
                    3 fill in the blank     a card's phrase with its last word left out
                    4 circle the right answer  a question of the lesson with a number
                                           answer; three numbers in Ol Chiki,
                                           Devanagari and Western digits
                    5 trace the numeral     1-10 (or the lesson's numbers) in light grey
                                           in Ol Chiki and Devanagari, then boxes to copy
  teacher page    the answer key.
A flashcard PDF per lesson: fronts (picture + Santali) and backs (Hindi), 2 × 4 cards
per A4, backs mirrored for double-sided printing (flip on the long edge); a word
without native review carries a "review pending" mark.

Pictures: OpenMoji PNGs (static/openmoji/, CC BY-SA 4.0; attribution on every page).
Colour emoji fonts do not render in reportlab, so pictures are images.
The generator is pure layout: all Santali comes from the caller (the content pack's
translations), never from a model here. The same PDFs are pre-rendered into the
content pack, and the tablet serves them from there (it does not draw PDFs itself).
"""

import argparse
import datetime
import random
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

import config
from nipun import lakshya
from worksheet import P, ps, ps_sat, _SCRIPT_FONTS

ROOT = Path(__file__).resolve().parent
EMOJI_DIR = ROOT / "static" / "openmoji"
ATTRIBUTION = "Pictures: OpenMoji (openmoji.org), CC BY-SA 4.0."

OLCK = "᱐᱑᱒᱓᱔᱕᱖᱗᱘᱙"
DEVA = "०१२३४५६७८९"

# Headings: Hindi, then Santali. The Santali headings are pending native review
# (docs/native_review.md); where there is none yet, the Hindi stands alone.
H = {
    "title":   ("अभ्यास पत्रक", "ᱠᱟᱹᱢᱤ ᱠᱟᱜᱚᱡ"),
    "name":    ("नाम", ""),
    "date":    ("तारीख", ""),
    "grade":   ("कक्षा", "ᱠᱞᱟᱥ"),
    "goal":    ("NIPUN लक्ष्य", "NIPUN ᱞᱚᱠᱷᱭᱚ"),
    "count":   ("गिनो और लिखो", ""),
    "match":   ("चित्र को शब्द से मिलाओ", ""),
    "fill":    ("खाली जगह भरो", ""),
    "circle":  ("सही उत्तर पर गोला लगाओ", ""),
    "trace":   ("अंक पर लिखो, फिर खुद लिखो", ""),
    "key":     ("शिक्षक के लिए: उत्तर", ""),
    "cards":   ("फ़्लैशकार्ड: काटकर इस्तेमाल करें", ""),
    "front":   ("सामने", ""),
    "back":    ("पीछे", ""),
    "pending": ("मूल वक्ता की समीक्षा बाकी", ""),
    "duplex":  ("दोनों तरफ़ छापें (लंबे किनारे से पलटें)", ""),
}


def both(k):
    hi, sat = H[k]
    return f"{hi} / {sat}" if sat else hi


def numerals(n):
    """'7' -> '᱗ / ७ / 7'."""
    s = str(n)
    return f"{''.join(OLCK[int(d)] for d in s)} / {''.join(DEVA[int(d)] for d in s)} / {s}"


def emoji_files(seq):
    """The OpenMoji file for each picture in an emoji string, in order (operators kept)."""
    out = []
    for ch in seq:
        if ch in "‍️" or ch.isspace():
            continue
        f = EMOJI_DIR / f"{ord(ch):X}.png"
        if f.is_file():
            out.append((ch, f))
    return out


def pictures(seq, size=1.1 * cm, max_n=12):
    files = emoji_files(seq)[:max_n]
    if not files:
        return Spacer(1, size)
    t = Table([[Image(str(f), size, size) for _, f in files]], colWidths=[size + 0.1 * cm] * len(files))
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1)]))
    return t


def _number_of(word):
    from curriculum import NUMBER_WORDS
    from textnorm import normalize_key
    w = normalize_key(word)
    return NUMBER_WORDS.get(word) if word in NUMBER_WORDS else next(
        (v for k, v in NUMBER_WORDS.items() if normalize_key(k) == w), None)


def _box(size=1.4 * cm):
    t = Table([[""]], colWidths=[size], rowHeights=[size])
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#555555"))]))
    return t


def build(lesson, grade, topic, cards, santali_of, out, date=None, seed=2026):
    """lesson: lesson_engine lesson dict; cards: [{hi, sat, emoji, n, review_status}];
    santali_of(hindi) -> Santali text or "" (the pack's translations). Returns the answer key."""
    date = date or datetime.date.today()
    rnd = random.Random(f"{seed}:{grade}:{topic}")
    doc = SimpleDocTemplate(out if hasattr(out, "write") else str(out), pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm,
                            topMargin=1.3 * cm, bottomMargin=1.4 * cm,
                            title=f"{config.APP_NAME} {grade} {topic}", author=config.APP_NAME)
    HD = ps("HD", 15, True, "#0D2137", TA_CENTER)
    SUB = ps("SUB", 9.5, False, "#1A5276", TA_CENTER)
    EX = ps("EX", 12, True, "#0D2137")
    BD = ps("BD", 11, False)
    SAT = ps_sat("SAT", 12)
    BIG = ps("BIG", 13, False, "#111111", TA_CENTER)
    FT = ps("FT", 7, False, "#777777", TA_CENTER)
    names = config.APP_NAME_LOCAL
    lids = lesson.get("lakshya_ids") or []
    grade_txt = "बालवाटिका / ᱵᱟᱞᱣᱟᱴᱤᱠᱟ" if str(grade) == "0" else f"{H['grade'][0]} {grade} / {H['grade'][1]} {grade}"
    title = lesson.get("title", topic)
    s = [P(f"{' / '.join(n for n in (names['hi'], names['sat']) if n)} — {both('title')}", HD),
         P(f"{title}  |  {grade_txt}  |  {date.strftime('%d.%m.%Y')}", SUB),
         P(f"{both('goal')}: " + (", ".join(lids) if lids else "—"), SUB),
         Spacer(1, 0.25 * cm),
         P(f"{both('name')}: ____________________________     {both('date')}: ______________", BD),
         Spacer(1, 0.3 * cm)]
    key = []
    n_ex = 0

    def exercise(k, body):
        nonlocal n_ex
        n_ex += 1
        s.append(KeepTogether([P(f"{n_ex}. {both(k)}", EX), Spacer(1, 0.15 * cm)] + body + [Spacer(1, 0.45 * cm)]))
        return n_ex

    # 1 count and write
    counts = []
    for c in cards:
        files = emoji_files(c.get("emoji", ""))
        if not files:
            continue
        n = c.get("n")
        seq = c["emoji"]
        if n and len(files) == 1:
            seq = files[0][0] * int(n)
        elif n is None:
            last = c["hi"].split()[-1] if c["hi"].split() else ""
            n = _number_of(last)
        if n is not None and len(emoji_files(seq)) <= 12:
            counts.append((seq, int(n)))
    rnd.shuffle(counts)
    counts = counts[:4]
    if counts:
        rows = [[pictures(seq, 1.0 * cm), _box()] for seq, _ in counts]
        t = Table(rows, colWidths=[14 * cm, 2 * cm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
        i = exercise("count", [t])
        key.append((i, both("count"), [f"({chr(97 + j)}) {numerals(n)}" for j, (_, n) in enumerate(counts)]))

    # 2 match picture to word
    single, seen = [], set()                  # one picture per card, and every picture different
    for c in cards:
        f = emoji_files(c.get("emoji", ""))
        if len(f) == 1 and c.get("sat") and f[0][0] not in seen:
            seen.add(f[0][0]); single.append(c)
    single = single[:5]
    if len(single) >= 3:
        words = list(single)
        for _ in range(50):                    # no word next to its own picture
            rnd.shuffle(words)
            if all(w is not a for w, a in zip(words, single)):
                break
        DOT_R = ps("DOTR", 11, False, "#111111", 2)          # right-aligned
        rows = [[pictures(a["emoji"], 1.3 * cm), P(f"{chr(97 + j)}) ●", BD), P("●", DOT_R),
                 P(f"{b['sat']}  ({b['hi']})", SAT)] for j, (a, b) in enumerate(zip(single, words))]
        t = Table(rows, colWidths=[2.2 * cm, 1.2 * cm, 6 * cm, 7 * cm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (2, 0), (2, -1), "RIGHT")]))
        i = exercise("match", [t])
        key.append((i, both("match"), [f"{chr(97 + j)}) {a['sat']} ({a['hi']})" for j, a in enumerate(single)]))

    # 3 fill in the blank (a card's phrase of 3+ words, last word left out)
    phrases = [c for c in cards if len(c["hi"].split()) >= 3]
    rnd.shuffle(phrases)
    phrases = phrases[:3]
    if phrases:
        rows = []
        for j, c in enumerate(phrases):
            hi_words = c["hi"].split()
            sat_words = (c.get("sat") or "").split()
            sat_line = " ".join(sat_words[:-1]) + " ________" if len(sat_words) >= 2 else ""
            rows.append([P(f"{chr(97 + j)})", BD), P(" ".join(hi_words[:-1]) + " ________", BD), P(sat_line, SAT)])
        t = Table(rows, colWidths=[0.8 * cm, 7.6 * cm, 8.4 * cm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
        i = exercise("fill", [t])
        key.append((i, both("fill"), [f"{chr(97 + j)}) {c['hi'].split()[-1]}"
                                      + (f" / {(c.get('sat') or '').split()[-1]}" if len((c.get('sat') or '').split()) >= 2 else "")
                                      for j, c in enumerate(phrases)]))

    # 4 circle the right answer (questions with a number answer)
    qs = []
    for st in lesson.get("steps", []):
        digits = (st.get("accept_answers") or {}).get("digits") or []
        if st.get("type") == "assessment_prompt" and digits and digits[0].isdigit():
            qs.append((st["hindi"], santali_of(st["hindi"]), int(digits[0])))
    if qs:
        rows, ans = [], []
        for j, (hi, sat, a) in enumerate(qs[:3]):
            opts = sorted({a, max(0, a - 1) if a > 1 else a + 2, a + 1})
            rnd.shuffle(opts)
            cells = [P(numerals(o), BIG) for o in opts]
            q = [P(f"{chr(97 + j)}) {hi}", BD)] + ([P(sat, SAT)] if sat else [])
            rows.append([q, *cells])
            ans.append(f"{chr(97 + j)}) {numerals(a)}")
        t = Table(rows, colWidths=[8.2 * cm, 2.9 * cm, 2.9 * cm, 2.9 * cm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
        i = exercise("circle", [t])
        key.append((i, both("circle"), ans))

    # 5 trace the numeral (number lessons)
    nums = sorted({n for _, n in counts} | {a for *_, a in qs} | {int(c["n"]) for c in cards if c.get("n")})
    is_number = any(l.startswith("NIPUN-") and "-NUM-" in l for l in lids)
    if is_number:
        nums = [n for n in (nums or list(range(1, 11))) if 0 <= n <= 20][:10] or list(range(1, 11))
        TR = ps("TR", 30, False, "#C8C8C8", TA_CENTER, leading=1.2)
        fo, fd = _SCRIPT_FONTS.get("olchiki"), _SCRIPT_FONTS.get("devanagari")
        rows = []
        for n in nums[:6]:
            o = "".join(OLCK[int(d)] for d in str(n)); d = "".join(DEVA[int(x)] for x in str(n))
            rows.append([Paragraph(f'<font name="{fo}">{o}</font>' if fo else o, TR),
                         Paragraph(f'<font name="{fd}">{d}</font>' if fd else d, TR), _box(1.3 * cm), _box(1.3 * cm), _box(1.3 * cm)])
        t = Table(rows, colWidths=[2.6 * cm, 2.6 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        i = exercise("trace", [t])
        key.append((i, both("trace"), [numerals(n) for n in nums[:6]]))

    s.append(Spacer(1, 0.3 * cm))
    # teacher page: the answer key
    s += [PageBreak(), P(both("key"), HD), P(f"{title}  |  {grade_txt}  |  {', '.join(lids)}", SUB), Spacer(1, 0.4 * cm)]
    for i, name, answers in key:
        s.append(P(f"{i}. {name}", EX))
        for a in answers:
            s.append(P(a, SAT))
        s.append(Spacer(1, 0.3 * cm))
    if lids:
        s.append(Spacer(1, 0.4 * cm))
        for lid in lids:
            s.append(P(f"{lid}: {lakshya.get(lid)['text']}", ps("LT", 8.5, False, "#333333")))
        s.append(P("NIPUN Bharat guidelines (Ministry of Education, 2021), p. 11.", FT))

    def footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#777777"))
        canvas.drawCentredString(A4[0] / 2, 0.8 * cm, f"{config.APP_NAME} · {grade}/{topic} · {ATTRIBUTION} "
                                                      "Santali lines: native review pending.")
        canvas.restoreState()
    doc.build(s, onFirstPage=footer, onLaterPages=footer)
    return key


def build_flashcards(deck, out, date=None):
    """deck: {title, grade, topic, lakshya_ids, cards: [{hi, sat, emoji, review_status}]}."""
    date = date or datetime.date.today()
    doc = SimpleDocTemplate(out if hasattr(out, "write") else str(out), pagesize=A4, leftMargin=1.2 * cm, rightMargin=1.2 * cm,
                            topMargin=1.2 * cm, bottomMargin=1.4 * cm, title=f"{config.APP_NAME} flashcards")
    HD = ps("FHD", 12, True, "#0D2137", TA_CENTER)
    SAT = ps_sat("FSAT", 20, False, "#111111", TA_CENTER)
    HI = ps("FHI", 22, False, "#111111", TA_CENTER, leading=1.5)
    PEND = ps("FPEND", 7.5, False, "#B03A2E", TA_CENTER)
    W, Hh = 9.3 * cm, 6.2 * cm
    cards = [c for c in deck["cards"] if c.get("sat")]
    reviewed = {"native_reviewed", "teacher_verified"}

    def front(c):
        n = max(1, len(emoji_files(c.get("emoji", ""))[:12]))
        size = min(1.6 * cm, (W - 0.8 * cm) / n - 0.1 * cm)          # fit the card's width
        cell = [pictures(c.get("emoji", ""), size, 12), Spacer(1, 0.2 * cm), P(c["sat"], SAT)]
        if c.get("review_status") not in reviewed:
            cell.append(P(both("pending"), PEND))
        return cell

    def back(c):
        return [Spacer(1, 1.2 * cm), P(c["hi"], HI)]

    def grid(items, mirror=False):
        rows = []
        for r in range(0, len(items), 2):
            pair = items[r:r + 2] + [None] * (2 - len(items[r:r + 2]))
            if mirror:
                pair = pair[::-1]
            rows.append([x if x is not None else "" for x in pair])
        t = Table(rows, colWidths=[W, W], rowHeights=[Hh] * len(rows))
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#999999")),
                               ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        return t

    s = []
    for start in range(0, len(cards), 8):
        page = cards[start:start + 8]
        s += [P(f"{deck['title']} — {both('cards')} — {both('front')}", HD), Spacer(1, 0.2 * cm),
              grid([front(c) for c in page]), PageBreak(),
              P(f"{deck['title']} — {both('back')} ({both('duplex')})", HD), Spacer(1, 0.2 * cm),
              grid([back(c) for c in page], mirror=True), PageBreak()]
    if s:
        s.pop()

    def footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#777777"))
        canvas.drawCentredString(A4[0] / 2, 0.8 * cm, f"{config.APP_NAME} · {deck['grade']}/{deck['topic']} · "
                                                      f"{', '.join(deck.get('lakshya_ids') or [])} · {ATTRIBUTION}")
        canvas.restoreState()
    doc.build(s or [P("—", HD)], onFirstPage=footer, onLaterPages=footer)


def main():
    """Samples from the newest content pack (its translations and flashcards)."""
    import glob
    import json
    import zipfile
    from lesson_engine import get_lesson
    from textnorm import normalize_key
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--grade", default="2")
    ap.add_argument("--topic", default="addition")
    ap.add_argument("--out", default=str(ROOT / "docs" / "samples"))
    a = ap.parse_args()
    z = zipfile.ZipFile(sorted(glob.glob(str(ROOT / "dist" / "packs" / "content-pack-*.zip")))[-1])
    tr = json.loads(z.read("translations.json"))["hi-to-sat"]
    decks = json.loads(z.read("api/flashcards.json"))["decks"]
    deck = next(d for d in decks if d["grade"] == a.grade and d["topic"] == a.topic)
    lesson = get_lesson(a.grade, a.topic)
    sat = lambda hi: (tr.get(normalize_key(hi)) or {}).get("text", "")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    build(lesson, a.grade, a.topic, deck["cards"], sat, out / f"worksheet_v2_{a.grade}_{a.topic}.pdf")
    build_flashcards(deck, out / f"flashcards_{a.grade}_{a.topic}.pdf")
    print("wrote", out / f"worksheet_v2_{a.grade}_{a.topic}.pdf", out / f"flashcards_{a.grade}_{a.topic}.pdf")


if __name__ == "__main__":
    main()
