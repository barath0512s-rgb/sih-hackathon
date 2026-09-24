"""The REST API against the real models (work package 2 acceptance).

B2  every reply has its own audio file, even for concurrent requests
B3/B4  no fake confidence, no fake English pivot; greedy decoding
B5  a correction is reused (both directions)
B6  a lesson survives a restart
B7  /session/response needs an explicit step and grades that step
B8  /health/models reports each language's engines, and no online dependency
Needs the model files; skipped without them.
"""

import hashlib
import importlib
import threading

import pytest

import config

pytestmark = pytest.mark.skipif(
    not (config.ASR_DIR / "model_onnx.py").exists() or
    not (config.NMT_DIR / "config.json").exists(),
    reason="model files not downloaded")


@pytest.fixture(scope="module")
def api(tmp_path_factory):
    """The app, with its database and audio folders in a temp directory."""
    import database
    mp = pytest.MonkeyPatch()
    tmp = tmp_path_factory.mktemp("api")
    mp.setattr(database, "DB_FILE", tmp / "api.db")
    mp.setattr(config, "TTS_OUT_DIR", tmp / "tts_out")
    mp.setattr(config, "TTS_CACHE_DIR", tmp / "tts_cache")
    app_module = importlib.import_module("app")
    app_module.app.testing = True
    yield app_module
    mp.undo()


def post(api, path, **body):
    r = api.app.test_client().post(path, json=body)
    return r.status_code, r.get_json()


# ── B2 ────────────────────────────────────────────────────────────────────────
def test_concurrent_requests_get_their_own_audio(api):
    lines = ["आज हम जोड़ना सीखेंगे। एक और एक मिलाओ।", "यहाँ कितने पत्थर हैं? बताओ।"]
    results = {}

    def go(text):
        results[text] = post(api, "/translate/text", text=text, direction="hi-to-sat")[1]

    threads = [threading.Thread(target=go, args=(t,)) for t in lines]
    for t in threads: t.start()
    for t in threads: t.join()

    a, b = (results[t] for t in lines)
    assert a["audio_url"] and b["audio_url"] and a["audio_url"] != b["audio_url"]
    client = api.app.test_client()
    for r in (a, b):
        served = client.get(r["audio_url"]).data
        # The right content: byte-identical to the clip synthesised for THIS
        # sentence (cache key = engine + voice + the text actually spoken).
        spoken = api.pl.transliterate_santali(r["translated_text"])
        model = api.pl._voice_model("santali")
        digest = hashlib.md5(f"piper:{model}:{spoken}".encode("utf-8")).hexdigest()
        assert served == (config.TTS_CACHE_DIR / f"{digest}.wav").read_bytes()
    assert client.get(a["audio_url"]).data != client.get(b["audio_url"]).data


def test_audio_urls_cannot_escape_the_folder(api):
    c = api.app.test_client()
    assert c.get("/audio/..%2Fapp.py").status_code == 404
    assert c.get("/audio/" + "0" * 32).status_code == 404


def test_deprecated_alias_serves_the_newest_clip(api):
    _, r = post(api, "/translate/text", text="बहुत अच्छा!", direction="hi-to-sat")
    c = api.app.test_client()
    assert c.get("/audio/output").data == c.get(r["audio_url"]).data


# ── B3 / B4 ───────────────────────────────────────────────────────────────────
def test_no_fake_confidence_or_pivot(api):
    _, glossary = post(api, "/translate/text", text="यहाँ कितने पत्थर हैं? बताओ।")
    assert glossary["source"] == "glossary" and glossary["model_score"] is None
    _, model = post(api, "/translate/text", text="गांव के सभी लोग मेले में गए थे।")
    assert model["source"] == "model"
    assert 0 < model["model_score"] < 1
    for r in (glossary, model):
        assert r["english_pivot"] == "" and r["confidence"] is None
    assert config.NMT_NUM_BEAMS == 1


# ── B5 ────────────────────────────────────────────────────────────────────────
def test_correction_is_reused_both_ways(api):
    _, first = post(api, "/translate/text", text="मेरी किताब कहाँ है?")
    code, fb = post(api, "/feedback", hindi_text="मेरी किताब कहाँ है?",
                    santali_text=first["translated_text"], is_correct=False,
                    corrected_text="ᱴᱮᱥᱴ ᱠᱚᱨᱮᱠᱥᱚᱱ")
    assert code == 200 and fb["reused"]
    assert "reused" in fb["message"]
    _, again = post(api, "/translate/text", text="मेरी किताब कहाँ है ।")   # typed differently
    assert again["translated_text"] == "ᱴᱮᱥᱴ ᱠᱚᱨᱮᱠᱥᱚᱱ" and again["source"] == "teacher"

    post(api, "/feedback", hindi_text="(model output)", santali_text="ᱫᱟᱜ ᱮᱢ ᱢᱮ",
         is_correct=False, corrected_text="पानी दो", direction="sat-to-hi")
    _, back = post(api, "/translate/text", text="ᱫᱟᱜ ᱮᱢ ᱢᱮ ᱾", direction="sat-to-hi")
    assert back["translated_text"] == "पानी दो" and back["source"] == "teacher"


def test_bad_direction_is_rejected(api):
    assert post(api, "/translate/text", text="x", direction="en-to-fr")[0] == 400
    assert post(api, "/feedback", hindi_text="a", santali_text="b", direction="x")[0] == 400


# ── B6 / B7 ───────────────────────────────────────────────────────────────────
def test_lesson_survives_a_restart_and_grades_the_given_step(api):
    _, s = post(api, "/session/start", grade="2", topic="addition")
    sid = s["session_id"]
    post(api, "/session/next", session_id=sid)
    post(api, "/translate/text", text="दो आम और तीन आम मिलाओ।", session_id=sid)

    api.sessions.clear()                     # what a server restart does to memory

    code, r = post(api, "/session/response", session_id=sid, response="᱗", step=3)
    assert code == 200 and r["signal"] == "green" and r["step"] == 3
    assert post(api, "/session/response", session_id=sid, response="7")[0] == 400
    assert post(api, "/session/response", session_id=sid, response="7", step=9)[0] == 400
    _, summ = post(api, "/session/summary", session_id=sid)
    assert summ["sentences_translated"] == 1 and summ["steps_completed"] == 1
    assert summ["comprehension"]["green"] == 1


# ── B9: latency is measured where the user is ────────────────────────────────
def test_latency_is_logged_and_completed_by_the_client(api):
    import database
    _, r = post(api, "/translate/text", text="गांव के बच्चे खेत में खेल रहे हैं।", device_id="tab-7")
    rid = r["request_id"]
    assert rid and r["tts_engine"] in ("piper", "cache")
    code, _ = post(api, "/metrics/client", request_id=rid, client_total_ms=812.0, response_ms=640.0)
    assert code == 200
    with database._db() as c:
        row = c.execute("SELECT * FROM latency_log WHERE id=?", (rid,)).fetchone()
    assert row["device_id"] == "tab-7" and row["input_type"] == "typed"
    assert row["client_total_ms"] == 812.0
    assert row["network_ms"] == pytest.approx(max(0.0, 640.0 - row["server_ms"]))
    assert "nmt" in row["model_versions"]

    summary = api.app.test_client().get("/metrics/latency").get_json()
    key = "typed hi-to-sat computed"
    assert summary["paths"][key]["count"] >= 1
    assert summary["paths"][key]["client_total_ms"]["n"] >= 1


def test_speech_failure_keeps_the_text_and_is_logged(api, monkeypatch):
    import database
    monkeypatch.setitem(config.PIPER_VOICES, "hindi", "no-such-voice")
    monkeypatch.setattr(config, "TTS_CACHE_DIR", config.TTS_CACHE_DIR / "empty_for_failure")
    code, r = post(api, "/translate/text", text="ᱫᱟᱜ ᱮᱢ ᱢᱮ", direction="sat-to-hi")
    assert code == 200 and r["translated_text"]
    assert r["audio_url"] is None and r["tts_error"] and r["tts_engine"] == "none"
    with database._db() as c:
        row = c.execute("SELECT tts_error, tts_engine FROM latency_log WHERE id=?",
                        (r["request_id"],)).fetchone()
    assert row["tts_engine"] == "none" and "no-such-voice" in row["tts_error"]


def test_client_timing_is_validated(api):
    assert post(api, "/metrics/client", request_id="nope", client_total_ms=1, response_ms=1)[0] == 404
    assert post(api, "/metrics/client", request_id="x", client_total_ms="a", response_ms=1)[0] == 400
    assert post(api, "/metrics/client", request_id="x", client_total_ms=100, response_ms=500)[0] == 400


# ── B8 ────────────────────────────────────────────────────────────────────────
def test_health_models_reports_each_language(api):
    h = api.app.test_client().get("/health/models").get_json()
    assert h["online_dependencies"] == []
    for lang in ("hi", "sat"):
        for stage in ("asr", "nmt", "tts"):
            assert h["languages"][lang][stage]["engine"]
            assert h["languages"][lang][stage]["bytes"] > 0
    assert h["languages"]["sat"]["tts"]["loaded"]
    assert "greedy" in h["languages"]["hi"]["nmt"]["engine"]


def test_worksheet_is_a_pdf(api):
    r = api.app.test_client().post("/worksheet", json={"hindi_text": "आज", "santali_text": "ᱛᱮᱦᱮᱸᱡ"})
    assert r.status_code == 200 and r.data[:4] == b"%PDF"
