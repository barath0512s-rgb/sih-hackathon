"""Central configuration. Every path is absolute; every tunable lives here.

The product name is on hold. It lives only in APP_NAME / APP_NAME_LOCAL, and
the frontend reads it from GET /config, so a rename is a one-line change here.
"""

from pathlib import Path

# ── Product name ──────────────────────────────────────────────────────────────
APP_NAME = "VaaniSetu"
# The same name as shown in each UI language's own script.
APP_NAME_LOCAL = {
    "hi":  "वाणीसेतु",
    "sat": "ᱣᱟᱱᱤᱥᱮᱛᱩ",
    "en":  APP_NAME,
}

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).resolve().parent
DATA_DIR      = BASE_DIR / "data"            # runtime state: database, logs
MODELS_DIR    = BASE_DIR / "models"
FONTS_DIR     = MODELS_DIR / "fonts"
PIPER_DIR     = MODELS_DIR / "piper"
ASR_DIR       = MODELS_DIR / "indicconformer"
NMT_DIR       = MODELS_DIR / "indictrans2-indic-indic"
TTS_CACHE_DIR = BASE_DIR / "tts_cache"       # synthesised audio, keyed by content
TTS_OUT_DIR   = BASE_DIR / "tts_out"         # per-request audio files
STATIC_DIR    = BASE_DIR / "static"          # the only folder served as-is over HTTP

# Exact model revisions in use (download_models.py fetches these). Every
# latency measurement records them, so numbers are tied to a model version.
ASR_REPO, ASR_REVISION = "ai4bharat/indic-conformer-600m-multilingual", "e9b71b369c048e2c6b634d4c131061c34e441179"
NMT_REPO, NMT_REVISION = "ai4bharat/indictrans2-indic-indic-dist-320M", "ffb7582b6d43791f1fb26b2153fc065f2e9ea575"

# The feedback database predates this file and sits in the project root.
DB_FILE = BASE_DIR / "vaanisetu_feedback.db"

# ── Feature flags ─────────────────────────────────────────────────────────────
# The application must run with no network. gTTS (Google) is an online service
# and may only be used when this is explicitly switched on.
ALLOW_ONLINE_TTS = False

# Models are read from disk only. These stop transformers and huggingface_hub
# from contacting the Hub (update checks, telemetry, silent re-downloads).
OFFLINE_ENV = {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
               "HF_HUB_DISABLE_TELEMETRY": "1"}

# ── Speech recognition ────────────────────────────────────────────────────────
# Chosen per language from bench/asr_decoding.py (results in bench/results/).
# On the synthetic clips CTC was about twice as fast as RNN-T with no worse
# character error rate. Trimming silence helped Hindi but slightly hurt Santali,
# whose unreleased word-final stops are quiet enough to be clipped.
# Re-run bench/asr_decoding.py on real recordings before trusting this.
ASR_DECODING = {"hi": "ctc", "sat": "ctc"}
ASR_TRIM_SILENCE = {"hi": True, "sat": False}

# ── Translation ───────────────────────────────────────────────────────────────
NMT_NUM_BEAMS       = 1      # greedy; beam search is slower on CPU for short lines
NMT_MAX_TOKENS      = 128
# The limit is also sized to the input: min(128, 3 x input tokens + 10). On the
# benchmark lines this changed no output and saved no time (no line ran on:
# bench/results/nmt_limits.md); it caps the worst case if the model loops.
NMT_LIMIT_FACTOR, NMT_LIMIT_MARGIN = 3, 10
NMT_NO_REPEAT_NGRAM = 3      # blocks the repeating-phrase loops this model can fall into

# ── Speech ────────────────────────────────────────────────────────────────────
# No offline voice reads Ol Chiki, so Santali is transliterated first
# (translit/olchiki.py) and read by an existing Piper voice:
#   "devanagari": the hi_IN voice, Indian phonetics (default)
#   "latin":      the en_US voice, kept for A/B comparison
SANTALI_TTS_SCRIPT = "devanagari"
PIPER_VOICES = {
    "hindi":              "hi_IN-pratham-medium",
    "santali_devanagari": "hi_IN-pratham-medium",   # same file: loaded once
    "santali_latin":      "en_US-lessac-medium",
}

# Each spoken reply is its own file in TTS_OUT_DIR. Old ones are deleted after
# this long, and never more than this many are kept.
AUDIO_KEEP_SECONDS = 30 * 60
AUDIO_KEEP_MAX     = 200

# ── Server ────────────────────────────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = 5000

# Hub mode over HTTPS (python app.py --https): tablets on the Wi-Fi need
# https:// for the microphone. tools/make_cert.py writes the files here.
HTTPS_PORT = 5443
CERT_DIR   = BASE_DIR / "certs"

# Audio for every line of a lesson a teacher imported (curriculum.py). Kept, not
# pruned like tts_out/, because the lesson is reused. Regenerable, so git-ignored.
LESSON_AUDIO_DIR = DATA_DIR / "lesson_audio"
# Lessons the team wrote. Added through the curriculum import on the first
# start (python app.py), so a fresh clone shows every lesson.
TEAM_LESSONS_FILE = BASE_DIR / "content" / "team_lessons.json"

DATA_DIR.mkdir(exist_ok=True)

# Must run before transformers is imported, so modules import config first.
import os as _os
for _k, _v in OFFLINE_ENV.items():
    _os.environ.setdefault(_k, _v)
