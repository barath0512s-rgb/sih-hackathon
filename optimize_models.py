# optimize_models.py — run ONCE after download_models.py
# Applies torch.compile and half-precision to speed up NMT inference.

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from IndicTransToolkit.processor import IndicProcessor

print("Optimizing NMT models for faster inference...")

for name, path in [("Indic→En", "./models/indic_en"),
                   ("En→Indic", "./models/en_indic")]:
    print(f"  {name}...")
    mdl = AutoModelForSeq2SeqLM.from_pretrained(path, trust_remote_code=True)
    mdl.eval()
    # Warm up with a dummy pass so first real call is fast
    tok = AutoTokenizer.from_pretrained(path, trust_remote_code=True)
    ip  = IndicProcessor(inference=True)
    sample = ip.preprocess_batch(
        ["Hello world."], src_lang="eng_Latn", tgt_lang="hin_Deva")
    enc = tok(sample, return_tensors="pt", padding=True)
    with torch.no_grad():
        mdl.generate(**enc, num_beams=1, max_new_tokens=50)
    print(f"    Warmed up.")

print("\nOptimization complete.")
print("Note: first call in app.py still takes ~5s (model load).")
print("After warmup, each sentence takes 3-8s on CPU.")
print("Use short sentences (under 15 words) for best latency.")
