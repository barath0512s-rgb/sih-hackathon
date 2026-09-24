"""Work package 5: every lesson is tagged with real NIPUN Lakshya goals.

No models needed.
"""

import re

from lesson_engine import NIPUN_LESSONS, get_all_lessons
from nipun import lakshya


def all_lessons():
    for gk, topics in NIPUN_LESSONS.items():
        for tk, lesson in topics.items():
            yield f"{gk}/{tk}", lesson


def test_every_lesson_has_a_valid_lakshya():
    for name, lesson in all_lessons():
        ids = lesson.get("lakshya_ids")
        assert ids, f"{name} has no Lakshya ID"
        for lid in ids:
            assert lakshya.get(lid), f"{name}: unknown Lakshya ID {lid}"
            # A lesson's domain matches the goals it claims.
            assert lakshya.get(lid)["domain"] == lesson["domain"], (name, lid)


def test_every_lesson_has_a_domain_mapping_and_review_status():
    for name, lesson in all_lessons():
        assert lesson["domain"] in ("literacy", "numeracy"), name
        assert lesson["mapping"], name
        assert lesson["review_status"], name


def test_ids_follow_the_documented_scheme():
    for lid, g in lakshya.LAKSHYAS.items():
        m = re.fullmatch(r"NIPUN-(BV|G[123])-(LIT|NUM)-\d", lid)
        assert m, lid
        assert {"LIT": "literacy", "NUM": "numeracy"}[m.group(2)] == g["domain"]
        stage = {"BV": "Balvatika"}.get(m.group(1), "Grade " + m.group(1)[1:])
        assert g["stage"] == stage


def test_goal_text_is_the_ministry_wording():
    # Spot checks against page 11 of the 2021 guidelines, verbatim.
    assert lakshya.get("NIPUN-G1-NUM-2")["text"] == "Perform simple addition and subtraction"
    assert lakshya.get("NIPUN-G2-NUM-2")["text"] == "Subtract numbers up to 99"
    assert lakshya.get("NIPUN-G2-LIT-2")["text"] == "45-60 words per minute"
    assert lakshya.get("NIPUN-G3-LIT-2")["text"] == "at least 60 words per minute"
    assert "p. 11" in lakshya.SOURCE


def test_lesson_list_carries_the_tags():
    for item in get_all_lessons():
        assert item["lakshya_ids"] and len(item["lakshya"]) == len(item["lakshya_ids"])
        assert item["lakshya"][0].startswith(item["lakshya_ids"][0])


def test_every_lesson_has_flashcards_and_the_frontend_has_none_of_its_own():
    from pathlib import Path
    for name, lesson in all_lessons():
        assert lesson.get("flashcards"), name
        for c in lesson["flashcards"]:
            assert c["hi"] and c["emoji"], name
    html = (Path(__file__).parent.parent / "frontend.html").read_text(encoding="utf-8")
    assert "const DECKS" not in html and "/flashcards" in html


def test_worksheet_prints_the_tag(tmp_path):
    import fitz     # pymupdf, in requirements-dev.txt
    from worksheet import generate_worksheet
    out = tmp_path / "w.pdf"
    generate_worksheet("आज", "ᱛᱮᱦᱮᱸᱡ", "2", "Simple Addition", out=str(out),
                       lakshya_ids=["NIPUN-G1-NUM-2"])
    with fitz.open(str(out)) as doc:
        text = " ".join(p.get_text() for p in doc).replace("\n", " ")
    assert "NIPUN-G1-NUM-2" in text
    assert "Perform simple addition and subtraction" in text
