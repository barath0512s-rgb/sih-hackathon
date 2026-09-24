"""Does the first request after the server starts cost extra? (Does warm-up pay?)

    python bench/cold_start.py [--trials 3]

Each trial starts the real app in a fresh process (all models loaded, as in
class) and sends the same recorded clip to /translate/audio three times. The
first request's extra time over the other two is what the first sentence of a
lesson would cost. Writes bench/results/cold_start.md.

Why the whole app and not the ASR model alone: timing a bare model in a script
showed a first call of ~8.5 s, but the app's own start-up already absorbs that
cost, so the bare number does not describe what a teacher waits.
"""

import argparse
import json
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402


def one_trial():
    """Runs in a child process: boot the app, time 3 requests, print JSON."""
    import importlib
    import database
    tmp = Path(tempfile.mkdtemp(prefix="cold_"))
    database.DB_FILE = tmp / "cold.db"
    config.TTS_OUT_DIR, config.TTS_CACHE_DIR = tmp / "out", tmp / "cache"
    app = importlib.import_module("app")
    client = app.app.test_client()
    clip = json.loads((ROOT / "bench/clips/synthetic/manifest.json").read_text(encoding="utf-8"))[0]
    out = []
    for _ in range(3):
        config.TTS_CACHE_DIR = Path(tempfile.mkdtemp(prefix="cold_cache_"))   # never a TTS cache hit
        app.TRANSLATION_CACHE.clear()                                         # never a translation cache hit
        with open(ROOT / clip["file"], "rb") as f:
            t0 = time.perf_counter()
            r = client.post("/translate/audio", content_type="multipart/form-data",
                            data={"audio": (f, "clip.webm"), "direction": "hi-to-sat"})
        j = r.get_json()
        out.append({"ms": (time.perf_counter() - t0) * 1000,
                    "asr": j["latency"]["asr"] * 1000, "nmt": j["latency"]["nmt"] * 1000,
                    "tts": j["latency"]["tts"] * 1000})
    print("TIMES " + json.dumps(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--one", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.one:
        return one_trial()

    rows = []
    for t in range(a.trials):
        r = subprocess.run([sys.executable, __file__, "--one"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=ROOT)
        line = next((l for l in r.stdout.splitlines() if l.startswith("TIMES ")), None)
        if not line:
            raise SystemExit(f"trial {t+1} failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
        times = json.loads(line[6:])
        first, steady = times[0], statistics.median([x["ms"] for x in times[1:]])
        rows.append((first, steady))
        print(f"  trial {t+1}: first {first['ms']:.0f} ms (asr {first['asr']:.0f}, nmt {first['nmt']:.0f}, "
              f"tts {first['tts']:.0f}), later {steady:.0f} ms")

    extra = statistics.median(f["ms"] - s for f, s in rows)
    lines = ["# First request after server start", "",
             f"{a.trials} trials, each a fresh app process with all models loaded; the same "
             f"synthetic Hindi clip sent 3 times, caches cleared before each request. "
             f"ASR decoding {config.ASR_DECODING['hi']}, trim {config.ASR_TRIM_SILENCE['hi']}.", "",
             "| Trial | First request ms | ASR | NMT | TTS | Later requests (median) ms |",
             "|---|---|---|---|---|---|"]
    lines += [f"| {i+1} | {f['ms']:.0f} | {f['asr']:.0f} | {f['nmt']:.0f} | {f['tts']:.0f} | {s:.0f} |"
              for i, (f, s) in enumerate(rows)]
    lines += ["", f"Median extra time on the first request: **{extra:.0f} ms**."]
    (ROOT / "bench/results/cold_start.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
