"""Phase L3: the browser's endpointing rule, replayed on recorded clips.

    python bench/endpoint_sim.py [--clips bench/clips/public/manifest.json] [--endpoint-ms 500]

The same rule as frontend.html (startVad): 20 ms frames; the first 300 ms set
the noise floor; a frame is speech if its RMS > max(3 x floor, 0.01); after
speech has started, ENDPOINT ms of silence stops the recording.

For each clip it reports:
  wait_ms      from the end of speech (last speech frame) to the automatic stop
               (the endpointing cost added to every reply)
  cut_early    the stop came before the last speech frame of the clip, i.e. a
               pause inside the sentence ended the recording and later words
               were lost
  lost_s       seconds of speech after the early stop
Recorded clips, not a live microphone: the browser's own timing is logged by
the app (/metrics/latency).
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
FRAME_MS, CALIBRATE_MS = 20, 300


def simulate(x, sr, endpoint_ms, long_ms=None, long_after_s=2.5):
    fr = int(sr * FRAME_MS / 1000)
    n = len(x) // fr
    rms = np.sqrt((x[:n * fr].reshape(n, fr) ** 2).mean(1))
    cal = max(1, CALIBRATE_MS // FRAME_MS)
    floor = rms[:cal].mean()
    loud = rms > max(3 * floor, 0.01)
    loud[:cal] = False
    idx = np.flatnonzero(loud)
    if not len(idx):
        return None
    last_speech = idx[-1]
    started, last_loud, first = False, None, None
    for i in range(cal, n):
        if loud[i]:
            started, last_loud = True, i
            first = i if first is None else first
            continue
        # Adaptive rule: a longer wait once the utterance has run past long_after_s.
        need = endpoint_ms
        if long_ms and started and (last_loud - first) * FRAME_MS / 1000 >= long_after_s:
            need = long_ms
        if started and (i - last_loud) * FRAME_MS >= need:
            return {"stop_s": i * FRAME_MS / 1000, "end_s": (last_speech + 1) * FRAME_MS / 1000,
                    "cut_early": bool(last_loud < last_speech),
                    "lost_s": max(0.0, (last_speech - last_loud) * FRAME_MS / 1000),
                    "wait_ms": (i - last_loud) * FRAME_MS}
    # Silence never long enough inside the clip: the stop would come after its end.
    tail = (n - 1 - last_speech) * FRAME_MS
    return {"stop_s": None, "end_s": (last_speech + 1) * FRAME_MS / 1000, "cut_early": False,
            "lost_s": 0.0, "wait_ms": endpoint_ms if tail < endpoint_ms else tail}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clips", default=str(ROOT / "bench/clips/public/manifest.json"))
    ap.add_argument("--endpoint-ms", type=int, nargs="+", default=[500, 700, 1000])
    ap.add_argument("--adaptive", default="500:1000:2.5",
                    help="short_ms:long_ms:after_s, the rule frontend.html uses")
    a = ap.parse_args()
    man = [c for c in json.loads(Path(a.clips).read_text(encoding="utf-8")) if c["lang"] == "hi"]
    lines = [f"# Endpointing replayed on {len(man)} clips ({Path(a.clips).name})", "",
             "Rule as in frontend.html: 20 ms frames, 300 ms calibration, speech = RMS > max(3 x floor, 0.01).",
             "Public dataset, adult read speech (FLEURS) unless the manifest says otherwise. Laptop, offline.", "",
             "| Endpoint silence | Clips cut early (a pause ended the recording) | Speech lost when cut, median | Wait after speech ends |",
             "|---|---|---|---|"]
    sh, lg, af = a.adaptive.split(":")
    rules = [(f"{ep} ms", ep, None, 0) for ep in a.endpoint_ms] + \
            [(f"adaptive: {sh} ms, {lg} ms after {af} s of speech", int(sh), int(lg), float(af))]
    for name, ep, long_ms, after in rules:
        res = []
        for c in man:
            f = ROOT / c["file"]
            if f.suffix != ".wav":
                f = Path(str(f) + "_converted.wav")          # made by the benchmarks (ffmpeg)
            x, sr = sf.read(str(f))
            if x.ndim > 1:
                x = x.mean(1)
            r = simulate(x, sr, ep, long_ms, after)
            if r:
                res.append(r)
        cut = [r for r in res if r["cut_early"]]
        lost = statistics.median([r["lost_s"] for r in cut]) if cut else 0
        waits = sorted(r["wait_ms"] for r in res)
        lines.append(f"| {name} | {len(cut)} of {len(res)} | {lost:.1f} s | median {statistics.median(waits):.0f} ms |")
    out = ROOT / "bench" / "results" / f"endpoint_sim_{Path(a.clips).parent.name}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
