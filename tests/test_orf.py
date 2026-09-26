"""C1: oral reading fluency scoring (no models needed)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import orf  # noqa: E402

P = "आज रविवार है। मीना अपने दादा के साथ बगीचे में गई।"


def test_a_perfect_reading():
    s = orf.score(P, "आज रविवार है मीना अपने दादा के साथ बगीचे में गई", 6.0)
    assert s["correct"] == 11 and s["errors"] == 0 and s["wcpm"] == 110.0 and s["accuracy"] == 1.0


def test_misread_skipped_and_not_reached_words():
    s = orf.score(P, "आज रविवार है मीना अपनी दादा साथ", 6.0)
    st = [w["status"] for w in s["words"]]
    assert st[:4] == ["correct"] * 4
    assert st[4] == "correct"                 # अपनी for अपने: a near spelling (the recogniser's, not the child's)
    assert st[6] == "omitted"                 # के skipped
    assert st[7] == "correct"
    assert st[8:] == ["not_reached"] * 3      # stopped: not errors
    assert s["attempted"] == 8 and s["errors"] == 1


def test_a_wrong_word_is_an_error_and_extra_words_are_listed():
    s = orf.score(P, "आज सोमवार है मीना अपने दादा के साथ बगीचे में गई थी", 6.0)
    assert s["words"][1]["status"] == "error" and s["words"][1]["heard"] == "सोमवार"
    assert s["extra"] == ["थी"]


def test_nipun_bands_quote_the_guidelines():
    assert orf.nipun_band("2", 50) == {"lakshya": "NIPUN-G2-LIT-2", "goal": "45-60 words per minute", "met": True}
    assert orf.nipun_band("3", 59)["met"] is False and orf.nipun_band("3", 59)["goal"] == "at least 60 words per minute"
    assert orf.nipun_band("1", 50) is None
    from nipun import lakshya
    assert lakshya.get("NIPUN-G2-LIT-2")["text"] == "45-60 words per minute"
    assert lakshya.get("NIPUN-G3-LIT-2")["text"] == "at least 60 words per minute"


def test_passages_are_hindi_and_cover_both_reading_goals():
    d = json.loads((ROOT / "content" / "orf_passages.json").read_text(encoding="utf-8"))
    goals = {g for p in d["passages"] for g in p["lakshya_ids"]}
    assert {"NIPUN-G2-LIT-2", "NIPUN-G3-LIT-2"} <= goals
    for p in d["passages"]:
        assert 40 <= len(p["text"].split()) <= 80


def test_the_route_deletes_the_recording():
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    body = src[src.index("def orf_score"):src.index('@app.route("/languages")')]
    assert "tmp_path.unlink(missing_ok=True)" in body and "wav.unlink(missing_ok=True)" in body
    assert body.index("finally:") < body.index("tmp_path.unlink")
    assert 'consent") != "1"' in body


def test_kotlin_vectors_are_current():
    sys.path.insert(0, str(ROOT / "tools" / "android"))
    import make_orf_vectors as mk
    assert mk.OUT.read_text(encoding="utf-8") == mk.build(), "run python tools/android/make_orf_vectors.py"
