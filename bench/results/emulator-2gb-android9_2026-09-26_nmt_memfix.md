# A5 on-device translation: emulator, 2 GB, Android 9, 2 threads — after the memory fix

The same build as `emulator-2gb-android9_2026-09-26_nmt.md` except that the decoder reads its logits through the Java heap (the full run's in-app PSS grew from about 1010 MB to 1499 MB over 1503 sentences: a direct-buffer copy per step). Outputs are unchanged by the fix (80 of 80 golden sentences identical here too). Run with 200 IN22-Conv sentences and 20 free-form clips.

- Device (read from it): Android SDK built for x86_64, Android 9, x86_64, RAM 2.0 GB (MemTotal 2046740 kB). Airplane mode: on. Debug build (benchmark hook). Model pack `model-pack-20260926-2106.zip`.
- Engine: IndicTrans2 indic-indic-dist-320M int8 on ONNX Runtime (Android 1.28), greedy, no-repeat 3-gram, the int8 length cap and stem-loop guard; IndicTransToolkit pre/post-processing and SentencePiece ported to Kotlin (unit tests: identical pre-processing and token ids on 300 of 300 sentences).
- The recogniser is released before translation loads (one large model at a time).

## Same output as the laptop

- The 80 golden sentences (40 Hindi lesson lines, 40 IN22-Conv Santali): tablet output identical to the laptop's int8 output on **80 of 80**.
- IN22-Conv Hindi → Santali, 200 sentences: identical to the laptop's int8 output on 200 of 200.

## Quality (IN22-Conv, Hindi → Santali, CC BY 4.0)

| Engine | n | chrF++ |
|---|---|---|
| Laptop, int8 ONNX (Python) | 200 | 28.75 |
| Tablet, int8 ONNX (Kotlin port) | 200 | **28.75** |

- Difference: +0.00 (the bar: within 0.5).

## Time

- Translation on the tablet, per sentence (IN22-Conv, 200): p50 0.46 s, p90 0.90 s. First sentence (includes loading the model): 3.91 s.
- Peak PSS, phase 1 (translation): app 1197 MB + WebView 101 MB.

## Free-form Hindi speech → Santali speech, all on the tablet

- Public Hindi clips (FLEURS, not lesson lines), 20: recognition → translation → synthesis. From the WAV handed over to the reply audio file ready: **p50 13.48 s, p90 15.07 s** (n = 20; the first loads models; playback start not included).
- Peak PSS, phase 2 (recognition + translation + synthesis): app 1261 MB + WebView 81 MB.
