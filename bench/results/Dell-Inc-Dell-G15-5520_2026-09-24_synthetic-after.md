# Latency benchmark: synthetic-after

- Date: 2026-09-24
- Device: Dell Inc. Dell G15 5520; 12th Gen Intel(R) Core(TM) i7-12700H; 20 logical CPUs; 15.7 GB RAM; Windows 10; Python 3.11.0
- Clips: 60 (C:\Users\Barath Srinivasan\Desktop\vaanisetu_1\bench\clips\synthetic\manifest.json)
- Models: ASR e9b71b369c, NMT ffb7582b6d (beams=1), TTS hi_IN-pratham-medium
- Server boot (all models loaded): 20.4 s
- Cold request (first after boot, hi): 1536 ms
- Caches empty at start; database throw-away.

> **Synthetic clips**: Piper reading the lines, not real speech. Timings are
> representative; the CER column is NOT a measure of ASR accuracy on real
> teachers or children.

`pipeline_ms` = upload start to reply audio received, in-process (no Wi-Fi).
Warm requests only (the cold request is excluded). Times in ms.

| Direction | n | pipeline median | p90 | max | ASR median | NMT median | TTS median | CER median |
|---|---|---|---|---|---|---|---|---|
| hi-to-sat | 29 | 1508 | 1676 | 2082 | 588 | 685 | 196 | 0.000 |
| sat-to-hi | 30 | 1575 | 1853 | 2251 | 682 | 755 | 185 | 0.195 |

Lines translated by the model only (no glossary or cache hit):

| Direction | n | pipeline median | p90 | max | ASR median | NMT median | TTS median |
|---|---|---|---|---|---|---|---|
| hi-to-sat | 18 | 1474 | 1842 | 2082 | 570 | 775 | 147 |
| sat-to-hi | 30 | 1575 | 1853 | 2251 | 682 | 755 | 185 |

Requests over 3 s: 0 of 59.
Translations answered by the model: 48 of 59 (the rest by the glossary or a cache).
TTS errors: 0.

Raw data: `Dell-Inc-Dell-G15-5520_2026-09-24_synthetic-after.csv`.
