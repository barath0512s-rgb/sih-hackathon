# ASR decoding and silence trimming (public)

80 clips; ASR only (audio already decoded to WAV); times in ms.

> **Public dataset, adult speech.** Child speech: NOT MEASURED. Sources and
> licences per clip: `bench/clips/public/manifest.json`. Laptop, offline.
> WER and CER are corpus-level (all errors / all reference words or characters).

| Language | Decoding | Trim silence | ASR median ms | ASR p90 ms | WER | CER | CER median per clip |
|---|---|---|---|---|---|---|---|
| hi | rnnt | no | 2207 | 2598 | 0.111 | 0.046 | 0.025 |
| hi | rnnt | yes | 2081 | 2723 | 0.113 | 0.045 | 0.026 |
| hi | ctc | no | 954 | 1072 | 0.109 | 0.045 | 0.024 |
| hi | ctc | yes | 907 | 982 | 0.111 | 0.045 | 0.026 |
