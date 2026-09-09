# VaaniSetu (वाणीसेतु) — "Voice Bridge"

**An offline, real-time, bidirectional Hindi ↔ Santali teaching assistant for tribal classrooms.**

| | |
|---|---|
| **Event** | Smart India Hackathon 2026 |
| **Problem Statement** | SIH26042 |
| **Theme** | Smart Education |
| **Category** | Software |
| **Languages** | Hindi (Devanagari) ↔ Santali (Ol Chiki) |
| **Runs on** | A standard laptop, CPU only, no internet required |

---

## 1. The Problem

India has roughly **7.5 million Santali speakers**, concentrated in Jharkhand, West Bengal, Odisha and Bihar. Santali is one of the 22 scheduled languages of India and has its own script, **Ol Chiki (ᱚᱞ ᱪᱤᱠᱤ)**.

The classroom reality:

- Government schools in these districts teach in **Hindi**.
- Grade 1–3 children arrive speaking only **Santali** at home.
- Teachers are frequently posted from outside the region and **do not speak Santali**.
- The child therefore has to learn *mathematics* and *literacy* through a language they do not yet understand.

The result is a **foundational learning gap**. A child who cannot understand "दो और तीन कितने होते हैं?" is not failing at addition — they are failing at Hindi, and the system records it as failing at mathematics.

### Why existing tools do not solve it

| Tool | Why it fails here |
|---|---|
| Google Translate | Does not support Santali at all |
| Generic translation apps | One-way, text-only, no teaching structure |
| Cloud AI services | Rural schools have unreliable or no internet |
| Human translators | Not affordable or available at classroom scale |

---

## 2. The Solution

VaaniSetu is a **teaching assistant**, not a translation box. The teacher speaks or types Hindi; the child hears Santali in their own script and voice. The child can answer back in Santali and the teacher hears Hindi.

Around that core sits the part that makes it a *lesson* rather than a phrasebook:

1. **Bidirectional classroom dialogue** — not one-way translation.
2. **Three FLN content modes** — teaching script, activity instruction, assessment prompt.
3. **Pre-loaded NIPUN Bharat lesson templates** — structured teaching, not a blank text box.
4. **Per-response comprehension signal** — green / yellow / red after each student answer.
5. **Teacher session summary** — analytics when the lesson finishes.
6. **Bilingual PDF worksheet** — generated from the actual lesson that was just taught.
7. **Instant learning** — a teacher can correct a translation and the correction is used forever after.
8. **Fully offline** — every model runs locally on the laptop.

> **NIPUN Bharat** (National Initiative for Proficiency in Reading with Understanding and Numeracy) is the Government of India's mission for foundational literacy and numeracy by Grade 3. VaaniSetu's lessons are written against its competency goals.

---

## 3. System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  BROWSER  (frontend.html — single file, no build step)       │
│  Classroom · Lessons · Flashcards · Progress · Settings      │
└───────────────────────────┬──────────────────────────────────┘
                            │  HTTP / JSON  (same origin, or LAN)
┌───────────────────────────▼──────────────────────────────────┐
│  FLASK API  (app.py) — 16 endpoints                          │
└───────────────────────────┬──────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────┐
│  PIPELINE  (pipeline.py)                                     │
│                                                              │
│   Microphone (.webm)                                         │
│        │  ffmpeg → 16 kHz mono float32                       │
│        ▼                                                     │
│   ① ASR    IndicConformer 600M (ONNX, RNN-T)                 │
│        │   native Hindi + Santali, 22 Indian languages        │
│        ▼                                                     │
│   ② NMT    IndicTrans2 indic-indic-dist-320M                 │
│        │   DIRECT hi↔sat — no English pivot                   │
│        ▼                                                     │
│   ③ TTS    Piper (offline neural)                            │
│            sat → Ol Chiki transliterated to Latin → en_US    │
│            hi → Devanagari read directly by hi_IN            │
└───────────────────────────┬──────────────────────────────────┘
                            │
      ┌─────────────────────┼─────────────────────┐
      ▼                     ▼                     ▼
  SQLite               NIPUN Lessons         ReportLab
  feedback DB          lesson_engine.py      worksheet.py
  (instant learning)   (5 lessons)           (bilingual PDF)
```

### Three short-circuits before any model runs

Requests are answered from the cheapest layer that can answer them:

1. **Human correction (SQLite)** — if a teacher has corrected this exact Hindi line, return their wording. 100% accurate, instant.
2. **Translation cache (memory)** — `TRANSLATION_CACHE`, keyed `mode::text`. If this line was translated before, reuse it. ~0.02 s.
3. **TTS cache (disk, MD5)** — `tts_cache/<md5(voice:text)>.wav`. If this audio was synthesised before, copy the file. ~0.01 s.

Only on a miss do the neural models run.

---

## 4. The AI Pipeline in Detail

### ① Speech Recognition — AI4Bharat IndicConformer 600M

| | |
|---|---|
| **Model** | `ai4bharat/indic-conformer-600m-multilingual` |
| **Runtime** | ONNX Runtime, CPU |
| **Decoding** | RNN-T (transducer) |
| **Languages** | 22 — `as bn brx doi kok gu hi kn ks mai ml mr mni ne or pa sa sat sd ta te ur` |

**Why not Whisper?** Whisper had roughly a 2-in-10 success rate on Hindi in a noisy classroom and has no Santali support at all. IndicConformer supports both **natively**, including Santali (`sat`) in Ol Chiki.

**Why RNN-T over CTC?** RNN-T uses a joint prediction network, so it decodes using linguistic context rather than frame-by-frame guesses. Markedly more robust to classroom noise and accented speech.

Whisper remains as an automatic fallback if the IndicConformer files are missing.

### ② Translation — AI4Bharat IndicTrans2 (Direct Indic→Indic)

| | |
|---|---|
| **Model** | `ai4bharat/indictrans2-indic-indic-dist-320M` |
| **Direction** | Hindi ↔ Santali, **direct** |
| **Decoding** | Greedy (`num_beams=1`) |

**Why no English pivot?** The original design was Hindi → English → Santali using two 200M models. That doubled latency and, worse, **destroyed meaning**: English has no grammatical gender or respect markers, so `आप` (respectful "you") and `तुम` (familiar "you") both collapse to "you" and cannot be recovered on the way out. A direct Indic→Indic model preserves gender, respect level and numeric context.

**Why greedy decoding?** Beam search is several times slower on CPU for a marginal quality gain on short classroom sentences. Greedy keeps translation at roughly 0.35–0.65 s.

**Generation settings** (`pipeline.py`):

| Parameter | Value | Reason |
|---|---|---|
| `NMT_BEAMS` | 1 | Greedy — fast CPU inference |
| `NMT_MAX_TOKENS` | 128 | Classroom lines are short |
| `NMT_NO_REPEAT_NGRAM` | 3 | Blocks the degenerate looping this model can fall into |
| `NMT_LENGTH_PENALTY` | 1.0 | Neutral |

**Domain glossary post-processing.** The model sometimes leaks its own mode label into the output — emitting `ᱥᱮᱪᱮᱫ:` ("Teaching:") or `ᱠᱩᱠᱞᱤ:` ("Question:") as a prefix. `_apply_domain_glossary()` strips these so the child hears the sentence, not the instruction label.

**Background pre-caching.** On startup a daemon thread translates all **18 NIPUN lesson sentences** and stores them in memory, so every scripted line in a demo answers from cache instead of running the model.

### ③ Speech Synthesis — Piper (offline neural TTS)

| Voice | Model | Reads |
|---|---|---|
| Santali | `en_US-lessac-medium` | Latin transliteration of Ol Chiki |
| Hindi | `hi_IN-pratham-medium` | Devanagari directly |

**The Ol Chiki problem.** No fast TTS engine speaks Santali. VaaniSetu maps each Ol Chiki letter to its Latin phonetic equivalent in Python (`transliterate_santali()`, a 34-entry table covering U+1C5A–U+1C77 plus space and basic punctuation), then has an English-reading voice pronounce it. `ᱛᱮᱦᱮᱧ ᱟᱢ ᱥᱮᱞᱮᱫ` becomes `teheny am seled` — phonetically close enough for a child to recognise their own language.

**Why Piper, and the road to it:**

| Attempt | Outcome |
|---|---|
| Indic Parler-TTS | ~30 s per sentence on CPU. Unusable. |
| INT8 quantised Parler | PyTorch CPU dispatch regressions. Abandoned. |
| gTTS (Google) | Fast (~0.8 s) but **requires internet** — fatal for rural schools. |
| **Piper** | **~0.15 s, fully offline, neural quality.** ✅ |

Piper is the current engine. gTTS remains a fallback if a voice file is missing, and a short silence is written if both fail, so the audio endpoint never returns an error.

---

## 5. Engineering Evolution

The project was rebuilt in six phases. Each solved a measured problem.

| Phase | Problem | Solution | Result |
|---|---|---|---|
| **1** | Whisper: 2/10 on Hindi, no Santali | IndicConformer 600M ONNX + RNN-T | Reliable native Hindi & Santali ASR |
| **2** | Two-hop translation, lost gender/respect | Direct `indic-indic-320M`, greedy | ~0.4 s, meaning preserved |
| **3** | Parler-TTS 30 s on CPU | Ol Chiki→Latin transliteration + fast TTS | Speech in under a second |
| **4** | Model repeats the same mistake | SQLite feedback loop + `train_nmt.py` LoRA | Corrections apply instantly |
| **5** | Repeated phrases re-synthesised | MD5 TTS cache + NIPUN pre-cache | Cache hits ~0.01–0.02 s |
| **6** | gTTS needs internet | **Piper offline neural TTS** | **Zero network at runtime** |

---

## 6. Measured Performance

Measured on this project, CPU only, no GPU:

| Stage | Cold | Cached |
|---|---|---|
| Translation (NMT) | 0.35 – 0.65 s | ~0.02 s |
| Speech (Piper TTS) | ~0.15 s | ~0.01 s |
| **Typed round trip** | **~0.5 s** | **~0.02 s** |
| Server boot (all models) | ~30 s | — |
| Piper voice load | ~2 s each, at startup | — |

TTS improved from **~0.80 s (gTTS) to ~0.15 s (Piper)** — roughly 5× faster *and* offline.

*Note: the microphone (ASR) path has not been benchmarked with a stopwatch in this build; the figures above are the text path. The design target for full speech-to-speech is under 4 s.*

---

## 7. Feature Reference

### Classroom
- Hindi ⇄ Santali, typed or spoken
- Three FLN modes: **Lesson Script**, **Activity**, **Assessment**
- Lesson step navigation with "what to say" and "coming next" cues
- Live latency breakdown (ASR / NMT / TTS / total) and confidence
- Playback of synthesised speech

### Lessons — NIPUN Bharat aligned
| Grade | Lesson | Competency |
|---|---|---|
| 1 | Counting 1 to 10 | Counts objects up to 10, says numbers in order |
| 1 | Basic Shapes | Identifies circle, square, triangle |
| 2 | Simple Addition | Adds two single-digit numbers using objects |
| 2 | Reading Simple Words | Reads common two-syllable words aloud |
| 3 | Simple Subtraction | Subtracts single-digit numbers using objects |

Each lesson is a sequence of typed steps (`lesson_script`, `activity_instruction`, `assessment_prompt`), each carrying a `hindi` line, a teacher `note`, and — for assessment steps — an `accept_answers` list. Answers are accepted in digits, Hindi words or romanised form, e.g. `["7", "सात", "saat"]`.

### Comprehension signals
After a student answers, the response is graded:

| Signal | Meaning |
|---|---|
| 🟢 **Green** | Answer matches an accepted answer — student understood |
| 🟡 **Yellow** | Something was said, but not the expected answer — partial |
| 🔴 **Red** | No response — concept needs repeating |

### Session summary
Duration, steps completed, sentences translated, average latency, green/yellow/red counts, a percentage score, and a plain-language verdict:
- ≥70% → "Good — students grasped the concept"
- ≥40% → "Partial — repeat key terms next session"
- <40% → "Needs reinforcement — revisit this lesson"

### Bilingual worksheet (PDF)
Generated from the **actual session just taught**: the NIPUN competency goal, the key Hindi/Santali concept pair, and a full lesson-progression table of every line translated. Rendered with real Unicode fonts (Noto Sans Devanagari + Noto Sans Ol Chiki) so both scripts print correctly.

### Instant learning (feedback loop)
👍 / 👎 on any translation. A 👎 opens a correction box. Corrections are stored in SQLite and **checked before the model on every future request** — so a teacher's fix is applied immediately and permanently, with no retraining. The accumulated corrections also export to CSV for LoRA fine-tuning (`train_nmt.py`).

### The interface itself is in Hindi and Santali — not English

This is a design decision, not a detail. The user is a teacher in a tribal school, so **there is no English in the UI at all**. Every visible string exists twice, in a single translation table:

| UI language | Nav labels |
|---|---|
| **हिन्दी** (default) | कक्षा · पाठ · चित्र पत्ते · प्रगति · सेटिंग |
| **ᱥᱟᱱᱛᱟᱲᱤ** (Ol Chiki) | full Santali translation of the entire interface |

> **Honest caveat, from the source file itself:** *"The Santali column was written without a native speaker to check it, so treat it as a first draft."* Correcting it requires editing one table and nothing else in the file.

### Five views
| View | Hindi | Purpose |
|---|---|---|
| Classroom | कक्षा | The live teaching screen |
| Lessons | पाठ | Browse and pick a lesson |
| Flashcards | चित्र पत्ते | Vocabulary deck with flip-all |
| Progress | प्रगति | Cumulative lines, steps, accuracy, time |
| Settings | सेटिंग | Preferences |

### Settings (persisted in `localStorage`)
| Setting | Key | Effect |
|---|---|---|
| UI language | `vs_lang` | Hindi or Santali |
| Autoplay | `vs_autoplay` | Speak the translation automatically |
| Large type | `vs_big` | Scales the whole UI for classroom projection |
| Spoken confirmations | `vs_confirm` | Announce actions aloud |
| **Server address** | `vs_server` | **Point the UI at a laptop over Wi-Fi** |

That last one is what makes the tablet/phone story work today: the HTML can be opened on any device on the same network and pointed at the teacher's laptop, with no app install.

### Accessibility
- Skip-to-content link (`मुख्य भाग पर जाएँ`)
- Keyboard operable: **Ctrl/Cmd + Enter** translates, **Enter** submits a student answer, **Escape** closes dialogs, lesson steps are Enter/Space activatable
- Large-type mode for projection

---

## 8. API Reference

All 16 endpoints served by `app.py`.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Serves `frontend.html` |
| GET | `/health` | Liveness + CPU/GPU device |
| GET | `/health/models` | What actually loaded: ASR backend, NMT status, cache sizes, active sessions |
| GET | `/lessons` | All lessons, each with its full step plan inlined |
| POST | `/session/start` | Begin a lesson session → `session_id` |
| POST | `/session/next` | Advance one step |
| POST | `/session/goto` | Jump to a specific step index |
| POST | `/session/response` | Grade a student answer → green/yellow/red |
| POST | `/session/summary` | Session analytics |
| POST | `/translate/text` | Translate typed text (either direction) |
| POST | `/translate/audio` | Translate a recorded clip (multipart) |
| POST | `/translate/reverse` | Santali → Hindi convenience route |
| GET | `/audio/output` | Latest **Santali** audio |
| GET | `/audio/hindi` | Latest **Hindi** audio |
| POST | `/worksheet` | Generate and download the bilingual PDF |
| POST | `/feedback` | Store a 👍/👎 or a correction |

**Example — translate typed Hindi:**
```bash
curl -X POST http://127.0.0.1:5000/translate/text \
  -H "Content-Type: application/json" \
  -d '{"text":"आज हम जोड़ना सीखेंगे।","direction":"hi-to-sat","mode":"lesson_script"}'
```
```json
{
  "translated_text": "ᱛᱮᱦᱮᱧ ᱟᱢ ᱥᱮᱞᱮᱫ ᱥᱮᱪ ᱢᱮ ᱾",
  "confidence": 95.0,
  "audio_url": "/audio/output",
  "latency": { "asr": 0.0, "nmt": 0.35, "tts": 0.15, "total": 0.5 }
}
```

---

## 9. Project Structure

| File | Role |
|---|---|
| `app.py` | Flask server, 16 REST endpoints, session registry |
| `pipeline.py` | **Core ML** — ASR, NMT, transliteration, Piper TTS, caches |
| `indicconformer_asr.py` | ONNX wrapper for IndicConformer, 22 languages |
| `lesson_engine.py` | NIPUN lesson templates, `LessonSession`, grading, summary |
| `worksheet.py` | Bilingual PDF generator (ReportLab + Unicode fonts) |
| `database.py` | SQLite feedback store, correction lookup, CSV export |
| `frontend.html` | Entire UI — single file, no build step |
| `verify_models.py` | End-to-end pre-flight check → `verify_report.txt` |
| `test_pipeline.py` | 7 component tests |
| `train_nmt.py` | LoRA fine-tuning on collected corrections (GPU) |
| `generate_dataset.py` | Builds the 33-pair NIPUN parallel corpus |
| `run_vaanisetu.bat` | Double-click launcher (`run_vaanisetu.bat verify` to self-check) |
| `training_data/` | `nipun_hindi_santali.csv` — 33 curated Hindi↔Santali pairs |
| `models/` | All model weights (git-ignored) |
| `tts_cache/` | MD5-keyed synthesised audio |

### Documentation
| File | Contents |
|---|---|
| `README.md` | This file |
| `WORKFLOW.md` | The phase-by-phase architectural decision log |
| `VaaniSetu_WINNER_Build_Guide.md` | 1,636-line original build guide (historical; predates the current architecture) |

### Setup, legacy and scratch files
These exist in the folder but are **not part of the running application**:

| File | Status |
|---|---|
| `download_models.py` | ⚠️ **Stale** — still downloads Whisper, the two pivot models and Parler-TTS, none of which the current pipeline uses |
| `optimize_models.py` | Legacy warm-up for the retired pivot models |
| `run_setup.ps1` | ⚠️ One-shot setup script — **contains a committed HuggingFace token** |
| `extract.py` | One-shot: pulled the original source files out of the build guide |
| `patch.py` | ⚠️ **Destructive** one-shot rewriter — previously stubbed TTS to silence. Do not run |
| `generate_dataset.py` | Regenerates the 33-pair training CSV |
| `frontend_v2…v6.html`, `frontend_old_backup.html` | Design iterations kept for reference |
| `app.py.bak`, `pipeline.py.bak`, `worksheet.py.bak` | Manual backups |

### What git ignores
`models/` · `tts_cache/` · `vaanisetu_env/` · `*.wav *.mp3 *.webm` · `*.onnx *.pt *.bin *.safetensors` · `vaanisetu_feedback.db` · `__pycache__/`

Consequence: a fresh clone has **no models, no voices and no audio cache**. Section 10's download steps are mandatory, not optional.

### Dependencies
`requirements.txt` pins **161 packages**. The ones that matter: `torch` (CPU build), `transformers==4.46.1`, `onnxruntime`, `IndicTransToolkit`, `piper-tts==1.8.0`, `Flask`, `flask-cors`, `reportlab`, `gTTS` (fallback only), `soundfile`.

### Data model
```sql
CREATE TABLE feedback (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    hindi_text     TEXT,
    santali_text   TEXT,
    is_correct     BOOLEAN,
    corrected_text TEXT,
    timestamp      REAL
);
```

### Disk footprint
| Component | Size |
|---|---|
| IndicConformer (ASR) | 2.4 GB |
| IndicTrans2 indic-indic (NMT) | 2.5 GB |
| Piper voices | 121 MB |
| Fonts | 232 KB |
| *(legacy, unused)* whisper / indic_en / en_indic / parler tts | ~5.7 GB |

---

## 10. Setup

**Requirements:** Python 3.10 or 3.11, `ffmpeg` on PATH, ~8 GB RAM, ~6 GB disk.

```bash
# 1. Environment
python -m venv vaanisetu_env
vaanisetu_env\Scripts\activate        # Windows
source vaanisetu_env/bin/activate     # Mac/Linux

# 2. Dependencies
pip install -r requirements.txt

# 3. Offline voices (~121 MB, not in git)
python -m piper.download_voices en_US-lessac-medium  --data-dir models/piper
python -m piper.download_voices hi_IN-pratham-medium --data-dir models/piper

# 4. Verify everything loads and speaks
python verify_models.py

# 5. Run
python app.py
```

Then open **http://127.0.0.1:5000**. The server also binds `0.0.0.0`, so any device on the same Wi-Fi can reach it at `http://<laptop-ip>:5000`.

On Windows you can simply double-click **`run_vaanisetu.bat`** (or `run_vaanisetu.bat verify` to self-check first).

---

## 11. Testing & Verification

Two scripts, with different jobs.

### `verify_models.py` — the pre-flight check (run this before a demo)
Loads the **real** models and exercises the whole system, writing `verify_report.txt`:

| Group | Checks |
|---|---|
| **[1] Dependencies** | Every import, plus `ffmpeg` on PATH |
| **[2] Model files** | ASR / NMT / font directories exist, with file counts and sizes |
| **[3] Pipeline load** | `VaaniSetuPipeline()` constructs; warns if ASR silently fell back to Whisper |
| **[4] Translation** | Both directions, all three lesson modes, and that the cache actually hits |
| **[5] Speech** | Transliteration, synthesis, **and that the audio is audible rather than silent** |
| **[6] Lessons, grading, storage** | Lesson engine, green/yellow/red, correction DB overrides the model, PDF renders |
| **[7] Speech in, speech out** | Full `full_forward()` on a sample WAV if one is present |

The audio-silence check exists for a specific reason: a stubbed-out TTS once shipped undetected because the file size looked plausible. This test measures RMS and fails on silence.

### `test_pipeline.py` — 7 component tests
1. Hindi → Santali translation
2. Santali → Hindi (bidirectional)
3. Santali TTS audio output
4. All 3 FLN content modes
5. Lesson engine loads correctly
6. Comprehension signals green/red
7. Bilingual worksheet PDF

---

## 12. Offline Guarantee

Every **AI stage** runs locally:

| Stage | Runtime | Network? |
|---|---|---|
| ASR | ONNX Runtime, local weights | ❌ None |
| NMT | PyTorch, local weights | ❌ None |
| TTS | Piper, local ONNX voices | ❌ None |
| Lessons / grading / worksheet | Pure Python | ❌ None |
| **UI fonts** | **Google Fonts CDN** | ⚠️ **Yes — see below** |

**Verified:** with Python's socket layer forcibly disabled, gTTS raises `gTTSError` while Piper synthesises both voices successfully. The served audio is 22 050 Hz RIFF/WAV — gTTS emits MP3 — confirming Piper produced it.

### ⚠️ One remaining network dependency: the fonts

`frontend.html` loads **Baloo 2** and **Noto Sans Ol Chiki** from `fonts.googleapis.com`. The models are offline; the *typeface* is not. On a school laptop with no internet this matters more than it sounds — as the file's own comment warns, without Noto Sans Ol Chiki **every Santali letter renders as an empty box**, which breaks the core feature.

**The fix is small and the asset is already in the repo:** `models/fonts/NotoSansOlChiki-Regular.ttf` and `NotoSansDevanagari-Regular.ttf` are already vendored for the PDF generator. Serving those from Flask and swapping the `<link>` for a local `@font-face` makes the whole application genuinely offline. **This should be done before any offline demo.**

This matters because the target deployment is a school with no reliable connectivity.

---

## 13. Honest Status & Known Limitations

Things a reviewer should know rather than discover:

| # | Item | Impact |
|---|---|---|
| 1 | **Live HuggingFace token committed in `run_setup.ps1`**, present in git history | ⚠️ **Security — revoke it.** Deleting the line is not enough |
| 2 | **UI fonts load from Google Fonts** (§12) | ⚠️ **Breaks the offline claim.** With no internet, every Santali letter renders as a box. Fix before any offline demo |
| 3 | `/audio/hindi` exists on the backend but the current UI never calls it; autoplay is gated to Hindi→Santali | Reverse direction is **silent in the UI** even though the backend speaks it |
| 4 | Direction must be switched with the swap button; typing Santali does not auto-switch | UX friction |
| 5 | Ol Chiki transliteration drops the danda `᱾` and diacritics such as `ᱹ` | Slight pronunciation loss |
| 6 | Confidence is hard-coded to 95% (greedy decoding returns no sequence scores) | Displayed number is not a real measure |
| 7 | Sessions live in an in-memory dict | **Restarting the server loses every active lesson**; no multi-worker deployment |
| 8 | Single shared `output_*.wav` per direction | Concurrent users could collide |
| 9 | Santali is voiced by a US-English voice | Loses Indian phonetic colour; mapping Ol Chiki→Devanagari and using the Hindi voice would likely sound better |
| 10 | The Santali UI strings were written without a native speaker | Author's own caveat — treat as a first draft |
| 11 | ASR falls back to Whisper silently if IndicConformer files are missing | Santali speech input degrades badly with no visible warning; `verify_models.py` catches it |
| 12 | `download_models.py` still fetches the abandoned Whisper/pivot/Parler models | A fresh clone downloads ~5 GB it will not use |
| 13 | `patch.py` is one-shot scaffolding that rewrites `pipeline.py` | **Do not run it** — it previously stubbed TTS to silence |
| 14 | Training corpus is 33 curated pairs | Enough to demonstrate LoRA, not to move general quality |
| 15 | Flask dev server, `debug=False`, bound to `0.0.0.0` | Fine for a demo; not a production deployment |

---

## 14. Roadmap

- **Phase 2 — On-device:** full ONNX INT8 export so the pipeline runs on a mid-range Android phone with no laptop.
- **More languages:** the ASR already covers 22 Indian languages; the NMT is Indic→Indic. Mundari, Ho and Bhili are natural next targets.
- **Grow the corpus:** collected teacher corrections feed LoRA fine-tuning via `train_nmt.py`.
- **Teacher dashboard:** aggregate comprehension analytics across sessions and classes.
- **Offline Hindi voice quality:** evaluate additional `hi_IN` Piper voices.

---

## 15. Slide Deck Outline (for PPT generation)

A 17-slide deck. Each row names the section to pull content from.

**Do not put §13 (Known Limitations) in the deck** — it is for your own tracking. But read it before you present, so nothing surprises you in Q&A.

| # | Slide Title | Content | Source |
|---|---|---|---|
| 1 | **VaaniSetu — वाणीसेतु** | Title, "Voice Bridge", SIH 2026 · PS SIH26042 · Smart Education. Tagline: *Offline, real-time Hindi ↔ Santali teaching assistant* | §Header |
| 2 | **The Problem** | 7.5M Santali speakers · teachers speak Hindi · children speak Santali · foundational learning gap. One line: *the child isn't failing at maths, they're failing at Hindi* | §1 |
| 3 | **Why Nothing Existing Works** | 4-row table: Google Translate / generic apps / cloud AI / human translators | §1 |
| 4 | **Our Solution** | 8 bullets: bidirectional · 3 FLN modes · NIPUN lessons · comprehension signals · summary · worksheet · instant learning · offline | §2 |
| 5 | **System Architecture** | The ASCII block diagram, redrawn as boxes: Browser → Flask → Pipeline (ASR/NMT/TTS) → SQLite / Lessons / PDF | §3 |
| 6 | **Three Short-Circuits** | Correction DB → memory cache → TTS cache → models. Emphasise: *models only run on a miss* | §3 |
| 7 | **① Speech Recognition** | IndicConformer 600M, ONNX, RNN-T, 22 languages. *Why not Whisper:* 2/10 on Hindi, no Santali | §4① |
| 8 | **② Translation** | IndicTrans2 320M direct Indic→Indic. *Why no English pivot:* आप vs तुम collapse to "you" | §4② |
| 9 | **③ Speech Synthesis** | Ol Chiki has no TTS → transliterate to Latin. Table of 4 attempts ending at Piper | §4③ |
| 10 | **Engineering Evolution** | The 6-phase table — problem → solution → result | §5 |
| 11 | **Performance** | Latency table. Headline: *TTS 0.80s → 0.15s, and now offline* | §6 |
| 12 | **NIPUN Bharat Alignment** | 5-lesson table with competencies + the green/yellow/red signal | §7 |
| 13 | **Instant Learning** | 👍/👎 → correction stored → checked *before* the model on every later request. *Right forever after, no retraining* | §7 |
| 14 | **Built for the Actual User** | The UI itself is in Hindi and Santali — no English anywhere. Five views, large-type mode, works on a tablet over Wi-Fi | §7 |
| 15 | **Offline Guarantee** | Runtime table + the socket-disabled verification result | §12 |
| 16 | **Demo** | Live: speak Hindi → hear Santali → child answers → green signal → download worksheet | §7 |
| 17 | **Roadmap** | On-device ONNX INT8 · more tribal languages · corpus growth · teacher dashboard | §14 |

### Talking points that land with judges

- *"We removed the English pivot because English cannot carry Indian grammatical respect. आप and तुम both become 'you' and you can never get it back."*
- *"We replaced a 30-second TTS with a 0.15-second one that needs no internet — because the schools we are building for do not have internet."*
- *"When a teacher corrects us, we are right forever after. No retraining, no waiting."*
- *"This is not a translation app. It is a lesson that happens to cross a language barrier."*
- *"There is no English anywhere in our interface. The teacher we built this for does not need it."*

---

## 16. Current Repository State

| | |
|---|---|
| **Branch** | `fix/pipeline-import-tests-session-logging` |
| **Latest commit** | `35f3de8` — Implement frontend_v3.html logic into frontend.html |
| **Uncommitted** | 21 paths (9 modified, 12 untracked) |

### Commit history
| Commit | What it did |
|---|---|
| `35f3de8` | Implemented the frontend_v3 logic into `frontend.html`, fixed a print-encoding error |
| `637545e` | Integrated the frontend with a working sidebar and dynamic backend fetching |
| `8692ac9` | Editorial redesign of the frontend, connected to the ML backend |
| `212b45c` | Removed the dead Parler import, fixed the broken test suite, wired up lesson-translation logging |
| `08752ab` | Initial: optimised pipeline, IndicConformer ASR, direct NMT, gTTS transliteration |

**The Piper offline-TTS work, the Hindi TTS route and this README are not yet committed.** Commit before the demo so the working state is recoverable.

---

## 17. Credits

Built on open models from **AI4Bharat** (IIT Madras) — IndicConformer and IndicTrans2 — and **Piper** (Rhasspy) for offline neural speech. Fonts: Noto Sans Devanagari and Noto Sans Ol Chiki. Lesson competencies follow the **NIPUN Bharat** framework, Ministry of Education, Government of India.
