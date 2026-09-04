# VaaniSetu Progress & Workflow Architecture

This document logs the major architectural decisions and pipeline optimizations applied to VaaniSetu to meet the strict latency and accuracy requirements for live classroom deployment.

## Phase 1: Native Speech Recognition (ASR) Upgrade
- **Problem:** Whisper Small had a 2/10 success rate detecting Hindi and was highly inconsistent with microphone noise.
- **Solution:** Swapped Whisper for **AI4Bharat IndicConformer (600M)** ONNX models.
- **Optimization:** Upgraded from fast CTC decoding to **RNN-T decoding**. RNN-T utilizes a joint language model network to intelligently predict words based on context, drastically improving microphone consistency and accuracy for both Hindi and Santali accents.
- **Implementation:** `indicconformer_asr.py` handles the ONNX initialization (loading all 22 language heads), and `_to_wav` in `pipeline.py` uses `ffmpeg` to format browser `.webm` recordings to 16kHz float32 arrays on the fly.

## Phase 2: NMT Latency & Pivot Removal
- **Problem:** Translation took 2 passes (Hindi -> English -> Santali) using two 200M models, doubling latency and dropping grammatical gender/respect context in the English pivot.
- **Solution:** Implemented the massive **`ai4bharat/indictrans2-indic-indic-dist-320M`** direct translation model.
- **Optimization:** To ensure CPU execution remains fast, **Greedy Search** decoding (`num_beams=1`) was implemented, bypassing the heavy beam-search algorithms. NMT generation now takes ~0.4 seconds on a standard CPU.

## Phase 3: The TTS Bottleneck & Transliteration Fix
- **Problem:** Parler-TTS, an auto-regressive speech LLM, was taking ~30 seconds to generate audio on CPU, blowing past the strict <10s requirement. Dynamic INT8 Quantization was tested but caused PyTorch CPU dispatch regressions.
- **Solution:** Removed Parler-TTS entirely. 
- **Optimization (Phonetic Transliteration):** Santali Ol Chiki script (which is completely unsupported by fast TTS engines) is now mapped character-by-character to the Latin alphabet natively in Python. The Latin text is then passed to `gTTS` (Google TTS API) using an Indian accent identifier (`tld='co.in'`). 
- **Result:** Phonetic Santali speech is generated and streamed back in **~0.5 seconds**, bringing the *entire pipeline latency to under 4 seconds*.

## Phase 4: Instant Learning & Feedback Loop
- **Problem:** The model needed to learn from incorrect classroom translations dynamically.
- **Solution:** Added a UI feedback loop (👍/👎 buttons on translations).
- **Implementation:** 
  - `database.py` logs all user corrections to `vaanisetu_feedback.db`. 
  - `pipeline.py` intercepts translations and checks the database *before* running the ML models. If a human-corrected translation exists for a given input, it instantly bypasses NMT and returns the 100% accurate string.
  - `train_nmt.py` allows offline LoRA fine-tuning on the accumulated SQLite feedback data.

## Phase 5: TTS Caching
- **Solution:** Added MD5-based `.wav` caching (`./tts_cache/`). Commonly repeated classroom phrases (e.g., "What is your name?", "Sit down") hit the cache and return audio instantly (0.01s) without hitting the network.
