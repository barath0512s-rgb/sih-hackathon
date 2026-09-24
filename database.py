"""SQLite storage: teacher corrections and lesson sessions.

Corrections are matched on a normalised key (textnorm.normalize_key) in both
directions, so a fix is reused however the sentence is typed next time.
Sessions and their events are stored as they happen, so a server restart does
not lose a lesson in progress.
"""

import contextlib
import json
import sqlite3
import time

import config
from textnorm import normalize_key

DB_FILE = config.DB_FILE          # module-level so tests can point it elsewhere

DIRECTIONS = ("hi-to-sat", "sat-to-hi")


@contextlib.contextmanager
def _db():
    conn = sqlite3.connect(str(DB_FILE), timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create or migrate the schema. Safe to call any number of times."""
    with _db() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hindi_text TEXT,
                santali_text TEXT,
                is_correct BOOLEAN,
                corrected_text TEXT,
                timestamp REAL
            )""")
        cols = {r["name"] for r in c.execute("PRAGMA table_info(feedback)")}
        # Migration 1: corrections work in both directions and match on a key.
        if "direction" not in cols:
            c.execute("ALTER TABLE feedback ADD COLUMN direction TEXT NOT NULL DEFAULT 'hi-to-sat'")
        if "source_key" not in cols:
            c.execute("ALTER TABLE feedback ADD COLUMN source_key TEXT")
        for r in c.execute("SELECT id, direction, hindi_text, santali_text "
                           "FROM feedback WHERE source_key IS NULL").fetchall():
            src = r["hindi_text"] if r["direction"] == "hi-to-sat" else r["santali_text"]
            c.execute("UPDATE feedback SET source_key=? WHERE id=?",
                      (normalize_key(src or ""), r["id"]))
        c.execute("CREATE INDEX IF NOT EXISTS idx_feedback_key "
                  "ON feedback(direction, source_key, timestamp)")

        c.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                grade TEXT NOT NULL,
                topic TEXT NOT NULL,
                step_idx INTEGER NOT NULL DEFAULT 0,
                started_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )""")
        c.execute("""
            CREATE TABLE IF NOT EXISTS session_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id),
                kind TEXT NOT NULL,              -- 'translation' | 'response'
                step INTEGER NOT NULL,
                payload TEXT NOT NULL,           -- JSON
                ts REAL NOT NULL
            )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_events_session "
                  "ON session_events(session_id, id)")


# ── Corrections ───────────────────────────────────────────────────────────────
def save_feedback(hindi, santali, is_correct, corrected="", direction="hi-to-sat"):
    """Store a thumbs-up, thumbs-down, or correction.

    hindi_text / santali_text always hold the Hindi and Santali sides, whichever
    way the translation ran. corrected_text is in the target language.
    """
    if direction not in DIRECTIONS:
        raise ValueError(f"direction must be one of {DIRECTIONS}")
    source = hindi if direction == "hi-to-sat" else santali
    with _db() as c:
        c.execute("""
            INSERT INTO feedback (hindi_text, santali_text, is_correct, corrected_text,
                                  timestamp, direction, source_key)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (hindi, santali, bool(is_correct), corrected or "", time.time(),
             direction, normalize_key(source or "")))


def get_correction(source_text, direction="hi-to-sat"):
    """The teacher-verified translation of source_text, or None.

    The newest feedback for the sentence wins. A correction returns the
    corrected text; a thumbs-up returns the translation that was approved;
    a thumbs-down with no correction returns None, so the model answers.
    """
    key = normalize_key(source_text or "")
    if not key:
        return None
    with _db() as c:
        r = c.execute("""
            SELECT corrected_text, hindi_text, santali_text, is_correct
            FROM feedback WHERE direction=? AND source_key=?
            ORDER BY timestamp DESC, id DESC LIMIT 1""", (direction, key)).fetchone()
    if not r:
        return None
    if r["corrected_text"] and r["corrected_text"].strip():
        return r["corrected_text"].strip()
    if r["is_correct"]:
        target = r["santali_text"] if direction == "hi-to-sat" else r["hindi_text"]
        return (target or "").strip() or None
    return None


def export_to_csv(output_path="training_data/human_feedback_dataset.csv"):
    """Export the corrections to a CSV for LoRA fine-tuning."""
    import pandas as pd
    with _db() as c:
        df = pd.read_sql_query("SELECT * FROM feedback", c)
    df.to_csv(output_path, index=False, encoding="utf-8")
    return output_path


# ── Sessions ──────────────────────────────────────────────────────────────────
def create_session(sid, grade, topic):
    now = time.time()
    with _db() as c:
        c.execute("INSERT INTO sessions (id, grade, topic, step_idx, started_at, updated_at) "
                  "VALUES (?, ?, ?, 0, ?, ?)", (sid, str(grade), topic, now, now))


def set_session_step(sid, step_idx):
    with _db() as c:
        c.execute("UPDATE sessions SET step_idx=?, updated_at=? WHERE id=?",
                  (int(step_idx), time.time(), sid))


def add_session_event(sid, kind, step, payload):
    with _db() as c:
        c.execute("INSERT INTO session_events (session_id, kind, step, payload, ts) "
                  "VALUES (?, ?, ?, ?, ?)",
                  (sid, kind, int(step), json.dumps(payload, ensure_ascii=False), time.time()))
        c.execute("UPDATE sessions SET updated_at=? WHERE id=?", (time.time(), sid))


def load_session(sid):
    """(session row as dict, [events as dicts]) or None if unknown."""
    with _db() as c:
        s = c.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
        if not s:
            return None
        ev = c.execute("SELECT kind, step, payload, ts FROM session_events "
                       "WHERE session_id=? ORDER BY id", (sid,)).fetchall()
    return dict(s), [dict(e, payload=json.loads(e["payload"])) for e in ev]


if __name__ == "__main__":
    init_db()
    print(f"Database ready: {DB_FILE}")
