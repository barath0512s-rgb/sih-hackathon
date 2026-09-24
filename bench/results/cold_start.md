# First request after server start

3 trials, each a fresh app process with all models loaded; the same synthetic Hindi clip sent 3 times, caches cleared before each request. ASR decoding ctc, trim True.

| Trial | First request ms | ASR | NMT | TTS | Later requests (median) ms |
|---|---|---|---|---|---|
| 1 | 1664 | 480 | 846 | 269 | 1735 |
| 2 | 1616 | 415 | 901 | 236 | 1722 |
| 3 | 1523 | 365 | 847 | 246 | 1657 |

Median extra time on the first request: **-105 ms**.
