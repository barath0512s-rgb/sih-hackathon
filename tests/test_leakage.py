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


def test_asr_benchmark_clips_are_refused(tmp_path):
    from eval.leakage import assert_no_asr_test_leakage, record_asr_clips
    man = tmp_path / "manifest.json"
    man.write_text(json.dumps([{
        "reference": "ᱟᱢ ᱪᱮᱫ ᱧᱩᱛᱩᱢ", "speaker_id": "S1",
        "source": {"dataset": "ai4bharat/IndicVoices", "revision": "abcdef1234", "split": "valid", "id": "a.flac"}}]),
        encoding="utf-8")
    h = tmp_path / "hashes.json"
    assert record_asr_clips(man, h) == 1
    ok = {"dataset": "ai4bharat/IndicVoices", "id": "b.flac", "speaker_id": "S2", "text": "ᱤᱧ"}
    assert assert_no_asr_test_leakage([ok], h) == 1
    for bad in ({**ok, "text": "ᱟᱢ ᱪᱮᱫ ᱧᱩᱛᱩᱢ।"}, {**ok, "id": "a.flac"}, {**ok, "speaker_id": "S1"}):
        with pytest.raises(LeakedTestSentence):
            assert_no_asr_test_leakage([bad], h)


def test_the_real_benchmark_clips_are_recorded():
    from pathlib import Path
    root = Path(__file__).parent.parent
    data = json.loads((root / "eval" / "test_set_hashes.json").read_text(encoding="utf-8"))
    man = json.loads((root / "bench/clips/public/manifest.json").read_text(encoding="utf-8"))
    # FLEURS reuses a sentence id when several speakers read the same sentence.
    ids = {f"{c['source']['dataset']}:{c['source']['id']}" for c in man}
    assert set(data["asr-public"]["source_ids"]) == ids


def test_any_asr_fine_tuning_script_uses_the_guard():
    from pathlib import Path
    root = Path(__file__).parent.parent
    for f in list(root.glob("*asr*.py")) + list(root.glob("train*.py")) + list(root.glob("tools/**/finetune*.py")):
        src = f.read_text(encoding="utf-8")
        if "fine-tun" in src.lower() or f.name.startswith(("train", "finetune")):
            assert "assert_no_test_leakage(" in src or "assert_no_asr_test_leakage(" in src, f.name
