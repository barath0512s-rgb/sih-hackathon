"""A7: the language registry, the README table made from it, and the preview voices."""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import languages  # noqa: E402


def test_the_registry_is_valid_and_its_sources_exist():
    sources = (ROOT / "docs" / "sources.md").read_text(encoding="utf-8")
    anchors = set(re.findall(r'<a name="([^"]+)">', sources))
    codes = [l["code"] for l in languages.load()]
    assert codes == ["hi", "sat", "unr", "hoc"]
    for l in languages.load():
        for st in languages.STAGES:
            s = l["stages"][st]
            if s["source"]:
                assert s["source"].split("#")[1] in anchors, s["source"]
            if s["maturity"] in ("production", "preview"):
                assert s["engine"] and s["licence"], (l["code"], st)


def test_the_readme_table_is_the_registry():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    block = text.split(languages.START)[1].split(languages.END)[0].strip()
    assert block == languages.readme_table(), "regenerate: python languages.py (paste between the markers)"


def test_nothing_preview_is_called_production():
    unr = languages.get("unr")["stages"]
    assert unr["tts"]["maturity"] == "preview" and unr["asr"]["maturity"] == "not available"


def test_preview_voices_use_the_official_tokenizer():
    pytest.importorskip("transformers")
    import mms_tts
    for lang in ("unr", "hoc"):
        if not mms_tts.available(lang):
            pytest.skip("preview voices not installed")
        from transformers import AutoTokenizer
        try:
            hub = AutoTokenizer.from_pretrained(f"facebook/mms-tts-{lang}")
        except Exception:
            pytest.skip("Hub tokenizer not cached")
        v = mms_tts.MmsVoice(lang)
        for s in ("ଆମେ ଇସ୍କୁଲ ଜାନା।", "  ଟ ଡ  ", "ହାତ ହେ 12"):
            assert v.ids(s) == hub(s).input_ids
        assert mms_tts.to_model_script("नमस्ते") == "ନମସ୍ତେ"
        with pytest.raises(ValueError):
            mms_tts.to_model_script("\U000118A1")          # Warang Citi: not supported yet
