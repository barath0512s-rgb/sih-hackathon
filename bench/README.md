# Benchmarks

Every latency number in the README comes from a script here. Re-run them after
changing a model, a decoding setting, or the hardware.

| Script | Measures | Output |
|---|---|---|
| `bench_latency.py` | Recorded clips through the real app: upload → ASR → NMT → TTS → reply audio received. Median, p90, max per direction | `results/<device>_<date>_<label>.{csv,md}` |
| `asr_decoding.py` | RNN-T vs CTC decoding, with and without silence trimming: ASR time and CER per language | `results/asr_decoding_<label>.md` |
| `cold_start.py` | Whether the first request after the server starts costs extra (fresh app processes) | `results/cold_start.md` |
| `nmt_limits.py` | Whether sizing the NMT decode limit to the input saves time or changes output | `results/nmt_limits.md` |
| `tts_first_sentence.py` | The most that playing the first sentence early could save | `results/tts_first_sentence.md` |
| `make_synthetic_clips.py` | Makes the synthetic clips below | `clips/synthetic/` |

## What `bench_latency.py` does and does not measure

`pipeline_ms` runs from the start of the upload to the reply audio being fully
received, with the app in-process: it **excludes Wi-Fi**. What a teacher
actually waits is measured in the browser, from releasing the microphone to the
reply audio starting to play; every browser reports that to the server, and
`GET /metrics/latency` summarises it per path. On the laptop itself the two
differ by the time to fetch, decode and start the audio (~0.25 s in one
measured request).

Both benchmark runs start with empty caches and a throw-away database.

## Synthetic clips (what exists today)

`clips/synthetic/` holds 30 Hindi and 30 Santali lines read by the Piper
`hi_IN-pratham-medium` voice, padded with silence (0.8 s before, 0.6 s after)
and encoded to WebM/Opus like the browser's recordings. Regenerate with
`python bench/make_synthetic_clips.py` (the audio files are git-ignored; the
manifest is not).

They are good for **timing**. They are **not** good for accuracy: the voice is
clean and synthetic, so the CER columns compare settings on identical audio and
say nothing about accuracy on children or teachers in a noisy classroom.

## Public-dataset clips (adult speech)

`fetch_public_clips.py` downloads a fixed, seeded selection of public clips.
Only the manifest (`clips/public/manifest.json`) is in git. Each entry records
the dataset, revision, file, row, licence and the SHA-256 of the audio, so a
re-fetch can be checked with `--check`.

| Language | Source | Licence | Status |
|---|---|---|---|
| Hindi | `google/fleurs`, `hi_in` test: 80 of the 187 utterances of 3-10 s | CC BY 4.0 | fetched |
| Santali | `ai4bharat/IndicVoices`, `santali` **valid** split (the dataset has no test split): 80 clips of 3-10 s, 62 speakers | CC BY 4.0 | fetched (gated: accept the terms first) |

```bash
python bench/fetch_public_clips.py
python bench/asr_decoding.py  --clips bench/clips/public/manifest.json --label public
python bench/bench_latency.py --clips bench/clips/public/manifest.json --label public
python tools/deck_numbers.py --write
```

Every result from these clips is labelled **"public dataset, adult speech"**.
None of them is child speech: child-speech accuracy is **NOT MEASURED**.
`asr_decoding.py` reports corpus-level WER and CER (all errors over all
reference words or characters), two ways.

### WER normalisation

- **Raw WER**: the dataset's transcript and the recogniser's output exactly as
  written, split on spaces.
- **Normalised WER and CER**: both sides through `textnorm.normalize_for_wer`,
  the same rules for Hindi and Santali:
  1. Unicode NFC (two encodings of the same letter compare equal).
  2. Dataset annotation tags in angle brackets are removed (IndicVoices writes
     `<unintelligible>`; no recogniser outputs it). 2 of the 80 Santali
     transcripts have one.
  3. Every punctuation mark (Unicode category P) becomes a space: `, . ? ! : ;`
     hyphens and quotes, Devanagari `।` `॥`, Ol Chiki `᱾` `᱿`.
  4. Devanagari digits (०-९) and Ol Chiki digits (᱐-᱙) become ASCII digits.
  5. Whitespace is collapsed to single spaces and trimmed.

  Nothing else changes. Spelling variants still count as errors (nukta,
  chandrabindu vs anusvara, Latin case), and so do numbers written as digits
  on one side and as words on the other. (The app's answer matching,
  `textnorm.normalize_key`, is looser: it also folds nukta and chandrabindu.
  It is not used for WER.)

## Real recordings (needed)

Put 10 or more real teacher (Hindi) and child (Santali) recordings in
`clips/real/`, with a `clips/real/manifest.json` in the same format as
`clips/synthetic/manifest.json`:

```json
[
  {"file": "bench/clips/real/hi_01.webm", "lang": "hi",
   "reference": "exact words spoken, as text", "kind": "real: teacher, classroom"},
  {"file": "bench/clips/real/sat_01.webm", "lang": "sat",
   "reference": "ᱮᱠᱟᱞ ᱚᱞ ᱪᱤᱠᱤ ᱛᱮ", "kind": "real: child, classroom"}
]
```

Any format ffmpeg reads works (WebM, WAV, M4A, MP3). The `reference` must be
what was actually said, in Devanagari or Ol Chiki. Then:

```bash
python bench/bench_latency.py --clips bench/clips/real/manifest.json --label real
python bench/asr_decoding.py  --clips bench/clips/real/manifest.json --label real
```

The ASR settings in `config.py` (`ASR_DECODING`, `ASR_TRIM_SILENCE`) were chosen
on synthetic clips and should be re-checked with `asr_decoding.py` on real ones.
