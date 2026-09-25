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
    mp.setattr(config, "LESSON_AUDIO_DIR", tmp / "lesson_audio")
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


def test_overlapping_model_translations_all_finish(api):
    # IndicProcessor shares one placeholder queue per instance; without the
    # lock in pipeline._nmt, overlapping translations hung for ever.
    lines = [f"गांव के {w} आज बाज़ार में नए कपड़े खरीदने गए।" for w in
             ("किसान", "बच्चे", "लोग", "शिक्षक", "व्यापारी", "मजदूर")]
    out = {}
    threads = [threading.Thread(target=lambda l=l: out.__setitem__(
        l, api.pl._nmt(l, "hin_Deva", "sat_Olck", api.pl.tok_nmt, api.pl.mdl_nmt)[0]))
        for l in lines]
    for t in threads: t.start()
    for t in threads: t.join(timeout=180)
    assert not any(t.is_alive() for t in threads), "a translation is stuck"
    assert len(out) == len(lines) and all(out.values())
    # The same answer as when run alone: no placeholder crossed over.
    alone = api.pl._nmt(lines[0], "hin_Deva", "sat_Olck", api.pl.tok_nmt, api.pl.mdl_nmt)[0]
    assert out[lines[0]] == alone


def _stream(api, wav_bytes, direction="hi-to-sat"):
    import io as _io
    import json as _json
    r = api.app.test_client().post("/translate/audio_stream",
                                   data={"audio": (_io.BytesIO(wav_bytes), "a.wav"), "direction": direction,
                                         "device_id": "stream-test"},
                                   content_type="multipart/form-data")
    assert r.status_code == 200 and r.mimetype == "application/x-ndjson"
    return [_json.loads(l) for l in r.get_data(as_text=True).splitlines() if l.strip()]


def test_long_utterances_stream_in_chunks_short_ones_stay_whole(api, tmp_path):
    long_hi = ("कुछ अणुओं में अस्थिर केंद्रक होता है जिसका मतलब यह है कि उनमें थोड़े या बिना "
               "किसी झटके से टूटने की प्रवृत्ति होती है")
    short_hi = "तीन और चार कितने होते हैं?"
    for text, want_many in ((long_hi, True), (short_hi, False)):
        wav = tmp_path / "in.wav"
        api.pl.hindi_tts(text, str(wav))                     # the offline voice reads the line
        ev = _stream(api, wav.read_bytes())
        kinds = [e["type"] for e in ev]
        assert kinds[0] == "asr" and kinds[-1] == "done"
        chunks = [e for e in ev if e["type"] == "chunk"]
        assert len(chunks) == ev[0]["chunks"]
        assert (len(chunks) > 1) == want_many, (text, ev[0]["recognized_text"])
        for c in chunks:
            assert c["translated_text"] and c["audio_url"] and not c["tts_error"]
        assert [c["ms"] for c in chunks] == sorted(c["ms"] for c in chunks)
        assert ev[-1]["translated_text"] == " ".join(c["translated_text"] for c in chunks)
    import database
    with database._db() as c:
        row = c.execute("SELECT input_type, chunks FROM latency_log WHERE device_id='stream-test' "
                        "ORDER BY ts DESC LIMIT 2").fetchall()
    assert {r["input_type"] for r in row} == {"voice", "voice-stream"}
    code, _ = post(api, "/metrics/client", request_id=ev[-1]["request_id"], client_total_ms=900.0,
                   response_ms=700.0, client_last_ms=2500.0)
    assert code == 200


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


# ── WP7: flashcards come from the lessons ────────────────────────────────────
def test_flashcards_are_built_from_the_lessons(api):
    from lesson_engine import get_lesson
    c = api.app.test_client()
    r = c.get("/flashcards?grade=2&topic=reading_words")
    assert r.status_code == 200
    (deck,) = r.get_json()["decks"]
    lesson = get_lesson("2", "reading_words")
    assert [x["hi"] for x in deck["cards"]] == [x["hi"] for x in lesson["flashcards"]]
    assert deck["lakshya_ids"] == lesson["lakshya_ids"]
    for card in deck["cards"]:
        # Every card says which layer answered it and whether it was reviewed.
        assert card["sat"] and card["source"] in ("teacher", "glossary", "wordlist", "cached", "model")
        assert card["review_status"]
        assert not card["sat"].endswith(("᱾", "।"))       # a card is a word, not a sentence
    # घर comes from the corrected word list, marked as not yet reviewed.
    ghar = next(x for x in deck["cards"] if x["hi"] == "घर")
    assert ghar["sat"] == "ᱳᱲᱟᱜ" and ghar["source"] == "wordlist"
    assert ghar["review_status"] == "pending_native_review"
    # A card with no word-list entry falls through to the model, labelled so.
    phool = next(x for x in deck["cards"] if x["hi"] == "फूल")
    assert phool["source"] in ("cached", "model") and phool["review_status"] == "unreviewed_model_output"

    everything = c.get("/flashcards").get_json()["decks"]
    assert {d["topic"] for d in everything} == {
        "counting_1_10", "shapes", "addition", "reading_words", "subtraction"}
    assert c.get("/flashcards?grade=9").status_code == 404


def test_speak_says_the_given_text(api):
    code, r = post(api, "/speak", text="ᱳᱲᱟᱜ", lang="sat")
    assert code == 200 and r["audio_url"] and r["tts_error"] is None
    spoken = api.pl.transliterate_santali("ᱳᱲᱟᱜ")
    digest = hashlib.md5(f"piper:{api.pl._voice_model('santali')}:{spoken}".encode("utf-8")).hexdigest()
    assert api.app.test_client().get(r["audio_url"]).data == \
        (config.TTS_CACHE_DIR / f"{digest}.wav").read_bytes()
    assert post(api, "/speak", text="", lang="sat")[0] == 400
    assert post(api, "/speak", text="x", lang="en")[0] == 400


# ── WP14: a teacher imports a lesson ─────────────────────────────────────────
TEN_LINES = """आज हम पाँच तक गिनती सीखेंगे।
यह एक आम है।
यहाँ दो केले हैं।
मेज़ पर तीन पत्थर हैं।
चार फूल देखो।
अपनी पाँच उंगलियाँ दिखाओ।
मेरे साथ एक से पाँच तक गिनो।
कितने आम हैं?
मेज़ पर कितने पत्थर हैं?
शाबाश, तुमने अच्छा गिना।"""


def test_importing_a_ten_line_lesson(api):
    c = api.app.test_client()
    # 1. The teacher pastes the text: a draft comes back, nothing is stored.
    r = c.post("/curriculum/import", json={"text": TEN_LINES, "grade": "1", "title": "पाँच तक गिनती"})
    assert r.status_code == 200
    (d,) = r.get_json()["lessons"]
    assert len(d["lines"]) == 10
    assert [l["type"] for l in d["lines"]] == [
        "lesson_script", "lesson_script", "lesson_script", "lesson_script",
        "activity_instruction", "activity_instruction", "activity_instruction",
        "assessment_prompt", "assessment_prompt", "lesson_script"]
    assert d["suggested"]["domain"] == "numeracy" and d["suggested"]["lakshya_ids"]
    assert len(r.get_json()["lakshyas"]) == 15
    before = len(c.get("/lessons").get_json()["lessons"])

    # 2. The teacher changes one label, gives an expected answer, confirms the goals.
    d["lines"][9]["type"] = "activity_instruction"
    d["lines"][7]["answer"] = "एक"
    r = c.post("/curriculum/save", json={**d, "lakshya_ids": d["suggested"]["lakshya_ids"],
                                          "lakshya_confirmed": True})
    assert r.status_code == 200, r.get_json()
    les = r.get_json()
    topic = les["topic"]

    # Typed steps, the teacher's label kept, Lakshya IDs, Santali on every line.
    assert len(les["steps"]) == 10 and les["steps"][9]["type"] == "activity_instruction"
    assert les["lakshya_ids"] == d["suggested"]["lakshya_ids"]
    for st in les["steps"]:
        assert st["santali"] and st["review_status"] in ("pending_native_review", "teacher_verified")
    assert les["steps"][7]["accept_answers"]["digits"] == ["1"]

    # Audio for every line.
    assert les["audio_errors"] == 0
    for st in les["steps"]:
        wav = c.get(st["audio_url"])
        assert wav.status_code == 200 and wav.data[:4] == b"RIFF" and len(wav.data) > 4000

    # A worksheet PDF with the tags.
    pdf = c.get(les["worksheet_url"])
    assert pdf.status_code == 200 and pdf.data[:4] == b"%PDF"

    # A deck of at least 5 cards.
    (deck,) = c.get(les["flashcards_url"]).get_json()["decks"]
    assert len(deck["cards"]) >= 5 and deck["lakshya_ids"] == les["lakshya_ids"]

    # Stored: it is a lesson like the others, and it survives a restart.
    lessons = c.get("/lessons").get_json()["lessons"]
    assert len(lessons) == before + 1
    mine = next(l for l in lessons if l["topic"] == topic)
    assert mine["imported"] and mine["grade"] == "1" and len(mine["plan"]) == 10
    api.sessions.clear()
    code, s = post(api, "/session/start", grade="1", topic=topic)
    assert code == 200
    code, g = post(api, "/session/response", session_id=s["session_id"], response="1", step=7)
    assert code == 200 and g["signal"] == "green"
    assert topic in {l["topic"] for l in c.get("/curriculum").get_json()["lessons"]}


def test_curriculum_rejects_bad_input(api):
    c = api.app.test_client()
    assert c.post("/curriculum/import", json={"text": ""}).status_code == 400
    r = c.post("/curriculum/save", json={"grade": "1", "title": "x", "lakshya_ids": ["NIPUN-G1-NUM-1"],
                                         "lines": [{"hindi": "आम गिनो।"}]})
    assert r.status_code == 400 and "Confirm" in r.get_json()["error"]
    assert r.get_json()["code"] == "confirm"          # the UI says it in Hindi
    r = c.post("/curriculum/save", json={"grade": "1", "title": "x", "lakshya_ids": ["NIPUN-G1-NUM-1"],
                                         "lakshya_confirmed": True, "lines": [{"hindi": "hello"}]})
    assert r.get_json()["code"] == "line_not_hindi" and r.get_json()["params"] == {"n": 1}
    assert c.get("/lesson_audio/..%2Fapp.py/0").status_code == 404
    assert c.get("/curriculum/imp_0000000000/worksheet").status_code == 404


def test_team_lessons_are_added_once_on_start(api, tmp_path):
    import json
    seed = tmp_path / "seed.json"
    seed.write_text(json.dumps({"lessons": [{
        "grade": "1", "title": "बीज पाठ", "lakshya_ids": ["NIPUN-G1-NUM-1"],
        "lines": [{"hindi": "यह एक आम है।"}, {"hindi": "कितने आम हैं?", "answer": "एक"}]}]},
        ensure_ascii=False), encoding="utf-8")
    logged = []
    assert api.seed_team_lessons(seed, log=logged.append) == 1
    assert api.seed_team_lessons(seed, log=logged.append) == 0      # idempotent
    mine = [l for l in api.get_all_lessons() if l["title"] == "बीज पाठ"]
    assert len(mine) == 1 and mine[0]["imported"] and mine[0]["lakshya_ids"] == ["NIPUN-G1-NUM-1"]
    # The team's real file parses and splits exactly as recorded.
    import curriculum
    for L in json.loads(config.TEAM_LESSONS_FILE.read_text(encoding="utf-8"))["lessons"]:
        body, _ = curriculum.team_body(L)
        curriculum.validate(body)


def test_curriculum_accepts_a_csv_file(api):
    import io as _io
    csv = "grade,topic,line\n0,अक्षर,यह अक्षर क है।\n0,अक्षर,क की ध्वनि सुनो।\n".encode("utf-8")
    r = api.app.test_client().post("/curriculum/import",
                                   data={"file": (_io.BytesIO(csv), "lesson.csv")},
                                   content_type="multipart/form-data")
    assert r.status_code == 200
    (d,) = r.get_json()["lessons"]
    assert d["grade"] == "0" and d["suggested"]["lakshya_ids"] == ["NIPUN-BV-LIT-1"]


def test_worksheet_is_a_pdf(api):
    r = api.app.test_client().post("/worksheet", json={"hindi_text": "आज", "santali_text": "ᱛᱮᱦᱮᱸᱡ"})
    assert r.status_code == 200 and r.data[:4] == b"%PDF"


def test_audio_from_an_old_cache_entry_is_still_served(api):
    # A voice clip cached long ago must not make the new reply look old: the
    # pruner deleted such replies at once (demo_reset.py got a 404, 25 Sep 2026).
    import os
    import time
    client = api.app.test_client()
    text = "ᱡᱚᱦᱟᱨ ᱜᱩᱨᱩ"
    first = client.post("/speak", json={"text": text, "lang": "sat"}).get_json()
    assert client.get(first["audio_url"]).status_code == 200
    old = time.time() - config.AUDIO_KEEP_SECONDS - 3600
    for f in config.TTS_CACHE_DIR.glob("*.wav"):
        os.utime(f, (old, old))
    second = client.post("/speak", json={"text": text, "lang": "sat"}).get_json()
    assert second["tts_engine"] == "cache"
    assert client.get(second["audio_url"]).status_code == 200
