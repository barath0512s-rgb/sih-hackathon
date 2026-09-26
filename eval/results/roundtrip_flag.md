# Round-trip check (A3): does back-translation find the worst translations?

- IN22-Conv, 1503 Hindi–Santali pairs (CC BY 4.0), never used for training. Forward: the app's model (`hyp_in22-conv_hin_Deva-sat_Olck.txt`); back-translation by the same model (onnx-fp32 (config.NMT_BACKEND at the time of the forward run; see eval/results/benchmarks.md)).
- Sentence chrF (sacrebleu defaults). **Worst** = forward chrF against the reference below the tune half's 25th percentile (23.3). Flag = round-trip chrF against the Hindi source below the threshold.
- Halves: a random split of the 1503 sentences with a fixed seed (20260927): tune 751, test 752. The 'worst' cut and the threshold come from the tune half only; the test half is scored once.
- An earlier version split by a hash of the Hindi sentence (tune 765, test 738): threshold 34.5, test precision 0.446, recall 0.558. The seeded split is the one reported.

**Threshold 29.0. Test half: precision 0.464, recall 0.449** (84 of 187 worst translations flagged; 181 of 752 sentences flagged). Tune half: precision 0.484, recall 0.492.

- Spearman correlation between round-trip chrF and forward chrF on the test half: 0.268.
- The flag cannot see errors the model makes the same way in both directions (a wrong word translated back to the right Hindi word); it is a warning, not a quality score.

| Threshold (test half) | Precision | Recall | Flagged |
|---|---|---|---|
| 20.0 | 0.618 | 0.251 | 76 |
| 30.0 | 0.455 | 0.465 | 191 |
| 40.0 | 0.339 | 0.610 | 336 |
| 50.0 | 0.286 | 0.722 | 472 |
| 60.0 | 0.266 | 0.850 | 597 |
