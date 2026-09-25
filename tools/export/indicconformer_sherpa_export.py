# %% [markdown]
# # IndicConformer 120M (Hindi, Santali) -> sherpa-onnx CTC, INT8
#
# F1 Phase A. Run this in **Google Colab** (Python 3.10/3.11) or **WSL2 with a
# Python 3.10 environment**. AI4Bharat's NeMo fork (branch `nemo-v2`) is
# needed, as the model cards say. The models are gated: log in with a Hugging
# Face account that has accepted their terms.
#
# What it writes, per language, into `out/<lang>/`:
# - `model.onnx`, then `model.int8.onnx`: the CTC path only, with sherpa-onnx metadata
# - `tokens.txt`: `<token> <id>` lines, the CTC blank last
# - `inspect.json`: the model facts this export relied on (read from the model, not assumed)
# - `nemo_transcripts.json`: NeMo's own CTC transcripts of the public clips (Phase P
#   manifest), for comparison with sherpa-onnx on the laptop (`compare_nemo_sherpa.py`)
#
# The script **stops with a message** instead of guessing when the model is
# multilingual with per-language output masks, or when the preprocessor is one
# sherpa-onnx cannot reproduce.

# %% Install (Colab: run once, then restart the runtime if asked)
import os
import subprocess
import sys

IN_COLAB = "google.colab" in sys.modules
if IN_COLAB and not os.path.exists("NeMo"):
    subprocess.run("git clone https://github.com/AI4Bharat/NeMo.git && cd NeMo && git checkout nemo-v2 && "
                   "bash reinstall.sh", shell=True, check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "onnx", "onnxruntime", "huggingface_hub",
                    "soundfile"], check=True)

# %% Log in (a token with access to the two gated models). Never write the token to a file you commit.
from huggingface_hub import hf_hub_download, login  # noqa: E402

if IN_COLAB:
    login()          # paste the token when asked

# %% Settings
REPOS = {
    "hi": ("ai4bharat/indicconformer_stt_hi_hybrid_ctc_rnnt_large", "indicconformer_stt_hi_hybrid_rnnt_large.nemo"),
    "sat": ("ai4bharat/indicconformer_stt_sat_hybrid_ctc_rnnt_large", "indicconformer_stt_sat_hybrid_rnnt_large.nemo"),
}
OUT = os.path.abspath("out")
# The Phase P clips: copy bench/clips/public/ (manifest + wav files) next to this script,
# or leave it out to skip the transcripts.
CLIPS = os.path.abspath("public")

# %% Load, inspect, export
import json  # noqa: E402

import torch  # noqa: E402
import nemo.collections.asr as nemo_asr  # noqa: E402


def inspect(model, lang):
    cfg = model.cfg
    pre = cfg.preprocessor
    info = {
        "class": type(model).__name__,
        "tokenizer": type(model.tokenizer).__name__,
        "vocab_size": int(getattr(model.tokenizer, "vocab_size", len(getattr(model.tokenizer, "vocab", [])))),
        "preprocessor": {k: pre.get(k) for k in ("_target_", "sample_rate", "features", "n_fft", "window_size",
                                                  "window_stride", "window", "normalize", "dither", "log",
                                                  "frame_splicing", "pad_to")},
        "subsampling_factor": cfg.encoder.get("subsampling_factor"),
        "encoder_layers": cfg.encoder.get("n_layers"),
        "d_model": cfg.encoder.get("d_model"),
        "multisoftmax": bool(cfg.get("decoder", {}).get("multisoftmax", False))
                        or hasattr(model, "language_masks") and bool(getattr(model, "language_masks")),
        "aux_ctc": bool(cfg.get("aux_ctc")),
        "language": lang,
    }
    if hasattr(model, "language_masks") and model.language_masks:
        info["language_mask_keys"] = sorted(model.language_masks.keys())
    return info


def export(lang):
    repo, fname = REPOS[lang]
    path = hf_hub_download(repo, fname)
    model = nemo_asr.models.ASRModel.restore_from(path, map_location="cpu")
    model.eval()
    d = os.path.join(OUT, lang)
    os.makedirs(d, exist_ok=True)
    info = inspect(model, lang)
    json.dump(info, open(os.path.join(d, "inspect.json"), "w"), indent=1, default=str)
    print(json.dumps(info, indent=1, default=str))

    if info["multisoftmax"]:
        raise SystemExit(f"{lang}: multisoftmax model (per-language output masks {info.get('language_mask_keys')}). "
                         "Exporting it for sherpa-onnx needs the mask baked into the CTC head: stop and report.")
    if str(info["preprocessor"].get("normalize")) not in ("per_feature", "None", "none"):
        raise SystemExit(f"{lang}: preprocessor normalize={info['preprocessor'].get('normalize')}: check "
                         "sherpa-onnx supports it before exporting.")

    model.cur_decoder = "ctc"
    model.set_export_config({"decoder_type": "ctc"})
    onnx_path = os.path.join(d, "model.onnx")
    model.export(onnx_path)

    vocab = list(model.tokenizer.vocab) if hasattr(model.tokenizer, "vocab") else \
        [model.tokenizer.ids_to_tokens([i])[0] for i in range(info["vocab_size"])]
    with open(os.path.join(d, "tokens.txt"), "w", encoding="utf-8") as f:
        for i, t in enumerate(vocab):
            f.write(f"{t} {i}\n")
        f.write(f"<blk> {len(vocab)}\n")

    import onnx
    m = onnx.load(onnx_path)
    meta = {"vocab_size": str(len(vocab) + 1), "normalize_type": str(info["preprocessor"].get("normalize") or ""),
            "subsampling_factor": str(info["subsampling_factor"]), "model_type": "EncDecCTCModelBPE",
            "version": "1", "model_author": "AI4Bharat", "url": f"https://huggingface.co/{repo}",
            "comment": f"IndicConformer 120M {lang}, CTC branch, exported for sherpa-onnx (VaaniSetu F1)",
            "language": lang}
    for k, v in meta.items():
        p = m.metadata_props.add(); p.key, p.value = k, v
    onnx.save(m, onnx_path)

    from onnxruntime.quantization import QuantType, quantize_dynamic
    quantize_dynamic(onnx_path, os.path.join(d, "model.int8.onnx"), weight_type=QuantType.QUInt8)
    for f in ("model.onnx", "model.int8.onnx", "tokens.txt"):
        print(f, os.path.getsize(os.path.join(d, f)) / 1e6, "MB")

    # NeMo's own CTC transcripts of the public clips, for the comparison on the laptop.
    man = os.path.join(CLIPS, "manifest.json")
    if os.path.exists(man):
        clips = [c for c in json.load(open(man, encoding="utf-8")) if c["lang"] == lang]
        files = [os.path.join(CLIPS, os.path.relpath(c["file"], "bench/clips/public")) for c in clips]
        with torch.no_grad():
            hyps = model.transcribe(files, batch_size=1, logprobs=False, language_id=lang)
        if isinstance(hyps, tuple):
            hyps = hyps[0]
        hyps = [h.text if hasattr(h, "text") else h for h in hyps]
        json.dump({c["file"]: h for c, h in zip(clips, hyps)},
                  open(os.path.join(d, "nemo_transcripts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        print(f"{lang}: {len(hyps)} NeMo transcripts written")


for lang in ("hi", "sat"):
    export(lang)

# %% Download the results (Colab): out/ as a zip
if IN_COLAB:
    subprocess.run("cd out && zip -r ../indicconformer_sherpa.zip .", shell=True, check=True)
    from google.colab import files
    files.download("indicconformer_sherpa.zip")
