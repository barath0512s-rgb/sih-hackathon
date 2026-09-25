# sherpa-onnx transducer vs NeMo RNN-T (IndicConformer 120M)

Laptop (WSL2, Ubuntu), 2 threads. Public clips (`bench/clips/public/manifest.json`); WER/CER normalised (bench/README.md; tags removed from references only). NeMo = the fork's own RNN-T transcripts from the export script. Hallucinated = non-empty, WER vs NeMo >= 0.5 where NeMo's own WER vs the reference < 0.5. Beam = modified_beam_search, 4 paths; hotwords score 1.5.
Santali clips: IndicVoices validation split (no public Santali test split); may overlap model-development data.

| Lang | Model | Decoding | n | n_distinct | Same as NeMo | WER vs NeMo | WER vs ref | NeMo WER vs ref | Empty (NeMo non-empty) | Hallucinated | Changed by hotwords | Median ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hi | int8 | greedy | 80 | 69 | 46/80 | 4.2% | 11.0% | 10.9% | 0 | 0 |  | 581 |
| hi | int8 | beam | 80 | 69 | 44/80 | 4.5% | 10.9% | 10.9% | 0 | 0 |  | 684 |
| hi | int8 | beam+hotwords | 80 | 69 | 40/80 | 10.0% | 16.3% | 10.9% | 0 | 3 | 15 | 701 |
| hi | fp32 | greedy | 80 | 69 | 59/80 | 2.5% | 10.9% | 10.9% | 0 | 0 |  | 570 |
| hi | fp32 | beam | 80 | 69 | 56/80 | 2.8% | 10.8% | 10.9% | 0 | 0 |  | 924 |
| hi | fp32 | beam+hotwords | 80 | 69 | 51/80 | 8.6% | 16.5% | 10.9% | 0 | 2 | 15 | 886 |
| hi | | hotwords file | | | 11 accepted answers from the lessons | | | | | | | |
| sat | int8 | greedy | 80 | 80 | 30/80 | 18.0% | 35.8% | 34.5% | 0 | 2 |  | 448 |
| sat | int8 | beam | 80 | 80 | 29/80 | 18.3% | 35.8% | 34.5% | 0 | 2 |  | 528 |
| sat | int8 | beam+hotwords | 80 | 80 | 22/80 | 24.1% | 40.0% | 34.5% | 0 | 7 | 37 | 522 |
| sat | fp32 | greedy | 80 | 80 | 44/80 | 10.1% | 33.4% | 34.5% | 0 | 0 |  | 400 |
| sat | fp32 | beam | 80 | 80 | 36/80 | 12.0% | 33.2% | 34.5% | 0 | 1 |  | 677 |
| sat | fp32 | beam+hotwords | 80 | 80 | 26/80 | 17.0% | 36.2% | 34.5% | 0 | 4 | 34 | 692 |
| sat | | hotwords file | | | 9 accepted answers from the lessons | | | | | | | |
