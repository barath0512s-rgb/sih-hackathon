"""Print the numbers the deck and README may use, each with its source.

    python tools/deck_numbers.py
    python tools/deck_numbers.py --write     # also save to bench/results/deck_numbers.txt

Nothing here is typed in by hand. Every value is read from a results file in
bench/, from the repository, or from the model files on disk. Anything that has
no such source is printed as NOT MEASURED.

Every measured value is from the laptop, running offline. Nothing here was
measured on a tablet.
"""

import csv
import io
import re
import statistics
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
    warm_all = [r for r in rows if r["cold"] == "False"]
    # Distinct sentences per direction (FLEURS has several readers per sentence).
    from textnorm import normalize_key
    seen, warm = set(), []
    for r in warm_all:
        k = (r["direction"], normalize_key(r["reference"]))
        if k not in seen:
            seen.add(k); warm.append(r)
    src = f"bench/results/{csv_path.name}"
    kind = ("public dataset, adult speech, BEFORE Phase L" if "before_phase_l" in label else
            ("public dataset, adult speech, Santali speech recognition "
             + ("RNN-T" if "rnnt" in label else "CTC") + (", silence trimmed" if "trim" in label else ", no trimming"))
            if label.startswith("public_sat_") else
            "synthetic clips, BEFORE the latency work (baseline)" if "baseline" in label else
            "synthetic clips" if "synthetic" in label else
            "public dataset, adult speech" if "public" in label else
            "real clips" if "real" in label else label)
    print(f"\nVoice to voice, {kind} (run '{label}', {LAPTOP}; excludes Wi-Fi)")
    for d in ("hi-to-sat", "sat-to-hi"):
        s = stats([float(r["pipeline_ms"]) / 1000 for r in warm if r["direction"] == d])
        if s:
            n_all = sum(r["direction"] == d for r in warm_all)
            out(f"{d} median / p90 / max",
                f"{sec(s['median'])} / {sec(s['p90'])} / {sec(s['max'])} s (n={n_all}, n_distinct={s['n']})", src)
    over = sum(float(r["pipeline_ms"]) > 3000 for r in warm)
    out("requests over 3 s", f"{over} of {len(warm)} (n={len(warm_all)}, n_distinct={len(warm)})", src)
    if any(r["direction"] == "sat-to-hi" for r in warm) and "public" in label:
        print("  (Santali: IndicVoices validation split, no public Santali test split; may overlap model-development data)")
    gl = sum(r["source"] == "glossary" for r in warm)
    out("answered by the verified sentence glossary", f"{gl} of {len(warm)}", src)
    errs = sum(bool(r["tts_error"]) for r in warm)
    out("speech (TTS) failures", f"{errs} of {len(warm)}", src)
    if md_path.exists():
        m = re.search(r"Server boot \(all models loaded\): ([\d.]+) s", md_path.read_text(encoding="utf-8"))
        out("server boot, all models loaded", f"{m.group(1)} s" if m else NM, f"bench/results/{md_path.name}")
    if "synthetic" in label:
        print("  (Synthetic clips are Piper reading the lines. Their CER is NOT an ASR accuracy figure.)")
    # Time grows with sentence length, so say how long the sentences were (per
    # direction: Hindi and Santali words are not comparable).
    for d in ("hi-to-sat", "sat-to-hi"):
        dw = [r for r in warm if r["direction"] == d]
        if not dw:
            continue
        out(f"{d}: sentence length, median words", f"{statistics.median(len(r['reference'].split()) for r in dw):g}",
            src)
        if "public" not in label:
            continue
        # Santali answers are short: bin them finer, and give the <= 10-word figure
        # the Santali decoding choice depends on.
        bins = (((0, 6), (6, 11), (11, 18), (18, 999)) if d == "sat-to-hi" else
                ((0, 12), (12, 18), (18, 24), (24, 999)))
        if d == "sat-to-hi":
            bins = ((0, 11),) + bins
        for lo, hi in bins:
            b = [r for r in dw if lo <= len(r["reference"].split()) < hi]
            n_b = sum(r["direction"] == d and lo <= len(r["reference"].split()) < hi for r in warm_all)
            if b:
                ms = [float(r["pipeline_ms"]) for r in b]
                span = f"≤ {hi - 1}" if lo == 0 else f"{lo}-{hi - 1}" if hi < 999 else f"{lo}+"
                out(f"  {d} {span} words{' (small sample)' if len(b) < 10 else ''}: median / p90 / over 3 s",
                    f"{sec(statistics.median(ms) / 1000)} / {sec(pct(ms, 90) / 1000)} s / "
                    f"{sum(m > 3000 for m in ms)} of {len(b)} (n={n_b}, n_distinct={len(b)})", src)


def latency_steps():
    """Phase L: step-by-step latency from bench/latency_steps.py (one CSV per engine)."""
    files = sorted(RESULTS.glob("latency_steps_*.csv"))
    if not files:
        return
    print(f"\nPhase L: time from the end of speech, by step ({LAPTOP}; in-process: upload and "
          f"decoding excluded)")
    print("  full = whole utterance translated and voiced; first / last = clause streaming, "
          "first / last chunk's audio ready")
    print("  public figures use distinct sentences (first clip of each): n = clips, n_distinct = sentences used")
    from bench.latency_steps import distinct_first, read_rows
    for f in files:
        name = f.stem.replace("latency_steps_", "")
        all_rows = read_rows(name)
        rows = distinct_first(all_rows)
        src = f"bench/results/{f.name}"
        tag = (" (the app, run 2)" if name == "app" else " (the app, run 1)" if name == "app_run1"
               else " (before Phase L)" if name == "torch-t14" else "")
        n_all = sum(r["set"] == "public" for r in all_rows)
        pub = [r for r in rows if r["set"] == "public"]
        les = [r for r in rows if r["set"] == "lesson"]
        g = lambda rs, k: [float(r[k]) / 1000 for r in rs]
        up17 = [r for r in pub if int(r["words"]) <= 17]
        n_up17 = sum(r["set"] == "public" and r["words"] <= 17 for r in all_rows)
        nn = f"n={n_all}, n_distinct={len(pub)}"
        if pub:
            full = g(pub, "full_ms")
            out(f"{name}{tag}: public full median / p90",
                f"{sec(statistics.median(full))} / {sec(pct(full, 90))} s ({nn})", src)
            out(f"{name}: public full over 3 s", f"{sum(x > 3 for x in full)} of {len(pub)} ({nn})", src)
            if up17:
                out(f"{name}: public ≤17 words, full p90",
                    f"{sec(pct(g(up17, 'full_ms'), 90))} s (n={n_up17}, n_distinct={len(up17)})", src)
            out(f"{name}: public first audio median / p90",
                f"{sec(statistics.median(g(pub, 'first_audio_ms')))} / {sec(pct(g(pub, 'first_audio_ms'), 90))} s ({nn})", src)
            out(f"{name}: public last audio median / p90",
                f"{sec(statistics.median(g(pub, 'last_audio_ms')))} / {sec(pct(g(pub, 'last_audio_ms'), 90))} s ({nn})", src)
            out(f"{name}: chunked vs whole agreement (chrF++, median)",
                f"{statistics.median(float(r['chunk_vs_whole_chrf']) for r in pub):.1f} ({nn})", src)
            for lo, hi in ((0, 11), (12, 17), (18, 23), (24, 999)):
                b = [r for r in pub if lo <= int(r["words"]) <= hi]
                nb = sum(r["set"] == "public" and lo <= r["words"] <= hi for r in all_rows)
                if b:
                    span = f"{lo}-{hi}" if hi < 999 else f"{lo}+"
                    out(f"  {name}: {span} words{' (small sample)' if len(b) < 10 else ''}, full median / p90, first p90",
                        f"{sec(statistics.median(g(b, 'full_ms')))} / {sec(pct(g(b, 'full_ms'), 90))} s, "
                        f"{sec(pct(g(b, 'first_audio_ms'), 90))} s (n={nb}, n_distinct={len(b)})", src)
        if les:
            out(f"{name}: lesson lines full median / p90",
                f"{sec(statistics.median(g(les, 'full_ms')))} / {sec(pct(g(les, 'full_ms'), 90))} s (n={len(les)})", src)
    eng = RESULTS / "nmt_engines.md"
    if eng.exists():
        print(f"\nTranslation engines, public sentences, median ms and outputs identical to PyTorch "
              f"({LAPTOP}; bench/results/{eng.name})")
        for m in re.finditer(r"^\| (\S+) \| ([\d-]+) \| ([\d-]+) \| ([\d-]+) \| ([\d-]+) \| (\d+) \| (\d+) \| (\d+) of (\d+) \|",
                             eng.read_text(encoding="utf-8"), re.M):
            out(f"{m.group(1)}", f"{m.group(6)} ms, {m.group(8)} of {m.group(9)} identical", f"bench/results/{eng.name}")


def pct(v, p):
    v = sorted(v)
    return v[max(0, min(len(v) - 1, -(-len(v) * p // 100) - 1))]


def asr_decoding_synthetic():
    """CTC vs RNN-T and silence trimming, from bench/results/asr_decoding_synthetic.md."""
    f = RESULTS / "asr_decoding_synthetic.md"
    if not f.exists():
        return
    med = {}
    for m in re.finditer(r"^\| (hi|sat) \| (ctc|rnnt) \| (yes|no) \| (\d+) \|", f.read_text(encoding="utf-8"), re.M):
        med[(m.group(1), m.group(2), m.group(3))] = int(m.group(4))
    print(f"\nSpeech recognition time, synthetic clips (median ms; {LAPTOP})")
    for lang in ("hi", "sat"):
        if (lang, "ctc", "no") in med and (lang, "rnnt", "no") in med:
            out(f"{lang}: CTC vs RNN-T, no trimming", f"{med[(lang, 'ctc', 'no')]} vs {med[(lang, 'rnnt', 'no')]} ms",
                f"bench/results/{f.name}")
        if (lang, "ctc", "no") in med and (lang, "ctc", "yes") in med:
            out(f"{lang}: time saved by trimming silence (CTC)",
                f"{med[(lang, 'ctc', 'no')] - med[(lang, 'ctc', 'yes')]} ms", f"bench/results/{f.name}")


def asr_accuracy():
    """Corpus WER/CER on the public clips, scored by bench/asr_decoding.score (one definition)."""
    import json
    raw = RESULTS / "asr_decoding_public.jsonl"
    print(f"\nSpeech recognition accuracy (public dataset, adult speech; {LAPTOP})")
    if not raw.exists():
        out("WER / CER", NM, "run bench/fetch_public_clips.py, then bench/asr_decoding.py --label public")
        return
    from bench.asr_decoding import SAT_CAVEAT, VARIANTS, score
    rows = [json.loads(l) for l in raw.read_text(encoding="utf-8").splitlines() if l.strip()]
    src = f"bench/results/{raw.name}"
    for lang in ("hi", "sat"):
        mine = [r for r in rows if r["lang"] == lang]
        if not mine:
            out(f"{lang}: WER / CER", NM, "no clips for this language yet")
            continue
        for dec, trim in VARIANTS:
            v = [r for r in mine if r["decoding"] == dec and r["trim"] == trim]
            if not v:
                continue
            sc = score(v)
            used = " (in use)" if (dec == config.ASR_DECODING[lang] and trim == config.ASR_TRIM_SILENCE[lang]) else ""
            out(f"{lang}: {dec}, trim {'on' if trim else 'off'}{used}",
                f"WER raw {sc['wer_raw'] * 100:.1f}%, normalised {sc['wer_norm'] * 100:.1f}%, "
                f"CER {sc['cer_norm'] * 100:.1f}%; {sc['median_ms']:.0f} ms "
                f"(n={sc['n']}, n_distinct={sc['n_distinct']})", src)
        if lang == "sat":
            one = [r for r in mine if (r["decoding"], r["trim"]) == VARIANTS[0]]
            print(f"  {SAT_CAVEAT} Dataset tags removed from the references: {score(one)['tags_removed']}.")
    print("  Child speech: NOT MEASURED.")


def translation():
    import json
    res = ROOT / "eval" / "results" / "benchmarks.json"
    print(f"\nTranslation quality (the model alone; {LAPTOP})")
    if not res.exists():
        out("chrF++ hin<->sat on IN22-Gen, IN22-Conv, FLORES", NM,
            "test sets are gated; run eval/eval_benchmarks.py after access")
        return
    d = json.loads(res.read_text(encoding="utf-8"))
    for r in d["results"]:
        out(f"{r['set']} {r['direction']} chrF++ / BLEU",
            f"{r['chrf++']} / {r['bleu']} (n={r['n']}, n_distinct={r.get('n_distinct', '?')})",
            f"eval/results/{res.name}")


def size(path):
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def latency_three_runs(tag="hp"):
    """The three runs (High performance plan, AC, apps closed): every run and the median of p90s."""
    if not (RESULTS / f"latency_steps_app_{tag}3.csv").exists() or not list(RESULTS.glob(f"*_public_{tag}3.csv")):
        return
    import latency_runs as lr
    tags = [f"{tag}{i}" for i in (1, 2, 3)]
    src = f"bench/results/latency_{tag}_runs.md"
    print(f"\nLatency, three runs ({', '.join(tags)}; laptop on AC, Best performance power mode, other apps closed; "
          "distinct sentences; p90 s)")
    import re as _re
    for d in lr.DEFINITIONS:
        print("  " + _re.sub(r"\*\*|`", "", d))
    steps = {t: lr.steps_run(t) for t in tags}
    h = steps[tags[0]]["≤ 17"]
    out("HEADLINE: from end of speech, ≤ 17 words, full time p90 (median of 3 runs)",
        f"{statistics.median([steps[t]['≤ 17'][3] for t in tags]):.2f} s (n={h[0]}, n_distinct={h[1]})", src)
    for name, (n, nd, _, _) in steps[tags[0]].items():
        firsts = [steps[t][name][2] for t in tags]; fulls = [steps[t][name][3] for t in tags]
        out(f"from end of speech, hi->sat, {lr.label(name, nd)} words: first / full p90",
            " | ".join(f"{a:.2f} / {b:.2f}" for a, b in zip(firsts, fulls))
            + f"; median {statistics.median(firsts):.2f} / {statistics.median(fulls):.2f} s (n={n}, n_distinct={nd})", src)
    v2v = {t: lr.v2v_run(t)[0] for t in tags}
    for key, (n, nd, _) in v2v[tags[0]].items():
        p = [v2v[t][key][2] for t in tags]
        out(f"upload to audio, {key[0]}, {lr.label(key[1], nd)} words: p90",
            " | ".join(f"{x:.2f}" for x in p) + f"; median {statistics.median(p):.2f} s (n={n}, n_distinct={nd})", src)


def f1_phase_a():
    """F1 Phase A (tablet feasibility), measured on the laptop, NOT on a tablet."""
    sv = RESULTS / "sherpa_vs_nemo.md"
    gold = sorted(RESULTS.glob("golden_nmt_*_t2_*.md"))
    if not sv.exists() and not gold:
        return
    print("\nF1 Phase A: engines for the tablet, measured on the LAPTOP (not on a tablet; 2 threads)")
    if sv.exists():
        for m in re.finditer(r"^\| (hi|sat) \| (model[\w.]*onnx) \| (\d+) \| (\d+/\d+) \| ([\d.]+%) \| ([\d.]+%) \| "
                             r"([\d.]+%) \| ([\d.]+%) \| (\d+) \| (\d+) \|", sv.read_text(encoding="utf-8"), re.M):
            out(f"ASR 120M {m.group(1)} sherpa-onnx {m.group(2)}",
                f"WER {m.group(6)} (NeMo {m.group(8)}); same as NeMo {m.group(4)}; {m.group(9)} ms; {m.group(10)} MB",
                f"bench/results/{sv.name}")
    rn = RESULTS / "sherpa_vs_nemo_rnnt.md"
    if rn.exists():
        for m in re.finditer(r"^\| (hi|sat) \| (int8|fp32) \| ([\w+]+) \| (\d+) \| (\d+) \| (\d+/\d+) \| ([\d.]+%) \| "
                             r"([\d.]+%) \| ([\d.]+%) \| (\d+) \| (\d+) \| (\d*) \| (\d+) \|", rn.read_text(encoding="utf-8"), re.M):
            out(f"ASR 120M {m.group(1)} RNN-T sherpa {m.group(2)} {m.group(3)}",
                f"WER {m.group(8)} (NeMo {m.group(9)}); empty {m.group(10)}, hallucinated {m.group(11)}"
                + (f", changed by hotwords {m.group(12)}" if m.group(12) else "")
                + f"; {m.group(13)} ms (n={m.group(4)}, n_distinct={m.group(5)})", f"bench/results/{rn.name}")
    for g in gold:
        t = g.read_text(encoding="utf-8")
        same = re.search(r"Identical token IDs \| (\d+ of \d+)", t)
        ms = re.findall(r"Median time per sentence, (PyTorch|ONNX \w+) \| (\d+) ms", t)
        d = "hin->sat" if "_hi" in g.stem else "sat->hin"
        kind = "int8" if "int8" in g.stem else "fp32"
        out(f"NMT ONNX {kind} {d} vs PyTorch",
            f"{same.group(1) if same else NM} identical; " + ", ".join(f"{k} {v} ms" for k, v in ms), f"bench/results/{g.name}")


def main():
    print(f"{config.APP_NAME}: deck numbers. Values come from files in this repo; "
          f"measurements are '{LAPTOP}'.")

    runs = latest_runs()
    if not runs:
        print(f"\nVoice to voice: {NM} (no bench/results/*.csv)")
    for label in sorted(runs):
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

    latency_steps()
    latency_three_runs()
    asr_decoding_synthetic()
    asr_accuracy()
    translation()
    f1_phase_a()
    print()
    out("ASR WER on child speech / classroom noise", NM, "no child or noisy test set")
    out("chrF++ on the 33-row training CSV", "not used", "it is training data, never a test set")


if __name__ == "__main__":
    import contextlib
    if "--write" in sys.argv:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main()
        text = buf.getvalue()
        print(text, end="")
        (RESULTS / "deck_numbers.txt").write_text(text, encoding="utf-8")
        print(f"\nSaved to bench/results/deck_numbers.txt")
    else:
        main()
