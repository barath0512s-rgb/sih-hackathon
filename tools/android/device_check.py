"""F1 M1 on a real device or emulator: install, import a pack, run the REST contract.

    python tools/android/device_check.py --apk android/app/build/outputs/apk/debug/app-debug.apk \
        --pack dist/packs/content-pack-<time>.zip [--serial emulator-5554] [--label emulator-4gb]

Steps: install the APK; copy the pack into the app's private files (run-as, debug
build) and import it through the app's own verified import; forward a local port
to the in-app server (127.0.0.1:5000 on the device); run contract/rest_contract.json
with no engines on the device (so engine cases must answer 503); switch airplane
mode on and run it again; read the app's PSS with dumpsys meminfo. Writes
bench/results/android_m1_<label>.md. Every figure names the device and its RAM.
"""

import argparse
import datetime
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contract.runner import run  # noqa: E402

PKG = "org.team8bitpool.app"
PORT = 5057


def adb(serial, *args, check=True):
    cmd = ["adb"] + (["-s", serial] if serial else []) + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout.strip()


def send(method, path, body):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=data, method=method,
                                 headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), e.read()


def pss_kb(serial):
    out = adb(serial, "shell", "dumpsys", "meminfo", PKG)
    m = re.search(r"TOTAL PSS:\s+(\d+)", out) or re.search(r"^\s*TOTAL\s+(\d+)", out, re.M)
    return int(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apk", type=Path, required=True)
    ap.add_argument("--pack", type=Path, required=True)
    ap.add_argument("--serial")
    ap.add_argument("--label", required=True, help="e.g. emulator-4gb, samsung-4gb")
    a = ap.parse_args()
    s = a.serial

    dev = {k: adb(s, "shell", "getprop", p) for k, p in (("model", "ro.product.model"),
           ("android", "ro.build.version.release"), ("sdk", "ro.build.version.sdk"), ("abi", "ro.product.cpu.abi"))}
    mem = adb(s, "shell", "cat", "/proc/meminfo").splitlines()[0]
    kb = int(re.search(r"(\d+)", mem).group(1))
    dev["ram"] = f"{kb / 1024 / 1024:.1f} GB (MemTotal)"
    dev["cores"] = adb(s, "shell", "nproc")
    print(dev)

    adb(s, "install", "-r", str(a.apk))
    adb(s, "shell", "pm", "clear", PKG)
    adb(s, "shell", "pm", "grant", PKG, "android.permission.RECORD_AUDIO", check=False)
    adb(s, "push", str(a.pack), "/data/local/tmp/pack.zip")
    adb(s, "shell", "am", "start", "-W", "-n", f"{PKG}/.MainActivity")
    adb(s, "shell", "run-as", PKG, "cp", "/data/local/tmp/pack.zip", "files/pack.zip")
    adb(s, "forward", f"tcp:{PORT}", "tcp:5000")
    t0 = time.time()
    adb(s, "shell", "am", "start", "-n", f"{PKG}/.MainActivity", "--es", "import_pack", "pack.zip")
    counts = None
    while time.time() - t0 < 180:
        try:
            st, _, raw = send("GET", "/health/models", None)
            cp = json.loads(raw).get("content_pack") if st == 200 else None
            if cp:
                counts = cp.get("counts"); break
        except (OSError, ValueError):
            pass
        time.sleep(1)
    import_s = time.time() - t0
    if counts is None:
        sys.exit("the pack was not installed within 180 s (adb logcat -s tablet)")
    print("pack installed in", round(import_s, 1), "s:", counts)

    online = run(send, engines=set())
    adb(s, "shell", "cmd", "connectivity", "airplane-mode", "enable", check=False)
    time.sleep(3)
    airplane = adb(s, "shell", "settings", "get", "global", "airplane_mode_on")
    offline = run(send, engines=set())
    adb(s, "shell", "cmd", "connectivity", "airplane-mode", "disable", check=False)
    # Typed mode: a lesson line, through the page's own endpoint, timed on the device.
    st, _, raw = send("GET", "/lessons", None)
    line = json.loads(raw)["lessons"][0]["plan"][0]["hindi"]
    typed = []
    for _ in range(20):
        t = time.perf_counter()
        send("POST", "/translate/text", {"text": line, "direction": "hi-to-sat"})
        typed.append((time.perf_counter() - t) * 1000)
    typed.sort()
    pss = pss_kb(s)

    n_cases = len(json.loads((ROOT / "contract" / "rest_contract.json").read_text(encoding="utf-8"))["cases"])
    lines = [f"# F1 M1 on {dev['model']} ({a.label})", "",
             f"- Date: {datetime.date.today().isoformat()}. Device: {dev['model']}, Android {dev['android']} "
             f"(SDK {dev['sdk']}), {dev['abi']}, {dev['cores']} cores, RAM {dev['ram']}.",
             f"- APK: `{a.apk.name}` ({a.apk.stat().st_size / 1e6:.1f} MB). Pack: `{a.pack.name}` "
             f"({a.pack.stat().st_size / 1e6:.1f} MB): {json.dumps(counts)}.",
             "- No speech, translation or voice engine is on the device in M1: those contract cases must answer "
             "503 engine_not_on_device, and they did if they are not listed as failures.", "",
             "| Check | Result |", "|---|---|",
             f"| Pack import (copy, SHA-256 check of every file, install) | {import_s:.1f} s |",
             f"| REST contract, network on | {n_cases - len(online)} of {n_cases} cases pass |",
             f"| REST contract, airplane mode (airplane_mode_on={airplane}) | {n_cases - len(offline)} of {n_cases} cases pass |",
             f"| Typed lesson line from the pack, round trip over adb forward (20 runs) | median {typed[10]:.0f} ms, max {typed[-1]:.0f} ms |",
             f"| App PSS after the checks (dumpsys meminfo) | {pss / 1024:.0f} MB |" if pss else "| App PSS | NOT MEASURED |"]
    if online or offline:
        lines += ["", "Failures:", ""] + [f"- online: {f}" for f in online] + [f"- airplane: {f}" for f in offline]
    out = ROOT / "bench" / "results" / f"android_m1_{a.label}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
