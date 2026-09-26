# Samsung session (F1 M1 on a real tablet + hub-mode microphone)

For the Samsung tablet (4 GB RAM, Android 13). Everything measured here is
labelled **"4 GB, Android 13"**; it is never a 2 GB measurement. The 2 GB
evidence stays the Android 9 emulator (`bench/results/android_m1_emulator-2gb-android9.md`).

## A. Before plugging in

On the tablet: Settings → About tablet → Software information → tap **Build
number** 7 times; then Settings → Developer options → **USB debugging** on.
Plug in over USB and accept the "Allow USB debugging?" prompt on the tablet.

## B. The app check, one pass (I run this)

```bash
python tools/android/device_check.py --apk android/app/build/outputs/apk/release/app-release.apk --debug-apk android/app/build/outputs/apk/debug/app-debug.apk --pack <newest dist/packs/content-pack-*.zip> --label samsung-4gb-android13 --record docs/demo_assets/android_samsung.mp4
```

It records model, Android version, RAM, CPU and WebView version; installs the
release APK; imports the content pack; runs the 24 shared API checks with the
network on and then in airplane mode; checks the page renders in the WebView
(lessons, a lesson line, Translate → Santali) while screen-recording about 30 s;
records 3 s from the native microphone (debug build of the same code); samples
peak PSS; writes `bench/results/samsung-4gb-android13_<date>_m1.md`.

## C. Hub mode: the tablet's browser uses the laptop (microphone test)

1. On the laptop: Settings → Network & internet → **Mobile hotspot** on. Connect
   the tablet to that Wi-Fi. (The laptop's hotspot address is usually
   `192.168.137.1`; `ipconfig` shows it.)
2. **Then** start the hub in HTTPS mode: `run_vaanisetu.bat https`. It remakes the
   server certificate for the laptop's current addresses, including the hotspot,
   and keeps the same CA. (Start it after the hotspot is on, or the certificate
   will not name the hotspot address.)
3. The CA certificate to install on the tablet, once:
   **`C:\Users\Barath Srinivasan\Desktop\vaanisetu_1\certs\hub-ca.crt`**
   (only the `.crt`; never copy `hub-ca.key`). Either copy it to the tablet over
   USB, or open `https://192.168.137.1:5443/hub-ca.crt` in the tablet's Chrome and
   accept the one-time warning to download it.
4. On the tablet (Android 13): Settings → Security and privacy → More security
   settings → Install from device storage (or "Encryption & credentials → Install a
   certificate") → **CA certificate** → Install anyway → choose `hub-ca.crt`.
5. In the tablet's Chrome open **`https://192.168.137.1:5443`**. There must be no
   warning (the padlock is shown). Allow the microphone when asked.
6. Press **🎤 हिंदी बोलिए**, say *"दो आम और तीन आम मिलाओ। कुल कितने हुए? उंगलियों पर गिनो।"*,
   press it again to stop. Santali should appear and be spoken.
7. On the laptop: `python tools/hub_mic_check.py --since-minutes 10` prints what the
   hub logged: a voice row with a client time means the microphone, upload and
   playback worked.
8. The client time is reported as its own figure, labelled **"tablet browser via
   laptop hub, Wi-Fi"**: measured by the tablet's browser from the end of speech
   (mic released) to the reply audio starting to play, so it includes the upload
   and download over Wi-Fi and playback start, which the laptop benchmarks do not.
   It is never mixed with the laptop figures. Repeat the line 3 times if possible
   and report every time.

Afterwards, the result goes into STATUS.md and `docs/claims.yaml` as "Samsung, 4 GB,
Android 13, hub mode over the laptop's hotspot".
