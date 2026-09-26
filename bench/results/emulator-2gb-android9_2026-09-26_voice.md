# A1 on-device voice for lesson lines: emulator, 2 GB, Android 9, 2 threads

- Device (read from it): Google Android SDK built for x86_64, Android 9 (SDK 28), x86_64, RAM 2.0 GB (MemTotal 2046740 kB), 4 cores. Airplane mode: on.
- Build: **debug APK** (the benchmark hook exists only in debug builds; same native libraries and models as release). sherpa-onnx 1.13.8, int8 IndicConformer 120M (Hindi CTC, Santali transducer), 2 threads, one recogniser loaded at a time; Piper hi voice for synthesis.
- Thresholds: {'hi': 0.9, 'sat': 0.95} (bench/results/lesson_match.md). Clips: the test half of the laptop tuning set (synthetic lesson lines in the pack's own audio; non-lesson: public real clips and near-miss sentences).
- Laptop: nothing else running during the run (the emulator itself runs on the laptop's CPU).

## Hindi lesson line → Santali

- **Parity with the laptop:** device transcript identical to the laptop's on **88 of 90** clips.
- Matching on the device: precision **0.980** (50 of 51 accepted), recall **0.833** (50 of 60 lesson lines); non-lesson clips accepted: 1 of 30.

- **Voice to voice, matched lesson lines (n = 50): p50 0.50 s, p90 0.82 s** (WAV handed to the app → reply with its audio file ready; playback start not included). Audio from: ['pack'].

| Clip | Laptop | Device |
|---|---|---|
| hi_a017d00a9c6d_pack | चार सैकड़े की जगह पर है दो दहाई की जगह पर और पांच इकाई की जगह पर | चार सैकडे की जगह पर है दो दहाई की जगह पर और पांच इकाई की जगह पर |
| hi_neg_34a955d4591d | लखा सिंह ने छप्पन बोग भजन भी प्रस्तुत किए गायक राजू खंडेलवाल उनके साथ थे | लक्खा सिंह ने छप्पन भोग भजन भी प्रस्तुत किए गायक राजू खंडेलवाल उनके साथ थे |

## Santali line → Hindi

- **Parity with the laptop:** device transcript identical to the laptop's on **39 of 40** clips.
- Matching on the device: precision **1.000** (4 of 4 accepted), recall **0.160** (4 of 25 lesson lines); non-lesson clips accepted: 0 of 15.

- **Voice to voice, matched lesson lines (n = 4): p50 0.45 s, p90 0.68 s** (WAV handed to the app → reply with its audio file ready; playback start not included). Audio from: ['pack'].

| Clip | Laptop | Device |
|---|---|---|
| sat_7c047f62c5f7_pack | ᱮᱠᱥᱮᱨᱟᱱ ᱨᱤᱭᱟᱜ ᱥᱮᱨᱮᱧ ᱟᱢ ᱪᱮᱫ ᱵᱟᱰᱟᱭᱟᱢᱟ | ᱮᱠᱥᱮᱨᱟ ᱱᱤᱭᱟ ᱥᱮᱨᱮᱧ ᱟᱢ ᱪᱮᱫ ᱵᱟᱰᱟᱭᱟᱢᱟ |

## Spoken Santali answers (child → grade → Hindi feedback)

- Graded as expected: **8 of 16** (right answers green, wrong answers not green). Hindi feedback audio returned: 16 of 16. Time per answer (recognition + grading + feedback audio): p50 0.12 s, p90 0.98 s (n = 16; the first includes loading the Santali model).

| Answer | Said | Heard | Grade | Expected |
|---|---|---|---|---|
| ans_0_imp_67cb986ab3_6_right | ᱯᱮ | ᱛᱤ | yellow | green |
| ans_0_imp_67cb986ab3_6_wrong | ᱵᱤᱨᱫᱟᱹᱜᱟᱲ | ᱵᱤᱨᱫᱟᱹᱜᱟᱲ | yellow | not green |
| ans_3_imp_e065e91dbc_5_right | ᱵᱤᱨᱫᱟᱹᱜᱟᱲ | ᱵᱤᱨᱫᱟᱹᱜᱟᱲ | green | green |
| ans_3_imp_e065e91dbc_5_wrong | ᱯᱮ | ᱴᱷᱤᱠ | yellow | not green |
| ans_3_imp_5c91c0c1bb_7_right | ᱱᱟᱶᱟ ᱜᱮᱞ ᱜᱮᱞ ᱜᱮᱞ ᱥᱮᱨᱢᱟ | ᱱᱟᱣᱟ ᱜᱤᱞ ᱜᱮᱞ ᱜᱮᱞ ᱥᱮᱨᱢᱟ | yellow | green |
| ans_3_imp_5c91c0c1bb_7_wrong | ᱯᱮ | ᱯᱤᱠ | yellow | not green |
| ans_2_imp_8835da564c_7_right | ᱫᱟᱜ | ᱫᱟᱜ | green | green |
| ans_2_imp_8835da564c_7_wrong | ᱯᱮ | ᱯᱤᱪ | yellow | not green |
| ans_0_imp_223bee4bcc_6_right | ᱯᱮ | ᱴᱷᱤᱠ | yellow | green |
| ans_2_imp_8835da564c_6_right | ᱫᱷᱤᱨᱤ | ᱫᱷᱮᱹᱨᱮᱹ | yellow | green |
| ans_3_imp_46b74c74d2_10_right | ᱢᱤᱥ | ᱢᱮᱥ | yellow | green |
| ans_3_imp_5c91c0c1bb_6_right | ᱯᱩᱱ | ᱛᱟᱞᱤ | yellow | green |
| ans_0_imp_223bee4bcc_5_right | ᱢᱤᱫ | ᱢᱮᱛᱷᱟ | yellow | green |
| ans_3_imp_e065e91dbc_6_right | ᱵᱟᱨ | ᱵᱟᱨ | green | green |
| ans_2_imp_acb593a491_5_right | ᱢᱤᱫ ᱥᱟᱭ ᱵᱟᱨ ᱥᱟᱭ ᱥᱟᱭ ᱥᱟᱭ ᱜᱮᱞ ᱜᱮᱞ ᱜᱮᱞ ᱥᱟᱭ ᱥᱟᱭ ᱢᱤᱫ ᱥᱟᱭ ᱥᱟᱭ ᱵᱟᱨ ᱜᱮᱞ ᱜᱮᱞ ᱢᱤᱫ ᱥᱟᱭ ᱜᱮᱞ ᱥᱟᱭ ᱜᱮᱞ ᱢᱤᱫ ᱜᱮᱞ ᱜᱮᱞ ᱵᱟᱨ ᱜᱮᱞ ᱥᱟᱭ | ᱢᱤᱫ ᱥᱟᱭ ᱵᱟᱨ ᱥᱟᱭ ᱥᱟᱭ ᱥᱟᱭ ᱜᱮᱞ ᱜᱮᱞ ᱜᱮᱞ ᱥᱟᱭ ᱥᱟᱭ ᱢᱤᱫ ᱥᱟᱭ ᱥᱟᱭ ᱵᱟᱨ ᱜᱮᱞ ᱜᱮᱞ ᱢᱤᱫ ᱥᱟᱭ ᱜᱮᱞ ᱥᱟᱭ ᱜᱮᱞ ᱢᱤᱫ ᱜᱮᱞ ᱜᱮᱞ ᱵᱟᱨ ᱜᱮᱞ ᱥᱟᱭ | green | green |
| ans_3_imp_2a190b718f_5_right | ᱤᱨᱟᱹᱞ | ᱤᱨᱟ ᱞ | yellow | green |

- On-device synthesis, sat lines with no pack audio (n = 10): p50 0.61 s, p90 0.97 s (the first includes loading the voice).
- On-device synthesis, hi lines with no pack audio (n = 5): p50 0.32 s, p90 0.66 s (the first includes loading the voice).

## Memory

- **Peak PSS (dumpsys meminfo every 1 s, 49 samples): app 655 MB, WebView renderer 90 MB, sum 732 MB**; in-app peak (Debug.getPss after each call) 655 MB. During the run the recogniser for one language and the synthesis voice are loaded.
