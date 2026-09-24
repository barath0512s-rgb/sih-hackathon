# app.py — REST API for the browser frontend (and, later, the tablet app)

import io
import re
import tempfile
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file
from flask_cors import CORS

import config
import database
from lesson_engine import LessonSession, get_all_lessons, get_lesson
from pipeline import TRANSLATION_CACHE, TTSError, VaaniSetuPipeline
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
    """Synthesise the translated line offline. Returns (audio_url, error)."""
    config.TTS_OUT_DIR.mkdir(exist_ok=True)
    aid = uuid.uuid4().hex
    out = config.TTS_OUT_DIR / f"{aid}.wav"
    try:
        if direction == "hi-to-sat":
            pl.santali_tts(text, str(out))
        else:
            pl.hindi_tts(text, str(out))
    except TTSError as e:
        out.unlink(missing_ok=True)
        return None, str(e)
    with _audio_lock:
        _latest[direction] = aid
        _prune_audio()
    return f"/audio/{aid}", None


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
_NMT_MODEL = {"engine": "IndicTrans2 indic-indic-dist-320M, PyTorch, "
                        f"{'greedy' if config.NMT_NUM_BEAMS == 1 else f'beam {config.NMT_NUM_BEAMS}'} decoding",
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
            "hi":  {"asr": _ASR_MODEL, "nmt": _NMT_MODEL, "tts": _tts_engine("hindi")},
            "sat": {"asr": _ASR_MODEL, "nmt": _NMT_MODEL, "tts": _tts_engine("santali")},
        },
        "online_dependencies": online,
        "tts_engine_counts": pl.tts_engine_counts,
        "tts_cache_files": sum(1 for _ in config.TTS_CACHE_DIR.glob("*.wav")) if config.TTS_CACHE_DIR.exists() else 0,
        "translation_cache_entries": len(TRANSLATION_CACHE),
        "active_sessions": len(sessions),
        # kept for older clients
        "asr_backend": pl.asr_backend,
        "nmt_loaded": hasattr(pl, "mdl_nmt"),
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


# ── Translation ───────────────────────────────────────────────────────────────
def _translation_json(r, audio_url, tts_error, latency):
    return {
        "translated_text": r["text"],
        # teacher | glossary | cached | model: which layer answered
        "source":          r["source"],
        # Raw mean token probability, only for "model". Not a quality estimate
        # (eval/model_score_sanity.py), so the UI does not show it.
        "model_score":     r["model_score"],
        "audio_url":       audio_url,
        "tts_error":       tts_error,
        "latency":         latency,
        # Deprecated, kept empty for older clients: there is no English pivot,
        # and there is no meaningful confidence number.
        "english_pivot":   "",
        "confidence":      None,
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
    t2 = time.time()
    audio_url, tts_error = _speak(direction, r["text"])
    t3 = time.time()

    _record(request.form.get("session_id", ""), direction, recognized, r["text"], round(t3 - t0, 2))
    out = _translation_json(r, audio_url, tts_error, {
        "asr": round(t1 - t0, 2), "nmt": round(t2 - t1, 2),
        "tts": round(t3 - t2, 2), "total": round(t3 - t0, 2)})
    out["recognized_text"] = recognized
    return jsonify(out)


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
    t1 = time.time()
    audio_url, tts_error = _speak(direction, r["text"])
    t2 = time.time()

    _record(data.get("session_id", ""), direction, text, r["text"], round(t2 - t0, 2))
    return jsonify(_translation_json(r, audio_url, tts_error, {
        "asr": 0.0, "nmt": round(t1 - t0, 2),
        "tts": round(t2 - t1, 2), "total": round(t2 - t0, 2)}))


@app.route("/translate/reverse", methods=["POST"])
def reverse():
    d = request.json or {}
    text = d.get("santali_text", "")
    if not text:
        return jsonify({"error": "No text"}), 400
    r = pl.translate(text, "sat-to-hi")
    return jsonify({"hindi_text": r["text"], "source": r["source"]})


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


# ── Worksheet and feedback ────────────────────────────────────────────────────
@app.route("/worksheet", methods=["POST"])
def worksheet():
    d = request.json or {}
    sess = _session(d.get("session_id", ""))
    lesson_steps = None
    if sess:
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
                       d.get("grade", "2"), d.get("topic", "Lesson"),
                       lesson_steps=lesson_steps, out=buf)
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


if __name__ == "__main__":
    print(f"\n{config.APP_NAME} server started on port {config.PORT}.")
    app.run(host=config.HOST, port=config.PORT, debug=False, threaded=True)
