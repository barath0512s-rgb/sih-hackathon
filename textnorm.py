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
_SENTENCE_MARKS = "।॥᱾᱿"
_TRAILING = "।॥᱾᱿.!?,;:'\"‘’“”-–— "
_INVISIBLE = "​‌‍﻿"          # zero-width space/non-joiner/joiner, BOM


def normalize_key(text: str) -> str:
    """Matching key for a sentence or an answer.

    - Unicode NFC (so precomposed and decomposed letters compare equal)
    - nukta removed (ज़ = ज) and chandrabindu folded into anusvara (पाँच = पांच):
      both are routinely typed either way
    - zero-width characters removed
    - Devanagari and Ol Chiki digits become ASCII digits
    - danda / Ol Chiki sentence marks become "." ; trailing punctuation dropped
    - whitespace collapsed, spaces before punctuation removed, Latin lower-cased
    """
    if not text:
        return ""
    s = unicodedata.normalize("NFC", text)
    s = s.replace("़", "")                   # nukta (NFC decomposes क़ -> क + ़)
    s = s.replace("ँ", "ं")             # chandrabindu -> anusvara
    for ch in _INVISIBLE:
        s = s.replace(ch, "")
    s = "".join(_DIGITS.get(c, c) for c in s)
    for m in _SENTENCE_MARKS:
        s = s.replace(m, ".")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r" ([.!?,;:])", r"\1", s)
    s = s.strip(_TRAILING)
    return s.lower()


def digits_of(text: str) -> str:
    """The ASCII digit string in a short answer ("᱗" -> "7"), or "" if none."""
    s = normalize_key(text)
    return s if s.isdigit() else ""
