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

**Note on piper-tts:** the Python package is GPL-3.0-or-later. Our code
imports it, so the application as distributed must meet GPL terms. Choose the
project's own licence with this in mind. There is no `LICENSE` file for our
own code yet; the team has to decide that.

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
