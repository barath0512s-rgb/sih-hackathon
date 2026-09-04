# VaaniSetu (वाणीসেতু)

VaaniSetu is a real-time, bidirectional Hindi ↔ Santali translation platform designed for classroom learning and rural education. It aims to bridge the language gap for Santali-speaking students by providing an ultra-low latency (<4s) translation pipeline featuring native speech recognition (ASR) and text-to-speech (TTS) optimized for CPU execution.

## Features
- **Ultra-Low Latency Pipeline:** Hindi to Santali speech-to-speech translation in under 4 seconds.
- **Native IndicConformer ASR:** Uses AI4Bharat's IndicConformer (600M) running on ONNX with RNN-T decoding for highly accurate Hindi and Santali microphone transcription, heavily robust against classroom noise.
- **Direct NMT (No English Pivot):** Uses `ai4bharat/indictrans2-indic-indic-dist-320M` for direct Hindi to Santali translation (and vice versa), maintaining grammatical gender and respect markers.
- **Phonetic TTS Transliteration:** Automatically transliterates Santali Ol Chiki script into Latin for blazing-fast phonetic audio generation via `gTTS`.
- **Instant TTS Caching:** MD5 hashed audio cache to instantly return audio for known classroom phrases (0.01s).
- **Instant Learning (Feedback DB):** Built-in UI to flag translations as 👍/👎. Corrections are logged to SQLite (`vaanisetu_feedback.db`) for future LoRA fine-tuning and instant cache overriding.

## Setup Instructions

### 1. Environment Setup
Requires Python 3.10+ and `ffmpeg` installed on your system path.
```bash
python -m venv vaanisetu_env
# Windows
.\vaanisetu_env\Scripts\activate
# Mac/Linux
source vaanisetu_env/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Model Download
The `pipeline.py` script automatically downloads the required AI4Bharat models via HuggingFace on first boot. 
*Note: You must be logged in to HuggingFace CLI with a token that has access to `ai4bharat/indictrans2-indic-indic-dist-320M` and `ai4bharat/indic-conformer-600m-multilingual`.*

### 4. Run the Server
```bash
python app.py
```
The application will be available at `http://127.0.0.1:5000`.

## Directory Structure
- `app.py`: Flask web server and API endpoints (`/translate/audio`, `/translate/text`, `/feedback`).
- `pipeline.py`: Core ML logic (ASR, NMT, TTS caching, transliteration).
- `indicconformer_asr.py`: ONNX-based native speech recognition wrapper.
- `database.py`: SQLite integration for the Feedback loop.
- `frontend.html`: Web interface for the teacher/student dashboard.
- `train_nmt.py`: Script for LoRA fine-tuning based on DB feedback.
