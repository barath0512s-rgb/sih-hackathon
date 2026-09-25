# Latency benchmark: public_sat_rnnt_trim

- Date: 2026-09-25
- Device: Dell Inc. Dell G15 5520; 12th Gen Intel(R) Core(TM) i7-12700H; 20 logical CPUs; 15.7 GB RAM; Windows 10; Python 3.11.0
- Clips: 80 (bench/clips/public/manifest.json)
- Models: ASR e9b71b369c, NMT ffb7582b6d (beams=1), TTS hi_IN-pratham-medium
- ASR decoding: {'hi': 'ctc', 'sat': 'rnnt'}; trim silence: {'hi': True, 'sat': True}; NMT engine: onnx-fp32
- Server boot (all models loaded): 20.1 s
- Cold request (first after boot, sat): 3511 ms
- Caches empty at start; database throw-away.

> **Public dataset, adult speech** (sources and licences per clip in the
> manifest). Child speech: NOT MEASURED. Laptop, offline, in-process.

`pipeline_ms` = upload start to reply audio received, in-process (no Wi-Fi).
Warm requests only (the cold request is excluded). Times in ms.

| Direction | n | pipeline median | p90 | max | ASR median | NMT median | TTS median | CER median |
|---|---|---|---|---|---|---|---|---|
| sat-to-hi | 79 | 2219 | 2566 | 3148 | 992 | 847 | 349 | 0.068 |

Lines translated by the model only (no glossary or cache hit):

| Direction | n | pipeline median | p90 | max | ASR median | NMT median | TTS median |
|---|---|---|---|---|---|---|---|
| sat-to-hi | 79 | 2219 | 2566 | 3148 | 992 | 847 | 349 |

Requests over 3 s: 2 of 79.
Translations answered by the model: 79 of 79 (the rest by the glossary or a cache).
TTS errors: 0.

Raw data: `Dell-Inc-Dell-G15-5520_2026-09-25_public_sat_rnnt_trim.csv`.
