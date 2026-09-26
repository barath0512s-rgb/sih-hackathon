# Santali voice for the content pack: the comparison rule for the finale

Written 27 Sep 2026, before any finale data exists. The submission keeps Piper
(A6: `bench/results/voice_compare.md`; the pre-declared rule compared means over
all 210 lines and Parler's mean was higher). This rule replaces it for the finale
and is fixed now; it may not be changed after results are seen.

## Candidates

- **Piper**: the current voice (Piper hi_IN-pratham reading the Ol Chiki transliteration).
- **Parler**: Indic Parler-TTS pre-rendered audio.
- **Ours**: the C4 fine-tuned voice, if built.
- **Hybrid**: Parler (or Ours) per line, falling back to Piper when a **guard** rejects the clip.
  The guard may use only (a) the clip's duration against the line's length
  (seconds per character, bounds set on the selection half) and (b) the tablet's
  sherpa-onnx 120M recogniser. It may **not** use the 600M recogniser, which is
  the judge below, so the selection and the evaluation stay independent.

## Data

- The content pack's Santali lines at the time of the finale build.
- Split once, before anything is scored: a line goes to **held-out** if the SHA-1 of its
  text is odd, to **selection** otherwise. Guard bounds and any other choices are made on
  the selection half only. The held-out half is scored **once**; its numbers are reported
  whatever they are.

## Measures (held-out half)

1. ASR round-trip CER with the hub's Santali recogniser (IndicConformer 600M, the app's
   settings), after `textnorm.normalize_for_wer` with spaces removed: **mean and median**.
2. Failure rate: lines with CER above 0.5.
3. Native listeners (MOS-lite sheet, `docs/samples/mos_lite_sheet.md` format, blind A/B): mean
   "clear" and "natural" scores, if at least 3 native listeners fill it in.

## Decision

A candidate replaces Piper in the pack only if, on the held-out half, **all** hold:

- mean CER lower than Piper's by at least 0.02;
- median CER not higher than Piper's;
- failure rate not higher than Piper's;
- if MOS-lite scores exist: "clear" not lower than Piper's.

If more than one candidate passes, the one with the lowest held-out mean CER ships.
Otherwise Piper stays. Pack size is reported but does not decide.
