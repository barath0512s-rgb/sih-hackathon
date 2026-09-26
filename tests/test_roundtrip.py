"""A3: the round-trip check flags a model translation whose back-translation drifts
(no model weights: the model calls are replaced)."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for m in ("torch", "transformers", "IndicTransToolkit", "sacrebleu"):
    pytest.importorskip(m)

import config  # noqa: E402
import pipeline  # noqa: E402


@pytest.fixture
def pl(monkeypatch):
    p = pipeline.VaaniSetuPipeline.__new__(pipeline.VaaniSetuPipeline)
    backs = {"ᱥᱟᱹᱨᱤ": "बच्चे स्कूल जाते हैं", "ᱵᱷᱩᱞ": "मौसम बहुत ठंडा था और सब घर पर रहे"}
    monkeypatch.setattr(p, "_nmt_review", lambda text, s, t, **k: ({"बच्चे स्कूल जाते हैं": "ᱥᱟᱹᱨᱤ"}.get(text, "ᱵᱷᱩᱞ"), 0.9, False),
                        raising=False)
    monkeypatch.setattr(p, "_nmt", lambda text, s, t: (backs[text], 0.9), raising=False)
    monkeypatch.setattr(p, "_apply_domain_glossary", lambda out, lang: out, raising=False)
    monkeypatch.setattr(pipeline.database, "get_correction", lambda text, d: None)
    monkeypatch.setattr(pipeline, "lookup_hi_to_sat", lambda text: None)
    monkeypatch.setattr(config, "ROUNDTRIP_CHECK", True)
    monkeypatch.setattr(config, "ROUNDTRIP_CHRF_THRESHOLD", 40.0)
    pipeline.TRANSLATION_CACHE.clear()
    yield p
    pipeline.TRANSLATION_CACHE.clear()


def test_a_faithful_round_trip_is_not_flagged(pl):
    r = pl.translate("बच्चे स्कूल जाते हैं", "hi-to-sat", roundtrip=True)
    assert r["roundtrip_chrf"] == 100.0 and not r.get("needs_review")


def test_a_drifting_round_trip_is_flagged_and_says_why(pl):
    r = pl.translate("आज हम गिनती सीखेंगे", "hi-to-sat", roundtrip=True)
    assert r["roundtrip_chrf"] < 40.0
    assert r["needs_review"] and r["review_reason"] == "roundtrip"


def test_without_the_check_nothing_is_added(pl):
    r = pl.translate("आज हम गिनती सीखेंगे", "hi-to-sat")
    assert "roundtrip_chrf" not in r and not r.get("needs_review")
    # asked again with the check, the cached translation gets it
    r = pl.translate("आज हम गिनती सीखेंगे", "hi-to-sat", roundtrip=True)
    assert r["source"] == "cached" and r["needs_review"]


def test_the_threshold_is_the_tuned_one():
    import importlib
    importlib.reload(config)
    res = json.loads((ROOT / "eval" / "results" / "roundtrip_flag.json").read_text(encoding="utf-8"))
    assert config.ROUNDTRIP_CHRF_THRESHOLD == res["threshold"]
