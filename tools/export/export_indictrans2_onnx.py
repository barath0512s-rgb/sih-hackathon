"""Export IndicTrans2 indic-indic-dist-320M to ONNX (fp32 and dynamic int8).

    python tools/export/export_indictrans2_onnx.py            # -> models/indictrans2-onnx/

Three graphs, the usual encoder-decoder split with a key/value cache:
  encoder.onnx         input_ids, attention_mask -> encoder_hidden_states
  decoder_init.onnx    decoder_input_ids, encoder_hidden_states, encoder_attention_mask
                       -> logits, present.{i}.{self_k,self_v,cross_k,cross_v} for 18 layers
  decoder_step.onnx    decoder_input_ids, encoder_hidden_states, encoder_attention_mask,
                       past.{i}.{...} -> logits, present.{i}.{self_k,self_v}
The cross-attention keys and values are computed once, by decoder_init, and
reused by every step. nmt_onnx.py runs the greedy loop.
int8: onnxruntime.quantization.quantize_dynamic (weights int8, activations
quantised on the fly), written next to the fp32 files as *.int8.onnx.

Shared with Phase F1 (Android): the same graphs are meant for ONNX Runtime
Android. Only the export is here; the laptop build does not depend on it.
"""

import argparse
import os
import sys
import time
from pathlib import Path

import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import config  # noqa: E402

OUT = config.MODELS_DIR / "indictrans2-onnx"
OPSET = 17


def load():
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(config.NMT_DIR), trust_remote_code=True)
    m = AutoModelForSeq2SeqLM.from_pretrained(str(config.NMT_DIR), trust_remote_code=True,
                                              attn_implementation="eager").eval()
    return tok, m


class Encoder(nn.Module):
    def __init__(self, m):
        super().__init__(); self.enc = m.model.encoder

    def forward(self, input_ids, attention_mask):
        return self.enc(input_ids=input_ids, attention_mask=attention_mask, return_dict=True).last_hidden_state


class DecoderInit(nn.Module):
    def __init__(self, m):
        super().__init__(); self.dec, self.head = m.model.decoder, m.lm_head

    def forward(self, decoder_input_ids, encoder_hidden_states, encoder_attention_mask):
        o = self.dec(input_ids=decoder_input_ids, encoder_hidden_states=encoder_hidden_states,
                     encoder_attention_mask=encoder_attention_mask, use_cache=True, return_dict=True)
        flat = [t for layer in o.past_key_values for t in layer]
        return (self.head(o.last_hidden_state), *flat)


class DecoderStep(nn.Module):
    def __init__(self, m):
        super().__init__(); self.dec, self.head = m.model.decoder, m.lm_head
        self.n = m.config.decoder_layers

    def forward(self, decoder_input_ids, encoder_hidden_states, encoder_attention_mask, *past):
        pkv = tuple(tuple(past[4 * i:4 * i + 4]) for i in range(self.n))
        o = self.dec(input_ids=decoder_input_ids, encoder_hidden_states=encoder_hidden_states,
                     encoder_attention_mask=encoder_attention_mask, past_key_values=pkv,
                     use_cache=True, return_dict=True)
        flat = [t for layer in o.past_key_values for t in layer[:2]]      # new self k, v only
        return (self.head(o.last_hidden_state), *flat)


def kv_names(prefix, n, cross=True):
    names = []
    for i in range(n):
        names += [f"{prefix}.{i}.self_k", f"{prefix}.{i}.self_v"]
        if cross:
            names += [f"{prefix}.{i}.cross_k", f"{prefix}.{i}.cross_v"]
    return names


def export(tok, m):
    OUT.mkdir(parents=True, exist_ok=True)
    n = m.config.decoder_layers
    src = tok(["hin_Deva sat_Olck यह एक छोटा वाक्य है ।"], return_tensors="pt")
    ids, mask = src["input_ids"], src["attention_mask"]
    with torch.no_grad():
        hid = Encoder(m)(ids, mask)
        start = torch.tensor([[m.config.decoder_start_token_id]])
        init_out = DecoderInit(m)(start, hid, mask)
        past = init_out[1:]

        t = time.time()
        torch.onnx.export(Encoder(m), (ids, mask), str(OUT / "encoder.onnx"), opset_version=OPSET,
                          input_names=["input_ids", "attention_mask"], output_names=["encoder_hidden_states"],
                          dynamic_axes={"input_ids": {1: "src"}, "attention_mask": {1: "src"},
                                        "encoder_hidden_states": {1: "src"}})
        print(f"encoder.onnx ({time.time() - t:.0f} s)")

        t = time.time()
        pres = kv_names("present", n)
        dyn = {"encoder_hidden_states": {1: "src"}, "encoder_attention_mask": {1: "src"}}
        for i in range(n):
            dyn[f"present.{i}.cross_k"] = {2: "src"}; dyn[f"present.{i}.cross_v"] = {2: "src"}
        torch.onnx.export(DecoderInit(m), (start, hid, mask), str(OUT / "decoder_init.onnx"), opset_version=OPSET,
                          input_names=["decoder_input_ids", "encoder_hidden_states", "encoder_attention_mask"],
                          output_names=["logits"] + pres, dynamic_axes=dyn)
        print(f"decoder_init.onnx ({time.time() - t:.0f} s)")

        t = time.time()
        pin = kv_names("past", n)
        pout = kv_names("present", n, cross=False)
        dyn = {"encoder_hidden_states": {1: "src"}, "encoder_attention_mask": {1: "src"}}
        for i in range(n):
            dyn[f"past.{i}.self_k"] = {2: "past"}; dyn[f"past.{i}.self_v"] = {2: "past"}
            dyn[f"past.{i}.cross_k"] = {2: "src"}; dyn[f"past.{i}.cross_v"] = {2: "src"}
            dyn[f"present.{i}.self_k"] = {2: "past1"}; dyn[f"present.{i}.self_v"] = {2: "past1"}
        nxt = torch.tensor([[int(init_out[0][0, -1].argmax())]])
        torch.onnx.export(DecoderStep(m), (nxt, hid, mask, *past), str(OUT / "decoder_step.onnx"),
                          opset_version=OPSET,
                          input_names=["decoder_input_ids", "encoder_hidden_states", "encoder_attention_mask"] + pin,
                          output_names=["logits"] + pout, dynamic_axes=dyn)
        print(f"decoder_step.onnx ({time.time() - t:.0f} s)")


def quantize(per_channel=False, suffix="int8"):
    from onnxruntime.quantization import QuantType, quantize_dynamic
    for name in ("encoder", "decoder_init", "decoder_step"):
        t = time.time()
        quantize_dynamic(str(OUT / f"{name}.onnx"), str(OUT / f"{name}.{suffix}.onnx"),
                         weight_type=QuantType.QInt8, per_channel=per_channel)
        print(f"{name}.{suffix}.onnx ({time.time() - t:.0f} s)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skip-export", action="store_true")
    ap.add_argument("--per-channel", action="store_true",
                    help="one int8 scale per output channel (writes *.int8pc.onnx)")
    ap.add_argument("--model-dir", help="a Hugging Face model folder to export instead of config.NMT_DIR "
                    "(e.g. a LoRA-merged Mundari model from notebooks/mundari_lora.ipynb)")
    ap.add_argument("--out", help="output folder instead of models/indictrans2-onnx")
    a = ap.parse_args()
    global OUT
    if a.model_dir:
        config.NMT_DIR = Path(a.model_dir)
    if a.out:
        OUT = Path(a.out)
        OUT.mkdir(parents=True, exist_ok=True)
    if not a.skip_export:
        tok, m = load()
        export(tok, m)
    quantize(per_channel=a.per_channel, suffix="int8pc" if a.per_channel else "int8")
    for f in sorted(OUT.glob("*.onnx")):
        print(f"  {f.name:28} {f.stat().st_size / 1e6:7.1f} MB")


if __name__ == "__main__":
    main()
