# Sources

Every external fact used in the code, the docs or the deck, with where it comes
from. Quotes are exact. "Accessed" is the date we last read the source. When an
entry here disagrees with an older claim anywhere else, this file wins, and the
disagreement is noted.

Anchors (`#name`) are what `docs/claims.yaml` points to.

---

## Problem statement

### <a name="brief"></a>SIH26042 brief
- **Source:** the official problem-statement text as given to the team (quoted in
  the team's master prompt). The sih.gov.in page itself was not re-fetched for
  this file: **not verified by fetch**.
- Facts used: Ho, Mundari and Santhali; lesson scripts, activity instructions,
  assessment prompts; voice-to-voice "≤ 3 s"; worksheets and flashcards aligned
  to NIPUN Bharat learning outcomes; offline on "2 GB RAM, Android 9+" tablets
  after initial content synchronisation; demo video and GitHub repository.
- The symbol before "2 GB" is garbled in the official text; we write "2 GB RAM,
  Android 9+" with no ≤ or ≥.

## Education policy and statistics

### <a name="nipun"></a>NIPUN Bharat guidelines (Lakshyas)
- **URL:** https://static.pib.gov.in/WriteReadData/specificdocs/documents/2021/jul/doc20217531.pdf
- **Accessed:** 2026-09-24. Ministry of Education, 2021.
- **Page 11, "Lakshyas: Learning Goals of the Mission"**, quoted in full in
  `nipun/lakshya.py` (15 goals). Examples: Grade 2 "45-60 words per minute";
  Grade 3 "at least 60 words per minute"; Grade 3 "Read and write numbers up to
  9999"; Balvatika "Recognizes and reads numerals up to 10."
- Read by eye as well as extracted, because an earlier automatic extraction was
  suspected of swapping the Grade 2 and 3 values. It had not.

### <a name="jepc"></a>JEPC Language Mapping Survey, Phase 1 (Jharkhand)
- **URL:** https://languageandlearningfoundation.org/wp-content/uploads/2025/04/LM-Report-Jharkhand-Phase-1.pdf
- **Accessed:** 2026-09-24. Carried out by JEPC with JCERT support. Data "collected
  on the portal in January and February 2024" (p. 15). Page numbers are the
  report's printed ones (PDF page = printed + 3).
- p. 13: "Number of participating schools: 8,244"; "Number of students represented: 1, 06, 930"; 7 districts, 72 blocks.
- p. 5 (executive summary): "…covering 8,244 schools and representing 1,06,930 students."
- p. 18: "In the surveyed districts, Hindi serves as the Medium of Instruction (MoI) in approximately 98% of schools."
- p. 17, Table 1: "Ho 17.03%", "Santali 13.07%", "Mundari 7.32%" (of Grade 1 students' home languages).
- p. 6: "Approximately 80% of schools in the surveyed districts of Jharkhand, falling under Type II, III, and IV categories, pose moderate to severe learning disadvantages for students"
- p. 6: "The survey found that 36.1% of students have minimal proficiency, 41.2% have functional proficiency, and only 22.7% have good proficiency in Hindi."
- p. 18: "…accounting for around 51.2% of students, indicating that a sizeable portion of the student population possesses a very less or no understanding of Hindi."
- The report gives both 36.1% and 51.2%; we quote both.

### <a name="google-translate-santali"></a>Santali in Google Translate
- **Google Translate (the consumer product) added Santali in June 2024. TRUE.**
- Google India blog, 27 June 2024,
  https://blog.google/intl/en-in/google-translate-new-languages-2024/ (accessed
  2026-09-25): "The list includes 7 new Indian languages - Awadhi, Bodo, Khasi,
  Kokborok, Marwadi, Santali, and Tulu."
- Google Translate Help, "What's new in Google Translate: More than 100 new
  languages", https://support.google.com/translate/answer/15139004 (accessed
  2026-09-25): "Santali" is in the list of new languages (between "Sango" and
  "Seychellois Creole").
- **Script: not specified** by either page.
- The **Cloud Translation API** is a different product. Its language list,
  https://docs.cloud.google.com/translate/docs/languages ("Last updated
  2026-09-18 UTC", accessed 2026-09-25), does **not** list Santali.
- Correction history: on 25 Sep we first marked this claim NOT VERIFIED,
  because we had checked only the global blog post (which does not name
  Santali) and the Cloud API list. The India blog and the Help page, found by
  the team, confirm it.

## Models

### <a name="indicconformer-600m"></a>AI4Bharat IndicConformer 600M multilingual (speech recognition, in use)
- **Repo:** `ai4bharat/indic-conformer-600m-multilingual` @ `e9b71b369c048e2c6b634d4c131061c34e441179` (`config.ASR_REVISION`).
- **Licence:** MIT. Model card: "IndicConformer is released under the MIT license."
- **Languages:** "all 22 official Indian languages", including Santali (`sat`), per the card; the loaded model reports 22 language codes.
- **Size on disk:** printed by `tools/deck_numbers.py` (`bench/results/deck_numbers.txt`).
- **Decoding:** hybrid CTC + RNN-T ("Multilingual Conformer-based Hybrid CTC + RNNT ASR model", model card).

### <a name="indictrans2-model"></a>AI4Bharat IndicTrans2 indic-indic-dist-320M (translation, in use)
- **Repo:** `ai4bharat/indictrans2-indic-indic-dist-320M` @ `ffb7582b6d43791f1fb26b2153fc065f2e9ea575`.
- **Licence:** MIT (`models/indictrans2-indic-indic/LICENSE`: "MIT License / Copyright (c) AI4Bharat.").
- Supports `hin_Deva` and `sat_Olck` (model card language list).

### <a name="indictrans2-paper"></a>IndicTrans2 paper: published Santali scores
- Gala et al., "IndicTrans2: Towards High-Quality and Accessible Machine Translation Models for all 22 Scheduled Indian Languages", TMLR 12/2023. arXiv 2305.16307v3 (CC BY 4.0). Accessed 2026-09-25.
- The paper gives no hin→sat or sat→hin score for a single direction. It reports
  chrF++ **averaged** "to that language and from that language" over the common
  Indic languages. For the distilled M2M model (IT2-Dist-M2M), row `sat_Olck`:
  - Table 19, FLORES-200: xx-sat **26.1**, sat-xx **31.5**
  - Table 20, IN22-Gen: xx-sat **30.0**, sat-xx **35.8**
  - Table 21, IN22-Conv: xx-sat **30.4**, sat-xx **33.8**
- We compare our hin↔sat scores with these as a plausibility range only.

### <a name="indicconformer-120m"></a>AI4Bharat IndicConformer 120M, Hindi and Santali (for Android, not yet used)
- `ai4bharat/indicconformer_stt_hi_hybrid_ctc_rnnt_large` @ `deada84ce8…`; `ai4bharat/indicconformer_stt_sat_hybrid_ctc_rnnt_large` @ `507c307549…`.
- **Licence:** MIT (Hub card data). **Gated.** One `.nemo` file each, 523,192,320 bytes. Accessed 2026-09-24.
- **Structure, read from the `.nemo` files (2026-09-25):** each "per-language" model is multilingual inside: 22 language tokenizers (256 BPE pieces each), `multisoftmax: true`, a 5632-token vocabulary plus blank, and `language_keys` for the joint network; NeMo masks the output to the requested `language_id`. SHA-256: hi `7cad1308…`, sat `98435e5a…` (`bench/results/export_120m_check.md`).
- Card read 2026-09-25 (access granted): "a conformer-Large model, consisting of 120M parameters, as the encoder, with a hybrid CTC-RNNT decoder"; 17 conformer blocks, model dimension 512. Needs the AI4Bharat NeMo fork (`nemo-v2`). **The card does not say which data it was trained or validated on.**

### <a name="sherpa-hotwords"></a>sherpa-onnx hotwords (contextual biasing)
- https://k2-fsa.github.io/sherpa/onnx/hotwords/index.html, accessed 2026-09-25. Licence of sherpa-onnx: Apache-2.0.
- Quote: "Only transducer models support hotwords in sherpa-onnx." Also: "You have to change the decoding method to `modified_beam_search` to use hotwords." Hotwords file: one phrase per line, optional per-phrase score (`phrase :3.5`); needs `bpe.vocab` (modeling unit `bpe`) for sentencepiece models.
- **CTC models: not supported.** So "expected-answer biasing" needs the RNN-T (transducer) branch of IndicConformer exported to sherpa-onnx, not only the CTC branch.
- NeMo transducers: modified beam search and hotwords for NeMo transducer models were added by PR #3077, merged 5 Feb 2026 (https://github.com/k2-fsa/sherpa-onnx/pull/3077). The hotwords page's own examples use only Zipformer/Conformer (icefall) models.
- Open risk: issue #3267 (open, accessed 2026-09-25) reports that `modified_beam_search` with a NeMo **TDT** model returns empty or hallucinated text about 20% of the time, even with no hotwords (https://github.com/k2-fsa/sherpa-onnx/issues/3267). IndicConformer is RNN-T, not TDT; whether it is affected: **NOT MEASURED**.

### <a name="ctranslate2"></a>CTranslate2 and IndicTrans2 (Phase L1a)
- CTranslate2 Transformers converter guide,
  https://opennmt.net/CTranslate2/guides/transformers.html (accessed
  2026-09-25). The supported families it lists include BART, M2M100, MarianMT,
  MBART, NLLB and T5; IndicTrans2's custom architecture
  (`IndicTransForConditionalGeneration`, loaded with `trust_remote_code`) is not
  among them.
- IndicTrans2 README, https://github.com/AI4Bharat/IndicTrans2 (accessed
  2026-09-25): CT2 checkpoints are provided for the fairseq En-Indic and Indic-En
  models ("The pretrained checkpoints have 3 directories, a fairseq model
  directory and 2 CT-ported model directories"). The Indic-Indic models,
  including indic-indic-dist-320M, are listed as HF only, so there is no fairseq
  checkpoint to convert either.
- **Conclusion: CTranslate2 does not support this model.** Not measured.

### <a name="in22-bpcc"></a>IN22 through the BPCC repository
- The IndicTrans2 README links an IN22 download:
  https://huggingface.co/datasets/ai4bharat/BPCC/resolve/main/additional/IN22_testset.zip
  (licence in the README's table: IN22-Gen and IN22-Conv, "CC-BY-4.0").
- `ai4bharat/BPCC` is gated too (403 on 2026-09-25), so it is not a way round
  the IN22 gate.

### <a name="piper-pratham"></a>Piper voice hi_IN-pratham-medium (in use)
- MODEL_CARD: https://huggingface.co/rhasspy/piper-voices/blob/main/hi/hi_IN/pratham/medium/MODEL_CARD, accessed 2026-09-24.
- Licence given as "http://creativecommons.org/licenses/by-nc-sa/4.0/" (**CC BY-NC-SA 4.0**). Dataset: AI4Bharat indicnlp_corpus.

### <a name="piper-lessac"></a>Piper voice en_US-lessac-medium (A/B option, off)
- MODEL_CARD: https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/lessac/medium/MODEL_CARD, accessed 2026-09-24.
- Data: Blizzard 2013 Lessac dataset; licence page https://www.cstr.ed.ac.uk/projects/blizzard/2013/lessac_blizzard2013/license.html (terms not reviewed by us).

## Datasets (evaluation only; never trained or tuned on)

### <a name="fleurs"></a>google/fleurs (Hindi speech benchmark)
- https://huggingface.co/datasets/google/fleurs @ `70bb2e84b976b7e960aa89f1c648e09c59f894dd`. **Licence: CC BY 4.0** (Hub card data). Not gated.
- Used: `hi_in` test split (418 utterances); 80 of the 187 that last 3-10 s,
  picked with seed 26042 (`bench/fetch_public_clips.py`,
  `bench/clips/public/manifest.json`). Adult read speech. FLEURS has several
  speakers per sentence: the 80 clips hold 69 distinct sentences.

### <a name="indicvoices"></a>ai4bharat/IndicVoices (Santali speech benchmark)
- https://huggingface.co/datasets/ai4bharat/IndicVoices @ `c96f9088f1…`. **Licence: CC BY 4.0** (Hub card data). **Gated.**
- Santali: 45 train shards and one `valid` shard (217,769,865 bytes). **There is no test split** (repo file list, 2026-09-25; the card lists only `valid` and `train` for every language). We use `valid` only: 80 clips, 62 speakers.
- Access granted 2026-09-25. **Label used wherever a Santali ASR number appears:** "IndicVoices validation split (no public Santali test split); may overlap model-development data".
- **How the validation split was used, checked 2026-09-25:**
  - IndicVoices paper (Javed et al., arXiv 2403.01926, https://arxiv.org/html/2403.01926), Section 7, on the paper's own model: "we train a multilingual 130M conformer based model (IndicASR) following the same architecture as proposed by [38], using only the IndicVoices train set." Table 6 caption: "Number of speakers (#sp) and hours (#h) in the train, validation and test and splits across languages." The paper does not say how the validation split was used (early stopping, checkpoint selection or neither), and it describes a test split that the Hub dataset does not contain for Santali.
  - The IndicConformer model cards we use (600M multilingual; 120M `..._hi_...` and `..._sat_...`) name no training data, cite no paper and say nothing about a validation split (read 2026-09-24/25).
  - Nothing links the paper's 130M IndicASR to either checkpoint we use. **So: unknown.** The validation clips may overlap the data used to develop the models (training or checkpoint selection); our Santali WER may be optimistic.
- **Not used for ASR evaluation:** `ai4bharat/indicvoices_r` (its Santali `test` split is derived from the same IndicVoices recordings; decision 2026-09-25).
- Card fields used: `text` (transcript), `speaker_id`, `gender`, `age_group`, `task_name`, `scenario`. Two of the 80 transcripts contain the tag `<unintelligible>`: removed from the references only before normalised WER (2 tokens; `bench/README.md`).

### <a name="indicvoices-r"></a>ai4bharat/indicvoices_r
- @ `5f4495c91d…`, **CC BY 4.0**, gated; has a Santali **test** split (2 shards, 537 MB) and 108 train shards. Access granted 2026-09-25; not used yet. It is a speech-synthesis corpus built from IndicVoices recordings (enhanced audio), so its test clips may be IndicVoices utterances. **Not used for ASR evaluation** (derived from the same recordings).

### <a name="in22"></a>ai4bharat/IN22-Gen and IN22-Conv (translation benchmark)
- IN22-Gen @ `e042ab3d30…`, 1024 sentences; IN22-Conv @ `18cd45870f…`, 1503 sentences. **CC BY 4.0** (card: `license: cc-by-4.0`), n-way parallel, includes `hin_Deva` and `sat_Olck`. Gated; access granted 2026-09-25; used by `eval/eval_benchmarks.py`.

### <a name="flores"></a>FLORES-200 devtest (translation benchmark)
- `facebook/flores` @ `71abf77d8b…` has `sat_Olck` and `hin_Deva` devtest; the maintained successor `openlanguagedata/flores_plus` also has both.
- **Licence: CC BY-SA 4.0** (Hub card data for both). Gated; access granted 2026-09-25.
- The master prompt gave no licence for FLORES. The official card says CC BY-SA 4.0.

## Software licences (from each installed package's metadata)

### <a name="packages"></a>Runtime and dev packages
- Runtime: see `THIRD_PARTY_LICENSES.md`. `piper-tts` 1.8.0 is **GPL-3.0-or-later**.
- **Dev and test only, never shipped:**
  - `aksharamukha` 2.3 (GNU AGPL 3.0): transliteration cross-check in tests;
  - `pymupdf` 1.28.2 (AGPL 3.0 or commercial): reads PDFs in tests;
  - `sacrebleu` 2.5.1 (Apache-2.0);
  - `jiwer` 4.0.0 (Apache-2.0);
  - `pyarrow` 25.0.1 (Apache-2.0);
  - `pandas` 3.0.5 (BSD-3-Clause);
  - `pytest` 8.4.2 (MIT);
  - `PyYAML` 6.0.3 (MIT).

### <a name="fonts"></a>Fonts
- Noto Sans Devanagari, Noto Sans Ol Chiki, Baloo 2, Kalam: SIL Open Font License 1.1 (licence files in `static/fonts/`, e.g. "This Font Software is licensed under the SIL Open Font License, Version 1.1.").

## Uplift sources (added 2026-09-26)

### <a name="indic-parler-tts"></a>ai4bharat/indic-parler-tts (B1 pre-render)
- https://huggingface.co/ai4bharat/indic-parler-tts, accessed 2026-09-26.
- Licence: "This model is permissively licensed under the Apache 2.0 license."
- Languages: "Assamese, Bengali, Bodo, Dogri, English, Gujarati, Hindi, Kannada, Konkani, Maithili, Malayalam, Manipuri, Marathi, Nepali, Odia, Sanskrit, Santali, Sindhi, Tamil, Telugu, and Urdu."
- **Santali has no recommended-speaker table entry, is absent from the card's training-data table and from its evaluation (MOS) table.** So Santali quality is unknown until A6 measures it. Description used (the card's example without the accent): see `tools/parler_prerender.py`; fixed seed 1234.

### <a name="mms-tts"></a>facebook/mms-tts-unr (Mundari) and facebook/mms-tts-hoc (Ho)
- https://huggingface.co/facebook/mms-tts-unr, https://huggingface.co/facebook/mms-tts-hoc, accessed 2026-09-26. Card licence `cc-by-nc-4.0` (both; approved by the team for non-commercial use). VITS, 16 kHz, 1 speaker.
- `tokenizer_config.json` of both: `"is_uroman": false`, `"phonemize": false`, `"add_blank": true`, `"normalize": true`. The vocabularies (`vocab.json`, 54 and 55 entries) are **Odia-script** letters.
- **So the voices read Odia script, not Devanagari or Warang Citi.** Teacher lines in Devanagari are converted by `translit/odia.py` before synthesis. (The uplift prompt assumed Devanagari or Warang Citi input; the model files win.)
- There is **no `facebook/mms-tts-sat`** (the Hub API returns no such model), so C4 starts from `mms-tts-unr`.

### <a name="mmloso"></a>MMLoSo 2025 shared task (Hindi–Mundari data)
- Findings paper, ACL Anthology 2025.mmloso-1.14, https://aclanthology.org/2025.mmloso-1.14.pdf, accessed 2026-09-26.
- Licence: "All data is distributed under the Creative Commons BY-SA 4.0 license." (Confirms the team's approval note.)
- Script: "Hindi, Bhili, and Mundari are written in Devanagari"; Mundari "Although traditionally written in multiple scripts, we use Devanagari".
- Size: "each with 20,000 high-quality parallel sentence pairs"; test statistics table: Mundari 2000 source sentences.
- **Test references are not public:** "The test set contains only the source sentence and language direction; participants must generate the target translation." So our scores use a held-out 5 % of the training file.
- Hosted on Kaggle: https://kaggle.com/competitions/mm-lo-so-2025 (cited in system paper 2025.mmloso-1.11). Downloading needs a Kaggle account that accepts the competition rules.
- System paper 2025.mmloso-1.12 used "a stratified 95/5 train-validation split prior to augmentation"; our split is the same size.

### <a name="finetune-hf-vits"></a>ylacombe/finetune-hf-vits (C4 training code)
- https://github.com/ylacombe/finetune-hf-vits @ `6f3f51f4d667f5c3eef89484d151ffd39d2c2b89`, MIT License (LICENSE file, accessed 2026-09-26). Fine-tuning MMS needs the discriminator converted from the original MMS checkpoint (`convert_original_discriminator_checkpoint.py --language_code <iso>`).

### <a name="indicvoices-r-santali"></a>IndicVoices-R, Santali config (C4 data)
- Hub API card data (accessed 2026-09-26): config `Santali`, train 32,613 examples, test 660; download size 38.8 GB; fields include `speaker_id`, `gender`, `snr`, `duration`, `text`, `audio` (48 kHz). CC BY 4.0, gated (access already granted 2026-09-25).

### <a name="sherpa-onnx-tts"></a>sherpa-onnx 1.13.8 (Apache-2.0)
- Same version as the WSL export environment (`tools/export/requirements-nemo-wsl.txt`). VITS models are read with metadata keys `sample_rate`, `add_blank`, `n_speakers`, `language`, `comment` ("piper" for Piper voices), `frontend` ("characters" for character models); source `sherpa-onnx/csrc/offline-tts-vits-model.cc` @ `040afe360a`.

### <a name="openmoji"></a>OpenMoji (A2 pictures)
- https://github.com/hfg-gmuend/openmoji @ `aeb8bb3a59…`, accessed 2026-09-26. README: "OpenMoji graphics are licensed under the Creative Commons Share Alike License 4.0 ([CC BY-SA 4.0]…)"; attribution suggestion: "All emojis designed by OpenMoji – the open-source emoji and icon project. License: CC BY-SA 4.0". Approved by the team. 29 PNGs in `static/openmoji/` (`ATTRIBUTION.md`).
