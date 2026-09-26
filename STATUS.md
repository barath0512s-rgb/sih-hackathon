# STATUS, 26 Sep 2026: submission freeze, round 2 (master prompt v2)

## Ministry clauses at the submission freeze (candidate, 27 Sep 2026; final at 28 Sep 18:00)

Replaces section 1 below (kept as history). Every number is in the evidence file named.

| # | Clause (SIH26042) | Verdict | Evidence |
|---|---|---|---|
| 1 | Hindi-speaking teachers teach in the mother tongue (Ho, Mundari, Santali) with no language training | **PARTIAL.** Santali: speech, translation and speech output on the hub; on the tablet for lesson lines and typed sentences. Mundari and Ho: voices only, labelled Preview (hub); no recognition or translation; Mundari translation prepared, not trained | `languages.json`, `mms_tts.py`, `notebooks/mundari_lora.ipynb` |
| 2 | Translate Hindi FLN content into accurate text and synthesised audio | **PARTIAL.** Every lesson line has Ol Chiki text and offline audio. Public benchmarks: chrF++ Hindi → Santali 32.2 (IN22-Conv). A round-trip caution flag marks doubtful model output for native review (test precision 0.464, recall 0.449). No native review has been done | `eval/results/benchmarks.md`, `eval/results/roundtrip_flag.md`, `docs/native_review.md` |
| 3 | Real-time voice to voice, no more than 3 s | **PARTIAL.** Laptop, public adult speech, ≤ 17 words, from the end of speech: p90 2.85 s. Tablet (2 GB emulator), lesson lines: p50 0.50 s, p90 0.82 s. Free-form speech on a 2 GB tablet: p50 13.48 s, so it stays on the laptop hub. Children's speech, classroom Wi-Fi, a real 2 GB tablet: NOT MEASURED | `bench/results/latency_hp_runs.md`, `bench/results/emulator-2gb-android9_2026-09-26_voice.md`, `…_nmt_memfix.md` |
| 4 | Bilingual worksheets and visual flashcards aligned to NIPUN Bharat | **MET, with caveats.** Worksheet v2 (pictures, five exercise types, answer key) and cut-out flashcards for all 18 lessons, with the Ministry's Lakshya IDs; every Lakshya has a lesson; reading-fluency check against the NIPUN words-per-minute goals. Caveats: the lesson-to-goal mapping is not teacher-reviewed; the Santali on them awaits native review; reading-fluency accuracy with children NOT MEASURED | `tests/test_worksheet_v2.py`, `docs/samples/`, `bench/results/orf_validation.md` |
| 5 | Whole application offline on low-cost tablets (2 GB RAM, Android 9+) after initial content synchronisation | **PARTIAL.** On a 2 GB Android 9 emulator in airplane mode: lessons, worksheets, flashcards, typed translation, spoken lesson lines, spoken answers and sync, from signed packs (24 of 24 contract cases). Not on a real 2 GB tablet; free-form speech is not on the tablet; translation needs about 1.2 GB. The Realme Pad Mini (4 GB): pending | `bench/results/emulator-2gb-android9_2026-09-26_voice.md`, `…_nmt.md`, `bench/results/sync_roundtrip_2026-09-26.md` |
| 6 | A working application, demo video and GitHub repository | **PARTIAL.** Application and public repository; demo video script v2 ready, video not recorded yet | `docs/demo_video_script.md` |

## UPLIFT before submission (26–28 Sep 2026): progress

Freeze 28 Sep 18:00 IST. Anything not finished and tested by then stays behind its flag, switched off.

| Item | State | Evidence |
|---|---|---|
| B1 Parler pre-render | **Done**: 209 Santali lines of the pack rendered with `ai4bharat/indic-parler-tts` (Apache-2.0) to `content_audio/parler/` (git-ignored). Santali is listed on the card but has no speaker entry and no evaluation, so quality is unknown until A6. Nothing ships from it before A6 | `tools/parler_prerender.py`, `docs/sources.md#indic-parler-tts` |
| B2 GPU notebooks | **Written, not run** (needs the team's Kaggle/Colab GPU). Mundari: CPU dry-run of the training path passed. Voice: its ONNX exporter tested on `mms-tts-unr` on the laptop | `notebooks/*.ipynb` (from `tools/make_notebooks.py`), `tools/export/export_mms_vits_onnx.py` |
| A1 on-device voice for lesson lines | **Built, flag on (`ON_DEVICE_VOICE`), measured on the 2 GB Android 9 emulator.** sherpa-onnx 1.13.8 AAR; the int8 models arrive as a verified **model pack** (361 MB, `tools/android/build_model_pack.py`), imported like the content pack. Hindi CTC / Santali transducer loaded one at a time, Piper hi voice (M2), Kotlin ports of `translit/olchiki.py` (125/125 vectors) and of the matcher. Laptop tuning (synthetic clips, held-out half): Hindi threshold 0.90, precision 0.979, recall 0.723; Santali 0.95, precision 1.000, recall 0.108. Emulator (debug build, airplane mode, 2 threads): Hindi transcripts identical to the laptop on 88 of 90; matching precision 0.980, recall 0.833; voice to voice for matched lesson lines p50 0.50 s, p90 0.82 s (to the reply audio file); spoken Santali answers graded as expected 8 of 16 (right answers often misheard in the synthetic voice); peak PSS app 655 MB + WebView 90 MB. Real voices: NOT MEASURED. Realme: pending the device session | `bench/results/lesson_match.md`, `bench/results/emulator-2gb-android9_2026-09-26_voice.md` |
| A1 matcher change | A unit test found an everyday sentence matching an unrelated lesson line at 0.51 (the first threshold was 0.41). Near-miss negatives and a same-numbers rule were added and the threshold re-tuned; recorded in the results file | `tests/test_lesson_match.py`, `lesson_match.py` |
| A2 worksheet v2 + flashcards | **Built, flag on (`WORKSHEET_V2`).** Student exercises (count and write, match picture to word, fill in the blank, circle the answer, trace the numeral) with OpenMoji pictures, Ol Chiki / Devanagari / Western numerals, Lakshya IDs, date, answer key; cut-out flashcards with mirrored backs and a review-pending mark. Pre-rendered into the content pack for every lesson; **the tablet serves the pack's PDFs (it does not render PDFs itself)** | `worksheet_v2.py`, `docs/samples/`, `tests/test_worksheet_v2.py` |
| A3 round-trip flag | **Built, flag on (`ROUNDTRIP_CHECK`), a weak signal.** A model translation is translated back; round-trip chrF below 29.0 → "⚠️ मूल वक्ता से जाँचें", no auto-play, nearest verified sentence. IN22-Conv split in half with a fixed seed; threshold tuned on one half, scored once on the other: **test precision 0.464, recall 0.449** for the worst quarter (tune half 0.484 / 0.492); it flags about a quarter of model output. A **caution flag for native review, not a quality score**. (The first version used a hash split: 34.5, 0.446 / 0.558; superseded.) Typed translations and content packs only; voice replies skip it (a second model pass). New content pack: 37 of 110 model lines flagged; the tablet shows the flag from the pack | `eval/results/roundtrip_flag.md`, `tests/test_roundtrip.py` |
| A4 correction sync | **Built.** There was **no Ed25519 signing before** (the manifest said "from M5"); built now: the hub signs every content and model pack (`pack_signing.py`, key in `certs/`, git-ignored); the tablet verifies with its own Ed25519 (RFC 8032 port, Android 9 has none) and refuses unsigned or changed packs. Tablet export: its corrections and class counts, signed with the tablet's own key (trusted on first use per device). Hub merge: new → applied; same tablet newer → applied; two sources disagree → not applied, listed in `docs/native_review.md`. Automated round trip on the emulator (second tablet = app data cleared): PASS; tampered pack refused | `sync.py`, `bench/results/sync_roundtrip_2026-09-26.md`, `tests/test_sync.py`, `SyncTest.kt` |
| A8 Lakshya progress | **Built.** Per NIPUN Lakshya and ISO week: lessons taught (a session counts once something happens in it), green / yellow / red; from the hub's lessons and synced tablets; CSV on hub and tablet, PDF on the hub; no names, no audio | `progress.py`, `tests/test_progress.py` |
| A6 Santali voice comparison | **Done; the pack keeps Piper** (rule fixed in advance: Parler ships only if its mean CER is lower). ASR round-trip CER (600M) on 210 pack lines: Piper mean 0.445 / median 0.275; Parler mean 0.776 / median 0.091 (better on 139 lines, worse on 49: Parler sometimes produces long audio that does not match the line). A per-line choice could use Parler for most lines: **a team decision**, not taken (it would change the rule after seeing the result). Our own voice (C4): not built. MOS-lite sheet with 10 blind A/B pairs for native listeners; scores NOT MEASURED | `bench/results/voice_compare.md`, `docs/samples/mos_lite_sheet.md`, `docs/samples/voices/` |
| A7 language registry + Mundari/Ho preview | **Built.** `languages.json` (engine, licence, maturity per stage) drives the README table, `GET /languages` and the deck numbers. Mundari and Ho voices (MMS, CC BY-NC 4.0) on the laptop hub, labelled Preview; they read Odia script, so Devanagari lines are converted; Warang Citi is refused (no conversion yet). **Not on the tablet** (114 MB each). **Samples of teacher-authored Mundari/Ho lines: not made** — we have no teacher-authored lines yet (needed from the team) | `languages.py`, `mms_tts.py`, `tests/test_languages.py` |
| A5 on-device translation | **Typed new sentences: built, flag on (`ON_DEVICE_NMT`). Free-form speech: off (`FREE_FORM_VOICE`).** IndicTrans2 int8 on ONNX Runtime (Android) with Kotlin ports of IndicTransToolkit's pre/post-processing (read from its source, upstream quirks kept) and SentencePiece BPE: identical pre-processing and token ids on 300 of 300 sentences (unit test). On the 2 GB Android 9 emulator: output identical to the laptop's int8 on 1502 of 1503 IN22-Conv sentences and 80 of 80 golden ones; chrF++ 32.04 on both; p50 0.60 s per sentence. The first full run leaked memory (a direct-buffer copy per decoding step: app PSS 1010 → 1499 MB); fixed, outputs unchanged. Memory after the fix: 1197 MB while translating, **above the 900 MB guideline**, so translation loads on demand and the recogniser is released first. Free-form speech → speech on 2 GB works but swaps models per utterance: **p50 13.48 s** — too slow. **Decision (27 Sep): free-form voice stays on the laptop hub**; on-device typed translation is timed on the Realme in the device session (step B2). Packaging: sherpa-onnx's onnxruntime 1.28.2 is kept and ONNX Runtime's 1.28.0 Java bridge is patched to it (`tools/android/patch_ort_jni.py`; ELF symbol versions) | `bench/results/emulator-2gb-android9_2026-09-26_nmt.md`, `…_nmt_memfix.md`, `NmtTest.kt` |
| C1 reading fluency | **Built, hub (`ORF`).** Passage (three team-written passages, Grades 2-3) read aloud → Hindi recognition → word alignment → words correct per minute, errors highlighted, teacher override by tapping a word; NIPUN goals quoted ("45-60 words per minute", "at least 60 words per minute"). Consent checkbox in Hindi; the recording is deleted after recognition. New Grade 2 lesson for NIPUN-G2-LIT-2 (the Lakshya that had none). Adult public read speech: 5.9 % of correct words marked wrongly, simulated misreadings recall 1.000 / precision 0.570. **Children: NOT MEASURED. Not on the tablet yet** | `orf.py`, `bench/results/orf_validation.md`, `content/orf_passages.json` |
| C2 photo import | **Laptop hub only (decision of 27 Sep).** Built: `ocr.py` (Tesseract with `hin.traineddata`, photo straightened, greyed, enlarged, deleted after reading) → `POST /curriculum/photo` → the text in the lesson-import box for the teacher to check (flag `PHOTO_IMPORT`, off until measured). Ten test pages of the team's own Hindi to print and photograph (`docs/samples/ocr_pages/`), scored by `bench/ocr_eval.py`. **Waiting for Tesseract on the laptop (the team is installing it).** **No ML Kit on the tablet**: it sends usage metrics to Google when online, against the offline and privacy design | `ocr.py`, `docs/sources.md#tesseract`, `#mlkit-text` |
| C3 Mundari translation | **In progress** (priority over C4): `notebooks/mundari_lora.ipynb` ready for Kaggle (token from Kaggle Secrets, never printed or saved; resumable; exact steps in its first cell); waiting for the team's run. It also exports 10 test-split Mundari sentences for the voice samples. The official MMLoSo test set has no public references | `docs/sources.md#mmloso` |
| C4 own Santali voice | **In progress**: `notebooks/santali_voice.ipynb` ready for Kaggle; waiting for the team's run | notebook |
| A6 rule for the finale | Piper stays in the pack (decision of 27 Sep). New rule written now, before any finale data: split the pack lines once (SHA-1 parity), choose on the selection half, score the held-out half once; a candidate (Parler, our voice, or a guarded hybrid whose guard may not use the judge recogniser) replaces Piper only if mean CER is lower by ≥ 0.02, median and failure rate are not worse, and native "clear" scores are not lower | `docs/voice_rule_finale.md` |
| A7 samples | **Mundari:** only MMLoSo test-split sentences, never ours (no native speakers on the team); `tools/make_mundari_samples.py` adds them to the leakage guard and speaks them; **waiting for the MMLoSo test file** (from the notebook run or the Kaggle download). **Ho:** no published, licensed Ho text found, so no Ho sample; the app shows "Ho voice model available; content pending a native speaker" | `tools/make_mundari_samples.py` |
| APK licence | **Accepted by the team (27 Sep): the APK as a whole is distributed under GPL-3.0 terms** (espeak-ng inside sherpa-onnx); our code is public and MIT. GPL text and a source notice in the APK and in `android/`. For the finale: a character-based voice without espeak-ng | `android/COPYING-GPL-3.0.txt`, `android/app/src/main/assets/licenses/` |
| Licence correction | sherpa-onnx's Piper path compiles in **espeak-ng (GPL-3.0-or-later)**: the APK now redistributes GPL code (source link recorded). The earlier plan "sherpa-onnx removes the GPL dependency" was wrong | `THIRD_PARTY_LICENSES.md` |
| Differences from the uplift prompt | MMS Ho/Mundari voices read **Odia script** (`translit/odia.py`); there is **no `mms-tts-sat`** (C4 starts from `mms-tts-unr`); MMLoSo's official test set has **no public references** (held-out 5 % of the training file instead) | `docs/sources.md` |

## RENAME. VaaniSetu → Nijbhasha (26 Sep 2026)

Formerly VaaniSetu, renamed to avoid confusion with another team's project.

| What | Now |
|---|---|
| Product name (`config.APP_NAME`) | **Nijbhasha**; Devanagari **निजभाषा**; Ol Chiki form **left empty, pending native review** (the UI shows the Devanagari form in its place; the worksheet header prints only the non-empty forms) |
| Changed | the page (title, brand in hi/sat/en), worksheet and flashcard PDFs (`config.APP_NAME_LOCAL`, download file names), Android launcher label (from `app_config.json`), README (with the "formerly VaaniSetu" note), docs, demo script, tool messages, launcher `run_vaanisetu.bat` → `run_nijbhasha.bat` (git mv) |
| Unchanged on purpose | **Android package ID `org.team8bitpool.app`** (renaming it would break installs; it never carried the name); the database file `vaanisetu_feedback.db` (renaming would orphan stored corrections and lessons); the `vaanisetu_env` virtual environment and the internal class `VaaniSetuPipeline`; the hub CA already installed on devices (its subject still says VaaniSetu; remaking it would force a reinstall); `_archive/` and dated results files (records); STATUS quotes of the old deck (external file) |
| No splash screen | The Android app has no separate splash; the name shows in the launcher and the title bar (both from `app_config.json`) |
| GitHub repository | `barath0512s-rgb/sih-hackathon`: not renamed; waiting for your confirmation and the new name |
| Re-check after the rename, 2 GB Android 9 emulator, release APK, new content pack | Title bar "Nijbhasha"; pack import 15.0 s; 24/24 online and 24/24 in airplane mode; page check yes / yes / yes; release mic through the page 112,690 bytes (about 3.5 s); peak PSS 182 MB (app 82 + renderer 100). The debug-build MicBridge capture returned 3.04 s of **silence** (RMS 0) this time: the emulator's host audio input gave no sound on this boot (earlier runs of the same code: RMS 0.0035-0.07); not a measurement of the app. Clip re-recorded: `docs/demo_assets/android_emulator.mp4` (7.7 MB) |

## FREEZE-2 (branch `android-wp4`, fast-forwarded to `main`)

**Device change (26 Sep 2026):** the Samsung tablet (4 GB, Android 13) is replaced by a **Realme Pad Mini (4 GB RAM, 64 GB storage, Android 11)**; earlier plans that named the Samsung now name the Realme. No measurement was ever made on the Samsung. The 2 GB evidence stays the Android 9 emulator.

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Latency, three runs (AC power, Windows Best performance power mode, other apps closed; set by the user) | Median of the three runs' p90s, distinct sentences. **Upload to reply audio:** Hindi → Santali 2.38 s (n = 79, n_distinct = 68), Santali → Hindi 2.58 s (n = n_distinct = 80), answers of ≤ 10 words 2.27 s. **From the end of speech (FLEURS hi → sat):** time to first audio 2.75 s (all 69), full time 2.85 s (≤ 17 words, n_distinct = 32). **Run to run:** first-audio p90 3.40 / 2.75 / 2.54 s: one run over 3 s. 18-23 words, full p90 4.19-4.93 s. Every run and every word bin in the evidence file | `bench/results/latency_hp_runs.md` |
| 1 | Runs undisturbed? | The six runs ran back to back, 23:45-00:33 on 25-26 Sep (logs end 23:59, 00:06, 00:13, 00:19, 00:27, 00:33); no build, emulator or WSL during them (the emulator started at 09:28). Power: on AC; Windows power mode read back afterwards as **Best performance** (overlay `ded574b5-…` on the Balanced plan; its state during the night cannot be read back). No run re-done | `bench/results/latency_hp_runs.md` |
| 1b | Latency tables reconciled (saved data only) | Exact definitions now in README §6, `deck_numbers.txt` and `latency_hp_runs.md`: neither measure includes the 500 ms endpoint (off by default), Wi-Fi or playback start; end of speech = WAV handed to speech recognition, whole and streamed paths; upload = request to reply audio, whole, with ffmpeg re-encode. **Why end-of-speech full p90 3.67 s > upload 2.38 s:** medians agree (2.11 vs 2.03 s); in the end-of-speech runs the same six clips were slow every time (ASR 1.8-2.4 s) yet take 0.76 s alone (0.73 s re-encoded); each follows a clip with twice the streaming work (3.5 vs 1.9 s), run just before with no pause. That is an explanation, partly supported: re-run after a 1 s idle pause, the six clips took ASR 1.16 s and full 3.13 s (median; in the runs 2.02 and 4.17 s), so the preceding work explains about half, not all (`bench/results/pause_check.md`). Deck headline: end-of-speech ≤ 17-word full p90 2.85 s. **Streaming threshold:** ≤ 17 words: first sound 0.25-0.29 s sooner but last audio 0.65-0.70 s later; 18+: 0.48-0.60 s sooner; keep `STREAM_MIN_WORDS = 18`. Bins with n_distinct < 10 marked "small sample"; headline = ≤ 17 words: upload hi→sat p90 2.14 s, end-of-speech full 2.85 s | `bench/results/latency_hp_runs.md` |
| 3b | Native mic, **release** APK, 2 GB Android 9 emulator | Through the page (Hindi mic pressed about 3 s): 108,849 bytes uploaded to the in-app server, about 3.4 s of 16 kHz audio. Same run: 24/24 online and in airplane mode, page check yes/yes/yes, peak PSS 183 MB (app 82 + renderer 104) | `bench/results/emulator-2gb-android9_2026-09-26_m1.md` |
| 6 | Loop guard on the page | A reply the guard cut, or whose text contains a loop of word variants, is marked `needs_review`: the page shows "⚠️ मूल वक्ता से जाँचें", does not auto-play it (typed or streamed), and offers the nearest verified glossary sentence (`education_glossary.nearest_verified`). Tests: `tests/test_nmt_review.py` (page and lookup, no models) and `tests/test_api.py` (end to end) | `app.py`, `pipeline.py`, `frontend.html` |
| 7 | Old-WebView test in CI | CI runs the whole suite; the step logs need a GitHub login, so CI now also writes a public run summary (`.github/ci_summary.py`): counts, and the Chrome-69 test by name | `.github/workflows/tests.yml`, the run's Summary page |
| 4 | Tablet pass (Realme Pad Mini), prepared | One-pass `tools/android/device_check.py` (release APK, release-safe pack import folder, 24 checks online and in airplane mode, page checked through the accessibility tree, optional screen recording, mic via the debug build, peak PSS). Session steps and the CA path: `docs/device_session.md`; hub log reader: `tools/hub_mic_check.py`. **No tablet result yet** | `docs/device_session.md` |
| 3 | Emulator clip + one-pass check, release APK | 2 GB RAM, Android 9 emulator (WebView 69), **release** APK, release-safe import folder: pack import 7.2 s; contract 24/24 online and 24/24 in airplane mode; page in the WebView (lessons listed, line chosen, Translate → Santali): yes / yes / yes; mic 3.02 s (debug build); peak PSS 174 MB (app 77 + renderer 96-98; the earlier run: 185 MB). Clip `docs/demo_assets/android_emulator.mp4` (6.7 MB, about 30 s), caption as in `docs/demo_assets/README.md` | `bench/results/emulator-2gb-android9_2026-09-26_m1.md` |
| — | **CI was red since 873f6b0**, fixed | The Android test pack's 8 audio clips were never committed (a global `*.wav` rule in `.gitignore`), so `tests/test_android_assets.py::test_the_android_test_pack_is_intact` failed in every fresh clone (the Android unit tests would too); it passed here only because the files exist locally. Reproduced in a fresh clone with the CI requirements; fixed with a `.gitignore` exception and the clips committed (1 MB) | `.gitignore` |
| 5 | Demo script v1.2 | The Android segment is a recorded clip (Realme Pad Mini if its check passes, else the 2 GB emulator), with its exact caption and the 2 GB emulator line | `docs/demo_video_script.md`, `docs/demo_assets/README.md` |

---

## FREEZE. Decisions applied; M1 on a 2 GB Android 9 emulator (branch `android-wp4`)

| # | Item | Result | Evidence |
|---|---|---|---|
| 3 | Hindi silence trimming | **Off** (`config.ASR_TRIM_SILENCE`): normalised WER 12.5% untrimmed vs 13.1% trimmed | `asr_decoding_public.md` |
| 2 | Tablet NMT: int8 + guards | `nmt_guard.py`: length cap 2 x input + 10 tokens, and a stop on loops of word variants (same 3-letter stem, 3+ different words in the last 4); on for int8 only. On the saved outputs the guard fires on 2 of 7078 fp32 outputs, both genuine loops. The int8 run-ons seen: the ᱥᱟᱯᱷ… loop is stopped (one word kept), a 76-word counting run-on is capped to 50 words. IN22-Conv int8 with the guards: chrF++ **32.0 / 35.0** (unchanged; fp32 32.2 / 35.1). Tests: `tests/test_nmt_guard.py` | `eval/results/benchmarks_onnx-int8.md` |
| 1 | Tablet ASR | 120M for Hindi and Santali. Santali fp32 vs int8: rule recorded (fp32 if peak PSS stays under 900 MB with ASR + NMT + TTS loaded). **Not decided yet**: those engines are not on the device before M3-M4, so that PSS is NOT MEASURED. README/STATUS: "laptop hub = higher accuracy, tablet = portable" | README §4 |
| 4 | **M1 on a 2 GB RAM, Android 9 emulator** (API 28, x86_64, 4 cores, MemTotal 2.0 GB, WebView 69) | Pack import (SHA-256 checks) 7.6 s; REST contract **24 of 24** with network and **24 of 24 in airplane mode**; native mic 3.00 s captured at 16 kHz; typed lesson line 31 ms (median, over adb); **peak PSS 185 MB** (app 89 + WebView renderer 96) | `bench/results/android_m1_emulator-2gb-android9.md` |
| 4 | Bug found on Android 9, fixed | The page did not run at all: Android 9's WebView (Chrome 69) has no `??`, a syntax error that stopped the whole script (no lessons shown). Replaced by a helper; `tests/test_frontend_offline.py` now fails on post-Chrome-69 syntax and APIs. After the fix: lessons, session and typed translation checked through the real WebView (screenshots). CSS flex `gap` is not supported there: some spacing is lost (cosmetic) | `frontend.html` |
| 4 | Realme Pad Mini over USB | **NOT MEASURED**: no device connected yet (`adb devices`) | — |
| d | Demo path (`tools/demo_reset.py`) | **Bug found and fixed:** a reply made from a voice clip cached over 30 min earlier got a dead audio link (404): `shutil.copy2` kept the cache file's old time and the pruner deleted the reply at once. Now `copyfile`; regression test in `tests/test_api.py` (fails with the old code). After the fix `demo_reset.py` ends with **Ready**; the page's demo path checked in the browser: teacher line → Santali with the glossary badge and audio (served), Santali → Hindi, child's answer ᱗ green, a correction reused (placeholder, then removed with `--forget-demo-correction`), worksheet PDF, flashcards, lesson-import draft (3 lines, labels, NIPUN-G1-NUM-1) | `tools/demo_reset.py` |
| c | Demo script | `docs/demo_video_script.md` v1.1: laptop hub flow, plus a 20 s "Android app (work in progress)" segment showing only M1 on the tablet (now a Realme Pad Mini) in airplane mode, with its exact caption; to be filmed only after `device_check.py` passes on the tablet (now a Realme Pad Mini) | `docs/demo_video_script.md` |
| — | Latency, 3 runs | **Waiting for you**: high-performance power plan (a system setting I may not change) and other apps closed | — |

---

## F1-A2. Transducer (RNN-T) export for hotwords (branch `android-wp4`)

Laptop (WSL2), 2 threads; public clips (n = 80 per language; Hindi n_distinct = 69). Santali: IndicVoices
validation split (no public Santali test split); may overlap model-development data. Nothing on a tablet yet.

| Item | Result | Evidence |
|---|---|---|
| Export | IndicConformer 120M hi and sat, RNN-T branch, to sherpa-onnx NeMo transducer: encoder 481.5 MB (int8 137.5), decoder 13.8 (3.5), joiner 3.6 (0.9); tokens.txt and bpe.vocab (for hotwords). Multisoftmax as the fork decodes it (read from nemo-v2's source): per-language joiner layer (257 outputs), blank = local index 256, local token ids fed back into the shared embedding. The fork's joiner could not go through NeMo's exporter (a `language_ids` input); exported through a wrapper of the same computation | `tools/export/indicconformer_sherpa_export_rnnt.py` |
| Accuracy vs NeMo RNN-T (normalised WER vs reference) | fp32 greedy: Hindi 10.9% (NeMo 10.9%), Santali 33.4% (NeMo 34.5%); same text as NeMo on 59 / 44 of 80. int8 greedy: 11.0% / 35.8% | `bench/results/sherpa_vs_nemo_rnnt.md` |
| Issue #3267 (empty / hallucinated output with modified beam search) | **Not reproduced on our RNN-T models:** 0 empty outputs in every configuration (greedy, beam, beam+hotwords; fp32 and int8). Hallucinated (WER ≥ 0.5 against NeMo where NeMo was < 0.5 against the reference), without hotwords: 0-2 of 80 | same |
| Hotwords, unrelated to the clip (all lesson answers in that language, score 1.5) | Changes 15 of 80 Hindi and 34-37 of 80 Santali outputs; WER vs reference rises about 3-6 points (Hindi fp32 beam 10.8% → 16.5%, Santali 33.2% → 36.2%); hallucinated 2-7 of 80. Biasing with a broad list harms free speech: F4 must bias only an assessment step, with that step's answers, and must pass the false-accept test (STATUS PF3) | same |
| 120M RNN-T vs the app's 600M | Santali NeMo RNN-T 120M 34.5% vs 600M RNN-T 31.0% (trim on); Hindi 10.9% vs 13.1% | `asr_decoding_public.md` |

---

## F1-M1. App shell (branch `android-wp4`)

Measured on the Android **emulator with 4 GB RAM** (API 37, x86_64, 4 cores).
The AVD asks for 2 GB, but the emulator raises API 37 images to 4096 MB, so this
is **not** a 2 GB measurement. Not yet on the tablet (now a Realme Pad Mini) or on Android 9.

| Item | Result | Evidence |
|---|---|---|
| Shared REST contract | `contract/rest_contract.json` (24 cases + setup) and `contract/runner.py`. The **hub passes** (`tests/test_contract.py`); the tablet's Kotlin API passes the same file in JVM tests (`ContractTest.kt`) and **on the emulator: 24 of 24 with network, 24 of 24 in airplane mode** | `bench/results/android_m1_emulator-4gb.md` |
| App shell | Kotlin, minSdk 28, no AndroidX; WebView loads the repo's `frontend.html` (copied at build) from NanoHTTPD (BSD-3) on 127.0.0.1:5000, loopback only; cleartext allowed only for 127.0.0.1; APK 3.6 MB | `android/`, screenshot checked |
| Typed mode offline | Lesson lines, flashcard words and glossary sentences answer from the pack (teacher corrections first); a new sentence answers 503 `engine_not_on_device` until M4. Typed lesson line round trip: median 35 ms (over adb forward) | same |
| Content pack v0 | `tools/build_content_pack.py`: the hub's own /config, /lessons, /flashcards, all 17 lessons, 189 hi→sat and 18 sat→hi translations with source and review status, 399 Piper clips, 17 worksheet PDFs, SHA-256 manifest; 32.8 MB. Import checks every hash, refuses extra or changed files and paths outside the pack, keeps the old pack on failure (5 JVM tests); 3.3 s on the emulator. Hub route `GET /pack/latest`. Signing: M5 | `PackTest.kt` |
| Kotlin ports | `normalize_key` and answer grading match Python on 22 + 29 vectors (`tests/data/normalize_key_vectors.json`, checked from both sides) | `TextNormTest.kt`, `tests/test_android_assets.py` |
| Mic bridge | `window.VaaniMic`: AudioRecord 16 kHz mono PCM16 → WAV; the page uses it only inside the app. **Built, not exercised** (the emulator ran with no audio, and there is no on-device ASR before M3) | `MicBridge.kt` |
| Peak PSS | 117 MB after the checks (one dumpsys reading, not a peak over time) | `android_m1_emulator-4gb.md` |
| Bugs found on the device, fixed | (1) Android's ICU regex rejects `(?U)`: the Kotlin whitespace collapse crashed the app; now a plain loop. (2) A naming clash made `PackBridge.status()` call itself (stack overflow). (3) One failing request killed the app; the server now answers 500 and keeps running | commit |

**Not done in M1 / differences:** file-picker and hub-download import are built
but were only exercised through the debug import path (same verified import code);
`/worksheet` on the tablet returns the pack's per-lesson sheet, not one made from
the session's translated lines as on the hub; endpointing is off with the native mic;
new UI strings exist in Hindi and English, and Santali falls back to Hindi until a
native speaker writes them.

**Needed from you:** (1) a 2 GB emulator needs an Android 9-11 x86_64 system image
(about 1 GB download from Google via Android Studio's SDK Manager); may I install
one, or will you? (2) the tablet over USB (now a Realme Pad Mini) (developer mode, USB debugging)
for M1 on real hardware.

---

## F1-A. Phase A: can the engines run on a tablet? (branch `android-wp4`)

Everything here is measured on the **laptop** (WSL2 or Windows), 2 threads.
Nothing ran on a tablet: on-device figures are **NOT MEASURED**.

| Item | Result | Evidence |
|---|---|---|
| Export environment | WSL2 Ubuntu 26.04 with Python 3.10.21 (uv), AI4Bharat NeMo `nemo-v2` @ 8dce88cf8 installed with `.[asr]` on CPU torch 2.3.1. Five pins were needed before NeMo imported (numpy<2, Lightning 2.2.5, setuptools<81, pyarrow 16.1.0, ml-dtypes 0.4.1). The Colab notebook is regenerated from the same script | `tools/export/requirements-nemo-wsl.txt`, `indicconformer_sherpa_export.{py,ipynb}` |
| The 120M models are multisoftmax | The "Hindi" and "Santali" 120M models each hold all 22 language tokenizers and a 5633-output CTC head (22 x 256 + blank), masked per language. Exported by keeping the language's 256 rows plus blank (Hindi 1536-1791, Santali 4352-4607) | `bench/results/export_120m_check.md` |
| Export is exact | Exported graph (fp32, NeMo features) = NeMo CTC transcript on **80 of 80** clips, Hindi and Santali | `export_120m_check.md` |
| sherpa-onnx, fp32 (482 MB) | Normalised WER: Hindi 11.6% (NeMo 11.0%), Santali 37.4% (NeMo 37.3%). Identical to NeMo on 56 / 39 of 80: sherpa computes its own features. 528 / 406 ms median | `bench/results/sherpa_vs_nemo.md` |
| sherpa-onnx, int8 (138 MB) | Hindi 11.8%, Santali **39.2%** (+1.9 points over NeMo). 601 / 451 ms: on this x86 laptop int8 is slower than fp32; on ARM NOT MEASURED | same |
| 120M vs the app's 600M | Hindi 120M NeMo CTC 11.0% vs 600M CTC 12.5% (no trim); Santali 120M 37.3% vs 600M CTC 34.4%. Different models, same clips, same normalisation | `sherpa_vs_nemo.md`, `asr_decoding_public.md` |
| IndicTrans2 ONNX fp32, 300 sentences each way, 2 threads | **300 of 300** identical to PyTorch in both directions (first test of sat→hin); 344 / 321 ms vs PyTorch 639 / 599 ms | `golden_nmt_fp32_t2_{hi,sat}300.md` |
| IndicTrans2 ONNX int8, same | **Fails the ≥ 98% identical target**: 154 / 109 of 300 identical; chrF++ vs PyTorch output 90.0 / 81.7; 125 / 115 ms. Quality on IN22-Conv: 32.0 / 35.0 vs fp32 32.2 / 35.1 (`eval/results/benchmarks_onnx-int8.md`). So: different outputs of similar measured quality | `golden_nmt_int8_t2_{hi,sat}300.md` |
| Size on disk (int8 set) | ASR 138 MB x 2 + NMT int8 517 MB (the two decoder graphs duplicate the decoder weights) + Piper voice 64 MB = about 0.86 GB. RAM on a 2 GB device: **NOT MEASURED** | files above |

**Decisions for you:**
1. Which ASR for the tablet? (a) 120M per language: 138 MB each, int8 costs Santali 1.9 WER points; (b) 120M fp32: 482 MB each. I recommend (a) for Hindi, and measuring (a) vs (b) for Santali on the tablet (now a Realme Pad Mini) before choosing.
2. Translation on the tablet: int8 (517 MB, about 5x faster than PyTorch, not token-identical, IN22-Conv within 0.2 chrF++) or fp32 (2.05 GB, too large for 2 GB RAM)? I recommend int8, with the golden-test target changed from "identical" to "IN22-Conv chrF++ within 0.5", since that is your L1 rule.
3. For F4 hotwords, also export the RNN-T branch (encoder, decoder, joiner). The export needs the same multisoftmax slice on the joint network; not done yet.

---

## PF3. Decisions applied (branch `phase-p-finish`)

| # | Decision | Done | Evidence |
|---|---|---|---|
| 1 | Santali set = IndicVoices validation split, labelled | Label "IndicVoices validation split (no public Santali test split); may overlap model-development data" wherever a Santali ASR number appears (README, deck_numbers, claims, the ASR report). Checked: the IndicVoices paper trains its own 130M IndicASR "using only the IndicVoices train set" and does not say how the validation split was used; the IndicConformer cards we use name no training data. So **unknown**. IndicVoices-R is not used for ASR evaluation | `docs/sources.md#indicvoices` |
| 2 | `<unintelligible>` out of references only | `textnorm.strip_reference_tags` (references) + `normalize_for_wer` (both sides, no tag removal); **2 tokens removed**, in 2 of 80 Santali references. Every WER is unchanged (no hypothesis contained a tag). ASR report rebuilt from the saved raw transcripts (`bench/asr_decoding.py --rescore`) | `bench/results/asr_decoding_public.md`, `tests/test_wer_norm.py` |
| 3 | Hindi duplicates | WER keeps all 80 clips; translation and latency use the first clip of each of the **69 distinct** sentences; n and n_distinct in every table (ASR, voice to voice, Phase L, engines, endpointing, translation benchmarks, chunking). Rebuilt from saved CSVs/translations (`--rescore`); the engine comparison was re-run on 99 distinct sentences | README §6, `bench/results/*.md`, `eval/results/benchmarks.md` |
| 4 | Santali decoding | Already in place: RNN-T with trimming; answers of ≤ 10 words p90 **2.34 s** (41 answers, 1 over 3 s). Hindi stays on CTC | `…_public_sat_rnnt_trim.md` |

What changed in the numbers (distinct sentences instead of all clips):
- Phase L, ≤ 17 words full p90 (n = 38, n_distinct = 32): before 3.46 s (was 3.74), run 1 2.48 s, run 2 3.02 s (unchanged). Time to first audio p90 (n_distinct = 69): before 2.43 s, run 1 **2.46 s** (was 2.32), run 2 **2.68 s** (was 2.30); int8 **3.07 s**, over the 3 s target (was 2.13).
- Voice to voice hi→sat (n = 79, n_distinct = 68): median 1.96 s, p90 2.25 s. Before Phase L: 2.99 / 3.72 s, 34 of 68 over 3 s.
- Engines (99 distinct): ONNX fp32 504 ms vs PyTorch 1455 ms, 99 of 99 identical; int8 244 ms, 42 of 99 identical.
- Translation benchmarks: IN22-Conv n = 1503, n_distinct 1497 (hi) / 1500 (sat); scores on distinct sources equal the published-style scores to one decimal.

**Plan recorded for F4 (decision 6), expected-answer biasing:**
- Biasing may change only the **displayed** transcript. The grade comes from an **unbiased** decoding pass, or from the biased pass only when its score beats the unbiased one by a fixed confidence margin.
- The test set must include clips of **wrong** answers for every assessment step.
- Report: true-accept rate (right answers graded green) and **false-accept rate** (wrong answers turned green), with and without biasing. Biasing ships only if false accepts do not rise.

---

## PF2. Checkpoint review answers (branch `phase-p-finish`)

Laptop, offline; public datasets, adult speech; child speech NOT MEASURED.
Every number below is printed by `tools/deck_numbers.py` from the file named.

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Numbers from files | My earlier chat summary quoted the Santali RNN-T row **with** trimming (31.1%, 1070 ms) while the app then ran it without (31.3%, 1154 ms). Files and docs were right; the summary was not. New test: every decimal number in `docs/claims.yaml` must appear in the file that claim cites (`tests/test_claims.py`). It caught one more: the int8 claim quoted differences (0.2 / 0.1) I had computed; now it quotes only file values | `tests/test_claims.py` |
| 3 | WER normalisation | Raw and normalised WER, rules in `bench/README.md` ("WER normalisation"): NFC; dataset tags (`<unintelligible>`, 2 Santali transcripts) removed; all punctuation incl. `।` `॥` `᱾` `᱿` to spaces; Devanagari and Ol Chiki digits to ASCII; whitespace collapsed. Same rules for Hindi. **Correction:** the WERs reported before (Hindi 11.1%, Santali 31.3%) used the app's answer-matching key, which also folds nukta and chandrabindu; they were neither raw nor normalised by these rules. Replaced | `bench/results/asr_decoding_public.md`, `textnorm.normalize_for_wer`, `tests/test_wer_norm.py` |
| 3 | Hindi, CTC, trimmed (in use) | WER raw 14.3%, normalised 13.1%, CER 4.9%; 485 ms median | `asr_decoding_public.md` |
| 2 | Santali silence trimming | RNN-T: normalised WER 31.0% trimmed vs 31.2% not; 1144 vs 1281 ms. 8 of 80 transcripts change: 3 better, 2 worse. **Trimming on for Santali** (`config.ASR_TRIM_SILENCE`). The earlier "off" came from synthetic clips, where trimming seemed to clip quiet word-final stops; real speech does not show it | `asr_decoding_public.md`, `.jsonl` |
| 2 | Hindi silence trimming (not changed) | On this data trimming is 0.6 points **worse** for Hindi (normalised WER 13.1% vs 12.5%) for 31 ms. It was chosen on synthetic clips. **Your call:** switch Hindi trimming off? (All Hindi latency numbers were measured with it on) | `asr_decoding_public.md` |
| 4 | Santali decoding | Rule: RNN-T if Santali → Hindi p90 ≤ 3 s for answers of ≤ 10 words. RNN-T (trimmed): **2.34 s** (41 answers, 1 over 3 s) → **RNN-T**. CTC (trimmed): 1.77 s. Trade-off: 0.4-0.6 s more per reply for normalised WER 31.0% vs 34.7%. All lengths: RNN-T median 2.22 s, p90 2.57 s, 2 of 79 over 3 s; CTC 1.69 / 2.01 s, 1 of 79 | `…_public_sat_rnnt_trim.md`, `…_public_sat_ctc_trim.md`; length table in README §6 |
| 4 | Hotwords (sherpa-onnx) | Official docs: "Only transducer models support hotwords", with `modified_beam_search`; CTC not supported. NeMo transducer hotwords added 5 Feb 2026 (PR #3077). Open issue #3267: modified beam search on a NeMo TDT model returns empty or wrong text ~20% of the time; IndicConformer is RNN-T, effect NOT MEASURED | `docs/sources.md#sherpa-hotwords` |
| 4 | F4 plan: expected-answer biasing | Export the **RNN-T** branch (encoder, decoder, joiner) to sherpa-onnx as well as CTC, with `bpe.vocab`. At an assessment step, pass the lesson's `accept_answers` (Santali, plus Ol Chiki digits) as the stream's hotwords with a moderate score; everywhere else, no hotwords. Measure before adopting: answer accuracy with and without biasing, the false-accept rate on wrong answers (biasing must not turn a wrong answer into a right one), and the empty-output rate from issue #3267 | plan |
| 5 | Test split | Hindi: FLEURS **test** split only. Santali: IndicVoices has **no test split** (only `train` and `valid`), so the clips are from **valid**; the model card does not say whether valid was used in training. IndicVoices-R has a Santali test split, but it is a speech-synthesis corpus built from IndicVoices recordings. **Your call:** keep valid (labelled), switch to IndicVoices-R test, or record our own | `docs/sources.md#indicvoices`, `#indicvoices-r` |
| 5 | Leakage guard | `eval/test_set_hashes.json` now also holds the benchmark clips ("asr-public"): transcript hashes, source ids and the 62 Santali speaker ids. `assert_no_asr_test_leakage()` rejects a fine-tuning item with the same sentence, clip or speaker; `fetch_public_clips.py` refreshes it; a test fails if any training or fine-tuning script does not call a guard. FLEURS: the 80 clips hold 69 distinct sentences (several readers per sentence) | `eval/leakage.py`, `tests/test_leakage.py` |

Also since the first P-finish report: `bench_latency.py --asr-trim`; deck_numbers
length bins per direction, finer for Santali, with p90.

---

## PF. Phase P finished (first report; ASR numbers in it are superseded by PF2): Santali speech, translation benchmarks (branch `phase-p-finish`)

Hugging Face access arrived for all seven gated repos. Laptop, offline; public
datasets, adult speech; child speech NOT MEASURED. Numbers: `tools/deck_numbers.py`.

| Item | Result | Evidence |
|---|---|---|
| Santali clips | 80 IndicVoices valid clips (CC BY 4.0, 62 speakers, extempore and conversation, Ol Chiki transcripts), seeded like FLEURS. `fetch_public_clips.py` fixed for this dataset (audio column, clip id, age group) | `bench/clips/public/manifest.json` |
| ASR per language | Hindi: **CTC** (WER 11.1% vs 11.3%, 499 vs 1260 ms). Santali: **RNN-T** (WER 31.3% vs 34.5%, CER 10.6% vs 11.9%; 1154 vs 424 ms). `config.ASR_DECODING` changed to `sat: rnnt` | `bench/results/asr_decoding_public.md` |
| Voice to voice, both directions | Upload to reply audio: hi→sat median 1.95 s, p90 2.24 s, 0 of 79 over 3 s. sat→hi with RNN-T median 2.19 s, p90 2.61 s, **2 of 79 over 3 s** (max 3.25 s); with CTC 1.68 / 1.94 s, 0 of 80 | `…_public.md`, `…_public_sat_rnnt.md` |
| Translation, chrF++ / BLEU | hin→sat / sat→hin: IN22-Gen 31.3 / 37.6, IN22-Conv 32.2 / 35.1, FLORES devtest 27.4 / 34.1 (chrF++). All at or above the paper's all-source averages (a plausibility range only) | `eval/results/benchmarks.md` |
| Int8 translation (L1 rule) | IN22-Conv chrF++ 32.0 / 35.0: drops 0.2 / 0.1, within 0.5. **Kept for the tablet (F1)**; the laptop stays on fp32 (identical to PyTorch, targets already met; int8 has run-on outputs on long sentences) | `eval/results/benchmarks_onnx-int8.md` |
| Chunking quality | FLORES devtest, 814 sentences of 18+ words: chunked chrF++ 27.3 vs whole 27.5 (BLEU 2.3 vs 3.4). Closes the L2 "NOT MEASURED" | `eval/results/chunk_quality.md` |
| Phase L re-run | Same settings, second run: ≤ 17-word full p90 **3.02 s** (run 1: 2.48 s); first audio p90 2.30 s. The slow clips were slow in every step at once (ASR 1.7-2.4 s vs 0.7 s median): machine noise. **The ≤ 17-word target is borderline on this laptop**, not reliably met | `latency_steps_app.md`, `latency_steps_app_run1.md` |
| Unexplained earlier | The Phase L step bench (from end of speech) gives a higher hi→sat p90 (3.11 s) than the upload-to-audio bench (2.24 s) on the same clips. The two measure different paths (step-by-step calls vs one request) and ran at different times; not explained yet | both files above |
| deck_numbers fix | Sentence-length bins were pooling Hindi and Santali clips; now per direction | `tools/deck_numbers.py` |
| F1 Phase A prepared (not run) | Export notebook for the 120M hi/sat IndicConformer to sherpa-onnx CTC int8 (needs Python 3.10 + AI4Bharat NeMo `nemo-v2`: Colab or WSL2); stops rather than guesses if the model has per-language output masks. Comparison script sherpa vs NeMo | `tools/export/indicconformer_sherpa_export.{py,ipynb}`, `compare_nemo_sherpa.py` |

**Decisions for you:** (1) Santali on RNN-T (more accurate, 2 of 79 replies
over 3 s) or CTC (0 over 3 s)? I chose RNN-T. (2) Int8 translation for the
laptop too, or tablet only? I chose tablet only.

---

## L. Phase L: latency on realistic speech (branch `latency`)

Laptop, offline, from the end of speech (audio handed to the recogniser; upload,
decoding and endpointing not included). 80 FLEURS Hindi sentences (public
dataset, adult speech) and 30 lesson lines. Numbers: `tools/deck_numbers.py`.

| Target | Before | Now | Verdict |
|---|---|---|---|
| p90 full time, FLEURS sentences of ≤ 17 words | 3.74 s | **2.48 s** | **met** |
| p90 time to first audio, all FLEURS sentences (clause streaming) | 2.27 s | **2.32 s** | **met** |

| Item | Result | Evidence |
|---|---|---|
| L1a CTranslate2 | Not supported for this model (official converter list; no fairseq checkpoint for Indic-Indic) | `docs/sources.md#ctranslate2` |
| L1b ONNX Runtime fp32 | **Adopted.** 504 vs 1450 ms median on long sentences; 110 of 110 outputs identical to PyTorch; golden test 176 of 176 | `bench/results/nmt_engines.md`, `golden_nmt_fp32.md` |
| L1b ONNX Runtime int8 | 228 ms, but 43 of 110 identical and some long outputs run on (24+ words, full p90 7043 ms). **Off** until IN22-Conv shows chrF++ within 0.5 | `nmt_engines.md`, `latency_steps_onnx-int8-t6.md` |
| L1c PyTorch dynamic int8 | 901 ms, 16 of 110 identical. **Rejected** | `nmt_engines.md` |
| L2 clause streaming | `streaming.py` and `POST /translate/audio_stream` (NDJSON); the page plays chunks as they arrive. Used for utterances of 18+ words only: chunked output agrees with whole-sentence output at chrF++ 69 (median), quality vs references NOT MEASURED | `latency_steps_app.md`, `tests/test_api.py` |
| L3 endpointing | A 500 ms silence endpoint cuts **27 of 78** read FLEURS sentences early (pauses at commas); 0 of 30 lesson lines. Adaptive 500/1000 ms: 16 of 78. Built as a **setting, off by default** | `bench/results/endpoint_sim_*.md` |
| L4 tuning | Threads: translation 6, speech recognition 8 (more was slower); every engine warmed at start; output-length cap already sized to input; caches unchanged. In the end-to-end run, speech recognition was not faster (836 vs 774 ms median) despite the thread sweep; not explained yet | `bench/results/thread_sweep.md` |
| L5 word counter | Live count for typed Hindi; an estimate (≈, 2.2 words/s from FLEURS) while speaking; real count after recognition; past 15 words a Hindi hint | `frontend.html` |
| Environment incident | Installing an export tool pulled numpy 2, which breaks torch 2.2; restored numpy 1.26.4. `tests/test_environment.py` now guards it, and the export tools have their own requirements file | `tools/export/requirements-export.txt` |
| Model files | ONNX fp32 2.05 GB (the two decoder graphs each hold the decoder weights); int8 517 MB. For Android the two decoder graphs should share weights | `tools/export/export_indictrans2_onnx.py` |

---

## P. Phase P: publish and measure on public data (branch `phase-p`)

| Item | Result | Evidence |
|---|---|---|
| Push | `main` fast-forwarded `1115712` → `51545c7` and pushed; tag `v0.9-submission` pushed. CI ("tests") passed on `main` and on the tag; the badge reads "passing" | https://github.com/barath0512s-rgb/sih-hackathon/actions |
| Repo description and topics | **NOT DONE**: needs a GitHub login (`gh` is not installed). The current description claims "<4s", which was never measured | — |
| Hindi speech, public adult | 80 FLEURS test clips (CC BY 4.0, seeded). CTC (in use): WER 11.1%, CER 4.5%. RNN-T: WER 11.3%, CER 4.5%. CTC is 2.3× faster (907 vs 2081 ms median). **Decision: CTC stays for Hindi** | `bench/results/asr_decoding_public.md`, `.jsonl` |
| Voice to voice, public adult speech | hi→sat median 2.95 s, p90 3.69 s, max 5.68 s; **38 of 79 over 3 s**. It grows with length: 0-11 words 2.67 s (0 of 4 over), 24+ words 3.48 s (6 of 7 over). Translation is the largest part (NMT median 1744 ms) | `bench/results/Dell-Inc-Dell-G15-5520_2026-09-25_public.{md,csv}` |
| Santali speech, public adult | **NOT MEASURED**: `ai4bharat/IndicVoices` is gated and the account has no access (403). CTC vs RNN-T for Santali is therefore still undecided | `docs/sources.md#indicvoices` |
| Translation, chrF++ / BLEU | **NOT MEASURED**: IN22-Gen, IN22-Conv and FLORES are all gated (403). `eval/eval_benchmarks.py` is written and skips cleanly; its scoring path has not run yet | `eval/eval_benchmarks.py` |
| Test-set leakage guard | `eval/leakage.py`; `train_nmt.py` refuses to train if any sentence is a test sentence or if the test sets have not been hashed | `tests/test_leakage.py` |
| Fact-check protocol | `docs/sources.md` (every external fact, quoted, with access dates) and `docs/claims.yaml` (every README and deck claim). `tests/test_claims.py` fails if a README number has no evidence file | `tests/test_claims.py` |
| Corrections found while checking | (1) "Google Translate added Santali in 2024" is **TRUE** for the consumer Google Translate (Google India blog, 27 Jun 2024; Translate Help page). The Cloud Translation API does not list it. I first marked it unsupported after checking only the global blog and the Cloud API list; corrected. (2) The README's "115-155 ms" trimming saving was wrong: it is 115 ms (Hindi) and 156 ms (Santali). (3) FLORES is CC BY-SA 4.0, not stated in the prompt | `docs/sources.md#google-translate-santali` |
| Published reference scores | The IndicTrans2 paper gives no hin↔sat pair score, only averages into and out of Santali (IT2-Dist-M2M chrF++: FLORES 26.1/31.5, IN22-Gen 30.0/35.8, IN22-Conv 30.4/33.8). These are a plausibility range, not a like-for-like comparison | `docs/sources.md#indictrans2-paper` |

**Needed from you:** accept the terms (logged in as the Hugging Face account on
this laptop) on:
- `ai4bharat/IndicVoices`;
- `ai4bharat/indicvoices_r`;
- `ai4bharat/IN22-Gen` and `ai4bharat/IN22-Conv`;
- `facebook/flores`;
- `ai4bharat/indicconformer_stt_hi_hybrid_ctc_rnnt_large` and `…_sat_…` (for Phase F1).

Then either set the repo description and topics on GitHub, or install `gh` and
run `gh auth login`.

---

(Earlier: Checkpoint S, then WP14. Section 0 summarises the changes after
Checkpoint S.)

## 0. Since Checkpoint S

| Item | State | Commit |
|---|---|---|
| Word lists are flashcard-only until native review. Word-list cards say "word list" (not "verified glossary"). Every unreviewed card and every answer check with unreviewed answers shows a "review pending" badge. The six doubtful entries head `docs/native_review.md` | done | `54711f0` |
| `LICENSE` (MIT) for our code. `piper-tts` (GPL-3.0-or-later) is installed separately and not redistributed (`THIRD_PARTY_LICENSES.md`) | done | `54711f0` |
| **Finale plan, not started:** move speech synthesis to **sherpa-onnx (Apache-2.0)** on both the laptop and Android, removing the GPL dependency | planned | |
| WP14 curriculum import: paste or upload (.txt / .csv / .json); sentence split; script/activity/question labels the teacher can change; suggested Lakshya goals the teacher must confirm; Santali, audio, worksheet and flashcards; stored in SQLite; `pending_native_review` | done; the addendum's acceptance test passes (`tests/test_api.py::test_importing_a_ten_line_lesson`) | `4418c45`, `42ec510` |
| 10 lessons the team wrote (`content/team_lessons.json`), imported through WP14: 15 lessons. Then 2 more (Grade 3: numbers to 9999; read-aloud fluency): **17 lessons**. The server adds any missing team lesson on its first start | done; a fresh clone shows all 17 (checked) | `dfdb9cc` |
| **Bug found and fixed:** two overlapping model translations could hang a request for ever. `IndicProcessor` shares one placeholder queue and clears it after each batch. It could hit two classroom requests at once, or a request during the start-up pre-cache. Reproduced (6 overlapping: 5 stuck after 300 s), fixed with a lock (6 of 6 in 5.5 s), regression test added. The 3 lessons imported before the fix were re-checked: 22 of 22 lines match a fresh translation | done | `8cc1c41` |
| Real recordings: `bench/clips/real/` does not exist yet, so the benchmark was **not** re-run and CTC/RNN-T is not yet chosen per language | waiting for clips | |

### Pre-push polish (25 Sep)

| Item | Result | Commit |
|---|---|---|
| Files showing as modified | Line endings only: 13 files stored LF, checked out CRLF. `.gitattributes` fixes LF (CRLF for `.bat`); renormalising changed nothing in the index | `d0293b2` |
| Team lessons on first start | `app.seed_team_lessons()`; a fresh clone's first start added all 12 (17 in total) | `dfdb9cc` |
| Two Grade 3 lessons | numbers to 9999 (G3-NUM-1); 83-word read-aloud passage (G3-LIT-2, G3-LIT-1) | `dfdb9cc` |
| Worksheet headings | Hindi and Santali; only the Ministry's Lakshya text stays English | `8762dcb` |
| Fresh-clone test | clone, `python -m venv`, `pip install -r requirements.txt`, models linked, `download_models.py --verify-only` (423 files OK), `verify_models.py` (all pass), `pytest -q` (247 passed), `python app.py` (17 lessons). **Two README-path bugs found and fixed:** `download_models.py` could not download on a fresh machine (offline mode inherited from config.py); `verify_models.py` skipped the end-to-end speech check without a local clip | `b0519bf`, `6c97ee9` |
| CI | `.github/workflows/tests.yml` runs the model-free tests (simulated locally in a clean clone and venv: 222 passed, 25 skipped). The badge shows once pushed | `e0764ce`, `91b909a` |
| Demo | `docs/demo_video_script.md`, `tools/demo_reset.py` (run against the live server: 17 lessons, no online dependencies, warm-up 21.0 s) | `7997919` |

Notes:
- Commit `42ec510` describes the एक/समझ suggestion-rule change as its own. That change actually went in with `4418c45`; `42ec510` holds the Hindi messages and the deck-picker fix.
- The goal suggestions matched the team's own choice for 7 of 10 lessons, and 9 of 10 after tuning the rules on those same lessons, so this is not an independent accuracy figure. Line labels: the team changed none, but the lessons were written knowing the rules.

Branch `sih-final`, not pushed. Numbers come from `python tools/deck_numbers.py`
(laptop, offline). Anything with no script behind it is marked NOT MEASURED.

## 1. Ministry clauses (superseded: see "Ministry clauses at the submission freeze" at the top)

| # | Clause | Verdict | Evidence |
|---|---|---|---|
| 1 | Hindi-speaking teachers teach in the mother tongue (Ho, Mundari, Santali) with no language training | **PARTIAL**: Santali only | `test_pipeline.py`, `tests/test_api.py`. IndicTrans2 and IndicConformer do not support Ho or Mundari |
| 2 | Translate Hindi FLN content (lesson scripts, activity instructions, assessment prompts) into accurate text and synthesised audio | **PARTIAL**: text and offline audio for every line. Accuracy is **NOT MEASURED**, and no native review has been done. Content modes do not change the translation (documented in README §5) | `tests/test_api.py`, `tests/test_offline.py`, `docs/native_review.md` |
| 3 | Real-time voice to voice, no more than 3 s | **PARTIAL**. Laptop, offline. Short lesson lines (synthetic, median 6 words): median 1.51 s (hi→sat) and 1.57 s (sat→hi), 0 of 59 over 3 s. Long general sentences (public adult speech, FLEURS Hindi, median 17 words): median 2.95 s hi→sat, **38 of 79 over 3 s**. Santali public speech, child speech, tablet over Wi-Fi and on-device: **NOT MEASURED** | `bench/results/deck_numbers.txt` |
| 4 | Auto-generated bilingual worksheets and visual flashcard sets, aligned to NIPUN Bharat outcomes | **PARTIAL**: both are generated from the lessons and carry verbatim Lakshya IDs. 17 lessons (Balvatika to Grade 3, both domains); every Lakshya except G2-LIT-2 has a lesson; teachers can add lessons (WP14). Not met: the mapping is not teacher-reviewed; words per minute is counted by the teacher, not measured by the app | `tests/test_lakshya.py`, `tests/test_api.py::test_flashcards_are_built_from_the_lessons`, `docs/lakshya_mapping.md` |
| 5 | Whole application offline on low-cost tablets (2 GB RAM, Android 9+) after initial content synchronisation | **NOT MET**. Offline on the laptop only. A tablet browser can use the laptop hub (HTTPS for the mic, not yet tried on a tablet). No Android app, content pack or sync | `tests/test_offline.py`, `tests/test_https.py`; WP4 not started |
| 6 | Working application, demo video, GitHub repository | **PARTIAL**: application and repository exist; no demo video. `sih-final` is not pushed | |

## 2. Deck claims (`Team_8-BitPool_24BEC0207_VaaniSetu.pptx` / `.pdf`, 6 slides, the files on disk)

The verdicts are TRUE, FALSE and NOT MEASURED. "Fix" is a suggested rewording that stays true.

### Slide 2
| Claim | Verdict | Evidence / fix |
|---|---|---|
| "VaaniSetu — offline AI translation pipeline" | TRUE (laptop) | `tests/test_offline.py`. Fix: add "on the laptop" |
| "Student hears Santali (own voice)" | FALSE | A Hindi voice (`hi_IN-pratham-medium`) reads Santali transliterated into Devanagari; no Santali voice exists offline. How well children understand it: NOT MEASURED. Fix: "Student hears Santali (offline voice)" |
| "Teacher hears Hindi (reply)" | TRUE | `tests/test_api.py` (sat-to-hi with audio) |
| "Auto-generated bilingual worksheet + flashcard deck" | TRUE | `POST /worksheet`, `GET /flashcards` |

### Slide 3
| Claim | Verdict | Evidence / fix |
|---|---|---|
| "Frontend: single-file HTML/JS, zero build — opens in any browser, no install" | TRUE | `frontend.html`; it needs the laptop server running |
| "Backend: Flask REST API, 16 endpoints" | FALSE | 28 routes now (`grep -c @app.route app.py`), including 2 deprecated aliases. Fix: drop the number |
| "Full AI pipeline runs live … not a simulation" | TRUE | `test_pipeline.py`, `bench/bench_latency.py` |
| "Live per-response latency breakdown (ASR / NMT / TTS) shown to the teacher" | TRUE | frontend timing card; the browser-measured total is shown too |
| "ASR: IndicConformer 600M, ONNX/RNN-T" | FALSE | Decoding is **CTC** for both languages (`config.ASR_DECODING`), about 2× faster than RNN-T on synthetic clips (`bench/results/asr_decoding_synthetic.md`). Fix: "ONNX, CTC" |
| "NMT: IndicTrans2 320M, direct Hindi↔Santali, no English pivot" | TRUE | `config.NMT_REPO`; `english_pivot` is always empty |
| "TTS: Piper — offline neural, 0.15s per line (was 30s)" | NOT MEASURED | No script measured 0.15 s or 30 s. Measured instead (laptop, synthetic run): TTS stage median 196 ms (Santali) and 185 ms (Hindi), in the benchmark file. Fix: "TTS: Piper, offline, ~0.2 s per line on the laptop" (or drop the number) |
| "Verified offline — still works with internet sockets forcibly disabled" | TRUE | `tests/test_offline.py` |
| "Lesson script mode / Activity + assessment modes" | TRUE as UI modes | The modes do not change the translation (README §5) |
| "One-click worksheet download" | TRUE | |
| "Laptop or tablet, via Wi-Fi browser" | TRUE for the screen; tablet microphone NOT MEASURED | HTTPS hub added (`run_nijbhasha.bat https`), not yet tried on a tablet |
| "AI ENGINE — ON-DEVICE" | FALSE | Everything runs on the laptop; no Android app (WP4). Fix: "AI ENGINE — laptop hub, offline" |
| "Hindi↔Santali ASR — IndicConformer" | TRUE | |
| "TTS — Piper, offline neural voice" | TRUE | |
| "Correction cache checked before the model" | TRUE | `tests/test_api.py::test_correction_is_reused_both_ways` |
| "NIPUN Bharat lesson scaffolding" | TRUE | `lesson_engine.py` |
| "Santali audio playback (own script)" | TRUE for the Ol Chiki text on screen | The audio is a Hindi voice (see slide 2) |
| "Hindi response heard by teacher" | TRUE | |
| "Bilingual worksheet PDF" | TRUE | |
| "Green / yellow / red comprehension signal" | TRUE | `tests/test_api.py` |
| "NIPUN-aligned" | TRUE | Every lesson carries verbatim Lakshya IDs (`tests/test_lakshya.py`); the mapping is not teacher-reviewed |
| "NEP 2020 compliant" | NOT MEASURED | A policy claim no test can check. Fix: "aligned with NEP 2020's home-language recommendation" |

### Slide 4
| Claim | Verdict | Evidence / fix |
|---|---|---|
| "All 3 core AI models are already integrated and running … all open-source, CPU-only" | TRUE | |
| "Nothing left to build to prove the concept" | FALSE for clause 5 | On-device is not built |
| "Singh, Ekbal & Pakray, MMLoSo … fine-tuned IndicTrans2 achieves usable BLEU/chrF++ for Santali" | Not re-checked here | The audit verified the paper (ACL Anthology 2025.mmloso-1.9). It is **English↔Santali**, not Hindi↔Santali; say so. It was IJCNLP-AACL 2025 |
| "Real data already in use: the curated NIPUN corpus, AI4Bharat BPCC, NIPUN framework" | FALSE | The "corpus" is 33 pairs, used by no running feature and by no accuracy figure. BPCC is IndicTrans2's training data, not something we use. Fix: "IndicTrans2 (trained on AI4Bharat BPCC); NIPUN Bharat Lakshyas quoted in the code" |
| "the full ASR→NMT→TTS pipeline runs end-to-end offline, on CPU, with measured latency" | TRUE | `bench/results/` |
| "Santali (already built)" | TRUE | |
| "≤2GB Android budget" | wording | Write "2 GB RAM, Android 9+" (addendum C6) |
| "without losing the sub-second latency already measured" | FALSE | Measured voice to voice is 1.51 s / 1.57 s median (laptop, synthetic). Fix: "the 1.5 s median already measured on the laptop" |
| "INT8 ONNX export — the same technique already used for ASR" | FALSE | The ASR model is FP32 as downloaded. Fix: "INT8 ONNX export (planned for ASR and NMT)" |
| "100% local processing — audio never leaves the school's laptop, verified with sockets disabled" | TRUE | `tests/test_offline.py`; `ALLOW_ONLINE_TTS = False` |
| "DPDP Act 2023 aligned" | NOT MEASURED | No compliance review; no consent flow |
| "Interface is entirely in Hindi & Santali (no English)" | TRUE for the screen | The EN button shows only in evaluator mode (`?evaluator=1`). The worksheet PDF headings are English |

### Slide 5
| Claim | Verdict | Evidence / fix |
|---|---|---|
| "cuts dropout risk at the Grade-3 threshold" | NOT MEASURED | Fix: "aims to reduce …" |
| "Zero recurring cost — all models open-source/MIT-licensed" | FALSE (licence part) | IndicConformer and IndicTrans2 are MIT. The voice is **CC BY-NC-SA 4.0** and `piper-tts` is **GPL-3.0-or-later** (`THIRD_PARTY_LICENSES.md`). Fix: "no licence or cloud fees; models MIT, voice CC BY-NC-SA" |
| "Rs. 0 — Recurring cost — open-source, MIT-licensed" | TRUE for "no paid services"; FALSE for "MIT-licensed" | Same fix |
| "1,041 PALASH schools reached today" / "8 of 24 districts" | TRUE for PALASH, per the audit (PTI report, Jan 2026) | Reads as if VaaniSetu reached them. Fix: "PALASH runs in 1,041 schools in 8 of 24 districts (JEPC, Jan 2026)" |
| "Runs on the school's own laptop; tablets/phones join over Wi-Fi" | TRUE on our laptop | A typical school laptop: NOT MEASURED. Our laptop is an i7-12700H with 16 GB; the server's peak RAM is NOT MEASURED |
| "Day-1 Runs on existing laptops" | NOT MEASURED | Same |

### Slide 6
| Claim | Verdict | Evidence |
|---|---|---|
| Seven reference links | Per the audit, all resolve | Not re-checked here |

### Claims from the audited "v3" deck that are not in the files on disk
If a newer deck has these lines, they are **FALSE** today: "on-device AI pipeline
(Android tablet)", "Android tablet app (Android 9+, ≤2 GB RAM): full pipeline
on-device", "One-time content sync, then no network", "airplane-mode tablet test",
"On-device today … run on the tablet", "teacher fixes pooled at each sync". Two
v3 lines that were FALSE are now TRUE: "NIPUN Lakshya-tagged" (WP5) and a
flashcard deck built from lessons (WP7).

## 3. Numbers (`python tools/deck_numbers.py`, laptop, offline)

| Value | Result | Source |
|---|---|---|
| Voice to voice, hi→sat, median / p90 / max | 1.51 / 1.68 / 2.08 s (n=29) | synthetic-after CSV |
| Voice to voice, sat→hi, median / p90 / max | 1.57 / 1.85 / 2.25 s (n=30) | synthetic-after CSV |
| Requests over 3 s | 0 of 59 | same |
| Answered by the sentence glossary | 11 of 59 | same |
| Server boot, all models loaded | 20.4 s | synthetic-after .md |
| ASR / NMT model files | 2.56 GB / 1.30 GB | disk |
| Voice in use | 64 MB | disk |
| Real recordings, tablet, peak RAM, chrF++, child WER | NOT MEASURED | |
| Lessons / Lakshya-tagged / natively reviewed | 17 (5 built-in + 12 imported) / 17 / 0 | `lesson_engine.py` + local database |
| Lessons by stage and domain | Balvatika 2 lit + 2 num; G1 1 + 3; G2 2 + 2; G3 2 + 3 | same |
| Flashcard words in lessons | 89 | same |
| Tests | 247 pytest (8 files) + `test_pipeline.py` 7; 222 of them run in CI without models | `pytest --collect-only` |

The README previously said the Santali→Hindi median was 1.58 s. The raw median
is 1574.55 ms, so the correct figure is 1.57 s (1.58 came from rounding twice).

## 4. Submission track: done and not done

| Item | State | Commit |
|---|---|---|
| WP1 offline laptop build | done | `6f2f95d`, `652eb0e` |
| WP2 correctness fixes | done | `a236389` |
| WP3 honest latency, faster voice path | done | `a48860e`, `5ad58f4` |
| WP5 Lakshya tags | done | `a925c1c` |
| WP7 minimal flashcards | done | `7cfce08` |
| Hub-mode HTTPS | done; tablet mic not verified | `8dbb270` |
| README refresh, licences (C1), modes (C2), wording (C6), JEPC (C7), EN hidden (C8) | done | `6a03f6a` |
| `tools/deck_numbers.py` | done | `63e57c1` |
| Real-clip benchmark re-run | waiting for `bench/clips/real/` | |

## 5. Found at Checkpoint S (decided since: see section 0)

1. **The glossary word lists are not used for translation.** `lookup_hi_to_sat` matches whole verified sentences only. The `घर → ᱳᱲᱟᱜ` fix therefore reaches the lesson's accepted answers and the flashcards, but not free translation. Several word-list entries look doubtful: `बच्चा → ᱦᱚᱲ ᱠᱚ` ("people"), `कक्षा → ᱤᱥᱠᱩᱞ` ("school"), `कितना → ᱡᱚᱛᱚ` ("all"). They need native review before any wider use.
2. **The model is poor at single words.** Examples: `दो` → "this happens", `आठ` → "8 ᱜᱚᱴᱟᱝ", `तारा` → ᱥᱴᱟᱨ ("star" in English). The old flashcards showed these; the new ones use the word list first and label the source.
3. **The worksheet printed no Latin text at all**, because the Devanagari font has no Latin letters. Fixed in WP5; each script now gets its own font.
4. **Licence:** `piper-tts` is GPL-3.0-or-later. There is no `LICENSE` file for our own code; the team has to choose one.
5. **Addendum page numbers:** the JEPC home-language table is on printed p. 17, not p. 18. The README cites p. 17.
6. The in-app browser here would not open the self-signed HTTPS page, and I did not install the CA into Windows. The certificate was checked with a CA-pinned client instead.
