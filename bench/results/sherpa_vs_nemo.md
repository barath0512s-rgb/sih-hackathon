# sherpa-onnx export vs NeMo (IndicConformer 120M, CTC)

Laptop (WSL2, Ubuntu), 2 threads, greedy CTC; WER/CER normalised (bench/README.md). Clips: `bench/clips/public/manifest.json`. NeMo transcripts from the export notebook (same clips, NeMo CTC).

| Lang | Model | n | Same as NeMo | WER vs NeMo | WER vs ref | CER vs ref | NeMo WER vs ref | Median ms | Size MB |
|---|---|---|---|---|---|---|---|---|---|
| hi | model.int8.onnx | 80 | 35/80 | 5.5% | 11.8% | 4.6% | 11.0% | 601 | 138 |
| hi | model.onnx | 80 | 56/80 | 3.1% | 11.6% | 4.5% | 11.0% | 528 | 482 |
| sat | model.int8.onnx | 80 | 11/80 | 23.6% | 39.2% | 13.2% | 37.3% | 451 | 138 |
| sat | model.onnx | 80 | 39/80 | 10.8% | 37.4% | 12.4% | 37.3% | 406 | 482 |
