# A5 on-device translation: emulator, 2 GB, Android 9, 2 threads

- Device (read from it): Android SDK built for x86_64, Android 9, x86_64, RAM 2.0 GB (MemTotal 2046740 kB). Airplane mode: on. Debug build (benchmark hook). Model pack `(see the run log)`.
- Engine: IndicTrans2 indic-indic-dist-320M int8 on ONNX Runtime (Android 1.28), greedy, no-repeat 3-gram, the int8 length cap and stem-loop guard; IndicTransToolkit pre/post-processing and SentencePiece ported to Kotlin (unit tests: identical pre-processing and token ids on 300 of 300 sentences).
- The recogniser is released before translation loads (one large model at a time).

## Same output as the laptop

- The 80 golden sentences (40 Hindi lesson lines, 40 IN22-Conv Santali): tablet output identical to the laptop's int8 output on **80 of 80**.
- IN22-Conv Hindi → Santali, 1503 sentences: identical to the laptop's int8 output on 1502 of 1503.

## Quality (IN22-Conv, Hindi → Santali, CC BY 4.0)

| Engine | n | chrF++ |
|---|---|---|
| Laptop, int8 ONNX (Python) | 1503 | 32.04 |
| Tablet, int8 ONNX (Kotlin port) | 1503 | **32.04** |

- Difference: +0.00 (the bar: within 0.5).

## Time

- Translation on the tablet, per sentence (IN22-Conv, 1503): p50 0.60 s, p90 1.19 s. First sentence (includes loading the model): 4.86 s.
- Peak PSS, phase 1 (translation; in-app Debug.getPss after each sentence): app 1499 MB. **This build leaked**: each decoding step copied the logits into a direct buffer freed only by a GC; fixed and re-measured in `emulator-2gb-android9_2026-09-26_nmt_memfix.md` (outputs unchanged).

## Free-form Hindi speech → Santali speech, all on the tablet

- **Did not finish (this build, before the memory fix): on the 2 GB emulator the app was killed by Android's low-memory killer (after it had killed Google services) during the first free-form clips, when recognition, translation and synthesis were loaded in turn; lesson lines (A1) are unaffected**. After the fix it finishes: see `emulator-2gb-android9_2026-09-26_nmt_memfix.md`.
