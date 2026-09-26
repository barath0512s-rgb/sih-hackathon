# Latency benchmark: public_hp2

- Date: 2026-09-26
- Device: Dell Inc. Dell G15 5520; 12th Gen Intel(R) Core(TM) i7-12700H; 20 logical CPUs; 15.7 GB RAM; Windows 10; Python 3.11.0
- Clips: 160 (bench/clips/public/manifest.json)
- Models: ASR e9b71b369c, NMT ffb7582b6d (beams=1), TTS hi_IN-pratham-medium
- ASR decoding: {'hi': 'ctc', 'sat': 'rnnt'}; trim silence: {'hi': False, 'sat': True}; NMT engine: onnx-fp32
- Server boot (all models loaded): 21.0 s
- Cold request (first after boot, hi): 4870 ms
- Caches empty at start; database throw-away.

> **Public dataset, adult speech** (sources and licences per clip in the
> manifest). Child speech: NOT MEASURED. Laptop, offline, in-process.

`pipeline_ms` = upload start to reply audio received, in-process (no Wi-Fi).
Warm requests only (the cold request is excluded). Times in ms.

| Direction | n | pipeline median | p90 | max | ASR median | NMT median | TTS median | CER median |
|---|---|---|---|---|---|---|---|---|
| hi-to-sat | 79 | 2035 | 2354 | 3221 | 796 | 851 | 374 | 0.024 |
| sat-to-hi | 80 | 2163 | 2524 | 3051 | 938 | 860 | 369 | 0.072 |

Lines translated by the model only (no glossary or cache hit):

| Direction | n | pipeline median | p90 | max | ASR median | NMT median | TTS median |
|---|---|---|---|---|---|---|---|
| hi-to-sat | 79 | 2035 | 2354 | 3221 | 796 | 851 | 374 |
| sat-to-hi | 80 | 2163 | 2524 | 3051 | 938 | 860 | 369 |

Requests over 3 s: 2 of 159.
Translations answered by the model: 159 of 159 (the rest by the glossary or a cache).
TTS errors: 0.

Raw data: `Dell-Inc-Dell-G15-5520_2026-09-26_public_hp2.csv`.
