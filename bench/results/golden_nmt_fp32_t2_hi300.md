# Golden test: ONNX fp32 vs PyTorch, IndicTrans2 indic-indic-dist-320M

- 300 Hindi sentences (lesson lines, team lessons, FLEURS references, then IN22-Conv); hin_Deva -> sat_Olck;
  greedy, no-repeat 3-gram, the app's length cap. 2 threads each. Laptop, offline.

| Measure | Result |
|---|---|
| Identical token IDs | 300 of 300 (100.0%) |
| chrF++ of ONNX output vs PyTorch output | 100.0 |
| Median time per sentence, PyTorch | 639 ms |
| Median time per sentence, ONNX fp32 | 344 ms |
