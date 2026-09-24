"""Ol Chiki transliteration: the shared vectors, plus an independent cross-check."""

import json, re, unicodedata
from pathlib import Path

import pytest

from translit.olchiki import (to_devanagari, to_latin, number_to_santali,
                              _parse, _render_deva, _tidy, has_olchiki)

VECTORS = json.loads((Path(__file__).parent / "data" / "olchiki_vectors.json")
                     .read_text(encoding="utf-8"))
NFC = lambda s: unicodedata.normalize("NFC", s)
FN = {"to_devanagari": to_devanagari, "to_latin": to_latin}


def _run(v):
    return NFC(FN[v["function"]](v["input"], digits=v["digits"]))


@pytest.mark.parametrize("v", VECTORS["vectors"], ids=lambda v: f'{v["id"]}-{v["rule"]}')
def test_vector(v):
    assert _run(v) == v["expected"]


def test_vector_count():
    assert VECTORS["count"] == len(VECTORS["vectors"]) >= 60


def test_checker_is_not_vacuous():
    """A wrong expectation must fail: guards against a comparison that always passes."""
    wrong = {"input": "ᱫᱟᱜ", "function": "to_devanagari", "digits": "spoken",
             "expected": "दाग्"}           # the orthographic form, not the spoken one
    assert _run(wrong) != wrong["expected"]


def test_every_olchiki_codepoint_is_handled():
    """No character of the Ol Chiki block may survive into the speech text."""
    for cp in range(0x1C50, 0x1C80):
        ch = chr(cp)
        for s in (ch, "ᱠ" + ch, ch + "ᱟ"):
            assert not has_olchiki(to_devanagari(s)), (hex(cp), s)
            assert not has_olchiki(to_latin(s)), (hex(cp), s)


@pytest.mark.parametrize("n,words", [(0, "ᱥᱩᱱᱩᱢ"), (1, "ᱢᱤᱫ"), (10, "ᱜᱮᱞ"),
                                     (11, "ᱜᱮᱞ ᱢᱤᱫ"), (20, "ᱵᱟᱨ ᱜᱮᱞ"),
                                     (100, "ᱥᱟᱭ"), (123, "ᱥᱟᱭ ᱵᱟᱨ ᱜᱮᱞ ᱯᱮ")])
def test_numbers_match_the_glossary(n, words):
    assert number_to_santali(n) == words


def test_parser_matches_aksharamukha():
    """Independent cross-check. Rendered with Aksharamukha's orthographic
    conventions, every Santali string in the vectors must match it exactly.
    This catches parser bugs (vowel signs, virama, aspirates, nasals) that
    vectors written by the same hand could share."""
    ak = pytest.importorskip("aksharamukha.transliterate")
    import warnings
    warnings.filterwarnings("ignore")
    checked = 0
    for v in VECTORS["vectors"]:
        s = v["input"]
        if v["function"] != "to_devanagari" or "ᱻ" in s or not has_olchiki(s):
            continue
        if re.search(r"[0-9०-९᱐-᱙]", s):
            continue   # spoken numbers are our own rule; Aksharamukha keeps digits
        ours = NFC(_tidy(_render_deva(_parse(s), "digits", compat=True)))
        ref = NFC(re.sub(r"\s+([।॥])", r"\1", ak.process("Santali", "Devanagari", s)).strip())
        assert ours == ref, s
        checked += 1
    assert checked >= 50
