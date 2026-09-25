"""The hub meets the shared REST contract (contract/rest_contract.json).

The Android in-app server runs the same file (android/app/src/test,
tools/android/device_contract.py), so the tablet and the hub answer the page the
same way. Needs the model files; skipped without them.
"""

import importlib

import pytest

import config
from contract.runner import load, run

pytestmark = pytest.mark.skipif(
    not (config.ASR_DIR / "model_onnx.py").exists() or not (config.NMT_DIR / "config.json").exists(),
    reason="model files not downloaded")


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    import database
    mp = pytest.MonkeyPatch()
    tmp = tmp_path_factory.mktemp("contract")
    mp.setattr(database, "DB_FILE", tmp / "contract.db")
    mp.setattr(config, "TTS_OUT_DIR", tmp / "tts_out")
    mp.setattr(config, "TTS_CACHE_DIR", tmp / "tts_cache")
    mp.setattr(config, "LESSON_AUDIO_DIR", tmp / "lesson_audio")
    app_module = importlib.import_module("app")
    database.init_db()          # the app may already be imported (another test module): tables for this DB
    app_module.app.testing = True
    yield app_module.app.test_client()
    mp.undo()


def test_the_hub_meets_the_contract(client):
    def send(method, path, body):
        r = client.open(path, method=method, json=body)
        return r.status_code, r.content_type, r.data
    assert run(send) == []


def test_the_contract_is_well_formed():
    c = load()
    ids = [x["id"] for x in c["setup"] + c["cases"]]
    assert len(ids) == len(set(ids))
    for case in c["cases"]:
        assert case["method"] in ("GET", "POST") and case["path"].startswith("/")
        assert "types" in case or "content_type" in case, case["id"]


def test_a_server_without_an_engine_must_say_so():
    # A fake server that has no translation model and answers that honestly.
    import json

    def send(method, path, body):
        if path == "/translate/text" and body and body.get("text", "").startswith("यह वाक्य"):
            return 503, "application/json", json.dumps({"error": "x", "code": "engine_not_on_device"}).encode()
        return 500, "text/plain", b"not implemented"
    fails = run(send, engines=set())
    assert not any(f.startswith("translate_new_sentence") for f in fails)
