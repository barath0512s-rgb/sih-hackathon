# Latency, three runs (hp1, hp2, hp3)

Laptop on AC power, Windows power mode Best performance, other apps closed (set by the user). Offline. Every run is listed; the last column is the median of the three runs' p90s. Distinct sentences only (the first clip of each): n = clips, n_distinct = sentences used.

**Definitions.** Neither measure includes the endpointing wait: the silence endpoint (500 ms, 1000 ms after 2.5 s of speech) is a setting, off by default; with it on, add at least that wait. Neither includes Wi-Fi or the browser starting playback.
- **From the end of speech** (`bench/latency_steps.py`, Hindi -> Santali): starts when the recorded audio, already a WAV file, is handed to speech recognition in the same process. **Full time** stops when the Santali audio for the whole utterance is written (not streamed). **Time to first audio** stops when the first clause chunk's audio is written (streamed; computed for every clip, although the app streams only utterances of 18+ words). **Time to last audio**: the last chunk's audio. For each clip the benchmark runs the whole path and then the streamed path, and goes straight on to the next clip.
- **Upload to reply audio** (`bench/bench_latency.py`, both directions): starts when the request with the audio file is sent to the app in the same process (Flask test client, no network); includes saving the upload, re-encoding it with ffmpeg, speech recognition, the translation layers (teacher, glossary, cache, model), synthesis and downloading the reply audio; stops when the reply audio is received. Whole utterance, not streamed. One request after another.
- **Why the end-of-speech full time has the longer tail (p90 3.67 vs 2.38 s, medians 2.11 vs 2.03 s in run 3): an explanation, partly supported, not a result.** The medians agree; the tail comes from speech recognition. In the end-of-speech runs the same six clips were slow every time (ASR median 2.02 s, full 4.17 s); each follows a clip with about twice the usual streaming work (3.5 vs 1.9 s), run just before with no pause. Re-run after a 1 s idle pause (`bench/results/pause_check.md`), the six clips took ASR 1.16 s, full 3.13 s (median): the preceding work explains about half the extra time, not all of it (alone, with only the ASR model loaded, ASR took 0.76 s). So the upload figure may be closer to a line spoken after a pause, but that is not measured in class.
- **Streaming threshold:** on the saved runs, streaming brings the first sound forward by a median 0.25-0.29 s for 12-17 words but delays the last audio by 0.65-0.70 s; for 18+ words it gains 0.48-0.60 s. The app streams only 18+ words (`config.STREAM_MIN_WORDS = 18`); the data support it.
- Rows with fewer than 10 distinct sentences are marked **small sample**. The headline is the **<= 17-word** row.

## From the end of speech: FLEURS Hindi -> Santali (`bench/latency_steps.py --backend app`)

Time to first audio (clause streaming) and full time (whole utterance voiced), p90 in seconds.

| Words | n | n_distinct | hp1: first / full | hp2: first / full | hp3: first / full | Median of p90s: first / full |
|---|---|---|---|---|---|---|
| all | 80 | 69 | 3.40 / 4.08 | 2.75 / 3.62 | 2.54 / 3.67 | **2.75 / 3.67** |
| ≤ 17 | 37 | 32 | 2.41 / 2.96 | 2.42 / 2.85 | 2.14 / 2.75 | **2.41 / 2.85** |
| 0-11 (small sample) | 3 | 3 | 2.23 / 3.29 | 2.47 / 3.21 | 2.13 / 2.90 | **2.23 / 3.21** |
| 12-17 | 34 | 29 | 2.59 / 2.96 | 2.42 / 2.85 | 2.21 / 2.75 | **2.42 / 2.85** |
| 18-23 | 34 | 28 | 3.74 / 4.93 | 3.25 / 4.19 | 3.40 / 4.76 | **3.40 / 4.76** |
| 24+ (small sample) | 9 | 9 | 3.71 / 4.33 | 3.40 / 4.09 | 3.10 / 3.68 | **3.40 / 4.09** |

Source files: `latency_steps_app_hp1.csv`, `latency_steps_app_hp2.csv`, `latency_steps_app_hp3.csv`

## Upload to reply audio, both directions (`bench/bench_latency.py`, public clips)

Full time (no streaming in this path), p90 in seconds. Santali clips: IndicVoices validation split (no public Santali test split); may overlap model-development data. Word bins count the reference words of the spoken sentence.

| Direction | Words | n | n_distinct | hp1 | hp2 | hp3 | Median of p90s |
|---|---|---|---|---|---|---|---|
| hi-to-sat | all | 79 | 68 | 2.93 | 2.38 | 2.37 | **2.38** |
| hi-to-sat | ≤ 17 | 40 | 34 | 2.60 | 2.14 | 2.09 | **2.14** |
| hi-to-sat | 0-11 (small sample) | 4 | 4 | 2.22 | 1.87 | 1.87 | **1.87** |
| hi-to-sat | 12-17 | 36 | 30 | 2.60 | 2.14 | 2.09 | **2.14** |
| hi-to-sat | 18-23 | 32 | 27 | 3.17 | 2.47 | 2.37 | **2.47** |
| hi-to-sat | 24+ (small sample) | 7 | 7 | 3.32 | 3.22 | 2.61 | **3.22** |
| sat-to-hi | all | 80 | 80 | 2.60 | 2.52 | 2.58 | **2.58** |
| sat-to-hi | 0-10 | 42 | 42 | 2.27 | 2.23 | 2.29 | **2.27** |
| sat-to-hi | 11-17 | 25 | 25 | 2.62 | 2.55 | 2.69 | **2.62** |
| sat-to-hi | 18+ | 13 | 13 | 2.94 | 2.80 | 2.75 | **2.80** |

Source files: `Dell-Inc-Dell-G15-5520_2026-09-26_public_hp1.csv`, `Dell-Inc-Dell-G15-5520_2026-09-26_public_hp2.csv`, `Dell-Inc-Dell-G15-5520_2026-09-26_public_hp3.csv`
