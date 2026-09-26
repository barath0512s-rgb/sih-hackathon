"""A4: the hub verifies and merges a tablet's signed export (no models needed)."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

pytest.importorskip("cryptography")
from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

import database  # noqa: E402
import sync  # noqa: E402


@pytest.fixture
def hub(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_FILE", tmp_path / "hub.db")
    monkeypatch.setattr(sync, "REVIEW", tmp_path / "native_review.md")
    database.init_db()
    sync.init()
    return tmp_path


def export(key, corrections, analytics=(), device="tabletA"):
    pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    payload = json.dumps({"format": 1, "kind": "tablet-export", "device_id": device, "public_key": pub,
                          "created": "2026-09-26T20:00:00+05:30", "corrections": list(corrections),
                          "analytics": list(analytics)}, ensure_ascii=False)
    return json.dumps({"payload": payload, "signature": key.sign(payload.encode("utf-8")).hex(),
                       "public_key": pub}).encode("utf-8")


def fix(hi, sat, t, corrected=None, ok=False):
    return {"hindi_text": hi, "santali_text": sat, "is_correct": ok, "corrected_text": corrected or "",
            "direction": "hi-to-sat", "timestamp": t}


def test_a_new_correction_is_applied_and_goes_into_the_next_pack(hub):
    k = Ed25519PrivateKey.generate()
    r = sync.import_file(export(k, [fix("दो आम", "ᱵᱟᱨ ᱟᱢ", 100, "ᱵᱟᱨᱭᱟ ᱟᱢ")],
                                [{"day": "2026-09-26", "grade": "1", "topic": "counting_1_10",
                                  "lakshya_ids": ["NIPUN-G1-NUM-1"], "sessions": 1, "green": 3, "yellow": 1, "red": 0}]))
    assert r["applied"] == 1 and not r["conflicts"] and r["analytics_rows"] == 1
    assert database.get_correction("दो आम।", "hi-to-sat") == "ᱵᱟᱨᱭᱟ ᱟᱢ"
    assert {"source_text": "दो आम"} in database.list_corrections("hi-to-sat")        # the pack builder's list
    assert sync.class_counts()[0]["green"] == 3


def test_disagreeing_sources_are_not_applied_but_listed_for_review(hub):
    database.save_feedback("दो आम", "ᱵᱟᱨ ᱟᱢ", False, "ᱵᱟᱨ ᱜᱚᱴᱟᱝ ᱟᱢ", "hi-to-sat")   # the hub's own correction
    k = Ed25519PrivateKey.generate()
    r = sync.import_file(export(k, [fix("दो आम", "ᱵᱟᱨ ᱟᱢ", 10 ** 10, "ᱵᱟᱨᱭᱟ ᱟᱢ")]))
    assert r["applied"] == 0 and len(r["conflicts"]) == 1
    assert database.get_correction("दो आम", "hi-to-sat") == "ᱵᱟᱨ ᱜᱚᱴᱟᱝ ᱟᱢ"         # unchanged
    text = sync.REVIEW.read_text(encoding="utf-8")
    assert sync.CONFLICT_HEADING in text and "ᱵᱟᱨᱭᱟ ᱟᱢ" in text and "ᱵᱟᱨ ᱜᱚᱴᱟᱝ ᱟᱢ" in text


def test_the_same_tablet_newer_correction_wins(hub):
    k = Ed25519PrivateKey.generate()
    sync.import_file(export(k, [fix("दो आम", "ᱵᱟᱨ ᱟᱢ", 100, "ᱵᱟᱨᱭᱟ ᱟᱢ")]))
    r = sync.import_file(export(k, [fix("दो आम", "ᱵᱟᱨ ᱟᱢ", 200, "ᱵᱟᱨ ᱟᱢ ᱠᱚ")]))
    assert r["applied"] == 1 and not r["conflicts"]
    assert database.get_correction("दो आम", "hi-to-sat") == "ᱵᱟᱨ ᱟᱢ ᱠᱚ"


def test_a_changed_file_or_a_changed_key_is_refused(hub):
    k = Ed25519PrivateKey.generate()
    blob = export(k, [fix("दो आम", "ᱵᱟᱨ ᱟᱢ", 100, "ᱵᱟᱨᱭᱟ ᱟᱢ")])
    outer = json.loads(blob)
    outer["payload"] = outer["payload"].replace("100", "999")
    with pytest.raises(sync.SyncError, match="signature"):
        sync.import_file(json.dumps(outer).encode())
    sync.import_file(blob)                                                          # first key: trusted
    with pytest.raises(sync.SyncError, match="different key"):
        sync.import_file(export(Ed25519PrivateKey.generate(), [], device="tabletA"))
    with pytest.raises(sync.SyncError):
        sync.import_file(b"not json")
