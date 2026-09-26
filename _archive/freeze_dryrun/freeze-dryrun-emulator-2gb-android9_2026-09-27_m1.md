# F1 M1 on google Android SDK built for x86_64 (freeze-dryrun-emulator-2gb-android9)

- Date: 2026-09-27. Read from the device: Google Android SDK built for x86_64 (generic_x86_64), Android 9 (SDK 28), sdk_gphone_x86_64-userdebug 9 PSR1.180720.122 6736742 dev-keys, SoC ranchu (board ), x86_64, 4 cores, RAM 2.0 GB (MemTotal 2046740 kB); WebView: com.google.android.webview 69.0.3497.100, in use com.android.chrome 69.0.3497.100.
- APK tested: `app-release.apk` (72.2 MB). Pack: `content-pack-20260927-0057.zip` (37.8 MB): {"lessons": 18, "flashcard_decks": 18, "translations_hi_to_sat": 203, "translations_sat_to_hi": 18, "audio_clips": 427}.
- No speech, translation or voice engine is on the device in M1: the contract cases that need one must answer 503 engine_not_on_device, and they did unless listed as failures.
- Manual steps asked for during the run: none.

| Check | Result |
|---|---|
| Pack import (push + SHA-256 check of every file + install, release build) | 13.3 s |
| REST contract, network on | 24 of 24 cases pass |
| Page in the WebView, airplane mode on (airplane_mode_on=1) | lesson lines listed: yes; line chosen: yes; Translate gave Santali: yes |
| REST contract, airplane mode | 24 of 24 cases pass |
| Typed lesson line from the pack, round trip over adb forward (20 runs) | median 30 ms, max 74 ms |
| Native mic, build under test, through the page (Hindi mic pressed for about 3 s) | 109490 bytes uploaded, about 3.4 s of 16 kHz audio |
| Native mic (MicBridge, 3 s, 16 kHz; debug build of the same code) | 3.02 s of audio, RMS 0.0001, peak 0.000 |
| Peak PSS over all stages (dumpsys meminfo every 1 s, 45 samples): app / WebView renderer / sum | 85 / 105 / **186 MB** |

Santali shown after Translate: ᱵᱟᱨ ᱩᱞ ᱟᱨ ᱯᱮ ᱩᱞ ᱢᱮᱥᱟᱣ ᱢᱮ। ᱡᱚᱛᱚ ᱛᱤᱱᱟᱜ ᱦᱩᱭᱮᱱᱟ? ᱩᱝᱜᱽᱞᱤ ᱨᱮ ᱜᱤᱱᱛᱤ ᱢᱮ।
