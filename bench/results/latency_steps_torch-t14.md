# Latency by step and sentence length: torch-t14

- Translation backend: PyTorch, fp32, 14 threads. Speech recognition: IndicConformer, ctc, trim=True. Speech: Piper hi_IN-pratham-medium. Every engine warmed first. Laptop, offline, in-process.
- **public** = google/fleurs Hindi test clips (public dataset, adult speech). **lesson** = the Hindi lesson lines (synthetic speech). Child speech: NOT MEASURED.
- Times in ms from the end of speech (audio handed to the recogniser); endpointing, upload and audio decoding not included. Median / p90.
- full = whole utterance translated and voiced. first / last audio = clause streaming (streaming.py): first chunk ready / all chunks ready.
- agree = chrF++ of the chunked translation against the whole-sentence translation (how much chunking changes the output), not accuracy.
- **n** = clips run; **n_distinct** = distinct sentences, the rows every figure is computed on (first clip of each sentence).

| Set | Words | n | n_distinct | ASR | NMT | TTS | full med | full p90 | full >3 s | first med | first p90 | last med | last p90 | stalls | agree |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| public | all | 80 | 69 | 775 | 2019 | 357 | 3164 | 4126 | 47 | 1799 | 2430 | 3421 | 5345 | 0 | 69.0 |
| public | 0-11 | 3 | 3 | 624 | 1824 | 247 | 2702 | 2859 | 0 | 1731 | 1799 | 1799 | 2592 | 0 | 100.0 |
| public | 12-17 | 35 | 29 | 751 | 1894 | 316 | 2991 | 3739 | 14 | 1761 | 2274 | 2855 | 4273 | 0 | 65.9 |
| public | 18-23 | 33 | 28 | 842 | 2206 | 426 | 3408 | 4146 | 25 | 1966 | 2800 | 3583 | 5345 | 0 | 68.5 |
| public | 24+ | 9 | 9 | 774 | 2397 | 483 | 3404 | 4797 | 8 | 1783 | 2262 | 4662 | 7353 | 0 | 68.8 |
| lesson | all | 30 | 30 | 164 | 964 | 142 | 1274 | 1627 | 0 | 785 | 1122 | 785 | 1122 | 0 | 100.0 |

Targets (Phase L), on distinct sentences:
- p90 time to first audio, all public sentences (n_distinct=69): 2430 ms (target ≤ 3000)
- p90 full time, public sentences of ≤ 17 words (n_distinct=32): 3463 ms (target ≤ 3000)
