"""A4 acceptance, automated: a correction made on one tablet reaches another through the hub.

    python tools/android/sync_roundtrip.py [--serial emulator-5554] [--apk <release apk>]

1. Tablet A: install the APK, import the newest signed content pack, correct one pack
   line (POST /feedback, as the page's correction box does), export (POST /sync/export)
   and pull the signed file.
2. Hub: merge it (sync.py) into a COPY of the hub database, and build a signed
   content pack (no audio, to be quick) from that copy.
3. Tablet B: the same device with the app's data cleared (`pm clear`: a new install
   with a new device key and no corrections), import the new pack, and ask for the
   corrected line (POST /translate/text): the tablet must answer with the
   correction, source "teacher".
4. A pack with one changed byte in its manifest is refused.
Writes bench/results/sync_roundtrip_<date>.md.
"""

import argparse
import datetime
import glob
import json
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "android"))

import device_check as dc  # noqa: E402

PKG = dc.PKG
EXT = f"/sdcard/Android/data/{PKG}/files"


def call(s, method, path, body=None):
    dc.adb(s, "forward", f"tcp:{dc.PORT}", "tcp:5000")
    return dc.send(method, path, body)


def import_pack(s, zip_path):
    dc.adb(s, "shell", "mkdir", "-p", f"{EXT}/import")
    dc.adb(s, "push", str(zip_path), f"{EXT}/import/{Path(zip_path).name}", timeout=600)
    dc.adb(s, "shell", "am", "start", "-n", f"{PKG}/.MainActivity")
    t0 = time.time()
    while dc.adb(s, "shell", "ls", f"{EXT}/import/", check=False).strip():
        if time.time() - t0 > 600:
            raise SystemExit("import did not finish")
        time.sleep(2)
    time.sleep(2)
    st, _, b = call(s, "GET", "/health/models")
    return json.loads(b).get("content_pack")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--serial")
    ap.add_argument("--apk", default=str(ROOT / "android/app/build/outputs/apk/release/app-release.apk"))
    a = ap.parse_args()
    s = dc.find_device(a.serial)
    log = []
    pack = sorted(glob.glob(str(ROOT / "dist" / "packs" / "content-pack-*.zip")))[-1]
    # 1. tablet A
    dc.adb(s, "shell", "pm", "clear", PKG, check=False)
    dc.install(s, Path(a.apk), replace=True)
    dc.adb(s, "shell", "am", "start", "-n", f"{PKG}/.MainActivity")
    time.sleep(4)
    cp = import_pack(s, pack)
    log.append(f"Tablet A: imported `{Path(pack).name}` ({cp and cp.get('created')}).")
    z = zipfile.ZipFile(pack)
    trans = json.loads(z.read("translations.json"))["hi-to-sat"]
    line = next(v for v in trans.values() if v["source"] == "model")
    hindi, before = line["source_text"], line["text"]
    corrected = before + " ᱥᱟᱹᱨᱤ"                     # a marked correction, recognisable later
    st, _, b = call(s, "POST", "/translate/text", {"text": hindi, "direction": "hi-to-sat"})
    got_a = json.loads(b)
    st, _, b = call(s, "POST", "/feedback", {"hindi_text": hindi, "santali_text": before, "direction": "hi-to-sat",
                                             "is_correct": False, "corrected_text": corrected})
    assert st == 200, b
    st, _, b = call(s, "POST", "/sync/export", {})
    exp = json.loads(b)
    assert st == 200 and exp["corrections"] == 1, b
    local = Path(tempfile.mkdtemp()) / exp["file"]
    dc.adb(s, "pull", f"{EXT}/export/{exp['file']}", str(local))
    log.append(f"Tablet A (device {exp['device_id']}): corrected “{hindi}” from “{before}” to “{corrected}”; "
               f"exported `{exp['file']}` ({exp['corrections']} correction, {exp['class_rows']} class rows).")
    # 2. hub, on a copy of its database
    import database
    work = Path(tempfile.mkdtemp())
    if Path(database.DB_FILE).exists():
        shutil.copyfile(database.DB_FILE, work / "hub.db")
    database.DB_FILE = work / "hub.db"
    database.init_db()
    import sync
    sync.REVIEW = work / "native_review.md"
    rep = sync.import_file(local.read_bytes())
    log.append(f"Hub (copy of its database): signature checked; merged: applied {rep['applied']}, "
               f"conflicts {len(rep['conflicts'])}.")
    from tools.build_content_pack import build, zip_dir
    out = work / "pack"
    build(out, audio=False, worksheets=False, log=lambda *x: None)
    newzip = zip_dir(out, work / f"content-pack-sync-{int(time.time())}.zip")
    m = json.loads((out / "translations.json").read_text(encoding="utf-8"))["hi-to-sat"]
    from textnorm import normalize_key
    carried = m[normalize_key(hindi)]
    log.append(f"Hub: new signed pack `{newzip.name}`; the line now reads “{carried['text']}” (source {carried['source']}).")
    # 3. tablet B
    dc.adb(s, "shell", "pm", "clear", PKG)
    dc.adb(s, "shell", "pm", "grant", PKG, "android.permission.RECORD_AUDIO", check=False)
    dc.adb(s, "shell", "am", "start", "-n", f"{PKG}/.MainActivity")
    time.sleep(4)
    import_pack(s, newzip)
    st, _, b = call(s, "POST", "/translate/text", {"text": hindi, "direction": "hi-to-sat"})
    got_b = json.loads(b)
    st2, _, b2 = call(s, "POST", "/sync/export", {})
    dev_b = json.loads(b2)["device_id"]
    ok = got_b.get("translated_text") == corrected and got_b.get("source") == "teacher"
    log.append(f"Tablet B (app data cleared: device {dev_b}): “{hindi}” → “{got_b.get('translated_text')}” "
               f"(source {got_b.get('source')}). **{'PASS' if ok else 'FAIL'}**")
    # 4. tampered pack refused
    bad = work / "content-pack-tampered.zip"
    with zipfile.ZipFile(newzip) as zin, zipfile.ZipFile(bad, "w") as zout:
        for it in zin.infolist():
            data = zin.read(it.filename)
            if it.filename == "manifest.json":
                data = data.replace(b'"format": 1', b'"format": 1 ')
            zout.writestr(it, data)
    dc.adb(s, "logcat", "-c", check=False)
    import_pack(s, bad)
    st, _, b = call(s, "POST", "/translate/text", {"text": hindi, "direction": "hi-to-sat"})
    still = json.loads(b).get("translated_text") == corrected
    refused = "signature" in dc.adb(s, "logcat", "-d", check=False) or still
    log.append(f"Tampered pack (one byte of manifest.json changed): {'refused, the previous pack stays' if still else 'NOT refused'}.")
    date = datetime.date.today().isoformat()
    info = dc.device_info(s)
    L = [f"# A4 correction sync round trip ({date})", "",
         f"- Device: {info['model']}, Android {info['android']}, RAM {info['ram']}; release APK. Tablet B is the "
         "same emulator with the app's data cleared (new device key, no corrections), standing in for a second tablet.",
         f"- Before the correction, tablet A answered “{got_a.get('translated_text')}” (source {got_a.get('source')}).", ""]
    L += [f"{i + 1}. {x}" for i, x in enumerate(log)]
    L += ["", f"Result: **{'PASS' if ok and still else 'FAIL'}**"]
    p = ROOT / "bench" / "results" / f"sync_roundtrip_{date}.md"
    p.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(L))
    sys.exit(0 if ok and still else 1)


if __name__ == "__main__":
    main()
