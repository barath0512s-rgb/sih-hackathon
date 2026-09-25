"""Phase L4: how many threads each engine should use on this machine.

    python bench/thread_sweep.py

Translation (ONNX Runtime fp32, the app's engine) on 40 FLEURS Hindi
references, and speech recognition (IndicConformer, CTC, the app's settings) on
30 FLEURS clips, each timed at several thread counts. Median ms. Writes
bench/results/thread_sweep.md. Run it again on a new machine: the best count
depends on the processor (this laptop mixes performance and efficiency cores).
"""

import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

THREADS = (2, 4, 6, 8, 14)


def nmt(threads):
    import config  # noqa
    from IndicTransToolkit import IndicProcessor
    from transformers import AutoTokenizer
    import nmt_onnx
    tok = AutoTokenizer.from_pretrained(str(config.NMT_DIR), trust_remote_code=True)
    sents = [c["reference"] for c in json.loads((ROOT / "bench/clips/public/manifest.json")
                                                 .read_text(encoding="utf-8")) if c["lang"] == "hi"][:40]
    eng = nmt_onnx.OnnxNMT(tok, IndicProcessor(inference=True), int8=False, threads=threads)
    eng.translate(sents[0], "hin_Deva", "sat_Olck")
    ms = []
    for s in sents:
        t0 = time.perf_counter(); eng.translate(s, "hin_Deva", "sat_Olck"); ms.append((time.perf_counter() - t0) * 1000)
    return statistics.median(ms)


def asr(threads):
    import config
    config.ASR_THREADS = threads
    from indicconformer_asr import IndicConformerASR
    a = IndicConformerASR()
    clips = [c["file"] for c in json.loads((ROOT / "bench/clips/public/manifest.json")
                                            .read_text(encoding="utf-8")) if c["lang"] == "hi"][:30]
    a.transcribe(str(ROOT / clips[0]), lang="hi", decoding=config.ASR_DECODING["hi"], trim=True)
    ms = []
    for f in clips:
        t0 = time.perf_counter()
        a.transcribe(str(ROOT / f), lang="hi", decoding=config.ASR_DECODING["hi"], trim=config.ASR_TRIM_SILENCE["hi"])
        ms.append((time.perf_counter() - t0) * 1000)
    return statistics.median(ms)


def main():
    if len(sys.argv) == 3:                       # child process: one engine, one count
        fn = nmt if sys.argv[1] == "nmt" else asr
        print(json.dumps(fn(int(sys.argv[2]))))
        return
    res = {}
    for engine in ("nmt", "asr"):
        for th in THREADS:
            # A fresh process each time: thread pools cannot be resized reliably in one.
            r = subprocess.run([sys.executable, __file__, engine, str(th)], capture_output=True, text=True,
                               cwd=ROOT, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            res[(engine, th)] = float(r.stdout.strip().splitlines()[-1])
            print(f"{engine} {th:>2} threads: {res[(engine, th)]:.0f} ms", flush=True)
    import platform
    lines = ["# Thread counts (Phase L4)", "",
             f"Median ms. Laptop, offline; {os.cpu_count()} logical CPUs; {platform.processor()}.",
             "Translation: ONNX Runtime fp32, 40 FLEURS Hindi references. Speech recognition: "
             "IndicConformer (CTC), 30 FLEURS clips.", "",
             "| Threads | " + " | ".join(str(t) for t in THREADS) + " |",
             "|---|" + "---|" * len(THREADS),
             "| Translation | " + " | ".join(f"{res[('nmt', t)]:.0f}" for t in THREADS) + " |",
             "| Speech recognition | " + " | ".join(f"{res[('asr', t)]:.0f}" for t in THREADS) + " |"]
    best = {e: min(THREADS, key=lambda t: res[(e, t)]) for e in ("nmt", "asr")}
    lines += ["", f"Fastest: translation {best['nmt']} threads, speech recognition {best['asr']} threads."]
    (ROOT / "bench" / "results" / "thread_sweep.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
