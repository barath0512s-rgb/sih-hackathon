"""Class-level NIPUN Lakshya progress (A8): per Lakshya ID and week.

For a cluster resource person: how many lessons working towards each Lakshya were
taught, and how many answers were green / yellow / red. Class level only: no child
names are ever recorded (the app has no field for one), and no audio.

Sources:
  the hub's own lessons   sessions + session_events (response signals)
  tablets                 sync_analytics, from the tablets' signed exports (sync.py)
A lesson with two Lakshya IDs counts towards both. Weeks are ISO weeks (YYYY-Www). A lesson counts as taught once something happened
in it (a translation or a graded answer): the page opens a session on start.
GET /progress/lakshya (?format=json|csv|pdf) on the hub; the tablet answers json/csv
from its own records.
"""

import csv
import datetime
import io
import json

import database


def _week(day):
    y, w, _ = datetime.date.fromisoformat(day).isocalendar()
    return f"{y}-W{w:02d}"


def rows():
    from lesson_engine import get_lesson
    agg = {}

    def add(lid, week, source, sessions=0, g=0, y=0, r=0):
        a = agg.setdefault((lid, week), {"lakshya_id": lid, "week": week, "lessons_taught": 0,
                                        "green": 0, "yellow": 0, "red": 0, "sources": set()})
        a["lessons_taught"] += sessions
        a["green"] += g; a["yellow"] += y; a["red"] += r
        a["sources"].add(source)

    with database._db() as c:
        # a session counts once something happened in it (the page opens one on start)
        sess = c.execute("""SELECT id, grade, topic, started_at FROM sessions s
                            WHERE EXISTS (SELECT 1 FROM session_events e WHERE e.session_id = s.id)""").fetchall()
        ev = c.execute("SELECT session_id, payload FROM session_events WHERE kind='response'").fetchall()
        synced = c.execute("SELECT * FROM sync_analytics").fetchall() if c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sync_analytics'").fetchone() else []
    signals = {}
    for e in ev:
        s = json.loads(e["payload"]).get("signal")
        signals.setdefault(e["session_id"], []).append(s)
    lids_of = {}
    for s in sess:
        k = (s["grade"], s["topic"])
        if k not in lids_of:
            les = get_lesson(*k)
            lids_of[k] = (les or {}).get("lakshya_ids") or []
        week = _week(datetime.date.fromtimestamp(s["started_at"]).isoformat())
        sig = signals.get(s["id"], [])
        for lid in lids_of[k]:
            add(lid, week, "hub", 1, sig.count("green"), sig.count("yellow"), sig.count("red"))
    for r in synced:
        for lid in [x for x in (r["lakshya_ids"] or "").split(",") if x]:
            add(lid, _week(r["day"]), f"tablet:{r['device_id']}", r["sessions"], r["green"], r["yellow"], r["red"])
    out = []
    for (lid, week), a in sorted(agg.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        a["sources"] = sorted(a["sources"])
        answers = a["green"] + a["yellow"] + a["red"]
        a["green_share"] = round(a["green"] / answers, 3) if answers else None
        out.append(a)
    return out


def as_csv(rs):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["week", "lakshya_id", "lessons_taught", "green", "yellow", "red", "green_share", "sources"])
    for r in rs:
        w.writerow([r["week"], r["lakshya_id"], r["lessons_taught"], r["green"], r["yellow"], r["red"],
                    "" if r["green_share"] is None else r["green_share"], " ".join(r["sources"])])
    return buf.getvalue()


def as_pdf(rs, out):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle
    import config
    from nipun import lakshya
    from worksheet import P, ps
    doc = SimpleDocTemplate(out, pagesize=landscape(A4), leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                            topMargin=1.2 * cm, bottomMargin=1.2 * cm, title=f"{config.APP_NAME} NIPUN progress")
    H = ps("PH", 14, True, "#0D2137", TA_CENTER)
    S = ps("PS", 8.5, False, "#333333")
    B = ps("PB", 9, False)
    head = ["सप्ताह / Week", "NIPUN लक्ष्य / Lakshya", "पाठ / Lessons", "✓ हरा", "~ पीला", "✗ लाल", "हरा %", "स्रोत / Sources"]
    data = [[P(h, B, bold=True) for h in head]]
    for r in rs:
        data.append([P(r["week"], B), P(r["lakshya_id"], B), P(str(r["lessons_taught"]), B), P(str(r["green"]), B),
                     P(str(r["yellow"]), B), P(str(r["red"]), B),
                     P("—" if r["green_share"] is None else f"{r['green_share'] * 100:.0f}%", B),
                     P(", ".join(r["sources"]), S)])
    t = Table(data, colWidths=[2.8 * cm, 4.2 * cm, 2 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 8.5 * cm], repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBBBBB")),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F5")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    lids = sorted({r["lakshya_id"] for r in rs})
    s = [P(f"{config.APP_NAME_LOCAL['hi']} — NIPUN लक्ष्य प्रगति (कक्षा स्तर) / NIPUN Lakshya progress (class level)", H),
         P(f"{datetime.date.today().strftime('%d.%m.%Y')} · कोई बच्चे का नाम या आवाज़ नहीं / no child names, no audio", S),
         Spacer(1, 0.3 * cm), t, Spacer(1, 0.4 * cm)]
    s += [P(f"{lid}: {lakshya.get(lid)['text']}", S) for lid in lids if lakshya.get(lid)]
    doc.build(s)
