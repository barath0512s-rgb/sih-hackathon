"""Normalised keys for matching text that people type or speak.

A teacher's correction must be reused for the same sentence even if it is typed
slightly differently next time, and a child's answer must be graded the same
whether they say "7", "७" or "᱗". The key is for matching only; the original
text is always what gets stored and shown.
"""

import re
import unicodedata

_DIGITS = {**{chr(0x0966 + i): str(i) for i in range(10)},      # Devanagari
           **{chr(0x1C50 + i): str(i) for i in range(10)}}      # Ol Chiki
_INVISIBLE = "​‌‍﻿"          # zero-width space/non-joiner/joiner, BOM

# Bump when normalize_key changes, so stored keys are recomputed (database.py).
KEY_VERSION = 2


def normalize_key(text: str) -> str:
    """Matching key for a sentence or an answer.

    - Unicode NFC (so precomposed and decomposed letters compare equal)
    - nukta removed (ज़ = ज) and chandrabindu folded into anusvara (पाँच = पांच):
      both are routinely typed either way
    - zero-width characters removed
    - Devanagari and Ol Chiki digits become ASCII digits
    - all punctuation removed (dandas, Ol Chiki sentence marks, ?, commas...):
      speech recognition writes none, so a spoken line must match a typed one
    - whitespace collapsed, Latin lower-cased
    """
    if not text:
        return ""
    s = unicodedata.normalize("NFC", text)
    s = s.replace("़", "")                   # nukta (NFC decomposes क़ -> क + ़)
    s = s.replace("ँ", "ं")             # chandrabindu -> anusvara
    for ch in _INVISIBLE:
        s = s.replace(ch, "")
    s = "".join(_DIGITS.get(c, c) for c in s)
    s = "".join(" " if unicodedata.category(c).startswith("P") else c for c in s)
    return re.sub(r"\s+", " ", s).strip().lower()


def digits_of(text: str) -> str:
    """The ASCII digit string in a short answer ("᱗" -> "7"), or "" if none."""
    s = normalize_key(text)
    return s if s.isdigit() else ""


# Annotation tags in IndicVoices transcripts ("<unintelligible>"): no recogniser writes them.
_TAG = re.compile(r"<[^<>\s]*>")


def strip_reference_tags(text: str):
    """(reference without dataset annotation tags, number of tags removed).
    For REFERENCES only: a tag in a hypothesis stays and counts as an error."""
    if not text:
        return "", 0
    found = _TAG.findall(text)
    return _TAG.sub(" ", text), len(found)


def normalize_for_wer(text: str) -> str:
    """Text for the *normalised* WER/CER in bench/ (rules in bench/README.md).

    Only formatting is removed, the same way for Hindi and Santali: Unicode NFC;
    every punctuation mark (Unicode category P: , . ? । ॥ ᱾ ᱿ - ...) replaced by
    a space; Devanagari and Ol Chiki digits written as ASCII digits; whitespace
    collapsed. Spelling is left alone (no nukta or chandrabindu folding, unlike
    normalize_key). Dataset tags are removed from references before this, by
    strip_reference_tags, never from hypotheses.
    """
    if not text:
        return ""
    s = unicodedata.normalize("NFC", text)
    s = "".join(_DIGITS.get(c, c) for c in s)
    s = "".join(" " if unicodedata.category(c).startswith("P") else c for c in s)
    return re.sub(r"\s+", " ", s).strip()
