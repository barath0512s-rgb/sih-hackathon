# Thread counts (Phase L4)

Median ms. Laptop, offline; 20 logical CPUs; Intel64 Family 6 Model 154 Stepping 3, GenuineIntel.
Translation: ONNX Runtime fp32, 40 FLEURS Hindi references. Speech recognition: IndicConformer (CTC), 30 FLEURS clips.

| Threads | 2 | 4 | 6 | 8 | 14 |
|---|---|---|---|---|---|
| Translation | 585 | 520 | 508 | 628 | 1278 |
| Speech recognition | 853 | 716 | 591 | 520 | 875 |

Fastest: translation 6 threads, speech recognition 8 threads.
