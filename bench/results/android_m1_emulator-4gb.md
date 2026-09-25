# F1 M1 on sdk_gphone16k_x86_64 (emulator-4gb)

- Date: 2026-09-25. Device: sdk_gphone16k_x86_64, Android 17 (SDK 37), x86_64, 4 cores, RAM 3.8 GB (MemTotal).
- APK: `app-debug.apk` (3.6 MB). Pack: `content-pack-20260925-1816.zip` (32.8 MB): {"lessons": 17, "flashcard_decks": 17, "translations_hi_to_sat": 189, "translations_sat_to_hi": 18, "audio_clips": 399}.
- No speech, translation or voice engine is on the device in M1: those contract cases must answer 503 engine_not_on_device, and they did if they are not listed as failures.

| Check | Result |
|---|---|
| Pack import (copy, SHA-256 check of every file, install) | 3.3 s |
| REST contract, network on | 24 of 24 cases pass |
| REST contract, airplane mode (airplane_mode_on=1) | 24 of 24 cases pass |
| Typed lesson line from the pack, round trip over adb forward (20 runs) | median 35 ms, max 62 ms |
| App PSS after the checks (dumpsys meminfo) | 117 MB |
