"""Latency benchmark: recorded clips through the real app, on this device.

    python bench/bench_latency.py                                   # synthetic clips
    python bench/bench_latency.py --clips bench/clips/real/manifest.json --label real

For every clip it posts the audio to /translate/audio exactly as the browser
does (WebM/Opus upload -> ffmpeg -> ASR -> NMT -> TTS), then downloads the reply
audio. The app runs in-process against a throw-away database and EMPTY caches,
so nothing is served from an earlier run.

What is measured, per clip:
  pipeline_ms   upload start -> reply audio fully received. In-process, so it
                excludes Wi-Fi. On a tablet, the browser's own voice-to-voice
                timer (GET /metrics/latency) adds network and audio start-up.
  asr/nmt/tts   the server's stage times
  cer           character error rate of the transcript vs the reference text
The first clip after boot is reported separately as the cold request.

Writes bench/results/<device>_<date>_<label>.csv and .md.
"""

import argparse
import csv
import datetime
import importlib
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from textnorm import normalize_key  # noqa: E402


def device_info():
    info = {"os": f"{platform.system()} {platform.release()}", "python": platform.python_version(),
            "cpu": platform.processor(), "logical_cpus": os.cpu_count()}
    if platform.system() == "Windows":
        def ps(cmd):
            r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                               capture_output=True, text=True)
            return r.stdout.strip()
        info["cpu"] = ps("(Get-CimInstance Win32_Processor | Select-Object -First 1).Name") or info["cpu"]
        info["model"] = ps("(Get-CimInstance Win32_ComputerSystem).Manufacturer + ' ' + "
                           "(Get-CimInstance Win32_ComputerSystem).Model")
        ram = ps("(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory")
        info["ram_gb"] = round(int(ram) / 2**30, 1) if ram.isdigit() else None
    return info


def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")[:40] or "device"


def pct(v, p):
    v = sorted(v)
    return v[max(0, min(len(v) - 1, -(-len(v) * p // 100) - 1))]


def stats(values):
    return {"n": len(values), "median": statistics.median(values),
            "p90": pct(values, 90), "max": max(values)} if values else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", default=str(ROOT / "bench/clips/synthetic/manifest.json"))
    ap.add_argument("--label", default="synthetic")
    ap.add_argument("--limit", type=int, default=0, help="clips per language (0 = all)")
    ap.add_argument("--lang", choices=("hi", "sat"), help="one source language only")
    ap.add_argument("--asr-decoding", action="append", default=[], metavar="LANG=ctc|rnnt",
                    help="override config.ASR_DECODING for this run (e.g. sat=rnnt)")
    ap.add_argument("--asr-trim", action="append", default=[], metavar="LANG=on|off",
                    help="override config.ASR_TRIM_SILENCE for this run (e.g. sat=on)")
    a = ap.parse_args()
    for kv in a.asr_trim:
        lang, v = kv.split("=")
        assert lang in config.ASR_TRIM_SILENCE and v in ("on", "off"), kv
        config.ASR_TRIM_SILENCE[lang] = v == "on"
    for kv in a.asr_decoding:
        lang, mode = kv.split("=")
        assert lang in config.ASR_DECODING and mode in ("ctc", "rnnt"), kv
        config.ASR_DECODING[lang] = mode

    manifest = json.loads(Path(a.clips).read_text(encoding="utf-8"))
    if a.limit:
        manifest = [c for lang in ("hi", "sat") for c in [m for m in manifest if m["lang"] == lang][:a.limit]]
    if a.lang:
        manifest = [c for c in manifest if c["lang"] == a.lang]
    synthetic = any("synthetic" in c.get("kind", "") for c in manifest)

    # Throw-away state: nothing served from an earlier run.
    import database
    tmp = Path(tempfile.mkdtemp(prefix="bench_"))
    database.DB_FILE = tmp / "bench.db"
    config.TTS_OUT_DIR, config.TTS_CACHE_DIR = tmp / "out", tmp / "cache"

    t_boot = time.perf_counter()
    app = importlib.import_module("app")
    boot_s = time.perf_counter() - t_boot
    client = app.app.test_client()

    rows = []
    for i, c in enumerate(manifest):
        direction = "hi-to-sat" if c["lang"] == "hi" else "sat-to-hi"
        with open(ROOT / c["file"], "rb") as f:
            data = {"audio": (f, Path(c["file"]).name), "direction": direction,
                    "mode": "lesson_script", "device_id": "bench"}
            t0 = time.perf_counter()
            r = client.post("/translate/audio", data=data, content_type="multipart/form-data")
        j = r.get_json()
        audio = client.get(j["audio_url"]).data if j.get("audio_url") else b""
        wall = (time.perf_counter() - t0) * 1000
        ref, hyp = normalize_key(c["reference"]), normalize_key(j.get("recognized_text", ""))
        import jiwer
        rows.append({
            "clip": c["file"], "lang": c["lang"], "direction": direction,
            "clip_seconds": c.get("seconds"), "cold": i == 0,
            "pipeline_ms": round(wall, 1),
            "asr_ms": round(j["latency"]["asr"] * 1000, 1), "nmt_ms": round(j["latency"]["nmt"] * 1000, 1),
            "tts_ms": round(j["latency"]["tts"] * 1000, 1), "server_ms": round(j["latency"]["total"] * 1000, 1),
            "source": j.get("source"), "tts_engine": j.get("tts_engine"),
            "audio_bytes": len(audio), "tts_error": j.get("tts_error") or "",
            "cer": round(jiwer.cer(ref, hyp), 3) if ref else "",
            "wer": round(jiwer.wer(ref, hyp), 3) if ref else "",
            "reference": c["reference"], "recognized": j.get("recognized_text", ""),
        })
        print(f"  {i+1:>2}/{len(manifest)} {c['lang']:>3}  {wall:7.0f} ms  "
              f"asr {rows[-1]['asr_ms']:6.0f}  nmt {rows[-1]['nmt_ms']:6.0f}  tts {rows[-1]['tts_ms']:5.0f}  "
              f"{rows[-1]['source']:>8}  cer {rows[-1]['cer']}")

    dev = device_info()
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    name = f"{slug(dev.get('model') or dev['cpu'])}_{date}_{a.label}"
    out_dir = ROOT / "bench" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

    warm = [r for r in rows if not r["cold"]]
    lines = [f"# Latency benchmark: {a.label}", "",
             f"- Date: {date}",
             f"- Device: {dev.get('model', '?')}; {dev['cpu']}; {dev['logical_cpus']} logical CPUs; "
             f"{dev.get('ram_gb', '?')} GB RAM; {dev['os']}; Python {dev['python']}",
             f"- Clips: {len(rows)} ({a.clips})",
             f"- Models: ASR {config.ASR_REVISION[:10]}, NMT {config.NMT_REVISION[:10]} "
             f"(beams={config.NMT_NUM_BEAMS}), TTS {app.pl._voice_model('hindi')}",
             f"- ASR decoding: {config.ASR_DECODING}; trim silence: {config.ASR_TRIM_SILENCE}; "
             f"NMT engine: {app.pl.nmt_backend}",
             f"- Server boot (all models loaded): {boot_s:.1f} s",
             f"- Cold request (first after boot, {rows[0]['lang']}): {rows[0]['pipeline_ms']:.0f} ms",
             "- Caches empty at start; database throw-away.",
             ""]
    if any("public" in c.get("kind", "") for c in manifest):
        lines += ["> **Public dataset, adult speech** (sources and licences per clip in the",
                  f"> manifest). Child speech: NOT MEASURED. Laptop, offline, in-process.", ""]
    if synthetic:
        lines += ["> **Synthetic clips**: Piper reading the lines, not real speech. Timings are",
                  "> representative; the CER column is NOT a measure of ASR accuracy on real",
                  "> teachers or children.", ""]
    lines += ["`pipeline_ms` = upload start to reply audio received, in-process (no Wi-Fi).",
              "Warm requests only (the cold request is excluded). Times in ms.", "",
              "| Direction | n | pipeline median | p90 | max | ASR median | NMT median | TTS median | CER median |",
              "|---|---|---|---|---|---|---|---|---|"]
    for direction in ("hi-to-sat", "sat-to-hi"):
        d = [r for r in warm if r["direction"] == direction]
        if not d:
            continue
        p = stats([r["pipeline_ms"] for r in d])
        med = lambda k: statistics.median([r[k] for r in d])
        cers = [r["cer"] for r in d if r["cer"] != ""]
        lines.append(f"| {direction} | {p['n']} | {p['median']:.0f} | {p['p90']:.0f} | {p['max']:.0f} | "
                     f"{med('asr_ms'):.0f} | {med('nmt_ms'):.0f} | {med('tts_ms'):.0f} | "
                     f"{statistics.median(cers):.3f} |")
    # The same, only for lines the NMT model translated: glossary and cache hits
    # skip translation, so they would flatter a comparison between runs.
    lines += ["", "Lines translated by the model only (no glossary or cache hit):", "",
              "| Direction | n | pipeline median | p90 | max | ASR median | NMT median | TTS median |",
              "|---|---|---|---|---|---|---|---|"]
    for direction in ("hi-to-sat", "sat-to-hi"):
        d = [r for r in warm if r["direction"] == direction and r["source"] == "model"]
        if not d:
            continue
        p = stats([r["pipeline_ms"] for r in d])
        med = lambda k: statistics.median([r[k] for r in d])
        lines.append(f"| {direction} | {p['n']} | {p['median']:.0f} | {p['p90']:.0f} | {p['max']:.0f} | "
                     f"{med('asr_ms'):.0f} | {med('nmt_ms'):.0f} | {med('tts_ms'):.0f} |")
    over = [r for r in warm if r["pipeline_ms"] > 3000]
    lines += ["", f"Requests over 3 s: {len(over)} of {len(warm)}.",
              f"Translations answered by the model: {sum(r['source'] == 'model' for r in warm)} of {len(warm)} "
              "(the rest by the glossary or a cache).",
              f"TTS errors: {sum(bool(r['tts_error']) for r in rows)}.", "",
              f"Raw data: `{name}.csv`."]
    (out_dir / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
