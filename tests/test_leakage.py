"""The hash guard that keeps evaluation test sentences out of training (no models)."""

import hashlib
import json

import pytest

from eval.leakage import LeakedTestSentence, assert_no_test_leakage, normalise_for_hash


@pytest.fixture
def hashes(tmp_path):
    test = ["गांव के सभी लोग मेले में गए थे।", "ᱟᱢ ᱪᱮᱫ ᱧᱩᱛᱩᱢ?"]
    p = tmp_path / "hashes.json"
    p.write_text(json.dumps({"in22-conv": {"revision": "x", "sha256": [
        hashlib.sha256(normalise_for_hash(t).encode("utf-8")).hexdigest() for t in test]}}),
        encoding="utf-8")
    return p


def test_a_test_sentence_is_refused_even_lightly_edited(hashes):
    with pytest.raises(LeakedTestSentence, match="in22-conv"):
        assert_no_test_leakage([("आज हम पढ़ेंगे।", "ᱛᱮᱦᱮᱸᱡ"), ("गांव के सभी लोग  मेले में गए थे", "x")], hashes)
    with pytest.raises(LeakedTestSentence):
        assert_no_test_leakage([("x", "ᱟᱢ ᱪᱮᱫ ᱧᱩᱛᱩᱢ ?")], hashes)


def test_clean_data_passes(hashes):
    assert assert_no_test_leakage([("आज हम पढ़ेंगे।", "ᱛᱮᱦᱮᱸᱡ")], hashes) == 1


def test_training_refuses_to_start_without_the_hashes(tmp_path):
    with pytest.raises(LeakedTestSentence, match="missing"):
        assert_no_test_leakage([("a", "b")], tmp_path / "none.json")
    assert assert_no_test_leakage([("a", "b")], tmp_path / "none.json", require=False) == 0


def test_train_nmt_uses_the_guard():
    from pathlib import Path
    src = (Path(__file__).parent.parent / "train_nmt.py").read_text(encoding="utf-8")
    assert "assert_no_test_leakage(" in src
