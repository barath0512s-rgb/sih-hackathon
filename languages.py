"""The language registry (A7): languages.json, read by the page, the API, the README and the deck numbers.

    python languages.py        # prints the README table
"""

import json
from pathlib import Path

FILE = Path(__file__).resolve().parent / "languages.json"
MATURITY = ("production", "preview", "phrasebook", "not available")
STAGES = ("asr", "nmt", "tts")
STAGE_NAMES = {"asr": "Speech recognition", "nmt": "Translation", "tts": "Speech"}


def load():
    d = json.loads(FILE.read_text(encoding="utf-8"))
    for lang in d["languages"]:
        for st in STAGES:
            m = lang["stages"][st]["maturity"]
            if m not in MATURITY:
                raise ValueError(f"{lang['code']}.{st}: maturity {m!r} not in {MATURITY}")
    return d["languages"]


def get(code):
    return next((l for l in load() if l["code"] == code), None)


START, END = "<!-- languages:start -->", "<!-- languages:end -->"


def readme_table():
    rows = ["| Language | " + " | ".join(STAGE_NAMES[s] for s in STAGES) + " |", "|---" * (len(STAGES) + 1) + "|"]
    for l in load():
        cells = []
        for s in STAGES:
            st = l["stages"][s]
            if not st["engine"]:
                cells.append(st["maturity"])
            elif st["maturity"] == "not available":
                cells.append(f"not available (planned: {st['engine']})")
            else:
                cells.append(f"**{st['maturity']}**: {st['engine']} ({st['licence']})")
        rows.append(f"| {l['name_en']} ({l['name_local']}) | " + " | ".join(cells) + " |")
    return "\n".join(rows)


if __name__ == "__main__":
    print(readme_table())
