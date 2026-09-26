"""After a tablet used the hub's microphone: what the hub logged for it.

    python tools/hub_mic_check.py [--since-minutes 30] [--device <device_id>]

Lists the voice requests (typed ones too, marked) that reached the hub in the
last N minutes, newest first, from the hub's own latency log: direction, what
answered, server time, and the client's measured wait (client_total_ms = end of
speech to the reply's audio starting to play, reported by the browser; for a
streamed reply, to the first chunk). A voice row with a client time means the
tablet's microphone, the upload and the playback all worked. Read-only.
"""

import argparse
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import database  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since-minutes", type=float, default=30)
    ap.add_argument("--device")
    a = ap.parse_args()
    c = sqlite3.connect(f"file:{database.DB_FILE}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    q = ("SELECT ts, device_id, direction, input_type, source, server_ms, client_total_ms, client_last_ms, chunks, "
         "tts_error FROM latency_log WHERE ts > ?" + (" AND device_id = ?" if a.device else "") + " ORDER BY ts DESC")
    args = [time.time() - a.since_minutes * 60] + ([a.device] if a.device else [])
    rows = c.execute(q, args).fetchall()
    if not rows:
        print(f"No requests in the last {a.since_minutes:g} minutes.")
        return
    print("Client s = 'tablet browser via laptop hub, Wi-Fi': measured in the browser from the end of speech to the")
    print("reply audio starting to play, so it includes Wi-Fi both ways and playback start (not in the laptop benchmarks).")
    print("time      device    direction  input         source    server s  client s")
    for r in rows:
        client = f"{r['client_total_ms'] / 1000:.2f}" if r["client_total_ms"] is not None else "not reported"
        print(f"{time.strftime('%H:%M:%S', time.localtime(r['ts']))}  {(r['device_id'] or '-')[:8]:8}  "
              f"{r['direction']:9}  {r['input_type']:12}  {r['source']:8}  {r['server_ms'] / 1000:8.2f}  {client}"
              + (f"  (last chunk {r['client_last_ms'] / 1000:.2f})" if r["client_last_ms"] else "")
              + (f"  TTS error: {r['tts_error']}" if r["tts_error"] else ""))


if __name__ == "__main__":
    main()
