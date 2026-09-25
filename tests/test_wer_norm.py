from textnorm import normalize_for_wer


def test_punctuation_including_ol_chiki_marks_goes():
    assert normalize_for_wer("ᱤᱧ ᱫᱚ ᱥᱮᱨᱮᱧ᱾ ᱟᱢ ᱵᱟᱝ᱿") == "ᱤᱧ ᱫᱚ ᱥᱮᱨᱮᱧ ᱟᱢ ᱵᱟᱝ"
    assert normalize_for_wer("हाँ, मैं आऊँगा। ठीक है?") == "हाँ मैं आऊँगा ठीक है"


def test_digits_become_ascii_in_both_scripts():
    assert normalize_for_wer("᱗ ᱦᱚᱲ") == "7 ᱦᱚᱲ"
    assert normalize_for_wer("७ बच्चे 12") == "7 बच्चे 12"


def test_whitespace_and_tags():
    assert normalize_for_wer("  <unintelligible> ᱟᱫᱚ   ᱚᱱᱟ \n") == "ᱟᱫᱚ ᱚᱱᱟ"


def test_spelling_is_not_folded():
    # Unlike the matching key: nukta and chandrabindu still count as errors.
    assert normalize_for_wer("ज़रूर") != normalize_for_wer("जरूर")
    assert normalize_for_wer("पाँच") != normalize_for_wer("पांच")
