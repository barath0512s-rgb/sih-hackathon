# Golden test: ONNX int8 vs PyTorch, IndicTrans2 indic-indic-dist-320M

- 300 Santali sentences (IN22-Conv, in order); sat_Olck -> hin_Deva;
  greedy, no-repeat 3-gram, the app's length cap. 2 threads each. Laptop, offline.

| Measure | Result |
|---|---|
| Identical token IDs | 109 of 300 (36.3%) |
| chrF++ of ONNX output vs PyTorch output | 81.7 |
| Median time per sentence, PyTorch | 587 ms |
| Median time per sentence, ONNX int8 | 115 ms |
