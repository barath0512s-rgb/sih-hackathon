"""The repeated latency runs, every run shown and the median of the runs' p90s.

    python tools/latency_runs.py [--tag hp]

Reads, for tags hp1, hp2, hp3 (or --tag X -> X1, X2, X3):
  bench/results/latency_steps_app_<tag>.csv    from the end of speech, FLEURS Hindi -> Santali:
                                               time to first audio (clause streaming) and full time
  bench/results/*_public_<tag>.csv             upload to reply audio, both directions (bench_latency.py)
Distinct sentences only (the first clip of each; FLEURS has several readers per
sentence), with n (clips) and n_distinct in every row. Nothing is dropped: every
run is listed, and the summary column is the median of the three runs' p90s.
Writes bench/results/latency_<tag>_runs.md.
"""

import argparse
import csv
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RESULTS = ROOT / "bench" / "results"
STEP_BINS = ((0, 11), (12, 17), (18, 23), (24, 999))
SAT_BINS = ((0, 10), (11, 17), (18, 999))


DEFINITIONS = [
    "**Definitions.** Neither measure includes the endpointing wait: the silence endpoint (500 ms, "
    "1000 ms after 2.5 s of speech) is a setting, off by default; with it on, add at least that wait. "
    "Neither includes Wi-Fi or the browser starting playback.",
    "- **From the end of speech** (`bench/latency_steps.py`, Hindi -> Santali): starts when the recorded "
    "audio, already a WAV file, is handed to speech recognition in the same process. **Full time** stops "
    "when the Santali audio for the whole utterance is written (not streamed). **Time to first audio** "
    "stops when the first clause chunk's audio is written (streamed; computed for every clip, although "
    "the app streams only utterances of 18+ words). **Time to last audio**: the last chunk's audio. "
    "For each clip the benchmark runs the whole path and then the streamed path, and goes straight on "
    "to the next clip.",
    "- **Upload to reply audio** (`bench/bench_latency.py`, both directions): starts when the request with "
    "the audio file is sent to the app in the same process (Flask test client, no network); includes "
    "saving the upload, re-encoding it with ffmpeg, speech recognition, the translation layers "
    "(teacher, glossary, cache, model), synthesis and downloading the reply audio; stops when the reply "
    "audio is received. Whole utterance, not streamed. One request after another.",
    "- **Why the end-of-speech full time has the longer tail (p90 3.67 vs 2.38 s, medians 2.11 vs 2.03 s "
    "in run 3): an explanation, partly supported, not a result.** The medians agree; the tail comes from "
    "speech recognition. In the end-of-speech runs the same six clips were slow every time (ASR median "
    "2.02 s, full 4.17 s); each follows a clip with about twice the usual streaming work (3.5 vs 1.9 s), run "
    "just before with no pause. Re-run after a 1 s idle pause (`bench/results/pause_check.md`), the six "
    "clips took ASR 1.16 s, full 3.13 s (median): the preceding work explains about half the extra time, "
    "not all of it (alone, with only the ASR model loaded, ASR took 0.76 s). So the upload figure may be "
    "closer to a line spoken after a pause, but that is not measured in class.",
    "- **Streaming threshold:** on the saved runs, streaming brings the first sound forward by a median "
    "0.25-0.29 s for 12-17 words but delays the last audio by 0.65-0.70 s; for 18+ words it gains "
    "0.48-0.60 s. The app streams only 18+ words (`config.STREAM_MIN_WORDS = 18`); the data support it.",
    "- Rows with fewer than 10 distinct sentences are marked **small sample**. The headline is the "
    "**<= 17-word** row.",
]
SMALL = 10


def label(name, nd):
    return f"{name} (small sample)" if nd < SMALL else name


def pct(v, p):
    v = sorted(v)
    return v[max(0, min(len(v) - 1, -(-len(v) * p // 100) - 1))]


def span(lo, hi):
    return f"{lo}-{hi}" if hi < 999 else f"{lo}+"


def steps_run(tag):
    """{bin: (n, n_distinct, first_p90_s, full_p90_s)} for one latency_steps run, public only."""
    from bench.latency_steps import distinct_first, read_rows
    rows = read_rows(f"app_{tag}")
    pub_all = [r for r in rows if r["set"] == "public"]
    pub = [r for r in distinct_first(rows) if r["set"] == "public"]
    out = {}
    for name, lo, hi in [("all", 0, 999), ("≤ 17", 0, 17)] + [(span(lo, hi), lo, hi) for lo, hi in STEP_BINS]:
        a = [r for r in pub_all if lo <= r["words"] <= hi]
        d = [r for r in pub if lo <= r["words"] <= hi]
        if d:
            out[name] = (len(a), len(d), pct([r["first_audio_ms"] for r in d], 90) / 1000,
                         pct([r["full_ms"] for r in d], 90) / 1000)
    return out


def v2v_run(tag):
    """{(direction, bin): (n, n_distinct, p90_s)} for one bench_latency public run (warm requests)."""
    from textnorm import normalize_key
    f = sorted(RESULTS.glob(f"*_public_{tag}.csv"))[-1]
    rows = [r for r in csv.DictReader(f.open(encoding="utf-8")) if r["cold"] == "False"]
    seen, dist = set(), []
    for r in rows:
        k = (r["direction"], normalize_key(r["reference"]))
        if k not in seen:
            seen.add(k); dist.append(r)
    out = {}
    for d, bins in (("hi-to-sat", STEP_BINS), ("sat-to-hi", SAT_BINS)):
        head = [("all", 0, 999), ("≤ 17", 0, 17)] if d == "hi-to-sat" else [("all", 0, 999)]
        for name, lo, hi in head + [(span(lo, hi), lo, hi) for lo, hi in bins]:
            w = lambda r: len(r["reference"].split())
            a = [r for r in rows if r["direction"] == d and lo <= w(r) <= hi]
            b = [r for r in dist if r["direction"] == d and lo <= w(r) <= hi]
            if b:
                out[(d, name)] = (len(a), len(b), pct([float(r["pipeline_ms"]) for r in b], 90) / 1000)
    return out, f.name


def report(tag="hp"):
    tags = [f"{tag}{i}" for i in (1, 2, 3)]
    steps = {t: steps_run(t) for t in tags}
    v2v = {t: v2v_run(t) for t in tags}
    med = lambda xs: statistics.median(xs)
    lines = [f"# Latency, three runs ({', '.join(tags)})", "",
             "Laptop on AC power, Windows power mode Best performance, other apps closed (set by the user). "
             "Offline. Every run is listed; the last column is the median of the three runs' p90s. "
             "Distinct sentences only (the first clip of each): n = clips, n_distinct = sentences used.", ""]
    lines += DEFINITIONS + ["",
             "## From the end of speech: FLEURS Hindi -> Santali (`bench/latency_steps.py --backend app`)", "",
             "Time to first audio (clause streaming) and full time (whole utterance voiced), p90 in seconds.", "",
             "| Words | n | n_distinct | " + " | ".join(f"{t}: first / full" for t in tags) +
             " | Median of p90s: first / full |",
             "|---|---|---|" + "---|" * len(tags) + "---|"]
    for name in steps[tags[0]]:
        n, nd = steps[tags[0]][name][:2]
        cells = [f"{steps[t][name][2]:.2f} / {steps[t][name][3]:.2f}" for t in tags]
        lines.append(f"| {label(name, nd)} | {n} | {nd} | " + " | ".join(cells) +
                     f" | **{med([steps[t][name][2] for t in tags]):.2f} / {med([steps[t][name][3] for t in tags]):.2f}** |")
    lines += ["", "Source files: " + ", ".join(f"`latency_steps_app_{t}.csv`" for t in tags), "",
              "## Upload to reply audio, both directions (`bench/bench_latency.py`, public clips)", "",
              "Full time (no streaming in this path), p90 in seconds. Santali clips: IndicVoices validation split "
              "(no public Santali test split); may overlap model-development data. Word bins count the reference "
              "words of the spoken sentence.", "",
              "| Direction | Words | n | n_distinct | " + " | ".join(tags) + " | Median of p90s |",
              "|---|---|---|---|" + "---|" * len(tags) + "---|"]
    for key in v2v[tags[0]][0]:
        n, nd = v2v[tags[0]][0][key][:2]
        cells = [f"{v2v[t][0][key][2]:.2f}" for t in tags]
        lines.append(f"| {key[0]} | {label(key[1], nd)} | {n} | {nd} | " + " | ".join(cells) +
                     f" | **{med([v2v[t][0][key][2] for t in tags]):.2f}** |")
    lines += ["", "Source files: " + ", ".join(f"`{v2v[t][1]}`" for t in tags)]
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tag", default="hp")
    a = ap.parse_args()
    lines = report(a.tag)
    out = RESULTS / f"latency_{a.tag}_runs.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
