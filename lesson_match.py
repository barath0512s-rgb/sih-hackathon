"""Curriculum matching for the tablet's on-device voice path (A1).

The tablet has speech recognition but (until M4) no translation model. A spoken
lesson line is recognised, then matched against the content pack's pre-translated
lines; the pack's translation and audio are used only when the match is close
enough. Below the threshold the page shows the transcript and "not a lesson line"
and never invents a translation.

Similarity: cosine similarity of character trigram counts of textnorm.normalize_key
(text), padded with one space at each end, so word boundaries count. 1.0 = the same
trigrams in the same proportions. Numbers are compared as words: a digit run is
written out (Hindi words for Hindi, translit.olchiki.number_to_santali for Santali)
before the trigrams are taken, because a line written "4" and a line written "चार"
are the same utterance and speech recognition writes either. A match also needs the
same numbers in the same order as the line: in a maths lesson "दो" for "पांच" is a
different sentence, however similar the rest. The Kotlin port (android .../core/LessonMatch.kt)
is tested against tests/data/lesson_match_vectors.json, written from this file.

The threshold (config.LESSON_MATCH_THRESHOLD) is tuned by bench/lesson_match_tune.py
on synthetic lesson clips and scored on a held-out half: bench/results/lesson_match.md.
"""

import math
import re
from collections import Counter

from textnorm import normalize_key

# 0-99 in Hindi (standard spellings; normalize_key folds nukta and chandrabindu).
HINDI_0_99 = ("शून्य एक दो तीन चार पांच छह सात आठ नौ दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस "
              "बीस इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस तीस इकतीस बत्तीस तैंतीस चौंतीस "
              "पैंतीस छत्तीस सैंतीस अड़तीस उनतालीस चालीस इकतालीस बयालीस तैंतालीस चवालीस पैंतालीस छियालीस सैंतालीस "
              "अड़तालीस उनचास पचास इक्यावन बावन तिरेपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ साठ इकसठ बासठ "
              "तिरेसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर सत्तर इकहत्तर बहत्तर तिहत्तर चौहत्तर पचहत्तर "
              "छिहत्तर सतहत्तर अठहत्तर उन्यासी अस्सी इक्यासी बयासी तिरासी चौरासी पचासी छियासी सत्तासी अट्ठासी "
              "नवासी नब्बे इक्यानवे बानवे तिरानवे चौरानवे पचानवे छियानवे सत्तानवे अट्ठानवे निन्यानवे").split()
assert len(HINDI_0_99) == 100
_HI_NUMBER_WORDS = {normalize_key(w) for w in HINDI_0_99} | {"सौ", "हजार"}


def hindi_number(n: int) -> str:
    """0-9999 in Hindi words; larger numbers digit by digit."""
    if n < 100:
        return HINDI_0_99[n]
    if n >= 10000:
        return " ".join(HINDI_0_99[int(d)] for d in str(n))
    th, r = divmod(n, 1000)
    hu, r = divmod(r, 100)
    parts = ([HINDI_0_99[th], "हजार"] if th else []) + ([HINDI_0_99[hu], "सौ"] if hu else [])
    return " ".join(parts + ([HINDI_0_99[r]] if r else []))


def number_words(n: int, lang: str) -> str:
    if lang == "hi":
        return hindi_number(n)
    from translit.olchiki import number_to_santali
    return number_to_santali(n)


def canonical(text: str, lang: str) -> str:
    """normalize_key with every digit run written out in words."""
    k = normalize_key(text)
    return normalize_key(re.sub(r"[0-9]+", lambda m: f" {number_words(int(m.group()), lang)} ", k))


_SAT_NUMBER_WORDS = None


def number_tokens(text: str, lang: str) -> list:
    """The number words in canonical(text), in order (digits already written as words)."""
    global _SAT_NUMBER_WORDS
    if lang == "hi":
        words = _HI_NUMBER_WORDS
    else:
        if _SAT_NUMBER_WORDS is None:
            from translit.olchiki import _number_words
            _SAT_NUMBER_WORDS = {normalize_key(w) for w in _number_words().values()}
        words = _SAT_NUMBER_WORDS
    return [w for w in canonical(text, lang).split() if w in words]


def trigrams(text: str, lang: str = "hi") -> Counter:
    s = f" {canonical(text, lang)} "
    return Counter(s[i:i + 3] for i in range(len(s) - 2)) if len(s) >= 3 else Counter()


def similarity(a: str, b: str, lang: str = "hi") -> float:
    ta, tb = trigrams(a, lang), trigrams(b, lang)
    if not ta or not tb:
        return 0.0
    dot = sum(v * tb.get(k, 0) for k, v in ta.items())
    return dot / math.sqrt(sum(v * v for v in ta.values()) * sum(v * v for v in tb.values()))


def best(text: str, candidates, lang: str = "hi"):
    """(candidate, score) of the closest candidate, or (None, 0.0). Ties: the first in order."""
    top, score = None, 0.0
    t = trigrams(text, lang)
    if not t:
        return None, 0.0
    nt = math.sqrt(sum(v * v for v in t.values()))
    for c in candidates:
        tc = trigrams(c, lang)
        if not tc:
            continue
        s = sum(v * tc.get(k, 0) for k, v in t.items()) / (nt * math.sqrt(sum(v * v for v in tc.values())))
        if s > score:
            top, score = c, s
    return top, score


def match(text: str, candidates, threshold: float, lang: str = "hi"):
    """{"line", "score", "matched", "numbers_agree"}: matched only when score >= threshold
    and the utterance has exactly the line's numbers (so "दो आम" never matches "पांच आम")."""
    line, score = best(text, candidates, lang)
    agree = line is not None and number_tokens(text, lang) == number_tokens(line, lang)
    return {"line": line, "score": round(score, 6), "numbers_agree": agree,
            "matched": line is not None and score >= threshold and agree}
