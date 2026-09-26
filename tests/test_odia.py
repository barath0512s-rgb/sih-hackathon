"""translit/odia.py: Devanagari / Ol Chiki -> Odia script, for the MMS voices (A7, C4)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from translit.odia import deva_to_odia, olchiki_to_odia  # noqa: E402


def test_parallel_blocks_and_exceptions():
    assert deva_to_odia("नमस्ते") == "ନମସ୍ତେ"
    assert deva_to_odia("वन") == "ୱନ"                  # व -> ୱ, the letter the MMS vocabularies have
    assert deva_to_odia("क़") == "କ"                   # nukta dropped
    assert deva_to_odia("दो। तीन॥") == "ଦୋ। ତୀନ॥"      # dandas kept
    assert deva_to_odia("१२") == "୧୨"


def test_olchiki_goes_through_devanagari_and_o_is_the_inherent_vowel():
    assert olchiki_to_odia("ᱡᱚᱦᱟᱨ") == "ଜହାର୍"        # ᱚ /ɔ/ = Odia's inherent vowel
    assert olchiki_to_odia("ᱚᱲᱟᱜ") == "ଅଡାକ୍"
