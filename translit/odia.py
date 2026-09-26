"""Devanagari -> Odia script, for the MMS-TTS voices that read Odia script.

facebook/mms-tts-unr (Mundari) and facebook/mms-tts-hoc (Ho) are character models
whose vocabularies are Odia-script letters (is_uroman: false; docs/sources.md#mms-tts).
Our Mundari and Ho lines are written in Devanagari, and Santali in Ol Chiki, so
the text is converted before synthesis:

    Ol Chiki --translit.olchiki.to_devanagari--> Devanagari --deva_to_odia--> Odia

The two Unicode blocks are laid out in parallel (Odia = Devanagari + 0x200) for the
letters, vowel signs, virama, anusvara, visarga, candrabindu and digits. Exceptions:
ॉ / ऑ (how translit.olchiki writes ᱚ, /ɔ/) become the inherent vowel / ଅ, since
Odia's inherent vowel is /ɔ/; व (U+0935) becomes ୱ (U+0B71, the letter both MMS vocabularies contain); the danda
and double danda are shared and kept; the nukta forms (क़ …) lose the nukta; a
character with no Odia counterpart is kept as is, and the voice's tokenizer drops it
(mms_tts.oov() reports those). Pronunciation is pending native review.
"""

import unicodedata

_SPECIAL = {"व": "ୱ", "।": "।", "॥": "॥",
            "ॉ": "",          # ॉ (candra o, how olchiki.py writes ᱚ /ɔ/): Odia's inherent vowel is /ɔ/
            "ऑ": "ଅ",    # ऑ -> ଅ
            "ॅ": "େ"}    # ॅ -> େ
_NUKTA = {"क़": "क", "ख़": "ख", "ग़": "ग", "ज़": "ज",
          "ड़": "ड", "ढ़": "ढ", "फ़": "फ", "य़": "य"}


def _odia_exists(cp):
    try:
        unicodedata.name(chr(cp))
        return True
    except ValueError:
        return False


def deva_to_odia(text: str) -> str:
    out = []
    for ch in unicodedata.normalize("NFD", text):
        ch = _NUKTA.get(ch, ch)
        if ch == "़":                                   # nukta: dropped
            continue
        if ch in _SPECIAL:
            out.append(_SPECIAL[ch])
            continue
        cp = ord(ch)
        if 0x0900 <= cp <= 0x097F and _odia_exists(cp + 0x200):
            out.append(chr(cp + 0x200))
        else:
            out.append(ch)
    return unicodedata.normalize("NFC", "".join(out))


def olchiki_to_odia(text: str) -> str:
    from translit.olchiki import to_devanagari
    return deva_to_odia(to_devanagari(text, digits="spoken"))
