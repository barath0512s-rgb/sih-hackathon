# Round-trip check (A3): does back-translation find the worst translations?

- IN22-Conv, 1503 Hindi–Santali pairs (CC BY 4.0), never used for training. Forward: the app's model (`hyp_in22-conv_hin_Deva-sat_Olck.txt`); back-translation by the same model (onnx-fp32).
- Sentence chrF (sacrebleu defaults). **Worst** = forward chrF against the reference below the tune half's 25th percentile (23.9). Flag = round-trip chrF against the Hindi source below the threshold.
- Halves by a hash of the Hindi sentence: tune 765, test 738. Threshold chosen for the best F1 on the tune half.

**Threshold 34.5. Test half: precision 0.446, recall 0.558** (116 of 208 worst translations flagged; 260 of 738 sentences flagged). Tune half: precision 0.396, recall 0.539.

- Spearman correlation between round-trip chrF and forward chrF on the test half: 0.295.
- The flag cannot see errors the model makes the same way in both directions (a wrong word translated back to the right Hindi word); it is a warning, not a quality score.

| Threshold (test half) | Precision | Recall | Flagged |
|---|---|---|---|
| 20.0 | 0.642 | 0.293 | 95 |
| 30.0 | 0.493 | 0.481 | 203 |
| 40.0 | 0.386 | 0.620 | 334 |
| 50.0 | 0.329 | 0.750 | 474 |
| 60.0 | 0.309 | 0.880 | 592 |
