"""Photo import (C2), laptop hub only: a photographed page of Hindi text -> lesson text.

Tesseract OCR (Apache-2.0) with its Hindi model (`hin.traineddata`), run as a
program on the hub. The photo is read, straightened (EXIF rotation), converted to
grey, enlarged when small and contrast-stretched, recognised, and deleted: only
the text comes back, into the "add a lesson" box, where the teacher checks it
before the usual import (lines, types, NIPUN goals) runs.

Not on the tablet: ML Kit, the offline option there, is under Google's terms and
sends usage metrics to Google when the tablet is online, against the app's
offline and privacy design (docs/sources.md#mlkit-text). Decision of 27 Sep 2026.
Accuracy on the team's own photographed pages: bench/results/ocr_eval.md.
"""

import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import config

WINDOWS_DEFAULT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


class OcrError(Exception):
    pass


def tesseract_cmd():
    """The tesseract program: config.TESSERACT_CMD, else PATH, else the Windows installer's folder."""
    for c in (getattr(config, "TESSERACT_CMD", None), shutil.which("tesseract"), WINDOWS_DEFAULT):
        if c and Path(c).exists():
            return str(c)
    return None


def languages():
    cmd = tesseract_cmd()
    if not cmd:
        return []
    r = subprocess.run([cmd, "--list-langs"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [l.strip() for l in (r.stdout + r.stderr).splitlines()[1:] if l.strip() and " " not in l.strip()]


def available():
    return "hin" in languages()


def prepare(image_bytes):
    """PNG bytes ready for OCR: EXIF rotation, grey, at least 2000 px wide, contrast stretched."""
    from PIL import Image, ImageOps
    im = Image.open(io.BytesIO(image_bytes))
    im = ImageOps.exif_transpose(im).convert("L")
    if im.width < 2000:
        f = 2000 / im.width
        im = im.resize((2000, int(im.height * f)), Image.LANCZOS)
    im = ImageOps.autocontrast(im, cutoff=1)
    out = io.BytesIO()
    im.save(out, format="PNG")
    return out.getvalue()


def recognise(image_bytes, psm=4):
    """Hindi text of a page photo. psm 4: a single column of text of variable sizes."""
    cmd = tesseract_cmd()
    if not cmd:
        raise OcrError("Tesseract is not installed on the hub")
    if "hin" not in languages():
        raise OcrError("Tesseract's Hindi language data (hin.traineddata) is not installed")
    d = Path(tempfile.mkdtemp(prefix="ocr_"))
    try:
        p = d / "page.png"
        p.write_bytes(prepare(image_bytes))
        r = subprocess.run([cmd, str(p), "stdout", "-l", "hin", "--psm", str(psm)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        if r.returncode != 0:
            raise OcrError(f"Tesseract failed: {r.stderr.strip()[:200]}")
        return clean(r.stdout)
    finally:
        shutil.rmtree(d, ignore_errors=True)      # the photo is never kept


def clean(text):
    """Blank lines dropped, runs of spaces collapsed, form feeds removed."""
    import re
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in text.replace("\f", "\n").splitlines()]
    return "\n".join(l for l in lines if l)
