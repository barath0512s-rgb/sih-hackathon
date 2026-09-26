# Latency by step and sentence length: app_hp2

- Translation backend: the app's engine: onnx-fp32, 6 threads; speech recognition 8 threads. Speech recognition: IndicConformer, ctc, trim=False. Speech: Piper hi_IN-pratham-medium. Every engine warmed first. Laptop, offline, in-process.
- **public** = google/fleurs Hindi test clips (public dataset, adult speech). **lesson** = the Hindi lesson lines (synthetic speech). Child speech: NOT MEASURED.
- Times in ms from the end of speech (audio handed to the recogniser); endpointing, upload and audio decoding not included. Median / p90.
- full = whole utterance translated and voiced. first / last audio = clause streaming (streaming.py): first chunk ready / all chunks ready.
- agree = chrF++ of the chunked translation against the whole-sentence translation (how much chunking changes the output), not accuracy.
- **n** = clips run; **n_distinct** = distinct sentences, the rows every figure is computed on (first clip of each sentence).

| Set | Words | n | n_distinct | ASR | NMT | TTS | full med | full p90 | full >3 s | first med | first p90 | last med | last p90 | stalls | agree |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| public | all | 80 | 69 | 871 | 868 | 388 | 2133 | 3624 | 10 | 1725 | 2750 | 3264 | 4497 | 0 | 69.1 |
| public | 0-11 | 3 | 3 | 711 | 786 | 273 | 1721 | 3215 | 1 | 1560 | 2473 | 2295 | 2473 | 0 | 100.0 |
| public | 12-17 | 34 | 29 | 846 | 816 | 356 | 2030 | 2845 | 2 | 1705 | 2424 | 2581 | 3491 | 0 | 67.7 |
| public | 18-23 | 34 | 28 | 900 | 882 | 414 | 2151 | 4189 | 6 | 1780 | 3246 | 3433 | 5625 | 0 | 69.3 |
| public | 24+ | 9 | 9 | 853 | 968 | 440 | 2269 | 4094 | 1 | 1725 | 3398 | 4058 | 6678 | 0 | 71.5 |
| lesson | all | 30 | 30 | 316 | 510 | 400 | 1200 | 1344 | 0 | 806 | 998 | 806 | 998 | 0 | 100.0 |

Targets (Phase L), on distinct sentences:
- p90 time to first audio, all public sentences (n_distinct=69): 2750 ms (target ≤ 3000)
- p90 full time, public sentences of ≤ 17 words (n_distinct=32): 2845 ms (target ≤ 3000)
