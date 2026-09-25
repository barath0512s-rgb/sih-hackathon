# Latency by step and sentence length: onnx-int8-t6

- Translation backend: ONNX Runtime dynamic int8, 6 threads. Speech recognition: IndicConformer, ctc, trim=True. Speech: Piper hi_IN-pratham-medium. Every engine warmed first. Laptop, offline, in-process.
- **public** = google/fleurs Hindi test clips (public dataset, adult speech). **lesson** = the Hindi lesson lines (synthetic speech). Child speech: NOT MEASURED.
- Times in ms from the end of speech (audio handed to the recogniser); endpointing, upload and audio decoding not included. Median / p90.
- full = whole utterance translated and voiced. first / last audio = clause streaming (streaming.py): first chunk ready / all chunks ready.
- agree = chrF++ of the chunked translation against the whole-sentence translation (how much chunking changes the output), not accuracy.
- **n** = clips run; **n_distinct** = distinct sentences, the rows every figure is computed on (first clip of each sentence).

| Set | Words | n | n_distinct | ASR | NMT | TTS | full med | full p90 | full >3 s | first med | first p90 | last med | last p90 | stalls | agree |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| public | all | 80 | 69 | 838 | 516 | 653 | 2014 | 3783 | 9 | 1592 | 3069 | 2953 | 4547 | 0 | 65.9 |
| public | 0-11 | 3 | 3 | 724 | 456 | 655 | 1753 | 3234 | 1 | 1504 | 2056 | 1986 | 2056 | 0 | 100.0 |
| public | 12-17 | 35 | 29 | 815 | 471 | 647 | 1906 | 2289 | 1 | 1570 | 1993 | 2369 | 3112 | 0 | 63.7 |
| public | 18-23 | 33 | 28 | 888 | 526 | 675 | 2086 | 4076 | 6 | 1638 | 3187 | 3122 | 6081 | 0 | 67.2 |
| public | 24+ | 9 | 9 | 811 | 663 | 635 | 2095 | 7043 | 1 | 1539 | 3432 | 3713 | 6563 | 0 | 57.9 |
| lesson | all | 30 | 30 | 216 | 182 | 650 | 1102 | 1239 | 0 | 500 | 635 | 500 | 635 | 0 | 100.0 |

Targets (Phase L), on distinct sentences:
- p90 time to first audio, all public sentences (n_distinct=69): 3069 ms (target ≤ 3000)
- p90 full time, public sentences of ≤ 17 words (n_distinct=32): 2289 ms (target ≤ 3000)
