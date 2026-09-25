# ASR decoding and silence trimming (public)

160 clips; ASR only (audio already decoded to WAV); times in ms.

> **Public dataset, adult speech.** Child speech: NOT MEASURED. Sources and
> licences per clip: `bench/clips/public/manifest.json`. Laptop, offline.
> WER and CER are corpus-level (all errors / all reference words or characters).
> Santali clips: IndicVoices validation split (no public Santali test split); may overlap model-development data.

Raw = texts exactly as written. Normalised = `textnorm.normalize_for_wer` on both sides, after
removing dataset tags (`<unintelligible>`) from the references only (bench/README.md,
"WER normalisation"). n = clips, n_distinct = distinct reference sentences.

| Language | Decoding | Trim silence | n | n_distinct | ASR median ms | ASR p90 ms | WER raw | WER normalised | CER normalised | CER median per clip | Tags removed from references |
|---|---|---|---|---|---|---|---|---|---|---|---|
| hi | rnnt | no | 80 | 69 | 1428 | 1666 | 0.141 | 0.129 | 0.049 | 0.026 | 0 |
| hi | rnnt | yes | 80 | 69 | 1314 | 1618 | 0.143 | 0.131 | 0.049 | 0.026 | 0 |
| hi | ctc | no | 80 | 69 | 516 | 594 | 0.136 | 0.125 | 0.048 | 0.027 | 0 |
| hi | ctc | yes | 80 | 69 | 485 | 586 | 0.143 | 0.131 | 0.049 | 0.030 | 0 |
| sat | rnnt | no | 80 | 80 | 1281 | 1585 | 0.313 | 0.312 | 0.104 | 0.071 | 2 |
| sat | rnnt | yes | 80 | 80 | 1144 | 1478 | 0.311 | 0.310 | 0.103 | 0.072 | 2 |
| sat | ctc | no | 80 | 80 | 404 | 540 | 0.345 | 0.344 | 0.116 | 0.089 | 2 |
| sat | ctc | yes | 80 | 80 | 386 | 524 | 0.347 | 0.347 | 0.116 | 0.083 | 2 |
