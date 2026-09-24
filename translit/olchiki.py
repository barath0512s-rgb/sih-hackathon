"""Ol Chiki (Santali) -> Devanagari / Latin, for speech synthesis.

No fast offline TTS voice reads Ol Chiki. This module rewrites Santali text in
a script an existing offline voice can pronounce: Devanagari for the Piper
hi_IN voice (default), or Latin for the en_US voice (A/B option).

Design: parse -> phoneme tokens -> render. One parse feeds both scripts, and the
Android port mirrors the same structure. tests/data/olchiki_vectors.json holds
the reference vectors both implementations must pass.

Ol Chiki is a true alphabet: consonants carry no vowel. Devanagari is an
abugida: a bare consonant carries an inherent schwa. So "t" + "e" must become
the consonant with a vowel sign (ते), and a vowelless consonant needs a virama
(त्). A letter-for-letter map gets this wrong, which is why this is a parser.

Rules that depart from a plain orthographic transliteration (Aksharamukha's
"Santali" scheme is the reference in the test vectors). These are phonetic
choices for a Hindi-trained voice, and all need a native speaker's review:

  1. ᱚ is /ɔ/ -> ऑ / ॉ.  ᱟᱹ is /ə/ -> the inherent vowel (अ / no sign).
     Aksharamukha uses the reverse (ᱚ -> inherent, ᱟᱹ -> ॉ), which suits a
     Bengali-style reading where the inherent vowel is /ɔ/. A Hindi voice reads
     the inherent vowel as /ə/, so for speech the mapping is swapped.
  2. Checked stops: ᱜ ᱡ ᱫ ᱵ with no following vowel are unreleased k' c' t' p'
     -> क् च् त् प्. The ahad mark ᱽ keeps them voiced -> ग् ज् द् ब्.
  3. ᱻ (relaa) lengthens the vowel before it: i -> ī, u -> ū.
  4. ᱼ (phaarkaa) is a glottal break: nothing is written, but the next vowel
     starts a new syllable (independent vowel letter).
  5. ᱶ is a nasalised w; written as व (the nasalisation is dropped).
     Aksharamukha writes ङ, which reads as a velar nasal.
  6. Numbers are spoken as Santali number words, taken from
     education_glossary.NUMBERS_HI_SAT, whatever script the digits are in.
     The NMT model sometimes writes ASCII digits inside Santali; a Hindi voice
     would otherwise read those in Hindi.
  7. ᱝ before a vowel is the consonant ङ with a vowel sign (ᱝᱟ -> ङा).
     Aksharamukha always writes an anusvara, giving a detached ंआ.
  8. ᱷ that cannot aspirate the consonant before it is written ह, as Hindi
     writes the cluster in तुम्हारा: ᱢᱷᱟ -> म्हा, and alone ᱷᱟ -> हा.
     Aksharamukha writes a visarga with a detached vowel (म्ःआ, ःआ).

Known limit: a Hindi voice drops the schwa at the end of a word unless the word
ends in a consonant cluster, so a final ᱟᱹ after a single consonant may be lost.
"""

import re
import unicodedata

# ── Letter classes ────────────────────────────────────────────────────────────
VOWEL_LETTERS = {"ᱚ": "o", "ᱟ": "a", "ᱤ": "i", "ᱩ": "u", "ᱮ": "e", "ᱳ": "O"}

CONSONANTS = "ᱛᱜᱝᱞᱠᱡᱢᱣᱥᱦᱧᱨᱪᱫᱬᱭᱯᱰᱱᱲᱴᱵᱶ"
OH = "ᱷ"            # aspiration after a consonant, h elsewhere
CHECKED = "ᱜᱡᱫᱵ"     # unreleased in coda position unless marked with ahad
AHAD = "ᱽ"
GAAHLAA = "ᱹ"         # ᱟᱹ -> schwa
MU_GAAHLAA = "ᱺ"      # schwa + nasal
MU_TTUDDAG = "ᱸ"      # nasal
RELAA = "ᱻ"           # length
PHAARKAA = "ᱼ"        # glottal break
MUCAAD, DOUBLE_MUCAAD = "᱾", "᱿"

OLCK_DIGITS = {chr(0x1C50 + i): i for i in range(10)}
DEVA_DIGITS = {chr(0x0966 + i): i for i in range(10)}
ASCII_DIGITS = {str(i): i for i in range(10)}
ALL_DIGITS = {**OLCK_DIGITS, **DEVA_DIGITS, **ASCII_DIGITS}

# ── Devanagari rendering ──────────────────────────────────────────────────────
CONS_DEVA = {
    "ᱛ": "त", "ᱜ": "ग", "ᱝ": "ङ", "ᱞ": "ल", "ᱠ": "क", "ᱡ": "ज", "ᱢ": "म",
    "ᱣ": "व", "ᱥ": "स", "ᱦ": "ह", "ᱧ": "ञ", "ᱨ": "र", "ᱪ": "च", "ᱫ": "द",
    "ᱬ": "ण", "ᱭ": "य", "ᱯ": "प", "ᱰ": "ड", "ᱱ": "न", "ᱲ": "ड़", "ᱴ": "ट",
    "ᱵ": "ब", "ᱶ": "व",
}
CHECKED_DEVA = {"ᱜ": "क", "ᱡ": "च", "ᱫ": "त", "ᱵ": "प"}
ASPIRATE_DEVA = {"क": "ख", "ग": "घ", "च": "छ", "ज": "झ", "त": "थ", "द": "ध",
                 "प": "फ", "ब": "भ", "ट": "ठ", "ड": "ढ", "ड़": "ढ़"}
# quality -> (independent letter, vowel sign)
VOWEL_DEVA = {"o": ("ऑ", "ॉ"), "a": ("आ", "ा"), "i": ("इ", "ि"), "u": ("उ", "ु"),
              "e": ("ए", "े"), "O": ("ओ", "ो"), "@": ("अ", "")}
LONG_DEVA = {"i": ("ई", "ी"), "u": ("ऊ", "ू")}
VIRAMA, CANDRABINDU, ANUSVARA = "्", "ँ", "ं"

# ── Latin rendering (A/B option for the en_US voice) ─────────────────────────
CONS_LAT = {
    "ᱛ": "t", "ᱜ": "g", "ᱝ": "ng", "ᱞ": "l", "ᱠ": "k", "ᱡ": "j", "ᱢ": "m",
    "ᱣ": "w", "ᱥ": "s", "ᱦ": "h", "ᱧ": "ny", "ᱨ": "r", "ᱪ": "ch", "ᱫ": "d",
    "ᱬ": "n", "ᱭ": "y", "ᱯ": "p", "ᱰ": "d", "ᱱ": "n", "ᱲ": "r", "ᱴ": "t",
    "ᱵ": "b", "ᱶ": "w",
}
CHECKED_LAT = {"ᱜ": "k", "ᱡ": "ch", "ᱫ": "t", "ᱵ": "p"}
VOWEL_LAT = {"o": "o", "a": "a", "i": "i", "u": "u", "e": "e", "O": "o", "@": "a"}
LONG_LAT = {"i": "ee", "u": "oo"}

PUNCT = {MUCAAD: ("।", "."), DOUBLE_MUCAAD: ("॥", "."), "।": ("।", "."), "॥": ("॥", ".")}


# ── Numbers ───────────────────────────────────────────────────────────────────
_HINDI_NUMBER_NAMES = {0: "शून्य", 1: "एक", 2: "दो", 3: "तीन", 4: "चार", 5: "पांच",
                       6: "छह", 7: "सात", 8: "आठ", 9: "नौ", 10: "दस", 100: "सौ"}


def _number_words():
    """Santali number words, read from the glossary so there is one source."""
    from education_glossary import NUMBERS_HI_SAT
    return {n: NUMBERS_HI_SAT[w] for n, w in _HINDI_NUMBER_NAMES.items()}


def number_to_santali(n: int) -> str:
    """0-999 in Santali words (Ol Chiki). Larger numbers are read digit by digit.

    Tens and hundreds compose as in the glossary: 11 = ᱜᱮᱞ ᱢᱤᱫ (ten one),
    20 = ᱵᱟᱨ ᱜᱮᱞ (two ten), 100 = ᱥᱟᱭ.
    """
    w = _number_words()
    if n < 0:
        raise ValueError("negative numbers are not supported")
    if n < 10:
        return w[n]
    if n < 100:
        t, u = divmod(n, 10)
        return " ".join(([w[t]] if t > 1 else []) + [w[10]] + ([w[u]] if u else []))
    if n < 1000:
        h, r = divmod(n, 100)
        return " ".join(([w[h]] if h > 1 else []) + [w[100]] + ([number_to_santali(r)] if r else []))
    return " ".join(w[int(d)] for d in str(n))


# ── Parser ────────────────────────────────────────────────────────────────────
def _parse(text):
    """Split Ol Chiki text into tokens.

    ("C", {c, asp, voiced, v})   consonant, v is a vowel dict or None
    ("V", vowel)                 vowel with no consonant before it
    ("N", digits_str)            a run of digits in any script
    ("P", text)                  punctuation, space, anything else: passed on
    ("B", "ᱼ")                   phaarkaa, a glottal break
    """
    text = unicodedata.normalize("NFC", text)
    toks, i, n = [], 0, len(text)

    def vowel_at(j):
        """Parse a vowel letter and its marks starting at j. Returns (vowel, next_j)."""
        q = VOWEL_LETTERS[text[j]]
        v = {"q": q, "nasal": False, "long": False}
        j += 1
        while j < n and text[j] in (GAAHLAA, MU_GAAHLAA, MU_TTUDDAG, RELAA):
            m = text[j]
            if m in (GAAHLAA, MU_GAAHLAA) and v["q"] == "a":
                v["q"] = "@"
            if m in (MU_GAAHLAA, MU_TTUDDAG):
                v["nasal"] = True
            if m == RELAA:
                v["long"] = True
            j += 1
        return v, j

    while i < n:
        ch = text[i]
        if ch in ALL_DIGITS:
            j = i
            while j < n and text[j] in ALL_DIGITS:
                j += 1
            toks.append(("N", text[i:j]))
            i = j
        elif ch in CONSONANTS:
            c = {"c": ch, "asp": False, "voiced": False, "v": None}
            i += 1
            while i < n and text[i] in (OH, AHAD):
                if text[i] == OH:
                    c["asp"] = True
                else:
                    c["voiced"] = True
                i += 1
            if i < n and text[i] in VOWEL_LETTERS:
                c["v"], i = vowel_at(i)
            elif i < n and text[i] in (MU_TTUDDAG, MU_GAAHLAA, GAAHLAA):
                # A mark straight after a consonant: treat as a schwa.
                c["v"] = {"q": "@", "nasal": text[i] != GAAHLAA, "long": False}
                i += 1
            toks.append(("C", c))
        elif ch in VOWEL_LETTERS:
            v, i = vowel_at(i)
            toks.append(("V", v))
        elif ch == OH:
            # ᱷ with no consonant before it is a plain h.
            toks.append(("C", {"c": "ᱦ", "asp": False, "voiced": False, "v": None, "oh": True}))
            i += 1
            if i < n and text[i] in VOWEL_LETTERS:
                toks[-1][1]["v"], i = vowel_at(i)
        elif ch == PHAARKAA:
            toks.append(("B", ch))   # glottal break
            i += 1
        elif ch in (AHAD, GAAHLAA, MU_GAAHLAA, MU_TTUDDAG, RELAA):
            i += 1          # a mark with nothing to attach to
        else:
            toks.append(("P", ch))
            i += 1
    return toks


def _prev_has_vowel(toks, k):
    return k > 0 and (toks[k - 1][0] == "V" or
                      (toks[k - 1][0] == "C" and toks[k - 1][1]["v"] is not None))


# ── Renderers ─────────────────────────────────────────────────────────────────
def _render_deva(toks, digits, compat=False):
    """compat=True reproduces Aksharamukha's orthographic conventions. It is used
    only by the tests, to check this parser against an independent implementation."""
    vowels = dict(VOWEL_DEVA, o=("अ", ""), **{"@": ("ऑ", "ॉ")}) if compat else VOWEL_DEVA
    out = []
    for k, (kind, x) in enumerate(toks):
        if kind == "B":
            out.append(x if compat else "")
        elif kind == "N":
            out.append(_render_number(x, digits, "deva"))
        elif kind == "P":
            out.append(PUNCT.get(x, (x, x))[0])
        elif kind == "V":
            ind, _ = LONG_DEVA[x["q"]] if x["long"] and x["q"] in LONG_DEVA else vowels[x["q"]]
            out.append(ind + (CANDRABINDU if x["nasal"] else ""))
        else:
            c, v = x["c"], x["v"]
            if v is None and c == "ᱝ" and _prev_has_vowel(toks, k):
                out.append(ANUSVARA)          # ŋ closing a syllable
                continue
            if compat and (x.get("oh") or (x["asp"] and CONS_DEVA[c] not in ASPIRATE_DEVA)):
                ind = ""
                if v:
                    q = v["q"]
                    ind = LONG_DEVA[q][0] if v["long"] and q in LONG_DEVA else vowels[q][0]
                head = "" if x.get("oh") else CONS_DEVA[c] + VIRAMA
                out.append(head + "ः" + ind + (CANDRABINDU if v and v["nasal"] else ""))
                continue
            if compat and c == "ᱝ":
                ind = (LONG_DEVA[v["q"]] if v["long"] and v["q"] in LONG_DEVA else vowels[v["q"]])[0] if v else ""
                out.append(ANUSVARA + ind + (CANDRABINDU if v and v["nasal"] else ""))
                continue
            checked = v is None and c in CHECKED and not x["voiced"] and not compat
            base = CHECKED_DEVA[c] if checked else CONS_DEVA[c]
            if compat and c == "ᱶ":
                base = "ङ"
            if x["asp"]:
                base = ASPIRATE_DEVA.get(base, base + VIRAMA + "ह")
            if v is None:
                out.append(base + VIRAMA + ("’" if compat and x["voiced"] else ""))
            else:
                _, sign = LONG_DEVA[v["q"]] if v["long"] and v["q"] in LONG_DEVA else vowels[v["q"]]
                out.append(base + sign + (CANDRABINDU if v["nasal"] else ""))
    return "".join(out)


def _render_latin(toks, digits):
    out = []
    for kind, x in toks:
        if kind == "B":
            continue
        if kind == "N":
            out.append(_render_number(x, digits, "latin"))
        elif kind == "P":
            out.append(PUNCT.get(x, (x, x))[1])
        elif kind == "V":
            out.append(_lat_vowel(x))
        else:
            c, v = x["c"], x["v"]
            base = CHECKED_LAT[c] if (v is None and c in CHECKED and not x["voiced"]) else CONS_LAT[c]
            if x["asp"]:
                base += "h"
            out.append(base + (_lat_vowel(v) if v else ""))
    return "".join(out)


def _lat_vowel(v):
    s = LONG_LAT[v["q"]] if v["long"] and v["q"] in LONG_LAT else VOWEL_LAT[v["q"]]
    return s + ("n" if v["nasal"] else "")


def _render_number(digit_str, digits, script):
    value = int("".join(str(ALL_DIGITS[d]) for d in digit_str))
    if digits == "digits":
        if script == "deva":
            return "".join(chr(0x0966 + ALL_DIGITS[d]) for d in digit_str)
        return str(value)
    words = number_to_santali(value)
    render = _render_deva if script == "deva" else _render_latin
    return " " + render(_parse(words), "spoken") + " "


def _tidy(s):
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" ([।॥.,?!])", r"\1", s)
    return s.strip()


# ── Public API ────────────────────────────────────────────────────────────────
def to_devanagari(text: str, digits: str = "spoken") -> str:
    """Ol Chiki -> Devanagari for a Hindi voice.

    digits="spoken": numbers become Santali number words (for speech).
    digits="digits": Ol Chiki digits become Devanagari digits (for display).
    """
    if digits not in ("spoken", "digits"):
        raise ValueError("digits must be 'spoken' or 'digits'")
    return _tidy(_render_deva(_parse(text), digits))


def to_latin(text: str, digits: str = "spoken") -> str:
    """Ol Chiki -> Latin for an English voice (A/B comparison path)."""
    if digits not in ("spoken", "digits"):
        raise ValueError("digits must be 'spoken' or 'digits'")
    return _tidy(_render_latin(_parse(text), digits))


def has_olchiki(text: str) -> bool:
    return any(0x1C50 <= ord(c) <= 0x1C7F for c in text)
