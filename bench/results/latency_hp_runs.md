# Latency, three runs (hp1, hp2, hp3)

Laptop on AC power, Windows power plan High performance, other apps closed (set by the user). Offline. Every run is listed; the last column is the median of the three runs' p90s. Distinct sentences only (the first clip of each): n = clips, n_distinct = sentences used.

## From the end of speech: FLEURS Hindi -> Santali (`bench/latency_steps.py --backend app`)

Time to first audio (clause streaming) and full time (whole utterance voiced), p90 in seconds.

| Words | n | n_distinct | hp1: first / full | hp2: first / full | hp3: first / full | Median of p90s: first / full |
|---|---|---|---|---|---|---|
| all | 80 | 69 | 3.40 / 4.08 | 2.75 / 3.62 | 2.54 / 3.67 | **2.75 / 3.67** |
| ≤ 17 | 37 | 32 | 2.41 / 2.96 | 2.42 / 2.85 | 2.14 / 2.75 | **2.41 / 2.85** |
| 0-11 | 3 | 3 | 2.23 / 3.29 | 2.47 / 3.21 | 2.13 / 2.90 | **2.23 / 3.21** |
| 12-17 | 34 | 29 | 2.59 / 2.96 | 2.42 / 2.85 | 2.21 / 2.75 | **2.42 / 2.85** |
| 18-23 | 34 | 28 | 3.74 / 4.93 | 3.25 / 4.19 | 3.40 / 4.76 | **3.40 / 4.76** |
| 24+ | 9 | 9 | 3.71 / 4.33 | 3.40 / 4.09 | 3.10 / 3.68 | **3.40 / 4.09** |

Source files: `latency_steps_app_hp1.csv`, `latency_steps_app_hp2.csv`, `latency_steps_app_hp3.csv`

## Upload to reply audio, both directions (`bench/bench_latency.py`, public clips)

Full time (no streaming in this path), p90 in seconds. Santali clips: IndicVoices validation split (no public Santali test split); may overlap model-development data. Word bins count the reference words of the spoken sentence.

| Direction | Words | n | n_distinct | hp1 | hp2 | hp3 | Median of p90s |
|---|---|---|---|---|---|---|---|
| hi-to-sat | all | 79 | 68 | 2.93 | 2.38 | 2.37 | **2.38** |
| hi-to-sat | 0-11 | 4 | 4 | 2.22 | 1.87 | 1.87 | **1.87** |
| hi-to-sat | 12-17 | 36 | 30 | 2.60 | 2.14 | 2.09 | **2.14** |
| hi-to-sat | 18-23 | 32 | 27 | 3.17 | 2.47 | 2.37 | **2.47** |
| hi-to-sat | 24+ | 7 | 7 | 3.32 | 3.22 | 2.61 | **3.22** |
| sat-to-hi | all | 80 | 80 | 2.60 | 2.52 | 2.58 | **2.58** |
| sat-to-hi | 0-10 | 42 | 42 | 2.27 | 2.23 | 2.29 | **2.27** |
| sat-to-hi | 11-17 | 25 | 25 | 2.62 | 2.55 | 2.69 | **2.62** |
| sat-to-hi | 18+ | 13 | 13 | 2.94 | 2.80 | 2.75 | **2.80** |

Source files: `Dell-Inc-Dell-G15-5520_2026-09-26_public_hp1.csv`, `Dell-Inc-Dell-G15-5520_2026-09-26_public_hp2.csv`, `Dell-Inc-Dell-G15-5520_2026-09-26_public_hp3.csv`
