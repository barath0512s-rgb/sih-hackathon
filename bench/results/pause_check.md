# Pause check: the six slow clips after a 1 s idle pause

- Engine: the app's engine: onnx-fp32, 6 threads; speech recognition 8 threads. Same path as `bench/latency_steps.py` full time (from the end of speech, whole utterance, not streamed), app settings, empty voice cache; each clip after a 1 s pause, no heavy clip before it. Laptop, offline, AC power, Best performance mode.
- Compared with the same clips in the three saved runs (`latency_steps_app_hp1-3.csv`), where each followed another clip's streaming work with no pause.

| Clip | After a 1 s pause: ASR / full ms | In the runs: ASR ms (hp1, hp2, hp3) | In the runs: full ms |
|---|---|---|---|
| fleurs-hi_00015_1992 | 1375 / 3150 | 2424, 2039, 1877 | 4329, 4094, 3678 |
| fleurs-hi_00033_1910 | 934 / 2478 | 2288, 1754, 2012 | 4082, 3263, 3672 |
| fleurs-hi_00034_1721 | 1109 / 3754 | 1920, 2034, 1722 | 5341, 5825, 5327 |
| fleurs-hi_00050_1958 | 821 / 2549 | 2306, 1813, 1856 | 4923, 4189, 4226 |
| fleurs-hi_00053_1966 | 1211 / 3115 | 2038, 1881, 2268 | 4931, 4128, 4761 |
| fleurs-hi_00060_1803 | 1454 / 3155 | 2033, 1965, 2087 | 4021, 4154, 3911 |

Median over the six clips: after a pause ASR 1160 ms, full 3132 ms; in the runs ASR 2022 ms, full 4172 ms.
