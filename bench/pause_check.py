"""Check of the latency explanation: are the end-of-speech benchmark's six slow clips
slow by themselves, or because of the streaming work run just before them?

    python bench/pause_check.py

The six clips that were slow in every run of bench/latency_steps.py (hp1-hp3) go
through the same whole-utterance path, with the app's settings (speech
recognition, `app` translation engine, Piper synthesis into an empty cache),
each after a 1 s idle pause and no heavy clip before it. Their times are set
beside what the same clips took in the three saved runs.
Writes bench/results/pause_check.md.
"""

import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from bench.latency_steps import make_backend, read_rows  # noqa: E402

SLOW = ["00015", "00033", "00034", "00050", "00053", "00060"]


def main():
    import pipeline
    pl = pipeline.VaaniSetuPipeline()
    translate, desc = make_backend(pl, "app")
    tmp = Path(tempfile.mkdtemp(prefix="pause_"))
    config.TTS_CACHE_DIR = tmp / "tts_cache"                 # empty: every clip is really synthesised
    saved = {i: {r["clip"]: r for r in read_rows(f"app_hp{i}") if r["set"] == "public"} for i in (1, 2, 3)}
    clips = [c for c in saved[1] if any(f"_{s}_" in c for s in SLOW)]
    # Warm every engine, then let the machine settle.
    w = pl._to_wav(str(ROOT / clips[0]))
    pl._transcribe(w, "hi"); translate("नमस्ते बच्चो"); pl.santali_tts("ᱡᱚᱦᱟᱨ", str(tmp / "warm.wav"))
    rows = []
    for clip in clips:
        wav = pl._to_wav(str(ROOT / clip))
        time.sleep(1.0)                                      # the pause
        t0 = time.perf_counter(); hyp = pl._transcribe(wav, "hi"); asr = (time.perf_counter() - t0) * 1000
        t0 = time.perf_counter(); sat = translate(hyp); nmt = (time.perf_counter() - t0) * 1000
        t0 = time.perf_counter(); pl.santali_tts(sat, str(tmp / "whole.wav")); tts = (time.perf_counter() - t0) * 1000
        before = [saved[i][clip] for i in (1, 2, 3)]
        rows.append((clip, asr, nmt, tts, asr + nmt + tts,
                     [b["asr_ms"] for b in before], [b["full_ms"] for b in before]))
        print(f"{clip}: asr {asr:.0f} nmt {nmt:.0f} tts {tts:.0f} full {asr + nmt + tts:.0f} ms | "
              f"in the runs: asr {[b['asr_ms'] for b in before]} full {[b['full_ms'] for b in before]}", flush=True)
    lines = ["# Pause check: the six slow clips after a 1 s idle pause", "",
             f"- Engine: {desc}. Same path as `bench/latency_steps.py` full time (from the end of speech, whole "
             "utterance, not streamed), app settings, empty voice cache; each clip after a 1 s pause, no heavy clip "
             "before it. Laptop, offline, AC power, Best performance mode.",
             "- Compared with the same clips in the three saved runs (`latency_steps_app_hp1-3.csv`), where each "
             "followed another clip's streaming work with no pause.", "",
             "| Clip | After a 1 s pause: ASR / full ms | In the runs: ASR ms (hp1, hp2, hp3) | In the runs: full ms |",
             "|---|---|---|---|"]
    for clip, asr, nmt, tts, full, a3, f3 in rows:
        lines.append(f"| {Path(clip).stem} | {asr:.0f} / {full:.0f} | {', '.join(map(str, a3))} | {', '.join(map(str, f3))} |")
    m = lambda xs: statistics.median(xs)
    lines += ["", f"Median over the six clips: after a pause ASR {m([r[1] for r in rows]):.0f} ms, full "
              f"{m([r[4] for r in rows]):.0f} ms; in the runs ASR {m([x for r in rows for x in r[5]]):.0f} ms, full "
              f"{m([x for r in rows for x in r[6]]):.0f} ms."]
    (ROOT / "bench" / "results" / "pause_check.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
