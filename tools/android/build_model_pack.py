"""Build the tablet's model pack (A1: on-device speech), and check it on the laptop.

    python tools/android/build_model_pack.py            # dist/packs/model-pack-<time>.zip
    python tools/android/build_model_pack.py --check-only <zip>

The models are too large for the APK, so, like lessons, they arrive as a pack and
are imported the same ways (file picker, hub, the app's import folder), with the
same SHA-256 manifest check. Contents:
  asr/hi/model.int8.onnx, tokens.txt                  IndicConformer 120M Hindi, NeMo CTC, int8
  asr/sat/{encoder,decoder,joiner}.int8.onnx, tokens.txt   120M Santali, NeMo transducer, int8
  tts/hi/model.onnx, tokens.txt                       Piper hi_IN-pratham-medium with the
                                                      metadata sherpa-onnx reads (as its
                                                      scripts/piper/add_meta_data.py writes)
  tts/espeak-ng-data/                                 sherpa-onnx's espeak-ng data (tts-models release)
  models.json                                         engine settings the app reads
  manifest.json                                       format 1, kind "models", SHA-256 of every file
Stored uncompressed (ONNX does not compress; importing is then a copy).
The check loads the packed files with sherpa-onnx 1.13.8 (the AAR's version),
recognises one public clip per language and synthesises one line per language.
"""

import argparse
import datetime
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import config  # noqa: E402

SHERPA = config.MODELS_DIR / "indicconformer-120m-sherpa"
ESPEAK = ROOT / "dist" / "sherpa" / "espeak-ng-data"     # from espeak-ng-data.tar.bz2 (docs/sources.md#sherpa-onnx-tts)
ESPEAK_SHA256 = "4135ccf82e1f40613491c0874d4945ae9e9c7840933d8e25a6f9e003d9ebf533"
VOICE = config.PIPER_VOICES["hindi"]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def piper_with_metadata(src_onnx, src_json, out_dir):
    import onnx
    cfg = json.loads(Path(src_json).read_text(encoding="utf-8"))
    with open(out_dir / "tokens.txt", "w", encoding="utf-8", newline="\n") as f:
        for s, i in cfg["phoneme_id_map"].items():
            if s == "\n":
                continue
            f.write(f"{s} {i[0] if isinstance(i, list) else i}\n")
    m = onnx.load(str(src_onnx))
    while len(m.metadata_props):
        m.metadata_props.pop()
    meta = {"model_type": "vits", "comment": "piper", "language": "Hindi", "voice": cfg["espeak"]["voice"],
            "version": 1, "has_espeak": 1, "has_g2pw": 0, "n_speakers": cfg["num_speakers"],
            "sample_rate": cfg["audio"]["sample_rate"]}
    for k, v in meta.items():
        p = m.metadata_props.add()
        p.key, p.value = k, str(v)
    onnx.save(m, str(out_dir / "model.onnx"))
    return cfg["inference"], cfg["audio"]["sample_rate"]


def build(out_zip):
    stage = Path(tempfile.mkdtemp(prefix="modelpack_"))
    (stage / "asr/hi").mkdir(parents=True)
    (stage / "asr/sat").mkdir(parents=True)
    (stage / "tts/hi").mkdir(parents=True)
    shutil.copyfile(SHERPA / "hi/model.int8.onnx", stage / "asr/hi/model.int8.onnx")
    shutil.copyfile(SHERPA / "hi/tokens.txt", stage / "asr/hi/tokens.txt")
    for n in ("encoder", "decoder", "joiner"):
        shutil.copyfile(SHERPA / f"sat/rnnt/{n}.int8.onnx", stage / f"asr/sat/{n}.int8.onnx")
    shutil.copyfile(SHERPA / "sat/rnnt/tokens.txt", stage / "asr/sat/tokens.txt")
    inference, sr = piper_with_metadata(config.PIPER_DIR / f"{VOICE}.onnx", config.PIPER_DIR / f"{VOICE}.onnx.json",
                                        stage / "tts/hi")
    if not ESPEAK.is_dir():
        raise SystemExit(f"{ESPEAK} missing: download espeak-ng-data.tar.bz2 from the sherpa-onnx tts-models release "
                         f"(sha256 {ESPEAK_SHA256}) and unpack it into dist/sherpa/")
    shutil.copytree(ESPEAK, stage / "tts/espeak-ng-data")
    models = {
        "asr": {"hi": {"type": "nemo_ctc", "model": "asr/hi/model.int8.onnx", "tokens": "asr/hi/tokens.txt",
                       "decoding": "greedy_search", "trim_silence": config.ASR_TRIM_SILENCE["hi"],
                       "source": "ai4bharat IndicConformer 120M hi, CTC branch, int8 (bench/results/sherpa_vs_nemo.md)"},
                "sat": {"type": "nemo_transducer", "encoder": "asr/sat/encoder.int8.onnx",
                        "decoder": "asr/sat/decoder.int8.onnx", "joiner": "asr/sat/joiner.int8.onnx",
                        "tokens": "asr/sat/tokens.txt", "decoding": "greedy_search",
                        "trim_silence": config.ASR_TRIM_SILENCE["sat"],
                        "source": "ai4bharat IndicConformer 120M sat, RNN-T branch, int8 (bench/results/sherpa_vs_nemo_rnnt.md)"}},
        "tts": {"hi": {"model": "tts/hi/model.onnx", "tokens": "tts/hi/tokens.txt", "data_dir": "tts/espeak-ng-data",
                       "noise_scale": inference["noise_scale"], "noise_scale_w": inference["noise_w"],
                       "length_scale": inference["length_scale"], "sample_rate": sr,
                       "source": f"Piper {VOICE} (the hub's voice); Santali is read after translit/olchiki.py"}},
        "sherpa_onnx": "1.13.8",
    }
    (stage / "models.json").write_text(json.dumps(models, ensure_ascii=False, indent=1), encoding="utf-8")
    files = {p.relative_to(stage).as_posix(): sha256(p) for p in sorted(stage.rglob("*")) if p.is_file()}
    manifest = {"format": 1, "kind": "models", "created": datetime.datetime.now().isoformat(timespec="seconds"),
                "app_name": config.APP_NAME, "files": files}
    (stage / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    import pack_signing
    pack_signing.sign_dir(stage)                     # A4: signed like the content pack
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_STORED) as z:
        for p in sorted(stage.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(stage).as_posix())
    shutil.rmtree(stage)
    return out_zip


def check(zip_path):
    import numpy as np
    import sherpa_onnx
    import soundfile as sf
    from translit.olchiki import to_devanagari
    d = Path(tempfile.mkdtemp(prefix="modelpack_check_"))
    zipfile.ZipFile(zip_path).extractall(d)
    m = json.loads((d / "models.json").read_text(encoding="utf-8"))
    man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    bad = [f for f, h in man["files"].items() if sha256(d / f) != h]
    assert not bad, bad
    a = m["asr"]
    rec = {"hi": sherpa_onnx.OfflineRecognizer.from_nemo_ctc(model=str(d / a["hi"]["model"]), tokens=str(d / a["hi"]["tokens"]),
                                                             num_threads=2, decoding_method="greedy_search"),
           "sat": sherpa_onnx.OfflineRecognizer.from_transducer(
               encoder=str(d / a["sat"]["encoder"]), decoder=str(d / a["sat"]["decoder"]), joiner=str(d / a["sat"]["joiner"]),
               tokens=str(d / a["sat"]["tokens"]), num_threads=2, model_type="nemo_transducer", decoding_method="greedy_search")}
    clips = json.loads((ROOT / "bench/clips/public/manifest.json").read_text(encoding="utf-8"))
    for lang in ("hi", "sat"):
        c = next(c for c in clips if c["lang"] == lang)
        x, sr = sf.read(str(ROOT / c["file"]), dtype="float32")
        s = rec[lang].create_stream(); s.accept_waveform(sr, x); rec[lang].decode_stream(s)
        print(f"asr {lang}: {s.result.text!r} (reference {c['reference']!r})")
    t = m["tts"]["hi"]
    tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
        vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=str(d / t["model"]), tokens=str(d / t["tokens"]),
                                                   data_dir=str(d / t["data_dir"]), noise_scale=t["noise_scale"],
                                                   noise_scale_w=t["noise_scale_w"], length_scale=t["length_scale"]),
        num_threads=2)))
    for name, text in (("hi", "दो आम और तीन आम मिलाओ।"), ("sat", to_devanagari("ᱵᱟᱨ ᱟᱢ ᱟᱨ ᱯᱮ ᱟᱢ ᱢᱤᱥᱟᱹᱣ ᱢᱮ᱾"))):
        g = tts.generate(text, sid=0, speed=1.0)
        w = np.array(g.samples, dtype=np.float32)
        out = ROOT / "dist" / "lesson_match" / f"modelpack_tts_{name}.wav"
        out.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out), w, g.sample_rate)
        print(f"tts {name}: {len(w) / g.sample_rate:.2f} s at {g.sample_rate} Hz, rms {float(np.sqrt((w ** 2).mean())):.3f} -> {out.name}")
    shutil.rmtree(d, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check-only")
    a = ap.parse_args()
    z = Path(a.check_only) if a.check_only else build(
        ROOT / "dist" / "packs" / f"model-pack-{datetime.datetime.now():%Y%m%d-%H%M}.zip")
    print(z, f"{z.stat().st_size / 1e6:.1f} MB")
    check(z)


if __name__ == "__main__":
    main()
