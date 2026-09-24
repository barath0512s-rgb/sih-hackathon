# Latency benchmark: synthetic-baseline

- Date: 2026-09-24
- Device: Dell Inc. Dell G15 5520; 12th Gen Intel(R) Core(TM) i7-12700H; 20 logical CPUs; 15.7 GB RAM; Windows 10; Python 3.11.0
- Clips: 60 (C:\Users\Barath Srinivasan\Desktop\vaanisetu_1\bench\clips\synthetic\manifest.json)
- Models: ASR e9b71b369c, NMT ffb7582b6d (beams=1), TTS hi_IN-pratham-medium
- Server boot (all models loaded): 21.8 s
- Cold request (first after boot, hi): 2455 ms
- Caches empty at start; database throw-away.

> **Synthetic clips**: Piper reading the lines, not real speech. Timings are
> representative; the CER column is NOT a measure of ASR accuracy on real
> teachers or children.

`pipeline_ms` = upload start to reply audio received, in-process (no Wi-Fi).
Warm requests only (the cold request is excluded). Times in ms.

| Direction | n | pipeline median | p90 | max | ASR median | NMT median | TTS median | CER median |
|---|---|---|---|---|---|---|---|---|
| hi-to-sat | 29 | 2194 | 2688 | 3058 | 926 | 1131 | 178 | 0.033 |
| sat-to-hi | 30 | 2204 | 2528 | 2916 | 982 | 989 | 220 | 0.217 |

Requests over 3 s: 1 of 59.
Translations answered by the model: 59 of 59 (the rest by the glossary or a cache).
TTS errors: 0.

Raw data: `Dell-Inc-Dell-G15-5520_2026-09-24_synthetic-baseline.csv`.
