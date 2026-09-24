# VaaniSetu (वाणीसेतु), "Voice Bridge"

[![tests](https://github.com/barath0512s-rgb/sih-hackathon/actions/workflows/tests.yml/badge.svg)](https://github.com/barath0512s-rgb/sih-hackathon/actions/workflows/tests.yml)

**An offline Hindi ↔ Santali teaching assistant for Grade 1–3 classrooms in Jharkhand.**
The teacher speaks or types Hindi. The child hears Santali and can answer in
Santali. The teacher hears Hindi.

| | |
|---|---|
| Event | Smart India Hackathon 2026 |
| Problem statement | SIH26042, *AI-Powered Vernacular Pedagogy and Real-Time Translation Tool for Mother Tongue-Based Primary Education* (Government of Jharkhand) |
| Theme / category | Smart Education / Software |
| Languages | Hindi (Devanagari) ↔ Santali (Ol Chiki) |
| Runs today on | A laptop (the "laptop hub"), CPU only, no internet. A tablet or phone on the same Wi-Fi can use it through its browser |
| In progress | The Android app that runs everything on a 2 GB RAM, Android 9+ tablet with no laptop (work package 4). **Not built yet** |

The product name is on hold. It is set in one place, `APP_NAME` in `config.py`.

**Every number in this README comes from a script in this repository.** Run
`python tools/deck_numbers.py` to print them with their source files. Anything
without a script behind it is marked **NOT MEASURED**.

---

## 1. The problem

The JEPC Language Mapping Survey, Phase 1, was carried out by the Jharkhand
Education Project Council with JCERT. Its data was collected in January and
February 2024
([report](https://languageandlearningfoundation.org/wp-content/uploads/2025/04/LM-Report-Jharkhand-Phase-1.pdf);
page numbers below are the report's printed page numbers).

- Coverage: 7 districts, 72 blocks, **8,244 schools**, **1,06,930 Grade 1 students** (p. 13).
- *"In the surveyed districts, Hindi serves as the Medium of Instruction (MoI) in approximately 98% of schools."* (p. 18)
- Home languages of Grade 1 students include **Ho 17.03%, Santali 13.07%, Mundari 7.32%** (Table 1, p. 17).
- *"Approximately 80% of schools in the surveyed districts of Jharkhand, falling under Type II, III, and IV categories, pose moderate to severe learning disadvantages for students"* (p. 6).
- On children's Hindi, the report gives two figures. The executive summary says: *"The survey found that 36.1% of students have minimal proficiency, 41.2% have functional proficiency, and only 22.7% have good proficiency in Hindi."* (p. 6). The findings section says the minimal-proficiency segment is *"around 51.2% of students, indicating that a sizeable portion of the student population possesses a very less or no understanding of Hindi."* (p. 18). We quote both, because the report does.

So a child who cannot answer "दो और तीन कितने होते हैं?" may not be failing at
addition. They may not understand the Hindi question.

---

## 2. What the ministry asks for, and what runs today

The problem statement's clauses, one row each. "Runs today" means on the
laptop, offline, and checked by the named test or script.

| # | Requirement | Runs today (laptop, offline) | Not done yet | How to check |
|---|---|---|---|---|
| 1 | Hindi-speaking teachers teach in the mother tongue (Ho, Mundari, Santali) with no language training | **Santali only.** Hindi ↔ Santali, typed or spoken, with Santali speech | Ho and Mundari: the translation and speech-recognition models we use do not support them | `python test_pipeline.py` |
| 2 | Translate Hindi FLN content (lesson scripts, activity instructions, assessment prompts) into accurate text and synthesised audio | Every lesson line is translated to Ol Chiki text and spoken offline. 18 lesson sentences come from a hand-written glossary; other lines come from the model | Translation quality: **NOT MEASURED** (no held-out test set yet). No native speaker has reviewed the output or the Santali voice. Content modes organise the lesson but **do not change the translation** (see §5) | `pytest tests/test_api.py`, `tests/test_offline.py` |
| 3 | Real-time voice-to-voice dialogue, no more than 3 s | Laptop, **synthetic** clips (Piper reading the lines), in-process: median **1.51 s** Hindi→Santali and **1.57 s** Santali→Hindi; **0 of 59** over 3 s | Real teacher and child recordings: **NOT MEASURED**. Tablet over classroom Wi-Fi: **NOT MEASURED**. On a tablet with no laptop: **NOT MEASURED** | `python bench/bench_latency.py`, then `python tools/deck_numbers.py` |
| 4 | Auto-generated bilingual worksheets and visual flashcard sets, aligned to NIPUN Bharat learning outcomes | A bilingual PDF worksheet from the lesson just taught. Flashcard decks built from the lessons (`GET /flashcards`). Both carry the lesson's NIPUN Lakshya IDs, quoted word for word from the Ministry's guidelines. A teacher can add a lesson from Hindi text; it gets Santali, audio, a worksheet and flashcards (§3) | 17 lessons (Balvatika to Grade 3, literacy and numeracy): 5 built in, 12 written by the team and added through the same import path a teacher uses. Every Lakshya except G2-LIT-2 (45-60 words per minute) has a lesson. The lesson-to-goal mapping has not been checked by a teacher | `pytest tests/test_lakshya.py tests/test_curriculum.py` |
| 5 | Whole application offline on low-cost tablets (**2 GB RAM, Android 9+**) after initial content synchronisation | Fully offline **on the laptop**. A tablet's browser can use the laptop hub over local Wi-Fi. The hub can serve HTTPS so the browser may use the microphone (§9), but that is not yet checked on a real tablet. The tablet then needs the laptop | The on-device Android app, content pack and sync are **not built** (work package 4). Nothing runs on the tablet itself | `pytest tests/test_offline.py`; `GET /health/models` shows `online_dependencies: []` |
| 6 | A working application, a demo video and a GitHub repository | The application and this repository | Demo video: not recorded yet | |

---

## 3. What it does

1. **Two-way classroom dialogue.** Hindi → Santali and Santali → Hindi, typed or spoken, with speech in both directions.
2. **NIPUN Bharat lessons.** 17 lessons from Balvatika to Grade 3, in literacy and numeracy. Five are built in (counting, shapes, addition, reading words, subtraction). Twelve were written by the team in simple Hindi (`content/team_lessons.json`). The server adds them on its first start, through the same import path a teacher uses (below). Each lesson is a sequence of steps: the line to say, a teaching note, and for questions, the accepted answers.
2a. **Add a lesson (curriculum import).** The teacher pastes Hindi lesson text, or uploads a `.txt`, `.csv` or `.json` file (`grade, topic, line`). The app:
    - splits it into sentences;
    - labels each line as a lesson script, activity or question (the teacher taps a label to change it);
    - suggests NIPUN goals from the grade and keywords, which the teacher must confirm.

    It then makes the Santali and the audio for every line, a flashcard deck and a worksheet, and stores the lesson. Every Santali line is marked as awaiting native review.
3. **NIPUN Lakshya tags.** Every lesson names the NIPUN goals it works towards, e.g. `NIPUN-G1-NUM-2`: *"Perform simple addition and subtraction"*. See `docs/lakshya_mapping.md`.
4. **Answer checking.** After a question, the child's answer (Hindi or Santali, typed or spoken, any digit script: 7, ७, ᱗) is marked green, yellow or red.
5. **Session summary.** Steps done, lines translated, green/yellow/red counts.
6. **Bilingual worksheet (PDF)** of the lesson just taught, with its Lakshya tags.
7. **Flashcards** made from the numbers and nouns in each lesson. Each card says where its Santali came from: the word list, a teacher's correction, or the model. Anything no native speaker has checked carries a "review pending" badge. So does every answer check whose accepted answers are unreviewed.
8. **Teacher corrections are reused.** A 👎 opens a correction box. The correction is stored and used, before the model, every time that line comes up again, in either direction.
9. **Where each translation came from.** A badge on each translation shows its source: verified glossary, teacher correction, cached, or model. No confidence number is shown, because the model's score does not tell good output from bad (`eval/model_score_sanity.py`).
10. **Voice-to-voice timer.** The browser measures from the end of the teacher's input to the reply starting to play, and shows it.
11. **Offline.** No internet at any point after setup.

---

## 4. How it works

```
 Browser (frontend.html, one file, no build step)        Tablet browser on the same Wi-Fi
 Classroom · Lessons · Flashcards · Progress · Settings   (optional; https, see §9)
                 │   HTTP / JSON                                  │
                 ▼                                                ▼
 ┌─────────────────────────── laptop hub: app.py (Flask) ──────────────────────────┐
 │ pipeline.py                                                                     │
 │   voice ─ ffmpeg 16 kHz ─► ASR  IndicConformer 600M (ONNX, CTC)                  │
 │                             │                                                   │
 │   text ────────────────────►├─► 1. teacher correction   (SQLite)                │
 │                             ├─► 2. sentence glossary    (education_glossary.py) │
 │                             ├─► 3. earlier translation  (memory cache)          │
 │                             └─► 4. NMT  IndicTrans2 indic-indic 320M, greedy    │
 │                                          │  direct Hindi ↔ Santali, no English  │
 │                                          ▼                                      │
 │                             TTS  Piper, offline                                 │
 │                               Santali: Ol Chiki → Devanagari → Hindi voice      │
 │                               Hindi:   read directly                            │
 └─────────────────────────────────────────────────────────────────────────────────┘
   SQLite: corrections, sessions, latency log   ·   lesson_engine.py   ·   worksheet.py (PDF)
```

A translation is answered by the first layer that can answer it, in the order
shown. The model runs only when the other three cannot answer.

### Speech recognition: IndicConformer 600M
- `ai4bharat/indic-conformer-600m-multilingual`, ONNX Runtime on the CPU. It reads Santali (`sat`) in Ol Chiki natively.
- **CTC decoding** for both languages. On the synthetic clips, CTC was about twice as fast as RNN-T with no worse character error rate (`bench/results/asr_decoding_synthetic.md`). This is re-checked per language once real recordings exist.
- Leading and trailing silence is trimmed for Hindi. It is not trimmed for Santali, because trimming made Santali slightly worse on the same clips.
- There is no fallback. If the model files are missing, the server stops and says how to get them.

### Translation: IndicTrans2 indic-indic 320M
- `ai4bharat/indictrans2-indic-indic-dist-320M`, **direct** Hindi ↔ Santali. Going through English would lose distinctions English does not make, such as respectful आप versus familiar तुम.
- Greedy decoding (`NMT_NUM_BEAMS = 1`), `no_repeat_ngram_size = 3`, and an output-length cap sized to the input.
- The model sometimes starts its output with a label such as `ᱥᱮᱪᱮᱫ:` ("Teaching:"); that prefix is removed.
- At start-up, a background thread translates every lesson line and flashcard word once, so the lesson answers from the cache.

### Speech synthesis: Piper
- No offline voice reads Ol Chiki. `translit/olchiki.py` rewrites Santali in Devanagari, so the offline Hindi voice `hi_IN-pratham-medium` can speak it. For example, `ᱛᱮᱦᱮᱸᱡ ᱟᱞᱮ` becomes `तेहेँच् आले`.
- The transliterator is a parser, not a lookup table. It covers the whole Ol Chiki block, including digits (spoken as Santali number words), punctuation and every diacritic. Its core is cross-checked against the independent Aksharamukha transliterator, and 125 reference cases are tested. Its phonetic choices still need native review.
- If a clip cannot be made offline, the translation is still shown. The reply carries `audio_url: null` and a `tts_error`. The screen says so in Hindi, and the failure is logged. Silence is never played.
- gTTS (online) is off: it is used only if `config.ALLOW_ONLINE_TTS = True`.

---

## 5. Content modes

Every lesson step is typed as **lesson script**, **activity instruction** or
**assessment prompt**, as the problem statement names them. The modes organise
the lesson: they set the step's label, its teaching note, and whether an answer
is expected. **They do not change the translation.** The same Hindi line gets
the same Santali in every mode. Only the cache key includes the mode.

---

## 6. Measured performance (laptop, offline)

Laptop: Dell G15 5520, Intel Core i7-12700H, 15.7 GB RAM, Windows, CPU only.
Every figure is from `bench/`. See `bench/README.md` to re-run.

### Voice to voice, synthetic clips

60 clips of Piper reading classroom lines. **This is not real speech.** Each
clip is sent to `/translate/audio` exactly as the browser sends it. The time
runs from upload start to the reply audio being received. The app runs
in-process, so Wi-Fi is not included. Warm requests, empty caches.
Source: `bench/results/Dell-Inc-Dell-G15-5520_2026-09-24_synthetic-after.csv`.

| Direction | n | Median | p90 | Max |
|---|---|---|---|---|
| Hindi → Santali | 29 | 1.51 s | 1.68 s | 2.08 s |
| Santali → Hindi | 30 | 1.57 s | 1.85 s | 2.25 s |

- Requests over 3 s: **0 of 59**.
- Server start with all models loaded: **20.4 s**.
- The same benchmark before the latency work: median 2.19 s and 2.20 s, 1 request over 3 s (`…_synthetic-baseline.md`). Single runs vary; the next table isolates each change.

### What each change did

| Change | Measured effect | Decision | Source |
|---|---|---|---|
| CTC instead of RNN-T decoding | ASR about 2× faster (Hindi 693 vs 1521 ms), CER no worse | CTC for both languages | `asr_decoding_synthetic.md` |
| Trim silence at both ends | 115–155 ms less ASR time; CER better for Hindi, slightly worse for Santali | On for Hindi only | `asr_decoding_synthetic.md` |
| Warm the ASR up at start | The first request costs nothing extra (−105 ms, within noise) | Not added | `cold_start.md` |
| Size the NMT output limit to the input | No time saved, no output changed | Kept as a safety cap | `nmt_limits.md` |
| Play the first sentence early | At most 86 ms (median), on 22 of 60 replies | Not built | `tts_first_sentence.md` |
| Match glossary sentences ignoring punctuation | Spoken lesson lines answered by the glossary: 0 → 11 of 59 | Done | the two benchmark files |

### What the teacher sees

The timer's big number is measured **in the browser**: from releasing the
microphone (or pressing Translate) to the reply starting to play. The bars
under it are the server's ASR, NMT and TTS times. Every request is logged, and
`GET /metrics/latency` returns count, median, p90 and max per path.

### Not measured yet

| What | Status |
|---|---|
| Real teacher and child recordings | **NOT MEASURED** (`bench/clips/real/` is empty) |
| ASR error rate, adult vs child, quiet vs noisy | **NOT MEASURED** |
| Translation quality (chrF++ on held-out sentences) | **NOT MEASURED** |
| Voice to voice from a tablet over classroom Wi-Fi | **NOT MEASURED**. The browser logs it, so `/metrics/latency` will show it after classroom use |
| Anything on a 2 GB RAM, Android 9+ tablet | **NOT MEASURED** (work package 4) |
| Peak RAM of the laptop server | **NOT MEASURED** |

---

## 7. NIPUN Bharat alignment

Lakshya text is quoted from *NIPUN Bharat — Guidelines for Implementation*,
Ministry of Education, 2021, p. 11. The IDs are ours.

| Grade | Lesson | Lakshya IDs | Fit |
|---|---|---|---|
| 1 | Counting 1 to 10 | NIPUN-BV-NUM-1, NIPUN-G1-NUM-1 | full, partial |
| 1 | Basic Shapes | NIPUN-BV-NUM-2 | partial |
| 2 | Simple Addition | NIPUN-G1-NUM-2 | full |
| 2 | Reading Simple Words | NIPUN-BV-LIT-2, NIPUN-G2-LIT-1 | full, partial |
| 3 | Simple Subtraction | NIPUN-G1-NUM-2, NIPUN-G2-NUM-2 | full, partial |
| Balvatika | पाँच तक गिनती (counting to 5) | NIPUN-BV-NUM-1 | imported |
| Balvatika | छोटे से बड़े तक (small to big) | NIPUN-BV-NUM-2 | imported |
| Balvatika | अक्षर म (the letter म) | NIPUN-BV-LIT-1 | imported |
| Balvatika | दो अक्षर वाले शब्द (two-letter words) | NIPUN-BV-LIT-2 | imported |
| 1 | दस से बीस तक (10 to 20) | NIPUN-G1-NUM-1 | imported |
| 1 | छोटे वाक्य पढ़ना (short sentences) | NIPUN-G1-LIT-1 | imported |
| 2 | सौ से बड़ी संख्याएँ (numbers above 100) | NIPUN-G2-NUM-1 | imported |
| 2 | कहानी सुनो और समझो (listen to a story) | NIPUN-G2-LIT-1 | imported |
| 3 | गुणा: बराबर समूह (multiplication) | NIPUN-G3-NUM-2 | imported |
| 3 | पढ़कर समझना (reading for meaning) | NIPUN-G3-LIT-1 | imported |
| 3 | हज़ार तक की संख्याएँ (numbers to 9999, place value) | NIPUN-G3-NUM-1 | imported |
| 3 | ज़ोर से पढ़ना: रीना और तालाब (read-aloud fluency) | NIPUN-G3-LIT-2, NIPUN-G3-LIT-1 | imported |

Every stage from Balvatika to Grade 3 now has at least one literacy and one numeracy lesson, and every Lakshya except G2-LIT-2 (45–60 words per minute) has a lesson. For reading fluency (G3-LIT-2), the read-aloud lesson has an 83-word passage: the teacher times one minute and counts the words read; the app does not measure words per minute itself. For the imported lessons, the goals were suggested by keyword rules and confirmed by the team. Every mapping awaits teacher review.
Details: `docs/lakshya_mapping.md`.

---

## 8. The interface

- **Hindi by default, Santali as an option.** The teacher's screen has no English. The `EN` button appears only in evaluator mode: open the page with `?evaluator=1` (and `?evaluator=0` to turn it off again).
- The Santali interface text was written without a native speaker, so treat it as a first draft.
- Five views: Classroom (कक्षा), Lessons (पाठ), Flashcards (चित्र पत्ते), Progress (प्रगति), Settings (सेटिंग).
- Settings are kept in the browser: interface language, autoplay, large type, spoken confirmations, and the **server address**, which points a tablet's browser at the laptop hub.
- Keyboard: Ctrl/Cmd + Enter translates, Enter submits an answer, Escape closes dialogs.

---

## 9. Setup

You need Python 3.10 or 3.11, `ffmpeg` on PATH, and room for the model files
(`model_manifest.json` pins 423 files, 3.98 GB).

```bash
python -m venv vaanisetu_env
vaanisetu_env\Scripts\activate            # Windows
source vaanisetu_env/bin/activate         # Mac/Linux
pip install -r requirements.txt
python download_models.py                  # models and voices, pinned revisions, checked against model_manifest.json
python verify_models.py                    # loads everything, checks speech is audible
python app.py                              # the first start also adds the team's lessons, so it takes longer
```

Already have the models on another checkout? Copy (or link) its `models/`
folder into the new one and run `python download_models.py --verify-only`
instead of downloading again.

Open **http://127.0.0.1:5000**. On Windows, double-click `run_vaanisetu.bat`,
or use `run_vaanisetu.bat verify` to check everything first.

### Laptop hub for tablets on the same Wi-Fi

A browser allows the microphone only on `https://` pages or on localhost. To
let a tablet's browser use the laptop:

```bash
run_vaanisetu.bat https          # or: python app.py --https
```

This makes a certificate for the laptop's current Wi-Fi addresses
(`tools/make_cert.py`, files in `certs/`, never committed). It then serves on
port 5443 and prints the address to open on the tablet, e.g.
`https://172.18.222.252:5443`. The tablet either accepts the browser's
warning once, or installs the laptop's CA certificate (`/hub-ca.crt`, served by
the plain server on port 5000). That CA can vouch only for this laptop and for
private-network addresses.

Everything still runs on the laptop; the tablet is only a screen and a
microphone. Checked on the laptop: a client that trusts only the hub's CA
connects over the Wi-Fi address (`tests/test_https.py`). **Not checked yet:
the microphone on a real tablet.**

---

## 10. Tests

```bash
pip install -r requirements-dev.txt
pytest -q                  # tests that need the models are skipped without them
                           # (GitHub Actions runs this without models: .github/workflows/tests.yml)
python test_pipeline.py    # 7 end-to-end component checks
python verify_models.py    # the pre-flight check; writes verify_report.txt
```

The pytest suite covers:
- transliteration (125 cases);
- text normalisation and correction reuse;
- separate audio for concurrent requests;
- offline operation (network sockets blocked before the models load);
- the frontend loading nothing from the internet;
- the API's routes and responses;
- sessions surviving a restart;
- latency logging;
- speech-failure handling;
- Lakshya tags;
- worksheets and flashcards;
- the HTTPS certificate;
- curriculum import (splitting, labels, goal suggestions, uploads, and the addendum's acceptance test: a 10-line lesson with typed steps, Lakshya IDs, audio, a worksheet and at least 5 flashcards);
- overlapping translations finishing (a hang, fixed).

---

## 11. API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | The UI (`frontend.html`) |
| GET | `/config` | Product name, for the UI |
| GET | `/health` | Liveness and device |
| GET | `/health/models` | Per language: which ASR, NMT and TTS engine loaded, its files and size, and `online_dependencies` |
| GET | `/lessons` | All lessons with their steps and Lakshya tags |
| GET | `/flashcards?grade=&topic=` | Flashcard decks from the lessons, each card with its source and review status |
| POST | `/translate/text` | Translate typed text (`direction`: `hi-to-sat` or `sat-to-hi`) |
| POST | `/translate/audio` | Translate a recorded clip (multipart) |
| POST | `/translate/reverse` | Santali → Hindi shortcut |
| POST | `/speak` | Speak a given line as it is (`text`, `lang`: `sat` or `hi`) |
| GET | `/audio/<id>` | The clip for one reply |
| GET | `/audio/output`, `/audio/hindi` | Deprecated: the newest Santali / Hindi clip |
| POST | `/session/start`, `/session/next`, `/session/goto` | Run a lesson |
| POST | `/session/response` | Mark an answer to a given `step` (JSON, or multipart with `audio`) |
| POST | `/session/summary` | Session summary |
| POST | `/worksheet` | The bilingual PDF |
| POST | `/feedback` | 👍 / 👎 or a correction, with `direction` |
| POST | `/metrics/client` | The browser's own timing for a request |
| GET | `/metrics/latency` | Count, median, p90 and max per path |
| POST | `/curriculum/import` | Hindi text or a `.txt` / `.csv` / `.json` file → draft lessons: lines with suggested labels and suggested NIPUN goals. Nothing is stored |
| POST | `/curriculum/save` | The teacher's corrected draft with `lakshya_confirmed: true` → Santali, audio, flashcards, stored lesson |
| GET | `/curriculum` | The imported lessons |
| GET | `/curriculum/<topic>/worksheet` | An imported lesson's worksheet (PDF) |
| GET | `/lesson_audio/<topic>/<n>` | The audio for line n of an imported lesson |
| GET | `/hub-ca.crt` | The laptop hub's CA certificate, for tablets |

A reply from `/translate/text`:

```json
{
  "translated_text": "ᱜᱤᱫᱽᱨᱟᱹ ᱠᱚ ᱵᱤᱨᱫᱟᱹᱜᱟᱲ ᱨᱮ ᱪᱟᱞᱟᱣᱚᱜ ᱠᱟᱱᱟ ᱾",
  "source": "model",
  "model_score": 0.7,
  "audio_url": "/audio/110bfe8dd4fa448a95e12c280dfffeaa",
  "tts_error": null,
  "tts_engine": "piper",
  "request_id": "…",
  "latency": { "asr": 0.0, "nmt": 0.41, "tts": 0.12, "total": 0.53 },
  "english_pivot": "",
  "confidence": null
}
```

- `source` is `teacher`, `glossary`, `cached` or `model`.
- `model_score` is set only for `model` output. It is not a quality estimate, and the UI does not show it.
- `english_pivot` and `confidence` are always empty. They are kept so older clients do not break.
- The latency values are one example; yours will differ.

---

## 12. Project layout

| Path | What it is |
|---|---|
| `app.py` | Flask server |
| `pipeline.py` | ASR, translation layers, transliteration, Piper TTS, caches |
| `indicconformer_asr.py` | ONNX wrapper for IndicConformer |
| `translit/olchiki.py` | Ol Chiki → Devanagari / Latin transliteration |
| `textnorm.py` | Text normalisation for matching corrections and glossary lines |
| `education_glossary.py` | Verified sentences, word lists, and the log of glossary changes |
| `lesson_engine.py` | Lessons, flashcard words, answer checking, sessions |
| `nipun/lakshya.py` | NIPUN Lakshya goals, verbatim, with our IDs |
| `worksheet.py` | Bilingual PDF |
| `database.py` | SQLite: `feedback`, `sessions`, `session_events`, `latency_log` |
| `config.py` | Product name, paths, model revisions, settings |
| `frontend.html` | The whole UI |
| `download_models.py`, `model_manifest.json` | Fetch and verify the pinned model files |
| `verify_models.py`, `test_pipeline.py`, `tests/` | Checks and tests |
| `bench/`, `eval/` | Benchmarks and evaluations, with results |
| `tools/deck_numbers.py` | Prints every number the deck may use, with its source |
| `tools/make_cert.py` | Certificate for the HTTPS laptop hub |
| `curriculum.py` | Curriculum import: reading uploads, splitting, labels, goal suggestions, flashcard words |
| `content/team_lessons.json`, `tools/import_lessons.py` | The team's 12 lessons (added on first start), and a script to import other lesson files through the import endpoints |
| `tools/demo_reset.py`, `docs/demo_video_script.md` | Getting ready to record the demo, and the shot list |
| `docs/` | Lakshya mapping, glossary changes, the native-review list |
| `THIRD_PARTY_LICENSES.md` | Model, voice, package and font licences |
| `training_data/`, `train_nmt.py`, `generate_dataset.py` | A 33-pair corpus and a LoRA script. Not used for any accuracy figure |
| `_archive/` | Old scripts and drafts, not used by the app. Do not run `patch.py` or `extract.py` |

Git ignores `models/`, audio files, caches, the database, `certs/` and the
virtual environment. A fresh clone must download the models (§9).

---

## 13. Known limitations

| Item | Impact |
|---|---|
| Nothing runs on a tablet without the laptop | The ministry's on-device requirement is not met yet (work package 4) |
| Santali only; no Ho or Mundari | The models we use do not support them |
| No native speaker has reviewed the Santali | This covers translations, the glossary, the transliteration, the Santali interface text and the voice. See `docs/native_review.md` |
| Santali is spoken by a Hindi voice reading a transliteration | How well children understand it: **NOT MEASURED** |
| All speed figures use synthetic clips | Real classroom speech may be slower or less accurate |
| Word lists in `education_glossary.py` are used only for flashcards | Translation uses whole verified sentences only |
| Imported lessons are stored in the local database, not in git | The team's lessons are added again on any laptop's first start. A teacher's own imports stay on that laptop; content packs for tablets are work package 4 |
| Line labels and goal suggestions come from simple keyword rules | The teacher checks every label and must confirm the goals. The rules were tuned on the team's own lessons: they matched 7 of 10 goal suggestions before tuning and 9 of 10 after. That is not an independent accuracy figure |
| The NIPUN goal text on the import screen is in English | It is quoted from the Ministry's English guidelines |
| The worksheet's headings are in English | The on-screen interface is not |
| Flask development server | Fine for a classroom hub, not a public deployment |
| Default voice licence is non-commercial (CC BY-NC-SA 4.0); `piper-tts` is GPL-3.0-or-later, installed separately and not redistributed | Our code is MIT (`LICENSE`). Moving speech to sherpa-onnx (Apache-2.0) is planned for the finale. See `THIRD_PARTY_LICENSES.md` |

---

## 14. Roadmap

1. **Android app (work package 4):** on-device ASR, translation and speech on a 2 GB RAM, Android 9+ tablet, a content pack, and syncing teacher corrections.
2. **Real recordings:** re-run every benchmark on teacher and child speech. Report adult and child, quiet and noisy, separately.
3. **Native review** of the glossary, the number words, the transliteration and the voice.
4. **Curriculum import:** add worksheets from imported lessons to the content pack, and let teachers edit a lesson after saving it.
5. Move speech synthesis to sherpa-onnx (Apache-2.0) on both the laptop and Android.

---

## 15. Deck outline (for the slides)

Use only numbers printed by `python tools/deck_numbers.py`. Label them
"laptop, offline", and say "synthetic clips" wherever that applies.

| # | Slide | Content | Source |
|---|---|---|---|
| 1 | Title | Name, SIH26042, Smart Education | header |
| 2 | The problem | JEPC survey: 98% of schools teach in Hindi; Santali is 13.07% of Grade 1 home languages. Quote the report's exact sentences | §1 |
| 3 | What the ministry asks | The six clauses, with runs today / not done yet | §2 |
| 4 | What it does | The features in §3 | §3 |
| 5 | How it works | Laptop-hub diagram; the four translation layers | §4 |
| 6 | Speech in | IndicConformer, CTC measured about 2× faster than RNN-T (synthetic) | §4, §6 |
| 7 | Translation | Direct Hindi ↔ Santali, no English in between | §4 |
| 8 | Speech out | Ol Chiki → Devanagari → offline voice | §4 |
| 9 | Speed | 1.51 s / 1.57 s median, 0 of 59 over 3 s: laptop, offline, synthetic clips | §6 |
| 10 | NIPUN alignment | Lakshya table | §7 |
| 11 | Teacher corrections | Stored and reused before the model | §3 |
| 12 | Offline | Offline tests, `/health/models` | §2, §10 |
| 13 | What is next | Android on-device, real recordings, native review | §14 |

---

## 16. Credits

Models from **AI4Bharat** (IIT Madras): IndicConformer and IndicTrans2.
Offline speech by **Piper**. Fonts: Noto Sans Devanagari, Noto Sans Ol Chiki,
Baloo 2, Kalam. Learning goals from **NIPUN Bharat**, Ministry of Education,
Government of India. Our code: MIT (`LICENSE`). Everything else: `THIRD_PARTY_LICENSES.md`.
