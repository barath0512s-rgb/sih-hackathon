# Golden test: ONNX fp32 vs PyTorch, IndicTrans2 indic-indic-dist-320M

- 176 Hindi sentences (lesson lines, team lessons, FLEURS references); hin_Deva -> sat_Olck;
  greedy, no-repeat 3-gram, the app's length cap. 4 threads each. Laptop, offline.

| Measure | Result |
|---|---|
| Identical token IDs | 176 of 176 (100.0%) |
| chrF++ of ONNX output vs PyTorch output | 100.0 |
| Median time per sentence, PyTorch | 629 ms |
| Median time per sentence, ONNX fp32 | 276 ms |
