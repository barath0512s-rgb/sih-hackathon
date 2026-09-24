"""Download the models the application uses, and verify them.

Only three model sets are in use:
  ASR  ai4bharat/indic-conformer-600m-multilingual   -> models/indicconformer
  NMT  ai4bharat/indictrans2-indic-indic-dist-320M   -> models/indictrans2-indic-indic
  TTS  Piper voices                                  -> models/piper

Every file is checked against model_manifest.json (size and SHA-256), so a
teammate ends up with byte-identical files to the ones the app was tested with.

    python download_models.py                  # download what is missing, then verify
    python download_models.py --verify-only    # verify, download nothing
    python download_models.py --write-manifest # hash the files on disk into the manifest

The two AI4Bharat repos are gated: accept their terms on huggingface.co, then run
`huggingface-cli login` once before downloading.
"""

import argparse, hashlib, json, subprocess, sys
from pathlib import Path

import config

MANIFEST = config.BASE_DIR / "model_manifest.json"

HF_MODELS = [
    {   # IndicConformer 600M multilingual, ONNX. RNN-T and CTC heads for 22 languages.
        "name": "asr",
        "repo": "ai4bharat/indic-conformer-600m-multilingual",
        "revision": "e9b71b369c048e2c6b634d4c131061c34e441179",
        "dir": config.ASR_DIR,
        "ignore": [],
    },
    {   # IndicTrans2 distilled, direct Indic<->Indic. The repo ships the weights
        # twice; transformers loads model.safetensors, so the 1.2 GB .bin is skipped.
        "name": "nmt",
        "repo": "ai4bharat/indictrans2-indic-indic-dist-320M",
        "revision": "ffb7582b6d43791f1fb26b2153fc065f2e9ea575",
        "dir": config.NMT_DIR,
        "ignore": ["pytorch_model.bin"],
    },
]

PIPER_VOICES = ["hi_IN-pratham-medium", "en_US-lessac-medium"]

# Files that are on disk but must not be listed in the manifest.
SKIP_PARTS = {".cache", "__pycache__"}


def _files(root: Path, ignore=()):
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(config.BASE_DIR).as_posix()
        if SKIP_PARTS & set(p.parts) or p.name in ignore:
            continue
        yield rel, p


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest():
    entries = {}
    for m in HF_MODELS:
        for rel, p in _files(m["dir"], m["ignore"]):
            entries[rel] = {"size": p.stat().st_size, "sha256": _sha256(p)}
    for rel, p in _files(config.PIPER_DIR):
        entries[rel] = {"size": p.stat().st_size, "sha256": _sha256(p)}
    MANIFEST.write_text(json.dumps(entries, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    total = sum(e["size"] for e in entries.values())
    print(f"Wrote {MANIFEST.name}: {len(entries)} files, {total/1e9:.2f} GB")


def download():
    from huggingface_hub import snapshot_download
    for m in HF_MODELS:
        print(f"[{m['name']}] {m['repo']} @ {m['revision'][:10]}")
        snapshot_download(repo_id=m["repo"], revision=m["revision"],
                          local_dir=str(m["dir"]), ignore_patterns=m["ignore"])
    config.PIPER_DIR.mkdir(parents=True, exist_ok=True)
    for v in PIPER_VOICES:
        if (config.PIPER_DIR / f"{v}.onnx").exists():
            continue
        print(f"[tts] piper voice {v}")
        subprocess.run([sys.executable, "-m", "piper.download_voices", v,
                        "--data-dir", str(config.PIPER_DIR)], check=True)


def verify() -> bool:
    if not MANIFEST.exists():
        print(f"{MANIFEST.name} is missing; nothing to verify against.")
        return False
    want = json.loads(MANIFEST.read_text(encoding="utf-8"))
    bad = []
    for rel, e in want.items():
        p = config.BASE_DIR / rel
        if not p.exists():
            bad.append(f"MISSING   {rel}")
        elif p.stat().st_size != e["size"]:
            bad.append(f"SIZE      {rel}  ({p.stat().st_size} != {e['size']})")
        elif _sha256(p) != e["sha256"]:
            bad.append(f"CHECKSUM  {rel}")
    total = sum(e["size"] for e in want.values())
    if bad:
        print(f"{len(bad)} of {len(want)} files failed verification:")
        for b in bad[:30]:
            print("  " + b)
        return False
    print(f"All {len(want)} model files verified ({total/1e9:.2f} GB).")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--write-manifest", action="store_true")
    a = ap.parse_args()
    if a.write_manifest:
        write_manifest()
        sys.exit(0)
    if not a.verify_only:
        download()
    sys.exit(0 if verify() else 1)
