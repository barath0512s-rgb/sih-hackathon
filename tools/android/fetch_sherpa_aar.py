"""Download the sherpa-onnx Android library the app builds against, and check it.

    python tools/android/fetch_sherpa_aar.py

The official release AAR (Apache-2.0) from
https://github.com/k2-fsa/sherpa-onnx/releases/tag/v1.13.8 ; 50.1 MB, so it is not
kept in git. The same version as the laptop's sherpa-onnx and the WSL export.
"""
import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/v1.13.8/sherpa-onnx-1.13.8.aar"
SHA256 = "633c24321e06b1fe79feafa03ea16cbc0f8a286641e2da3559bac91bdb13bd96"
OUT = ROOT / "android" / "app" / "libs" / "sherpa-onnx-1.13.8.aar"


def ok(p):
    return p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == SHA256


if __name__ == "__main__":
    if ok(OUT):
        print("present and verified:", OUT)
        sys.exit(0)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".part")
    urllib.request.urlretrieve(URL, tmp)
    if not ok(tmp):
        tmp.unlink()
        sys.exit("SHA-256 mismatch: not installed")
    tmp.replace(OUT)
    print("downloaded and verified:", OUT)
