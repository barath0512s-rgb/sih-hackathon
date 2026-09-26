"""Correction sync between tablets and the hub (A4 / M5).

A tablet exports a signed file (Settings → Export for the hub, or POST /sync/export
on the tablet): its teachers' corrections and class-level counts. No child names
and no audio are recorded on the tablet, so none can be exported.

    {"payload": "<JSON text>", "signature": "<hex Ed25519 of the payload's UTF-8 bytes>",
     "public_key": "<hex>"}
    payload = {"format": 1, "kind": "tablet-export", "device_id", "public_key", "created",
               "corrections": [{direction, hindi_text, santali_text, is_correct,
                                corrected_text, source_key, timestamp}],
               "analytics":  [{day, grade, topic, lakshya_ids, sessions, green, yellow, red}]}

The hub (POST /sync/import, or python sync.py <file>):
  1. checks the signature, and the tablet's key: trusted on first use per device_id;
     a device whose key changes is refused (someone else's file, or a reset tablet
     that must be re-registered by deleting its row in sync_devices);
  2. merges corrections, per sentence and direction:
       the hub has no verified translation  -> applied
       the same text                        -> nothing to do
       the hub's newest came from this same tablet and this one is newer -> applied
       otherwise (two sources disagree)     -> NOT applied; listed in
                                               docs/native_review.md for a native speaker
  3. stores the class counts (one row per device, day and lesson; a re-import replaces it).
The next content pack carries the merged corrections (tools/build_content_pack.py
already includes every correction) and is signed (pack_signing.py).
"""

import datetime
import json
import sys
from pathlib import Path

import database
import pack_signing
from textnorm import normalize_key

REVIEW = Path(__file__).resolve().parent / "docs" / "native_review.md"
CONFLICT_HEADING = "## 6. Sync conflicts (two sources disagree; not applied)"


class SyncError(Exception):
    pass


def init():
    with database._db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS sync_devices (
                        device_id TEXT PRIMARY KEY, public_key TEXT NOT NULL, first_seen REAL, last_seen REAL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS sync_analytics (
                        device_id TEXT, day TEXT, grade TEXT, topic TEXT, lakshya_ids TEXT,
                        sessions INTEGER, green INTEGER, yellow INTEGER, red INTEGER,
                        PRIMARY KEY (device_id, day, grade, topic))""")
        cols = {r["name"] for r in c.execute("PRAGMA table_info(feedback)")}
        if "origin" not in cols:
            c.execute("ALTER TABLE feedback ADD COLUMN origin TEXT NOT NULL DEFAULT 'hub'")


def verify(blob: bytes) -> dict:
    try:
        outer = json.loads(blob)
        payload_text, sig, pub = outer["payload"], outer["signature"], outer["public_key"]
    except (ValueError, KeyError, TypeError):
        raise SyncError("not a tablet export file")
    if not pack_signing.verify(pub, payload_text.encode("utf-8"), sig):
        raise SyncError("the signature does not match: the file was changed or is not from a tablet")
    p = json.loads(payload_text)
    if p.get("format") != 1 or p.get("kind") != "tablet-export" or p.get("public_key") != pub:
        raise SyncError("unsupported export format")
    init()
    import time
    with database._db() as c:
        row = c.execute("SELECT public_key FROM sync_devices WHERE device_id=?", (p["device_id"],)).fetchone()
        if row and row["public_key"] != pub:
            raise SyncError(f"device {p['device_id']} is known with a different key: refused")
        if row:
            c.execute("UPDATE sync_devices SET last_seen=? WHERE device_id=?", (time.time(), p["device_id"]))
        else:
            c.execute("INSERT INTO sync_devices VALUES (?, ?, ?, ?)", (p["device_id"], pub, time.time(), time.time()))
    return p


def _verified_text(r, direction):
    corrected = (r["corrected_text"] or "").strip()
    if corrected:
        return corrected
    if r["is_correct"]:
        return ((r["santali_text"] if direction == "hi-to-sat" else r["hindi_text"]) or "").strip() or None
    return None


def merge(p: dict) -> dict:
    init()
    device = p["device_id"]
    report = {"device_id": device, "applied": 0, "same": 0, "conflicts": [], "ignored": 0, "analytics_rows": 0}
    # the tablet's newest feedback per sentence
    newest = {}
    for c in sorted(p.get("corrections", []), key=lambda c: c.get("timestamp", 0)):
        if c.get("direction") not in database.DIRECTIONS:
            report["ignored"] += 1
            continue
        src = c["hindi_text"] if c["direction"] == "hi-to-sat" else c["santali_text"]
        newest[(c["direction"], normalize_key(src or ""))] = c
    for (direction, key), c in newest.items():
        mine = _verified_text(c, direction)
        if not key or mine is None:
            report["ignored"] += 1                       # a thumbs-down alone: nothing to share
            continue
        with database._db() as db:
            hub = db.execute("""SELECT corrected_text, hindi_text, santali_text, is_correct, timestamp, origin
                                FROM feedback WHERE direction=? AND source_key=?
                                ORDER BY timestamp DESC, id DESC LIMIT 1""", (direction, key)).fetchone()
        theirs = _verified_text(hub, direction) if hub else None
        if theirs is not None and theirs == mine:
            report["same"] += 1
            continue
        same_source_newer = hub is not None and hub["origin"] == f"tablet:{device}" and c["timestamp"] > hub["timestamp"]
        if theirs is None or same_source_newer:
            database.save_feedback(c["hindi_text"], c["santali_text"], c.get("is_correct", False),
                                   c.get("corrected_text", ""), direction,
                                   timestamp=c["timestamp"], origin=f"tablet:{device}")
            report["applied"] += 1
        else:
            report["conflicts"].append({"direction": direction, "source": c["hindi_text"] if direction == "hi-to-sat"
                                        else c["santali_text"], "hub": theirs, "hub_origin": hub["origin"],
                                        "tablet": mine, "device_id": device})
    with database._db() as db:
        for a in p.get("analytics", []):
            db.execute("INSERT OR REPLACE INTO sync_analytics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (device, a["day"], str(a["grade"]), a["topic"], ",".join(a.get("lakshya_ids", [])),
                        int(a.get("sessions", 0)), int(a.get("green", 0)), int(a.get("yellow", 0)), int(a.get("red", 0))))
            report["analytics_rows"] += 1
    if report["conflicts"]:
        _write_conflicts(report["conflicts"])
    return report


def _write_conflicts(conflicts, path=None):
    path = Path(path or REVIEW)
    text = path.read_text(encoding="utf-8") if path.exists() else "# Items awaiting native Santali review\n"
    if CONFLICT_HEADING not in text:
        text = text.rstrip("\n") + "\n\n" + CONFLICT_HEADING + "\n\n" + \
            "A tablet's correction disagrees with a correction from another source. Neither is changed until a " \
            "native speaker decides; then correct the sentence on the hub.\n\n" + \
            "| Date | Direction | Source sentence | On the hub (from) | From the tablet | Decision |\n|---|---|---|---|---|---|\n"
    today = datetime.date.today().isoformat()
    rows = "".join(f"| {today} | {c['direction']} | {c['source']} | {c['hub']} ({c['hub_origin']}) | {c['tablet']} "
                   f"(tablet:{c['device_id']}) | |\n" for c in conflicts
                   if f"| {c['source']} | {c['hub']} (" not in text or f"| {c['tablet']} (tablet:{c['device_id']})" not in text)
    path.write_text(text.rstrip("\n") + "\n" + rows, encoding="utf-8", newline="\n")


def import_file(blob: bytes) -> dict:
    return merge(verify(blob))


def class_counts():
    """Rows for the Lakshya view (A8): per device, day, lesson."""
    init()
    with database._db() as db:
        return [dict(r) for r in db.execute("SELECT * FROM sync_analytics ORDER BY day, grade, topic")]


if __name__ == "__main__":
    for f in sys.argv[1:]:
        print(json.dumps(import_file(Path(f).read_bytes()), ensure_ascii=False, indent=1))
