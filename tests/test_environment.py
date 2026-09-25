"""The environment the app runs in (no models needed)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_numpy_stays_below_2_everywhere():
    # torch 2.2 does not run with numpy 2; an export tool once pulled it in.
    for name in ("requirements.txt", "tools/export/requirements-export.txt"):
        text = (ROOT / name).read_text(encoding="utf-8")
        pins = [l for l in text.splitlines() if l.startswith("numpy==")]
        assert pins and all(p.split("==")[1].startswith("1.") for p in pins), name


def test_installed_numpy_is_1x():
    import numpy
    assert numpy.__version__.startswith("1."), numpy.__version__
