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
| 2 | Translate Hindi FLN content (lesson scripts, activity instructions, assessment prompts) into accurate text and synthesised audio | Every lesson line is translated to Ol Chiki text and spoken offline. 18 lesson sentences come from a hand-written glossary; other lines come from the model | Translation quality on public test sets (the model alone): chrF++ Hindi → Santali 31.3 (IN22-Gen), 32.2 (IN22-Conv), 27.4 (FLORES-200); see §6. Lesson lines themselves: **NOT MEASURED** (no reference translations). No native speaker has reviewed the output or the Santali voice. Content modes organise the lesson but **do not change the translation** (see §5) | `pytest tests/test_api.py`, `tests/test_offline.py` |
| 3 | Real-time voice-to-voice dialogue, no more than 3 s | Laptop, offline, public adult speech, three runs (AC, Best performance mode, apps closed; median of the runs' p90s, distinct sentences, definitions in §6). **Headline, sentences of ≤ 17 words:** upload to reply audio Hindi → Santali **p90 2.14 s** (34 sentences); from the end of speech, full time **p90 2.85 s**, first audio p90 2.41 s (32 sentences). Santali → Hindi, all 80 answers: **p90 2.58 s**; answers of ≤ 10 words 2.27 s (IndicVoices validation split; may overlap model-development data). Neither figure includes the 500 ms silence endpoint, which is off by default | Longer sentences: 18-23 words take p90 2.47 s (upload) to 4.76 s (end of speech, pessimistic tail, §6) to finish; over all sentences, first audio p90 was 2.54, 2.75 and **3.40 s** in the three runs. Bins under 10 sentences are small samples. Child speech, classroom Wi-Fi, and a tablet with no laptop: **NOT MEASURED** | `python bench/latency_steps.py --backend app --tag hp1` and `python bench/bench_latency.py --clips bench/clips/public/manifest.json --label public_hp1` (three times), then `python tools/latency_runs.py` |
| 4 | Auto-generated bilingual worksheets and visual flashcard sets, aligned to NIPUN Bharat learning outcomes | A bilingual PDF worksheet from the lesson just taught. Flashcard decks built from the lessons (`GET /flashcards`). Both carry the lesson's NIPUN Lakshya IDs, quoted word for word from the Ministry's guidelines. A teacher can add a lesson from Hindi text; it gets Santali, audio, a worksheet and flashcards (§3) | 17 lessons (Balvatika to Grade 3, literacy and numeracy): 5 built in, 12 written by the team and added through the same import path a teacher uses. Every Lakshya except G2-LIT-2 (45-60 words per minute) has a lesson. The lesson-to-goal mapping has not been checked by a teacher | `pytest tests/test_lakshya.py tests/test_curriculum.py` |
| 5 | Whole application offline on low-cost tablets (**2 GB RAM, Android 9+**) after initial content synchronisation | Fully offline **on the laptop hub** (tablets use its browser page over local Wi-Fi). **Android app, work in progress (F1 M1):** on an Android 9 emulator with 2 GB RAM, in airplane mode, the app shows the lessons, flashcards and typed translations of lesson lines from a verified content pack, through the same page and REST contract as the hub (24 of 24 contract cases); peak PSS 185 MB (app + WebView) | On the tablet: speech recognition, translation of new sentences and voice synthesis are **not built yet** (M2-M4); the Samsung tablet itself: **NOT MEASURED** yet | `bench/results/android_m1_emulator-2gb-android9.md`; `pytest tests/test_offline.py` |
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

### Laptop hub and tablet: two set-ups

- **Laptop hub = higher accuracy.** The laptop runs the larger models: IndicConformer
  600M for speech and IndicTrans2 in full precision (fp32), identical to the
  published model.
- **Tablet = portable.** The Android app (work in progress) will run smaller
  engines that fit a 2 GB RAM, Android 9+ tablet: IndicConformer **120M** per
  language (Hindi and Santali) and IndicTrans2 **int8** with a length cap and a
  repetition guard (`nmt_guard.py`). Measured on the laptop: 120M Hindi WER
  10.9% (600M: 12.5%), 120M Santali 34.5% (600M: 31.0%); int8 IN22-Conv chrF++
  32.0 / 35.0 vs fp32 32.2 / 35.1. Santali on the tablet uses fp32 if the app's
  peak PSS stays under 900 MB with speech, translation and voice loaded,
  otherwise int8 (decided when those engines run on the device, M3-M4).

### Speech recognition: IndicConformer 600M
- `ai4bharat/indic-conformer-600m-multilingual`, ONNX Runtime on the CPU. It reads Santali (`sat`) in Ol Chiki natively.
- Decoding per language, from public speech (§6): Hindi **CTC**, Santali **RNN-T**. Silence trimming: Hindi off, Santali on.
- There is no fallback. If the model files are missing, the server stops and says how to get them.

### Translation: IndicTrans2 indic-indic 320M
- `ai4bharat/indictrans2-indic-indic-dist-320M`, **direct** Hindi ↔ Santali. Going through English would lose distinctions English does not make, such as respectful आप versus familiar तुम.
- Greedy decoding (`NMT_NUM_BEAMS = 1`), `no_repeat_ngram_size = 3`, and an output-length cap sized to the input.
- Runs on **ONNX Runtime** (fp32, 6 threads) when the exported model is on disk (`tools/export/export_indictrans2_onnx.py`); otherwise on PyTorch. The ONNX output is token-for-token identical to PyTorch on every sentence tested (`bench/results/golden_nmt_fp32.md`).
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
| Trim silence at both ends | With CTC, 115 ms (Hindi) and 156 ms (Santali) less median ASR time; CER better for Hindi, slightly worse for Santali | On for Hindi only | `asr_decoding_synthetic.md` |
| Warm the ASR up at start | The first request costs nothing extra (−105 ms, within noise) | Not added | `cold_start.md` |
| Size the NMT output limit to the input | No time saved, no output changed | Kept as a safety cap | `nmt_limits.md` |
| Play the first sentence early | At most 86 ms (median), on 22 of 60 replies | Not built | `tts_first_sentence.md` |
| Match glossary sentences ignoring punctuation | Spoken lesson lines answered by the glossary: 0 → 11 of 59 | Done | the two benchmark files |

### What the teacher sees

The timer's big number is measured **in the browser**: from releasing the
microphone (or pressing Translate) to the reply starting to play. The bars
under it are the server's ASR, NMT and TTS times. Every request is logged, and
`GET /metrics/latency` returns count, median, p90 and max per path.

### Public speech (adult), both directions

80 Hindi clips from `google/fleurs` (**test** split, CC BY 4.0, 3-10 s) and 80
Santali clips from `ai4bharat/IndicVoices` (**IndicVoices validation split (no
public Santali test split)**; CC BY 4.0, 62 speakers, Ol Chiki transcripts),
both seeded. The model cards do not say how that split was used, so the Santali
numbers **may overlap model-development data** (`docs/sources.md#indicvoices`).
None of these clips, sentences or speakers can be used for fine-tuning
(`eval/leakage.py`). **Public dataset, adult speech; child speech NOT MEASURED.**
Laptop, offline. `bench/fetch_public_clips.py` fetches the same clips for
anyone with access.

**n** = clips, **n_distinct** = distinct sentences. FLEURS has several readers
per sentence (80 clips, 69 sentences): WER uses all 80 clips (different
speakers); translation and latency use the first clip of each sentence.

Speech recognition (`bench/results/asr_decoding_public.md`; corpus-level).
**Raw** WER compares the texts exactly as written; **normalised** WER and CER
remove punctuation (including ᱾ and ।) and digit-script differences, the same
way for both languages, after removing dataset tags (`<unintelligible>`: 2 in
the Santali references) from the **references only** (rules: `bench/README.md`).

| Language | Decoding | Silence trimmed | n | n_distinct | WER raw | WER normalised | CER normalised | Median time |
|---|---|---|---|---|---|---|---|---|
| Hindi | **CTC (in use)** | **no (in use)** | 80 | 69 | 13.6% | 12.5% | 4.8% | 516 ms |
| Hindi | CTC | yes | 80 | 69 | 14.3% | 13.1% | 4.9% | 485 ms |
| Hindi | RNN-T | yes | 80 | 69 | 14.3% | 13.1% | 4.9% | 1314 ms |
| Santali | **RNN-T (in use)** | **yes (in use)** | 80 | 80 | 31.1% | 31.0% | 10.3% | 1144 ms |
| Santali | RNN-T | no | 80 | 80 | 31.3% | 31.2% | 10.4% | 1281 ms |
| Santali | CTC | yes | 80 | 80 | 34.7% | 34.7% | 11.6% | 386 ms |

Voice to voice, upload to reply audio, in-process (no Wi-Fi), warm requests:

| Direction | n | n_distinct | Median | p90 | Max | Over 3 s | Source |
|---|---|---|---|---|---|---|---|
| Hindi → Santali | 79 | 68 | 1.96 s | 2.25 s | 2.74 s | 0 | `…_2026-09-25_public.csv` |
| Santali → Hindi (RNN-T, trimmed: in use) | 79 | 79 | 2.22 s | 2.57 s | 3.15 s | 2 | `…_public_sat_rnnt_trim.csv` |
| Santali → Hindi (CTC, trimmed) | 79 | 79 | 1.69 s | 2.01 s | 3.85 s | 1 | `…_public_sat_ctc_trim.csv` |
| Hindi → Santali, before Phase L | 79 | 68 | 2.99 s | 3.72 s | 5.68 s | 34 | `…_public_before_phase_l.csv` |

Santali → Hindi by answer length (Santali words), median / p90 (IndicVoices
validation split; may overlap model-development data):

| Answer length | n | n_distinct | RNN-T (in use) | CTC |
|---|---|---|---|---|
| ≤ 10 words | 41 | 41 | 1.98 / **2.34 s** (1 over 3 s) | 1.58 / 1.77 s (0 over) |
| ≤ 5 words | 10 | 10 | 1.82 / 1.99 s | 1.34 / 1.54 s |
| 6-10 words | 31 | 31 | 2.04 / 2.34 s | 1.60 / 1.77 s |
| 11-17 words | 25 | 25 | 2.26 / 2.56 s | 1.73 / 2.01 s |
| 18+ words | 13 | 13 | 2.50 / 2.76 s | 1.90 / 2.21 s |

Santali uses RNN-T because the rule was: RNN-T if its p90 for answers of up to
10 words stays within 3 s (2.34 s). The trade-off: about 0.4-0.6 s more per
reply for 3.7 fewer word errors per 100 words. Silence trimming is on for
Santali too: normalised WER 31.0% vs 31.2% without, 137 ms faster.
Hindi stays on CTC, and Hindi silence trimming is **off**: on this data it was
0.6 WER points worse (13.1% vs 12.5%) for 31 ms.

### Translation quality (public test sets)

The model alone (no glossary, cache or teacher corrections), as the app runs it
(ONNX Runtime fp32, greedy). chrF++ and BLEU with sacrebleu
(`eval/eval_benchmarks.py`, `eval/results/benchmarks.md`). These sets are for
evaluation only; `eval/leakage.py` stops any training script that sees them.

| Test set | Licence | n | n_distinct (hi / sat sources) | Hindi → Santali chrF++ / BLEU | Santali → Hindi chrF++ / BLEU | Paper chrF++ (all-source avg, → sat / sat →) |
|---|---|---|---|---|---|---|
| IN22-Gen | CC BY 4.0 | 1024 | 1024 / 1024 | 31.3 / 4.2 | 37.6 / 15.8 | 30.0 / 35.8 |
| IN22-Conv | CC BY 4.0 | 1503 | 1497 / 1500 | 32.2 / 5.5 | 35.1 / 15.3 | 30.4 / 33.8 |
| FLORES-200 devtest | CC BY-SA 4.0 | 1012 | 1012 / 1012 | 27.4 / 3.3 | 34.1 / 12.6 | 26.1 / 31.5 |

Scores use every pair, as published results do. On distinct sources only
(IN22-Conv repeats a few short lines) every score is the same to one decimal
(`eval/results/benchmarks.md`).

For comparison only: the IndicTrans2 paper reports this model's chrF++
**averaged over all Indic languages** into / out of Santali (FLORES 26.1 / 31.5,
IN22-Gen 30.0 / 35.8, IN22-Conv 30.4 / 33.8). That is not the Hindi pair itself,
so it shows the scores are plausible, not better. Compare chrF++, not BLEU: the
paper tokenises Indic text differently.

### Speed on realistic speech (Phase L)

Two measures, both timed **from the end of speech**: from the moment the
recorded audio reaches the speech recogniser. Upload and audio decoding are not
included (laptop, in-process), and neither is endpointing (below).

- **Full time**: until the Santali audio for the **whole** utterance is ready.
  This is what a reply costs when the sentence is translated in one piece.
- **Time to first audio**: with **clause streaming** (`streaming.py`), a long
  utterance is cut at sentence ends and clause words (लेकिन, क्योंकि, और, कि…,
  never inside a phrase, at most 10 words per chunk). The first chunk is
  translated and spoken while the rest are still being prepared, and time to
  first audio runs until that first chunk's audio is ready. **Time to last
  audio** runs until the last chunk's audio is ready; the listener hears it
  after the chunks before it have played.

The app translates utterances of up to 17 words whole, and streams only longer
ones (`config.STREAM_MIN_WORDS`), because chunking changes the wording: the
chunked translation agrees with the whole-sentence one at chrF++ 69 (median).
Against human references it costs little: on the 814 FLORES-200 devtest
sentences of 18+ words, chunked chrF++ 27.3 vs whole 27.5 (BLEU 2.3 vs 3.4);
chunking scores higher on 387 of them (`eval/results/chunk_quality.md`).

**Current reference: three runs** (26 Sep 2026; laptop on AC power, Windows Best performance mode, other apps closed; Hindi silence trimming off). Every run is shown; the bold column is the median of the three runs' p90s (`bench/results/latency_hp_runs.md`). Headline: the **≤ 17-word** row.

**Definitions.** Neither measure includes the endpointing wait: the silence endpoint (500 ms, 1000 ms after 2.5 s of speech) is a setting, off by default; with it on, add at least that wait. Neither includes Wi-Fi or the browser starting playback.
- **From the end of speech** (`bench/latency_steps.py`, Hindi -> Santali): starts when the recorded audio, already a WAV file, is handed to speech recognition in the same process. **Full time** stops when the Santali audio for the whole utterance is written (not streamed). **Time to first audio** stops when the first clause chunk's audio is written (streamed; computed for every clip, although the app streams only utterances of 18+ words). **Time to last audio**: the last chunk's audio. For each clip the benchmark runs the whole path and then the streamed path, and goes straight on to the next clip.
- **Upload to reply audio** (`bench/bench_latency.py`, both directions): starts when the request with the audio file is sent to the app in the same process (Flask test client, no network); includes saving the upload, re-encoding it with ffmpeg, speech recognition, the translation layers (teacher, glossary, cache, model), synthesis and downloading the reply audio; stops when the reply audio is received. Whole utterance, not streamed. One request after another.
- **Why the end-of-speech full time has the longer tail (p90 3.67 vs 2.38 s, medians 2.11 vs 2.03 s in run 3):** the medians agree; the tail comes from speech recognition. In the end-of-speech runs the same six clips were slow every time (1.8-2.4 s), yet alone they take 0.76 s median (0.73 s re-encoded: the format is not the cause). Each follows a clip with about twice the usual streaming work (median 3.5 s vs 1.9 s), which that benchmark runs just before, with no pause. The upload benchmark does not stream. So its full time is the realistic one for a line spoken after a pause; the end-of-speech full time is pessimistic in the tail.
- **Streaming threshold:** on the saved runs, streaming brings the first sound forward by a median 0.25-0.29 s for 12-17 words but delays the last audio by 0.65-0.70 s; for 18+ words it gains 0.48-0.60 s. The app streams only 18+ words (`config.STREAM_MIN_WORDS = 18`); the data support it.
- Rows with fewer than 10 distinct sentences are marked **small sample**. The headline is the **<= 17-word** row.

#### From the end of speech: FLEURS Hindi -> Santali (`bench/latency_steps.py --backend app`)

Time to first audio (clause streaming) and full time (whole utterance voiced), p90 in seconds.

| Words | n | n_distinct | hp1: first / full | hp2: first / full | hp3: first / full | Median of p90s: first / full |
|---|---|---|---|---|---|---|
| all | 80 | 69 | 3.40 / 4.08 | 2.75 / 3.62 | 2.54 / 3.67 | **2.75 / 3.67** |
| ≤ 17 | 37 | 32 | 2.41 / 2.96 | 2.42 / 2.85 | 2.14 / 2.75 | **2.41 / 2.85** |
| 0-11 (small sample) | 3 | 3 | 2.23 / 3.29 | 2.47 / 3.21 | 2.13 / 2.90 | **2.23 / 3.21** |
| 12-17 | 34 | 29 | 2.59 / 2.96 | 2.42 / 2.85 | 2.21 / 2.75 | **2.42 / 2.85** |
| 18-23 | 34 | 28 | 3.74 / 4.93 | 3.25 / 4.19 | 3.40 / 4.76 | **3.40 / 4.76** |
| 24+ (small sample) | 9 | 9 | 3.71 / 4.33 | 3.40 / 4.09 | 3.10 / 3.68 | **3.40 / 4.09** |

Source files: `latency_steps_app_hp1.csv`, `latency_steps_app_hp2.csv`, `latency_steps_app_hp3.csv`

#### Upload to reply audio, both directions (`bench/bench_latency.py`, public clips)

Full time (no streaming in this path), p90 in seconds. Santali clips: IndicVoices validation split (no public Santali test split); may overlap model-development data. Word bins count the reference words of the spoken sentence.

| Direction | Words | n | n_distinct | hp1 | hp2 | hp3 | Median of p90s |
|---|---|---|---|---|---|---|---|
| hi-to-sat | all | 79 | 68 | 2.93 | 2.38 | 2.37 | **2.38** |
| hi-to-sat | ≤ 17 | 40 | 34 | 2.60 | 2.14 | 2.09 | **2.14** |
| hi-to-sat | 0-11 (small sample) | 4 | 4 | 2.22 | 1.87 | 1.87 | **1.87** |
| hi-to-sat | 12-17 | 36 | 30 | 2.60 | 2.14 | 2.09 | **2.14** |
| hi-to-sat | 18-23 | 32 | 27 | 3.17 | 2.47 | 2.37 | **2.47** |
| hi-to-sat | 24+ (small sample) | 7 | 7 | 3.32 | 3.22 | 2.61 | **3.22** |
| sat-to-hi | all | 80 | 80 | 2.60 | 2.52 | 2.58 | **2.58** |
| sat-to-hi | 0-10 | 42 | 42 | 2.27 | 2.23 | 2.29 | **2.27** |
| sat-to-hi | 11-17 | 25 | 25 | 2.62 | 2.55 | 2.69 | **2.62** |
| sat-to-hi | 18+ | 13 | 13 | 2.94 | 2.80 | 2.75 | **2.80** |

Source files: `Dell-Inc-Dell-G15-5520_2026-09-26_public_hp1.csv`, `Dell-Inc-Dell-G15-5520_2026-09-26_public_hp2.csv`, `Dell-Inc-Dell-G15-5520_2026-09-26_public_hp3.csv`

The two earlier runs below (Balanced plan, Hindi trimming on) are kept for the record.

FLEURS Hindi (public dataset, adult speech; n = 80 clips, n_distinct = 69
sentences, the first clip of each counted) and the 30 lesson lines; laptop,
offline; `bench/latency_steps.py`. Run twice with the same settings (run 1:
`latency_steps_app_run1.*`; run 2: `latency_steps_app.*`).

| Measure (distinct sentences) | n / n_distinct | Before Phase L | Now, run 1 | Now, run 2 | Target |
|---|---|---|---|---|---|
| Full time, sentences of ≤ 17 words, p90 | 38 / 32 | 3.46 s | **2.48 s** | **3.02 s** | ≤ 3 s: met in run 1, missed by 20 ms in run 2 |
| Time to first audio, all sentences, median / p90 | 80 / 69 | 1.80 / 2.43 s | 1.80 / **2.46 s** | 1.66 / **2.68 s** | p90 ≤ 3 s: **met** |
| Full time, all sentences, median / p90 | 80 / 69 | 3.16 / 4.13 s | 2.26 / 3.29 s | 2.01 / 3.57 s | — |
| Full time over 3 s | 80 / 69 | 47 of 69 | 12 of 69 | 11 of 69 | — |
| Time to last audio, median / p90 | 80 / 69 | 3.42 / 5.35 s | 3.41 / 4.54 s | 3.15 / 4.52 s | — |
| Lesson lines, full time, p90 | 30 / 30 | 1.63 s | 1.24 s | 1.21 s | — |

By sentence length (words recognised), full time median / p90, and time to
first audio p90:

| Words | n / n_distinct | Before Phase L: full | first p90 | Run 1: full | first p90 | Run 2: full | first p90 |
|---|---|---|---|---|---|---|---|
| 0-11 | 3 / 3 | 2.70 / 2.86 s | 1.80 s | 2.09 / 2.30 s | 1.85 s | 1.69 / 3.02 s | 2.30 s |
| 12-17 | 35 / 29 | 2.99 / 3.74 s | 2.27 s | 1.97 / 2.84 s | 2.25 s | 1.84 / 3.02 s | 2.11 s |
| 18-23 | 33 / 28 | 3.41 / 4.15 s | 2.80 s | 2.35 / 3.39 s | 2.55 s | 2.10 / 4.97 s | 3.21 s |
| 24+ | 9 / 9 | 3.40 / 4.80 s | 2.26 s | 2.87 / 3.29 s | 2.71 s | 2.14 / 4.32 s | 3.48 s |

The slowest clips in run 2 were slow in all three steps at once (speech
recognition 1.7-2.4 s against a 0.7 s median), so the tail is the laptop, not a
step of the pipeline. The ≤ 17-word target is therefore borderline on this
laptop, not reliably met.

What changed (each measured):

| Step | Result | Decision |
|---|---|---|
| Translation on ONNX Runtime fp32 instead of PyTorch | median 504 vs 1455 ms on the FLEURS sentences; identical outputs on 99 of 99 distinct sentences (69 FLEURS + 30 lesson lines) | **Adopted** |
| Threads | More threads were slower: translation best at 6 (of 14 cores), speech recognition at 8 | NMT 6, ASR 8 |
| ONNX Runtime dynamic int8 | 244 ms; IN22-Conv chrF++ 32.0 / 35.0 vs fp32 32.2 / 35.1 (n = 1503; `eval/results/benchmarks_onnx-int8.md`). But only 42 of 99 outputs identical, some long outputs run on (24+ words: full p90 7.04 s), and time to first audio p90 is 3.07 s | Passes the quality rule; **kept for the tablet** (F1). The laptop stays on fp32, which already meets the targets |
| PyTorch dynamic int8 (Linear layers) | 1111 ms, only 15 of 99 identical | Rejected |
| CTranslate2 | Its converters do not support this model (`docs/sources.md#ctranslate2`) | Not possible |
| Endpointing: stop after 500 ms of silence | Cuts 27 of 78 read FLEURS clips early (n = 80 clips, 78 evaluated, n_distinct = 67 sentences; each recording's pauses count); 0 of 30 lesson lines. Adaptive 500/1000 ms: 16 of 78 | A **setting, off by default** (`bench/results/endpoint_sim_*.md`) |
| Word counter | Live count while typing; an estimate (≈) while speaking, from FLEURS' 2.2 words per second; past 15 words a Hindi hint to speak shorter sentences | Built |

Sources: `bench/results/latency_steps_app.md`, `latency_steps_torch-t14.md`,
`latency_steps_onnx-int8-t6.md`, `nmt_engines.md`, `golden_nmt_fp32.md`,
`golden_nmt_int8.md`, `endpoint_sim_public.md`, `endpoint_sim_synthetic.md`.

### Not measured yet

| What | Status |
|---|---|
| Real teacher and child recordings | **NOT MEASURED** (`bench/clips/real/` is empty) |
| ASR error rate on child speech and with classroom noise | **NOT MEASURED** (adult speech, both languages: see above) |
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
pip install -r tools/export/requirements-export.txt
python tools/export/export_indictrans2_onnx.py   # optional: faster translation (ONNX Runtime), same output
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
