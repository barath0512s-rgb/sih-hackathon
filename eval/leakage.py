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


# ── Speech: the benchmark clips (bench/clips/public/manifest.json) ─────────────
# Their transcripts, source ids ("dataset:id") and speakers are recorded as the
# "asr-public" entry, so no fine-tuning run can use them: not the clip, not the
# same sentence, and not another recording by the same speaker (IndicVoices'
# train split may hold the valid split's speakers). Speaker ids are dataset
# identifiers, not names; transcripts are stored only as hashes.

def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def record_asr_clips(manifest, path=HASHES):
    """Add the public benchmark clips to the hash file (called by
    bench/fetch_public_clips.py after it writes the manifest)."""
    clips = json.loads(Path(manifest).read_text(encoding="utf-8"))
    data = json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else {}
    data["asr-public"] = {
        "revision": sorted({f"{c['source']['dataset']}@{c['source']['revision'][:10]}:{c['source']['split']}"
                            for c in clips}),
        "sha256": sorted({_sha(normalise_for_hash(c["reference"])) for c in clips}),
        "source_ids": sorted({f"{c['source']['dataset']}:{c['source']['id']}" for c in clips}),
        "speaker_ids": sorted({f"{c['source']['dataset']}:{c['speaker_id']}" for c in clips if c.get("speaker_id")}),
    }
    Path(path).write_text(json.dumps(data, indent=0) + "\n", encoding="utf-8")
    return len(clips)


def assert_no_asr_test_leakage(items, path=HASHES, require=True):
    """Raise LeakedTestSentence if any fine-tuning item is, or shares a sentence
    or a speaker with, a benchmark clip. items: dicts with any of "text",
    "dataset" + "id", "dataset" + "speaker_id"."""
    if not Path(path).exists() or "asr-public" not in json.loads(Path(path).read_text(encoding="utf-8")):
        if require:
            raise LeakedTestSentence(f"{Path(path).name} has no asr-public entry: run "
                                     "bench/fetch_public_clips.py first, so the benchmark clips can be excluded.")
        return 0
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    texts, _ = load_hashes(path)
    ids, spk = set(data["asr-public"]["source_ids"]), set(data["asr-public"]["speaker_ids"])
    for i, it in enumerate(items):
        why = ("same sentence" if it.get("text") and _sha(normalise_for_hash(it["text"])) in texts else
               "same clip" if f"{it.get('dataset')}:{it.get('id')}" in ids else
               "same speaker" if f"{it.get('dataset')}:{it.get('speaker_id')}" in spk else None)
        if why:
            raise LeakedTestSentence(f"fine-tuning item {i} matches a benchmark clip ({why}): {it}")
    return len(items)
