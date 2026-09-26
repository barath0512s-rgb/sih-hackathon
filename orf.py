"""Oral reading fluency (C1): a child reads a passage aloud; words correct per minute.

The recording is recognised (Hindi ASR), the transcript is aligned to the passage
word by word (Levenshtein with backtrace), and each passage word gets a status:
  correct      read as written (or a near spelling: recognisers spell some words
               differently, e.g. प्रवृत्ति / प्रवृति; see NEAR below)
  error        read as a different word (substitution)
  omitted      skipped
  not_reached  after the last word the child read (not counted as an error)
plus the extra words the child said (insertions, shown, not counted).
  WCPM = correct words / reading time in minutes
reading time = the speech span of the recording (silence at both ends trimmed).
The teacher can override any word on the page; the numbers are recomputed there.

NIPUN Bharat goals (Lakshyas, docs/sources.md#nipun): Grade 2 "45-60 words per
minute" (NIPUN-G2-LIT-2), Grade 3 "at least 60 words per minute" (NIPUN-G3-LIT-2).
Audio is never stored (the hub deletes the upload after recognition; the tablet
never writes it). Validated on public adult Hindi read speech
(bench/results/orf_validation.md); children's reading: NOT MEASURED.
"""

from textnorm import normalize_key

NEAR = 0.75            # character similarity at or above which a word counts as read correctly


def words(text):
    return [w for w in (normalize_key(x) for x in (text or "").split()) if w]


def _sim(a, b):
    """1 - normalised character edit distance."""
    if a == b:
        return 1.0
    n, m = len(a), len(b)
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        cur = [i] + [0] * m
        for j in range(1, m + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] != b[j - 1]))
        prev = cur
    return 1 - prev[m] / max(n, m)


def align(passage, spoken, near=NEAR):
    """[(op, passage_index or None, spoken_index or None)], op in ok|sub|del|ins."""
    P, S = passage, spoken
    n, m = len(P), len(S)
    ok = [[P[i] == S[j] or (near is not None and _sim(P[i], S[j]) >= near) for j in range(m)] for i in range(n)]
    D = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        D[i][0] = i
    for j in range(1, m + 1):
        D[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i][j] = min(D[i - 1][j] + 1, D[i][j - 1] + 1, D[i - 1][j - 1] + (0 if ok[i - 1][j - 1] else 1))
    out, i, j = [], n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and D[i][j] == D[i - 1][j - 1] + (0 if ok[i - 1][j - 1] else 1):
            out.append(("ok" if ok[i - 1][j - 1] else "sub", i - 1, j - 1)); i -= 1; j -= 1
        elif i > 0 and D[i][j] == D[i - 1][j] + 1:
            out.append(("del", i - 1, None)); i -= 1
        else:
            out.append(("ins", None, j - 1)); j -= 1
    return out[::-1]


def score(passage_text, spoken_text, seconds, near=NEAR):
    """{words: [{word, status, heard}], extra, correct, errors, omitted, attempted, seconds, wcpm, accuracy}."""
    raw = [w for w in (passage_text or "").split() if normalize_key(w)]
    P, S = [normalize_key(w) for w in raw], words(spoken_text)
    spoken_raw = [w for w in (spoken_text or "").split() if normalize_key(w)]
    ops = align(P, S, near)
    status = ["omitted"] * len(P)
    heard = [None] * len(P)
    extra = []
    last = -1
    for op, i, j in ops:
        if op in ("ok", "sub"):
            status[i] = "correct" if op == "ok" else "error"
            heard[i] = spoken_raw[j]
            last = max(last, i)
        elif op == "ins":
            extra.append(spoken_raw[j])
    for i in range(last + 1, len(P)):
        status[i] = "not_reached"
    correct = status.count("correct")
    errors = status.count("error") + status.count("omitted")
    attempted = correct + errors
    minutes = seconds / 60 if seconds else 0
    return {"words": [{"word": w, "status": st, "heard": h} for w, st, h in zip(raw, status, heard)],
            "extra": extra, "correct": correct, "errors": errors, "omitted": status.count("omitted"),
            "attempted": attempted, "seconds": round(seconds, 2),
            "wcpm": round(correct / minutes, 1) if minutes else None,
            "accuracy": round(correct / attempted, 3) if attempted else None}


def nipun_band(grade, wcpm):
    """The NIPUN reading goal for the grade, and whether this reading meets it."""
    if wcpm is None:
        return None
    g = str(grade)
    if g == "2":
        return {"lakshya": "NIPUN-G2-LIT-2", "goal": "45-60 words per minute", "met": wcpm >= 45}
    if g == "3":
        return {"lakshya": "NIPUN-G3-LIT-2", "goal": "at least 60 words per minute", "met": wcpm >= 60}
    return None


def speech_seconds(wav_path):
    """Reading time: the recording with silence at both ends trimmed (indicconformer_asr.trim_silence)."""
    import soundfile as sf
    from indicconformer_asr import trim_silence
    x, sr = sf.read(str(wav_path), dtype="float32")
    x = x.mean(axis=1) if x.ndim > 1 else x
    return len(trim_silence(x[None, :], sr=sr)[0]) / sr
