"""Work package 14, the parts that need no models: reading uploads, splitting,
labelling, Lakshya suggestions, flashcard words, and checking a draft.
"""

import json

import pytest

import curriculum as c
from nipun import lakshya


def test_split_keeps_end_marks_and_drops_empty_lines():
    text = "आज हम गिनती सीखेंगे। यहाँ पाँच आम हैं!\n\nकितने आम हैं? सब मिलकर बोलो\n।।"
    assert c.split(text) == ["आज हम गिनती सीखेंगे।", "यहाँ पाँच आम हैं!",
                             "कितने आम हैं?", "सब मिलकर बोलो"]


def test_split_normalises():
    assert c.split("आम​  गिनो ।") == ["आम गिनो ।"]


@pytest.mark.parametrize("line, kind", [
    ("कितने आम हैं?", "assessment_prompt"),
    ("यह शब्द क्या है", "assessment_prompt"),               # question word, no ?
    ("मुझे जवाब बताओ।", "assessment_prompt"),
    ("अपनी उंगलियाँ दिखाओ।", "activity_instruction"),
    ("आम गिनो।", "activity_instruction"),
    ("बोर्ड की ओर देखिए।", "activity_instruction"),
    ("यह एक आम है।", "lesson_script"),
    ("आज हम जोड़ना सीखेंगे।", "lesson_script"),
])
def test_classify_rules(line, kind):
    assert c.classify(line) == kind


@pytest.mark.parametrize("grade, text, domain, ids", [
    ("0", "यह एक है। ये दो हैं। तीन गिनो।", "numeracy", ["NIPUN-BV-NUM-1"]),
    ("1", "दो और तीन जोड़ो।", "numeracy", ["NIPUN-G1-NUM-2"]),
    ("2", "नौ में से चार घटाओ।", "numeracy", ["NIPUN-G2-NUM-2"]),
    ("3", "तीन का चार से गुणा करो।", "numeracy", ["NIPUN-G3-NUM-2"]),
    ("0", "यह अक्षर क है। इसकी ध्वनि सुनो।", "literacy", ["NIPUN-BV-LIT-1"]),
    ("2", "यह कहानी पढ़ो। शब्द लिखो।", "literacy", ["NIPUN-G2-LIT-1"]),
])
def test_suggest(grade, text, domain, ids):
    s = c.suggest(grade, c.split(text))
    assert s["domain"] == domain and s["lakshya_ids"] == ids
    for lid in s["lakshya_ids"]:
        assert lakshya.get(lid)["domain"] == domain


def test_suggest_nothing_when_no_keywords():
    s = c.suggest("1", ["सुप्रभात बच्चो।"])
    assert s["domain"] is None and s["lakshya_ids"] == []


def test_flashcard_words_are_numbers_and_known_nouns():
    cards = c.flashcard_words(c.split("यह एक आम है। यहाँ दो केले हैं। 7 पत्थर। आम खाओ।"))
    assert [x["hi"] for x in cards] == ["एक", "आम", "दो", "केले", "7", "पत्थर"]
    assert cards[0]["n"] == 1 and cards[4]["n"] == 7


def test_parse_pasted_text():
    (d,) = c.parse_upload(text="आम गिनो।", grade="2", title="आम")
    assert d == {"grade": "2", "title": "आम", "text": "आम गिनो।"}


def test_parse_csv_groups_rows_into_lessons():
    csv = "grade,topic,line\n1,फल,यह आम है।\n1,फल,आम गिनो।\n2,शब्द,यह शब्द पढ़ो।\n"
    drafts = c.parse_upload(filename="x.csv", data=csv.encode("utf-8"))
    assert [(d["grade"], d["title"]) for d in drafts] == [("1", "फल"), ("2", "शब्द")]
    assert c.draft(drafts[0])["lines"][1] == {"hindi": "आम गिनो।", "type": "activity_instruction",
                                             "answer": ""}


def test_parse_json_and_txt():
    rows = [{"grade": "0", "topic": "गिनती", "line": "एक, दो, तीन।"}]
    (d,) = c.parse_upload(filename="x.json", data=json.dumps(rows, ensure_ascii=False).encode("utf-8"))
    assert d["grade"] == "0" and d["title"] == "गिनती"
    (t,) = c.parse_upload(filename="x.txt", data="आम गिनो।".encode("utf-8-sig"), grade="1")
    assert t["text"] == "आम गिनो।"


@pytest.mark.parametrize("kwargs, msg", [
    ({"text": "   "}, "no lesson text"),
    ({"filename": "x.pdf", "data": b"%PDF"}, ".txt, .csv or .json"),
    ({"filename": "x.json", "data": b"{nope"}, "could not be read"),
    ({"filename": "x.csv", "data": b"a,b\n1,2\n"}, "no rows"),
    ({"filename": "x.txt", "data": "आम".encode("utf-16")}, "UTF-8"),
])
def test_bad_uploads_say_why(kwargs, msg):
    with pytest.raises(c.CurriculumError, match=msg):
        c.parse_upload(**kwargs)


GOOD = {"grade": "1", "title": "आम", "lakshya_ids": ["NIPUN-G1-NUM-1"], "lakshya_confirmed": True,
        "lines": [{"hindi": "यह एक आम है।", "type": "lesson_script"},
                  {"hindi": "कितने आम हैं?", "type": "assessment_prompt", "answer": "एक"}]}


def test_validate_and_build():
    grade, title, lines, ids = c.validate(GOOD)
    lesson = c.build_lesson(grade, title, lines, ids)
    assert lesson["domain"] == "numeracy" and lesson["review_status"] == "pending_native_review"
    assert lesson["steps"][1]["accept_answers"]["digits"] == ["1"]
    assert lesson["steps"][1]["accept_answers"]["review_status"] == "pending_native_review"
    assert "accept_answers" not in lesson["steps"][0]
    assert [x["hi"] for x in lesson["flashcards"]] == ["एक", "आम"]


@pytest.mark.parametrize("change, msg", [
    ({"lakshya_confirmed": False}, "Confirm"),
    ({"lakshya_ids": []}, "at least one"),
    ({"lakshya_ids": ["NIPUN-G9-NUM-1"]}, "Unknown"),
    ({"lakshya_ids": ["NIPUN-G1-NUM-1", "NIPUN-G1-LIT-1"]}, "one domain"),
    ({"grade": "5"}, "Grade"),
    ({"title": ""}, "title"),
    ({"lines": [{"hindi": "hello there", "type": "lesson_script"}]}, "not in Hindi"),
    ({"lines": [{"hindi": "आम", "type": "song"}]}, "unknown type"),
])
def test_validate_rejects(change, msg):
    with pytest.raises(c.CurriculumError, match=msg):
        c.validate({**GOOD, **change})


def test_answer_key_accepts_alternatives_and_numbers():
    k = c.answer_key("एक सौ बीस / 120")
    assert k["hi"] == ["एक सौ बीस"] and k["digits"] == ["120"]
    k = c.answer_key("तीन")
    assert k["hi"] == ["तीन"] and k["digits"] == ["3"]
    assert c.answer_key("  ") is None
