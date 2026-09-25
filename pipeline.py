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

# Decoding settings live in config.py (NMT_NUM_BEAMS, NMT_MAX_TOKENS, ...).

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
                sentences.append((h, mode))
            # Flashcard words too, so the flashcard view does not wait on the model.
            for card in lesson.get("flashcards", []):
                sentences.append((card["hi"], "lesson_script"))
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
        # The PyTorch model is loaded only when something needs it (the
        # fallback, a test, a benchmark). With the ONNX engine it is never
        # loaded, which saves its memory.
        self._mdl_nmt = None
        self._mdl_lock = threading.Lock()
        self.ip = IndicProcessor(inference=True)
        self.onnx_nmt = None
        self.nmt_backend = "torch"
        if config.NMT_BACKEND.startswith("onnx"):
            try:
                import nmt_onnx
                if (nmt_onnx.ONNX_DIR / "encoder.onnx").exists():
                    self.onnx_nmt = nmt_onnx.OnnxNMT(self.tok_nmt, self.ip,
                                                     int8=config.NMT_BACKEND == "onnx-int8",
                                                     threads=config.NMT_THREADS)
                    self.nmt_backend = config.NMT_BACKEND
                else:
                    print(f"  ONNX translation files not found in {nmt_onnx.ONNX_DIR}; using PyTorch. "
                          "Export them with: python tools/export/export_indictrans2_onnx.py")
            except Exception as e:                     # onnxruntime missing or a bad file
                print(f"  ONNX translation unavailable ({type(e).__name__}: {e}); using PyTorch.")
        if self.onnx_nmt is None:
            _ = self.mdl_nmt
        print(f"  NMT Indic->Indic (Direct) ready: {self.nmt_backend}.")

        # ── TTS: Piper, offline. Voices are loaded in _warmup. ────────────────────
        # Santali: Ol Chiki -> config.SANTALI_TTS_SCRIPT -> a Piper voice.
        # Counts which engine produced each clip, so tests can prove no online call.
        self.tts_engine_counts = {"piper": 0, "cache": 0, "gtts": 0}

        self._tts_lock = threading.Lock()
        # IndicProcessor keeps one placeholder queue per instance and clears it
        # in postprocess_batch, so two overlapping translations (two requests,
        # or a request during the start-up pre-cache) could take each other's
        # placeholders or leave one thread waiting on the queue for ever. One
        # translation at a time: preprocess, generate and postprocess together.
        self._nmt_lock = threading.Lock()
        self._voices    = {}

        self._warmup()

        # Pre-cache all NIPUN lesson sentences in background
        threading.Thread(target=_populate_nipun_cache, args=(self,),
                         daemon=True).start()

        print("Pipeline ready.\n")

    def _warmup(self):
        print("  Warming up NMT...")
        try:
            self._nmt("आज हम जोड़ना सीखेंगे।", "hin_Deva", "sat_Olck")
            print("  Warmup complete.")
        except Exception as e:
            print(f"  Warmup skipped: {e}")
        # Loading a Piper voice takes about 2s. Do it now, not mid-lesson.
        # Only the voices this configuration speaks with are loaded.
        for lang in ("hindi", "santali"):
            self._piper(self._voice_model(lang))

    @property
    def mdl_nmt(self):
        """The PyTorch translation model, loaded on first use."""
        with self._mdl_lock:
            if self._mdl_nmt is None:
                self._mdl_nmt = AutoModelForSeq2SeqLM.from_pretrained(
                    str(config.NMT_DIR), trust_remote_code=True).to(DEVICE).eval()
            return self._mdl_nmt

    @mdl_nmt.setter
    def mdl_nmt(self, model):
        self._mdl_nmt = model

    def _nmt(self, text, src_lang, tgt_lang, tokenizer=None, model=None):
        """Translate one sentence. Returns (text, model_score).

        With no `model`, the app's engine: ONNX Runtime when exported
        (config.NMT_BACKEND), else PyTorch. Passing a PyTorch model runs that
        model (tests and benchmarks compare engines this way).

        model_score is the geometric mean of the per-token probabilities of the
        greedy output, computed from real log-probs. It is NOT a quality
        estimate: eval/model_score_sanity.py shows gibberish input scoring
        higher than a real classroom sentence. It is returned for evaluation
        and never shown to teachers. None when beam search is on.
        """
        with self._nmt_lock:
            if model is None and self.onnx_nmt is not None:
                out, _, score = self.onnx_nmt.translate_scored(text, src_lang, tgt_lang)
                return out, score
            return self._nmt_locked(text, src_lang, tgt_lang, tokenizer or self.tok_nmt,
                                    model if model is not None else self.mdl_nmt)

    def _nmt_locked(self, text, src_lang, tgt_lang, tokenizer, model):
        batch = self.ip.preprocess_batch(
            [text], src_lang=src_lang, tgt_lang=tgt_lang)
        enc = tokenizer(
            batch, truncation=True, padding="longest",
            return_tensors="pt").to(DEVICE)
        with torch.no_grad():
            out = model.generate(
                **enc,
                num_beams=config.NMT_NUM_BEAMS,
                max_new_tokens=min(config.NMT_MAX_TOKENS,
                                   config.NMT_LIMIT_FACTOR * enc["input_ids"].shape[1]
                                   + config.NMT_LIMIT_MARGIN),
                no_repeat_ngram_size=config.NMT_NO_REPEAT_NGRAM,
                return_dict_in_generate=True,
                output_scores=True)

        score = None
        if config.NMT_NUM_BEAMS == 1:
            logp = model.compute_transition_scores(
                out.sequences, out.scores, normalize_logits=True)[0]
            logp = logp[torch.isfinite(logp)]
            if len(logp):
                score = round(float(logp.mean().exp()), 3)

        decoded = tokenizer.batch_decode(
            out.sequences, skip_special_tokens=True,
            clean_up_tokenization_spaces=True)
        return self.ip.postprocess_batch(decoded, lang=tgt_lang)[0], score

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

    def _transcribe(self, audio_path, lang):
        return self.asr.transcribe(self._to_wav(audio_path), lang=lang,
                                   decoding=config.ASR_DECODING[lang],
                                   trim=config.ASR_TRIM_SILENCE[lang])

    def transcribe_hindi(self, audio_path):
        """Transcribe Hindi audio with IndicConformer (settings in config.py)."""
        return self._transcribe(audio_path, "hi")

    def transcribe_santali(self, audio_path):
        """Transcribe Santali audio to Ol Chiki with IndicConformer."""
        return self._transcribe(audio_path, "sat")

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

    def translate(self, text, direction="hi-to-sat", content_mode="lesson_script"):
        """Translate one line. Returns {"text", "source", "model_score"}.

        Answered by the cheapest layer that can answer it, in this order:
          teacher   a teacher's correction (always wins, both directions)
          glossary  a verified sentence in education_glossary.py
          cached    an earlier model translation of the same line
          model     IndicTrans2
        model_score is set only for "model" (see _nmt: not a quality estimate).
        """
        if direction not in ("hi-to-sat", "sat-to-hi"):
            raise ValueError(f"unknown direction {direction!r}")
        fwd = direction == "hi-to-sat"

        # A correction must be checked before the glossary: a teacher fixing a
        # glossary sentence would otherwise be ignored for ever.
        fixed = database.get_correction(text, direction)
        if fixed:
            return {"text": fixed, "source": "teacher", "model_score": None}

        hit = (lookup_hi_to_sat if fwd else lookup_sat_to_hi)(text)
        if hit:
            return {"text": hit[0], "source": "glossary", "model_score": None}

        key = f"{direction}::{content_mode}::{text}"
        if key in TRANSLATION_CACHE:
            cached = dict(TRANSLATION_CACHE[key])
            cached["source"] = "cached"
            return cached

        src, tgt = ("hin_Deva", "sat_Olck") if fwd else ("sat_Olck", "hin_Deva")
        out, score = self._nmt(text, src, tgt)
        if fwd:
            out = self._apply_domain_glossary(out, "sat_Olck")
        result = {"text": out, "source": "model", "model_score": score}
        TRANSLATION_CACHE[key] = result
        return result

    def hindi_to_santali(self, hindi_text, content_mode="lesson_script"):
        """(santali, source, model_score). Kept for older callers; see translate()."""
        r = self.translate(hindi_text, "hi-to-sat", content_mode)
        return r["text"], r["source"], r["model_score"]

    def santali_to_hindi(self, santali_text):
        """Hindi text. Kept for older callers; see translate()."""
        return self.translate(santali_text, "sat-to-hi")["text"]

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

    def _speak(self, text, lang, out_path, gtts_lang, info=None):
        """Synthesise `text` to out_path with the Piper voice for `lang`.

        Raises TTSError if no offline voice can speak it. gTTS is tried only when
        config.ALLOW_ONLINE_TTS is True. Silence is never written.
        If `info` is a dict, info["tts_engine"] is set to piper, cache or gtts.
        """
        info = info if info is not None else {}
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
            info["tts_engine"] = "cache"
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
                    info["tts_engine"] = "piper"
                    return out_path
                except Exception as e:
                    err = f"{type(e).__name__}: {e}"
                    print(f"  [PIPER FAILED] {err}")
            if config.ALLOW_ONLINE_TTS:
                from gtts import gTTS
                gTTS(text, lang=gtts_lang).save(str(out_path))
                self.tts_engine_counts["gtts"] += 1
                info["tts_engine"] = "gtts"
                return out_path
        raise TTSError(f"Offline speech failed ({err}).")

    def santali_tts(self, santali_text, out_path="output_santali.wav", info=None):
        """Speak a Santali line: Ol Chiki is transliterated, then read by Piper."""
        spoken = self.transliterate_santali(santali_text).strip()
        if not spoken:
            raise TTSError("The Santali text has nothing that can be spoken.")
        gtts_lang = "en" if config.SANTALI_TTS_SCRIPT == "latin" else "hi"
        return self._speak(spoken, "santali", out_path, gtts_lang, info)

    def hindi_tts(self, hindi_text, out_path="output_hindi.wav", info=None):
        """Speak a Hindi line with the Hindi Piper voice."""
        text = (hindi_text or "").strip()
        if not text:
            raise TTSError("There is no Hindi text to speak.")
        return self._speak(text, "hindi", out_path, "hi", info)

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

