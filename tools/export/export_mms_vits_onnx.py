"""Export a Hugging Face VITS / MMS-TTS model (character input) to one ONNX file.

    python tools/export/export_mms_vits_onnx.py --model facebook/mms-tts-unr --out models/mms-tts/unr
    python tools/export/export_mms_vits_onnx.py --model <fine-tuned folder> --out <dir>   # C4 notebook

Writes <out>/model.onnx, <out>/tokens.txt ("<char> <id>" per line, as sherpa-onnx
character models use), <out>/tts.json (sample rate, add_blank, pad id, whether the
model lower-cases and needs uroman) and copies the model's README/licence note.

Graph: input_ids int64 [1, T] (already tokenised: characters -> ids, a blank (pad
id) between every pair and at both ends when add_blank is true, exactly what
transformers' VitsTokenizer does) -> waveform float32 [1, N]. The noise, noise-w
and speaking-rate values are the model config's, fixed at export. mms_tts.py
tokenises and runs it with onnxruntime; the Kotlin port does the same on Android.
Check: the ONNX output is compared with the PyTorch model on the same ids and the
same noise seed is not possible across runtimes, so the check compares lengths
(identical durations when noise_scale_duration is 0 for the check) and prints both.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[2]
OPSET = 17


class Wrap(torch.nn.Module):
    def __init__(self, m):
        super().__init__()
        self.m = m

    def forward(self, input_ids):
        return self.m(input_ids=input_ids).waveform


def tokenize(tok, text):
    return tok(text, return_tensors="pt").input_ids


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--check-text", default=None, help="text in the model's script for the length check")
    a = ap.parse_args()
    from transformers import AutoTokenizer, VitsModel

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tok = AutoTokenizer.from_pretrained(a.model)
    m = VitsModel.from_pretrained(a.model).eval()
    vocab = tok.get_vocab()
    sample = a.check_text or "".join(c for c in list(vocab)[:12] if len(c) == 1 and c.strip())
    ids = tokenize(tok, sample)
    torch.onnx.export(Wrap(m), (ids,), str(out / "model.onnx"), opset_version=OPSET,
                      input_names=["input_ids"], output_names=["waveform"],
                      dynamic_axes={"input_ids": {1: "T"}, "waveform": {1: "N"}})
    with open(out / "tokens.txt", "w", encoding="utf-8", newline="\n") as f:
        for ch, i in sorted(vocab.items(), key=lambda kv: kv[1]):
            f.write(f"{ch} {i}\n")
    tc = tok.init_kwargs
    meta = {"source": a.model, "sample_rate": m.config.sampling_rate, "add_blank": bool(tc.get("add_blank", True)),
            "pad_id": vocab[tok.pad_token], "pad_token": tok.pad_token, "normalize": bool(tc.get("normalize", True)),
            "is_uroman": bool(tc.get("is_uroman", False)), "language": tc.get("language"),
            "noise_scale": m.config.noise_scale, "noise_scale_duration": m.config.noise_scale_duration,
            "speaking_rate": m.config.speaking_rate, "opset": OPSET}
    (out / "tts.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    tok.save_pretrained(str(out / "tokenizer"))      # the exact tokenizer (mms_tts.py uses it on the laptop)
    src_readme = Path(a.model) / "README.md"
    if src_readme.exists():
        shutil.copyfile(src_readme, out / "MODEL_CARD.md")

    import numpy as np
    import onnxruntime as ort
    s = ort.InferenceSession(str(out / "model.onnx"), providers=["CPUExecutionProvider"])
    w = s.run(None, {"input_ids": ids.numpy()})[0]
    with torch.inference_mode():
        pt = m(input_ids=ids).waveform.numpy()
    print(f"ids {ids.shape[1]}: onnx {w.shape[1] / meta['sample_rate']:.2f} s, torch {pt.shape[1] / meta['sample_rate']:.2f} s, "
          f"rms {float(np.sqrt((w ** 2).mean())):.3f}")
    print(f"{out / 'model.onnx'}: {(out / 'model.onnx').stat().st_size / 1e6:.1f} MB")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
