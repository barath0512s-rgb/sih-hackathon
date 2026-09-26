# Demo video assets

Recorded with `adb screenrecord` by `tools/android/device_check.py --record ...`.
Each clip is shown with its caption exactly as written here.

| File | Caption (exact) | Evidence |
|---|---|---|
| `android_emulator.mp4` | Android 9 emulator, 2 GB RAM, airplane mode: app shell + typed translation. On-device speech and AI: in progress. | `bench/results/emulator-2gb-android9_<date>_m1.md` |
| `android_samsung.mp4` (recorded only after "Samsung connected") | Samsung tablet, 4 GB RAM, Android 13, airplane mode: app shell + typed translation. On-device speech and AI: in progress. | `bench/results/samsung-4gb-android13_<date>_m1.md` |

Line shown under either clip: "On a 2 GB RAM, Android 9 emulator: peak memory
185 MB; 24 of 24 app checks pass in airplane mode." (`bench/results/android_m1_emulator-2gb-android9.md`)
