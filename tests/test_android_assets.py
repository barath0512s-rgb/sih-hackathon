"""The Android app's copies stay in step with the Python they mirror (no models needed)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "android"))


def test_app_config_matches_config_py():
    import sync_config
    assert sync_config.OUT.read_text(encoding="utf-8") == sync_config.expected(), \
        "run python tools/android/sync_config.py"


def test_kotlin_vectors_match_python():
    # TextNormTest.kt checks the Kotlin port against these; here, that they still
    # describe what Python does today.
    from lesson_engine import grade
    from textnorm import normalize_key
    v = json.loads((ROOT / "tests" / "data" / "normalize_key_vectors.json").read_text(encoding="utf-8"))
    for c in v["normalize_key"]:
        assert normalize_key(c["in"]) == c["key"], c
    for c in v["grade"]:
        step = {"accept_answers": c["accept_answers"]} if c["accept_answers"] else {}
        assert grade(step, c["answer"]) == c["signal"], c


def test_the_android_test_pack_is_intact():
    import hashlib
    d = ROOT / "android" / "app" / "src" / "test" / "resources" / "pack"
    m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    for name, sha in m["files"].items():
        assert hashlib.sha256((d / name).read_bytes()).hexdigest() == sha, name


def test_the_tablet_server_listens_on_loopback_only():
    src = (ROOT / "android/app/src/main/java/org/team8bitpool/app/server/LocalServer.kt").read_text(encoding="utf-8")
    assert 'NanoHTTPD("127.0.0.1", port)' in src
