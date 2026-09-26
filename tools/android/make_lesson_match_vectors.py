"""Write tests/data/lesson_match_vectors.json from lesson_match.py (the Kotlin port's reference).

    python tools/android/make_lesson_match_vectors.py

Self-contained (no content pack needed): the candidate lines are the Android test
pack's Hindi lines and Santali lines; the utterances are fixed below plus the
laptop transcripts of a sample of the A1 tuning clips when present.
tests/test_lesson_match.py fails if the file no longer matches Python.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "tests" / "data" / "lesson_match_vectors.json"
PACK = ROOT / "android" / "app" / "src" / "test" / "resources" / "pack"

UTTERANCES = {
    "hi": ["दो आम और तीन आम मिलाओ", "कुल कितने हुए", "3425", "तीन हज़ार चार सौ पच्चीस", "4", "चार", "",
           "आज मौसम बहुत अच्छा है", "गिनो 1 से 10 तक", "दो आम और पांच आम मिलाओ", "एक सौ", "उंगलियों पर गिनो", "99", "100", "10000", "007"],
    "sat": ["ᱵᱟᱨ ᱟᱢ", "᱔", "ᱯᱩᱱ", "12", "ᱜᱮᱞ ᱵᱟᱨ", "1000", "ᱡᱚᱦᱟᱨ", "", "ᱥᱟᱭ ᱢᱤᱫ", "101"],
}


def build():
    from lesson_match import canonical, match, similarity
    from textnorm import normalize_key
    tr = json.loads((PACK / "translations.json").read_text(encoding="utf-8"))
    cands = {"hi": sorted(tr["hi-to-sat"]),
             "sat": sorted({normalize_key(v["text"]) for v in tr["hi-to-sat"].values()} | set(tr["sat-to-hi"]))}
    utt = {k: list(v) for k, v in UTTERANCES.items()}
    for lang in utt:          # the candidates themselves, lightly damaged, as utterances
        for c in cands[lang][:15]:
            utt[lang] += [c, c[: max(1, len(c) * 2 // 3)]]
    out = {"note": "lesson_match.py reference for LessonMatch.kt; regenerate with tools/android/make_lesson_match_vectors.py",
           "candidates": cands, "canonical": [], "similarity": [], "match": []}
    for lang, us in utt.items():
        for u in us:
            out["canonical"].append({"lang": lang, "in": u, "out": canonical(u, lang)})
            m = match(u, cands[lang], 0.5, lang)
            out["match"].append({"lang": lang, "in": u, "threshold": 0.5, **m})
        for a, b in zip(us, us[1:]):
            out["similarity"].append({"lang": lang, "a": a, "b": b, "score": round(similarity(a, b, lang), 9)})
    return json.dumps(out, ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8", newline="\n")
    print("wrote", OUT.relative_to(ROOT))
