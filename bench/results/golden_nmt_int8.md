# Golden test: ONNX int8 vs PyTorch, IndicTrans2 indic-indic-dist-320M

- 176 Hindi sentences (lesson lines, team lessons, FLEURS references); hin_Deva -> sat_Olck;
  greedy, no-repeat 3-gram, the app's length cap. 4 threads each. Laptop, offline.

| Measure | Result |
|---|---|
| Identical token IDs | 89 of 176 (50.6%) |
| chrF++ of ONNX output vs PyTorch output | 89.5 |
| Median time per sentence, PyTorch | 662 ms |
| Median time per sentence, ONNX int8 | 115 ms |
