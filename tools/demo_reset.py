"""Get the laptop hub ready to record the demo video (docs/demo_video_script.md).

    run_vaanisetu.bat                      (in another window: start the server first)
    python tools/demo_reset.py             check, clean sessions, warm up
    python tools/demo_reset.py --forget-demo-correction
                                           also remove earlier corrections of the
                                           demo's correction line, so the correction shot of the
                                           script starts from the model's output

What it does, in order:
  1. copies the database to data/backups/ (nothing is lost);
  2. deletes the lesson sessions and their events, so Progress starts at zero.
     Teacher corrections, imported lessons and the latency log are kept;
  3. with --forget-demo-correction, deletes only the corrections whose source
     is the demo's correction line (DEMO_CORRECTION_LINE);
  4. checks the server: all lessons loaded, no online dependency;
  5. warms up: translates every line the script uses, both directions, runs
     speech recognition once per language, and builds the flashcards and a
     worksheet, so the first take is as fast as the tenth.
Then reload the page in the browser.
"""

import argparse
import datetime
import json
import shutil
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from textnorm import normalize_key  # noqa: E402

# The lines docs/demo_video_script.md uses. Keep the two in step.
DEMO_HINDI = [
    "आज हम जोड़ना सीखेंगे। एक और एक मिलाओ।",
    "दो आम और तीन आम मिलाओ। कुल कितने हुए? उंगलियों पर गिनो।",
    "तीन और चार कितने होते हैं?",
]
DEMO_SANTALI = ["ᱯᱮ ᱟᱨ ᱯᱩᱱ ᱡᱚᱛᱚ ᱦᱩᱭᱩᱜᱼᱟ?"]
DEMO_CORRECTION_LINE = "गांव के बच्चे खेत में खेल रहे हैं।"


def call(base, path, body=None, files=None):
    """GET, JSON POST, or a multipart POST with one audio file."""
    headers, data = {}, None
    if files:
        boundary = uuid.uuid4().hex
        parts = []
        for k, v in (body or {}).items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        name, blob = files
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="audio"; filename="{name}"\r\n'
                     f'Content-Type: application/octet-stream\r\n\r\n'.encode() + blob + b"\r\n")
        data = b"".join(parts) + f"--{boundary}--\r\n".encode()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=300) as r:
        raw = r.read()
        return json.loads(raw) if r.headers.get_content_type() == "application/json" else raw


def step(msg):
    print(f"\n{msg}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--server", default=f"http://127.0.0.1:{config.PORT}")
    ap.add_argument("--forget-demo-correction", action="store_true")
    a = ap.parse_args()
    base = a.server.rstrip("/")

    try:
        call(base, "/health")
    except (urllib.error.URLError, ConnectionError) as e:
        sys.exit(f"The server is not running at {base} ({e}). Start run_vaanisetu.bat first, "
                 f"wait for 'Running on', then run this again.")

    step("1. Backing up the database")
    backups = config.DATA_DIR / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    dest = backups / f"{config.DB_FILE.stem}.{datetime.datetime.now():%Y%m%d-%H%M%S}.db"
    shutil.copy2(config.DB_FILE, dest)
    print(f"   {dest.relative_to(ROOT)}")

    step("2. Clearing lesson sessions")
    with sqlite3.connect(config.DB_FILE) as c:
        n_ev = c.execute("DELETE FROM session_events").rowcount
        n_s = c.execute("DELETE FROM sessions").rowcount
        print(f"   removed {n_s} sessions and {n_ev} session events; corrections, lessons "
              f"and the latency log are kept")
        if a.forget_demo_correction:
            step("3. Forgetting earlier corrections of the demo's correction line")
            n = c.execute("DELETE FROM feedback WHERE direction = 'hi-to-sat' AND source_key = ?",
                          (normalize_key(DEMO_CORRECTION_LINE),)).rowcount
            print(f"   removed {n} feedback rows for: {DEMO_CORRECTION_LINE}")

    step("4. Checking the server")
    lessons = call(base, "/lessons")["lessons"]
    team = json.loads(config.TEAM_LESSONS_FILE.read_text(encoding="utf-8"))["lessons"]
    have = {(l["grade"], l["title"]) for l in lessons}
    missing = [L["title"] for L in team if (L["grade"], L["title"]) not in have]
    print(f"   lessons: {len(lessons)}" + (f"; MISSING team lessons: {missing}" if missing else ""))
    online = call(base, "/health/models").get("online_dependencies")
    print(f"   online dependencies: {online if online else 'none'}")
    problems = bool(missing) or bool(online)

    step("5. Warming up")
    t0 = time.time()
    for line in DEMO_HINDI + [DEMO_CORRECTION_LINE]:
        r = call(base, "/translate/text", {"text": line, "direction": "hi-to-sat"})
        print(f"   hi→sat [{r['source']}] {line[:40]}")
    for line in DEMO_SANTALI:
        r = call(base, "/translate/text", {"text": line, "direction": "sat-to-hi"})
        print(f"   sat→hi [{r['source']}] {line[:40]}")
    # Speech recognition once per language: the server speaks a line, and that
    # audio is sent back as a recording.
    for lang, direction, text in (("hi", "hi-to-sat", DEMO_HINDI[2]), ("sat", "sat-to-hi", DEMO_SANTALI[0])):
        spoken = call(base, "/speak", {"text": text, "lang": lang})
        if not spoken.get("audio_url"):
            print(f"   speech warm-up ({lang}) skipped: {spoken.get('tts_error')}")
            problems = True
            continue
        wav = call(base, spoken["audio_url"])
        r = call(base, "/translate/audio", {"direction": direction}, files=("warm.wav", wav))
        print(f"   speech {lang}: heard '{r.get('recognized_text', '')[:40]}'")
    decks = call(base, "/flashcards")["decks"]
    print(f"   flashcards: {len(decks)} decks")
    pdf = call(base, "/worksheet", {"hindi_text": DEMO_HINDI[0], "santali_text": "", "grade": "2"})
    print(f"   worksheet: {len(pdf)} bytes")
    print(f"   warm-up took {time.time() - t0:.1f} s")

    print("\n" + ("CHECK THE PROBLEMS ABOVE before recording." if problems else
                  "Ready. Reload the page in the browser, then follow docs/demo_video_script.md."))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
