# ASR decoding and silence trimming (public)

160 clips; ASR only (audio already decoded to WAV); times in ms.

> **Public dataset, adult speech.** Child speech: NOT MEASURED. Sources and
> licences per clip: `bench/clips/public/manifest.json`. Laptop, offline.
> WER and CER are corpus-level (all errors / all reference words or characters).

| Language | Decoding | Trim silence | ASR median ms | ASR p90 ms | WER | CER | CER median per clip |
|---|---|---|---|---|---|---|---|
| hi | rnnt | no | 1385 | 1696 | 0.111 | 0.046 | 0.025 |
| hi | rnnt | yes | 1260 | 1516 | 0.113 | 0.045 | 0.026 |
| hi | ctc | no | 549 | 644 | 0.109 | 0.045 | 0.024 |
| hi | ctc | yes | 499 | 627 | 0.111 | 0.045 | 0.026 |
| sat | rnnt | no | 1154 | 1471 | 0.313 | 0.106 | 0.071 |
| sat | rnnt | yes | 1070 | 1344 | 0.311 | 0.106 | 0.072 |
| sat | ctc | no | 424 | 566 | 0.345 | 0.119 | 0.089 |
| sat | ctc | yes | 401 | 571 | 0.347 | 0.120 | 0.083 |
