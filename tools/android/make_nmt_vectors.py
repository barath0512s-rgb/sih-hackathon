"""A5: golden vectors for the tablet's translation port (IndicProcessor, SentencePiece, decoding).

    python tools/android/make_nmt_vectors.py      # -> android/app/src/test/resources/nmt_vectors.json

For 300 source sentences (the prompt's minimum):
  Hindi -> Santali: the 189 Hindi lines of the content pack, then IN22-Conv Hindi
  sentences up to 250; Santali -> Hindi: the first 50 IN22-Conv Santali sentences.
records, from the app's own Python path (IndicTransToolkit + the model's tokenizer):
  pre       IndicProcessor.preprocess_batch output ("hin_Deva sat_Olck …")
  ids       the tokenizer's input ids (with eos)
and for the first 40 of each direction, the app's int8 ONNX translation:
  seq       the generated ids (greedy, no-repeat-3-gram, the int8 guard's cap)
  decoded   tokenizer.batch_decode(seq, skip_special_tokens)
  out       IndicProcessor.postprocess_batch + the stem-loop cut, i.e. what the app shows
IN22-Conv: CC BY 4.0 (ai4bharat/IN22-Conv); used here only as test input.
PYTHONHASHSEED is fixed so placeholder numbering (a Python set) is repeatable.
"""

import glob
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "android" / "app" / "src" / "test" / "resources" / "nmt_vectors.json"

if os.environ.get("PYTHONHASHSEED") != "0":
    sys.exit(subprocess.call([sys.executable, *sys.argv], env={**os.environ, "PYTHONHASHSEED": "0"}))

sys.path.insert(0, str(ROOT))
import config  # noqa: E402


def main():
    import pandas as pd
    from transformers import AutoTokenizer
    from IndicTransToolkit.processor import IndicProcessor
    from nmt_onnx import OnnxNMT
    tok = AutoTokenizer.from_pretrained(str(config.NMT_DIR), trust_remote_code=True)
    ip = IndicProcessor(inference=True)
    pack = sorted(glob.glob(str(ROOT / "dist" / "packs" / "content-pack-*.zip")))[-1]
    tr = json.loads(zipfile.ZipFile(pack).read("translations.json"))["hi-to-sat"]
    hi = [v["source_text"] for v in tr.values()]
    conv = pd.read_parquet(ROOT / "data/public/ai4bharat__IN22-Conv/data/train-00000-of-00001.parquet")
    hi += [s for s in conv["hin_Deva"].tolist() if s not in hi][: 250 - len(hi)]
    sat = conv["sat_Olck"].tolist()[:50]
    nmt = OnnxNMT(tok, ip, int8=True, threads=4)
    cases = []
    for direction, src, tgt, lines in (("hi-to-sat", "hin_Deva", "sat_Olck", hi), ("sat-to-hi", "sat_Olck", "hin_Deva", sat)):
        for i, s in enumerate(lines):
            pre = ip.preprocess_batch([s], src_lang=src, tgt_lang=tgt)[0]
            ip.postprocess_batch([pre], lang=tgt)                # pops the placeholder map this sentence queued
            ids = tok([pre])["input_ids"][0]
            c = {"direction": direction, "src": s, "pre": pre, "pieces": tok.convert_ids_to_tokens(ids), "ids": ids}
            if i < 40:
                out, seq, _ = nmt.translate_scored(s, src, tgt)
                c.update(seq=[int(x) for x in seq], decoded=tok.batch_decode([seq], skip_special_tokens=True)[0], out=out)
            cases.append(c)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"note": __doc__.split("\n\n")[0], "engine": "onnx int8 " + str(config.MODELS_DIR.name),
                               "cases": cases}, ensure_ascii=False, indent=0), encoding="utf-8", newline="\n")
    print("wrote", OUT.relative_to(ROOT), len(cases), "cases")


if __name__ == "__main__":
    main()
