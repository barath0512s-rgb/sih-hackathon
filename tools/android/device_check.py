"""F1 M1 on a real device or emulator: one command, resumable where the device needs you.

    python tools/android/device_check.py --apk android/app/build/outputs/apk/release/app-release.apk \
        --debug-apk android/app/build/outputs/apk/debug/app-debug.apk \
        --pack dist/packs/content-pack-<time>.zip [--serial <id>] [--label realme-pad-mini-4gb-android11] \
        [--record docs/demo_assets/android_realme.mp4]
    ... when it stops with "ACTION NEEDED" (exit code 2), do what it says, then run the
    same command again with --resume.

Stages (the progress is kept in dist/device_check/<serial>.json):
  setup     device facts read from the device (getprop, /proc/meminfo, /proc/cpuinfo,
            dumpsys package com.google.android.webview); install the release APK; grant
            the microphone; import the pack through the app's import folder (the same
            verified import as the file picker, release builds too); the 24 shared API
            checks with the network on; typed lesson line timings.
  airplane  airplane mode on: adb where Android allows it, otherwise it asks you
            (Android 11 does not let adb toggle it without root).
  offline   in airplane mode: the page in the WebView through the accessibility tree
            (lessons listed, a line chosen, Translate -> Santali), screen-recorded with
            --record; the native mic of the build under test through the page; the 24
            checks again.
  debugmic  the debug build of the same code over it (same key): 3 s through MicBridge.
  report    bench/results/<label>_<date>_m1.md.
It stops with exact instructions, rather than retrying, when: the install is refused
(Realme/ColorOS: "Install via USB"), taps or the accessibility dump are refused
("Disable permission monitoring"), the microphone permission cannot be granted, airplane
mode must be switched by hand, or the app was killed in the background (battery
setting). PSS is sampled every second in every stage (app, WebView renderer, sum; peak).
Every figure names the device and its RAM as read from it; nothing is assumed.
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
OL_CHIKI = re.compile("[\u1C5A-\u1C7F]")
STAGES = ["setup", "airplane", "offline", "debugmic", "report"]

INSTALL_VIA_USB = (
    "The tablet refused the install over USB. On the tablet: Settings -> Additional settings -> Developer "
    "options -> turn ON 'Install via USB' (Realme may ask you to sign in or insert a SIM once). If a prompt "
    "'Install this app?' appears on the tablet during the install, tap Install. Then say 'done'.")
PERMISSION_MONITORING = (
    "The tablet refused adb taps or the screen-reading dump (Realme/ColorOS permission monitoring). On the "
    "tablet: Settings -> Additional settings -> Developer options -> turn ON 'Disable permission monitoring' "
    "(if the tablet asks to restart, restart it and reconnect USB, accepting 'Allow USB debugging' again). "
    "Then say 'done'.")
MIC_PERMISSION = (
    "The microphone permission could not be granted over adb. On the tablet: Settings -> Apps -> App management "
    "-> VaaniSetu -> Permissions -> Microphone -> Allow. Then say 'done'.")
AIRPLANE_ON = ("Android 11 does not let adb switch airplane mode. On the tablet: swipe down from the top and tap "
               "the airplane icon so it is ON (Wi-Fi and mobile data off). Leave USB connected. Then say 'done'.")
KILLED = ("The app was stopped in the background by the tablet. On the tablet: Settings -> Battery -> (App battery "
          "management / More battery settings) -> VaaniSetu -> turn ON 'Allow background activity' (and 'Allow "
          "auto launch' if shown). Then say 'done'.")


class ActionNeeded(Exception):
    """Something only a person can do on the device."""


def adb_raw(serial, *args, timeout=120):
    """stdout + stderr, never raises: for the commands whose failure text we inspect."""
    cmd = ["adb"] + (["-s", serial] if serial else []) + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return (r.stdout + "\n" + r.stderr).strip()


def adb(serial, *args, check=True, timeout=120):
    cmd = ["adb"] + (["-s", serial] if serial else []) + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout.strip()


def device_info(s):
    """Everything read from the device; nothing assumed."""
    p = lambda k: adb(s, "shell", "getprop", k, check=False)
    kb = int(re.search(r"(\d+)", adb(s, "shell", "cat", "/proc/meminfo").splitlines()[0]).group(1))
    cpuinfo = adb(s, "shell", "cat", "/proc/cpuinfo", check=False)
    hw = re.search(r"^Hardware\s*:\s*(.+)$", cpuinfo, re.M)
    soc = " ".join(x for x in (p("ro.soc.manufacturer"), p("ro.soc.model")) if x) \
        or p("ro.board.platform") or p("ro.hardware") or (hw.group(1).strip() if hw else "?")
    wv_pkg = adb(s, "shell", "dumpsys", "package", "com.google.android.webview", check=False)
    wv = re.search(r"versionName=(\S+)", wv_pkg)
    cur = re.search(r"Current WebView package \(name, version\): \(([^,]+), ([^)]+)\)",
                    adb(s, "shell", "dumpsys", "webviewupdate", check=False))
    return {"manufacturer": p("ro.product.manufacturer"), "brand": p("ro.product.brand"),
            "model": p("ro.product.model"), "device": p("ro.product.device"),
            "android": p("ro.build.version.release"), "sdk": p("ro.build.version.sdk"),
            "abi": p("ro.product.cpu.abi"), "soc": soc, "board": p("ro.board.platform"),
            "cores": str(cpuinfo.count("processor\t")),
            "ram": f"{kb / 1024 / 1024:.1f} GB (MemTotal {kb} kB)",
            "webview_package": f"com.google.android.webview {wv.group(1)}" if wv else "com.google.android.webview not installed",
            "webview_in_use": f"{cur.group(1)} {cur.group(2)}" if cur else "?",
            "rom": p("ro.build.version.opporom") or p("ro.build.version.realmeui") or p("ro.build.display.id")}


def app_alive(s):
    return bool(adb(s, "shell", "pidof", PKG, check=False).strip())


def install(s, apk, replace=False):
    out = adb_raw(s, "install", *(["-r"] if replace else []), str(apk), timeout=300)
    if "Success" in out:
        return
    if any(k in out for k in ("INSTALL_FAILED_USER_RESTRICTED", "canceled by user", "INSTALL_FAILED_ABORTED",
                              "INSTALL_FAILED_VERIFICATION_FAILURE")):
        raise ActionNeeded(INSTALL_VIA_USB + f" (adb said: {out[-200:]})")
    raise RuntimeError(f"install failed: {out[-400:]}")


def grant_mic(s):
    out = adb_raw(s, "shell", "pm", "grant", PKG, "android.permission.RECORD_AUDIO")
    ok = "granted=true" in adb(s, "shell", "dumpsys", "package", PKG, check=False).split("RECORD_AUDIO", 1)[-1][:40]
    if not ok and ("SecurityException" in out or "Exception" in out):
        raise ActionNeeded(MIC_PERMISSION + f" (adb said: {out[-160:]})")


def airplane_on(s):
    return adb(s, "shell", "settings", "get", "global", "airplane_mode_on", check=False).strip() == "1"


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
    r = adb_raw(s, "shell", "uiautomator", "dump", "/sdcard/vs_ui.xml", timeout=60)
    if "SecurityException" in r or "not allowed" in r.lower():
        raise ActionNeeded(PERMISSION_MONITORING)
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
    r = adb_raw(s, "shell", "input", "tap", str((box[0] + box[2]) // 2), str((box[1] + box[3]) // 2))
    if "INJECT_EVENTS" in r or "SecurityException" in r:
        raise ActionNeeded(PERMISSION_MONITORING)


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
            time.sleep(3)
            sat = []
            for _ in range(5):          # an old WebView updates its accessibility tree late: look again
                sat = [n["text"].strip() for n in ui_nodes(s) if len(OL_CHIKI.findall(n["text"])) > 10]
                if sat:
                    break
                time.sleep(1.5)
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


def mic_through_page(s, seconds=3):
    """The native microphone in the build under test (release), through the page: press
    the Hindi mic button, wait, press it again. The page uploads what MicBridge recorded to
    the in-app server, which logs the body size (no speech recognition on the device in M1,
    so the page then says so). Returns (bytes, approx seconds of 16 kHz 16-bit audio) or None."""
    adb(s, "logcat", "-c", check=False)
    btn = find_visible(s, lambda n: "हिंदी बोलिए" in n["text"] and "Button" in n["cls"])
    if not btn:
        return None
    tap(s, btn["box"]); time.sleep(seconds); tap(s, btn["box"]); time.sleep(4)
    log = adb(s, "logcat", "-d", "-s", "tablet:I", check=False)
    m = re.findall(r"request POST /translate/audio(?:_stream)? body=(\d+) bytes", log)
    if not m:
        return None
    n = int(m[-1])
    return n, max(0.0, (n - 44 - 400) / 32000)       # minus WAV header and multipart fields (approx.)



class Sampler:
    """Runs a PssSampler for one stage and folds its peaks into the saved state."""

    def __init__(self, s, st):
        self.st, self.p = st, PssSampler(s)
        self.p.start()

    def stop(self):
        self.p.running = False; self.p.join(5)
        pk = self.st.setdefault("pss", {"app": 0, "renderer": 0, "sum": 0, "samples": 0})
        pk["app"] = max(pk["app"], self.p.peak); pk["renderer"] = max(pk["renderer"], self.p.peak_renderer)
        pk["sum"] = max(pk["sum"], self.p.peak_sum); pk["samples"] += self.p.samples


def stage_setup(s, a, st):
    st["device"] = dev = device_info(s)
    print(json.dumps(dev, ensure_ascii=False))
    adb(s, "uninstall", PKG, check=False)
    install(s, a.apk)
    grant_mic(s)
    imp = f"/sdcard/Android/data/{PKG}/files/import"
    adb(s, "shell", "mkdir", "-p", imp)
    adb(s, "forward", f"tcp:{PORT}", "tcp:5000")
    smp = Sampler(s, st)
    try:
        t0 = time.time()
        adb(s, "push", str(a.pack), f"{imp}/pack.zip", timeout=300)
        adb(s, "shell", "am", "start", "-W", "-n", f"{PKG}/.MainActivity")
        counts = None
        while time.time() - t0 < 240:
            try:
                code, _, raw = send("GET", "/health/models", None)
                cp = json.loads(raw).get("content_pack") if code == 200 else None
                if cp:
                    counts = cp.get("counts"); break
            except (OSError, ValueError):
                pass
            time.sleep(1)
        if counts is None:
            if not app_alive(s):
                raise ActionNeeded(KILLED)
            raise RuntimeError("the pack was not installed within 240 s (adb logcat -s tablet)")
        st["import_s"], st["counts"] = round(time.time() - t0, 1), counts
        st["online"] = run(send, engines=set())
        _, _, raw = send("GET", "/lessons", None)
        line = json.loads(raw)["lessons"][0]["plan"][0]["hindi"]
        typed = []
        for _ in range(20):
            t = time.perf_counter(); send("POST", "/translate/text", {"text": line, "direction": "hi-to-sat"})
            typed.append((time.perf_counter() - t) * 1000)
        st["typed"] = sorted(typed)
    finally:
        smp.stop()


def stage_airplane(s, a, st):
    # VS_MANUAL_AIRPLANE=1 behaves as on Android 11 (adb cannot switch it): for testing the manual path.
    import os
    if not airplane_on(s) and os.environ.get("VS_MANUAL_AIRPLANE") != "1":
        adb(s, "shell", "cmd", "connectivity", "airplane-mode", "enable", check=False)
        time.sleep(3)
    if not airplane_on(s):
        raise ActionNeeded(AIRPLANE_ON)
    st["airplane"] = "1"


def stage_offline(s, a, st):
    if not airplane_on(s):
        raise ActionNeeded(AIRPLANE_ON)
    adb(s, "forward", f"tcp:{PORT}", "tcp:5000")
    smp = Sampler(s, st)
    try:
        st["page"] = page_flow(s, a.record)
        if not app_alive(s):
            raise ActionNeeded(KILLED)
        st["mic_release"] = mic_through_page(s)
        adb(s, "shell", "am", "start", "-n", f"{PKG}/.MainActivity")
        time.sleep(3)
        st["offline"] = run(send, engines=set())
        if st["offline"] and not app_alive(s):
            raise ActionNeeded(KILLED)
    finally:
        smp.stop()


def stage_debugmic(s, a, st):
    if not a.debug_apk:
        st["mic_debug"] = None
        return
    install(s, a.debug_apk, replace=True)
    grant_mic(s)
    adb(s, "shell", "run-as", PKG, "rm", "-f", "files/mic_test.json", check=False)
    adb(s, "shell", "am", "start", "-n", f"{PKG}/.MainActivity", "--ei", "mic_test_ms", "3000")
    st["mic_debug"] = None
    for _ in range(20):
        time.sleep(1)
        out = adb(s, "shell", "run-as", PKG, "cat", "files/mic_test.json", check=False)
        if out.startswith("{"):
            st["mic_debug"] = json.loads(out); break


def stage_report(s, a, st):
    dev = st["device"]
    n_cases = len(load_contract()["cases"])
    stem = a.label or re.sub(r"[^A-Za-z0-9]+", "-", f"{dev['brand']}-{dev['model']}").strip("-").lower()
    date = datetime.date.today().isoformat()
    page, mic_r, mic, pss, typed = st["page"], st.get("mic_release"), st.get("mic_debug"), st["pss"], st["typed"]
    lines = [f"# F1 M1 on {dev['brand']} {dev['model']} ({stem})", "",
             f"- Date: {date}. Read from the device: {dev['manufacturer']} {dev['model']} ({dev['device']}), "
             f"Android {dev['android']} (SDK {dev['sdk']}), {dev['rom']}, SoC {dev['soc']} (board {dev['board']}), "
             f"{dev['abi']}, {dev['cores']} cores, RAM {dev['ram']}; WebView: {dev['webview_package']}, "
             f"in use {dev['webview_in_use']}.",
             f"- APK tested: `{a.apk.name}` ({a.apk.stat().st_size / 1e6:.1f} MB). Pack: `{a.pack.name}` "
             f"({a.pack.stat().st_size / 1e6:.1f} MB): {json.dumps(st['counts'])}.",
             "- No speech, translation or voice engine is on the device in M1: the contract cases that need one must "
             "answer 503 engine_not_on_device, and they did unless listed as failures.",
             f"- Manual steps asked for during the run: {', '.join(st.get('actions', [])) or 'none'}.", "",
             "| Check | Result |", "|---|---|",
             f"| Pack import (push + SHA-256 check of every file + install, release build) | {st['import_s']:.1f} s |",
             f"| REST contract, network on | {n_cases - len(st['online'])} of {n_cases} cases pass |",
             f"| Page in the WebView, airplane mode on (airplane_mode_on={st.get('airplane')}) | lesson lines listed: "
             f"{'yes' if page['lessons_listed'] else 'NO'}; line chosen: {'yes' if page['line_chosen'] else 'NO'}; "
             f"Translate gave Santali: {'yes' if page['translated'] else 'NO'} |",
             f"| REST contract, airplane mode | {n_cases - len(st['offline'])} of {n_cases} cases pass |",
             f"| Typed lesson line from the pack, round trip over adb forward (20 runs) | median {typed[10]:.0f} ms, "
             f"max {typed[-1]:.0f} ms |",
             (f"| Native mic, build under test, through the page (Hindi mic pressed for about 3 s) | "
              f"{mic_r[0]} bytes uploaded, about {mic_r[1]:.1f} s of 16 kHz audio |"
              if mic_r else "| Native mic, build under test, through the page | FAILED: no upload seen |"),
             (f"| Native mic (MicBridge, 3 s, 16 kHz; debug build of the same code) | {mic['seconds']:.2f} s of audio, "
              f"RMS {mic['rms']:.4f}, peak {mic['peak']:.3f} |" if mic and mic.get("ok")
              else f"| Native mic, debug build | {'FAILED: ' + json.dumps(mic) if a.debug_apk else 'NOT MEASURED (no --debug-apk)'} |"),
             f"| Peak PSS over all stages (dumpsys meminfo every 1 s, {pss['samples']} samples): app / WebView renderer / "
             f"sum | {pss['app'] / 1024:.0f} / {pss['renderer'] / 1024:.0f} / **{pss['sum'] / 1024:.0f} MB** |"]
    if page.get("santali"):
        lines += ["", f"Santali shown after Translate: {page['santali'][:120]}"]
    if page.get("recording"):
        lines += ["", f"Screen recording: `{a.record.as_posix()}` ({page['recording']})."]
    if st["online"] or st["offline"]:
        lines += ["", "Failures:", ""] + [f"- online: {f}" for f in st["online"]] + [f"- airplane: {f}" for f in st["offline"]]
    out = ROOT / "bench" / "results" / f"{stem}_{date}_m1.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    print("\nDone. You can switch airplane mode off on the device.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apk", type=Path, required=True, help="the build to test (release)")
    ap.add_argument("--debug-apk", type=Path, help="debug build of the same code, for the MicBridge capture")
    ap.add_argument("--pack", type=Path, required=True)
    ap.add_argument("--serial")
    ap.add_argument("--label", help="file name stem, e.g. realme-pad-mini-4gb-android11 (default: brand-model)")
    ap.add_argument("--record", type=Path, help="screen-record the page check to this .mp4")
    ap.add_argument("--resume", action="store_true", help="continue after an ACTION NEEDED stop")
    a = ap.parse_args()

    s = find_device(a.serial)
    state_file = ROOT / "dist" / "device_check" / f"{re.sub(r'[^A-Za-z0-9]+', '_', s)}.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    st = json.loads(state_file.read_text(encoding="utf-8")) if a.resume and state_file.exists() else {"done": []}
    funcs = {"setup": stage_setup, "airplane": stage_airplane, "offline": stage_offline,
             "debugmic": stage_debugmic, "report": stage_report}
    for stage in STAGES:
        if stage in st["done"]:
            continue
        print(f"== {stage}", flush=True)
        try:
            funcs[stage](s, a, st)
        except ActionNeeded as e:
            st.setdefault("actions", []).append(stage)
            state_file.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"\nACTION NEEDED ({stage}): {e}\nThen run the same command again with --resume.")
            sys.exit(2)
        st["done"].append(stage)
        state_file.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
