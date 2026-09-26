# Latency by step and sentence length: app_hp3

- Translation backend: the app's engine: onnx-fp32, 6 threads; speech recognition 8 threads. Speech recognition: IndicConformer, ctc, trim=False. Speech: Piper hi_IN-pratham-medium. Every engine warmed first. Laptop, offline, in-process.
- **public** = google/fleurs Hindi test clips (public dataset, adult speech). **lesson** = the Hindi lesson lines (synthetic speech). Child speech: NOT MEASURED.
- Times in ms from the end of speech (audio handed to the recogniser); endpointing, upload and audio decoding not included. Median / p90.
- full = whole utterance translated and voiced. first / last audio = clause streaming (streaming.py): first chunk ready / all chunks ready.
- agree = chrF++ of the chunked translation against the whole-sentence translation (how much chunking changes the output), not accuracy.
- **n** = clips run; **n_distinct** = distinct sentences, the rows every figure is computed on (first clip of each sentence).

| Set | Words | n | n_distinct | ASR | NMT | TTS | full med | full p90 | full >3 s | first med | first p90 | last med | last p90 | stalls | agree |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| public | all | 80 | 69 | 867 | 858 | 390 | 2113 | 3672 | 9 | 1716 | 2544 | 3151 | 5071 | 0 | 69.1 |
| public | 0-11 | 3 | 3 | 801 | 801 | 351 | 1858 | 2899 | 0 | 1666 | 2131 | 2131 | 2439 | 0 | 100.0 |
| public | 12-17 | 34 | 29 | 808 | 800 | 352 | 1902 | 2755 | 2 | 1675 | 2214 | 2526 | 3566 | 0 | 67.7 |
| public | 18-23 | 34 | 28 | 918 | 898 | 420 | 2175 | 4761 | 6 | 1788 | 3402 | 3404 | 5885 | 0 | 69.3 |
| public | 24+ | 9 | 9 | 864 | 965 | 405 | 2291 | 3678 | 1 | 1748 | 3101 | 4041 | 5701 | 0 | 71.5 |
| lesson | all | 30 | 30 | 298 | 556 | 334 | 1212 | 1350 | 0 | 698 | 972 | 698 | 972 | 0 | 100.0 |

Targets (Phase L), on distinct sentences:
- p90 time to first audio, all public sentences (n_distinct=69): 2544 ms (target ≤ 3000)
- p90 full time, public sentences of ≤ 17 words (n_distinct=32): 2755 ms (target ≤ 3000)
