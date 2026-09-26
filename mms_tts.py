"""Mundari and Ho voices, Preview (A7): facebook/mms-tts-unr / mms-tts-hoc as ONNX.

    python mms_tts.py unr "<a teacher's line in Devanagari>" out.wav

The models (CC BY-NC 4.0) are exported by tools/export/export_mms_vits_onnx.py to
models/mms-tts/<lang>/ (model.onnx, tokens.txt, tts.json). They read Odia script
(docs/sources.md#mms-tts), so a Devanagari or Ol Chiki line is converted first
(translit/odia.py). Warang Citi (Ho's own script) has no conversion yet: refused.
Tokenisation is transformers' VitsTokenizer itself, saved with the export: it keeps
only characters in the vocabulary (digits and most punctuation are dropped: write
numbers as words). tests/test_mms_tts.py checks it against the Hub's tokenizer.
Everything these voices say is labelled Preview: pronunciation is not reviewed.
"""

import json
import sys
from pathlib import Path

import numpy as np

import config

MMS_DIR = config.MODELS_DIR / "mms-tts"
NAMES = {"unr": "Mundari", "hoc": "Ho"}


def to_model_script(text):
    from translit.odia import deva_to_odia, olchiki_to_odia
    if any(0x118A0 <= ord(c) <= 0x118FF for c in text):
        raise ValueError("Warang Citi is not supported yet: write the line in Devanagari")
    if any(0x1C50 <= ord(c) <= 0x1C7F for c in text):
        return olchiki_to_odia(text)
    return deva_to_odia(text)


class MmsVoice:
    def __init__(self, lang, threads=2):
        import onnxruntime as ort
        d = MMS_DIR / lang
        self.lang = lang
        self.meta = json.loads((d / "tts.json").read_text(encoding="utf-8"))
        self.vocab = {}
        for line in (d / "tokens.txt").read_text(encoding="utf-8").split("\n"):
            if line:
                ch, i = line.rsplit(" ", 1)
                self.vocab[ch if ch else " "] = int(i)
        so = ort.SessionOptions()
        so.intra_op_num_threads = threads
        self.sess = ort.InferenceSession(str(d / "model.onnx"), so, providers=["CPUExecutionProvider"])
        self._tok = None

    def ids(self, odia_text):
        """The model's input ids, from transformers' own VitsTokenizer saved with the model.
        (Its pad token is an ordinary letter, ହ for Mundari and ଟ for Ho, which the
        tokenizer treats as a special token wherever it occurs; reproducing that by
        hand risks a mismatch, so the real tokenizer is used.)"""
        if self._tok is None:
            from transformers import AutoTokenizer
            self._tok = AutoTokenizer.from_pretrained(str(MMS_DIR / self.lang / "tokenizer"))
        return self._tok(odia_text).input_ids

    def oov(self, odia_text):
        """Characters the voice cannot say (dropped)."""
        text = odia_text.lower() if self.meta.get("normalize", True) else odia_text
        return sorted({c for c in text if c not in self.vocab})

    def synth(self, text):
        ids = self.ids(to_model_script(text))
        if len(ids) <= 1:
            raise ValueError("nothing the voice can say in this line")
        w = self.sess.run(None, {"input_ids": np.array([ids], dtype=np.int64)})[0][0]
        return w.astype(np.float32), self.meta["sample_rate"]


def available(lang):
    return (MMS_DIR / lang / "model.onnx").is_file()


if __name__ == "__main__":
    import soundfile as sf
    v = MmsVoice(sys.argv[1])
    w, sr = v.synth(sys.argv[2])
    sf.write(sys.argv[3], w, sr)
    print(f"{len(w) / sr:.2f} s -> {sys.argv[3]}")
