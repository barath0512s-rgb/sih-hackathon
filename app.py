# app.py — REST API for the browser frontend (and, later, the tablet app)

import io
import json
import re
import tempfile
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_file, stream_with_context
from flask_cors import CORS

import config
import curriculum
import database
import streaming
from education_glossary import lookup_hi_to_sat, lookup_sat_to_hi, lookup_word_hi_to_sat
from lesson_engine import LessonSession, get_all_lessons, get_lesson
from pipeline import TRANSLATION_CACHE, TTSError, VaaniSetuPipeline
from nipun import lakshya
from worksheet import generate_worksheet

# Only static/ is public. The project root used to be the static folder, which
# let anyone on the classroom Wi-Fi download the database and the source code.
app = Flask(__name__, static_folder=str(config.STATIC_DIR), static_url_path="/static")
CORS(app)
database.init_db()          # idempotent; also migrates older databases
pl = VaaniSetuPipeline()

DIRECTIONS = ("hi-to-sat", "sat-to-hi")


# ── Sessions ──────────────────────────────────────────────────────────────────
# The database is the source of truth; this dict only caches loaded sessions,
# so a restart loses nothing: an unknown id is reloaded from SQLite.
sessions = {}
_sessions_lock = threading.Lock()


def _session(sid):
    if not sid:
        return None
    with _sessions_lock:
        s = sessions.get(sid)
        if s is None:
            s = LessonSession.load(sid)
            if s is not None:
                sessions[sid] = s
        return s


def _record(sid, direction, source_text, translated_text, latency):
    """Log a translation against its lesson (feeds the worksheet and summary).
    Hindi and Santali go in fixed slots whichever way the translation ran."""
    sess = _session(sid)
    if not sess:
        return
    if direction == "hi-to-sat":
        sess.record_translation(source_text, translated_text, latency)
    else:
        sess.record_translation(translated_text, source_text, latency)


# ── Audio: one file per request ───────────────────────────────────────────────
# Every clip gets its own id, so two tablets never overwrite each other's audio
# and the browser can never play the previous sentence by mistake.
_AUDIO_ID = re.compile(r"^[0-9a-f]{32}$")
_latest = {}                     # direction -> newest clip id (deprecated aliases)
_audio_lock = threading.Lock()


def _prune_audio():
    """Keep clips for config.AUDIO_KEEP_SECONDS, and at most AUDIO_KEEP_MAX."""
    files = sorted(config.TTS_OUT_DIR.glob("*.wav"), key=lambda p: p.stat().st_mtime)
    cutoff = time.time() - config.AUDIO_KEEP_SECONDS
    for i, p in enumerate(files):
        if p.stat().st_mtime < cutoff or i < len(files) - config.AUDIO_KEEP_MAX:
            p.unlink(missing_ok=True)


def _speak(direction, text):
    """Synthesise the translated line offline.
    Returns (audio_url, error, tts_engine) where tts_engine is piper|cache|gtts|none."""
    config.TTS_OUT_DIR.mkdir(exist_ok=True)
    aid = uuid.uuid4().hex
    out = config.TTS_OUT_DIR / f"{aid}.wav"
    info = {}
    try:
        if direction == "hi-to-sat":
            pl.santali_tts(text, str(out), info=info)
        else:
            pl.hindi_tts(text, str(out), info=info)
    except TTSError as e:
        out.unlink(missing_ok=True)
        app.logger.error("TTS failed (%s): %s | text: %.60s", direction, e, text)
        return None, str(e), "none"
    with _audio_lock:
        _latest[direction] = aid
        _prune_audio()
    return f"/audio/{aid}", None, info.get("tts_engine", "none")


@app.route("/audio/<aid>")
def audio_clip(aid):
    if not _AUDIO_ID.match(aid):
        abort(404)
    p = config.TTS_OUT_DIR / f"{aid}.wav"
    if not p.exists():
        abort(404)
    return send_file(p, mimetype="audio/wav")


def _latest_clip(direction):
    aid = _latest.get(direction)
    if not aid:
        abort(404)
    return audio_clip(aid)


@app.route("/audio/output")
def audio_output():
    """Deprecated: the newest Santali clip. Use the audio_url in the response."""
    return _latest_clip("hi-to-sat")


@app.route("/audio/hindi")
def audio_hindi():
    """Deprecated: the newest Hindi clip. Use the audio_url in the response."""
    return _latest_clip("sat-to-hi")


# ── Pages and status ──────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_file(config.BASE_DIR / "frontend.html")


@app.route("/config")
def client_config():
    """Product name for the UI, so a rename is one edit in config.py."""
    return jsonify({"app_name": config.APP_NAME,
                    "app_name_local": config.APP_NAME_LOCAL})


def _size(path):
    p = Path(path)
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file() and ".cache" not in f.parts)


# Model files on disk, measured once at start.
_ASR_MODEL = {"engine": "IndicConformer 600M multilingual, ONNX, RNN-T decoding",
              "path": str(config.ASR_DIR), "bytes": _size(config.ASR_DIR)}
def _nmt_model():
    """What actually translates: ONNX Runtime (Phase L) or PyTorch."""
    dec = "greedy" if config.NMT_NUM_BEAMS == 1 else f"beam {config.NMT_NUM_BEAMS}"
    if pl.onnx_nmt is not None:
        import nmt_onnx
        sfx = ".int8.onnx" if pl.nmt_backend == "onnx-int8" else ".onnx"
        files = [nmt_onnx.ONNX_DIR / f"{n}{sfx}" for n in ("encoder", "decoder_init", "decoder_step")]
        return {"engine": f"IndicTrans2 indic-indic-dist-320M, ONNX Runtime {pl.nmt_backend.split('-')[1]}, "
                          f"{config.NMT_THREADS} threads, {dec} decoding",
                "path": str(nmt_onnx.ONNX_DIR), "bytes": sum(_size(f) for f in files)}
    return {"engine": f"IndicTrans2 indic-indic-dist-320M, PyTorch, {dec} decoding",
            "path": str(config.NMT_DIR / "model.safetensors"),
            "bytes": _size(config.NMT_DIR / "model.safetensors")}


def _tts_engine(lang):
    model = pl._voice_model(lang)
    path = config.PIPER_DIR / f"{model}.onnx"
    via = ""
    if lang == "santali":
        via = f", reading Ol Chiki transliterated to {config.SANTALI_TTS_SCRIPT.title()}"
    return {"engine": f"Piper {model}{via}", "path": str(path),
            "bytes": path.stat().st_size if path.exists() else 0,
            "loaded": pl._voices.get(model) is not None}


@app.route("/health/models")
def health_models():
    """What actually runs for each language, and whether anything needs the network."""
    online = ["gTTS (Google Text-to-Speech), used only if Piper fails"] if config.ALLOW_ONLINE_TTS else []
    return jsonify({
        "languages": {
            "hi":  {"asr": _ASR_MODEL, "nmt": _nmt_model(), "tts": _tts_engine("hindi")},
            "sat": {"asr": _ASR_MODEL, "nmt": _nmt_model(), "tts": _tts_engine("santali")},
        },
        "online_dependencies": online,
        "tts_engine_counts": pl.tts_engine_counts,
        "tts_cache_files": sum(1 for _ in config.TTS_CACHE_DIR.glob("*.wav")) if config.TTS_CACHE_DIR.exists() else 0,
        "translation_cache_entries": len(TRANSLATION_CACHE),
        "active_sessions": len(sessions),
        # kept for older clients
        "asr_backend": pl.asr_backend,
        "nmt_loaded": pl.onnx_nmt is not None or pl._mdl_nmt is not None,
        "nmt_backend": pl.nmt_backend,
    })


@app.route("/health")
def health():
    try:
        import torch
        device = "GPU" if torch.cuda.is_available() else "CPU"
    except Exception:
        device = "CPU"
    return jsonify({"status": "ok", "device": device})


@app.route("/lessons")
def lessons():
    """Lesson list with every step inlined, so the UI can show the whole plan.
    `steps` stays an integer for older clients; `plan` carries the step objects."""
    out = []
    for meta in get_all_lessons():
        lesson = get_lesson(meta["grade"], meta["topic"])
        item = dict(meta)
        item["plan"] = lesson["steps"] if lesson else []
        out.append(item)
    return jsonify({"lessons": out})


@app.route("/flashcards")
def flashcards():
    """Flashcard decks made from the lessons: GET /flashcards?grade=2&topic=addition.
    Both filters are optional. Each card's Santali comes from, in order: a
    teacher's correction, the glossary word list (a card is one word or a short
    phrase, which the sentence glossary does not hold), then the translation
    layers (cached, model). `source` says which one answered, and
    `review_status` says whether a native speaker has checked it."""
    grade, topic = request.args.get("grade"), request.args.get("topic")
    decks = []
    for meta in get_all_lessons():
        if grade and meta["grade"] != str(grade):
            continue
        if topic and meta["topic"] != topic:
            continue
        lesson = get_lesson(meta["grade"], meta["topic"])
        cards = []
        for c in lesson.get("flashcards", []):
            cards.append({"hi": c["hi"], "emoji": c.get("emoji", ""), "n": c.get("n"),
                          **_card_santali(c["hi"])})
        decks.append({"grade": meta["grade"], "topic": meta["topic"],
                      "title": meta["title"], "lakshya_ids": meta["lakshya_ids"],
                      "lakshya": meta["lakshya"], "cards": cards})
    if (grade or topic) and not decks:
        return jsonify({"error": "No lesson matches that grade and topic"}), 404
    return jsonify({"decks": decks})


def _card_santali(hi):
    fixed = database.get_correction(hi, "hi-to-sat")
    if fixed:
        return {"sat": fixed, "source": "teacher", "review_status": "teacher_verified"}
    word = lookup_word_hi_to_sat(hi)
    if word:
        # Not "glossary": that badge reads "verified", and the word lists are not.
        return {"sat": word[0], "source": "wordlist", "review_status": "pending_native_review"}
    r = pl.translate(hi, "hi-to-sat", "lesson_script")
    # The model ends even one word with a full stop (᱾); a card has none.
    return {"sat": r["text"].strip().rstrip("᱾।.").strip(), "source": r["source"],
            "review_status": "unreviewed_model_output"}


@app.route("/speak", methods=["POST"])
def speak():
    """Speak a given line as it is, without translating it: {text, lang: "sat"|"hi"}.
    Flashcards use it so the voice says the word printed on the card."""
    d = request.json or {}
    text, lang = (d.get("text") or "").strip(), d.get("lang", "sat")
    if not text or lang not in ("sat", "hi"):
        return jsonify({"error": "text and lang (sat or hi) are required"}), 400
    audio_url, tts_error, tts_engine = _speak("hi-to-sat" if lang == "sat" else "sat-to-hi", text)
    return jsonify({"audio_url": audio_url, "tts_error": tts_error, "tts_engine": tts_engine})


# ── Translation ───────────────────────────────────────────────────────────────
def _model_versions():
    return {"asr": config.ASR_REVISION[:10], "nmt": config.NMT_REVISION[:10],
            "nmt_beams": config.NMT_NUM_BEAMS, "nmt_engine": pl.nmt_backend,
            "tts_hindi": pl._voice_model("hindi"), "tts_santali": pl._voice_model("santali"),
            "santali_script": config.SANTALI_TTS_SCRIPT}


def _log(rid, device_id, direction, input_type, r, tts_engine, lat, tts_error=None, chunks=None):
    """One latency_log row; the client later adds what the user actually waited.
    A failed clip is recorded here too, with the reason."""
    database.log_latency(
        rid, device_id=device_id or None, direction=direction, input_type=input_type,
        source=r["source"], tts_engine=tts_engine,
        asr_ms=lat["asr"] * 1000, nmt_ms=lat["nmt"] * 1000, tts_ms=lat["tts"] * 1000,
        server_ms=lat["total"] * 1000, model_versions=_model_versions(), tts_error=tts_error,
        chunks=chunks)


def _nearest(r, source_text, direction):
    """The nearest verified sentence, only for a translation that needs review."""
    if not r.get("needs_review"):
        return None
    from education_glossary import nearest_verified
    return nearest_verified(source_text, direction)


def _translation_json(r, audio_url, tts_error, latency, rid=None, tts_engine=None):
    return {
        # Send back with POST /metrics/client once the audio is playing.
        "request_id":      rid,
        "translated_text": r["text"],
        # teacher | glossary | cached | model: which layer answered
        "source":          r["source"],
        # Raw mean token probability, only for "model". Not a quality estimate
        # (eval/model_score_sanity.py), so the UI does not show it.
        "model_score":     r["model_score"],
        "audio_url":       audio_url,
        "tts_error":       tts_error,
        "tts_engine":      tts_engine,          # piper | cache | gtts | none
        "latency":         latency,
        # Deprecated, kept empty for older clients: there is no English pivot,
        # and there is no meaningful confidence number.
        "english_pivot":   "",
        "confidence":      None,
        # A loop was cut or found in the model's output: the page shows "check
        # with a native speaker", does not auto-play, and offers the nearest
        # verified sentence (nmt_guard.py).
        "needs_review":    bool(r.get("needs_review")),
        "nearest_verified": r.get("nearest_verified"),
    }


@app.route("/translate/audio", methods=["POST"])
def translate_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio"}), 400
    direction = request.form.get("direction", "hi-to-sat")
    if direction not in DIRECTIONS:
        return jsonify({"error": f"direction must be one of {DIRECTIONS}"}), 400
    mode = request.form.get("mode", "lesson_script")

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        request.files["audio"].save(tmp.name)
        tmp_path = Path(tmp.name)
    t0 = time.time()
    try:
        if direction == "hi-to-sat":
            recognized = pl.transcribe_hindi(str(tmp_path))
        else:
            recognized = pl.transcribe_santali(str(tmp_path))
    finally:
        tmp_path.unlink(missing_ok=True)
        Path(str(tmp_path) + "_converted.wav").unlink(missing_ok=True)
    t1 = time.time()
    r = pl.translate(recognized, direction, mode)
    r = dict(r, nearest_verified=_nearest(r, recognized, direction))
    t2 = time.time()
    audio_url, tts_error, tts_engine = _speak(direction, r["text"])
    t3 = time.time()

    _record(request.form.get("session_id", ""), direction, recognized, r["text"], round(t3 - t0, 2))
    lat = {"asr": round(t1 - t0, 3), "nmt": round(t2 - t1, 3),
           "tts": round(t3 - t2, 3), "total": round(t3 - t0, 3)}
    rid = uuid.uuid4().hex
    _log(rid, request.form.get("device_id"), direction, "voice", r, tts_engine, lat, tts_error)
    out = _translation_json(r, audio_url, tts_error, lat, rid, tts_engine)
    out["recognized_text"] = recognized
    return jsonify(out)


def _stream_parts(text, direction):
    """How a recognised utterance is spoken (Phase L2). Whole: a short line,
    Santali input (no Santali splitter yet), or a line a teacher corrected or
    the glossary knows. Otherwise clause chunks (streaming.py)."""
    if direction != "hi-to-sat" or len(text.split()) < config.STREAM_MIN_WORDS:
        return [text]
    if database.get_correction(text, direction) or (lookup_hi_to_sat if direction == "hi-to-sat"
                                                     else lookup_sat_to_hi)(text):
        return [text]
    return streaming.chunks(text) or [text]


@app.route("/translate/audio_stream", methods=["POST"])
def translate_audio_stream():
    """Like /translate/audio, but a long utterance is translated and spoken
    chunk by chunk (Phase L2). The reply is NDJSON, one line per event:
      {"type":"asr", "recognized_text", "chunks"}
      {"type":"chunk", "i", "source_text", "translated_text", "source",
       "audio_url", "tts_error", "tts_engine", "ms"}           (ms since the audio arrived)
      {"type":"done", "request_id", "translated_text", "latency"}
    The first chunk's audio can play while the rest are still being made."""
    if "audio" not in request.files:
        return jsonify({"error": "No audio"}), 400
    direction = request.form.get("direction", "hi-to-sat")
    if direction not in DIRECTIONS:
        return jsonify({"error": f"direction must be one of {DIRECTIONS}"}), 400
    mode = request.form.get("mode", "lesson_script")
    sid, device = request.form.get("session_id", ""), request.form.get("device_id")
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        request.files["audio"].save(tmp.name)
        tmp_path = Path(tmp.name)

    def events():
        t0 = time.time()
        try:
            recognized = (pl.transcribe_hindi if direction == "hi-to-sat" else pl.transcribe_santali)(str(tmp_path))
        finally:
            tmp_path.unlink(missing_ok=True)
            Path(str(tmp_path) + "_converted.wav").unlink(missing_ok=True)
        t1 = time.time()
        parts = _stream_parts(recognized, direction)
        yield json.dumps({"type": "asr", "recognized_text": recognized, "chunks": len(parts)},
                         ensure_ascii=False) + "\n"
        outs, nmt_s, tts_s, sources, engines, errors = [], 0.0, 0.0, [], [], []
        for i, part in enumerate(parts):
            a = time.time()
            r = pl.translate(part, direction, mode)
            b = time.time()
            audio_url, tts_error, tts_engine = _speak(direction, r["text"])
            c = time.time()
            nmt_s += b - a; tts_s += c - b
            outs.append(r["text"]); sources.append(r["source"]); engines.append(tts_engine)
            if tts_error:
                errors.append(tts_error)
            yield json.dumps({"type": "chunk", "i": i, "source_text": part, "translated_text": r["text"],
                              "source": r["source"], "audio_url": audio_url, "tts_error": tts_error,
                              "tts_engine": tts_engine, "ms": round((c - t0) * 1000),
                              "needs_review": bool(r.get("needs_review")),
                              "nearest_verified": _nearest(r, part, direction)},
                             ensure_ascii=False) + "\n"
        whole = " ".join(outs)
        lat = {"asr": round(t1 - t0, 3), "nmt": round(nmt_s, 3), "tts": round(tts_s, 3),
               "total": round(time.time() - t0, 3)}
        rid = uuid.uuid4().hex
        src = sources[0] if len(set(sources)) == 1 else "model"
        _record(sid, direction, recognized if direction == "hi-to-sat" else whole,
                whole if direction == "hi-to-sat" else recognized, lat["total"])
        _log(rid, device, direction, "voice-stream" if len(parts) > 1 else "voice",
             {"source": src}, engines[0] if len(set(engines)) == 1 else "piper", lat,
             "; ".join(errors) or None, chunks=len(parts))
        yield json.dumps({"type": "done", "request_id": rid, "translated_text": whole, "source": src,
                          "latency": lat}, ensure_ascii=False) + "\n"

    return Response(stream_with_context(events()), mimetype="application/x-ndjson")


@app.route("/translate/text", methods=["POST"])
def translate_text():
    data = request.json or {}
    text = data.get("text", "")
    direction = data.get("direction", "hi-to-sat")
    if direction not in DIRECTIONS:
        return jsonify({"error": f"direction must be one of {DIRECTIONS}"}), 400
    mode = data.get("mode", "lesson_script")

    t0 = time.time()
    r = pl.translate(text, direction, mode)
    r = dict(r, nearest_verified=_nearest(r, text, direction))
    t1 = time.time()
    audio_url, tts_error, tts_engine = _speak(direction, r["text"])
    t2 = time.time()

    _record(data.get("session_id", ""), direction, text, r["text"], round(t2 - t0, 2))
    lat = {"asr": 0.0, "nmt": round(t1 - t0, 3),
           "tts": round(t2 - t1, 3), "total": round(t2 - t0, 3)}
    rid = uuid.uuid4().hex
    _log(rid, data.get("device_id"), direction, "typed", r, tts_engine, lat, tts_error)
    return jsonify(_translation_json(r, audio_url, tts_error, lat, rid, tts_engine))


@app.route("/translate/reverse", methods=["POST"])
def reverse():
    d = request.json or {}
    text = d.get("santali_text", "")
    if not text:
        return jsonify({"error": "No text"}), 400
    r = pl.translate(text, "sat-to-hi")
    return jsonify({"hindi_text": r["text"], "source": r["source"]})


# ── Latency metrics ───────────────────────────────────────────────────────────
@app.route("/metrics/client", methods=["POST"])
def metrics_client():
    """The browser reports what the user actually waited for one request.
    {request_id, client_total_ms (input end -> audio playing),
     response_ms (input end -> response received)}"""
    d = request.json or {}
    try:
        total, resp = float(d["client_total_ms"]), float(d["response_ms"])
        last = float(d["client_last_ms"]) if d.get("client_last_ms") is not None else None
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "request_id, client_total_ms and response_ms are required"}), 400
    if not (0 <= resp <= total < 10 * 60 * 1000) or (last is not None and not total <= last < 10 * 60 * 1000):
        return jsonify({"error": "timings out of range"}), 400
    if not database.report_client_timing(d.get("request_id", ""), total, resp, last):
        return jsonify({"error": "unknown request_id"}), 404
    return jsonify({"status": "ok"})


@app.route("/metrics/latency")
def metrics_latency():
    """Count, median, p90 and max per path (voice/typed, direction, cached/computed)."""
    return jsonify({"paths": database.latency_summary(),
                    "model_versions": _model_versions()})


# ── Lesson sessions ───────────────────────────────────────────────────────────
@app.route("/session/start", methods=["POST"])
def session_start():
    d = request.json or {}
    grade, topic = str(d.get("grade", "2")), d.get("topic", "addition")
    lesson = get_lesson(grade, topic)
    if not lesson:
        return jsonify({"error": "Lesson not found"}), 404
    sid = uuid.uuid4().hex
    sess = LessonSession(lesson, sid=sid, grade_=grade, topic=topic)
    with _sessions_lock:
        sessions[sid] = sess
    return jsonify({
        "session_id":  sid,
        "title":       lesson["title"],
        "competency":  lesson["competency"],
        "lakshya_ids": lesson["lakshya_ids"],
        "total_steps": sess.total_steps,
        "step":        sess.current_step,
    })


@app.route("/session/next", methods=["POST"])
def session_next():
    d = request.json or {}
    sid = d.get("session_id", "")
    sess = _session(sid)
    if sess is None:
        return jsonify({"error": "Session not found"}), 404
    sess.advance()
    if sess.current_step is None:
        return jsonify({"completed": True, "session_id": sid})
    return jsonify({"completed": False, "session_id": sid,
                    "step_index": sess.step_idx, "total_steps": sess.total_steps,
                    "step": sess.current_step})


@app.route("/session/goto", methods=["POST"])
def session_goto():
    """Jump the session to a specific step index. The UI lists all the lines."""
    d = request.json or {}
    sess = _session(d.get("session_id", ""))
    if sess is None:
        return jsonify({"error": "Session not found"}), 404
    try:
        sess.goto(d.get("step", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Bad step"}), 400
    return jsonify({"step_index": sess.step_idx, "total_steps": sess.total_steps,
                    "step": sess.current_step})


_SIGNAL_MESSAGES = {
    "green":  "Correct — student understood",
    "yellow": "Partial — try again",
    "red":    "Incorrect — repeat the concept",
}


@app.route("/session/response", methods=["POST"])
def session_response():
    """Grade a child's answer to one step.

    JSON:      {session_id, step, response}
    multipart: session_id, step, audio, lang ("sat" default, or "hi") —
               the spoken answer is transcribed, then graded.
    The step is required and graded as given.
    """
    voice = "audio" in request.files
    d = request.form if voice else (request.json or {})
    sess = _session(d.get("session_id", ""))
    if sess is None:
        return jsonify({"error": "Session not found"}), 404
    try:
        step = int(d["step"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "step is required: the index of the step being answered"}), 400
    if not 0 <= step < sess.total_steps:
        return jsonify({"error": f"step must be between 0 and {sess.total_steps - 1}"}), 400

    transcript = None
    if voice:
        lang = d.get("lang", "sat")
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            request.files["audio"].save(tmp.name)
            tmp_path = Path(tmp.name)
        try:
            transcript = (pl.transcribe_santali if lang == "sat" else pl.transcribe_hindi)(str(tmp_path))
        finally:
            tmp_path.unlink(missing_ok=True)
            Path(str(tmp_path) + "_converted.wav").unlink(missing_ok=True)
        answer = transcript
    else:
        answer = d.get("response", "")

    signal = sess.check_response(answer, step)
    out = {"signal": signal, "message": _SIGNAL_MESSAGES[signal], "step": step}
    if transcript is not None:
        out["transcript"] = transcript
    return jsonify(out)


@app.route("/session/summary", methods=["POST"])
def session_summary():
    d = request.json or {}
    sess = _session(d.get("session_id", ""))
    if sess is None:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(sess.summary())


# ── Curriculum import (work package 14) ───────────────────────────────────────
# Two steps, so the teacher stays in charge:
#   POST /curriculum/import  text or a file -> drafts: lines with suggested
#                            labels and suggested NIPUN goals. Nothing is stored.
#   POST /curriculum/save    the draft as the teacher corrected it, with the goals
#                            confirmed -> Santali for every line, audio for every
#                            line, a flashcard deck and a worksheet; stored in SQLite.
_import_lock = threading.Lock()


def _curriculum_error(e):
    return jsonify({"error": str(e), "code": e.code, "params": e.params}), 400


@app.route("/curriculum/import", methods=["POST"])
def curriculum_import():
    try:
        if "file" in request.files:
            f = request.files["file"]
            items = curriculum.parse_upload(filename=f.filename, data=f.read(),
                                            grade=request.form.get("grade"),
                                            title=request.form.get("title"))
        else:
            d = request.json or request.form
            items = curriculum.parse_upload(text=d.get("text"), grade=d.get("grade"),
                                            title=d.get("title"))
    except curriculum.CurriculumError as e:
        return _curriculum_error(e)
    return jsonify({
        "lessons": [curriculum.draft(i) for i in items],
        "types": list(curriculum.TYPES),
        "lakshyas": [{"id": k, **v} for k, v in lakshya.LAKSHYAS.items()],
        "lakshya_source": lakshya.SOURCE,
    })


def _lesson_audio(topic, i):
    return config.LESSON_AUDIO_DIR / topic / f"{i}.wav"


@app.route("/curriculum/save", methods=["POST"])
def curriculum_save():
    try:
        return jsonify(save_lesson(request.json or {}))
    except curriculum.CurriculumError as e:
        return _curriculum_error(e)


def save_lesson(body):
    """Validate a teacher-confirmed draft, add Santali and audio to every line,
    store it. Raises curriculum.CurriculumError if the draft is not usable."""
    grade, title, lines, ids = curriculum.validate(body)
    lesson = curriculum.build_lesson(grade, title, lines, ids)
    topic = "imp_" + uuid.uuid4().hex[:10]
    (config.LESSON_AUDIO_DIR / topic).mkdir(parents=True, exist_ok=True)
    audio_errors = 0
    with _import_lock:
        for i, step in enumerate(lesson["steps"]):
            r = pl.translate(step["hindi"], "hi-to-sat", step["type"])
            step["santali"] = r["text"]
            step["source"] = r["source"]
            # Every Santali line waits for a native speaker, whatever produced it.
            step["review_status"] = ("teacher_verified" if r["source"] == "teacher"
                                     else "pending_native_review")
            try:
                pl.santali_tts(r["text"], str(_lesson_audio(topic, i)))
                step["audio_url"] = f"/lesson_audio/{topic}/{i}"
            except TTSError as e:
                app.logger.error("Lesson audio failed (%s step %d): %s", topic, i, e)
                step["audio_url"], step["audio_error"] = None, str(e)
                audio_errors += 1
            key = step.get("accept_answers")
            if key:
                for answer in key["hi"]:
                    card = _card_santali(answer)
                    if card["sat"] and card["sat"] not in key["sat"]:
                        key["sat"].append(card["sat"])
                        key["sat_sources"][card["sat"]] = card["source"]
        database.save_imported_lesson(topic, grade, lesson)
    return {
        "grade": grade, "topic": topic, "title": title,
        "lakshya_ids": lesson["lakshya_ids"], "domain": lesson["domain"],
        "review_status": lesson["review_status"],
        "steps": lesson["steps"], "audio_errors": audio_errors,
        "flashcards_url": f"/flashcards?grade={grade}&topic={topic}",
        "worksheet_url": f"/curriculum/{topic}/worksheet",
    }


def seed_team_lessons(path=None, log=print):
    """Add every lesson in content/team_lessons.json that the database does not
    have yet (matched on grade and title), through the same path as a teacher's
    import. Safe to call on every start: when all are there it does nothing."""
    import json
    path = path or config.TEAM_LESSONS_FILE
    if not path.exists():
        return 0
    have = {(m["grade"], m["title"]) for m in get_all_lessons() if m["imported"]}
    todo = [L for L in json.loads(path.read_text(encoding="utf-8"))["lessons"]
            if (L["grade"], L["title"]) not in have]
    if todo:
        log(f"  Adding {len(todo)} lessons from {path.name} (first start only)…")
    for L in todo:
        body, _ = curriculum.team_body(L)
        r = save_lesson(body)
        log(f"    {r['title']}: {len(r['steps'])} lines, {r['audio_errors']} audio errors")
    return len(todo)


@app.route("/curriculum")
def curriculum_list():
    return jsonify({"lessons": [m for m in get_all_lessons() if m["imported"]]})


@app.route("/lesson_audio/<topic>/<int:i>")
def lesson_audio(topic, i):
    if not re.fullmatch(r"imp_[0-9a-f]{10}", topic):
        abort(404)
    path = _lesson_audio(topic, i)
    if not path.exists():
        abort(404)
    return send_file(path, mimetype="audio/wav")


def _find_imported(topic):
    for m in get_all_lessons():
        if m["topic"] == topic and m["imported"]:
            return m["grade"], get_lesson(m["grade"], topic)
    return None, None


@app.route("/curriculum/<topic>/worksheet")
def curriculum_worksheet(topic):
    grade, lesson = _find_imported(topic)
    if not lesson:
        abort(404)
    steps = [{"type": s["type"], "hindi": s["hindi"], "santali": s.get("santali", ""),
              "note": s.get("note", "")} for s in lesson["steps"]]
    first = steps[0]
    buf = io.BytesIO()
    generate_worksheet(first["hindi"], first["santali"],
                       "Balvatika" if grade == "0" else grade, lesson["title"],
                       lesson_steps=steps, out=buf, lakshya_ids=lesson["lakshya_ids"])
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf",
                     download_name=f"{config.APP_NAME}_{topic}_Worksheet.pdf")


# ── Worksheet and feedback ────────────────────────────────────────────────────
@app.route("/worksheet", methods=["POST"])
def worksheet():
    d = request.json or {}
    sess = _session(d.get("session_id", ""))
    lesson_steps = None
    lakshya_ids = None
    if sess:
        lakshya_ids = sess.lesson.get("lakshya_ids")
        lesson_steps = []
        for t in sess.translations:
            si = t["step"]
            if si < sess.total_steps:
                step_data = sess.lesson["steps"][si]
                lesson_steps.append({"type": step_data.get("type", ""),
                                     "hindi": t["hindi"], "santali": t["santali"],
                                     "note": step_data.get("note", "")})
    # Rendered in memory: a shared output file let concurrent requests collide.
    buf = io.BytesIO()
    generate_worksheet(d.get("hindi_text", ""), d.get("santali_text", ""),
                       d.get("grade", "2"), d.get("topic", ""),
                       lesson_steps=lesson_steps, out=buf, lakshya_ids=lakshya_ids)
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf",
                     download_name=f"{config.APP_NAME}_Worksheet.pdf")


@app.route("/feedback", methods=["POST"])
def save_feedback():
    """A thumbs-up, thumbs-down or correction on a translation.

    {hindi_text, santali_text, is_correct, corrected_text, direction}
    direction defaults to hi-to-sat; corrected_text is in the target language.
    """
    data = request.json or {}
    hindi, santali = data.get("hindi_text"), data.get("santali_text")
    direction = data.get("direction", "hi-to-sat")
    if direction not in DIRECTIONS:
        return jsonify({"error": f"direction must be one of {DIRECTIONS}"}), 400
    if not (hindi and santali):
        return jsonify({"error": "Missing text"}), 400
    corrected = (data.get("corrected_text") or "").strip()
    is_correct = bool(data.get("is_correct", False))
    database.save_feedback(hindi, santali, is_correct, corrected, direction)
    reused = bool(corrected) or is_correct
    return jsonify({"status": "success", "reused": reused,
                    "message": "Your correction will be reused for this sentence." if corrected else
                               "Saved. This translation will be reused." if is_correct else
                               "Saved."})


@app.route("/hub-ca.crt")
def hub_ca():
    """The laptop hub's CA certificate (public), for installing on a tablet so
    https://<laptop-ip>:5443 opens without a warning. See tools/make_cert.py."""
    ca = config.CERT_DIR / "hub-ca.crt"
    if not ca.exists():
        abort(404)
    return send_file(ca, mimetype="application/x-x509-ca-cert",
                     download_name=f"{config.APP_NAME}-hub-ca.crt")


@app.route("/pack/latest")
def pack_latest():
    """The newest content pack (tools/build_content_pack.py writes dist/packs/),
    for the Android app's "From the hub" import. 404 until one is built."""
    packs = sorted((config.BASE_DIR / "dist" / "packs").glob("content-pack-*.zip"))
    if not packs:
        abort(404)
    return send_file(packs[-1], mimetype="application/zip", download_name=packs[-1].name)


if __name__ == "__main__":
    import sys
    seed_team_lessons()
    if "--https" in sys.argv:
        # Laptop hub for tablets on the same Wi-Fi: the microphone needs https.
        from tools.make_cert import make_server_cert
        ips = make_server_cert(config.CERT_DIR)
        print(f"\n{config.APP_NAME} laptop hub (HTTPS) on port {config.HTTPS_PORT}.")
        for ip in ips:
            if ip != "127.0.0.1":
                print(f"  On the tablet, open: https://{ip}:{config.HTTPS_PORT}")
        app.run(host=config.HOST, port=config.HTTPS_PORT, debug=False, threaded=True,
                ssl_context=(str(config.CERT_DIR / "hub.crt"), str(config.CERT_DIR / "hub.key")))
    else:
        print(f"\n{config.APP_NAME} server started on port {config.PORT}.")
        app.run(host=config.HOST, port=config.PORT, debug=False, threaded=True)
