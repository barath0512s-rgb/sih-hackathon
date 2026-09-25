"""Guards for the int8 translation engine (the tablet's): a tighter length cap and
a repetition guard. Pure Python, so the Android port (F1 M4) can mirror it exactly.

Why: dynamic int8 sometimes falls into loops of *variants* of one word stem
(ᱥᱟᱯᱷᱟᱨᱤ ᱥᱟᱯᱷᱟᱹᱨᱤ ᱥᱟᱯᱷᱚᱨᱤ …), which the no-repeat-3-gram rule cannot stop because the
tokens differ. A real repetition in the source ("ᱜᱮᱞ ᱜᱮᱞ ᱜᱮᱞ") repeats the SAME word,
so the guard only fires when the repeated stem comes with different endings.

Measured on the saved test-set outputs (IN22-Gen, IN22-Conv, FLORES, both directions):
- fp32: output/input token ratio median 0.9, p99.9 2.12; the stem guard fires on 2 of
  7078 fp32 outputs, both genuine loops;
- the cap 2 x input + 10 tokens cuts 17 fp32 outputs (3 x + 10, the fp32 cap: 13).
"""

import math

STEM_LETTERS = 3      # letters a looping word family shares
WINDOW = 4            # consecutive words checked
DISTINCT = 3          # of which at least this many are different words
_PUNCT = ",.?!।॥᱾᱿;:"


def length_cap(n_input_tokens, factor=2.0, margin=10, hard_max=128):
    """max_new_tokens for an input of n tokens."""
    return min(hard_max, math.ceil(factor * n_input_tokens) + margin)


def stem_loop(words):
    """True if the last WINDOW words share their first STEM_LETTERS letters and at
    least DISTINCT of them differ (a loop of variants, not one repeated word)."""
    if len(words) < WINDOW:
        return False
    w = [x.strip(_PUNCT) for x in words[-WINDOW:]]
    if any(len(x) < STEM_LETTERS for x in w):
        return False
    return len({x[:STEM_LETTERS] for x in w}) == 1 and len(set(w)) >= DISTINCT


def first_loop(words):
    """Index of the word where the first stem loop completes, or None."""
    for k in range(WINDOW, len(words) + 1):
        if stem_loop(words[:k]):
            return k
    return None


def cut_stem_loop(text):
    """(text, cut): the text up to and including the first word of the loop."""
    words = text.split()
    k = first_loop(words)
    if k is None:
        return text, False
    return " ".join(words[:k - WINDOW + 1]), True
