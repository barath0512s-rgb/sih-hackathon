"""Fetch the public speech clips for the benchmarks. Only the manifest is in git.

    python bench/fetch_public_clips.py                 # every source you have access to
    python bench/fetch_public_clips.py --source fleurs-hi
    python bench/fetch_public_clips.py --check         # the clips on disk match the manifest?

Sources (the licence of every clip is recorded in the manifest):
  fleurs-hi       google/fleurs, hi_in, test split. CC BY 4.0. Not gated.
  indicvoices-sat ai4bharat/IndicVoices, santali, valid split. CC BY 4.0. Gated:
                  accept the terms on the dataset page while logged in
                  (huggingface-cli login), then run this again.

Selection: utterances of 3-10 s, then 80 chosen with a fixed seed (SEED), so
everyone who runs this gets the same clips. The audio is written to
bench/clips/public/<lang>/ as 16 kHz WAV (git-ignored); the manifest,
bench/clips/public/manifest.json, is committed. Each entry records the
dataset, revision, file and row, the licence and the SHA-256 of the audio, so
a re-fetch can be checked (--check).

Every result from these clips is labelled "public dataset, adult speech".
Nothing here is child speech.
"""

import argparse
import hashlib
import io
import json
import os
import random
import sys
from pathlib import Path

# This script downloads; config.py puts the Hugging Face libraries offline.
os.environ["HF_HUB_OFFLINE"] = "0"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "bench" / "clips" / "public"
MANIFEST = OUT / "manifest.json"
CACHE = ROOT / "data" / "public"          # the downloaded parquet files (git-ignored)
N, MIN_S, MAX_S, SEED = 80, 3.0, 10.0, 26042
SR = 16000

SOURCES = {
    "fleurs-hi": {
        "lang": "hi", "repo": "google/fleurs",
        "file": "parquet-data/hi_in/test-00000-of-00001.parquet",
        "split": "test", "license": "CC BY 4.0",
        "url": "https://huggingface.co/datasets/google/fleurs",
        "text": "transcription", "id": "id",
    },
    "indicvoices-sat": {
        "lang": "sat", "repo": "ai4bharat/IndicVoices",
        "file": "santali/valid-00000-of-00001.parquet",
        "split": "valid", "license": "CC BY 4.0",
        "url": "https://huggingface.co/datasets/ai4bharat/IndicVoices",
        "text": None, "id": None,          # read from the schema, see _columns
    },
}


def _columns(schema_names, src):
    """The text and id columns. IndicVoices' names are checked, not assumed."""
    text = src["text"] or next((c for c in ("text", "transcription", "verbatim", "normalized")
                                if c in schema_names), None)
    ident = src["id"] or next((c for c in ("id", "audio_filepath", "utterance_id", "file_name")
                               if c in schema_names), None)
    if not text:
        sys.exit(f"{src['repo']}: no text column among {schema_names}")
    return text, ident


def _decode(audio):
    """Audio struct (bytes) -> float32 mono at 16 kHz, and its duration."""
    import numpy as np
    import soundfile as sf
    data, sr = sf.read(io.BytesIO(audio["bytes"]), dtype="float32", always_2d=True)
    data = data.mean(axis=1)
    if sr != SR:
        # Linear resampling is enough for a benchmark input; recorded in the manifest.
        n = int(round(len(data) * SR / sr))
        data = np.interp(np.linspace(0, len(data) - 1, n), np.arange(len(data)), data).astype("float32")
    return data, len(data) / SR


def fetch(name):
    import pyarrow.parquet as pq
    import soundfile as sf
    from huggingface_hub import HfApi, hf_hub_download
    src = SOURCES[name]
    rev = HfApi().dataset_info(src["repo"]).sha
    try:
        path = hf_hub_download(src["repo"], src["file"], repo_type="dataset", revision=rev,
                               local_dir=str(CACHE / src["repo"].replace("/", "__")))
    except Exception as e:
        print(f"{name}: cannot download ({type(e).__name__}). "
              f"If the dataset is gated, accept its terms at {src['url']} and log in.")
        return None
    table = pq.read_table(path)
    text_col, id_col = _columns(table.schema.names, src)
    audio_col = "audio" if "audio" in table.schema.names else "audio_filepath"   # IndicVoices
    rows = table.to_pylist()
    # Durations first (cheap for FLEURS: num_samples; else decode).
    cand = []
    for i, r in enumerate(rows):
        secs = r["num_samples"] / SR if "num_samples" in r and r["num_samples"] else None
        if secs is None:
            secs = r.get("duration")
        if secs is None:
            secs = _decode(r[audio_col])[1]
        if MIN_S <= secs <= MAX_S and (r.get(text_col) or "").strip():
            cand.append(i)
    random.Random(SEED).shuffle(cand)
    picked = sorted(cand[:N])
    out_dir = OUT / src["lang"]
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for i in picked:
        r = rows[i]
        audio, secs = _decode(r[audio_col])
        rid = r.get(id_col, i) if id_col else i
        if isinstance(rid, dict):                 # IndicVoices: audio_filepath is {bytes, path}
            rid = rid.get("path") or i
        rid = str(rid)
        safe = "".join(ch if ch.isalnum() else "_" for ch in Path(rid).stem)[:40]
        f = out_dir / f"{name}_{i:05d}_{safe}.wav"
        sf.write(f, audio, SR, subtype="PCM_16")
        entries.append({
            "file": f.relative_to(ROOT).as_posix(), "lang": src["lang"],
            "reference": r[text_col].strip(), "seconds": round(secs, 2),
            "kind": "public dataset, adult speech",
            "source": {"dataset": src["repo"], "revision": rev, "file": src["file"],
                       "split": src["split"], "row": i, "id": rid},
            "license": src["license"], "url": src["url"],
            "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
            **{k: r[k] for k in ("gender", "age_group", "speaker_id", "task_name", "scenario", "state", "district")
               if k in r and not isinstance(r[k], (bytes, dict))},
        })
    print(f"{name}: {len(entries)} clips from {len(cand)} of {len(rows)} utterances in {MIN_S}-{MAX_S} s "
          f"({src['repo']} @ {rev[:10]})")
    return entries


def check():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    bad = [e["file"] for e in m if not (ROOT / e["file"]).exists()
           or hashlib.sha256((ROOT / e["file"]).read_bytes()).hexdigest() != e["sha256"]]
    print(f"{len(m) - len(bad)} of {len(m)} clips match the manifest." + (f" Missing or different: {bad[:5]}" if bad else ""))
    return not bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", choices=sorted(SOURCES), action="append")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        sys.exit(0 if check() else 1)
    old = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else []
    manifest = {e["file"]: e for e in old}
    for name in a.source or sorted(SOURCES):
        got = fetch(name)
        if got is None:
            continue
        lang = SOURCES[name]["lang"]
        manifest = {k: v for k, v in manifest.items() if not (v["lang"] == lang and
                    v["source"]["dataset"] == SOURCES[name]["repo"])}
        manifest.update({e["file"]: e for e in got})
    OUT.mkdir(parents=True, exist_ok=True)
    rows = sorted(manifest.values(), key=lambda e: (e["lang"], e["file"]))
    MANIFEST.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Manifest: {MANIFEST.relative_to(ROOT)} ({len(rows)} clips: "
          + ", ".join(f"{l} {sum(e['lang'] == l for e in rows)}" for l in ("hi", "sat")) + ")")


if __name__ == "__main__":
    main()
