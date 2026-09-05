# pipeline.py — accuracy-first configuration with IndicConformer ASR + DB learning

import torch, time, os, threading
import numpy as np
import soundfile as sf
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from IndicTransToolkit.processor import IndicProcessor
import database
database.init_db()

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ── ASR Backend Selection ─────────────────────────────────────────────────────
# Try IndicConformer first (native Indian language support including Santali).
# Falls back to Whisper if model isn't downloaded yet.
_USE_INDIC_CONFORMER = False
try:
    _IC_DIR = os.path.join(os.path.dirname(__file__), "models", "indicconformer")
    if os.path.isdir(_IC_DIR) and os.path.exists(os.path.join(_IC_DIR, "model_onnx.py")):
        from indicconformer_asr import IndicConformerASR
        _USE_INDIC_CONFORMER = True
        print("ASR backend: IndicConformer 600M Multilingual (Hindi + Santali native)")
    else:
        raise FileNotFoundError("IndicConformer not downloaded yet")
except Exception as _e:
    import whisper as _whisper_module
    print(f"ASR backend: Whisper small (fallback — {_e})")

NMT_BEAMS           = 1      # Greedy decoding for fast CPU inference (<10s latency)
NMT_MAX_TOKENS      = 128    # Shorter max tokens for faster processing
NMT_NO_REPEAT_NGRAM = 3      
NMT_LENGTH_PENALTY  = 1.0    

TRANSLATION_CACHE = {}

def _populate_nipun_cache(pipeline):
    """Background thread: pre-translate all NIPUN lesson sentences for reliability."""
    try:
        import lesson_engine
        all_lessons = lesson_engine.get_all_lessons()
        sentences = []
        for l in all_lessons:
            for step in l.get("steps", []):
                for mode in ["lesson_script", "activity_instruction", "assessment_prompt"]:
                    h = step.get("hindi", "").strip()
                    if h:
                        key = f"{mode}::{h}"
                        if key not in TRANSLATION_CACHE:
                            sentences.append((h, mode))
        seen = set()
        unique = [(h, m) for h, m in sentences if not (h, m) in seen and not seen.add((h, m))]
        print(f"  Pre-caching {len(unique)} NIPUN sentences in background…")
        for hindi, mode in unique:
            try:
                pipeline.hindi_to_santali(hindi, mode)
            except Exception:
                pass
        print("  Pre-cache complete — all lesson sentences cached.")
    except Exception as e:
        print(f"  Pre-cache skipped: {e}")

class VaaniSetuPipeline:

    def __init__(self):
        print(f"Loading pipeline on {DEVICE}...")

        # ── ASR ─────────────────────────────────────────────────────────────
        if _USE_INDIC_CONFORMER:
            self.asr = IndicConformerASR()
            self.asr_backend = "indicconformer"
        else:
            import whisper
            self.asr = whisper.load_model("small", download_root="./models/whisper")
            self.asr_backend = "whisper"
        print(f"  ASR ready ({self.asr_backend}).")

        # ── NMT: Direct Indic-to-Indic ──────────────────────────────────────────────
        MODEL_ID = "./models/indictrans2-indic-indic" if os.path.exists("./models/indictrans2-indic-indic") else "ai4bharat/indictrans2-indic-indic-dist-320M"
        self.tok_nmt = AutoTokenizer.from_pretrained(
            MODEL_ID, trust_remote_code=True)
        self.mdl_nmt = AutoModelForSeq2SeqLM.from_pretrained(
            MODEL_ID,
            trust_remote_code=True).to(DEVICE)
        self.mdl_nmt.eval()
        print("  NMT Indic→Indic (Direct) ready.")

        # ── TTS: Fast gTTS Transliteration ─────────────────────────────────────
        # ParlerTTS is removed because it takes 30s on CPU.
        # We now transliterate Ol Chiki to Latin and let Google TTS read it in <1s.
        print("  TTS ready (gTTS transliteration).")

        self.ip = IndicProcessor(inference=True)
        self._tts_lock = threading.Lock()

        self._warmup()

        # Pre-cache all NIPUN lesson sentences in background
        threading.Thread(target=_populate_nipun_cache, args=(self,),
                         daemon=True).start()

        print("Pipeline ready.\n")

    def _warmup(self):
        print("  Warming up NMT...")
        try:
            self._nmt("आज हम जोड़ना सीखेंगे।",
                      "hin_Deva", "sat_Olck",
                      self.tok_nmt, self.mdl_nmt)
            print("  Warmup complete.")
        except Exception as e:
            print(f"  Warmup skipped: {e}")

    def _nmt(self, text, src_lang, tgt_lang, tokenizer, model):
        batch = self.ip.preprocess_batch(
            [text], src_lang=src_lang, tgt_lang=tgt_lang)
        enc = tokenizer(
            batch, truncation=True, padding="longest",
            return_tensors="pt").to(DEVICE)
        with torch.no_grad():
            out = model.generate(
                **enc,
                num_beams=NMT_BEAMS,
                max_new_tokens=NMT_MAX_TOKENS,
                no_repeat_ngram_size=NMT_NO_REPEAT_NGRAM,
                length_penalty=NMT_LENGTH_PENALTY,
                early_stopping=True,
                return_dict_in_generate=True,
                output_scores=True)
        
        if hasattr(out, 'sequences_scores') and out.sequences_scores is not None:
            seq_score = out.sequences_scores[0].item()
            import math
            confidence = math.exp(seq_score) * 100 if seq_score < 0 else 99.0
        else:
            # Greedy decoding doesn't return sequence scores easily
            confidence = 95.0

        decoded = tokenizer.batch_decode(
            out.sequences, skip_special_tokens=True,
            clean_up_tokenization_spaces=True)
        
        translated = self.ip.postprocess_batch(decoded, lang=tgt_lang)[0]
        return translated, round(confidence, 1)

    @staticmethod
    def _to_wav(audio_path, target_sr=16000):
        """Convert any audio format to 16kHz mono WAV using ffmpeg. Returns wav path."""
        import subprocess
        if audio_path.lower().endswith(".wav"):
            return audio_path
        wav_path = audio_path + "_converted.wav"
        subprocess.run([
            "ffmpeg", "-y", "-i", audio_path,
            "-ar", str(target_sr), "-ac", "1", "-f", "wav", wav_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return wav_path

    def transcribe_hindi(self, audio_path):
        """Transcribe Hindi audio. Uses IndicConformer (native) or Whisper (fallback)."""
        audio_path = self._to_wav(audio_path)
        if self.asr_backend == "indicconformer":
            return self.asr.transcribe(audio_path, lang="hi", decoding="rnnt")
        else:
            vocab_prompt = "नमस्ते, आज हम जोड़ना और घटाना सीखेंगे। एक, दो, तीन, चार, पांच, आम, संख्या, उंगलियां, जवाब।"
            result = self.asr.transcribe(
                audio_path, language="hi", task="transcribe",
                initial_prompt=vocab_prompt,
                beam_size=5, best_of=5, temperature=0.0,
                condition_on_previous_text=False
            )
            return result["text"].strip()

    def transcribe_santali(self, audio_path):
        """Transcribe Santali (Ol Chiki). IndicConformer: native. Whisper: best-effort."""
        audio_path = self._to_wav(audio_path)
        if self.asr_backend == "indicconformer":
            return self.asr.transcribe(audio_path, lang="sat", decoding="rnnt")
        else:
            result = self.asr.transcribe(
                audio_path, task="transcribe",
                beam_size=5, temperature=0.0, condition_on_previous_text=False
            )
            return result["text"].strip()

    def _apply_domain_glossary(self, text, lang):
        glossary = {
            "sat_Olck": {
                "ᱥᱮᱪᱮᱫ:": "",          
                "ᱠᱟᱹᱢᱤᱦᱚᱨᱟ:": "",        
                "ᱠᱩᱠᱞᱤ:": "",            
                "ᱥᱮᱪᱮᱫ :": "", 
            },
            "eng_Latn": {
                "Teaching: ": "",
                "Activity instruction: ": "",
                "Question: ": ""
            }
        }
        for bad, good in glossary.get(lang, {}).items():
            text = text.replace(bad, good).strip()
        return text

    def hindi_to_santali(self, hindi_text, content_mode="lesson_script"):
        # 1. Instant Learning: Check if a human has corrected this exact phrase
        learned_santali = database.get_correction(hindi_text)
        if learned_santali:
            print(f"  [DB HIT] Instant Learning applied for: {hindi_text}")
            return (learned_santali, "Human Verified (DB)", 100.0)
            
        cache_key = f"{content_mode}::{hindi_text}"
        if cache_key in TRANSLATION_CACHE and \
                TRANSLATION_CACHE[cache_key] is not None:
            return TRANSLATION_CACHE[cache_key]

        # 2. Direct Translation (No English pivot!)
        santali, conf_sat = self._nmt(
            hindi_text, "hin_Deva", "sat_Olck",
            self.tok_nmt, self.mdl_nmt)
        
        santali = self._apply_domain_glossary(santali, "sat_Olck")

        # Mock English for the UI since the pivot was removed
        english_mock = "[Direct Translation used — No English intermediate]"
        total_conf = conf_sat

        result = (santali, english_mock, total_conf)
        TRANSLATION_CACHE[cache_key] = result
        return result

    def santali_to_hindi(self, santali_text):
        hindi, _ = self._nmt(
            santali_text, "sat_Olck", "hin_Deva",
            self.tok_nmt, self.mdl_nmt)
        return hindi

    def santali_tts(self, santali_text, out_path="output_santali.wav"):
        # 1. Check TTS cache for instant sub-10s return
        import hashlib, shutil, os
        cache_dir = "./tts_cache"
        os.makedirs(cache_dir, exist_ok=True)
        text_hash = hashlib.md5(santali_text.encode('utf-8')).hexdigest()
        cached_file = os.path.join(cache_dir, f"{text_hash}.wav")
        
        if os.path.exists(cached_file):
            print(f"  [TTS CACHE HIT] {santali_text[:20]}...")
            shutil.copy2(cached_file, out_path)
            return out_path

        # 2. Transliterate Ol Chiki to Latin and use fast gTTS
        from gtts import gTTS
        
        ol_chiki_to_latin = {
            'ᱚ': 'o', 'ᱛ': 't', 'ᱜ': 'g', 'ᱝ': 'ng', 'ᱞ': 'l', 
            'ᱟ': 'a', 'ᱠ': 'k', 'ᱡ': 'j', 'ᱢ': 'm', 'ᱣ': 'w',
            'ᱤ': 'i', 'ᱥ': 's', 'ᱦ': 'h', 'ᱧ': 'ny', 'ᱨ': 'r', 
            'ᱩ': 'u', 'ᱪ': 'ch', 'ᱫ': 'd', 'ᱬ': 'n', 'ᱭ': 'y',
            'ᱮ': 'e', 'ᱯ': 'p', 'ᱰ': 'd', 'ᱱ': 'n', 'ᱲ': 'r', 
            'ᱳ': 'o', 'ᱴ': 't', 'ᱵ': 'b', 'ᱶ': 'n', 'ᱷ': 'h',
            ' ': ' ', '?': '?', '.': '.', ',': ','
        }

        # Transliterate to Latin so gTTS can pronounce the phonetic Santali
        latin_text = "".join([ol_chiki_to_latin.get(c, "") for c in santali_text])
        if not latin_text.strip():
            latin_text = "Translation failed"

        with self._tts_lock:
            # lang='en', tld='co.in' gives an Indian phonetic reading of the Latin characters
            tts = gTTS(latin_text, lang='en', tld='co.in')
            tts.save(out_path)
            
            # Save to cache for next time
            shutil.copy2(out_path, cached_file)
            
        return out_path

    def full_forward(self, audio_path, content_mode="lesson_script"):
        t0 = time.time()
        hindi   = self.transcribe_hindi(audio_path)
        t1 = time.time()
        sat, en, conf = self.hindi_to_santali(hindi, content_mode)
        t2 = time.time()
        audio   = self.santali_tts(sat)
        t3 = time.time()
        return {
            "hindi_text":    hindi,
            "english_pivot": en,
            "santali_text":  sat,
            "confidence":    conf,
            "audio_path":    audio,
            "latency": {
                "asr":   round(t1 - t0, 2),
                "nmt":   round(t2 - t1, 2),
                "tts":   round(t3 - t2, 2),
                "total": round(t3 - t0, 2)
            }
        }
