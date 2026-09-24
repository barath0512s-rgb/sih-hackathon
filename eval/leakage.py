"""Keep the evaluation test sets out of training and tuning.

eval/eval_benchmarks.py writes eval/test_set_hashes.json: the SHA-256 of every
test sentence (IN22-Gen, IN22-Conv, FLORES-200 devtest), after normalisation.
Only hashes are stored, never the sentences. Every training or tuning script
calls assert_no_test_leakage() on its data before it starts:

    from eval.leakage import assert_no_test_leakage
    assert_no_test_leakage(pairs)          # pairs: [(source, target), ...]

It raises LeakedTestSentence if any sentence (either side) is a test sentence.
"""

import hashlib
import json
import re
import unicodedata
from pathlib import Path

HASHES = Path(__file__).resolve().parent / "test_set_hashes.json"


class LeakedTestSentence(RuntimeError):
    """Training data contains a sentence from an evaluation test set."""


def normalise_for_hash(text):
    """NFC, no zero-width marks, single spaces, no surrounding punctuation or
    case, so trivial edits of a test sentence still match."""
    t = unicodedata.normalize("NFC", text or "")
    t = re.sub(r"[\u200b-\u200d\ufeff]", "", t)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t.strip(" .।॥?!,;:\"'᱾᱿")


def load_hashes(path=HASHES):
    if not Path(path).exists():
        return set(), []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {h for s in data.values() for h in s["sha256"]}, sorted(data)


def assert_no_test_leakage(pairs, path=HASHES, require=True):
    """Raise LeakedTestSentence if any text in `pairs` is a test sentence.
    require=True also refuses to run without the hash file, so a fresh clone
    cannot train before the test sets have been hashed."""
    hashes, sets = load_hashes(path)
    if not hashes:
        if require:
            raise LeakedTestSentence(f"{Path(path).name} is missing: run eval/eval_benchmarks.py first, "
                              "so the test sets can be excluded.")
        return 0
    hits = []
    for i, pair in enumerate(pairs):
        for text in (pair if isinstance(pair, (tuple, list)) else (pair,)):
            if hashlib.sha256(normalise_for_hash(text).encode("utf-8")).hexdigest() in hashes:
                hits.append((i, text[:60]))
    if hits:
        raise LeakedTestSentence(f"{len(hits)} training items are test sentences from {sets}, "
                          f"e.g. item {hits[0][0]}: {hits[0][1]!r}")
    return len(pairs)
