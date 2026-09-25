# Latency by step and sentence length: app_run1

- Translation backend: the app's engine: onnx-fp32, 6 threads; speech recognition 8 threads. Speech recognition: IndicConformer, ctc, trim=True. Speech: Piper hi_IN-pratham-medium. Every engine warmed first. Laptop, offline, in-process.
- **public** = google/fleurs Hindi test clips (public dataset, adult speech). **lesson** = the Hindi lesson lines (synthetic speech). Child speech: NOT MEASURED.
- Times in ms from the end of speech (audio handed to the recogniser); endpointing, upload and audio decoding not included. Median / p90.
- full = whole utterance translated and voiced. first / last audio = clause streaming (streaming.py): first chunk ready / all chunks ready.
- agree = chrF++ of the chunked translation against the whole-sentence translation (how much chunking changes the output), not accuracy.
- **n** = clips run; **n_distinct** = distinct sentences, the rows every figure is computed on (first clip of each sentence).

| Set | Words | n | n_distinct | ASR | NMT | TTS | full med | full p90 | full >3 s | first med | first p90 | last med | last p90 | stalls | agree |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| public | all | 80 | 69 | 856 | 914 | 455 | 2262 | 3294 | 12 | 1802 | 2462 | 3409 | 4544 | 0 | 69.0 |
| public | 0-11 | 3 | 3 | 982 | 838 | 300 | 2087 | 2300 | 0 | 1753 | 1850 | 1850 | 2533 | 0 | 100.0 |
| public | 12-17 | 35 | 29 | 809 | 854 | 388 | 1969 | 2840 | 2 | 1752 | 2254 | 2767 | 3854 | 0 | 65.9 |
| public | 18-23 | 33 | 28 | 880 | 950 | 505 | 2348 | 3390 | 6 | 1838 | 2551 | 3681 | 4525 | 0 | 68.5 |
| public | 24+ | 9 | 9 | 932 | 1109 | 654 | 2870 | 3294 | 4 | 1994 | 2707 | 4544 | 5821 | 0 | 68.8 |
| lesson | all | 30 | 30 | 206 | 593 | 344 | 1120 | 1244 | 0 | 684 | 902 | 684 | 902 | 0 | 100.0 |

Targets (Phase L), on distinct sentences:
- p90 time to first audio, all public sentences (n_distinct=69): 2462 ms (target ≤ 3000)
- p90 full time, public sentences of ≤ 17 words (n_distinct=32): 2480 ms (target ≤ 3000)
