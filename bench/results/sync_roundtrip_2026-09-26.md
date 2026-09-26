# A4 correction sync round trip (2026-09-26)

- Device: Android SDK built for x86_64, Android 9, RAM 2.0 GB (MemTotal 2046740 kB); release APK. Tablet B is the same emulator with the app's data cleared (new device key, no corrections), standing in for a second tablet.
- Before the correction, tablet A answered “ᱤᱧ ᱥᱟᱶ ᱢᱤᱫ, ᱵᱟᱨ, ᱯᱮᱭᱟ, ᱯᱳᱱ, ᱢᱚᱬᱮ ᱜᱚᱴᱟᱝ ᱠᱟᱛᱷᱟ ᱞᱟᱹᱭ ᱢᱮ ᱾” (source model).

1. Tablet A: imported `content-pack-20260926-2024.zip` (2026-09-26T14:56:21+00:00).
2. Tablet A (device 462f846714d1a3a8): corrected “मेरे साथ एक, दो, तीन, चार, पाँच बोलो।” from “ᱤᱧ ᱥᱟᱶ ᱢᱤᱫ, ᱵᱟᱨ, ᱯᱮᱭᱟ, ᱯᱳᱱ, ᱢᱚᱬᱮ ᱜᱚᱴᱟᱝ ᱠᱟᱛᱷᱟ ᱞᱟᱹᱭ ᱢᱮ ᱾” to “ᱤᱧ ᱥᱟᱶ ᱢᱤᱫ, ᱵᱟᱨ, ᱯᱮᱭᱟ, ᱯᱳᱱ, ᱢᱚᱬᱮ ᱜᱚᱴᱟᱝ ᱠᱟᱛᱷᱟ ᱞᱟᱹᱭ ᱢᱮ ᱾ ᱥᱟᱹᱨᱤ”; exported `nijbhasha-export-462f846714d1a3a8-1790434617.json` (1 correction, 1 class rows).
3. Hub (copy of its database): signature checked; merged: applied 1, conflicts 0.
4. Hub: new signed pack `content-pack-sync-1790434751.zip`; the line now reads “ᱤᱧ ᱥᱟᱶ ᱢᱤᱫ, ᱵᱟᱨ, ᱯᱮᱭᱟ, ᱯᱳᱱ, ᱢᱚᱬᱮ ᱜᱚᱴᱟᱝ ᱠᱟᱛᱷᱟ ᱞᱟᱹᱭ ᱢᱮ ᱾ ᱥᱟᱹᱨᱤ” (source teacher).
5. Tablet B (app data cleared: device 067cf52692b00d1a): “मेरे साथ एक, दो, तीन, चार, पाँच बोलो।” → “ᱤᱧ ᱥᱟᱶ ᱢᱤᱫ, ᱵᱟᱨ, ᱯᱮᱭᱟ, ᱯᱳᱱ, ᱢᱚᱬᱮ ᱜᱚᱴᱟᱝ ᱠᱟᱛᱷᱟ ᱞᱟᱹᱭ ᱢᱮ ᱾ ᱥᱟᱹᱨᱤ” (source teacher). **PASS**
6. Tampered pack (one byte of manifest.json changed): refused, the previous pack stays.

Result: **PASS**
