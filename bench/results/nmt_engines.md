# Translation engines, same sentences (Phase L1)

IndicTrans2 indic-indic-dist-320M, hin_Deva → sat_Olck, greedy, the app's settings. Laptop, offline.
Median ms per sentence. "same" = token IDs identical to PyTorch fp32 (14 threads).
public = FLEURS Hindi references (long); lesson = Hindi lesson lines (short).
Distinct sentences: public n=80 clips, n_distinct=69; lesson n=30, n_distinct=30.

| Engine | public 0-11 | 12-17 | 18-23 | 24+ | public all | lesson all | same as PyTorch |
|---|---|---|---|---|---|---|---|
| torch-fp32-t14 | 1147 | 1274 | 1544 | 1798 | 1455 | 520 | 99 of 99 |
| torch-fp32-t4 | 895 | 860 | 1074 | 1259 | 1025 | 376 | 99 of 99 |
| torch-int8-t4 | 946 | 955 | 1111 | 1425 | 1111 | 410 | 15 of 99 |
| onnx-fp32-t6 | 459 | 417 | 513 | 657 | 504 | 213 | 99 of 99 |
| onnx-int8-t6 | 203 | 209 | 252 | 325 | 244 | 96 | 42 of 99 |
