# app.py — full REST API for the Android frontend

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os, time, tempfile
from pipeline import VaaniSetuPipeline
from lesson_engine import get_all_lessons, get_lesson, LessonSession
from worksheet import generate_worksheet
import database

app      = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)
# /feedback writes to SQLite. pipeline.py also calls this on import, but the
# route must not depend on that side effect. init_db is idempotent.
database.init_db()
pl       = VaaniSetuPipeline()
sessions = {}

def _record(sid, direction, source_text, translated_text, latency):
    """Log a translation against an active lesson session.

    Feeds the worksheet's lesson-progression table and the session summary's
    average latency. Hindi/Santali are stored in fixed slots regardless of
    which way the translation ran.
    """
    sess = sessions.get(sid)
    if not sess:
        return
    if direction == "hi-to-sat":
        sess.record_translation(source_text, translated_text, latency)
    else:
        sess.record_translation(translated_text, source_text, latency)

@app.route("/")
def index():
    return send_file("frontend.html")

@app.route("/health/models")
def health_models():
    """What actually loaded, so a broken model is visible without reading logs."""
    import os
    ok_tts = False
    try:
        from gtts import gTTS  # noqa: F401
        ok_tts = True
    except Exception:
        pass
    return jsonify({
        "asr_backend": getattr(pl, "asr_backend", "unknown"),
        "nmt_loaded":  hasattr(pl, "mdl_nmt"),
        "tts_gtts_importable": ok_tts,
        "tts_cache_files": len([f for f in os.listdir("tts_cache")
                                if f.endswith(".wav")]) if os.path.isdir("tts_cache") else 0,
        "translation_cache_entries": len(__import__("pipeline").TRANSLATION_CACHE),
        "active_sessions": len(sessions),
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

    `steps` stays an integer for older clients; `plan` carries the step objects.
    """
    out = []
    for meta in get_all_lessons():
        lesson = get_lesson(meta["grade"], meta["topic"])
        item   = dict(meta)
        item["plan"] = lesson["steps"] if lesson else []
        out.append(item)
    return jsonify({"lessons": out})

@app.route("/session/start", methods=["POST"])
def session_start():
    d      = request.json or {}
    lesson = get_lesson(d.get("grade","2"), d.get("topic","addition"))
    if not lesson:
        return jsonify({"error": "Lesson not found"}), 404
    sid              = f"s_{int(time.time()*1000)}"
    sessions[sid]    = LessonSession(lesson)
    sess             = sessions[sid]
    return jsonify({
        "session_id":  sid,
        "title":       lesson["title"],
        "competency":  lesson["competency"],
        "total_steps": sess.total_steps,
        "step":        sess.current_step
    })

@app.route("/translate/audio", methods=["POST"])
def translate_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio"}), 400
    
    direction = request.form.get("direction", "hi-to-sat")
    mode = request.form.get("mode", "lesson_script")
    
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        request.files["audio"].save(tmp.name)
        tmp_path = tmp.name
        
    t0 = time.time()
    if direction == "hi-to-sat":
        recognized = pl.transcribe_hindi(tmp_path)
        t1 = time.time()
        translated, pivot, conf = pl.hindi_to_santali(recognized, mode)
        t2 = time.time()
        pl.santali_tts(translated, "output_santali.wav")
        t3 = time.time()
    else:
        # sat-to-hi
        recognized = pl.transcribe_santali(tmp_path)
        t1 = time.time()
        translated = pl.santali_to_hindi(recognized)
        t2 = time.time()
        pivot = ""
        conf = 0.0
        pl.hindi_tts(translated, "output_hindi.wav")
        t3 = time.time()

    os.unlink(tmp_path)

    _record(request.form.get("session_id", ""), direction,
            recognized, translated, round(t3 - t0, 2))

    return jsonify({
        "recognized_text": recognized,
        "translated_text": translated,
        "english_pivot":   pivot,
        "confidence":      conf,
        "audio_url":       _audio_url(direction),
        "latency": {
            "asr":   round(t1 - t0, 2),
            "nmt":   round(t2 - t1, 2),
            "tts":   round(t3 - t2, 2),
            "total": round(t3 - t0, 2)
        }
    })

@app.route("/translate/text", methods=["POST"])
def translate_text():
    data = request.json
    text = data.get("text", "")
    direction = data.get("direction", "hi-to-sat")
    mode = data.get("mode", "lesson_script")
    
    t0 = time.time()
    if direction == "hi-to-sat":
        translated, pivot, conf = pl.hindi_to_santali(text, mode)
        t1 = time.time()
        pl.santali_tts(translated, "output_santali.wav")
        t2 = time.time()
    else:
        translated = pl.santali_to_hindi(text)
        pivot = ""
        conf = 0.0
        t1 = time.time()
        pl.hindi_tts(translated, "output_hindi.wav")
        t2 = time.time()

    _record(data.get("session_id", ""), direction,
            text, translated, round(t2 - t0, 2))

    return jsonify({
        "translated_text": translated,
        "english_pivot":   pivot,
        "confidence":      conf,
        "audio_url":       _audio_url(direction),
        "latency": {
            "asr":   0.0,
            "nmt":   round(t1 - t0, 2),
            "tts":   round(t2 - t1, 2),
            "total": round(t2 - t0, 2)
        }
    })

def _audio_url(direction):
    """Which clip this request produced. Cache-busting is the caller's job."""
    return "/audio/output" if direction == "hi-to-sat" else "/audio/hindi"

@app.route("/audio/hindi")
def audio_hindi():
    return send_file("output_hindi.wav", mimetype="audio/wav")

@app.route("/audio/output")
def audio():
    return send_file("output_santali.wav", mimetype="audio/wav")

@app.route("/session/next", methods=["POST"])
def session_next():
    d   = request.json or {}
    sid = d.get("session_id","")
    if sid not in sessions:
        return jsonify({"error": "Session not found"}), 404
    sess = sessions[sid]
    sess.advance()
    step = sess.current_step
    if step is None:
        return jsonify({"completed": True, "session_id": sid})
    return jsonify({
        "completed":   False, "session_id": sid,
        "step_index":  sess.step_idx,
        "total_steps": sess.total_steps,
        "step":        step
    })

@app.route("/session/goto", methods=["POST"])
def session_goto():
    """Jump the session to a specific step index. The UI lists all the lines."""
    d   = request.json or {}
    sid = d.get("session_id","")
    if sid not in sessions:
        return jsonify({"error": "Session not found"}), 404
    sess = sessions[sid]
    try:
        sess.step_idx = max(0, min(int(d.get("step", 0)), sess.total_steps - 1))
    except (TypeError, ValueError):
        return jsonify({"error": "Bad step"}), 400
    return jsonify({"step_index": sess.step_idx,
                    "total_steps": sess.total_steps,
                    "step": sess.current_step})

@app.route("/session/response", methods=["POST"])
def session_response():
    d   = request.json or {}
    sid = d.get("session_id","")
    if sid not in sessions:
        return jsonify({"error": "Session not found"}), 404
    sess = sessions[sid]
    step = d.get("step")
    if step is not None:
        try:
            # check_response grades step_idx-1, so aim it at the step the
            # teacher is actually on
            sess.step_idx = max(0, min(int(step) + 1, sess.total_steps))
        except (TypeError, ValueError):
            pass
    signal = sess.check_response(d.get("response",""))
    msgs   = {
        "green":  "Correct — student understood",
        "yellow": "Partial — try again",
        "red":    "Incorrect — repeat the concept"
    }
    return jsonify({"signal": signal, "message": msgs[signal]})

@app.route("/session/summary", methods=["POST"])
def session_summary():
    d   = request.json or {}
    sid = d.get("session_id","")
    if sid not in sessions:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(sessions[sid].summary())

@app.route("/translate/reverse", methods=["POST"])
def reverse():
    d    = request.json or {}
    text = d.get("santali_text","")
    if not text:
        return jsonify({"error": "No text"}), 400
    return jsonify({"hindi_text": pl.santali_to_hindi(text)})

@app.route("/worksheet", methods=["POST"])
def worksheet():
    d   = request.json or {}
    sid = d.get("session_id","")
    lesson_steps = None
    if sid in sessions:
        sess = sessions[sid]
        lesson_steps = []
        for t in sess.translations:
            si = t["step"]
            if si < sess.total_steps:
                step_data = sess.lesson["steps"][si]
                lesson_steps.append({
                    "type":    step_data.get("type",""),
                    "hindi":   t["hindi"],
                    "santali": t["santali"],
                    "note":    step_data.get("note","")
                })
    path = generate_worksheet(
        d.get("hindi_text",""), d.get("santali_text",""),
        d.get("grade","2"), d.get("topic","Lesson"),
        lesson_steps=lesson_steps)
    return send_file(path, mimetype="application/pdf",
                     download_name="VaaniSetu_Worksheet.pdf")

@app.route("/feedback", methods=["POST"])
def save_feedback():
    """Endpoint for user to submit right/wrong feedback on translations."""
    data = request.json
    hindi = data.get("hindi_text")
    santali = data.get("santali_text")
    is_correct = data.get("is_correct", False)
    corrected_text = data.get("corrected_text", "")
    
    if hindi and santali:
        database.save_feedback(hindi, santali, is_correct, corrected_text)
        return jsonify({"status": "success", "message": "Feedback saved to database."})
    return jsonify({"error": "Missing text"}), 400

if __name__ == "__main__":
    print("\nVaaniSetu server started.")
    print("Get your IP: ifconfig (Mac/Linux) | ipconfig (Windows)")
    print("Update SERVER in MainActivity.kt with your IP")
    app.run(host="0.0.0.0", port=5000, debug=False)
