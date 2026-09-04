$env:PYTHONIOENCODING = "utf-8"

# Activate virtual environment
.\vaanisetu_env\Scripts\activate

# Install the exact transformers version that works with both parler_tts and IndicTrans2
pip install "transformers==4.46.1" "tokenizers==0.20.3" "huggingface_hub>=0.21.0,<1.0"

# Login to Hugging Face
huggingface-cli login

# Download all models (Step 2 of guide)
python download_models.py

# Optimize models (Step 3 of guide)
python optimize_models.py

# Run all 7 tests (Step 8 of guide)
python test_pipeline.py
