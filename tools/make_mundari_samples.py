"""A7: Mundari voice samples from the MMLoSo 2025 test split only (no sentences of ours).

    python tools/make_mundari_samples.py             # reads dist/mundari/

Input (either, put in dist/mundari/ by the team):
  - mmloso_test_mundari_samples.json  written by notebooks/mundari_lora.ipynb, or
  - the competition's test CSV (columns row_id, source_sentence, source_lang, target_lang).
Steps:
  1. Every test sentence available (all test sources when the CSV is given, else the 10
     samples) is added to the leakage guard, eval/test_set_hashes.json, set
     "mmloso-test" (SHA-256 of eval.leakage.normalise_for_hash), so no training may use it.
  2. The 10 samples (Mundari source sentences, seeded as in the notebook) are spoken by
     facebook/mms-tts-unr (mms_tts.py; Devanagari converted to Odia script) into
     docs/samples/voices/mundari/NN.wav, with README.md: the text, the source, the
     licence (CC BY-SA 4.0, attribution: MMLoSo 2025 shared task) and "Preview:
     pronunciation not reviewed".
Ho: no published, licensed Ho text is used, so no Ho sample is made.
"""

import glob
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SRC = ROOT / "dist" / "mundari"
OUT = ROOT / "docs" / "samples" / "voices" / "mundari"
SOURCE = "MMLoSo 2025 shared task, official test file (https://kaggle.com/competitions/mm-lo-so-2025)"


def load():
    j = SRC / "mmloso_test_mundari_samples.json"
    csvs = sorted(glob.glob(str(SRC / "*test*.csv")))
    all_test, samples = [], []
    if csvs:
        import pandas as pd
        t = pd.read_csv(csvs[0])
        all_test = t["source_sentence"].astype(str).tolist()
        mun = t[t.source_lang.str.lower() == "mundari"]
        samples = [{"row_id": str(r.row_id), "mundari": r.source_sentence}
                   for _, r in mun.sample(n=min(10, len(mun)), random_state=20260927).iterrows()]
    elif j.exists():
        samples = json.loads(j.read_text(encoding="utf-8"))["sentences"]
        all_test = [s["mundari"] for s in samples]
    else:
        sys.exit(f"put the notebook's mmloso_test_mundari_samples.json or the competition's test CSV in {SRC}")
    return all_test, samples


def guard(sentences):
    from eval.leakage import HASHES, normalise_for_hash
    data = json.loads(HASHES.read_text(encoding="utf-8"))
    have = set(data.get("mmloso-test", {}).get("sha256", []))
    have |= {hashlib.sha256(normalise_for_hash(s).encode("utf-8")).hexdigest() for s in sentences}
    data["mmloso-test"] = {"source": SOURCE, "licence": "CC BY-SA 4.0", "sha256": sorted(have)}
    HASHES.write_text(json.dumps(data, indent=0) + "\n", encoding="utf-8", newline="\n")
    return len(have)


def main():
    import soundfile as sf
    import mms_tts
    all_test, samples = load()
    n = guard(all_test)
    OUT.mkdir(parents=True, exist_ok=True)
    v = mms_tts.MmsVoice("unr")
    rows = []
    for i, s in enumerate(samples, 1):
        w, sr = v.synth(s["mundari"])
        sf.write(str(OUT / f"{i:02d}.wav"), w, sr, subtype="PCM_16")
        rows.append(f"| {i:02d}.wav | {s['mundari']} | {s['row_id']} |")
    (OUT / "README.md").write_text("\n".join([
        "# Mundari voice samples (Preview)", "",
        f"- Text: {SOURCE}, **test split only**; CC BY-SA 4.0 (attribution: MMLoSo 2025 shared task).",
        "- Voice: facebook/mms-tts-unr (CC BY-NC 4.0), Devanagari converted to Odia script (`translit/odia.py`).",
        "- **Preview: pronunciation not reviewed by a native speaker.** The sentences are in the leakage guard "
        "(`eval/test_set_hashes.json`, set `mmloso-test`).", "",
        "| File | Sentence (Mundari, Devanagari) | Test row_id |", "|---|---|---|"] + rows) + "\n",
        encoding="utf-8", newline="\n")
    print(f"{len(rows)} samples -> {OUT}; {n} test sentences in the leakage guard")


if __name__ == "__main__":
    main()
