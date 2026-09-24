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

# The feedback database predates this file and sits in the project root.
DB_FILE = BASE_DIR / "vaanisetu_feedback.db"

# ── Feature flags ─────────────────────────────────────────────────────────────
# The application must run with no network. gTTS (Google) is an online service
# and may only be used when this is explicitly switched on.
ALLOW_ONLINE_TTS = False

# ── Server ────────────────────────────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = 5000

DATA_DIR.mkdir(exist_ok=True)
