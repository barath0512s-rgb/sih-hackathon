# Translation engines, same sentences (Phase L1)

IndicTrans2 indic-indic-dist-320M, hin_Deva → sat_Olck, greedy, the app's settings. Laptop, offline.
Median ms per sentence. "same" = token IDs identical to PyTorch fp32 (14 threads).
public = FLEURS Hindi references (long); lesson = Hindi lesson lines (short).

| Engine | public 0-11 | 12-17 | 18-23 | 24+ | public all | lesson all | same as PyTorch |
|---|---|---|---|---|---|---|---|
| torch-fp32-t14 | 1130 | 1223 | 1563 | 1796 | 1450 | 534 | 110 of 110 |
| torch-fp32-t4 | 786 | 819 | 1012 | 1272 | 968 | 343 | 110 of 110 |
| torch-int8-t4 | 724 | 733 | 987 | 1178 | 901 | 349 | 16 of 110 |
| onnx-fp32-t6 | 404 | 413 | 515 | 609 | 504 | 188 | 110 of 110 |
| onnx-int8-t6 | 162 | 192 | 238 | 320 | 228 | 87 | 43 of 110 |
