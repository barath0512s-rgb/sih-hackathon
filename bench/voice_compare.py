"""A6: which Santali voice should the content pack carry? ASR round-trip CER.

    python bench/voice_compare.py

Voices, on every Santali line of the content pack:
  (a) piper   the live voice: Piper hi_IN-pratham reading translit/olchiki.py's
              Devanagari (the pack's own audio files)
  (b) parler  ai4bharat/indic-parler-tts, pre-rendered from the Ol Chiki text
              (tools/parler_prerender.py; content_audio/parler/)
  (c) ours    the fine-tuned MMS voice from notebooks/santali_voice.ipynb, if
              models/santali-voice/ exists (C4); otherwise NOT BUILT
Metric, chosen before running: each clip is recognised by the hub's Santali ASR
(IndicConformer 600M, the app's settings) and compared with the line's text:
character error rate after textnorm.normalize_for_wer (spaces removed from both,
so word-boundary choices do not count). Lower = the recogniser hears the intended
line more exactly. It is a proxy for intelligibility, not a listening test (MOS:
NOT MEASURED; docs/samples/mos_lite_sheet.md is the sheet for native listeners).
Second opinion: the tablet's sherpa-onnx 120M int8 transducer.
Size: bytes per second of audio as the pack would carry it (16-bit WAV at the
voice's own rate; Parler at 44.1 kHz, or resampled to 22.05 kHz).
Decision rule: Parler audio ships in the pack only if its CER (600M) is lower than Piper's.
Writes bench/results/voice_compare.md / .json.
"""

import glob
import io
import json
import statistics
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from textnorm import normalize_for_wer  # noqa: E402

PARLER = ROOT / "content_audio" / "parler"
OURS = config.MODELS_DIR / "santali-voice"
OUT = ROOT / "bench" / "results" / "voice_compare"


def cer(ref, hyp):
    import jiwer
    r = normalize_for_wer(ref).replace(" ", "")
    h = normalize_for_wer(hyp).replace(" ", "")
    return jiwer.cer(r, h) if r else None


def main():
    if "--report-only" in sys.argv:
        saved = json.loads(OUT.with_suffix(".json").read_text(encoding="utf-8"))
        return report(saved, saved["rows"], saved["lines"])
    import soundfile as sf
    import pipeline
    pack = sorted(glob.glob(str(ROOT / "dist" / "packs" / "content-pack-*.zip")))[-1]
    z = zipfile.ZipFile(pack)
    index = json.loads(z.read("audio/index.json"))["sat"]
    pidx = json.loads((PARLER / "index.json").read_text(encoding="utf-8"))
    lines = [t for t in index if t in pidx]
    pl = pipeline.VaaniSetuPipeline()
    import sherpa_onnx
    d = config.MODELS_DIR / "indicconformer-120m-sherpa" / "sat" / "rnnt"
    sh = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=str(d / "encoder.int8.onnx"), decoder=str(d / "decoder.int8.onnx"), joiner=str(d / "joiner.int8.onnx"),
        tokens=str(d / "tokens.txt"), num_threads=4, model_type="nemo_transducer", decoding_method="greedy_search")
    from indicconformer_asr import trim_silence
    tmp = Path(tempfile.mkdtemp())
    rows = []
    t0 = time.time()
    for i, text in enumerate(lines):
        clips = {"piper": io.BytesIO(z.read(f"audio/{index[text]}")), "parler": PARLER / pidx[text]["file"]}
        for voice, src in clips.items():
            x, sr = sf.read(src, dtype="float32")
            x = x.mean(axis=1) if x.ndim > 1 else x
            f = tmp / f"{voice}.wav"
            sf.write(str(f), x, sr)
            big = pl.transcribe_santali(str(f))
            import librosa
            x16 = librosa.resample(x, orig_sr=sr, target_sr=16000) if sr != 16000 else x
            x16 = trim_silence(x16[None, :])[0]
            s = sh.create_stream(); s.accept_waveform(16000, x16); sh.decode_stream(s)
            rows.append({"line": text, "voice": voice, "seconds": round(len(x) / sr, 2), "rate": sr,
                         "asr600": big, "cer600": cer(text, big), "sherpa": s.result.text, "cer_sherpa": cer(text, s.result.text)})
        if i % 20 == 0:
            print(i, len(lines), f"{time.time() - t0:.0f} s", flush=True)
    res = {"pack": Path(pack).name, "lines": len(lines), "voices": {}}
    report(res, rows, len(lines))


def report(res, rows, n_lines):
    res = {k: v for k, v in res.items() if k != "rows"}
    res["voices"] = {}
    for v in ("piper", "parler"):
        R = [r for r in rows if r["voice"] == v and r["cer600"] is not None]
        secs = sum(r["seconds"] for r in R)
        rate = R[0]["rate"]
        res["voices"][v] = {"cer600_mean": round(statistics.mean(r["cer600"] for r in R), 4),
                            "cer600_median": round(statistics.median(r["cer600"] for r in R), 4),
                            "cer_sherpa_mean": round(statistics.mean(r["cer_sherpa"] for r in R), 4),
                            "audio_seconds": round(secs, 1), "rate": rate,
                            "wav_bytes_per_s": rate * 2, "pack_mb_at_own_rate": round(secs * rate * 2 / 1e6, 1),
                            "pack_mb_at_22k": round(secs * 22050 * 2 / 1e6, 1)}
    pw = {r["line"]: r["cer600"] for r in rows if r["voice"] == "piper"}
    better = sum(1 for r in rows if r["voice"] == "parler" and r["cer600"] is not None and r["cer600"] < pw[r["line"]])
    worse = sum(1 for r in rows if r["voice"] == "parler" and r["cer600"] is not None and r["cer600"] > pw[r["line"]])
    res["parler_better_lines"], res["parler_worse_lines"] = better, worse
    ship = res["voices"]["parler"]["cer600_mean"] < res["voices"]["piper"]["cer600_mean"]
    res["decision"] = "ship Parler audio in the pack" if ship else "keep Piper audio"
    res["ours"] = "present" if OURS.exists() else "NOT BUILT (notebooks/santali_voice.ipynb not run yet)"
    P, Q = res["voices"]["piper"], res["voices"]["parler"]
    L = ["# Santali voice comparison (A6): ASR round-trip CER", "",
         f"- Pack `{res['pack']}`: {n_lines} Santali lines, each spoken by (a) Piper (the live voice, via "
         "transliteration) and (b) Indic Parler-TTS (pre-rendered, B1). (c) Our own voice (C4): " + res["ours"] + ".",
         "- Metric (chosen before the run): the hub's Santali ASR (IndicConformer 600M) on each clip; character error "
         "rate against the line after `normalize_for_wer`, spaces removed. Second opinion: sherpa-onnx 120M int8. "
         "A proxy for intelligibility; **native listener ratings (MOS): NOT MEASURED** (sheet: docs/samples/mos_lite_sheet.md).",
         "- No timing is measured here; other work ran on the laptop during scoring (CER does not depend on it).",
         "- The mean is pulled up by clips where a voice fails badly (Parler sometimes produces long audio that "
         "does not match the line: CER above 1); the median shows the typical line.", "",
         "| Voice | CER, 600M (mean / median) | CER, sherpa 120M (mean) | Audio | Pack size at own rate | at 22.05 kHz |",
         "|---|---|---|---|---|---|",
         f"| (a) Piper, transliterated | **{P['cer600_mean']:.3f}** / {P['cer600_median']:.3f} | {P['cer_sherpa_mean']:.3f} | "
         f"{P['audio_seconds']} s at {P['rate']} Hz | {P['pack_mb_at_own_rate']} MB | {P['pack_mb_at_22k']} MB |",
         f"| (b) Indic Parler-TTS | **{Q['cer600_mean']:.3f}** / {Q['cer600_median']:.3f} | {Q['cer_sherpa_mean']:.3f} | "
         f"{Q['audio_seconds']} s at {Q['rate']} Hz | {Q['pack_mb_at_own_rate']} MB | {Q['pack_mb_at_22k']} MB |", "",
         f"- Per line: Parler lower CER on {better}, higher on {worse} of {n_lines}.",
         f"- **Decision (rule fixed in advance): {res['decision']}.**"]
    OUT.with_suffix(".md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    OUT.with_suffix(".json").write_text(json.dumps({**res, "rows": rows}, ensure_ascii=False, indent=1),
                                        encoding="utf-8", newline="\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
