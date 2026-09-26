"""A8: class-level NIPUN Lakshya progress from the hub's lessons and synced tablets (no models)."""
import datetime
import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import database  # noqa: E402
import progress  # noqa: E402
import sync  # noqa: E402


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_FILE", tmp_path / "hub.db")
    database.init_db()
    sync.init()


def test_hub_lessons_and_synced_tablets_are_counted_per_lakshya_and_week(db):
    database.create_session("s1", "1", "counting_1_10")          # Lakshyas NIPUN-BV-NUM-1, NIPUN-G1-NUM-1
    for sig in ("green", "green", "red"):
        database.add_session_event("s1", "response", 3, {"step": 3, "response": "3", "signal": sig})
    with database._db() as c:
        c.execute("INSERT INTO sync_analytics VALUES (?,?,?,?,?,?,?,?,?)",
                  ("tabletA", datetime.date.today().isoformat(), "1", "counting_1_10", "NIPUN-G1-NUM-1", 2, 5, 1, 0))
    rs = progress.rows()
    week = progress._week(datetime.date.today().isoformat())
    g1 = next(r for r in rs if r["lakshya_id"] == "NIPUN-G1-NUM-1" and r["week"] == week)
    assert (g1["lessons_taught"], g1["green"], g1["yellow"], g1["red"]) == (3, 7, 1, 1)
    assert g1["sources"] == ["hub", "tablet:tabletA"] and g1["green_share"] == round(7 / 9, 3)
    bv = next(r for r in rs if r["lakshya_id"] == "NIPUN-BV-NUM-1")
    assert (bv["lessons_taught"], bv["green"]) == (1, 2)


def test_a_session_with_nothing_in_it_is_not_a_lesson_taught(db):
    database.create_session("empty", "2", "addition")                 # the page opened it; nothing happened
    assert progress.rows() == []


def test_csv_and_pdf_exports(db):
    database.create_session("s1", "2", "addition")
    database.add_session_event("s1", "translation", 0, {"step": 0, "hindi": "x", "santali": "y", "latency": 1})
    rs = progress.rows()
    csv_text = progress.as_csv(rs)
    assert csv_text.splitlines()[0].startswith("week,lakshya_id,lessons_taught") and "NIPUN-G1-NUM-2" in csv_text
    pymupdf = pytest.importorskip("pymupdf")
    import io
    buf = io.BytesIO()
    progress.as_pdf(rs, buf)
    text = pymupdf.open(stream=buf.getvalue(), filetype="pdf")[0].get_text()
    assert "NIPUN-G1-NUM-2" in text
