# Latency by step and sentence length: app_hp1

- Translation backend: the app's engine: onnx-fp32, 6 threads; speech recognition 8 threads. Speech recognition: IndicConformer, ctc, trim=False. Speech: Piper hi_IN-pratham-medium. Every engine warmed first. Laptop, offline, in-process.
- **public** = google/fleurs Hindi test clips (public dataset, adult speech). **lesson** = the Hindi lesson lines (synthetic speech). Child speech: NOT MEASURED.
- Times in ms from the end of speech (audio handed to the recogniser); endpointing, upload and audio decoding not included. Median / p90.
- full = whole utterance translated and voiced. first / last audio = clause streaming (streaming.py): first chunk ready / all chunks ready.
- agree = chrF++ of the chunked translation against the whole-sentence translation (how much chunking changes the output), not accuracy.
- **n** = clips run; **n_distinct** = distinct sentences, the rows every figure is computed on (first clip of each sentence).

| Set | Words | n | n_distinct | ASR | NMT | TTS | full med | full p90 | full >3 s | first med | first p90 | last med | last p90 | stalls | agree |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| public | all | 80 | 69 | 982 | 1022 | 505 | 2540 | 4082 | 11 | 2028 | 3396 | 3813 | 5303 | 0 | 69.1 |
| public | 0-11 | 3 | 3 | 836 | 853 | 357 | 1994 | 3286 | 1 | 1729 | 2227 | 2227 | 2580 | 0 | 100.0 |
| public | 12-17 | 34 | 29 | 955 | 952 | 418 | 2295 | 2963 | 2 | 1972 | 2590 | 3092 | 3963 | 0 | 67.7 |
| public | 18-23 | 34 | 28 | 1052 | 1102 | 572 | 2640 | 4931 | 7 | 2057 | 3743 | 4064 | 6710 | 0 | 69.3 |
| public | 24+ | 9 | 9 | 937 | 1074 | 530 | 2616 | 4329 | 1 | 1971 | 3710 | 4677 | 6852 | 0 | 71.5 |
| lesson | all | 30 | 30 | 339 | 642 | 396 | 1402 | 1535 | 0 | 881 | 1165 | 881 | 1165 | 0 | 100.0 |

Targets (Phase L), on distinct sentences:
- p90 time to first audio, all public sentences (n_distinct=69): 3396 ms (target ≤ 3000)
- p90 full time, public sentences of ≤ 17 words (n_distinct=32): 2963 ms (target ≤ 3000)
