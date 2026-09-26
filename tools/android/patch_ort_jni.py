"""Make ONNX Runtime's Java bridge use the onnxruntime that sherpa-onnx ships (A5).

    python tools/android/patch_ort_jni.py      # after tools/android/fetch_sherpa_aar.py

Why: the app carries one libonnxruntime.so. sherpa-onnx 1.13.8 is built against
onnxruntime 1.28.2 and its JNI needs OrtGetApiBase@VERS_1.28.2; ONNX Runtime's
Android package on Maven stops at 1.28.0, whose Java bridge
(libonnxruntime4j_jni.so) needs OrtGetApiBase@VERS_1.28.0. ELF symbol versions
must match exactly, so the bridge would not load (checked on the emulator:
"cannot locate symbol OrtGetApiBase"). A patch release keeps the C API unchanged
(same ORT_API_VERSION), so the bridge's version requirement is rewritten from
VERS_1.28.0 to VERS_1.28.2 (the name in .dynstr and its ELF hash in .gnu.version_r).
Nothing else changes. ONNX Runtime is MIT-licensed (modification allowed).

Writes android/app/src/main/jniLibs/<abi>/: the patched libonnxruntime4j_jni.so and
sherpa-onnx's libonnxruntime.so (so the packaging step keeps that one). Git-ignored;
Gradle's pickFirst takes the app's own jniLibs first.
"""

import hashlib
import struct
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHERPA_AAR = ROOT / "android" / "app" / "libs" / "sherpa-onnx-1.13.8.aar"
ORT_URL = "https://repo1.maven.org/maven2/com/microsoft/onnxruntime/onnxruntime-android/1.28.0/onnxruntime-android-1.28.0.aar"
OUT = ROOT / "android" / "app" / "src" / "main" / "jniLibs"
ABIS = ("arm64-v8a", "x86_64")
OLD, NEW = b"VERS_1.28.0", b"VERS_1.28.2"


def elf_hash(name: bytes) -> int:
    h = 0
    for c in name:
        h = ((h << 4) + c) & 0xFFFFFFFF
        g = h & 0xF0000000
        if g:
            h ^= g >> 24
        h &= ~g & 0xFFFFFFFF
    return h


def patch(so: bytes) -> bytes:
    b = bytearray(so)
    shoff, = struct.unpack_from("<Q", b, 0x28)
    shentsize, shnum, _ = struct.unpack_from("<HHH", b, 0x3A)
    secs = [struct.unpack_from("<IIQQQQIIQQ", b, shoff + i * shentsize) for i in range(shnum)]
    verneed = next(s for s in secs if s[1] == 0x6FFFFFFE)
    strtab = secs[verneed[6]]
    n_patched = 0
    off = verneed[4]
    while True:
        _, vn_cnt, _, vn_aux, vn_next = struct.unpack_from("<HHIII", b, off)
        a = off + vn_aux
        for _ in range(vn_cnt):
            vna_hash, vna_flags, vna_other, vna_name, vna_next = struct.unpack_from("<IHHII", b, a)
            p = strtab[4] + vna_name
            if bytes(b[p:p + len(OLD) + 1]) == OLD + b"\0":
                b[p:p + len(NEW)] = NEW
                struct.pack_into("<I", b, a, elf_hash(NEW))
                n_patched += 1
            a += vna_next
        if not vn_next:
            break
        off += vn_next
    if n_patched != 1:
        raise SystemExit(f"expected one {OLD.decode()} requirement, found {n_patched}")
    return bytes(b)


def main():
    if not SHERPA_AAR.is_file():
        sys.exit("run tools/android/fetch_sherpa_aar.py first")
    cache = ROOT / "dist" / "onnxruntime-android-1.28.0.aar"
    if not cache.is_file():
        cache.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(ORT_URL, cache)
    print("onnxruntime-android-1.28.0.aar sha256", hashlib.sha256(cache.read_bytes()).hexdigest())
    with zipfile.ZipFile(cache) as ort, zipfile.ZipFile(SHERPA_AAR) as sh:
        for abi in ABIS:
            d = OUT / abi
            d.mkdir(parents=True, exist_ok=True)
            (d / "libonnxruntime4j_jni.so").write_bytes(patch(ort.read(f"jni/{abi}/libonnxruntime4j_jni.so")))
            (d / "libonnxruntime.so").write_bytes(sh.read(f"jni/{abi}/libonnxruntime.so"))
            print("wrote", d.relative_to(ROOT))


if __name__ == "__main__":
    main()
