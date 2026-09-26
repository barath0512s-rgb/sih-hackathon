# F1 M1 on Google Android SDK built for x86_64 (emulator-2gb-android9)

- Date: 2026-09-26. Device: Google Android SDK built for x86_64, Android 9 (SDK 28), x86_64, CPU ?, 4 cores, RAM 2.0 GB (MemTotal 2046740 kB), WebView com.android.chrome 69.0.3497.100.
- APK tested: `app-release.apk` (3.0 MB). Pack: `content-pack-20260925-1816.zip` (32.8 MB): {"lessons": 17, "flashcard_decks": 17, "translations_hi_to_sat": 189, "translations_sat_to_hi": 18, "audio_clips": 399}.
- No speech, translation or voice engine is on the device in M1: the contract cases that need one must answer 503 engine_not_on_device, and they did unless listed as failures.

| Check | Result |
|---|---|
| Pack import (push + SHA-256 check of every file + install, release build) | 7.2 s |
| REST contract, network on | 24 of 24 cases pass |
| Page in the WebView, airplane mode on (airplane_mode_on=1) | lesson lines listed: yes; line chosen: yes; Translate gave Santali: yes |
| REST contract, airplane mode | 24 of 24 cases pass |
| Typed lesson line from the pack, round trip over adb forward (20 runs) | median 21 ms, max 36 ms |
| Native mic (MicBridge, 3 s, 16 kHz; debug build of the same code) | 3.02 s of audio, RMS 0.0035, peak 0.014 |
| Peak PSS during the checks and the typed lesson (dumpsys meminfo every 1 s, 30 samples): app / WebView renderer / sum | 77 / 98 / **174 MB** |

Santali shown after Translate: ᱵᱟᱨ ᱩᱞ ᱟᱨ ᱯᱮ ᱩᱞ ᱢᱮᱥᱟᱣ ᱢᱮ। ᱡᱚᱛᱚ ᱛᱤᱱᱟᱜ ᱦᱩᱭᱮᱱᱟ? ᱩᱝᱜᱽᱞᱤ ᱨᱮ ᱜᱤᱱᱛᱤ ᱢᱮ।

Screen recording: `docs/demo_assets/android_emulator.mp4` (6.7 MB).
