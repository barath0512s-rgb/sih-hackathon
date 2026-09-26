"""A2: worksheet v2 and cut-out flashcards, for every lesson (no models needed)."""

import datetime
import io
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

pymupdf = pytest.importorskip("pymupdf")

from lesson_engine import get_all_lessons, get_lesson  # noqa: E402
import worksheet_v2 as w  # noqa: E402

SAT = "ᱥᱟᱱᱛᱟᱲᱤ ᱟᱲᱟᱝ"          # stand-in Santali: the generator only lays text out


def _cards(lesson):
    return [{"hi": c["hi"], "emoji": c.get("emoji", ""), "n": c.get("n"), "sat": SAT,
             "review_status": "pending_native_review"} for c in lesson.get("flashcards", [])]


def _text(buf):
    d = pymupdf.open(stream=buf.getvalue(), filetype="pdf")
    return d, "".join(p.get_text() for p in d)


@pytest.mark.parametrize("meta", get_all_lessons(), ids=lambda m: f"{m['grade']}_{m['topic']}")
def test_every_lesson_gets_a_worksheet_with_its_goal_and_an_answer_key(meta):
    lesson = get_lesson(meta["grade"], meta["topic"])
    buf = io.BytesIO()
    key = w.build(lesson, meta["grade"], meta["topic"], _cards(lesson), lambda hi: SAT, buf,
                  date=datetime.date(2026, 9, 26))
    d, text = _text(buf)
    assert d.page_count >= 2                                           # student pages + answer key
    assert any(0x1C50 <= ord(c) <= 0x1C7F for c in text)               # Ol Chiki is real text
    for lid in lesson.get("lakshya_ids") or []:
        assert lid in text
    assert "26.09.2026" in text and "OpenMoji" in text
    assert w.H["key"][0] in d[-1].get_text()                            # the last page is the key
    assert key, "no exercise could be made"


def test_numbers_are_shown_in_ol_chiki_devanagari_and_western_digits():
    assert w.numerals(7) == "᱗ / ७ / 7"
    assert w.numerals(12) == "᱑᱒ / १२ / 12"


def test_a_number_lesson_has_counting_circling_and_tracing():
    lesson = get_lesson("2", "addition")
    key = w.build(lesson, "2", "addition", _cards(lesson), lambda hi: SAT, io.BytesIO())
    names = [k[1] for k in key]
    assert w.both("count") in names and w.both("circle") in names and w.both("trace") in names
    # the addition cards' answers are the sums: "दो और एक तीन" -> 3
    count = next(k for k in key if k[1] == w.both("count"))[2]
    assert all(" / " in a for a in count)


def test_match_needs_different_pictures():
    lesson = get_lesson("1", "counting_1_10")                          # every card is an apple
    key = w.build(lesson, "1", "counting_1_10", _cards(lesson), lambda hi: SAT, io.BytesIO())
    assert w.both("match") not in [k[1] for k in key]
    lesson = get_lesson("2", "reading_words")
    key = w.build(lesson, "2", "reading_words", _cards(lesson), lambda hi: SAT, io.BytesIO())
    assert w.both("match") in [k[1] for k in key]


def test_flashcards_have_fronts_and_mirrored_backs_and_mark_unreviewed_words():
    lesson = get_lesson("2", "reading_words")
    cards = _cards(lesson)
    cards[0]["review_status"] = "native_reviewed"
    cards[0]["sat"] = "ᱟᱭᱳ"
    buf = io.BytesIO()
    w.build_flashcards({"title": lesson["title"], "grade": "2", "topic": "reading_words",
                        "lakshya_ids": lesson["lakshya_ids"], "cards": cards}, buf)
    d, text = _text(buf)
    assert d.page_count == 2 * ((len(cards) + 7) // 8)
    front, back = d[0].get_text(), d[1].get_text()
    assert "ᱟᱭᱳ" in front and w.H["pending"][0] in front
    assert front.count(w.H["pending"][0]) == min(8, len(cards)) - 1     # the reviewed word has no mark
    # backs are mirrored for double-sided printing: card 2 sits left of card 1
    x = lambda page, s: next(ch["bbox"][0] for b in page.get_text("rawdict")["blocks"] for l in b.get("lines", [])
                             for sp in l["spans"] for ch in sp["chars"] if ch["c"] == s[0]
                             and "".join(c["c"] for c in sp["chars"]).startswith(s[:2]))
    assert x(d[1], cards[1]["hi"]) < x(d[1], cards[0]["hi"])
