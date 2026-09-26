# Lesson-line matching (A1): threshold tuned on synthetic lesson clips

- Pack: `content-pack-20260926-1532.zip`. Clips and definitions: `bench/lesson_match_tune.py` docstring. Speech recognition: sherpa-onnx 1.13.8 int8 on the laptop, the tablet's models and settings (Hindi CTC, Santali transducer with silence trimming), 2 threads.
- **Positives are synthetic** (Piper, one voice: the pack's own audio, faster, slower + noise). Negatives: real speech (80 public clips per language, FLEURS / IndicVoices) and IN22-Conv sentences in the same Piper voice. Children's and teachers' real voices: **NOT MEASURED**.
- Threshold = the lowest with tune precision >= 0.98; scored on the held-out test half (different lines). The rule was fixed before the first scoring; the test half had been seen when the near-misses and the number rule below were added.
- A match needs the same numbers as the line (`lesson_match.number_tokens`), and the negatives include near-misses (a lesson line with one word or one number changed). **Both were added after the first tuning**, when a unit test showed an everyday sentence matching an unrelated lesson line at 0.51 (first tuning: Hindi threshold 0.41, test precision 0.970, recall 0.871, without near-misses).
- A line and the same line written with digits ("4" / "चार") count as the same line (numbers are compared as words; `lesson_match.canonical`). Added after the first scoring showed these as 'wrong line'.
- Errors no threshold removes: one-word lines misheard as another one-word line score 1.0 (e.g. Santali ᱜᱮᱞ recognised as ᱯᱮ).

## Hindi (teacher's lesson line → Santali)

- Candidates: 189 pack lines. Clips: {'pos_tune': 303, 'pos_test': 264, 'neg_tune': 233, 'neg_test': 251}.
- **Threshold 0.90.** Test half: **precision 0.979, recall 0.723** (191 of 264 positives matched to their own line; accepted 195; negatives accepted 4; wrong line 0). Tune half: precision 0.990, recall 0.637.

| Test half, positives of one version + all negatives | Precision | Recall |
|---|---|---|
| pack audio | 0.946 | 0.795 |
| piper 0.85 | 0.947 | 0.818 |
| piper 1.2 + noise 15 dB | 0.925 | 0.557 |

| Test half, negatives of one kind | Accepted / total |
|---|---|
| IN22-Conv, piper | 0 / 100 |
| near-miss: number swap | 0 / 34 |
| near-miss: word swap | 4 / 73 |
| real speech (public clip) | 0 / 44 |

| Threshold (test half) | Precision | Recall | Negatives accepted |
|---|---|---|---|
| 0.50 | 0.765 | 0.852 | 66 |
| 0.60 | 0.778 | 0.837 | 62 |
| 0.70 | 0.791 | 0.818 | 56 |
| 0.75 | 0.826 | 0.811 | 45 |
| 0.80 | 0.853 | 0.792 | 36 |
| 0.85 | 0.922 | 0.761 | 17 |
| 0.90 | 0.979 | 0.723 | 4 |

## Santali (line → Hindi)

- Candidates: 189 pack lines. Clips: {'pos_tune': 270, 'pos_test': 297, 'neg_tune': 181, 'neg_test': 195}.
- **Threshold 0.95.** Test half: **precision 1.000, recall 0.108** (32 of 297 positives matched to their own line; accepted 32; negatives accepted 0; wrong line 0). Tune half: precision 0.951, recall 0.144.

| Test half, positives of one version + all negatives | Precision | Recall |
|---|---|---|
| pack audio | 1.000 | 0.091 |
| piper 0.85 | 1.000 | 0.121 |
| piper 1.2 + noise 15 dB | 1.000 | 0.111 |

| Test half, negatives of one kind | Accepted / total |
|---|---|
| IN22-Conv, piper | 0 / 54 |
| near-miss: number swap | 0 / 20 |
| near-miss: word swap | 0 / 79 |
| real speech (public clip) | 0 / 42 |

| Threshold (test half) | Precision | Recall | Negatives accepted |
|---|---|---|---|
| 0.50 | 0.793 | 0.633 | 47 |
| 0.60 | 0.825 | 0.556 | 34 |
| 0.70 | 0.872 | 0.434 | 19 |
| 0.75 | 0.900 | 0.394 | 13 |
| 0.80 | 0.906 | 0.323 | 10 |
| 0.85 | 0.970 | 0.215 | 2 |
| 0.90 | 1.000 | 0.162 | 0 |
