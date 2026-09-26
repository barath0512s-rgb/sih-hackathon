# Tablet app (F1)

Kotlin, minSdk 28 (Android 9), no AndroidX. The app shows the same
`frontend.html` as the hub in a WebView, and answers the page from an in-app
server on `127.0.0.1:5000` (loopback only) with the hub's REST contract
(`contract/rest_contract.json`).

State (27 Sep 2026): lessons, flashcards, sessions and answer marking, pack
lines and audio, worksheet and flashcard PDFs, teacher corrections and the
reading check work offline from a signed **content pack**. With the signed
**model pack**: speech recognition and synthesis on the device (M2, M3), a
spoken lesson line matched to its pre-translated Santali (A1), and typed new
sentences translated on the device (M4). Free-form *spoken* translation stays
on the laptop hub (on 2 GB it needs a model swap per utterance). Anything the
tablet cannot do answers `503 engine_not_on_device`, never a fake result.

## Licence of the APK

The APK includes espeak-ng (GPL-3.0-or-later, inside sherpa-onnx's native
library), so **the APK as a whole is distributed under GPL-3.0 terms**
(`COPYING-GPL-3.0.txt`; the app carries it and a source notice in
`assets/licenses/`). Our code is MIT. Details: `THIRD_PARTY_LICENSES.md`.

## Build

Needs JDK 17 and the Android SDK (platform 36).

```bash
python tools/android/sync_config.py        # app name and the tablet's settings from config.py
python tools/android/fetch_sherpa_aar.py   # sherpa-onnx 1.13.8 AAR (50 MB, not in git; SHA-256 checked)
python tools/android/patch_ort_jni.py      # ONNX Runtime's Java bridge made to use sherpa-onnx's onnxruntime (A5)
cd android
./gradlew testDebugUnitTest assembleDebug
```

Speech and translation models are not in the APK: build the model pack
(`python tools/android/build_model_pack.py`, about 890 MB, signed) and import it
like the content pack. Packs are signed on the hub (`pack_signing.py`); the app
refuses an unsigned or changed pack.

On Windows, if Gradle fails with "Unable to establish loopback connection", the
temp path is too long for Java's sockets: set
`JAVA_TOOL_OPTIONS=-Djdk.net.unixdomain.tmpdir=C:\gt` (any short folder).

## Content pack

Built on the hub, with its models:

```bash
python tools/build_content_pack.py         # dist/packs/content-pack-<time>.zip
```

On the tablet: Settings → Content pack → From a file (USB, SD card, Downloads),
or From the hub (`https://<hub>:5443`; the hub serves `GET /pack/latest`, and the
tablet must trust the hub CA from `/hub-ca.crt`). The app checks the SHA-256 of
every file against `manifest.json` and keeps the previous pack if anything is
wrong. Signing (Ed25519) arrives in M5.

## Checks

- `android/app/src/test`: the contract (same file as the hub), the Kotlin
  ports of `normalize_key` and answer grading against Python's vectors
  (`tests/data/normalize_key_vectors.json`), and pack import refusals.
- `tools/android/device_check.py`: on a device or emulator, installs the APK,
  imports a pack, runs the contract with the network on and in airplane mode,
  and reads the app's PSS. Results in `bench/results/android_m1_<label>.md`.
