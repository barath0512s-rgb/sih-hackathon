"""Write the two GPU notebooks (B2) from the cell sources below.

    python tools/make_notebooks.py        # -> notebooks/mundari_lora.ipynb, notebooks/santali_voice.ipynb

Both run on Kaggle (GPU T4/P100) or Colab (T4). Both: pinned packages, a GPU check,
an interactive Hugging Face token kept only in memory (never written to disk),
checkpoints in a persistent folder so a stopped session resumes, and an ONNX
export at the end, made with this repo's own exporters.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "https://github.com/barath0512s-rgb/sih-hackathon"   # GitHub redirects after a rename

COMMON_SETUP = r'''
import os, sys, subprocess, json, glob, time, hashlib, random
ON_KAGGLE = os.path.exists("/kaggle")
ON_COLAB = "google.colab" in sys.modules
import torch
assert torch.cuda.is_available(), "No GPU: Kaggle -> Settings -> Accelerator -> GPU; Colab -> Runtime -> Change runtime type -> T4 GPU"
print("GPU:", torch.cuda.get_device_name(0), "| torch", torch.__version__)
if ON_COLAB:
    from google.colab import drive
    drive.mount("/content/drive")
    PERSIST = "/content/drive/MyDrive/nijbhasha"
else:
    PERSIST = "/kaggle/working"            # saved as the notebook's output; re-attach it to resume
os.makedirs(PERSIST, exist_ok=True)
# Resume on Kaggle: an earlier run's output attached as an input is copied back into
# /kaggle/working, so finished steps are skipped and training continues from its checkpoints.
import shutil
for prev in glob.glob("/kaggle/input/*/"):
    if any(os.path.exists(os.path.join(prev, m)) for m in ("lora_hi_unr", "lora_unr_hi", "santali_voice_run", "sat_meta.json")):
        print("resuming from", prev)
        shutil.copytree(prev, PERSIST, dirs_exist_ok=True)
if not os.path.exists("repo"):
    subprocess.run(["git", "clone", "-q", "--depth", "1", REPO_URL, "repo"], check=True)
sys.path.insert(0, os.path.abspath("repo"))
'''

HF_LOGIN = r'''
# Hugging Face token. On Kaggle: from Kaggle Secrets (Add-ons -> Secrets, label HF_TOKEN).
# Elsewhere: typed, hidden. Kept only in this process's memory: never printed, never written.
if not os.environ.get("HF_TOKEN"):
    if os.path.exists("/kaggle"):
        from kaggle_secrets import UserSecretsClient
        os.environ["HF_TOKEN"] = UserSecretsClient().get_secret("HF_TOKEN")
    else:
        import getpass
        os.environ["HF_TOKEN"] = getpass.getpass("Hugging Face read token (input hidden): ").strip()
from huggingface_hub import whoami
print("Hugging Face account:", whoami(token=os.environ["HF_TOKEN"])["name"])   # the account name only
'''


def nb(cells):
    out = []
    for kind, src in cells:
        src = src.strip("\n")
        c = {"cell_type": kind, "metadata": {}, "source": [l + "\n" for l in src.split("\n")]}
        c["source"][-1] = c["source"][-1].rstrip("\n")
        if kind == "code":
            c.update(outputs=[], execution_count=None)
        out.append(c)
    return {"cells": out, "metadata": {"accelerator": "GPU", "kernelspec": {"name": "python3", "display_name": "Python 3"},
                                       "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}


MUNDARI = [
    ("markdown", r'''
# Mundari preview: IndicTrans2 LoRA, Hindi ↔ Mundari (C3)

Two **directional LoRA adapters** (hi→unr, unr→hi) on `ai4bharat/indictrans2-indic-indic-dist-320M`,
the same base model the app uses, trained on the **MMLoSo 2025** Hindi–Mundari training file only
(20,000 pairs, CC BY-SA 4.0; Mundari in Devanagari; `docs/sources.md#mmloso`).

* The official MMLoSo test file has **no public references** ("The test set contains only the source
  sentence…"), so chrF++ and BLEU are measured on a fixed **5 % held-out part of the training file**
  (split by a hash of the Hindi sentence, before any training). The official test **sources** and the
  held-out sentences go to `leakage_hashes.json` for the repo's leakage guard. Optionally, the
  notebook also writes a Kaggle late-submission file for the official test.
* IndicTrans2 has no Mundari tag. `brx_Deva` (Bodo, Devanagari; unused by the app) is used as the
  **surrogate tag** for Mundari in both directions.

**Run on Kaggle (exact steps)**
1. kaggle.com → Settings → Phone verification done (needed for GPU and Internet).
2. Create → New Notebook → File → **Import Notebook** → upload this `.ipynb`.
3. Right panel → Session options → **Accelerator: GPU T4 x2** (or P100); **Internet: On**.
4. Add-ons → **Secrets** → Add secret: label **`HF_TOKEN`**, value = a Hugging Face **read** token → tick it
   for this notebook. (The code reads it with `UserSecretsClient`; it is never printed or saved.)
5. kaggle.com/competitions/mm-lo-so-2025 → Data → **accept the rules** (your account); then in the
   notebook: **Add Input** → Competitions → **mm-lo-so-2025**.
6. **Save Version → Save & Run All (Commit)** (runs in the background, up to 12 h, keeps the output).
7. When it finishes: the version's **Output** → download `mundari_onnx.zip`, `mundari_eval.json`,
   `leakage_hashes.json`, `mmloso_test_mundari_samples.json`. Put them in the repo's `dist/mundari/` and tell me.
8. If it stops: open the notebook → **Add Input** → *Notebook Output* → the stopped version → Save & Run All
   again; finished steps are skipped and training resumes from the newest checkpoint.

**Colab:** upload the competition's Hindi–Mundari training CSV (and the test CSV) to
`MyDrive/nijbhasha/mmloso/`, Runtime → T4 GPU, Run all; checkpoints stay in Drive.

**Expected runtime (T4):** setup 5 min · training ≈ 35–50 min per direction (3 epochs, 19k pairs) ·
evaluation 5 min · merge + ONNX export + int8 ≈ 10 min per direction. **≈ 2–2.5 h in total.**
These are estimates, not measurements.
'''),
    ("code", r'''
REPO_URL = "%s"
''' % REPO + COMMON_SETUP),
    ("code", r'''
# Pinned packages (the app's versions where it has them).
!pip install -q transformers==4.46.1 peft==0.13.2 accelerate==1.0.1 sacrebleu==2.5.1 sentencepiece==0.2.0 \
    onnx==1.17.0 onnxruntime==1.19.2 "numpy<2" \
    "IndicTransToolkit @ git+https://github.com/VarunGumma/IndicTransToolkit.git@3efb8418d0721b4ce267c2b3586899d313191357"
'''),
    ("code", HF_LOGIN),
    ("code", r'''
# Data: the MMLoSo Hindi-Mundari training file and the test sources.
import pandas as pd
cands = glob.glob("/kaggle/input/**/*.csv", recursive=True) + glob.glob(f"{PERSIST}/mmloso/*.csv")
print("\n".join(cands))
train_csv = [c for c in cands if "mundari" in os.path.basename(c).lower() and "test" not in c.lower()]
test_csv = [c for c in cands if "test" in os.path.basename(c).lower()]
assert train_csv, "Hindi-Mundari training CSV not found: add the competition data (Kaggle) or upload it (Colab)"
df = pd.read_csv(train_csv[0])
assert {"hindi", "mundari"} <= set(df.columns), df.columns
df = df.dropna(subset=["hindi", "mundari"]).drop_duplicates(subset=["hindi", "mundari"])
print(len(df), "pairs after de-duplication")

import unicodedata, re
def nkey(s):   # the repo's textnorm.normalize_key idea: NFC, lower, collapse spaces
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(s)).strip().lower())
def heldout(h):   # fixed 5 % split by the Hindi sentence, independent of row order
    return int(hashlib.sha1(nkey(h).encode()).hexdigest(), 16) % 20 == 0
df["held"] = df.hindi.map(heldout)
# a Mundari sentence that appears in both parts goes to held-out only
held_mun = set(df[df.held].mundari.map(nkey))
train_df = df[~df.held & ~df.mundari.map(nkey).isin(held_mun)]
held_df = df[df.held]
print("train", len(train_df), "held-out", len(held_df))

test_src = []
if test_csv:
    t = pd.read_csv(test_csv[0]); print(t.columns.tolist(), len(t))
    test_src = t[t.target_lang.str.lower().str.contains("mundari|hindi")]["source_sentence"].tolist() if "source_sentence" in t else []
leak = {"note": "sha1 of normalize_key(text): MMLoSo held-out (hi, unr) and official test sources; never train on these",
        "hashes": sorted({hashlib.sha1(nkey(s).encode()).hexdigest()
                          for s in list(held_df.hindi) + list(held_df.mundari) + test_src})}
json.dump(leak, open(f"{PERSIST}/leakage_hashes.json", "w"))
print(len(leak["hashes"]), "hashes -> leakage_hashes.json")

# A7 voice samples: 10 Mundari sentences from the official TEST file only (Mundari -> Hindi sources),
# seeded; they are already in leakage_hashes.json. MMLoSo 2025, CC BY-SA 4.0.
samples = []
if test_csv:
    t = pd.read_csv(test_csv[0])
    mun = t[(t.source_lang.str.lower() == "mundari")]
    for _, r in mun.sample(n=min(10, len(mun)), random_state=20260927).iterrows():
        samples.append({"row_id": str(r.row_id), "mundari": r.source_sentence})
json.dump({"source": "MMLoSo 2025 shared task, official test file (kaggle.com/competitions/mm-lo-so-2025)",
           "licence": "CC BY-SA 4.0", "split": "test", "sentences": samples},
          open(f"{PERSIST}/mmloso_test_mundari_samples.json", "w"), ensure_ascii=False, indent=1)
print(len(samples), "test-split Mundari sentences -> mmloso_test_mundari_samples.json")
'''),
    ("code", r'''
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, DataCollatorForSeq2Seq, Seq2SeqTrainer, Seq2SeqTrainingArguments
from peft import LoraConfig, get_peft_model, PeftModel
from IndicTransToolkit.processor import IndicProcessor
BASE = "ai4bharat/indictrans2-indic-indic-dist-320M"
HI, MUN = "hin_Deva", "brx_Deva"      # brx_Deva = surrogate tag for Mundari (see top)
tok = AutoTokenizer.from_pretrained(BASE, trust_remote_code=True, token=os.environ["HF_TOKEN"])
ip = IndicProcessor(inference=False)
MAXLEN = 256

def encode(src, tgt, sl, tl):
    s = ip.preprocess_batch(list(src), src_lang=sl, tgt_lang=tl, is_target=False)
    t = ip.preprocess_batch(list(tgt), src_lang=tl, tgt_lang=None, is_target=True)
    enc = tok(s, truncation=True, max_length=MAXLEN)
    lab = tok(text_target=t, truncation=True, max_length=MAXLEN)   # HF switches to the target vocabulary
    return [{"input_ids": a, "attention_mask": m, "labels": l}
            for a, m, l in zip(enc["input_ids"], enc["attention_mask"], lab["input_ids"])]
'''),
    ("code", r'''
EPOCHS, LR, BS = 3, 3e-4, 16
def train_direction(name, src, tgt, sl, tl):
    out = f"{PERSIST}/lora_{name}"
    if os.path.exists(f"{out}/final/adapter_config.json"):
        print(name, "already trained"); return f"{out}/final"
    base = AutoModelForSeq2SeqLM.from_pretrained(BASE, trust_remote_code=True, token=os.environ["HF_TOKEN"])
    cfg = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.1, task_type="SEQ_2_SEQ_LM",
                     target_modules=["q_proj", "k_proj", "v_proj", "out_proj", "fc1", "fc2"])
    model = get_peft_model(base, cfg); model.print_trainable_parameters()
    data = encode(src, tgt, sl, tl)
    args = Seq2SeqTrainingArguments(out, per_device_train_batch_size=BS, gradient_accumulation_steps=2,
        learning_rate=LR, num_train_epochs=EPOCHS, warmup_ratio=0.03, lr_scheduler_type="linear",
        fp16=True, logging_steps=50, save_steps=200, save_total_limit=2, report_to=[], seed=20260926)
    tr = Seq2SeqTrainer(model=model, args=args, train_dataset=data,
                        data_collator=DataCollatorForSeq2Seq(tok, model=model, label_pad_token_id=-100))
    last = sorted(glob.glob(f"{out}/checkpoint-*"), key=lambda p: int(p.rsplit("-", 1)[1]))
    RESUME_FROM = last[-1] if last else None
    print("resume from", RESUME_FROM)
    tr.train(resume_from_checkpoint=RESUME_FROM)
    model.save_pretrained(f"{out}/final")
    return f"{out}/final"

t0 = time.time()
ad_hi_mun = train_direction("hi_unr", train_df.hindi, train_df.mundari, HI, MUN)
print(f"hi->unr {time.time()-t0:.0f} s"); t0 = time.time()
ad_mun_hi = train_direction("unr_hi", train_df.mundari, train_df.hindi, MUN, HI)
print(f"unr->hi {time.time()-t0:.0f} s")
'''),
    ("code", r'''
# Held-out evaluation: chrF++ (word_order=2) and BLEU, sacrebleu defaults; greedy, as the app decodes.
import sacrebleu
def translate(model, texts, sl, tl, bs=32):
    ipi = IndicProcessor(inference=True); out = []
    model.eval().cuda()
    for i in range(0, len(texts), bs):
        b = ipi.preprocess_batch(texts[i:i+bs], src_lang=sl, tgt_lang=tl)
        enc = tok(b, truncation=True, max_length=MAXLEN, padding="longest", return_tensors="pt").to("cuda")
        with torch.no_grad():
            g = model.generate(**enc, num_beams=1, max_new_tokens=2 * enc["input_ids"].shape[1] + 10)
        dec = tok.batch_decode(g, skip_special_tokens=True, clean_up_tokenization_spaces=True)
        out += ipi.postprocess_batch(dec, lang=tl)
    return out

res = {"held_out_pairs": len(held_df), "train_pairs": len(train_df), "split": "sha1(normalize_key(hindi)) % 20 == 0",
       "decoding": "greedy", "surrogate_tag": MUN, "official_test": "no public references; not scored here"}
for name, ad, src, ref, sl, tl in [("hi->unr", ad_hi_mun, held_df.hindi, held_df.mundari, HI, MUN),
                                   ("unr->hi", ad_mun_hi, held_df.mundari, held_df.hindi, MUN, HI)]:
    base = AutoModelForSeq2SeqLM.from_pretrained(BASE, trust_remote_code=True, token=os.environ["HF_TOKEN"])
    m = PeftModel.from_pretrained(base, ad).merge_and_unload()
    hyp = translate(m, list(src), sl, tl)
    res[name] = {"chrF++": round(sacrebleu.corpus_chrf(hyp, [list(ref)], word_order=2).score, 2),
                 "BLEU": round(sacrebleu.corpus_bleu(hyp, [list(ref)]).score, 2),
                 "examples": [{"src": s, "ref": r, "hyp": h} for s, r, h in list(zip(src, ref, hyp))[:10]]}
    m.save_pretrained(f"{PERSIST}/merged_{name.replace('->', '_')}")
    tok.save_pretrained(f"{PERSIST}/merged_{name.replace('->', '_')}")
    print(name, res[name]["chrF++"], res[name]["BLEU"])
json.dump(res, open(f"{PERSIST}/mundari_eval.json", "w"), ensure_ascii=False, indent=1)
'''),
    ("code", r'''
# Export each merged model with the repo's own exporter (encoder, decoder_init, decoder_step + int8),
# the same graphs nmt_onnx.py runs for Santali.
for d in ("hi_unr", "unr_hi"):
    src = f"{PERSIST}/merged_{d}"
    subprocess.run([sys.executable, "repo/tools/export/export_indictrans2_onnx.py", "--model-dir", src,
                    "--out", f"{PERSIST}/onnx_{d}"], check=True)
    for f in glob.glob(f"{PERSIST}/onnx_{d}/*.onnx"):
        if not f.endswith(".int8.onnx"): os.remove(f)          # ship int8 only (as the app does)
subprocess.run(f"cd {PERSIST} && zip -qr mundari_onnx.zip onnx_hi_unr onnx_unr_hi mundari_eval.json leakage_hashes.json "
               "mmloso_test_mundari_samples.json", shell=True, check=True)
print(os.path.getsize(f"{PERSIST}/mundari_onnx.zip") / 1e6, "MB")
'''),
    ("code", r'''
# Optional: a Kaggle late-submission file for the official test (the leaderboard score is S = 0.6 BLEU + 0.4 chrF,
# weighted by direction). Only rows with a Hindi<->Mundari direction are filled; other pairs are left out.
if test_csv:
    t = pd.read_csv(test_csv[0])
    rows = []
    for d, ad, sl, tl in [("hindi->mundari", ad_hi_mun, HI, MUN), ("mundari->hindi", ad_mun_hi, MUN, HI)]:
        s_l, t_l = d.split("->")
        sub = t[(t.source_lang.str.lower() == s_l) & (t.target_lang.str.lower() == t_l)]
        if not len(sub): continue
        m = AutoModelForSeq2SeqLM.from_pretrained(f"{PERSIST}/merged_{'hi_unr' if s_l == 'hindi' else 'unr_hi'}", trust_remote_code=True)
        rows += list(zip(sub.row_id, translate(m, list(sub.source_sentence), sl, tl)))
    pd.DataFrame(rows, columns=["row_id", "target_sentence"]).to_csv(f"{PERSIST}/kaggle_mundari_rows.csv", index=False)
    print(len(rows), "rows -> kaggle_mundari_rows.csv (check the competition's sample_submission for the exact columns)")
'''),
]


VOICE = [
    ("markdown", r'''
# Our own Santali voice: fine-tune MMS-TTS (VITS) on one IndicVoices-R Santali speaker (C4)

* **Base:** `facebook/mms-tts-unr` (Mundari, a Munda language like Santali; CC BY-NC 4.0; character
  input in **Odia script**). There is no `mms-tts-sat`.
* **Text:** Ol Chiki → Devanagari (`translit/olchiki.py`) → Odia script (`translit/odia.py`), so the base
  vocabulary is kept (character-level, no espeak-ng; espeak-ng has no Santali).
* **Data:** `ai4bharat/indicvoices_r`, config **Santali** (CC BY 4.0, gated: accept the terms on the
  dataset page with your account first). One speaker: the one with the most clean hours
  (SNR ≥ 25 dB, 1–20 s clips). Speaker ID, hours and licence are written to `speaker_selection.json`.
* **Training:** `ylacombe/finetune-hf-vits` @ `6f3f51f` (MIT), with the discriminator converted from
  the original MMS checkpoint (`convert_original_discriminator_checkpoint.py --language_code unr`).
* **Export:** `tools/export/export_mms_vits_onnx.py` (this repo), tested on the laptop with mms-tts-unr.
* It ships only if it beats the live voice on the A6 round-trip CER, with a model card.

**Run on Kaggle (exact steps)**
1. kaggle.com → Settings → Phone verification done (needed for GPU and Internet).
2. Create → New Notebook → File → **Import Notebook** → upload this `.ipynb`.
3. Right panel → Session options → **Accelerator: GPU T4 x2** (or P100); **Internet: On**.
4. Add-ons → **Secrets** → Add secret: label **`HF_TOKEN`**, value = a Hugging Face **read** token → tick it
   for this notebook. (The code reads it with `UserSecretsClient`; it is never printed or saved.)
5. On huggingface.co/datasets/ai4bharat/indicvoices_r the terms must be accepted by the token's account
   (already done for this team on 25 Sep).
6. **Save Version → Save & Run All (Commit)**.
7. At the end download `santali_voice_onnx.zip` (model.onnx, tokens.txt, tts.json, tokenizer,
   speaker_selection.json, samples) into the repo's `dist/santali_voice/` and tell me.
8. If it stops (the 12 h limit): Add Input → the stopped version's output → Save & Run All again;
   finished shards are skipped and training resumes from the newest `checkpoint-*`.

**Expected runtime (T4):** metadata scan of 108 shards (columns only) ≈ 10–15 min · downloading the
chosen speaker's shards ≈ 20–60 min (depends on how many shards the speaker spans; the train split is
38.8 GB in total, only the needed shards are read) · training ≈ 2–3 h for 150 epochs on ~1–2 h of audio ·
export 5 min. **≈ 3–4.5 h.** Estimates, not measurements. A Kaggle session is limited to 12 h.
'''),
    ("code", r'''
REPO_URL = "%s"
''' % REPO + COMMON_SETUP),
    ("code", r'''
!pip install -q transformers==4.46.1 datasets==3.1.0 accelerate==1.0.1 huggingface_hub==0.26.2 pyarrow==17.0.0 \
    soundfile==0.12.1 librosa==0.10.2.post1 Cython==3.0.11 onnx==1.17.0 onnxruntime==1.19.2 "numpy<2" matplotlib tensorboard
if not os.path.exists("finetune-hf-vits"):
    subprocess.run("git clone -q https://github.com/ylacombe/finetune-hf-vits && cd finetune-hf-vits && "
                   "git checkout -q 6f3f51f4d667f5c3eef89484d151ffd39d2c2b89 && "
                   "cd monotonic_align && mkdir -p monotonic_align && python setup.py build_ext --inplace",
                   shell=True, check=True)
'''),
    ("code", HF_LOGIN),
    ("code", r'''
# 1. Speaker selection: read only the metadata columns of every Santali train shard.
import pyarrow.parquet as pq
from huggingface_hub import HfFileSystem
fs = HfFileSystem(token=os.environ["HF_TOKEN"])
shards = sorted(fs.glob("datasets/ai4bharat/indicvoices_r/Santali/train-*.parquet"))
print(len(shards), "shards")
meta_path = f"{PERSIST}/sat_meta.json"
meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
for i, sh in enumerate(shards):
    if sh in meta: continue
    with fs.open(sh, "rb") as f:
        t = pq.read_table(f, columns=["speaker_id", "duration", "snr", "gender", "text"]).to_pandas()
    meta[sh] = t.assign(text_len=t.text.str.len()).drop(columns=["text"]).to_dict("list")
    if i % 10 == 0: json.dump(meta, open(meta_path, "w")); print(i, end=" ", flush=True)
json.dump(meta, open(meta_path, "w"))
import pandas as pd
rows = pd.concat([pd.DataFrame(v).assign(shard=k) for k, v in meta.items()])
ok = rows[(rows.snr >= 25) & (rows.duration.between(1, 20))]
by = ok.groupby("speaker_id").agg(hours=("duration", lambda d: d.sum() / 3600), clips=("duration", "size"),
                                  gender=("gender", "first"), shards=("shard", "nunique")).sort_values("hours", ascending=False)
print(by.head(10))
SPEAKER = by.index[0]             # override here to choose another speaker
sel = {"dataset": "ai4bharat/indicvoices_r", "config": "Santali", "split": "train", "licence": "CC BY 4.0 (attribution)",
       "speaker_id": str(SPEAKER), "hours": round(float(by.loc[SPEAKER, "hours"]), 2),
       "clips": int(by.loc[SPEAKER, "clips"]), "gender": str(by.loc[SPEAKER, "gender"]),
       "filters": "snr >= 25 dB, 1-20 s", "top10": by.head(10).reset_index().to_dict("records")}
json.dump(sel, open(f"{PERSIST}/speaker_selection.json", "w"), indent=1, default=str)
print(sel["speaker_id"], sel["hours"], "h")
'''),
    ("code", r'''
# 2. Extract that speaker's clips (16 kHz wav) + Ol Chiki -> Odia text. Resumable per shard.
import io, soundfile as sf, librosa, numpy as np
from translit.odia import olchiki_to_odia
DATA = f"{PERSIST}/sat_speaker"; os.makedirs(f"{DATA}/wav", exist_ok=True)
need = sorted(ok[ok.speaker_id == SPEAKER].shard.unique())
done_path = f"{DATA}/done_shards.json"
done = set(json.load(open(done_path))) if os.path.exists(done_path) else set()
lines_path = f"{DATA}/lines.jsonl"
for sh in need:
    if sh in done: continue
    with fs.open(sh, "rb") as f:
        t = pq.read_table(f, columns=["speaker_id", "duration", "snr", "text", "audio"]).to_pandas()
    t = t[(t.speaker_id == SPEAKER) & (t.snr >= 25) & t.duration.between(1, 20)]
    with open(lines_path, "a", encoding="utf-8") as out:
        for _, r in t.iterrows():
            a, sr = sf.read(io.BytesIO(r.audio["bytes"]), dtype="float32")
            if a.ndim > 1: a = a.mean(1)
            a = librosa.resample(a, orig_sr=sr, target_sr=16000)
            name = hashlib.sha1(r.audio["bytes"][:4096]).hexdigest()[:16] + ".wav"
            sf.write(f"{DATA}/wav/{name}", a, 16000, subtype="PCM_16")
            out.write(json.dumps({"file_name": f"wav/{name}", "olchiki": r.text,
                                  "text": olchiki_to_odia(r.text)}, ensure_ascii=False) + "\n")
    done.add(sh); json.dump(sorted(done), open(done_path, "w")); print("shard done", sh.rsplit("/", 1)[1])
lines = [json.loads(l) for l in open(lines_path, encoding="utf-8")]
lines = list({l["file_name"]: l for l in lines}.values())
print(len(lines), "clips")
'''),
    ("code", r'''
# 3. Vocabulary check against the base model, hold out 20 clips for listening/CER, write metadata.csv.
from transformers import AutoTokenizer
base_tok = AutoTokenizer.from_pretrained("facebook/mms-tts-unr")
vocab = set(base_tok.get_vocab())
oov = {}
for l in lines:
    for c in l["text"]:
        if c != " " and c not in vocab: oov[c] = oov.get(c, 0) + 1
chars = sum(len(l["text"]) for l in lines)
print("out-of-vocabulary characters (dropped by the tokenizer):", oov, f"= {sum(oov.values()) / chars:.2%} of characters")
random.seed(20260926); random.shuffle(lines)
held, train = lines[:20], lines[20:]
import csv
with open(f"{DATA}/metadata.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["file_name", "text"])
    for l in train: w.writerow([l["file_name"], l["text"]])
json.dump(held, open(f"{PERSIST}/held_out_clips.json", "w"), ensure_ascii=False, indent=1)
print(len(train), "train clips,", len(held), "held out")
'''),
    ("code", r'''
# 4. Base checkpoint with a discriminator (converted from the original MMS unr checkpoint, CC BY-NC 4.0).
BASE_TRAIN = f"{PERSIST}/mms-unr-train"
if not os.path.exists(f"{BASE_TRAIN}/config.json"):
    subprocess.run(["python", "convert_original_discriminator_checkpoint.py", "--language_code", "unr",
                    "--pytorch_dump_folder_path", BASE_TRAIN], cwd="finetune-hf-vits", check=True)
'''),
    ("code", r'''
# 5. Fine-tune. Resumes from the newest checkpoint-* in OUT.
OUT = f"{PERSIST}/santali_voice_run"
cfg = {
  "project_name": "nijbhasha_santali_voice", "push_to_hub": False, "report_to": ["tensorboard"],
  "overwrite_output_dir": False, "output_dir": OUT, "resume_from_checkpoint": "latest",
  "dataset_name": DATA, "audio_column_name": "audio", "text_column_name": "text",
  "train_split_name": "train", "eval_split_name": "train",
  "full_generation_sample_text": held[0]["text"],
  "max_duration_in_seconds": 20, "min_duration_in_seconds": 1.0, "max_tokens_length": 500,
  "model_name_or_path": BASE_TRAIN, "preprocessing_num_workers": 2,
  "do_train": True, "num_train_epochs": 150, "gradient_accumulation_steps": 1, "gradient_checkpointing": False,
  "per_device_train_batch_size": 16, "learning_rate": 2e-5, "adam_beta1": 0.8, "adam_beta2": 0.99,
  "warmup_ratio": 0.01, "group_by_length": False,
  "do_eval": True, "eval_steps": 200, "per_device_eval_batch_size": 16, "max_eval_samples": 8,
  "do_step_schedule_per_epoch": True, "save_steps": 500, "save_total_limit": 2,
  "weight_disc": 3, "weight_fmaps": 1, "weight_gen": 1, "weight_kl": 1.5, "weight_duration": 1, "weight_mel": 35,
  "fp16": True, "seed": 456}
json.dump(cfg, open("finetune-hf-vits/santali.json", "w"), ensure_ascii=False, indent=1)
t0 = time.time()
subprocess.run("accelerate launch run_vits_finetuning.py santali.json", shell=True, cwd="finetune-hf-vits", check=True)
print(f"training {time.time() - t0:.0f} s")
'''),
    ("code", r'''
# 6. Export (the repo's exporter) + samples of the 20 held-out sentences, then zip.
EXP = f"{PERSIST}/santali_voice_onnx"
subprocess.run([sys.executable, "repo/tools/export/export_mms_vits_onnx.py", "--model", OUT, "--out", EXP,
                "--check-text", held[0]["text"]], check=True)
from transformers import VitsModel
m = VitsModel.from_pretrained(OUT).eval().cuda(); tk = AutoTokenizer.from_pretrained(OUT)
os.makedirs(f"{EXP}/samples", exist_ok=True)
for i, l in enumerate(held):
    with torch.no_grad():
        w = m(**tk(l["text"], return_tensors="pt").to("cuda")).waveform[0].cpu().numpy()
    sf.write(f"{EXP}/samples/{i:02d}.wav", w, m.config.sampling_rate)
json.dump(held, open(f"{EXP}/samples/texts.json", "w"), ensure_ascii=False, indent=1)
subprocess.run(f"cp {PERSIST}/speaker_selection.json {EXP}/ && cd {PERSIST} && zip -qr santali_voice_onnx.zip santali_voice_onnx", shell=True, check=True)
print(os.path.getsize(f"{PERSIST}/santali_voice_onnx.zip") / 1e6, "MB")
'''),
]


def main():
    d = ROOT / "notebooks"
    d.mkdir(exist_ok=True)
    for name, cells in (("mundari_lora", MUNDARI), ("santali_voice", VOICE)):
        (d / f"{name}.ipynb").write_text(json.dumps(nb(cells), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("wrote", d / f"{name}.ipynb")


if __name__ == "__main__":
    main()
