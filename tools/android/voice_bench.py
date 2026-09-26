"""A1 on a device: on-device voice for lesson lines, measured (debug build).

    python tools/android/voice_bench.py --label emulator-2gb-android9 [--serial emulator-5554]

1. Picks clips from the laptop's A1 tuning set (bench/lesson_match_tune.py; test half
   only): Hindi and Santali lesson lines (the pack's own audio) and non-lesson
   speech (public real clips and near-miss sentences); spoken Santali answers to
   lesson steps (Piper, as the tuning clips) with the expected grade; and lines with
   no pack audio for on-device synthesis.
2. Installs the debug APK, imports the newest content pack and model pack through
   the app's import folder (the same verified import as the file picker), switches
   airplane mode on, pushes the clips and starts VoiceBench.kt (debug only), which
   calls the page's own routes inside the app.
3. Samples PSS every second (app process, WebView renderer) with dumpsys meminfo.
4. Writes bench/results/<label>_<date>_voice.md and .json:
   - parity: the device's transcript equals the laptop's (sherpa-onnx 1.13.8, same
     int8 models) on the same clip;
   - matching on the device: precision and recall on these clips;
   - voice to voice for lesson lines: from the WAV handed to the app to the reply
     with its audio file ready (recognition + matching + audio lookup or
     synthesis). The WebView's playback start is not included. p50 / p90;
   - spoken answers: grade and Hindi feedback audio;
   - on-device synthesis time;
   - peak PSS.
"""

import argparse
import datetime
import glob
import json
import random
import re
import statistics
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "android"))

import config  # noqa: E402
import device_check as dc  # noqa: E402
from lesson_match import canonical  # noqa: E402

PKG = dc.PKG
OUT = ROOT / "dist" / "voice_bench"
LM = ROOT / "dist" / "lesson_match"
EXT = f"/sdcard/Android/data/{PKG}/files"


def pick(seed=20260926):
    rnd = random.Random(seed)
    clips = [c for c in json.loads((LM / "clips.json").read_text(encoding="utf-8"))["clips"] if c["split"] == "test"]
    chosen = []

    def take(pred, n):
        pool = [c for c in clips if pred(c)]
        rnd.shuffle(pool)
        chosen.extend(pool[:n])
    take(lambda c: c["lang"] == "hi" and c["variant"] == "pack audio", 60)
    take(lambda c: c["lang"] == "hi" and c["kind"] == "neg" and c["variant"].startswith("real"), 15)
    take(lambda c: c["lang"] == "hi" and c["kind"] == "neg" and c["variant"].startswith("near-miss"), 15)
    take(lambda c: c["lang"] == "sat" and c["variant"] == "pack audio", 25)
    take(lambda c: c["lang"] == "sat" and c["kind"] == "neg", 15)
    return chosen


def answers():
    """Spoken Santali answers to lesson steps: the first accepted Santali answer (expect green)
    and, for some steps, another step's answer (expect not green). Piper voice, as the tuning clips."""
    import io
    import wave
    import numpy as np
    from piper import PiperVoice
    from translit.olchiki import to_devanagari
    from bench.lesson_match_tune import to16k, write16
    voice = PiperVoice.load(str(config.PIPER_DIR / f"{config.PIPER_VOICES['hindi']}.onnx"))
    pack = sorted(glob.glob(str(ROOT / "dist" / "packs" / "content-pack-*.zip")))[-1]
    lessons = json.loads(zipfile.ZipFile(pack).read("lessons.json"))
    steps = []
    for l in lessons:
        for i, s in enumerate(l["lesson"]["steps"]):
            sat = (s.get("accept_answers") or {}).get("sat") or []
            if sat:
                steps.append((l["grade"], l["topic"], i, sat[0], set(sat)))
    rnd = random.Random(7)
    rnd.shuffle(steps)
    out = []
    for k, (g, t, i, ans, ok) in enumerate(steps[:12]):
        tries = [("right", ans, "green")]
        if k < 4:
            wrong = next(x[3] for x in steps if x[3] not in ok and canonical(x[3], "sat") not in {canonical(o, "sat") for o in ok})
            tries.append(("wrong", wrong, "not green"))
        for kind, text, expect in tries:
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                voice.synthesize_wav(to_devanagari(text), wf)
            buf.seek(0)
            with wave.open(buf) as wf:
                x = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768
                sr = wf.getframerate()
            name = f"ans_{g}_{t}_{i}_{kind}.wav"
            write16(OUT / name, to16k(x, sr))
            out.append({"id": name[:-4], "grade": g, "topic": t, "step": i, "file": name, "said": text, "expect": expect})
    return out


def tts_lines():
    import pandas as pd
    conv = pd.read_parquet(ROOT / "data/public/ai4bharat__IN22-Conv/data/train-00000-of-00001.parquet")
    sat = [s for s in conv["sat_Olck"].tolist()[300:310]]
    return [{"text": s, "lang": "sat"} for s in sat] + \
           [{"text": s, "lang": "hi"} for s in conv["hin_Deva"].tolist()[300:305]]


def pctl(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    f = int(k)
    return xs[f] + (xs[min(f + 1, len(xs) - 1)] - xs[f]) * (k - f)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--serial")
    ap.add_argument("--label", required=True)
    ap.add_argument("--device-label", required=True, help='e.g. "emulator, 2 GB, Android 9, 2 threads"')
    ap.add_argument("--skip-install", action="store_true")
    a = ap.parse_args()
    s = dc.find_device(a.serial)
    OUT.mkdir(parents=True, exist_ok=True)
    import shutil
    clips = pick()
    for c in clips:
        shutil.copyfile(LM / "clips" / f"{c['id']}.wav", OUT / f"{c['id']}.wav")
    man = {"clips": [{"id": c["id"], "lang": c["lang"], "file": f"{c['id']}.wav"} for c in clips],
           "answers": answers(), "tts": tts_lines()}
    (OUT / "manifest.json").write_text(json.dumps(man, ensure_ascii=False), encoding="utf-8")
    info = dc.device_info(s)

    if not a.skip_install:
        dc.install(s, ROOT / "android/app/build/outputs/apk/debug/app-debug.apk", replace=True)
        dc.grant_mic(s)
        dc.adb(s, "shell", "am", "force-stop", PKG)
        dc.adb(s, "shell", "am", "start", "-n", f"{PKG}/.MainActivity")
        time.sleep(4)
        dc.adb(s, "shell", "mkdir", "-p", f"{EXT}/import")
        for pat in ("content-pack-*.zip", "model-pack-*.zip"):
            z = sorted(glob.glob(str(ROOT / "dist" / "packs" / pat)))[-1]
            t0 = time.time()
            dc.adb(s, "push", z, f"{EXT}/import/{Path(z).name}", timeout=1200)
            dc.adb(s, "shell", "am", "start", "-n", f"{PKG}/.MainActivity")      # onResume imports the folder
            while dc.adb(s, "shell", "ls", f"{EXT}/import/", check=False).strip():
                if time.time() - t0 > 1800:
                    raise SystemExit("import did not finish in 30 min")
                time.sleep(3)
            print("imported", Path(z).name, f"{time.time() - t0:.0f} s", flush=True)
    # airplane mode (Android 9 allows adb to switch it)
    dc.adb(s, "shell", "settings", "put", "global", "airplane_mode_on", "1", check=False)
    dc.adb(s, "shell", "am", "broadcast", "-a", "android.intent.action.AIRPLANE_MODE", "--ez", "state", "true", check=False)
    airplane = dc.airplane_on(s)

    dc.adb(s, "shell", "rm", "-rf", f"{EXT}/bench")
    dc.adb(s, "shell", "mkdir", "-p", f"{EXT}/bench")
    dc.adb(s, "push", str(OUT) + "/.", f"{EXT}/bench/", timeout=600)
    dc.adb(s, "logcat", "-c", check=False)
    sampler = dc.PssSampler(s)
    sampler.start()
    t0 = time.time()
    dc.adb(s, "shell", "am", "start", "-n", f"{PKG}/.MainActivity", "--es", "voice_bench", "manifest.json")
    while "voice_bench done" not in dc.adb(s, "logcat", "-d", "-s", "tablet:I", check=False):
        if time.time() - t0 > 3600:
            raise SystemExit("bench did not finish in 60 min")
        if not dc.app_alive(s):
            raise SystemExit("the app died during the bench: " + dc.adb(s, "logcat", "-d", "-t", "60", check=False)[-2000:])
        time.sleep(5)
    sampler.running = False
    res_path = OUT / "result.json"
    dc.adb(s, "pull", f"{EXT}/bench/result.json", str(res_path))
    res = json.loads(res_path.read_text(encoding="utf-8"))
    report(a, info, clips, man, res, sampler, airplane)


def report(a, info, clips, man, res, sampler, airplane):
    lap = json.loads((ROOT / "bench/results/lesson_match_transcripts_laptop.json").read_text(encoding="utf-8"))["transcripts"]
    by = {c["id"]: c for c in clips}
    rows = []
    for r in res["clips"]:
        c = by[r["id"]]
        m = r.get("match") or {}
        same_line = c["line"] is not None and m.get("line") is not None and \
            canonical(m["line"], c["lang"]) == canonical(c["line"], c["lang"])
        rows.append(dict(c, device=r["recognized_text"], laptop=lap[c["id"]], ms=r["ms"], matched=bool(m.get("matched")),
                         correct=bool(m.get("matched")) and same_line, audio=r.get("audio_url"), engine=r.get("tts_engine")))
    date = datetime.date.today().isoformat()
    L = [f"# A1 on-device voice for lesson lines: {a.device_label}", "",
         f"- Device (read from it): {info['manufacturer']} {info['model']}, Android {info['android']} (SDK {info['sdk']}), "
         f"{info['abi']}, RAM {info['ram']}, {info['cores']} cores. Airplane mode: {'on' if airplane else 'OFF'}.",
         "- Build: **debug APK** (the benchmark hook exists only in debug builds; same native libraries and models as release). "
         f"sherpa-onnx 1.13.8, int8 IndicConformer 120M (Hindi CTC, Santali transducer), {config.ON_DEVICE_ASR_THREADS} threads, "
         "one recogniser loaded at a time; Piper hi voice for synthesis.",
         f"- Thresholds: {config.LESSON_MATCH_THRESHOLD} (bench/results/lesson_match.md). Clips: the test half of the laptop "
         "tuning set (synthetic lesson lines in the pack's own audio; non-lesson: public real clips and near-miss sentences).",
         "- Laptop: nothing else running during the run (the emulator itself runs on the laptop's CPU).", ""]
    for lang in ("hi", "sat"):
        R = [r for r in rows if r["lang"] == lang]
        same = sum(r["device"] == r["laptop"] for r in R)
        acc = [r for r in R if r["matched"]]
        pos = [r for r in R if r["kind"] == "pos"]
        cor = [r for r in R if r["correct"]]
        name = "Hindi lesson line → Santali" if lang == "hi" else "Santali line → Hindi"
        L += [f"## {name}", "",
              f"- **Parity with the laptop:** device transcript identical to the laptop's on **{same} of {len(R)}** clips.",
              f"- Matching on the device: precision **{(len(cor) / len(acc)) if acc else 1:.3f}** ({len(cor)} of {len(acc)} accepted), "
              f"recall **{len(cor) / len(pos) if pos else 0:.3f}** ({len(cor)} of {len(pos)} lesson lines); "
              f"non-lesson clips accepted: {sum(r['matched'] for r in R if r['kind'] == 'neg')} of {sum(r['kind'] == 'neg' for r in R)}.", ""]
        ms = [r["ms"] for r in R if r["correct"] and r["audio"]]
        if ms:
            L += [f"- **Voice to voice, matched lesson lines (n = {len(ms)}): p50 {pctl(ms, .5) / 1000:.2f} s, p90 "
                  f"{pctl(ms, .9) / 1000:.2f} s** (WAV handed to the app → reply with its audio file ready; playback start not "
                  f"included). Audio from: {sorted({r['engine'] for r in R if r['correct']})}.", ""]
        diff = [r for r in R if r["device"] != r["laptop"]][:5]
        if diff:
            L += ["| Clip | Laptop | Device |", "|---|---|---|"] + [f"| {r['id']} | {r['laptop']} | {r['device']} |" for r in diff] + [""]
    A = res.get("answers", [])
    if A:
        ok = sum((r["signal"] == "green") == (r["expect"] == "green") for r in A)
        fb = sum(bool(r.get("audio_url")) for r in A)
        ms = [r["ms"] for r in A]
        L += ["## Spoken Santali answers (child → grade → Hindi feedback)", "",
              f"- Graded as expected: **{ok} of {len(A)}** (right answers green, wrong answers not green). Hindi feedback "
              f"audio returned: {fb} of {len(A)}. Time per answer (recognition + grading + feedback audio): p50 "
              f"{pctl(ms, .5) / 1000:.2f} s, p90 {pctl(ms, .9) / 1000:.2f} s (n = {len(ms)}; the first includes loading the Santali model).", "",
              "| Answer | Said | Heard | Grade | Expected |", "|---|---|---|---|---|"]
        L += [f"| {r['id']} | {next(x['said'] for x in man['answers'] if x['id'] == r['id'])} | {r['transcript']} | {r['signal']} | {r['expect']} |" for r in A]
        L.append("")
    T = res.get("tts", [])
    if T:
        for lang in ("sat", "hi"):
            ms = [r["ms"] for r in T if r["lang"] == lang and r["tts_engine"] == "device"]
            if ms:
                L.append(f"- On-device synthesis, {lang} lines with no pack audio (n = {len(ms)}): p50 {pctl(ms, .5) / 1000:.2f} s, "
                         f"p90 {pctl(ms, .9) / 1000:.2f} s (the first includes loading the voice).")
        L.append("")
    L += [f"## Memory", "",
          f"- **Peak PSS (dumpsys meminfo every 1 s, {sampler.samples} samples): app {sampler.peak / 1024:.0f} MB, WebView "
          f"renderer {sampler.peak_renderer / 1024:.0f} MB, sum {sampler.peak_sum / 1024:.0f} MB**; in-app peak "
          f"(Debug.getPss after each call) {res.get('peak_app_pss_kb', 0) / 1024:.0f} MB. During the run the recogniser "
          "for one language and the synthesis voice are loaded.", ""]
    date = datetime.date.today().isoformat()
    base = ROOT / "bench" / "results" / f"{a.label}_{date}_voice"
    base.with_suffix(".md").write_text("\n".join(L), encoding="utf-8", newline="\n")
    base.with_suffix(".json").write_text(json.dumps({"device": info, "device_label": a.device_label, "rows": rows,
                                                    "answers": A, "tts": T, "peak_pss_kb": {"app": sampler.peak,
                                                    "renderer": sampler.peak_renderer, "sum": sampler.peak_sum},
                                                    "airplane": airplane}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
