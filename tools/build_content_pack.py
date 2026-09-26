"""Build the content pack the Android app imports (F1 M1; signing arrives in M5).

    python tools/build_content_pack.py                    # dist/packs/content-pack-<time>.zip
    python tools/build_content_pack.py --audio-lessons 1 --dir android/app/src/test/resources/pack

Runs on the hub, with its models: everything in the pack is what the hub itself
would answer, so a tablet with the pack gives the same lesson content offline.

Pack layout (format 1):
  manifest.json          format, created, app name, model versions, counts, and
                         the SHA-256 of every other file (the app refuses a pack
                         whose files do not match)
  api/config.json        GET /config, as the hub answers it
  api/lessons.json       GET /lessons
  api/flashcards.json    GET /flashcards
  lessons.json           every lesson in full (steps, accept_answers) for sessions
  translations.json      {"hi-to-sat": {key: {text, source, review_status}},
                          "sat-to-hi": {...}}; key = textnorm.normalize_key(source text).
                         Lesson lines, flashcard words, verified glossary sentences
                         and teacher corrections, through the hub's own layers.
  audio/index.json       {"sat": {text: file}, "hi": {text: file}}
  audio/<sha1>.wav       Piper audio for every translation and every Hindi line
  worksheets/<grade>_<topic>.pdf   one worksheet per lesson (v2 exercises + answer key when
                                   config.WORKSHEET_V2, else the lesson-lines sheet)
  flashcards/<grade>_<topic>.pdf   cut-out flashcards per lesson (A2)
"""

import argparse
import datetime
import hashlib
import importlib
import io
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FORMAT = 1


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(out_dir, audio=True, worksheets=True, audio_lessons=None, log=print):
    import config
    app = importlib.import_module("app")
    app.app.testing = True
    client = app.app.test_client()
    from education_glossary import VERIFIED_SENTENCES_HI_SAT, VERIFIED_SENTENCES_SAT_HI
    from lesson_engine import get_lesson
    from textnorm import normalize_key
    pl = app.pl

    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "api").mkdir(parents=True)

    def save(rel, obj):
        p = out_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=0) + "\n", encoding="utf-8", newline="\n")

    api = {}
    for name, path in (("config", "/config"), ("lessons", "/lessons"), ("flashcards", "/flashcards")):
        r = client.get(path)
        assert r.status_code == 200, (path, r.status_code)
        api[name] = r.get_json()
        save(f"api/{name}.json", api[name])

    lessons = []
    for meta in api["lessons"]["lessons"]:
        lessons.append({"grade": meta["grade"], "topic": meta["topic"],
                        "lesson": get_lesson(meta["grade"], meta["topic"])})
    save("lessons.json", lessons)

    # Every Hindi line a tablet may be asked to translate from the pack.
    hi_lines = [st["hindi"] for L in lessons for st in L["lesson"]["steps"] if st.get("hindi")]
    hi_lines += [c["hi"] for d in api["flashcards"]["decks"] for c in d["cards"]]
    hi_lines += list(VERIFIED_SENTENCES_HI_SAT)
    sat_lines = list(VERIFIED_SENTENCES_SAT_HI)
    import database
    for direction, src_list in (("hi-to-sat", hi_lines), ("sat-to-hi", sat_lines)):
        for row in database.list_corrections(direction):
            src_list.append(row["source_text"])

    review = {"teacher": "teacher_verified", "glossary": "verified_glossary", "cached": "unreviewed_model_output",
              "model": "unreviewed_model_output"}
    trans = {"hi-to-sat": {}, "sat-to-hi": {}}
    cards = {normalize_key(c["hi"]): c for d in api["flashcards"]["decks"] for c in d["cards"]}
    for direction, lines in (("hi-to-sat", hi_lines), ("sat-to-hi", sat_lines)):
        for line in lines:
            k = normalize_key(line)
            if not k or k in trans[direction]:
                continue
            if direction == "hi-to-sat" and k in cards and cards[k]["source"] in ("teacher", "wordlist"):
                c = cards[k]                     # a flashcard word: the card's own answer
                trans[direction][k] = {"source_text": line, "text": c["sat"], "source": c["source"],
                                       "review_status": c["review_status"]}
                continue
            r = pl.translate(line, direction, "lesson_script")
            trans[direction][k] = {"source_text": line, "text": r["text"], "source": r["source"],
                                   "review_status": review.get(r["source"], "unreviewed_model_output")}
    save("translations.json", trans)
    log(f"translations: {len(trans['hi-to-sat'])} hi-to-sat, {len(trans['sat-to-hi'])} sat-to-hi")

    index = {"sat": {}, "hi": {}}
    if audio:
        (out_dir / "audio").mkdir()
        want = {("sat", t["text"]) for t in trans["hi-to-sat"].values()}
        want |= {("hi", t["text"]) for t in trans["sat-to-hi"].values()}
        want |= {("hi", t["source_text"]) for t in trans["hi-to-sat"].values()}
        want |= {("sat", c["sat"]) for d in api["flashcards"]["decks"] for c in d["cards"]}
        if audio_lessons is not None:            # a small pack for tests: only the first N lessons' lines
            keep = {normalize_key(st.get("hindi", "")) for L in lessons[:audio_lessons] for st in L["lesson"]["steps"]}
            texts = {t["text"] for k, t in trans["hi-to-sat"].items() if k in keep}
            texts |= {t["source_text"] for k, t in trans["hi-to-sat"].items() if k in keep}
            want = {(lang, text) for lang, text in want if text in texts}
        for lang, text in sorted(want):
            text = text.strip()
            if not text or text in index[lang]:
                continue
            name = hashlib.sha1(f"{lang}:{text}".encode("utf-8")).hexdigest() + ".wav"
            target = out_dir / "audio" / name
            (pl.santali_tts if lang == "sat" else pl.hindi_tts)(text, str(target))
            index[lang][text] = name
        log(f"audio: {len(index['sat'])} Santali, {len(index['hi'])} Hindi clips")
    save("audio/index.json", index)

    if worksheets and config.WORKSHEET_V2:
        from worksheet_v2 import build as build_v2, build_flashcards
        (out_dir / "worksheets").mkdir()
        (out_dir / "flashcards").mkdir()
        decks = {(d["grade"], d["topic"]): d for d in api["flashcards"]["decks"]}
        sat_of = lambda hi: (trans["hi-to-sat"].get(normalize_key(hi)) or {}).get("text", "")
        for L in lessons:
            deck = decks.get((L["grade"], L["topic"]), {"title": L["topic"], "grade": L["grade"], "topic": L["topic"],
                                                         "lakshya_ids": [], "cards": []})
            build_v2(L["lesson"], L["grade"], L["topic"], deck["cards"], sat_of,
                     out_dir / "worksheets" / f"{L['grade']}_{L['topic']}.pdf")
            build_flashcards(deck, out_dir / "flashcards" / f"{L['grade']}_{L['topic']}.pdf")
        log(f"worksheets v2 and flashcards: {len(lessons)}")
    elif worksheets:
        from worksheet import generate_worksheet
        (out_dir / "worksheets").mkdir()
        for L in lessons:
            les = L["lesson"]
            steps = []
            for st in les["steps"]:
                t = trans["hi-to-sat"].get(normalize_key(st.get("hindi", "")))
                steps.append({"type": st.get("type", ""), "hindi": st.get("hindi", ""),
                              "santali": t["text"] if t else "", "note": st.get("note", "")})
            buf = io.BytesIO()
            generate_worksheet("", "", L["grade"], L["topic"], lesson_steps=steps, out=buf,
                               lakshya_ids=les.get("lakshya_ids"))
            (out_dir / "worksheets" / f"{L['grade']}_{L['topic']}.pdf").write_bytes(buf.getvalue())
        log(f"worksheets: {len(lessons)}")

    files = {p.relative_to(out_dir).as_posix(): sha256(p) for p in sorted(out_dir.rglob("*")) if p.is_file()}
    manifest = {
        "format": FORMAT,
        "created": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "app_name": config.APP_NAME,
        "model_versions": app._model_versions(),
        "counts": {"lessons": len(lessons), "flashcard_decks": len(api["flashcards"]["decks"]),
                   "translations_hi_to_sat": len(trans["hi-to-sat"]),
                   "translations_sat_to_hi": len(trans["sat-to-hi"]),
                   "audio_clips": len(index["sat"]) + len(index["hi"])},
        "files": files,
        "signature": None,          # Ed25519, from M5
    }
    save("manifest.json", manifest)
    return manifest


def zip_dir(src, zip_path):
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(Path(src).rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(src).as_posix())
    return zip_path


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", type=Path, help="write the unpacked pack here instead of a zip")
    ap.add_argument("--out", type=Path, help="zip path (default dist/packs/content-pack-<time>.zip)")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--no-worksheets", action="store_true")
    ap.add_argument("--audio-lessons", type=int, help="audio for the first N lessons only (test packs)")
    a = ap.parse_args()
    if a.dir:
        m = build(a.dir, audio=not a.no_audio, worksheets=not a.no_worksheets, audio_lessons=a.audio_lessons)
        print(json.dumps(m["counts"]), "->", a.dir)
        return
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    out = a.out or ROOT / "dist" / "packs" / f"content-pack-{stamp}.zip"
    with tempfile.TemporaryDirectory() as tmp:
        m = build(Path(tmp) / "pack", audio=not a.no_audio, worksheets=not a.no_worksheets)
        zip_dir(Path(tmp) / "pack", out)
    print(json.dumps(m["counts"]), "->", out, f"{out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
