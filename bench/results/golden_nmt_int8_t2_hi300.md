# Golden test: ONNX int8 vs PyTorch, IndicTrans2 indic-indic-dist-320M

- 300 Hindi sentences (lesson lines, team lessons, FLEURS references, then IN22-Conv); hin_Deva -> sat_Olck;
  greedy, no-repeat 3-gram, the app's length cap. 2 threads each. Laptop, offline.

| Measure | Result |
|---|---|
| Identical token IDs | 154 of 300 (51.3%) |
| chrF++ of ONNX output vs PyTorch output | 90.0 |
| Median time per sentence, PyTorch | 612 ms |
| Median time per sentence, ONNX int8 | 125 ms |
