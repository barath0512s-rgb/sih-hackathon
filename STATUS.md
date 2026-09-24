# STATUS, 24 Sep 2026: Checkpoint S, then WP14

Checkpoint S was approved. The sections below were updated after it. Changes
since then are summarised in section 0.

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

Notes:
- Commit `42ec510` describes the एक/समझ suggestion-rule change as its own. That change actually went in with `4418c45`; `42ec510` holds the Hindi messages and the deck-picker fix.
- The goal suggestions matched the team's own choice for 7 of 10 lessons, and 9 of 10 after tuning the rules on those same lessons, so this is not an independent accuracy figure. Line labels: the team changed none, but the lessons were written knowing the rules.

Branch `sih-final`, not pushed. Numbers come from `python tools/deck_numbers.py`
(laptop, offline). Anything with no script behind it is marked NOT MEASURED.

## 1. Ministry clauses

| # | Clause | Verdict | Evidence |
|---|---|---|---|
| 1 | Hindi-speaking teachers teach in the mother tongue (Ho, Mundari, Santali) with no language training | **PARTIAL**: Santali only | `test_pipeline.py`, `tests/test_api.py`. IndicTrans2 and IndicConformer do not support Ho or Mundari |
| 2 | Translate Hindi FLN content (lesson scripts, activity instructions, assessment prompts) into accurate text and synthesised audio | **PARTIAL**: text and offline audio for every line. Accuracy is **NOT MEASURED**, and no native review has been done. Content modes do not change the translation (documented in README §5) | `tests/test_api.py`, `tests/test_offline.py`, `docs/native_review.md` |
| 3 | Real-time voice to voice, no more than 3 s | **PARTIAL**: laptop, synthetic clips: median 1.51 s (hi→sat) and 1.57 s (sat→hi), 0 of 59 over 3 s. Real speech, tablet over Wi-Fi and on-device: **NOT MEASURED** | `bench/results/Dell-Inc-Dell-G15-5520_2026-09-24_synthetic-after.csv` |
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
| "Laptop or tablet, via Wi-Fi browser" | TRUE for the screen; tablet microphone NOT MEASURED | HTTPS hub added (`run_vaanisetu.bat https`), not yet tried on a tablet |
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
