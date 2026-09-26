"""A1: lesson-line matcher (lesson_match.py), its Kotlin vectors and its thresholds."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "android"))

from lesson_match import canonical, hindi_number, match, similarity  # noqa: E402


def test_numbers_are_compared_as_words():
    assert canonical("4", "hi") == canonical("चार", "hi") == "चार"
    assert canonical("3425", "hi") == "तीन हजार चार सौ पच्चीस"
    assert canonical("तीन हज़ार चार सौ पच्चीस", "hi") == canonical("3425", "hi")     # nukta folded
    assert canonical("᱔", "sat") == canonical("ᱯᱩᱱ", "sat")
    assert canonical("12", "sat") == "ᱜᱮᱞ ᱵᱟᱨ"


def test_hindi_numbers():
    assert [hindi_number(n) for n in (0, 11, 25, 49, 99, 100, 101, 1000, 1905)] == [
        "शून्य", "ग्यारह", "पच्चीस", "उनचास", "निन्यानवे", "एक सौ", "एक सौ एक", "एक हजार", "एक हजार नौ सौ पांच"]


def test_similarity_basics():
    assert similarity("दो आम और तीन आम मिलाओ।", "दो आम और तीन आम मिलाओ", "hi") == 1.0   # punctuation ignored
    assert similarity("", "आम", "hi") == 0.0
    assert 0 < similarity("दो आम और तीन आम मिलाओ", "दो आम मिलाओ", "hi") < 1


def test_below_threshold_is_never_a_match():
    lines = ["दो आम और तीन आम मिलाओ", "कुल कितने हुए"]
    m = match("आज मौसम बहुत अच्छा है", lines, 0.41, "hi")
    assert not m["matched"]
    m = match("दो आम और तीन आम मिलाओ", lines, 0.41, "hi")
    assert m["matched"] and m["line"] == lines[0] and m["score"] == 1.0


def test_kotlin_vectors_are_current():
    import make_lesson_match_vectors as mk
    assert mk.OUT.read_text(encoding="utf-8") == mk.build(), "run python tools/android/make_lesson_match_vectors.py"


def test_thresholds_come_from_the_tuning_result():
    import config
    r = json.loads((ROOT / "bench" / "results" / "lesson_match.json").read_text(encoding="utf-8"))
    assert config.LESSON_MATCH_THRESHOLD == {lang: r[lang]["threshold"] for lang in ("hi", "sat")}


def test_device_config_is_current():
    import sync_config
    assert sync_config.DEVICE_OUT.read_text(encoding="utf-8") == sync_config.expected_device(), \
        "run python tools/android/sync_config.py"
