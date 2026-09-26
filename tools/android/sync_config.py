"""Write android/app/src/main/assets/app_config.json from config.py.

    python tools/android/sync_config.py

The product name lives only in config.APP_NAME / APP_NAME_LOCAL. The app shows
this file's names before a content pack is installed, and Gradle takes the
launcher label from it. device_config.json holds the tablet's own settings
(on-device voice). tests/test_android_assets.py fails if it is out of date.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "android" / "app" / "src" / "main" / "assets" / "app_config.json"
DEVICE_OUT = OUT.with_name("device_config.json")


def expected():
    import config
    return json.dumps({"app_name": config.APP_NAME, "app_name_local": config.APP_NAME_LOCAL},
                      ensure_ascii=False, indent=1) + "\n"


def expected_device():
    """The tablet's own settings (A1): not part of GET /config."""
    import config
    return json.dumps({"on_device_voice": config.ON_DEVICE_VOICE,
                       "lesson_match_threshold": config.LESSON_MATCH_THRESHOLD,
                       "asr_threads": config.ON_DEVICE_ASR_THREADS,
                       "asr_trim_silence": config.ASR_TRIM_SILENCE,
                       "asr_decoding": config.ASR_DECODING}, ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(expected(), encoding="utf-8", newline="\n")
    DEVICE_OUT.write_text(expected_device(), encoding="utf-8", newline="\n")
    print("wrote", OUT.relative_to(ROOT), DEVICE_OUT.relative_to(ROOT))
