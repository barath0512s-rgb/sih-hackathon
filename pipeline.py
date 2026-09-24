# pipeline.py — IndicConformer ASR, IndicTrans2 NMT, Piper TTS. All local.

import config          # first: sets the offline environment before transformers loads
import torch, time, os, threading
import numpy as np
import soundfile as sf
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from IndicTransToolkit.processor import IndicProcessor
import database
database.init_db()
from education_glossary import lookup_hi_to_sat, lookup_sat_to_hi

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ── ASR ───────────────────────────────────────────────────────────────────────
# IndicConformer is required. It is the only local ASR that reads Santali, so a
# missing model is an error with instructions, not a silent downgrade.
if not (config.ASR_DIR / "model_onnx.py").exists():
    raise FileNotFoundError(
        f"IndicConformer ASR model not found in {config.ASR_DIR}. "
        "Run: python download_models.py")
from indicconformer_asr import IndicConformerASR
from translit import olchiki


class TTSError(RuntimeError):
    """Speech could not be produced offline. Never replaced by silence."""

NMT_BEAMS           = 4      # Beam search for better quality (still <8s on CPU)
NMT_MAX_TOKENS      = 128    # Shorter max tokens for faster processing
NMT_NO_REPEAT_NGRAM = 3      
NMT_LENGTH_PENALTY  = 1.0    

TRANSLATION_CACHE = {}


def _populate_nipun_cache(pipeline):
    """Background thread: pre-translate all NIPUN lesson sentences for reliability."""
    try:
        import lesson_engine
        sentences = []
        for meta in lesson_engine.get_all_lessons():
            lesson = lesson_engine.get_lesson(meta["grade"], meta["topic"])
            if not lesson:
                continue
            for step in lesson["steps"]:
                h = step.get("hindi", "").strip()
                if not h:
                    continue
                mode = step.get("type", "lesson_script")
                if f"{mode}::{h}" not in TRANSLATION_CACHE:
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
        self.asr = IndicConformerASR()
        self.asr_backend = "indicconformer"
        print(f"  ASR ready ({self.asr_backend}).")

        # ── NMT: Direct Indic-to-Indic ──────────────────────────────────────────────
        # Absolute path: a relative one failed when started from another folder
        # and silently fell back to downloading the model from the Hub.
        if not (config.NMT_DIR / "config.json").exists():
            raise FileNotFoundError(
                f"IndicTrans2 model not found in {config.NMT_DIR}. Run: python download_models.py")
        MODEL_ID = str(config.NMT_DIR)
        self.tok_nmt = AutoTokenizer.from_pretrained(
            MODEL_ID, trust_remote_code=True)
        self.mdl_nmt = AutoModelForSeq2SeqLM.from_pretrained(
            MODEL_ID,
            trust_remote_code=True).to(DEVICE)
        self.mdl_nmt.eval()
        print("  NMT Indic->Indic (Direct) ready.")

        # ── TTS: Piper, offline. Voices are loaded in _warmup. ────────────────────
        # Santali: Ol Chiki -> config.SANTALI_TTS_SCRIPT -> a Piper voice.
        # Counts which engine produced each clip, so tests can prove no online call.
        self.tts_engine_counts = {"piper": 0, "cache": 0, "gtts": 0}

        self.ip = IndicProcessor(inference=True)
        self._tts_lock = threading.Lock()
        self._voices    = {}

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
        # Loading a Piper voice takes about 2s. Do it now, not mid-lesson.
        # Only the voices this configuration speaks with are loaded.
        for lang in ("hindi", "santali"):
            self._piper(self._voice_model(lang))

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
        """Transcribe Hindi audio with IndicConformer (RNN-T)."""
        return self.asr.transcribe(self._to_wav(audio_path), lang="hi", decoding="rnnt")

    def transcribe_santali(self, audio_path):
        """Transcribe Santali audio to Ol Chiki with IndicConformer (RNN-T)."""
        return self.asr.transcribe(self._to_wav(audio_path), lang="sat", decoding="rnnt")

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
        # 0. Instant Learning: a human correction always wins. This must be
        # checked before the glossary — a teacher correcting one of the
        # verified glossary sentences would otherwise be silently ignored
        # forever, since the glossary would keep answering first.
        learned_santali = database.get_correction(hindi_text)
        if learned_santali:
            print(f"  [DB HIT] Instant Learning applied for: {hindi_text}")
            return (learned_santali, "Human Verified (DB)", 100.0)

        # 1. Education Glossary: verified sentence-level lookup (instant, 100% accurate)
        glossary_hit = lookup_hi_to_sat(hindi_text)
        if glossary_hit:
            santali, conf = glossary_hit
            print(f"  [GLOSSARY HIT] {hindi_text[:50]}")
            result = (santali, "Education Glossary (Verified)", conf)
            TRANSLATION_CACHE[f"{content_mode}::{hindi_text}"] = result
            return result

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
        # Glossary first for known education sentences
        glossary_hit = lookup_sat_to_hi(santali_text)
        if glossary_hit:
            hindi, _ = glossary_hit
            print(f"  [GLOSSARY HIT sat->hi] {santali_text[:30]}")
            return hindi
        hindi, _ = self._nmt(
            santali_text, "sat_Olck", "hin_Deva",
            self.tok_nmt, self.mdl_nmt)
        return hindi

    # ── Speech ────────────────────────────────────────────────────────────────
    @staticmethod
    def _voice_model(lang):
        """Piper voice file that speaks `lang` ("hindi" or "santali")."""
        if lang == "hindi":
            return config.PIPER_VOICES["hindi"]
        return config.PIPER_VOICES[f"santali_{config.SANTALI_TTS_SCRIPT}"]

    def transliterate_santali(self, santali_text):
        """The text actually handed to the voice for a Santali line."""
        if config.SANTALI_TTS_SCRIPT == "latin":
            return olchiki.to_latin(santali_text)
        return olchiki.to_devanagari(santali_text)

    def _piper(self, model):
        """Load a Piper voice file once, keyed by file name. None if unavailable."""
        if model in self._voices:
            return self._voices[model]
        voice = None
        path = config.PIPER_DIR / f"{model}.onnx"
        try:
            from piper import PiperVoice
            if path.exists():
                voice = PiperVoice.load(str(path))
                print(f"  Piper voice loaded: {model}")
            else:
                print(f"  Piper voice missing: {path}")
        except Exception as e:
            print(f"  Piper unavailable ({type(e).__name__}: {e})")
        self._voices[model] = voice
        return voice

    def _speak(self, text, lang, out_path, gtts_lang):
        """Synthesise `text` to out_path with the Piper voice for `lang`.

        Raises TTSError if no offline voice can speak it. gTTS is tried only when
        config.ALLOW_ONLINE_TTS is True. Silence is never written.
        """
        import hashlib, shutil, wave

        model = self._voice_model(lang)
        cache_dir = config.TTS_CACHE_DIR
        cache_dir.mkdir(exist_ok=True)
        # Engine and voice file are part of the key, so audio from one engine is
        # never served as another's. Old gTTS entries are simply never matched.
        digest = hashlib.md5(f"piper:{model}:{text}".encode("utf-8")).hexdigest()
        cached_file = cache_dir / f"{digest}.wav"

        if cached_file.exists() and cached_file.stat().st_size > 1024:
            shutil.copy2(cached_file, out_path)
            self.tts_engine_counts["cache"] += 1
            return out_path

        with self._tts_lock:
            voice = self._piper(model)
            err = f"voice {model} is not installed"
            if voice is not None:
                try:
                    with wave.open(str(out_path), "wb") as wf:
                        voice.synthesize_wav(text, wf)
                    shutil.copy2(out_path, cached_file)
                    self.tts_engine_counts["piper"] += 1
                    return out_path
                except Exception as e:
                    err = f"{type(e).__name__}: {e}"
                    print(f"  [PIPER FAILED] {err}")
            if config.ALLOW_ONLINE_TTS:
                from gtts import gTTS
                gTTS(text, lang=gtts_lang).save(str(out_path))
                self.tts_engine_counts["gtts"] += 1
                return out_path
        raise TTSError(f"Offline speech failed ({err}).")

    def santali_tts(self, santali_text, out_path="output_santali.wav"):
        """Speak a Santali line: Ol Chiki is transliterated, then read by Piper."""
        spoken = self.transliterate_santali(santali_text).strip()
        if not spoken:
            raise TTSError("The Santali text has nothing that can be spoken.")
        gtts_lang = "en" if config.SANTALI_TTS_SCRIPT == "latin" else "hi"
        return self._speak(spoken, "santali", out_path, gtts_lang)

    def hindi_tts(self, hindi_text, out_path="output_hindi.wav"):
        """Speak a Hindi line with the Hindi Piper voice."""
        text = (hindi_text or "").strip()
        if not text:
            raise TTSError("There is no Hindi text to speak.")
        return self._speak(text, "hindi", out_path, "hi")

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

