# Latency by step and sentence length: app

- Translation backend: the app's engine: onnx-fp32, 6 threads; speech recognition 8 threads. Speech recognition: IndicConformer, ctc, trim=True. Speech: Piper hi_IN-pratham-medium. Every engine warmed first. Laptop, offline, in-process.
- **public** = google/fleurs Hindi test clips (public dataset, adult speech). **lesson** = the Hindi lesson lines (synthetic speech). Child speech: NOT MEASURED.
- Times in ms from the end of speech (audio handed to the recogniser); endpointing, upload and audio decoding not included. Median / p90.
- full = whole utterance translated and voiced. first / last audio = clause streaming (streaming.py): first chunk ready / all chunks ready.
- agree = chrF++ of the chunked translation against the whole-sentence translation (how much chunking changes the output), not accuracy.
- **n** = clips run; **n_distinct** = distinct sentences, the rows every figure is computed on (first clip of each sentence).

| Set | Words | n | n_distinct | ASR | NMT | TTS | full med | full p90 | full >3 s | first med | first p90 | last med | last p90 | stalls | agree |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| public | all | 80 | 69 | 774 | 848 | 396 | 2014 | 3567 | 11 | 1659 | 2683 | 3145 | 4518 | 0 | 69.0 |
| public | 0-11 | 3 | 3 | 708 | 746 | 263 | 1685 | 3021 | 1 | 1598 | 2299 | 2299 | 2415 | 0 | 100.0 |
| public | 12-17 | 35 | 29 | 709 | 762 | 341 | 1836 | 3020 | 3 | 1640 | 2105 | 2505 | 3504 | 0 | 65.9 |
| public | 18-23 | 33 | 28 | 808 | 894 | 440 | 2104 | 4967 | 6 | 1704 | 3214 | 3346 | 6219 | 0 | 68.5 |
| public | 24+ | 9 | 9 | 735 | 946 | 423 | 2141 | 4324 | 1 | 1659 | 3478 | 4040 | 7077 | 0 | 68.8 |
| lesson | all | 30 | 30 | 201 | 542 | 347 | 1132 | 1209 | 0 | 734 | 897 | 734 | 897 | 0 | 100.0 |

Targets (Phase L), on distinct sentences:
- p90 time to first audio, all public sentences (n_distinct=69): 2683 ms (target ≤ 3000)
- p90 full time, public sentences of ≤ 17 words (n_distinct=32): 3020 ms (target ≤ 3000)
