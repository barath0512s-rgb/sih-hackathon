# F1 M1 on Android SDK built for x86_64 (emulator-2gb-android9)

- Date: 2026-09-25. Device: Android SDK built for x86_64, Android 9 (SDK 28), x86_64, 4 cores, RAM 2.0 GB (MemTotal).
- APK: `app-debug.apk` (3.8 MB). Pack: `content-pack-20260925-1816.zip` (32.8 MB): {"lessons": 17, "flashcard_decks": 17, "translations_hi_to_sat": 189, "translations_sat_to_hi": 18, "audio_clips": 399}.
- No speech, translation or voice engine is on the device in M1: those contract cases must answer 503 engine_not_on_device, and they did if they are not listed as failures.

| Check | Result |
|---|---|
| Pack import (copy, SHA-256 check of every file, install) | 7.6 s |
| REST contract, network on | 24 of 24 cases pass |
| REST contract, airplane mode (airplane_mode_on=1) | 24 of 24 cases pass |
| Typed lesson line from the pack, round trip over adb forward (20 runs) | median 31 ms, max 59 ms |
| Native mic (MicBridge, 3 s, 16 kHz) | 3.00 s of audio, RMS 0.0049, peak 0.013 |
| Peak PSS (dumpsys meminfo every 1 s, 10 samples): app process / WebView renderer / sum | 89 / 96 / **185 MB** |
