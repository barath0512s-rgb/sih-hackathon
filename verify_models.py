# verify_models.py — does the pipeline actually work, end to end?
#
# Run this once inside the venv:
#     .\vaanisetu_env\Scripts\activate
#     python verify_models.py
#
# It loads the real models, exercises every stage, and writes verify_report.txt
# next to this file. Unlike test_pipeline.py it also checks that the TTS audio
# contains sound, not silence, which is how a stubbed-out TTS slipped through.

import io, os, sys, time, wave, contextlib, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(HERE, "verify_report.txt")
lines, failures = [], 0


def log(s=""):
    print(s)
    lines.append(s)


def check(name, fn):
    """Run one check. fn returns a detail string, or raises."""
    global failures
    t0 = time.time()
    try:
        detail = fn() or ""
        log(f"  PASS  {name}   ({time.time()-t0:.2f}s)  {detail}")
        return True
    except Exception as e:
        failures += 1
        log(f"  FAIL  {name}   ({time.time()-t0:.2f}s)")
        log(f"        {type(e).__name__}: {e}")
        for ln in traceback.format_exc().strip().splitlines()[-3:]:
            log(f"        {ln}")
        return False


def audio_is_silent(path):
    """True when every sample is zero, which is what a stubbed TTS writes."""
    try:
        import soundfile as sf
        import numpy as np
        data, sr = sf.read(path, dtype="float32")
        if data.size == 0:
            return True, 0.0, 0
        rms = float(np.sqrt(np.mean(np.square(data))))
        return rms < 1e-4, rms, len(data) / float(sr)
    except Exception:
        # mp3 or anything soundfile will not open: fall back to size
        return os.path.getsize(path) < 2000, -1.0, -1.0


log("=" * 68)
log("VaaniSetu model verification")
log(f"python {sys.version.split()[0]}   cwd {HERE}")
log("=" * 68)

# ── 1. dependencies ───────────────────────────────────────────────────────────
log("\n[1] Dependencies")
for mod, why in [("torch", "NMT runtime"), ("transformers", "NMT loader"),
                 ("IndicTransToolkit", "pre and post processing"),
                 ("gtts", "Santali speech"), ("soundfile", "audio io"),
                 ("flask", "server"), ("flask_cors", "browser access"),
                 ("reportlab", "worksheet pdf"), ("onnxruntime", "IndicConformer ASR")]:
    def _imp(m=mod):
        __import__(m)
        return ""
    check(f"import {mod:<18} ({why})", _imp)

def _ffmpeg():
    import subprocess
    subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, check=True)
    return "on PATH"
check("ffmpeg (browser webm to wav)", _ffmpeg)

# ── 2. model files on disk ────────────────────────────────────────────────────
log("\n[2] Model files")
def _dir(p, label):
    def f():
        full = os.path.join(HERE, p)
        if not os.path.isdir(full):
            raise FileNotFoundError(f"{p} is missing")
        n = sum(len(fs) for _, _, fs in os.walk(full))
        mb = sum(os.path.getsize(os.path.join(r, x))
                 for r, _, fs in os.walk(full) for x in fs) / 1e6
        return f"{n} files, {mb:.0f} MB"
    return f
check("models/indicconformer      (ASR)", _dir("models/indicconformer", "ASR"))
check("models/indictrans2-indic-indic (NMT)", _dir("models/indictrans2-indic-indic", "NMT"))
check("models/fonts              (worksheet)", _dir("models/fonts", "fonts"))

# ── 3. load the pipeline ──────────────────────────────────────────────────────
log("\n[3] Pipeline load  (first run downloads models, be patient)")
pl = None
def _load():
    global pl
    from pipeline import VaaniSetuPipeline
    pl = VaaniSetuPipeline()
    return f"ASR backend = {pl.asr_backend}"
if not check("VaaniSetuPipeline()", _load):
    log("\nCannot continue without the pipeline.")
    io.open(REPORT, "w", encoding="utf-8").write("\n".join(lines))
    sys.exit(1)

if pl.asr_backend != "indicconformer":
    log("  NOTE  ASR fell back to Whisper. Santali speech input will be poor.")
    log("        Expected models/indicconformer/model_onnx.py to exist.")

# ── 4. translation ────────────────────────────────────────────────────────────
log("\n[4] Translation")
state = {}
HINDI = "आज हम जोड़ना सीखेंगे। एक और एक मिलाओ।"

def _fwd():
    sat, pivot, conf = pl.hindi_to_santali(HINDI, "lesson_script")
    if not sat.strip():
        raise AssertionError("empty Santali output")
    ol = sum(1 for c in sat if "᱐" <= c <= "᱿")
    if ol == 0:
        raise AssertionError(f"no Ol Chiki characters in output: {sat!r}")
    state["sat"] = sat
    return f"conf {conf}  ->  {sat}"
check("Hindi to Santali", _fwd)

def _back():
    hi = pl.santali_to_hindi(state.get("sat", "ᱡᱚᱦᱟᱨ"))
    if not hi.strip():
        raise AssertionError("empty Hindi output")
    dev = sum(1 for c in hi if "ऀ" <= c <= "ॿ")
    if dev == 0:
        raise AssertionError(f"no Devanagari in output: {hi!r}")
    return f"-> {hi}"
check("Santali to Hindi", _back)

def _modes():
    outs = []
    for m in ("lesson_script", "activity_instruction", "assessment_prompt"):
        o, _, _ = pl.hindi_to_santali("यह क्या है?", m)
        if not o.strip():
            raise AssertionError(f"empty output for mode {m}")
        outs.append(m)
    return "all three modes answered"
check("All 3 lesson modes", _modes)

def _cached():
    t0 = time.time(); pl.hindi_to_santali(HINDI, "lesson_script")
    dt = time.time() - t0
    if dt > 0.15:
        raise AssertionError(f"second call took {dt:.2f}s, cache is not being hit")
    return f"repeat call {dt*1000:.0f} ms"
check("Translation cache", _cached)

# ── 5. speech out ─────────────────────────────────────────────────────────────
log("\n[5] Speech (this is what was stubbed out before)")

def _translit():
    latin = pl.transliterate_santali(state.get("sat", "ᱡᱚᱦᱟᱨ"))
    if not latin.strip():
        raise AssertionError("transliteration produced nothing")
    return f"'{state.get('sat','')[:18]}' -> '{latin[:34]}'"
check("Ol Chiki to Latin", _translit)

def _tts():
    out = os.path.join(HERE, "_verify_tts.wav")
    if os.path.exists(out):
        os.remove(out)
    pl.santali_tts(state.get("sat", "ᱡᱚᱦᱟᱨ"), out)
    if not os.path.exists(out):
        raise AssertionError("no audio file was written")
    silent, rms, secs = audio_is_silent(out)
    kb = os.path.getsize(out) // 1024
    if silent:
        raise AssertionError(
            f"the audio is silent ({kb} KB, rms {rms:.5f}). "
            "gTTS did not run. Check the internet connection, or that "
            "santali_tts was not replaced with a stub.")
    return f"{kb} KB, {secs:.1f}s, rms {rms:.3f}"
check("Santali speech is audible", _tts)

def _tts_cache():
    out = os.path.join(HERE, "_verify_tts2.wav")
    t0 = time.time(); pl.santali_tts(state.get("sat", "ᱡᱚᱦᱟᱨ"), out); dt = time.time() - t0
    if dt > 0.6:
        raise AssertionError(f"cached speech took {dt:.2f}s, the cache is not working")
    return f"cache hit in {dt*1000:.0f} ms"
check("Speech cache", _tts_cache)

# ── 6. lessons, grading, corrections, worksheet ───────────────────────────────
log("\n[6] Lessons, grading and storage")

def _lessons():
    from lesson_engine import get_all_lessons, get_lesson
    ls = get_all_lessons()
    if len(ls) < 5:
        raise AssertionError(f"expected 5 or more lessons, got {len(ls)}")
    if get_lesson("2", "addition") is None:
        raise AssertionError("grade 2 addition is missing")
    return f"{len(ls)} lessons"
check("Lesson engine", _lessons)

def _grading():
    from lesson_engine import get_lesson, LessonSession
    s = LessonSession(get_lesson("2", "addition"))
    s.step_idx = 4                      # the asking step, graded as step_idx-1
    got = [s.check_response("7"), s.check_response("१२३"), s.check_response("")]
    if got != ["green", "yellow", "red"]:
        raise AssertionError(f"expected green/yellow/red, got {got}")
    return "green, yellow and red all fire"
check("Comprehension grading", _grading)

def _db():
    import database
    database.init_db()
    key = "__verify__ " + str(int(time.time()))
    database.save_feedback(key, "ᱢᱚᱰᱮᱞ", False, "ᱴᱤᱪᱚᱨ")
    got = database.get_correction(key)
    if got != "ᱴᱤᱪᱚᱨ":
        raise AssertionError(f"correction not returned, got {got!r}")
    sat, pivot, conf = pl.hindi_to_santali(key, "lesson_script")
    if sat != "ᱴᱤᱪᱚᱨ":
        raise AssertionError(f"pipeline ignored the saved correction, returned {sat!r}")
    return "a saved correction overrides the model"
check("Correction database", _db)

def _ws():
    from worksheet import generate_worksheet
    out = os.path.join(HERE, "_verify_worksheet.pdf")
    p = generate_worksheet(HINDI, state.get("sat", "ᱡᱚᱦᱟᱨ"),
                           grade="2", topic="Addition", out=out)
    kb = os.path.getsize(p) // 1024
    if kb < 5:
        raise AssertionError(f"pdf is only {kb} KB")
    head = open(p, "rb").read(4)
    if head != b"%PDF":
        raise AssertionError("not a pdf")
    return f"{kb} KB"
check("Worksheet PDF", _ws)

# ── 7. full speech to speech, if a sample recording exists ────────────────────
log("\n[7] Speech in, speech out")
sample = next((os.path.join(HERE, f) for f in
               ("test_latin.wav", "test_bn.wav", "test_out.wav")
               if os.path.exists(os.path.join(HERE, f))), None)
if sample:
    def _full():
        r = pl.full_forward(sample, "lesson_script")
        if not r["hindi_text"].strip():
            raise AssertionError("ASR returned nothing")
        return (f"heard '{r['hindi_text'][:30]}' -> '{r['santali_text'][:26]}' "
                f"in {r['latency']['total']}s "
                f"(asr {r['latency']['asr']}, nmt {r['latency']['nmt']}, tts {r['latency']['tts']})")
    check(f"full_forward on {os.path.basename(sample)}", _full)
else:
    log("  SKIP  no sample wav in the folder to transcribe")

# ── summary ───────────────────────────────────────────────────────────────────
log("\n" + "=" * 68)
if failures:
    log(f"{failures} check(s) FAILED. Details above.")
else:
    log("Every check passed. Start the server with:  python app.py")
log("=" * 68)

for tmp in ("_verify_tts.wav", "_verify_tts2.wav", "_verify_worksheet.pdf"):
    with contextlib.suppress(Exception):
        os.remove(os.path.join(HERE, tmp))

io.open(REPORT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(f"\nReport written to {REPORT}")
sys.exit(1 if failures else 0)
