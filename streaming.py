"""Split a long Hindi utterance into chunks that can be translated and spoken
one after another (Phase L2, clause streaming).

The first chunk is translated and spoken while the rest are still being
translated, so the listener hears the start sooner. Chunks must stay
meaningful, so the rules are conservative:

1. Split at sentence ends: । ? ! and a full stop.
2. A sentence of at most SHORT words is never split further. Classroom lines
   are short, and "तीन और चार कितने होते हैं?" must not become "तीन" + "और चार …".
3. A longer sentence is split before a clause word (लेकिन, क्योंकि, फिर, और,
   तो, कि) or after a comma, and only where both sides keep at least MIN_PART
   words.
4. A part still longer than MAX_WORDS is cut every ~MAX_WORDS words at a word
   boundary, as a last resort.
"""

import re

SHORT = 10          # sentences up to this many words stay whole
MIN_PART = 4        # never leave a clause shorter than this
MAX_WORDS = 10      # hard cap per chunk (rule 4)
CLAUSE_WORDS = ("लेकिन", "क्योंकि", "फिर", "और", "तो", "कि", "परंतु", "किंतु", "इसलिए")
RELATIVE_STARTS = ("जो", "जिस", "जिन", "जहाँ", "जहां", "जब", "जैसे")
# A chunk never starts with one of these: they belong to the words before them
# ("होता | है" or "घर | में" would break a phrase in two).
NEVER_START = {"है", "हैं", "था", "थे", "थी", "थीं", "हो", "होता", "होती", "होते", "हुआ", "हुई", "हुए",
               "का", "की", "के", "को", "से", "में", "पर", "ने", "तक", "भी", "ही", "रहा", "रहे", "रही",
               "गया", "गई", "गए", "जाता", "जाती", "जाते", "जा", "सकता", "सकती", "सकते", "दिया", "लिया",
               "वाला", "वाली", "वाले", "लिए", "द्वारा", "साथ", "बाद", "पहले"}

_SENT = re.compile(r"[^।?!.]+[।?!.]*")


def sentences(text):
    return [s.strip() for s in _SENT.findall(text or "") if s.strip()]


def _bare(w):
    return w.strip(",;:\"'()")


def _can_start(words, i):
    return _bare(words[i]) not in NEVER_START


def _split_long(words):
    """Rule 3: the clause boundary nearest the middle, recursively; rule 4 if none."""
    if len(words) <= MAX_WORDS:
        return [words]
    cands = []
    for i in range(MIN_PART, len(words) - MIN_PART + 1):
        w_prev, w = words[i - 1], _bare(words[i])
        if (w in CLAUSE_WORDS or w.startswith(RELATIVE_STARTS) or w_prev.endswith((",", ";", ":"))) \
                and _can_start(words, i):
            cands.append(i)
    mid = len(words) / 2
    if not cands:
        # Rule 4: cut near the middle, at the nearest word a chunk may start with.
        cands = [i for i in range(MIN_PART, len(words) - MIN_PART + 1) if _can_start(words, i)]
    if not cands:
        return [words]
    i = min(cands, key=lambda k: abs(k - mid))
    return _split_long(words[:i]) + _split_long(words[i:])


def chunks(text):
    """The utterance as a list of chunks (strings), in order."""
    out = []
    for s in sentences(text):
        words = s.split()
        if len(words) <= SHORT:
            out.append(s)
        else:
            out.extend(" ".join(p) for p in _split_long(words))
    return out
