# Latency by step and sentence length: torch-t14

- Translation backend: PyTorch, fp32, 14 threads. Speech recognition: IndicConformer, ctc, trim=True. Speech: Piper hi_IN-pratham-medium. Every engine warmed first. Laptop, offline, in-process.
- **public** = google/fleurs Hindi test clips (public dataset, adult speech). **lesson** = the Hindi lesson lines (synthetic speech). Child speech: NOT MEASURED.
- Times in ms from the end of speech (audio handed to the recogniser); endpointing, upload and audio decoding not included. Median / p90.
- full = whole utterance translated and voiced. first / last audio = clause streaming (streaming.py): first chunk ready / all chunks ready.
- agree = chrF++ of the chunked translation against the whole-sentence translation (how much chunking changes the output), not accuracy.

| Set | Words | n | ASR | NMT | TTS | full med | full p90 | full >3 s | first med | first p90 | last med | last p90 | stalls | agree |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| public | all | 80 | 774 | 2014 | 352 | 3146 | 4067 | 51 | 1786 | 2274 | 3348 | 4862 | 0 | 69.0 |
| public | 0-11 | 3 | 624 | 1824 | 247 | 2702 | 2859 | 0 | 1731 | 1799 | 1799 | 2592 | 0 | 100.0 |
| public | 12-17 | 35 | 751 | 1894 | 314 | 2931 | 3739 | 16 | 1758 | 2160 | 2769 | 3766 | 0 | 65.4 |
| public | 18-23 | 33 | 835 | 2092 | 422 | 3298 | 4126 | 27 | 1934 | 2797 | 3542 | 4910 | 0 | 69.6 |
| public | 24+ | 9 | 774 | 2397 | 483 | 3404 | 4797 | 8 | 1783 | 2262 | 4662 | 7353 | 0 | 68.8 |
| lesson | all | 30 | 164 | 964 | 142 | 1274 | 1627 | 0 | 785 | 1122 | 785 | 1122 | 0 | 100.0 |

Targets (Phase L):
- p90 time to first audio, all public sentences: 2274 ms (target ≤ 3000)
- p90 full time, public sentences of ≤ 17 words (n=38): 3739 ms (target ≤ 3000)
