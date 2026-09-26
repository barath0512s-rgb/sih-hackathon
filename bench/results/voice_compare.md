# Santali voice comparison (A6): ASR round-trip CER

- Pack `content-pack-20260926-2024.zip`: 210 Santali lines, each spoken by (a) Piper (the live voice, via transliteration) and (b) Indic Parler-TTS (pre-rendered, B1). (c) Our own voice (C4): NOT BUILT (notebooks/santali_voice.ipynb not run yet).
- Metric (chosen before the run): the hub's Santali ASR (IndicConformer 600M) on each clip; character error rate against the line after `normalize_for_wer`, spaces removed. Second opinion: sherpa-onnx 120M int8. A proxy for intelligibility; **native listener ratings (MOS): NOT MEASURED** (sheet: docs/samples/mos_lite_sheet.md).
- No timing is measured here; other work ran on the laptop during scoring (CER does not depend on it).
- The mean is pulled up by clips where a voice fails badly (Parler sometimes produces long audio that does not match the line: CER above 1); the median shows the typical line.

| Voice | CER, 600M (mean / median) | CER, sherpa 120M (mean) | Audio | Pack size at own rate | at 22.05 kHz |
|---|---|---|---|---|---|
| (a) Piper, transliterated | **0.445** / 0.275 | 0.413 | 490.6 s at 22050 Hz | 21.6 MB | 21.6 MB |
| (b) Indic Parler-TTS | **0.776** / 0.091 | 1.142 | 689.5 s at 44100 Hz | 60.8 MB | 30.4 MB |

- Per line: Parler lower CER on 139, higher on 49 of 210.
- **Decision (rule fixed in advance): keep Piper audio.**
