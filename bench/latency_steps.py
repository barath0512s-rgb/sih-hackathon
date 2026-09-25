"""Phase L: time every step of Hindi speech -> Santali speech, by sentence length.

    python bench/latency_steps.py --backend torch-t14      # the app today (14 threads)
    python bench/latency_steps.py --backend torch-t4       # 4 threads for translation
    python bench/latency_steps.py --backend torch-int8-t4  # + dynamic int8 Linear layers

Inputs: the public FLEURS Hindi clips (bench/clips/public/manifest.json;
public dataset, adult speech) and the Hindi lesson lines
(bench/clips/synthetic/manifest.json; synthetic speech, short lines).

For every clip, in-process on this laptop, offline:
  asr_ms      speech recognition (the app's settings), from the decoded audio
  whole       translate the whole utterance, then synthesise it
  chunked     streaming.chunks(): translate and synthesise chunk by chunk
Metrics (all measured from the moment the audio is handed to the recogniser,
i.e. after the end of speech; endpointing is reported separately):
  full_ms                 asr + translation + synthesis of the whole utterance
  first_audio_ms          chunked: asr + translation and synthesis of chunk 1
  last_audio_ms           chunked: asr + all chunks translated and synthesised,
                          one after the other (the audio of chunk k plays while
                          chunk k+1 is being prepared)
  stalls                  chunks whose audio is not ready when the previous
                          chunk's audio ends (a gap in the speech)
Quality: chrF++ of the chunked translation against the whole-sentence one
(agreement, not accuracy; accuracy needs FLORES references: NOT MEASURED).

Writes bench/results/latency_steps_<backend>.csv and .md.
"""

import argparse
import copy
import csv
import json
import statistics
import sys
import tempfile
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
import streaming  # noqa: E402

BINS = ((0, 11), (12, 17), (18, 23), (24, 999))


def pct(v, p):
    v = sorted(v)
    return v[max(0, min(len(v) - 1, -(-len(v) * p // 100) - 1))]


def wav_seconds(path):
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def make_backend(pl, name):
    """(callable text -> santali, description). Threads apply to translation only."""
    import torch
    if name == "app":                        # exactly what the app runs (config.py)
        def translate_app(text):
            out, _ = pl._nmt(text, "hin_Deva", "sat_Olck")
            return pl._apply_domain_glossary(out, "sat_Olck")
        return translate_app, (f"the app's engine: {pl.nmt_backend}, {config.NMT_THREADS} threads; "
                               f"speech recognition {config.ASR_THREADS} threads")
    threads = int(name.rsplit("-t", 1)[1]) if "-t" in name else torch.get_num_threads()
    if name.startswith("onnx"):
        from IndicTransToolkit import IndicProcessor
        import nmt_onnx
        int8 = "int8" in name
        eng = nmt_onnx.OnnxNMT(pl.tok_nmt, IndicProcessor(inference=True), int8=int8, threads=threads)

        def translate_onnx(text):
            out, _ = eng.translate(text, "hin_Deva", "sat_Olck")
            return pl._apply_domain_glossary(out, "sat_Olck")
        return translate_onnx, f"ONNX Runtime {'dynamic int8' if int8 else 'fp32'}, {threads} threads"
    model = pl.mdl_nmt                       # PyTorch: passed explicitly, so pl._nmt runs PyTorch
    if "int8" in name:
        model = torch.ao.quantization.quantize_dynamic(copy.deepcopy(pl.mdl_nmt), {torch.nn.Linear},
                                                       dtype=torch.qint8)

    def translate(text):
        torch.set_num_threads(threads)
        out, _ = pl._nmt(text, "hin_Deva", "sat_Olck", pl.tok_nmt, model)
        return pl._apply_domain_glossary(out, "sat_Olck")
    return translate, f"PyTorch, {'dynamic int8 Linear' if 'int8' in name else 'fp32'}, {threads} threads"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--backend", default="torch-t14")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()

    import sacrebleu
    import pipeline
    pl = pipeline.VaaniSetuPipeline()
    translate, desc = make_backend(pl, a.backend)
    tmp = Path(tempfile.mkdtemp(prefix="latsteps_"))
    config.TTS_CACHE_DIR = tmp / "tts_cache"          # empty: every clip is really synthesised

    items = []
    for label, man in (("public", "bench/clips/public/manifest.json"),
                       ("lesson", "bench/clips/synthetic/manifest.json")):
        for c in json.loads((ROOT / man).read_text(encoding="utf-8")):
            if c["lang"] == "hi":
                items.append((label, c))
    if a.limit:
        items = items[:a.limit] + [i for i in items if i[0] == "lesson"][:a.limit]

    # Warm every engine first (L4): no first-request penalty inside the numbers.
    w = pl._to_wav(str(ROOT / items[0][1]["file"]))
    pl._transcribe(w, "hi"); translate("नमस्ते बच्चो"); pl.santali_tts("ᱡᱚᱦᱟᱨ", str(tmp / "warm.wav"))

    rows = []
    for k, (label, c) in enumerate(items):
        wav = pl._to_wav(str(ROOT / c["file"]))                 # decoding is outside the timing
        t0 = time.perf_counter(); hyp = pl._transcribe(wav, "hi"); asr = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter(); sat = translate(hyp); nmt = (time.perf_counter() - t0) * 1000
        t0 = time.perf_counter(); pl.santali_tts(sat, str(tmp / "whole.wav")); tts = (time.perf_counter() - t0) * 1000

        parts, ready, t_acc, outs, durs = streaming.chunks(hyp), [], asr, [], []
        for j, ch in enumerate(parts):
            t0 = time.perf_counter(); o = translate(ch); t_acc += (time.perf_counter() - t0) * 1000
            f = tmp / f"c{j}.wav"
            t0 = time.perf_counter(); pl.santali_tts(o, str(f)); t_acc += (time.perf_counter() - t0) * 1000
            outs.append(o); ready.append(t_acc); durs.append(wav_seconds(f) * 1000)
        stalls, play_end = 0, None
        for j, r in enumerate(ready):
            start = r if play_end is None else max(r, play_end)
            if play_end is not None and r > play_end:
                stalls += 1
            play_end = start + durs[j]
        agree = sacrebleu.sentence_chrf(" ".join(outs), [sat], word_order=2).score if sat else 0.0
        rows.append({"set": label, "clip": c["file"], "words": len(hyp.split()), "chunks": len(parts),
                     "asr_ms": round(asr), "nmt_ms": round(nmt), "tts_ms": round(tts),
                     "full_ms": round(asr + nmt + tts), "first_audio_ms": round(ready[0]) if ready else "",
                     "last_audio_ms": round(ready[-1]) if ready else "", "stalls": stalls,
                     "chunk_vs_whole_chrf": round(agree, 1), "recognized": hyp, "whole": sat,
                     "chunked": " | ".join(outs)})
        r = rows[-1]
        print(f"{k + 1:>3}/{len(items)} {label:6} {r['words']:>2}w {r['chunks']}c  full {r['full_ms']:>5}  "
              f"first {r['first_audio_ms']:>5}  last {r['last_audio_ms']:>5}  (asr {r['asr_ms']} nmt {r['nmt_ms']} "
              f"tts {r['tts_ms']})  agree {r['chunk_vs_whole_chrf']}", flush=True)

    out = ROOT / "bench" / "results" / f"latency_steps_{a.backend}"
    with open(out.with_suffix(".csv"), "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)

    def block(rs):
        if not rs:
            return None
        g = lambda k: [r[k] for r in rs]
        return (len(rs), statistics.median(g("asr_ms")), statistics.median(g("nmt_ms")), statistics.median(g("tts_ms")),
                statistics.median(g("full_ms")), pct(g("full_ms"), 90), sum(x > 3000 for x in g("full_ms")),
                statistics.median(g("first_audio_ms")), pct(g("first_audio_ms"), 90),
                statistics.median(g("last_audio_ms")), pct(g("last_audio_ms"), 90), sum(g("stalls")),
                statistics.median(g("chunk_vs_whole_chrf")))

    lines = [f"# Latency by step and sentence length: {a.backend}", "",
             f"- Translation backend: {desc}. Speech recognition: IndicConformer, "
             f"{config.ASR_DECODING['hi']}, trim={config.ASR_TRIM_SILENCE['hi']}. Speech: Piper "
             f"{pl._voice_model('santali')}. Every engine warmed first. Laptop, offline, in-process.",
             "- **public** = google/fleurs Hindi test clips (public dataset, adult speech). "
             "**lesson** = the Hindi lesson lines (synthetic speech). Child speech: NOT MEASURED.",
             "- Times in ms from the end of speech (audio handed to the recogniser); endpointing, "
             "upload and audio decoding not included. Median / p90.",
             "- full = whole utterance translated and voiced. first / last audio = clause streaming "
             "(streaming.py): first chunk ready / all chunks ready.",
             "- agree = chrF++ of the chunked translation against the whole-sentence translation "
             "(how much chunking changes the output), not accuracy.", "",
             "| Set | Words | n | ASR | NMT | TTS | full med | full p90 | full >3 s | first med | first p90 | "
             "last med | last p90 | stalls | agree |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for label in ("public", "lesson"):
        groups = [("all", [r for r in rows if r["set"] == label])]
        if label == "public":
            groups += [(f"{lo}-{hi}" if hi < 999 else f"{lo}+", [r for r in rows if r["set"] == label and lo <= r["words"] <= hi])
                       for lo, hi in BINS]
        for name, rs in groups:
            b = block(rs)
            if b:
                lines.append(f"| {label} | {name} | {b[0]} | {b[1]:.0f} | {b[2]:.0f} | {b[3]:.0f} | {b[4]:.0f} | {b[5]:.0f} | "
                             f"{b[6]} | {b[7]:.0f} | {b[8]:.0f} | {b[9]:.0f} | {b[10]:.0f} | {b[11]} | {b[12]:.1f} |")
    up17 = [r for r in rows if r["set"] == "public" and r["words"] <= 17]
    pub = [r for r in rows if r["set"] == "public"]
    if pub:
        lines += ["", "Targets (Phase L):",
                  f"- p90 time to first audio, all public sentences: {pct([r['first_audio_ms'] for r in pub], 90)} ms "
                  f"(target ≤ 3000)",
                  f"- p90 full time, public sentences of ≤ 17 words (n={len(up17)}): "
                  f"{pct([r['full_ms'] for r in up17], 90) if up17 else 'n/a'} ms (target ≤ 3000)"]
    out.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
