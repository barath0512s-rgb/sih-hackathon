"""Import lessons through work package 14, as a teacher would.

    python tools/import_lessons.py                        # content/team_lessons.json
    python tools/import_lessons.py path/to/lessons.json
    python tools/import_lessons.py --server http://127.0.0.1:5000

For each lesson it:
  1. posts the Hindi text to /curriculum/import and gets the draft (automatic
     labels, suggested NIPUN goals);
  2. applies what the file says the teacher decided: a label where the file
     gives "type", the expected answers, and the goals in "lakshya_ids";
  3. posts that to /curriculum/save with the goals confirmed.
It reports where the teacher had to change the automatic label or goal.

Imported lessons live in the SQLite database, which is not in git, so run this
once on each laptop. A lesson whose grade and title are already imported is
skipped, so running it twice adds nothing.

Without --server the app is loaded in this process (it loads the models).
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class InProcess:
    def __init__(self):
        import app
        self.c = app.app.test_client()

    def get(self, path):
        r = self.c.get(path)
        return r.status_code, r.get_json()

    def post(self, path, body):
        r = self.c.post(path, json=body)
        return r.status_code, r.get_json()


class Http:
    def __init__(self, base):
        self.base = base.rstrip("/")

    def _call(self, path, body=None):
        import urllib.error
        import urllib.request
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.base + path, data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def get(self, path):
        return self._call(path)

    def post(self, path, body):
        return self._call(path, body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", default=str(ROOT / "content" / "team_lessons.json"))
    ap.add_argument("--server", help="a running server, e.g. http://127.0.0.1:5000")
    a = ap.parse_args()
    lessons = json.loads(Path(a.file).read_text(encoding="utf-8"))["lessons"]
    api = Http(a.server) if a.server else InProcess()

    _, have = api.get("/lessons")
    existing = {(l["grade"], l["title"]) for l in have["lessons"] if l.get("imported")}
    made = skipped = label_changes = goal_changes = 0
    for L in lessons:
        if (L["grade"], L["title"]) in existing:
            print(f"skip   grade {L['grade']}  {L['title']}  (already imported)")
            skipped += 1
            continue
        code, r = api.post("/curriculum/import", {"text": "\n".join(x["hindi"] for x in L["lines"]),
                                                  "grade": L["grade"], "title": L["title"]})
        if code != 200:
            sys.exit(f"import failed for {L['title']}: {r}")
        (d,) = r["lessons"]
        if len(d["lines"]) != len(L["lines"]):
            sys.exit(f"{L['title']}: the text split into {len(d['lines'])} lines, "
                     f"the file has {len(L['lines'])}. Put one sentence per line.")
        changed = []
        for i, (mine, got) in enumerate(zip(L["lines"], d["lines"])):
            want = mine.get("type") or ("assessment_prompt" if mine.get("answer") else got["type"])
            if want != got["type"]:
                changed.append(f"line {i + 1}: {got['type']} -> {want}")
                got["type"] = want
            got["answer"] = mine.get("answer", "")
        label_changes += len(changed)
        if d["suggested"]["lakshya_ids"] != L["lakshya_ids"]:
            goal_changes += 1
            changed.append(f"goals: suggested {d['suggested']['lakshya_ids']} -> {L['lakshya_ids']}")
        code, r = api.post("/curriculum/save", {**d, "lakshya_ids": L["lakshya_ids"],
                                                "lakshya_confirmed": True})
        if code != 200:
            sys.exit(f"save failed for {L['title']}: {r}")
        _, deck = api.get(r["flashcards_url"])
        cards = len(deck["decks"][0]["cards"]) if deck.get("decks") else 0
        print(f"added  grade {r['grade']}  {r['title']}  -> {r['topic']}: {len(r['steps'])} lines, "
              f"{cards} cards, {r['audio_errors']} audio errors, goals {r['lakshya_ids']}")
        for c in changed:
            print(f"         teacher changed {c}")
        made += 1
    print(f"\n{made} added, {skipped} already there. Teacher changes: {label_changes} labels, "
          f"{goal_changes} goal suggestions, over {len(lessons)} lessons.")


if __name__ == "__main__":
    main()
