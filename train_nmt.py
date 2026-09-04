import os
import torch

try:
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, Seq2SeqTrainingArguments, Seq2SeqTrainer
    from datasets import load_dataset
except ImportError:
    print("Run: pip install transformers datasets peft accelerate evaluate")
    exit(1)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
if DEVICE == "cpu":
    print("⚠️ WARNING: You are running this on a CPU. Fine-tuning a 320M parameter model will take weeks.")
    print("For SIH 2026, upload this script and 'nipun_hindi_santali.csv' to Google Colab Pro or RunPod (A100 GPU).")

# 1. We use the DIRECT Indic-to-Indic model, bypassing English completely!
MODEL_ID = "ai4bharat/indictrans2-indic-indic-dist-320M"

print("Loading tokenizer and base model...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_ID, trust_remote_code=True)

# 2. Apply LoRA (Low-Rank Adaptation)
# This allows us to train the model on a tiny GPU budget by only updating 1% of the brain
config = LoraConfig(
    r=16, 
    lora_alpha=32, 
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"], # Attention layers
    lora_dropout=0.05,
    bias="none",
    task_type="SEQ_2_SEQ_LM"
)
model = get_peft_model(model, config)
print(f"Trainable parameters: {model.get_nb_trainable_parameters()}")

# 3. Load our custom NIPUN dataset
print("Loading classroom dataset...")
dataset = load_dataset("csv", data_files="training_data/nipun_hindi_santali.csv")

def preprocess_function(examples):
    # Setup inputs (Hindi)
    inputs = examples["hindi"]
    model_inputs = tokenizer(inputs, max_length=128, truncation=True, padding="max_length")

    # Setup labels (Santali)
    labels = tokenizer(text_target=examples["santali"], max_length=128, truncation=True, padding="max_length")
    
    # -100 tells PyTorch to ignore padding tokens when calculating loss
    labels["input_ids"] = [
        [(l if l != tokenizer.pad_token_id else -100) for l in label] for label in labels["input_ids"]
    ]
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

tokenized_datasets = dataset.map(preprocess_function, batched=True)

# 4. Define Training Parameters
training_args = Seq2SeqTrainingArguments(
    output_dir="./vaanisetu_nmt_finetuned",
    learning_rate=2e-4, # Slightly higher for LoRA
    per_device_train_batch_size=8,
    weight_decay=0.01,
    save_total_limit=2,
    num_train_epochs=10, 
    predict_with_generate=True,
    fp16=torch.cuda.is_available(), # Use Mixed Precision if on GPU
    logging_steps=5,
)

# 5. Train
trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets["train"],
    tokenizer=tokenizer,
)

print("Starting Fine-Tuning... (This will take a long time on CPU)")
trainer.train()

# 6. Save the new adapter weights
model.save_pretrained("models/indic_indic_finetuned")
print("✅ Fine-tuning complete! Weights saved to models/indic_indic_finetuned")
