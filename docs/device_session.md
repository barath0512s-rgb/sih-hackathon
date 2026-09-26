# Device session: Realme Pad Mini (F1 M1 on a real tablet + hub-mode microphone)

The tablet: **Realme Pad Mini, 4 GB RAM, 64 GB storage, Android 11** (as given; the
check reads model, Android version, SoC, RAM and WebView version from the device
itself and reports those). Everything measured here is labelled **"4 GB, Android
11"**; it is never a 2 GB measurement. The 2 GB evidence stays the Android 9
emulator (`bench/results/android_m1_emulator-2gb-android9.md`,
`bench/results/emulator-2gb-android9_2026-09-26_m1.md`).

Trigger: when you say **"Realme connected"**, I run B, B2, then C, then report, then
update `main`, push and tag `v0.95-submission`.

## A. Before plugging in (on the tablet)

1. Settings → About tablet → Version → tap **Build number** 7 times (enter the lock
   screen PIN if asked).
2. Settings → Additional settings → **Developer options**:
   - **USB debugging**: on;
   - **Install via USB**: on (Realme may ask you to sign in or insert a SIM once);
   - **Disable permission monitoring**: on (lets adb tap the screen and read it for
     the page check).
3. Plug in over USB; on the tablet accept **"Allow USB debugging?"** (tick "Always allow").

## B. The app check (I run this; it stops and tells you when it needs you)

```bash
python tools/android/device_check.py --apk android/app/build/outputs/apk/release/app-release.apk --debug-apk android/app/build/outputs/apk/debug/app-debug.apk --pack <newest dist/packs/content-pack-*.zip> --label realme-pad-mini-4gb-android11 --record docs/demo_assets/android_realme.mp4
```

It stops with **ACTION NEEDED** (and I relay the exact taps) when:
- the install is refused → turn on "Install via USB"; tap **Install** if the tablet asks;
- taps or the screen dump are refused → turn on "Disable permission monitoring";
- the microphone permission cannot be granted → App management → Nijbhasha →
  Permissions → Microphone → Allow;
- **airplane mode** is needed: Android 11 does not let adb switch it → swipe down, tap
  the airplane icon (on); say "done";
- the app was killed in the background → Battery → Nijbhasha → **Allow background
  activity** (and auto launch if shown).
After each, I run the same command with `--resume`; it continues where it stopped.

What it records: model, Android version, SoC, RAM, WebView version (read from the
device); the release APK installed; the content pack imported (verified); the 24
shared API checks with the network on and again in airplane mode; the page in the
WebView (lessons, a lesson line, Translate → Santali), screen-recorded to
`docs/demo_assets/android_realme.mp4`; the native mic of the release build through
the page and of the debug build through MicBridge; peak PSS (app + WebView renderer).
Output: `bench/results/realme-pad-mini-4gb-android11_<date>_m1.md`. At the end you can
switch airplane mode off.

## B2. Typed translation on the tablet (A5), timed

After B, with airplane mode still ON (switch it on by hand if B ended with it off; Android 11
does not let adb switch it):

```bash
python tools/android/nmt_bench.py --serial <realme serial> --label realme-pad-mini-4gb-android11 --device-label "Realme Pad Mini, 4 GB, Android 11" --in22 200 --skip-phase2
```

It installs the debug build (the benchmark hook), clears the app's data, imports the signed
model pack only, and translates the 80 golden sentences (must equal the laptop's output) and
200 IN22-Conv sentences on the tablet: time per sentence, peak memory, chrF++ beside the
laptop's. Labelled "Realme Pad Mini, 4 GB, Android 11". Free-form *spoken* translation stays
on the laptop hub (decision of 27 Sep). Afterwards reinstall the release APK and re-import
both packs (or run B again with `--resume`) before the demo recording.

## C. Hub mode: the tablet's browser uses the laptop (microphone test)

1. Airplane mode **off** on the tablet. On the laptop: Settings → Network & internet →
   **Mobile hotspot** on. Connect the tablet to that Wi-Fi. (The laptop's hotspot
   address is usually `192.168.137.1`; `ipconfig` shows it.)
2. **Then** start the hub in HTTPS mode: `run_nijbhasha.bat https`. It remakes the
   server certificate for the laptop's current addresses, including the hotspot, and
   keeps the same CA. (Start it after the hotspot is on, or the certificate will not
   name the hotspot address.)
3. The CA certificate to install on the tablet, once:
   **`C:\Users\Barath Srinivasan\Desktop\vaanisetu_1\certs\hub-ca.crt`**
   (only the `.crt`; never copy `hub-ca.key`). Either copy it to the tablet over USB,
   or open `https://192.168.137.1:5443/hub-ca.crt` in the tablet's Chrome and accept the
   one-time warning to download it.
4. On the tablet (Android 11, Realme UI): Settings → Password & security (or Security) →
   System security / Encryption & credentials → **Install from storage** (or "Install a
   certificate") → **CA certificate** → Install anyway → choose `hub-ca.crt`.
5. In the tablet's Chrome open **`https://192.168.137.1:5443`**. There must be no
   warning (the padlock is shown). Allow the microphone when asked.
6. Press **🎤 हिंदी बोलिए**, say *"दो आम और तीन आम मिलाओ। कुल कितने हुए? उंगलियों पर गिनो।"*,
   press it again to stop. Santali should appear and be spoken. **Do this 3 times.**
7. On the laptop: `python tools/hub_mic_check.py --since-minutes 10` prints what the hub
   logged: a voice row with a client time means the microphone, upload and playback
   worked.
8. The client time is reported as its own figure, labelled **"tablet browser via laptop
   hub, Wi-Fi"**: measured by the tablet's browser from the end of speech (mic released)
   to the reply audio starting to play, so it includes the upload and download over
   Wi-Fi and playback start, which the laptop benchmarks do not. All 3 attempts are
   reported; it is never mixed with the laptop figures.

Afterwards, the results go into STATUS.md, `docs/claims.yaml` and `deck_numbers.txt` as
"Realme Pad Mini, 4 GB, Android 11" (app check) and "tablet browser via laptop hub,
Wi-Fi" (hub mode).
