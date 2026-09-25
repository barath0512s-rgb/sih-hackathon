# %% [markdown]
# # IndicConformer 120M (Hindi, Santali) -> sherpa-onnx CTC, INT8
#
# F1 Phase A. Runs in **WSL2 or Colab with Python 3.10** and AI4Bharat's NeMo
# fork (branch `nemo-v2`, as the model cards say). The `.nemo` files are gated:
# download them where you are logged in, then pass their paths.
#
#     python tools/export/indicconformer_sherpa_export.py \
#         --nemo hi=models/indicconformer-120m/hi/indicconformer_stt_hi_hybrid_rnnt_large.nemo \
#         --nemo sat=models/indicconformer-120m/sat/indicconformer_stt_sat_hybrid_rnnt_large.nemo \
#         --clips bench/clips/public/manifest.json --out models/indicconformer-120m-sherpa
#
# **Multisoftmax.** Each model's output layer covers 22 languages (5632 tokens,
# 256 per language, plus blank); NeMo masks it to the requested language. The
# CTC head is a 1x1 convolution, so keeping only that language's 256 rows and the
# blank row gives exactly the masked logits, and the same log-softmax. This
# script does that slice, then checks it instead of trusting it: NeMo's own CTC
# transcripts vs greedy decoding of the exported graph on the same clips.
#
# Writes, per language, into `<out>/<lang>/`:
# - `model.onnx` and `model.int8.onnx` (dynamic QUInt8, as sherpa-onnx's own NeMo
#   export does), with sherpa-onnx metadata
# - `tokens.txt` (`<piece> <id>`, blank last)
# - `inspect.json`: the facts read from the model
# - `nemo_transcripts.json`: NeMo CTC transcripts of the clips, and the exported
#   graph's own greedy transcripts (fp32), for `compare_nemo_sherpa.py`

# %% Imports and arguments
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch


def parse():
    ap = argparse.ArgumentParser(description="IndicConformer 120M -> sherpa-onnx CTC")
    ap.add_argument("--nemo", action="append", required=True, metavar="LANG=PATH")
    ap.add_argument("--clips", type=Path, help="bench manifest (wav files next to it, paths from repo root)")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument("--out", type=Path, required=True)
    return ap.parse_args()


# %% The sliced CTC head and the exported graph
class CtcForLanguage(torch.nn.Module):
    """Encoder + the language's rows of the CTC head + log-softmax.
    Inputs: audio_signal (B, 80, T) log-mel, length (B,). Output: logprobs (B, T', 257)."""

    def __init__(self, model, rows):
        super().__init__()
        self.encoder = model.encoder
        conv = model.ctc_decoder.decoder_layers[0]
        self.head = torch.nn.Conv1d(conv.in_channels, len(rows), kernel_size=1)
        with torch.no_grad():
            self.head.weight.copy_(conv.weight[rows])
            self.head.bias.copy_(conv.bias[rows])

    def forward(self, audio_signal, length):
        enc, enc_len = self.encoder(audio_signal=audio_signal, length=length)
        logits = self.head(enc).transpose(1, 2)
        return torch.log_softmax(logits, dim=-1), enc_len


def language_rows(model, lang):
    tok = model.tokenizer
    offset = tok.token_id_offset[lang]
    n = tok.tokenizers_dict[lang].vocab_size
    conv = model.ctc_decoder.decoder_layers[0]
    blank = conv.out_channels - 1
    return list(range(offset, offset + n)) + [blank], offset, n, blank


def pieces(model, lang):
    t = model.tokenizer.tokenizers_dict[lang]
    return [t.ids_to_tokens([i])[0] for i in range(t.vocab_size)]


def greedy(logprobs, toks):
    ids = logprobs.argmax(-1)
    out, prev = [], -1
    blank = len(toks)
    for i in ids:
        if i != prev and i != blank:
            out.append(toks[i])
        prev = i
    return "".join(out).replace("▁", " ").strip()


# %% Export one language
def export(lang, nemo_path, a):
    import nemo.collections.asr as nemo_asr
    import onnx
    import onnxruntime as ort
    import soundfile as sf
    from onnxruntime.quantization import QuantType, quantize_dynamic

    model = nemo_asr.models.ASRModel.restore_from(str(nemo_path), map_location="cpu")
    model.eval()
    model.preprocessor.featurizer.dither = 0.0
    model.preprocessor.featurizer.pad_to = 0
    cfg = model.cfg
    rows, offset, n, blank = language_rows(model, lang)
    toks = pieces(model, lang)
    d = a.out / lang
    d.mkdir(parents=True, exist_ok=True)
    info = {
        "nemo": str(nemo_path), "class": type(model).__name__, "language": lang,
        "tokenizer": type(model.tokenizer).__name__, "tokenizer_langs": list(model.tokenizer.tokenizers_dict),
        "token_offset": offset, "language_vocab": n, "head_outputs": model.ctc_decoder.decoder_layers[0].out_channels,
        "blank_row": blank,
        "multisoftmax": bool(cfg.decoder.get("multisoftmax", False)),
        "preprocessor": {k: cfg.preprocessor.get(k) for k in ("sample_rate", "features", "n_fft", "window_size",
                                                               "window_stride", "window", "normalize", "log")},
        "subsampling_factor": cfg.encoder.get("subsampling_factor"),
        "encoder_layers": cfg.encoder.get("n_layers"), "d_model": cfg.encoder.get("d_model"),
    }
    (d / "inspect.json").write_text(json.dumps(info, indent=1, default=str), encoding="utf-8")
    print(json.dumps(info, indent=1, default=str), flush=True)

    net = CtcForLanguage(model, rows).eval()
    x = torch.randn(1, 80, 400)
    xl = torch.tensor([400])
    onnx_path = d / "model.onnx"
    with torch.no_grad():
        torch.onnx.export(net, (x, xl), str(onnx_path), opset_version=17,
                          input_names=["audio_signal", "length"], output_names=["logprobs", "encoded_lengths"],
                          dynamic_axes={"audio_signal": {0: "B", 2: "T"}, "length": {0: "B"},
                                        "logprobs": {0: "B", 1: "T_out"}, "encoded_lengths": {0: "B"}})
    with open(d / "tokens.txt", "w", encoding="utf-8") as f:
        for i, t in enumerate(toks):
            f.write(f"{t} {i}\n")
        f.write(f"<blk> {n}\n")
    m = onnx.load(str(onnx_path))
    meta = {"vocab_size": str(n + 1), "normalize_type": str(cfg.preprocessor.get("normalize") or ""),
            "subsampling_factor": str(cfg.encoder.get("subsampling_factor")),
            "model_type": "EncDecCTCModelBPE", "version": "1", "model_author": "AI4Bharat",
            "url": f"https://huggingface.co/ai4bharat/indicconformer_stt_{lang}_hybrid_ctc_rnnt_large",
            "comment": f"CTC branch only, output layer sliced to language '{lang}' "
                       f"(rows {offset}-{offset + n - 1} and blank {blank} of multisoftmax head)"}
    del m.metadata_props[:]
    for k, v in meta.items():
        p = m.metadata_props.add()
        p.key, p.value = k, v
    onnx.save(m, str(onnx_path))
    quantize_dynamic(str(onnx_path), str(d / "model.int8.onnx"), weight_type=QuantType.QUInt8)
    for f in ("model.onnx", "model.int8.onnx", "tokens.txt"):
        print(f"{lang} {f}: {(d / f).stat().st_size / 1e6:.1f} MB", flush=True)

    # Check: NeMo's own CTC transcripts vs the exported graph on NeMo features.
    if a.clips:
        clips = [c for c in json.loads(a.clips.read_text(encoding="utf-8")) if c["lang"] == lang]
        files = [str(a.root / c["file"]) for c in clips]
        model.cur_decoder = "ctc"
        with torch.no_grad():
            hyps = model.transcribe(files, batch_size=1, logprobs=False, language_id=lang)
        if isinstance(hyps, tuple):
            hyps = hyps[0]
        nemo = [h.text if hasattr(h, "text") else h for h in hyps]
        sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        mine = []
        for f in files:
            wav, sr = sf.read(f, dtype="float32")
            assert sr == 16000, f
            with torch.no_grad():
                feats, fl = model.preprocessor(input_signal=torch.tensor(wav)[None], length=torch.tensor([len(wav)]))
            lp = sess.run(None, {"audio_signal": feats.numpy(), "length": fl.numpy().astype(np.int64)})[0][0]
            mine.append(greedy(lp, toks))
        same = sum(x.strip() == y for x, y in zip(nemo, mine))
        print(f"{lang}: exported graph (fp32, NeMo features) equals NeMo CTC on {same} of {len(files)} clips",
              flush=True)
        (d / "nemo_transcripts.json").write_text(json.dumps(
            {"nemo_ctc": {c["file"]: h for c, h in zip(clips, nemo)},
             "onnx_fp32_nemo_features": {c["file"]: h for c, h in zip(clips, mine)},
             "same": same, "n": len(files)}, ensure_ascii=False, indent=0), encoding="utf-8")


# %% Main
if __name__ == "__main__":
    a = parse()
    for kv in a.nemo:
        lang, path = kv.split("=", 1)
        export(lang, Path(path), a)
