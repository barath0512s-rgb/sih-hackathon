"""C2: photo import helpers (Tesseract itself is tested only where it is installed)."""
import io
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
PIL = pytest.importorskip("PIL")
import ocr  # noqa: E402


def test_clean_drops_blank_lines_and_extra_spaces():
    assert ocr.clean("आज  हम\n\n  गिनेंगे।\f\n") == "आज हम\nगिनेंगे।"


def test_prepare_straightens_greys_and_enlarges():
    from PIL import Image
    im = Image.new("RGB", (800, 600), "white")
    buf = io.BytesIO(); im.save(buf, format="JPEG")
    out = Image.open(io.BytesIO(ocr.prepare(buf.getvalue())))
    assert out.mode == "L" and out.width == 2000


def test_no_tesseract_is_a_clear_error(monkeypatch):
    monkeypatch.setattr(ocr, "tesseract_cmd", lambda: None)
    with pytest.raises(ocr.OcrError, match="not installed"):
        ocr.recognise(b"x")


def test_the_photo_is_not_kept():
    src = (ROOT / "ocr.py").read_text(encoding="utf-8")
    assert "shutil.rmtree(d, ignore_errors=True)" in src.split("def recognise")[1].split("def clean")[0]


def test_a_rendered_test_page_reads_back():
    if not ocr.available():
        pytest.skip("Tesseract with hin is not installed here")
    pymupdf = pytest.importorskip("pymupdf")
    import jiwer
    pdf = ROOT / "docs" / "samples" / "ocr_pages" / "page_01.pdf"
    png = pymupdf.open(str(pdf))[0].get_pixmap(dpi=200).tobytes("png")
    got = ocr.recognise(png)
    truth = pdf.with_suffix(".txt").read_text(encoding="utf-8")
    assert jiwer.cer(" ".join(truth.split()), " ".join(got.split())) < 0.2
