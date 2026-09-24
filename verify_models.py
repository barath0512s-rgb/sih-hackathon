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
import config
log(f"{config.APP_NAME} model verification")
log(f"python {sys.version.split()[0]}   cwd {HERE}")
log("=" * 68)

# ── 1. dependencies ───────────────────────────────────────────────────────────
log("\n[1] Dependencies")
_deps = [("torch", "NMT runtime"), ("transformers", "NMT loader"),
         ("IndicTransToolkit", "pre and post processing"),
         ("piper", "offline speech"), ("soundfile", "audio io"),
         ("flask", "server"), ("flask_cors", "browser access"),
         ("reportlab", "worksheet pdf"), ("onnxruntime", "IndicConformer ASR")]
# gTTS is an online service. It is only a dependency when explicitly enabled.
if config.ALLOW_ONLINE_TTS:
    _deps.append(("gtts", "online speech, ALLOW_ONLINE_TTS=True"))
for mod, why in _deps:
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
check("static/fonts              (UI + worksheet)", _dir("static/fonts", "fonts"))

def _manifest():
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(HERE, "download_models.py"),
                        "--verify-only"], capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError((r.stdout + r.stderr).strip().splitlines()[0])
    return r.stdout.strip().splitlines()[-1]
check("model files match model_manifest.json", _manifest)

# Leftovers from the retired architecture. Reported, never deleted: remove them
# yourself once you are sure. Not a failure.
log("\n[2b] Unused model data on disk (safe to delete, not required)")
_unused = [
    ("models/indictrans2-indic-indic/pytorch_model.bin", "duplicate of model.safetensors"),
    ("models/tts",      "Parler-TTS, retired"),
    ("models/whisper",  "Whisper ASR, retired"),
    ("models/en_indic", "English->Indic pivot model, retired"),
    ("models/indic_en", "Indic->English pivot model, retired"),
]
_reclaim = 0
for rel, why in _unused:
    p = os.path.join(HERE, rel)
    if os.path.isfile(p):
        b = os.path.getsize(p)
    elif os.path.isdir(p):
        b = sum(os.path.getsize(os.path.join(r, x)) for r, _, fs in os.walk(p) for x in fs)
    else:
        continue
    _reclaim += b
    log(f"  UNUSED  {rel:52} {b/1e9:5.2f} GB  {why}")
log(f"  total reclaimable: {_reclaim/1e9:.2f} GB" if _reclaim else "  none found")

# ── 3. load the pipeline ──────────────────────────────────────────────────────
# From here on the network is blocked: loading and every stage must be offline.
# Only connect() is refused, so local socketpairs some libraries use still work.
import socket as _socket, tempfile as _tempfile
from pathlib import Path as _Path
class _NoNetwork(_socket.socket):
    def connect(self, *a, **k):
        raise OSError("network access attempted: the app must run offline")
    connect_ex = connect
_socket.socket = _NoNetwork
# Synthesise into an empty cache, so the speech checks prove Piper really runs.
config.TTS_CACHE_DIR = _Path(_tempfile.mkdtemp(prefix="verify_tts_"))

log("\n[3] Pipeline load  (network blocked from here on)")
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

# ── 4. translation ────────────────────────────────────────────────────────────
log("\n[4] Translation")
state = {}
HINDI = "आज हम जोड़ना सीखेंगे। एक और एक मिलाओ।"

def _fwd():
    sat, source, _ = pl.hindi_to_santali(HINDI, "lesson_script")
    if not sat.strip():
        raise AssertionError("empty Santali output")
    ol = sum(1 for c in sat if "᱐" <= c <= "᱿")
    if ol == 0:
        raise AssertionError(f"no Ol Chiki characters in output: {sat!r}")
    state["sat"] = sat
    return f"from {source}  ->  {sat}"
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
log("\n[5] Speech, offline (this is what was stubbed out before)")

def _translit():
    spoken = pl.transliterate_santali(state.get("sat", "ᱡᱚᱦᱟᱨ"))
    if not spoken.strip():
        raise AssertionError("transliteration produced nothing")
    return f"'{state.get('sat','')[:18]}' -> '{spoken[:34]}'"
check(f"Ol Chiki to {config.SANTALI_TTS_SCRIPT.title()}", _translit)

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
            "Check that santali_tts was not replaced with a stub.")
    return f"{kb} KB, {secs:.1f}s, rms {rms:.3f}"
check("Santali speech is audible (Piper, offline)", _tts)

def _tts_hi():
    out = os.path.join(HERE, "_verify_tts_hi.wav")
    pl.hindi_tts("यहाँ कितने पत्थर हैं?", out)
    silent, rms, secs = audio_is_silent(out)
    if silent:
        raise AssertionError(f"the Hindi audio is silent (rms {rms:.5f})")
    return f"{secs:.1f}s, rms {rms:.3f}"
check("Hindi speech is audible (Piper, offline)", _tts_hi)

def _numbers():
    spoken = pl.transliterate_santali("᱗ ᱫᱷᱤᱨᱤ")
    if "एयाय्" not in spoken and "eyay" not in spoken:
        raise AssertionError(f"the digit was not spoken as a Santali number: {spoken!r}")
    return f"'᱗ ᱫᱷᱤᱨᱤ' -> '{spoken}'"
check("Santali numbers are spoken", _numbers)

def _tts_cache():
    out = os.path.join(HERE, "_verify_tts2.wav")
    t0 = time.time(); pl.santali_tts(state.get("sat", "ᱡᱚᱦᱟᱨ"), out); dt = time.time() - t0
    if dt > 0.6:
        raise AssertionError(f"cached speech took {dt:.2f}s, the cache is not working")
    return f"cache hit in {dt*1000:.0f} ms"
check("Speech cache", _tts_cache)

def _no_online():
    c = pl.tts_engine_counts
    if c["gtts"]:
        raise AssertionError(f"gTTS (online) produced {c['gtts']} clip(s)")
    return f"piper {c['piper']}, cache {c['cache']}, gTTS 0"
check("No online speech engine was used", _no_online)

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
    ask = 3                             # "तीन और चार कितने होते हैं?"
    got = [s.check_response(a, ask) for a in ("7", "᱗", "ᱮᱭᱟᱭ", "१२३", "")]
    if got != ["green", "green", "green", "yellow", "red"]:
        raise AssertionError(f"expected green x3, yellow, red; got {got}")
    return "7, ᱗ and ᱮᱭᱟᱭ are right; wrong is yellow; silence is red"
check("Comprehension grading", _grading)

def _db():
    import database
    # A throwaway database, so this check never writes into the real one.
    import tempfile as _tf
    real_db = database.DB_FILE
    database.DB_FILE = _Path(_tf.mkdtemp(prefix="verify_db_")) / "check.db"
    try:
        return _db_check(database)
    finally:
        database.DB_FILE = real_db

def _db_check(database):
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
# A real recording if there is one, else a synthetic benchmark clip
# (python bench/make_synthetic_clips.py) so the whole path is still exercised.
sample = next((os.path.join(HERE, f) for f in
               ("bench/clips/real/hi_01.webm", "bench/clips/synthetic/hi/hi_01.webm")
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

for tmp in ("_verify_tts.wav", "_verify_tts2.wav", "_verify_tts_hi.wav", "_verify_worksheet.pdf"):
    with contextlib.suppress(Exception):
        os.remove(os.path.join(HERE, tmp))

io.open(REPORT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(f"\nReport written to {REPORT}")
sys.exit(1 if failures else 0)
