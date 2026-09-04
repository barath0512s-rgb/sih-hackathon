# download_models.py — run ONCE. Takes 30-50 minutes.
import os
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from parler_tts import ParlerTTSForConditionalGeneration
import whisper

os.makedirs("models", exist_ok=True)

# ── 1. Whisper small — Hindi ASR (~244 MB) ───────────────────────────────────
print("1/3  Whisper small (Hindi ASR)...")
whisper.load_model("small", download_root="./models/whisper")
print("     Done.\n")

# ── 2. IndicTrans2 distilled — Indic→En (~800 MB) ────────────────────────────
print("2a/3  IndicTrans2 Indic→En (Hindi→English pivot)...")
tok = AutoTokenizer.from_pretrained(
    "ai4bharat/indictrans2-indic-en-dist-200M", trust_remote_code=True)
mdl = AutoModelForSeq2SeqLM.from_pretrained(
    "ai4bharat/indictrans2-indic-en-dist-200M", trust_remote_code=True)
tok.save_pretrained("./models/indic_en")
mdl.save_pretrained("./models/indic_en")
print("      Done.\n")

# ── 3. IndicTrans2 distilled — En→Indic (~800 MB) ────────────────────────────
print("2b/3  IndicTrans2 En→Indic (English→Santali)...")
tok2 = AutoTokenizer.from_pretrained(
    "ai4bharat/indictrans2-en-indic-dist-200M", trust_remote_code=True)
mdl2 = AutoModelForSeq2SeqLM.from_pretrained(
    "ai4bharat/indictrans2-en-indic-dist-200M", trust_remote_code=True)
tok2.save_pretrained("./models/en_indic")
mdl2.save_pretrained("./models/en_indic")
print("      Done.\n")

# ── 4. Indic Parler-TTS pretrained — Santali TTS (~1.8 GB) ──────────────────
# IMPORTANT: use indic-parler-tts-pretrained NOT indic-parler-tts
# The fine-tuned version has an incomplete decoder on HuggingFace.
print("3/3  Indic Parler-TTS pretrained (Santali TTS)...")
TTS_NAME = "ai4bharat/indic-parler-tts-pretrained"
tts_prompt_tok = AutoTokenizer.from_pretrained(TTS_NAME)
tts_mdl = ParlerTTSForConditionalGeneration.from_pretrained(TTS_NAME)
# Load description tokenizer from model config — do NOT hardcode flan-t5
tts_desc_tok = AutoTokenizer.from_pretrained(
    tts_mdl.config.text_encoder._name_or_path)
tts_prompt_tok.save_pretrained("./models/tts/prompt_tok")
tts_desc_tok.save_pretrained("./models/tts/desc_tok")
tts_mdl.save_pretrained("./models/tts/model")
print("     Done.\n")

# ── Verify ───────────────────────────────────────────────────────────────────
print("Verifying...")
total = 0
for path in ["models/whisper", "models/indic_en", "models/en_indic",
             "models/tts/model"]:
    if os.path.exists(path):
        mb = sum(os.path.getsize(os.path.join(r, f))
                 for r, _, fs in os.walk(path) for f in fs) // (1024*1024)
        total += mb
        print(f"  OK  {path} ({mb} MB)")
    else:
        print(f"  MISSING  {path}")
print(f"\nTotal: {total} MB")
print("Run: python test_pipeline.py")
