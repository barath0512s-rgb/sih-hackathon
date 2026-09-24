"""Print the numbers the deck and README may use, each with its source.

    python tools/deck_numbers.py

Nothing here is typed in by hand. Every value is read from a results file in
bench/, from the repository, or from the model files on disk. Anything that has
no such source is printed as NOT MEASURED.

Every measured value is from the laptop, running offline. Nothing here was
measured on a tablet.
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from bench.bench_latency import stats  # noqa: E402

RESULTS = ROOT / "bench" / "results"
NM = "NOT MEASURED"
LAPTOP = "laptop, offline"


def sec(x):
    """Seconds to 2 decimals, rounded half up once, from the raw value (a
    median of 1.5745 s is 1.57, not 1.58 via a rounded 1575 ms)."""
    from decimal import ROUND_HALF_UP, Decimal
    return str(Decimal(str(round(x, 6))).quantize(Decimal("0.01"), ROUND_HALF_UP))


def out(name, value, source):
    print(f"  {name:<44} {value:<28} [{source}]")


def latest_runs():
    """{label: (csv path, md path)} for the newest run of each label."""
    runs = {}
    for f in sorted(RESULTS.glob("*_????-??-??_*.csv")):
        m = re.match(r"(.+)_(\d{4}-\d{2}-\d{2})_(.+)\.csv$", f.name)
        if not m:
            continue
        date, label = m.group(2), m.group(3)
        if label not in runs or date >= runs[label][0]:
            runs[label] = (date, f, f.with_suffix(".md"))
    return {k: (v[1], v[2]) for k, v in runs.items()}


def latency(label, csv_path, md_path):
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    warm = [r for r in rows if r["cold"] == "False"]
    src = f"bench/results/{csv_path.name}"
    kind = "synthetic clips" if "synthetic" in label else "real clips" if "real" in label else label
    print(f"\nVoice to voice, {kind} (run '{label}', {LAPTOP}; excludes Wi-Fi)")
    for d in ("hi-to-sat", "sat-to-hi"):
        s = stats([float(r["pipeline_ms"]) / 1000 for r in warm if r["direction"] == d])
        if s:
            out(f"{d} median / p90 / max",
                f"{sec(s['median'])} / {sec(s['p90'])} / {sec(s['max'])} s (n={s['n']})", src)
    over = sum(float(r["pipeline_ms"]) > 3000 for r in warm)
    out("requests over 3 s", f"{over} of {len(warm)}", src)
    gl = sum(r["source"] == "glossary" for r in warm)
    out("answered by the verified sentence glossary", f"{gl} of {len(warm)}", src)
    errs = sum(bool(r["tts_error"]) for r in warm)
    out("speech (TTS) failures", f"{errs} of {len(warm)}", src)
    if md_path.exists():
        m = re.search(r"Server boot \(all models loaded\): ([\d.]+) s", md_path.read_text(encoding="utf-8"))
        out("server boot, all models loaded", f"{m.group(1)} s" if m else NM, f"bench/results/{md_path.name}")
    if "synthetic" in label:
        print("  (Synthetic clips are Piper reading the lines. Their CER is NOT an ASR accuracy figure.)")


def size(path):
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def main():
    print(f"{config.APP_NAME}: deck numbers. Values come from files in this repo; "
          f"measurements are '{LAPTOP}'.")

    runs = latest_runs()
    if not runs:
        print(f"\nVoice to voice: {NM} (no bench/results/*.csv)")
    for label in sorted(runs):
        if label.endswith("baseline"):
            continue
        latency(label, *runs[label])
    if not any("real" in k for k in runs):
        print(f"\nVoice to voice, real teacher/child recordings: {NM} (bench/clips/real/ has no run yet)")

    print("\nOn a 2 GB RAM, Android 9+ tablet")
    out("voice to voice", NM, "no tablet; work package 4")
    out("peak RAM", NM, "no tablet; work package 4")
    out("tablet model and Android version", NM, "no tablet yet")
    print(f"\nLaptop resources")
    out("peak RAM of the server", NM, "no script measures it yet")

    print(f"\nModel files on disk")
    asr, nmt = config.ASR_DIR, config.NMT_DIR
    voices = [config.PIPER_DIR / f"{v}.onnx" for v in
              {config.PIPER_VOICES["hindi"], config.PIPER_VOICES[f"santali_{config.SANTALI_TTS_SCRIPT}"]}]
    for name, p in (("ASR (IndicConformer 600M, ONNX)", asr), ("NMT (IndicTrans2 320M)", nmt)):
        out(name, f"{size(p) / 1e9:.2f} GB" if p.exists() else "missing", str(p.relative_to(ROOT)))
    out("TTS voices in use", f"{sum(size(v) for v in voices if v.exists()) / 1e6:.0f} MB",
        ", ".join(v.name for v in voices))
    import json
    man = json.loads((ROOT / "model_manifest.json").read_text(encoding="utf-8"))
    files = man.get("files", man)
    total = sum(f.get("size", 0) for f in (files.values() if isinstance(files, dict) else files))
    out("files pinned in model_manifest.json", f"{len(files)} files, {total / 1e9:.2f} GB", "model_manifest.json")

    print("\nContent")
    import database
    from lesson_engine import get_all_lessons, get_lesson
    metas = get_all_lessons()
    lessons = [get_lesson(m["grade"], m["topic"]) for m in metas]
    src = f"lesson_engine.py + {Path(database.DB_FILE).name} (imported)"
    n_imp = sum(m["imported"] for m in metas)
    out("lessons (built-in + imported)", f"{len(lessons)} ({len(lessons) - n_imp} + {n_imp})", src)
    by = {}
    for m in metas:
        by.setdefault(("Balvatika" if m["grade"] == "0" else "G" + m["grade"], m["domain"]), 0)
        by[("Balvatika" if m["grade"] == "0" else "G" + m["grade"], m["domain"])] += 1
    out("lessons by grade and domain",
        ", ".join(f"{g} {d[:3]} {n}" for (g, d), n in sorted(by.items())), src)
    out("lessons with a NIPUN Lakshya tag", str(sum(bool(l.get("lakshya_ids")) for l in lessons)), src)
    out("lessons reviewed by a native speaker",
        str(sum(l.get("review_status") == "native_reviewed" for l in lessons)), src + " review_status")
    out("flashcard words in lessons", str(sum(len(l.get("flashcards", [])) for l in lessons)), src)
    from education_glossary import VERIFIED_SENTENCES_HI_SAT
    out("sentence glossary entries", str(len(VERIFIED_SENTENCES_HI_SAT)), "education_glossary.py")
    import json as _j
    vec = _j.loads((ROOT / "tests" / "data" / "olchiki_vectors.json").read_text(encoding="utf-8"))
    out("transliteration test vectors", str(len(vec["vectors"])), "tests/data/olchiki_vectors.json")

    print("\nTranslation quality")
    out("chrF++ on held-out sentences", NM, "no held-out set yet; the 33-row CSV is not used")
    out("ASR WER, adult / child, quiet / noisy", NM, "needs real recordings")


if __name__ == "__main__":
    main()
