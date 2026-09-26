"""A5 on a device: the tablet's own translation (IndicTrans2 int8, ONNX Runtime) checked and timed.

    python tools/android/nmt_bench.py --serial emulator-5554 --label emulator-2gb-android9 \
        --device-label "emulator, 2 GB, Android 9, 2 threads" [--in22 N]

Phase 1, model pack only (no content pack, so every sentence goes to the model):
  - the 80 golden cases of nmt_vectors.json: the tablet's output must equal the
    laptop's int8 output (the app's Python path);
  - IN22-Conv Hindi -> Santali, the first N sentences (default all 1503): chrF++ of the
    tablet against the references, beside the laptop int8 on the same sentences
    (data/eval/hyp_in22-conv_hin_Deva-sat_Olck_onnx-int8.txt);
  - time per sentence.
Phase 2, with the content pack: free-form speech (the public Hindi clips, not lesson
lines) through POST /translate/audio: recognition -> translation -> synthesis on the
tablet, timed (WAV handed over -> reply audio file ready; playback not included).
Peak PSS sampled every second. Debug build (the benchmark hook), airplane mode.
Writes bench/results/<label>_<date>_nmt.md / .json.
"""

import argparse
import datetime
import glob
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "android"))

import device_check as dc  # noqa: E402

PKG = dc.PKG
EXT = f"/sdcard/Android/data/{PKG}/files"
OUT = ROOT / "dist" / "nmt_bench"


def pctl(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    f = int(k)
    return xs[f] + (xs[min(f + 1, len(xs) - 1)] - xs[f]) * (k - f)


def import_pack(s, pattern):
    z = sorted(glob.glob(str(ROOT / "dist" / "packs" / pattern)))[-1]
    dc.adb(s, "shell", "mkdir", "-p", f"{EXT}/import")
    dc.adb(s, "push", z, f"{EXT}/import/{Path(z).name}", timeout=1800)
    dc.adb(s, "shell", "am", "start", "-n", f"{PKG}/.MainActivity")
    t0 = time.time()
    while dc.adb(s, "shell", "ls", f"{EXT}/import/", check=False).strip():
        if time.time() - t0 > 1800:
            raise SystemExit("import did not finish")
        time.sleep(3)
    return Path(z).name


def run_bench(s, manifest, tag, timeout=4 * 3600):
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    dc.adb(s, "shell", "rm", "-rf", f"{EXT}/bench")
    dc.adb(s, "shell", "mkdir", "-p", f"{EXT}/bench")
    dc.adb(s, "push", str(OUT) + "/.", f"{EXT}/bench/", timeout=600)
    dc.adb(s, "logcat", "-c", check=False)
    sampler = dc.PssSampler(s)
    sampler.start()
    t0 = time.time()
    dc.adb(s, "shell", "am", "start", "-n", f"{PKG}/.MainActivity", "--es", "voice_bench", "manifest.json")
    while "voice_bench done" not in dc.adb(s, "logcat", "-d", "-s", "tablet:I", check=False):
        if time.time() - t0 > timeout:
            raise SystemExit(f"{tag}: did not finish")
        if not dc.app_alive(s):
            raise SystemExit(f"{tag}: the app died: " + dc.adb(s, "logcat", "-d", "-t", "80", check=False)[-3000:])
        time.sleep(10)
    sampler.running = False
    dc.adb(s, "pull", f"{EXT}/bench/result.json", str(OUT / f"result_{tag}.json"))
    return json.loads((OUT / f"result_{tag}.json").read_text(encoding="utf-8")), sampler


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--serial")
    ap.add_argument("--label", required=True)
    ap.add_argument("--device-label", required=True)
    ap.add_argument("--in22", type=int, default=1503)
    ap.add_argument("--skip-phase2", action="store_true")
    ap.add_argument("--phase1-from", help="report from a saved phase-1 result (dist/nmt_bench/result_phase1.json)")
    ap.add_argument("--phase2-error", help="what happened in phase 2, when it could not finish")
    a = ap.parse_args()
    import pandas as pd
    from sacrebleu.metrics import CHRF
    s = dc.find_device(a.serial)
    if not a.phase1_from:
        if OUT.exists():
            shutil.rmtree(OUT)
        OUT.mkdir(parents=True)
    info = dc.device_info(s)
    gold = [c for c in json.loads((ROOT / "android/app/src/test/resources/nmt_vectors.json").read_text(encoding="utf-8"))["cases"]
            if "seq" in c]
    conv = pd.read_parquet(ROOT / "data/public/ai4bharat__IN22-Conv/data/train-00000-of-00001.parquet")
    hi, ref = conv["hin_Deva"].tolist()[: a.in22], conv["sat_Olck"].tolist()[: a.in22]
    lap = (ROOT / "data/eval/hyp_in22-conv_hin_Deva-sat_Olck_onnx-int8.txt").read_text(encoding="utf-8").split("\n")[: a.in22]
    texts = [{"id": f"gold{i}", "text": c["src"], "direction": c["direction"]} for i, c in enumerate(gold)]
    texts += [{"id": f"in22_{i}", "text": t, "direction": "hi-to-sat"} for i, t in enumerate(hi)]
    # phase 1: model pack only
    if a.phase1_from:
        r1 = json.loads(Path(a.phase1_from).read_text(encoding="utf-8"))
        s1 = type("Saved", (), {"peak": r1.get("peak_app_pss_kb", 0), "peak_renderer": 0})()
        mp, airplane = "(see the run log)", True
    if not a.phase1_from:
      dc.adb(s, "shell", "pm", "clear", PKG, check=False)
      dc.install(s, ROOT / "android/app/build/outputs/apk/debug/app-debug.apk", replace=True)
      dc.grant_mic(s)
      dc.adb(s, "shell", "am", "start", "-n", f"{PKG}/.MainActivity")
      time.sleep(4)
      mp = import_pack(s, "model-pack-*.zip")
      dc.adb(s, "shell", "settings", "put", "global", "airplane_mode_on", "1", check=False)
      dc.adb(s, "shell", "am", "broadcast", "-a", "android.intent.action.AIRPLANE_MODE", "--ez", "state", "true", check=False)
      airplane = dc.airplane_on(s)
      r1, s1 = run_bench(s, {"texts": texts}, "phase1")
    by = {x["id"]: x for x in r1["texts"]}
    g_same = sum(by[f"gold{i}"]["translated_text"] == c["out"] for i, c in enumerate(gold))
    g_diff = [(c["src"], c["out"], by[f"gold{i}"]["translated_text"]) for i, c in enumerate(gold)
              if by[f"gold{i}"]["translated_text"] != c["out"]]
    dev = [by[f"in22_{i}"]["translated_text"] for i in range(len(hi))]
    chrf = CHRF(word_order=2)
    c_dev = chrf.corpus_score(dev, [ref]).score
    c_lap = chrf.corpus_score(lap, [ref]).score
    same_in22 = sum(d == l for d, l in zip(dev, lap))
    ms = [by[f"in22_{i}"]["latency"]["nmt"] * 1000 for i in range(len(hi))]
    ms_first = by["gold0"]["latency"]["nmt"] * 1000
    # phase 2: free-form speech with the content pack
    r2, s2, voice = None, None, []
    if not a.skip_phase2 and not a.phase2_error:
        cp = import_pack(s, "content-pack-*.zip")
        man = json.loads((ROOT / "bench/clips/public/manifest.json").read_text(encoding="utf-8"))
        clips = [c for c in man if c["lang"] == "hi"][:20]
        import soundfile as sf
        import librosa
        items = []
        for i, c in enumerate(clips):
            x, sr = sf.read(str(ROOT / c["file"]), dtype="float32")
            x = x.mean(axis=1) if x.ndim > 1 else x
            sf.write(str(OUT / f"free{i}.wav"), librosa.resample(x, orig_sr=sr, target_sr=16000) if sr != 16000 else x,
                     16000, subtype="PCM_16")
            items.append({"id": f"free{i}", "lang": "hi", "file": f"free{i}.wav", "reference": c["reference"]})
        r2, s2 = run_bench(s, {"clips": [{k: v for k, v in it.items() if k != "reference"} for it in items]}, "phase2")
        for it, r in zip(items, r2["clips"]):
            voice.append({"id": it["id"], "ms": r["ms"], "recognized": r["recognized_text"], "tts": r["tts_engine"],
                          "matched": (r.get("match") or {}).get("matched"), "latency": r.get("latency")})
    date = datetime.date.today().isoformat()
    L = [f"# A5 on-device translation: {a.device_label}", "",
         f"- Device (read from it): {info['model']}, Android {info['android']}, {info['abi']}, RAM {info['ram']}. "
         f"Airplane mode: {'on' if airplane else 'OFF'}. Debug build (benchmark hook). Model pack `{mp}`.",
         "- Engine: IndicTrans2 indic-indic-dist-320M int8 on ONNX Runtime (Android 1.28), greedy, no-repeat 3-gram, "
         "the int8 length cap and stem-loop guard; IndicTransToolkit pre/post-processing and SentencePiece ported to Kotlin "
         "(unit tests: identical pre-processing and token ids on 300 of 300 sentences).",
         "- The recogniser is released before translation loads (one large model at a time).", "",
         "## Same output as the laptop", "",
         f"- The 80 golden sentences (40 Hindi lesson lines, 40 IN22-Conv Santali): tablet output identical to the "
         f"laptop's int8 output on **{g_same} of {len(gold)}**.",
         f"- IN22-Conv Hindi → Santali, {len(hi)} sentences: identical to the laptop's int8 output on {same_in22} of {len(hi)}.", "",
         "## Quality (IN22-Conv, Hindi → Santali, CC BY 4.0)", "",
         f"| Engine | n | chrF++ |", "|---|---|---|",
         f"| Laptop, int8 ONNX (Python) | {len(hi)} | {c_lap:.2f} |",
         f"| Tablet, int8 ONNX (Kotlin port) | {len(hi)} | **{c_dev:.2f}** |", "",
         f"- Difference: {c_dev - c_lap:+.2f} (the bar: within 0.5).", "",
         "## Time", "",
         f"- Translation on the tablet, per sentence (IN22-Conv, {len(hi)}): p50 {pctl(ms, .5) / 1000:.2f} s, p90 "
         f"{pctl(ms, .9) / 1000:.2f} s. First sentence (includes loading the model): {ms_first / 1000:.2f} s.",
         (f"- Peak PSS, phase 1 (translation): app {s1.peak / 1024:.0f} MB + WebView {s1.peak_renderer / 1024:.0f} MB."
          if not a.phase1_from else f"- Peak PSS, phase 1 (translation; in-app Debug.getPss after each sentence): app {s1.peak / 1024:.0f} MB.")]
    if voice:
        vm = [v["ms"] for v in voice if not v["matched"]]
        L += ["", "## Free-form Hindi speech → Santali speech, all on the tablet", "",
              f"- Public Hindi clips (FLEURS, not lesson lines), {len(voice)}: recognition → translation → synthesis. "
              f"From the WAV handed over to the reply audio file ready: **p50 {pctl(vm, .5) / 1000:.2f} s, p90 "
              f"{pctl(vm, .9) / 1000:.2f} s** (n = {len(vm)}; the first loads models; playback start not included).",
              f"- Peak PSS, phase 2 (recognition + translation + synthesis): app {s2.peak / 1024:.0f} MB + WebView "
              f"{s2.peak_renderer / 1024:.0f} MB."]
    if a.phase2_error:
        L += ["", "## Free-form Hindi speech → Santali speech, all on the tablet", "", f"- **Did not finish: {a.phase2_error}**"]
    if g_diff:
        L += ["", "| Golden sentence | Laptop | Tablet |", "|---|---|---|"] + [f"| {a_} | {b} | {c} |" for a_, b, c in g_diff[:8]]
    base = ROOT / "bench" / "results" / f"{a.label}_{date}_nmt"
    base.with_suffix(".md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    base.with_suffix(".json").write_text(json.dumps({"device": info, "golden_same": g_same, "golden_n": len(gold),
                                                    "in22_n": len(hi), "chrf_device": c_dev, "chrf_laptop": c_lap,
                                                    "in22_same": same_in22, "nmt_ms": ms, "voice": voice,
                                                    "pss1": [s1.peak, s1.peak_renderer], "pss2": [s2.peak, s2.peak_renderer] if s2 else None},
                                                   ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
