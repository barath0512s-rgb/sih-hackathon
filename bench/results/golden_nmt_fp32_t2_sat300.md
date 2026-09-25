# Golden test: ONNX fp32 vs PyTorch, IndicTrans2 indic-indic-dist-320M

- 300 Santali sentences (IN22-Conv, in order); sat_Olck -> hin_Deva;
  greedy, no-repeat 3-gram, the app's length cap. 2 threads each. Laptop, offline.

| Measure | Result |
|---|---|
| Identical token IDs | 300 of 300 (100.0%) |
| chrF++ of ONNX output vs PyTorch output | 100.0 |
| Median time per sentence, PyTorch | 599 ms |
| Median time per sentence, ONNX fp32 | 321 ms |
