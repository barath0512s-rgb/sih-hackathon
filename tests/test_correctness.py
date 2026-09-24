"""Audit bugs fixed in work package 2 that need no model files.

B5  corrections: normalised keys, both directions, absolute DB path, migration
B6  sessions survive a restart
B7  grading: Santali and any-script digit answers, explicit step index
"""

import sqlite3
import time

import pytest

import config
import database
from textnorm import normalize_key


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A fresh database file for each test."""
    monkeypatch.setattr(database, "DB_FILE", tmp_path / "test.db")
    database.init_db()
    return database


# ── normalisation ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize("a,b", [
    ("आज हम गणित पढ़ेंगे।", "आज हम गणित पढ़ेंगे"),             # danda
    ("आज हम गणित पढ़ेंगे।", "आज  हम   गणित पढ़ेंगे ।"),        # spacing
    ("आज हम गणित पढ़ेंगे", "आज हम गणित पढ़ेंगे."),             # full stop
    ("पांच", "पाँच"),                                          # chandrabindu
    ("ज़रूर", "जरूर"),                                          # nukta
    ("ज़रूर", "ज़रूर"),                                    # decomposed nukta
    ("7", "७"), ("7", "᱗"),                                    # digits
    ("ᱫᱟᱜ ᱾", "ᱫᱟᱜ"),                                          # Ol Chiki full stop
    ("क्ष‍त्र", "क्षत्र"),                                  # zero-width joiner
])
def test_normalize_key_matches_variants(a, b):
    assert normalize_key(a) == normalize_key(b)


def test_normalize_key_keeps_different_sentences_apart():
    assert normalize_key("सात") != normalize_key("सात आम")
    assert normalize_key("7") != normalize_key("17")


# ── B5: corrections ───────────────────────────────────────────────────────────
def test_db_path_is_absolute():
    assert config.DB_FILE.is_absolute()


def test_correction_found_despite_typing_differences(db):
    db.save_feedback("आज हम गणित पढ़ेंगे।", "ᱢᱚᱰᱮᱞ", False, "ᱴᱤᱪᱚᱨ")
    for variant in ("आज हम गणित पढ़ेंगे", "आज  हम गणित पढ़ेंगे .", "आज हम गणित पढेंगे"):
        assert db.get_correction(variant) == "ᱴᱤᱪᱚᱨ", variant


def test_correction_in_the_santali_to_hindi_direction(db):
    db.save_feedback("गलत", "ᱫᱟᱜ ᱾", False, "पानी", direction="sat-to-hi")
    assert db.get_correction("ᱫᱟᱜ", "sat-to-hi") == "पानी"
    # ... and it does not leak into the other direction
    assert db.get_correction("गलत", "hi-to-sat") is None


def test_newest_feedback_wins(db):
    db.save_feedback("नमस्ते", "ᱟ", False, "ᱵ")
    time.sleep(0.01)
    db.save_feedback("नमस्ते", "ᱵ", True, "")          # later approval of the fix
    assert db.get_correction("नमस्ते") == "ᱵ"
    time.sleep(0.01)
    db.save_feedback("नमस्ते", "ᱵ", False, "")         # later rejection, no fix
    assert db.get_correction("नमस्ते") is None


def test_legacy_database_is_migrated(tmp_path, monkeypatch):
    """A database from before WP2 (no direction/source_key) keeps its data."""
    path = tmp_path / "legacy.db"
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, hindi_text TEXT,"
              " santali_text TEXT, is_correct BOOLEAN, corrected_text TEXT, timestamp REAL)")
    c.execute("INSERT INTO feedback (hindi_text, santali_text, is_correct, corrected_text, timestamp)"
              " VALUES ('आज हम गणित पढ़ेंगे', 'ᱢᱚᱰᱮᱞ', 0, 'ᱴᱤᱪᱚᱨ', 1.0)")
    c.commit(); c.close()
    monkeypatch.setattr(database, "DB_FILE", path)
    database.init_db()
    database.init_db()                                   # idempotent
    assert database.get_correction("आज हम गणित पढ़ेंगे।") == "ᱴᱤᱪᱚᱨ"
    rows = sqlite3.connect(path).execute(
        "SELECT direction, source_key FROM feedback").fetchall()
    assert rows == [("hi-to-sat", normalize_key("आज हम गणित पढ़ेंगे"))]


def test_spoken_line_without_punctuation_finds_correction_and_glossary(db):
    """Speech recognition writes no punctuation: a spoken line must still match."""
    from education_glossary import lookup_hi_to_sat
    db.save_feedback("दो आम लो। तीन आम दो।", "ᱢᱚᱰᱮᱞ", False, "ᱴᱤᱪᱚᱨ")
    assert db.get_correction("दो आम लो तीन आम दो") == "ᱴᱤᱪᱚᱨ"
    assert lookup_hi_to_sat("आज हम जोड़ना सीखेंगे एक और एक मिलाओ")


def test_keys_from_an_older_normaliser_are_recomputed(tmp_path, monkeypatch):
    path = tmp_path / "v1.db"
    monkeypatch.setattr(database, "DB_FILE", path)
    database.init_db()
    c = sqlite3.connect(path)
    c.execute("INSERT INTO feedback (hindi_text, santali_text, is_correct, corrected_text,"
              " timestamp, direction, source_key) VALUES ('दो आम लो। तीन आम दो।', 'ᱟ', 0,"
              " 'ᱵ', 1.0, 'hi-to-sat', 'दो आम लो. तीन आम दो')")        # a version-1 key
    c.execute("PRAGMA user_version = 1")
    c.commit(); c.close()
    database.init_db()
    assert database.get_correction("दो आम लो तीन आम दो") == "ᱵ"


# ── B7: grading ───────────────────────────────────────────────────────────────
import lesson_engine
from lesson_engine import LessonSession, get_lesson, grade

ADD = get_lesson("2", "addition")          # step 3: "तीन और चार कितने होते हैं?" -> 7


@pytest.mark.parametrize("answer", ["7", "७", "᱗", "सात", "saat", "Saat", "ᱮᱭᱟᱭ", "ᱮᱭᱟᱭ ᱜᱚᱴᱟᱝ ᱾"])
def test_right_answers_in_any_script_are_green(answer):
    assert grade(ADD["steps"][3], answer) == "green"


@pytest.mark.parametrize("answer,signal", [("8", "yellow"), ("ᱟᱨᱮ", "yellow"), ("", "red"), ("   ", "red")])
def test_wrong_and_empty_answers(answer, signal):
    assert grade(ADD["steps"][3], answer) == signal


def test_every_assessment_has_santali_answers_pending_review():
    for grade_key, topics in lesson_engine.NIPUN_LESSONS.items():
        for topic, lesson in topics.items():
            for st in lesson["steps"]:
                if st["type"] == "assessment_prompt":
                    acc = st.get("accept_answers")
                    assert acc and acc.get("sat"), (topic, st["hindi"])
                    assert acc.get("review_status") == "pending_native_review"
                    assert set(acc["sat"]) == set(acc["sat_sources"]), topic


def test_the_step_is_explicit(db):
    """Old code graded step_idx - 1: after one advance it graded step 0."""
    s = LessonSession(ADD)
    s.advance()
    assert s.check_response("7", step=3) == "green"
    assert s.check_response("7", step=1) == "yellow"      # that step asks no question
    with pytest.raises(ValueError):
        s.check_response("7", step=99)


# ── B6: sessions survive a restart ────────────────────────────────────────────
def test_session_survives_a_restart(db):
    s = LessonSession(ADD, sid="abc123", grade_="2", topic="addition")
    s.advance(); s.advance()
    s.record_translation("दो आम", "ᱵᱟᱨ ᱩᱞ", 0.8)
    s.check_response("᱗", step=3)
    del s                                                  # the process "restarts"
    r = LessonSession.load("abc123")
    assert r is not None
    assert r.step_idx == 2
    assert r.translations == [{"step": 2, "hindi": "दो आम", "santali": "ᱵᱟᱨ ᱩᱞ", "latency": 0.8}]
    assert [x["signal"] for x in r.responses] == ["green"]
    assert r.summary()["comprehension"]["green"] == 1


def test_unknown_session_is_none(db):
    assert LessonSession.load("nope") is None
