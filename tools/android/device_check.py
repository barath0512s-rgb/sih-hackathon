"""F1 M1 on a real device or emulator, in one pass.

    python tools/android/device_check.py --apk android/app/build/outputs/apk/release/app-release.apk \
        --debug-apk android/app/build/outputs/apk/debug/app-debug.apk \
        --pack dist/packs/content-pack-<time>.zip [--serial <id>] [--label samsung-4gb-android13] \
        [--record docs/demo_assets/android_samsung.mp4]

1. Finds the device (a USB device first, else the only device; --serial to choose) and
   records model, Android version, RAM (MemTotal), CPU, cores and WebView version.
2. Installs the APK given by --apk (the release build) from a clean state and imports
   the pack through the app's import folder (Android/data/<app>/files/import/): the
   same verified import as the file picker, available in release builds.
3. Runs contract/rest_contract.json against the in-app server (adb forward) with the
   network on. No speech, translation or voice engine is on the device in M1, so the
   cases that need one must answer 503 engine_not_on_device.
4. Switches airplane mode on and checks that the page really renders in the WebView,
   through Android's accessibility tree (uiautomator), by text, not by screen
   coordinates: the lesson lines are listed, a lesson line is chosen, Translate is
   pressed, and Santali (Ol Chiki) appears. With --record, this is screen-recorded
   (about 30 s), starting with the quick settings panel showing airplane mode.
5. Runs the contract again, still in airplane mode; then airplane mode off.
6. With --debug-apk: installs the debug build of the same code over it (same signing
   key) and records 3 s from the native microphone through MicBridge.
7. Samples PSS every second throughout (app process, WebView renderer, sum).
Writes bench/results/<device>_<date>_m1.md (or <label>_<date>_m1.md). Every figure names
the device and its RAM; nothing here is a 2 GB measurement unless the device has 2 GB.
"""

import argparse
import datetime
import json
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contract.runner import load as load_contract, run  # noqa: E402

PKG = "org.team8bitpool.app"
PORT = 5057
LINE = "मेज़ पर जो रखा है"          # line 2 of the default lesson (कक्षा २ · जोड़ना)
OL_CHIKI = re.compile(r"[ᱚ-᱿]")


def adb(serial, *args, check=True, timeout=120):
    cmd = ["adb"] + (["-s", serial] if serial else []) + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
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


def find_device(serial):
    rows = [l.split() for l in adb(None, "devices").splitlines()[1:] if l.strip()]
    ready = [r[0] for r in rows if len(r) > 1 and r[1] == "device"]
    if serial:
        if serial not in ready:
            sys.exit(f"{serial} is not connected and authorised: {rows}")
        return serial
    usb = [s for s in ready if not s.startswith("emulator-")]
    if len(usb) == 1:
        return usb[0]
    if not usb and len(ready) == 1:
        return ready[0]
    sys.exit(f"Choose a device with --serial: {rows or 'none connected'}")


def device_info(s):
    p = lambda k: adb(s, "shell", "getprop", k, check=False)
    kb = int(re.search(r"(\d+)", adb(s, "shell", "cat", "/proc/meminfo").splitlines()[0]).group(1))
    cpuinfo = adb(s, "shell", "cat", "/proc/cpuinfo", check=False)
    hw = re.search(r"^Hardware\s*:\s*(.+)$", cpuinfo, re.M)
    wv = re.search(r"Current WebView package \(name, version\): \(([^,]+), ([^)]+)\)",
                   adb(s, "shell", "dumpsys", "webviewupdate", check=False))
    return {"manufacturer": p("ro.product.manufacturer"), "model": p("ro.product.model"),
            "android": p("ro.build.version.release"), "sdk": p("ro.build.version.sdk"),
            "abi": p("ro.product.cpu.abi"), "ram": f"{kb / 1024 / 1024:.1f} GB (MemTotal {kb} kB)",
            "cpu": p("ro.soc.model") or p("ro.board.platform") or (hw.group(1).strip() if hw else "?"),
            "cores": str(cpuinfo.count("processor\t")),
            "webview": f"{wv.group(1)} {wv.group(2)}" if wv else "?"}


def pss_kb(serial):
    out = adb(serial, "shell", "dumpsys", "meminfo", PKG, check=False)
    m = re.search(r"TOTAL PSS:\s+(\d+)", out) or re.search(r"^\s*TOTAL\s+(\d+)", out, re.M)
    return int(m.group(1)) if m else None


def renderer_pss_kb(serial):
    """PSS of the WebView renderer (a separate sandboxed process), from the summary list."""
    out = adb(serial, "shell", "dumpsys", "meminfo", check=False)
    vals = [int(m.group(1).replace(",", "")) for m in re.finditer(r"^\s*([\d,]+)K: \S*sandboxed_process\d*", out, re.M)]
    return max(vals) if vals else 0


class PssSampler(threading.Thread):
    """PSS every second: the app process, the WebView renderer, and their sum; peaks kept."""

    def __init__(self, serial):
        super().__init__(daemon=True)
        self.serial, self.peak, self.peak_renderer, self.peak_sum = serial, 0, 0, 0
        self.samples, self.running = 0, True

    def run(self):
        while self.running:
            try:
                v, w = pss_kb(self.serial) or 0, renderer_pss_kb(self.serial)
                if v:
                    self.peak = max(self.peak, v); self.peak_renderer = max(self.peak_renderer, w)
                    self.peak_sum = max(self.peak_sum, v + w); self.samples += 1
            except Exception:
                pass
            time.sleep(1)


# ── the page, through the accessibility tree ─────────────────────────────────
def ui_nodes(s):
    adb(s, "shell", "uiautomator", "dump", "/sdcard/vs_ui.xml", check=False, timeout=60)
    xml = adb(s, "exec-out", "cat", "/sdcard/vs_ui.xml", check=False)
    try:
        root = ET.fromstring(xml[xml.index("<"):])
    except (ValueError, ET.ParseError):
        return []
    out = []
    for n in root.iter("node"):
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.get("bounds", ""))
        if not m:
            continue
        x1, y1, x2, y2 = map(int, m.groups())
        out.append({"text": (n.get("text") or "") + " " + (n.get("content-desc") or ""),
                    "cls": n.get("class", ""), "box": (x1, y1, x2, y2)})
    return out


def screen_h(s):
    m = re.search(r"(\d+)x(\d+)", adb(s, "shell", "wm", "size"))
    return int(m.group(2)) if m else 1920


def tap(s, box):
    adb(s, "shell", "input", "tap", str((box[0] + box[2]) // 2), str((box[1] + box[3]) // 2))


def find_visible(s, pred, swipes=6):
    """The first node matching pred that is on screen, scrolling down if needed."""
    h = screen_h(s)
    for _ in range(swipes + 1):
        for n in ui_nodes(s):
            x1, y1, x2, y2 = n["box"]
            if pred(n) and y2 > y1 and 0 < y1 and y2 < h * 0.95:
                return n
        adb(s, "shell", "input", "swipe", "500", str(int(h * 0.7)), "500", str(int(h * 0.35)), "400")
        time.sleep(1.2)
    return None


def page_flow(s, record=None):
    """Lessons listed -> a lesson line chosen -> Translate -> Santali shown. Returns findings."""
    res = {"lessons_listed": False, "line_chosen": False, "translated": False, "santali": ""}
    rec = None
    if record:
        adb(s, "shell", "rm", "-f", "/sdcard/vs_rec.mp4", check=False)
        rec = subprocess.Popen(["adb", "-s", s, "shell", "screenrecord", "--time-limit", "40", "/sdcard/vs_rec.mp4"])
        time.sleep(1)
        adb(s, "shell", "cmd", "statusbar", "expand-settings", check=False)     # airplane mode, shown
        time.sleep(4)
        adb(s, "shell", "cmd", "statusbar", "collapse", check=False)
        time.sleep(1)
    adb(s, "shell", "am", "start", "-n", f"{PKG}/.MainActivity")
    time.sleep(6)
    line = find_visible(s, lambda n: LINE in n["text"])
    res["lessons_listed"] = line is not None
    if line:
        time.sleep(1.5)
        tap(s, line["box"])
        time.sleep(2)
        res["line_chosen"] = True
        btn = find_visible(s, lambda n: "अनुवाद" in n["text"] and "Button" in n["cls"])
        if btn:
            tap(s, btn["box"])
            time.sleep(4)
            sat = [n["text"].strip() for n in ui_nodes(s) if len(OL_CHIKI.findall(n["text"])) > 10]
            res["translated"] = bool(sat)
            res["santali"] = sat[0] if sat else ""
    time.sleep(3)
    if rec:
        rec.wait(timeout=60)
        Path(record).parent.mkdir(parents=True, exist_ok=True)
        adb(s, "pull", "/sdcard/vs_rec.mp4", str(record), timeout=300)
        res["recording"] = f"{Path(record).stat().st_size / 1e6:.1f} MB"
    adb(s, "shell", "screencap", "-p", "/sdcard/vs_shot.png", check=False)
    shots = ROOT / "dist" / "screens"
    shots.mkdir(parents=True, exist_ok=True)
    adb(s, "pull", "/sdcard/vs_shot.png", str(shots / f"{s.replace(':', '_')}_translated.png"), check=False)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apk", type=Path, required=True, help="the build to test (release)")
    ap.add_argument("--debug-apk", type=Path, help="debug build of the same code, for the mic capture")
    ap.add_argument("--pack", type=Path, required=True)
    ap.add_argument("--serial")
    ap.add_argument("--label", help="file name stem, e.g. samsung-4gb-android13 (default: the model)")
    ap.add_argument("--record", type=Path, help="screen-record the page check to this .mp4")
    a = ap.parse_args()

    s = find_device(a.serial)
    dev = device_info(s)
    print(json.dumps(dev, ensure_ascii=False))

    adb(s, "uninstall", PKG, check=False)
    adb(s, "install", str(a.apk), timeout=300)
    adb(s, "shell", "pm", "grant", PKG, "android.permission.RECORD_AUDIO", check=False)
    imp = f"/sdcard/Android/data/{PKG}/files/import"
    adb(s, "shell", "mkdir", "-p", imp)
    adb(s, "forward", f"tcp:{PORT}", "tcp:5000")
    sampler = PssSampler(s); sampler.start()
    t0 = time.time()
    adb(s, "push", str(a.pack), f"{imp}/pack.zip", timeout=300)
    adb(s, "shell", "am", "start", "-W", "-n", f"{PKG}/.MainActivity")
    counts = None
    while time.time() - t0 < 240:
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
        sys.exit("the pack was not installed within 240 s (adb logcat -s tablet)")
    print("pack installed in", round(import_s, 1), "s (push + verified import):", counts)

    online = run(send, engines=set())
    adb(s, "shell", "cmd", "connectivity", "airplane-mode", "enable", check=False)
    time.sleep(3)
    airplane = adb(s, "shell", "settings", "get", "global", "airplane_mode_on", check=False)
    page = page_flow(s, a.record)
    offline = run(send, engines=set())
    adb(s, "shell", "cmd", "connectivity", "airplane-mode", "disable", check=False)
    st, _, raw = send("GET", "/lessons", None)
    line = json.loads(raw)["lessons"][0]["plan"][0]["hindi"]
    typed = []
    for _ in range(20):
        t = time.perf_counter()
        send("POST", "/translate/text", {"text": line, "direction": "hi-to-sat"})
        typed.append((time.perf_counter() - t) * 1000)
    typed.sort()
    time.sleep(2)
    sampler.running = False; sampler.join(5)

    mic = None
    if a.debug_apk:
        adb(s, "install", "-r", str(a.debug_apk), timeout=300)
        adb(s, "shell", "pm", "grant", PKG, "android.permission.RECORD_AUDIO", check=False)
        adb(s, "shell", "am", "start", "-n", f"{PKG}/.MainActivity", "--ei", "mic_test_ms", "3000")
        for _ in range(20):
            time.sleep(1)
            out = adb(s, "shell", "run-as", PKG, "cat", "files/mic_test.json", check=False)
            if out.startswith("{"):
                mic = json.loads(out); break

    n_cases = len(load_contract()["cases"])
    stem = a.label or re.sub(r"[^A-Za-z0-9]+", "-", f"{dev['manufacturer']}-{dev['model']}").strip("-")
    date = datetime.date.today().isoformat()
    lines = [f"# F1 M1 on {dev['manufacturer']} {dev['model']} ({stem})", "",
             f"- Date: {date}. Device: {dev['manufacturer']} {dev['model']}, Android {dev['android']} (SDK {dev['sdk']}), "
             f"{dev['abi']}, CPU {dev['cpu']}, {dev['cores']} cores, RAM {dev['ram']}, WebView {dev['webview']}.",
             f"- APK tested: `{a.apk.name}` ({a.apk.stat().st_size / 1e6:.1f} MB). Pack: `{a.pack.name}` "
             f"({a.pack.stat().st_size / 1e6:.1f} MB): {json.dumps(counts)}.",
             "- No speech, translation or voice engine is on the device in M1: the contract cases that need one must "
             "answer 503 engine_not_on_device, and they did unless listed as failures.", "",
             "| Check | Result |", "|---|---|",
             f"| Pack import (push + SHA-256 check of every file + install, release build) | {import_s:.1f} s |",
             f"| REST contract, network on | {n_cases - len(online)} of {n_cases} cases pass |",
             f"| Page in the WebView, airplane mode on (airplane_mode_on={airplane}) | lesson lines listed: "
             f"{'yes' if page['lessons_listed'] else 'NO'}; line chosen: {'yes' if page['line_chosen'] else 'NO'}; "
             f"Translate gave Santali: {'yes' if page['translated'] else 'NO'} |",
             f"| REST contract, airplane mode | {n_cases - len(offline)} of {n_cases} cases pass |",
             f"| Typed lesson line from the pack, round trip over adb forward (20 runs) | median {typed[10]:.0f} ms, "
             f"max {typed[-1]:.0f} ms |",
             (f"| Native mic (MicBridge, 3 s, 16 kHz; debug build of the same code) | {mic['seconds']:.2f} s of audio, "
              f"RMS {mic['rms']:.4f}, peak {mic['peak']:.3f} |" if mic and mic.get("ok")
              else f"| Native mic | {'FAILED: ' + json.dumps(mic) if a.debug_apk else 'NOT MEASURED (no --debug-apk)'} |"),
             f"| Peak PSS during the checks and the typed lesson (dumpsys meminfo every 1 s, {sampler.samples} "
             f"samples): app / WebView renderer / sum | {sampler.peak / 1024:.0f} / {sampler.peak_renderer / 1024:.0f} / "
             f"**{sampler.peak_sum / 1024:.0f} MB** |"]
    if page.get("santali"):
        lines += ["", f"Santali shown after Translate: {page['santali'][:120]}"]
    if page.get("recording"):
        lines += ["", f"Screen recording: `{a.record.as_posix()}` ({page['recording']})."]
    if online or offline:
        lines += ["", "Failures:", ""] + [f"- online: {f}" for f in online] + [f"- airplane: {f}" for f in offline]
    out = ROOT / "bench" / "results" / f"{stem}_{date}_m1.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
