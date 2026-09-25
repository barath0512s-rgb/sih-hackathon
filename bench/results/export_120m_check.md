# IndicConformer 120M export check (F1 Phase A)

Exported in WSL2 (Ubuntu 26.04, Python 3.10.21, AI4Bharat NeMo `nemo-v2` @ 8dce88cf8, torch 2.3.1 CPU) with
`tools/export/indicconformer_sherpa_export.py`. Model files are git-ignored (`models/`).

Each model is **multisoftmax**: one CTC head of 5633 outputs (22 languages x 256 tokens + blank); NeMo masks it
to the requested language. The export keeps only that language's 256 rows and the blank row. Check: greedy CTC
from the exported graph (fp32, NeMo's own features) against NeMo's CTC transcript, on the public clips.

| Lang | .nemo SHA-256 (first 16) | Token rows | Blank row | Exported graph = NeMo CTC | model.onnx MB | model.int8.onnx MB |
|---|---|---|---|---|---|---|
| hi | 7cad1308751a56ae | 1536-1791 | 5632 | 80 of 80 | 482 | 138 |
| sat | 98435e5a0fecbb76 | 4352-4607 | 5632 | 80 of 80 | 482 | 138 |

Preprocessor (from the model): 16 kHz, 80 mel features, n_fft 512, 25 ms window, 10 ms stride, hann,
per-feature normalisation; encoder 17 conformer layers, d_model 512, subsampling 4.
sherpa-onnx computes its own features, so its transcripts can differ: see `sherpa_vs_nemo.md`.
