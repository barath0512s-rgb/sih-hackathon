# Latency by step and sentence length: onnx-int8-t6

- Translation backend: ONNX Runtime dynamic int8, 6 threads. Speech recognition: IndicConformer, ctc, trim=True. Speech: Piper hi_IN-pratham-medium. Every engine warmed first. Laptop, offline, in-process.
- **public** = google/fleurs Hindi test clips (public dataset, adult speech). **lesson** = the Hindi lesson lines (synthetic speech). Child speech: NOT MEASURED.
- Times in ms from the end of speech (audio handed to the recogniser); endpointing, upload and audio decoding not included. Median / p90.
- full = whole utterance translated and voiced. first / last audio = clause streaming (streaming.py): first chunk ready / all chunks ready.
- agree = chrF++ of the chunked translation against the whole-sentence translation (how much chunking changes the output), not accuracy.

| Set | Words | n | ASR | NMT | TTS | full med | full p90 | full >3 s | first med | first p90 | last med | last p90 | stalls | agree |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| public | all | 80 | 826 | 526 | 645 | 1986 | 3102 | 9 | 1595 | 2132 | 2824 | 3882 | 0 | 66.0 |
| public | 0-11 | 3 | 724 | 456 | 655 | 1753 | 3234 | 1 | 1504 | 2056 | 1986 | 2056 | 0 | 100.0 |
| public | 12-17 | 35 | 807 | 476 | 633 | 1864 | 2222 | 1 | 1570 | 1880 | 2360 | 3087 | 0 | 63.7 |
| public | 18-23 | 33 | 870 | 516 | 672 | 2070 | 3880 | 6 | 1617 | 3123 | 3084 | 5358 | 0 | 68.4 |
| public | 24+ | 9 | 811 | 663 | 635 | 2095 | 7043 | 1 | 1539 | 3432 | 3713 | 6563 | 0 | 57.9 |
| lesson | all | 30 | 216 | 182 | 650 | 1102 | 1239 | 0 | 500 | 635 | 500 | 635 | 0 | 100.0 |

Targets (Phase L):
- p90 time to first audio, all public sentences: 2132 ms (target ≤ 3000)
- p90 full time, public sentences of ≤ 17 words (n=38): 2289 ms (target ≤ 3000)
