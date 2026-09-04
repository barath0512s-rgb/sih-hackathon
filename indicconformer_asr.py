"""
indicconformer_asr.py
Correct wrapper around AI4Bharat IndicConformer 600M Multilingual ONNX model.

Supported langs: as, bn, brx, doi, kok, gu, hi, kn, ks, mai, ml, mr, mni, ne,
                 or, pa, sa, sat, sd, ta, te, ur
"""

import os
import sys
import json
import importlib.util
import numpy as np
import torch
import soundfile as sf

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models", "indicconformer")


def _load_model_class():
    """Dynamically load the IndicASRModel class from the downloaded repo."""
    onnx_py = os.path.join(MODEL_DIR, "model_onnx.py")
    spec = importlib.util.spec_from_file_location("indicasr_onnx", onnx_py)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.IndicASRConfig, mod.IndicASRModel


class IndicConformerASR:
    """
    Drop-in replacement for Whisper that natively supports 22 Indian languages
    including Santali (sat) in Ol Chiki script.

    Usage:
        asr = IndicConformerASR()
        hindi_text   = asr.transcribe("audio.wav", lang="hi")
        santali_text = asr.transcribe("audio.wav", lang="sat")
    """

    SUPPORTED_LANGS = [
        "as","bn","brx","doi","kok","gu","hi","kn","ks","mai",
        "ml","mr","mni","ne","or","pa","sa","sat","sd","ta","te","ur"
    ]

    def __init__(self):
        print("Loading IndicConformer 600M Multilingual (ONNX)...")
        if not os.path.isdir(MODEL_DIR):
            raise FileNotFoundError(
                f"Model directory not found: {MODEL_DIR}\n"
                "Run download first:\n"
                "  python -c \"from huggingface_hub import snapshot_download; "
                "snapshot_download('ai4bharat/indic-conformer-600m-multilingual', "
                "local_dir='./models/indicconformer')\""
            )

        IndicASRConfig, IndicASRModel = _load_model_class()
        config = IndicASRConfig(ts_folder=MODEL_DIR)
        self.model  = IndicASRModel(config)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"  IndicConformer ready on {self.device}. Supports: {self.SUPPORTED_LANGS}")

    def _load_audio(self, audio_path, target_sr=16000):
        """Load audio → float32 mono tensor at 16 kHz. Handles webm/mp4 via ffmpeg."""
        import subprocess, tempfile, os

        # Convert non-wav formats (browser webm) to wav using ffmpeg
        if not audio_path.lower().endswith(".wav"):
            wav_tmp = audio_path + "_converted.wav"
            subprocess.run([
                "ffmpeg", "-y", "-i", audio_path,
                "-ar", str(target_sr), "-ac", "1",
                "-f", "wav", wav_tmp
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            audio_path = wav_tmp

        audio, sr = sf.read(audio_path, dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sr != target_sr:
            n_out = int(len(audio) * target_sr / sr)
            audio = np.interp(
                np.linspace(0, len(audio) - 1, n_out),
                np.arange(len(audio)),
                audio
            )
        return torch.tensor(audio, dtype=torch.float32).unsqueeze(0)

    def transcribe(self, audio_path, lang="hi", decoding="ctc"):
        """
        Transcribe audio to text.

        Args:
            audio_path : path to .wav / .webm file
            lang       : language code, e.g. 'hi' (Hindi) or 'sat' (Santali)
            decoding   : 'ctc' (fast, default) or 'rnnt' (slower, sometimes better)
        Returns:
            Transcribed text string
        """
        if lang not in self.SUPPORTED_LANGS:
            raise ValueError(
                f"Language '{lang}' not supported. Choose from: {self.SUPPORTED_LANGS}"
            )

        wav = self._load_audio(audio_path)          # (1, T) float32
        with torch.no_grad():
            text = self.model.forward(wav, lang=lang, decoding=decoding)
        return text.strip()
