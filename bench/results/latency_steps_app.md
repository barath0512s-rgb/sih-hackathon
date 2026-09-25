# Latency by step and sentence length: app

- Translation backend: the app's engine: onnx-fp32, 6 threads; speech recognition 8 threads. Speech recognition: IndicConformer, ctc, trim=True. Speech: Piper hi_IN-pratham-medium. Every engine warmed first. Laptop, offline, in-process.
- **public** = google/fleurs Hindi test clips (public dataset, adult speech). **lesson** = the Hindi lesson lines (synthetic speech). Child speech: NOT MEASURED.
- Times in ms from the end of speech (audio handed to the recogniser); endpointing, upload and audio decoding not included. Median / p90.
- full = whole utterance translated and voiced. first / last audio = clause streaming (streaming.py): first chunk ready / all chunks ready.
- agree = chrF++ of the chunked translation against the whole-sentence translation (how much chunking changes the output), not accuracy.

| Set | Words | n | ASR | NMT | TTS | full med | full p90 | full >3 s | first med | first p90 | last med | last p90 | stalls | agree |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| public | all | 80 | 836 | 895 | 430 | 2148 | 3110 | 12 | 1792 | 2323 | 3166 | 4422 | 0 | 69.0 |
| public | 0-11 | 3 | 982 | 838 | 300 | 2087 | 2300 | 0 | 1753 | 1850 | 1850 | 2533 | 0 | 100.0 |
| public | 12-17 | 35 | 795 | 854 | 387 | 1969 | 2480 | 2 | 1729 | 2185 | 2671 | 3409 | 0 | 65.4 |
| public | 18-23 | 33 | 879 | 930 | 463 | 2284 | 3354 | 6 | 1827 | 2489 | 3578 | 4365 | 0 | 69.6 |
| public | 24+ | 9 | 932 | 1109 | 654 | 2870 | 3294 | 4 | 1994 | 2707 | 4544 | 5821 | 0 | 68.8 |
| lesson | all | 30 | 206 | 593 | 344 | 1120 | 1244 | 0 | 684 | 902 | 684 | 902 | 0 | 100.0 |

Targets (Phase L):
- p90 time to first audio, all public sentences: 2323 ms (target ≤ 3000)
- p90 full time, public sentences of ≤ 17 words (n=38): 2480 ms (target ≤ 3000)
