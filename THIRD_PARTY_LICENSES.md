# Third-party licences

What this project uses and under which licence. Each entry says where its
licence was read from. This list is not legal advice. Check the source before
redistributing anything.

## Models

| Component | Used for | Licence | Read from |
|---|---|---|---|
| AI4Bharat IndicConformer 600M multilingual | Speech recognition | MIT | `models/indicconformer/README.md` (model card: `license: mit`) |
| AI4Bharat IndicTrans2 indic-indic-dist-320M | Translation | MIT | `models/indictrans2-indic-indic/LICENSE` |
| Piper voice `hi_IN-pratham-medium` | Hindi speech; Santali speech via Devanagari (default) | **CC BY-NC-SA 4.0**. Non-commercial, attribution, share-alike | [MODEL_CARD](https://huggingface.co/rhasspy/piper-voices/blob/main/hi/hi_IN/pratham/medium/MODEL_CARD) |
| Piper voice `en_US-lessac-medium` | Santali via Latin (A/B option, off by default) | Blizzard Challenge 2013 Lessac dataset licence ([licence page](https://www.cstr.ed.ac.uk/projects/blizzard/2013/lessac_blizzard2013/license.html)). We have not reviewed its terms | [MODEL_CARD](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/lessac/medium/MODEL_CARD) |

**Do not describe the voices as MIT.** The default voice (pratham) is
non-commercial. Two other voices are candidates for the Santali A/B test (not in
use yet): `hi_IN-priyamvada-medium` is also CC BY-NC-SA 4.0, and
`hi_IN-rohan-medium` is under the IIT Madras Indic TTS licence. These two are
taken from the team's audit; check their MODEL_CARDs before using either voice.

## Python packages (runtime, `requirements.txt`)

Versions and licences are read from each installed package's metadata.

| Package | Version | Licence |
|---|---|---|
| piper-tts | 1.8.0 | **GPL-3.0-or-later** |
| onnxruntime | 1.29.0 | MIT |
| torch (CPU) | 2.2.0 | BSD-3-Clause |
| transformers | 4.46.1 | Apache-2.0 |
| tokenizers | 0.20.3 | Apache-2.0 |
| huggingface_hub | 0.36.2 | Apache-2.0 |
| safetensors | 0.8.0 | Apache-2.0 |
| sentencepiece | 0.2.2 | Apache-2.0 |
| IndicTransToolkit | 1.1.1 | MIT |
| soundfile | 0.14.0 | BSD-3-Clause |
| numpy | 1.26.4 | BSD-3-Clause |
| Flask | 3.1.3 | BSD-3-Clause |
| flask-cors | 6.0.5 | MIT |
| reportlab | 5.0.1 | BSD |
| cryptography | 50.0.1 | Apache-2.0 OR BSD-3-Clause |

**Note on piper-tts:** the `piper-tts` package is **GPL-3.0-or-later**. It is
**installed separately** by `pip install -r requirements.txt` and is **not
redistributed** in this repository: no Piper code is copied into it. Our own
code is MIT (`LICENSE`). Plan for the finale: move speech synthesis to
sherpa-onnx (Apache-2.0) on both the laptop and Android, which removes the
GPL dependency. This change has not been made yet.

## Development and test tools (`requirements-dev.txt`, `requirements-ci.txt`)

These run tests and evaluations on developer machines and in CI. They are not
part of the application and are never shipped.

The two AGPL tools (aksharamukha and pymupdf) were approved by the team on
25 Sep 2026 for dev and test use only. They are pinned only in
`requirements-dev.txt`; CI installs those two pins from there.
`tests/test_agpl_isolation.py` checks three things: that neither is listed in
`requirements.txt` or `requirements-ci.txt`, that no app source file imports
them, and that loading the app's modules leaves neither in memory.

| Package | Version | Licence |
|---|---|---|
| aksharamukha | 2.3 | **GNU AGPL 3.0** (transliteration cross-check in tests) |
| pymupdf | 1.28.2 | **AGPL 3.0** or commercial (reads PDFs in tests) |
| sacrebleu | 2.5.1 | Apache-2.0 |
| jiwer | 4.0.0 | Apache-2.0 |
| pyarrow | 25.0.1 | Apache-2.0 |
| pandas | 3.0.5 | BSD-3-Clause |
| pytest | 8.4.2 | MIT |
| PyYAML | 6.0.3 | MIT |

## Evaluation data (downloaded by scripts, never committed)

| Dataset | Licence | Used for |
|---|---|---|
| google/fleurs (hi_in test) | CC BY 4.0 | Hindi speech benchmark |
| ai4bharat/IndicVoices (santali valid) | CC BY 4.0 | Santali speech benchmark (gated) |
| ai4bharat/IN22-Gen, IN22-Conv | CC BY 4.0 | translation benchmark (gated) |
| FLORES-200 devtest (facebook/flores) | CC BY-SA 4.0 | translation benchmark (gated) |

Details and exact sources: `docs/sources.md`.

## Fonts (`static/fonts/`, licence files alongside)

| Font | Licence |
|---|---|
| Noto Sans Devanagari | SIL Open Font License 1.1 (`OFL-NotoSansDevanagari.txt`) |
| Noto Sans Ol Chiki | SIL Open Font License 1.1 (`OFL-NotoSansOlChiki.txt`) |
| Baloo 2 | SIL Open Font License 1.1 (`OFL-Baloo2.txt`) |
| Kalam | SIL Open Font License 1.1 (`OFL-Kalam.txt`) |

## Documents cited

- NIPUN Bharat guidelines, Ministry of Education, 2021. The Lakshya text in
  `nipun/lakshya.py` is quoted from p. 11.
