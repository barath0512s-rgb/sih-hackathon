# Golden test: ONNX int8pc vs PyTorch, IndicTrans2 indic-indic-dist-320M

- 176 Hindi sentences (lesson lines, team lessons, FLEURS references); hin_Deva -> sat_Olck;
  greedy, no-repeat 3-gram, the app's length cap. 4 threads each. Laptop, offline.

| Measure | Result |
|---|---|
| Identical token IDs | 90 of 176 (51.1%) |
| chrF++ of ONNX output vs PyTorch output | 89.2 |
| Median time per sentence, PyTorch | 640 ms |
| Median time per sentence, ONNX int8pc | 125 ms |
