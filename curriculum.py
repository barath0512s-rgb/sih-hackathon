# curriculum.py — turn a teacher's Hindi lesson text into a typed, tagged lesson
#
# Work package 14. This module is pure logic, with no models:
#   parse_upload   pasted text, a .txt file, or CSV/JSON rows (grade, topic, line)
#   split          sentences, at । ? . ! and line breaks
#   classify       lesson_script | activity_instruction | assessment_prompt,
#                  by simple rules; the teacher can change any label
#   suggest        NIPUN Lakshya IDs from the grade and domain keywords; the
#                  teacher must confirm them
#   flashcard_words  numbers and known nouns in the lesson
#   build_lesson   the lesson dict, in the same shape as lesson_engine.NIPUN_LESSONS
# app.py adds the Santali, the audio, the worksheet and storage.

import csv
import io
import json
import re
import unicodedata

from nipun import lakshya

TYPES = ("lesson_script", "activity_instruction", "assessment_prompt")
GRADES = ("0", "1", "2", "3")                   # "0" is Balvatika
STAGE = {"0": "BV", "1": "G1", "2": "G2", "3": "G3"}
MAX_LINES, MAX_LINE_CHARS, MAX_TITLE = 60, 300, 80

_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
_PUNCT = "।॥?.!,;:\"'“”‘’()[]—–-…"


# ── Input ─────────────────────────────────────────────────────────────────────
class CurriculumError(ValueError):
    """The upload or the draft is not usable. `code` (and `params`) let the UI
    say it in the teacher's language; the English message is for logs and tests."""

    def __init__(self, message, code="invalid", params=None):
        super().__init__(message)
        self.code, self.params = code, params or {}


def parse_upload(text=None, filename=None, data=None, grade=None, title=None):
    """Drafts to show the teacher: [{"grade", "title", "text"}].

    text             pasted lesson text (one lesson)
    filename + data  an uploaded .txt, .csv or .json file (bytes)
    CSV and JSON rows carry grade, topic and line; rows are grouped into one
    lesson per (grade, topic), in the order they appear.
    """
    if data is not None:
        name = (filename or "").lower()
        try:
            raw = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise CurriculumError("The file must be UTF-8 text.", "file_encoding")
        if name.endswith(".csv"):
            rows = list(csv.DictReader(io.StringIO(raw)))
            return _group(rows, "CSV")
        if name.endswith(".json"):
            try:
                rows = json.loads(raw)
            except json.JSONDecodeError as e:
                raise CurriculumError(f"The JSON file could not be read: {e.msg}.", "json_bad")
            if isinstance(rows, dict):
                rows = rows.get("lines") or rows.get("rows") or []
            if not isinstance(rows, list):
                raise CurriculumError("The JSON file must be a list of {grade, topic, line}.", "json_shape")
            return _group(rows, "JSON")
        if name.endswith(".txt") or not name:
            text = raw
        else:
            raise CurriculumError("Upload a .txt, .csv or .json file.", "file_type")
    if not (text or "").strip():
        raise CurriculumError("There is no lesson text.", "no_text")
    return [{"grade": str(grade or "1"), "title": (title or "").strip(), "text": text}]


def _group(rows, kind):
    lessons, order = {}, []
    for i, r in enumerate(rows, 1):
        if not isinstance(r, dict):
            raise CurriculumError(f"{kind} row {i} is not a record with grade, topic, line.", "row_bad", {'n': i})
        r = {str(k).strip().lower(): ("" if v is None else str(v)).strip() for k, v in r.items()}
        if not r.get("line"):
            continue
        key = (r.get("grade") or "1", r.get("topic") or "Lesson")
        if key not in lessons:
            lessons[key] = []
            order.append(key)
        lessons[key].append(r["line"])
    if not order:
        raise CurriculumError(f"The {kind} file has no rows with grade, topic and line.", "no_rows")
    return [{"grade": g, "title": t, "text": "\n".join(lessons[(g, t)])} for g, t in order]


# ── Splitting and labelling ───────────────────────────────────────────────────
def normalise(line):
    line = unicodedata.normalize("NFC", line)
    line = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", line)     # zero-width marks
    return re.sub(r"\s+", " ", line).strip()


def split(text):
    """Sentences, each keeping its end mark. Lines with no letters are dropped."""
    out = []
    for chunk in re.split(r"[\r\n]+", text or ""):
        for s in re.findall(r"[^।?.!]+[।?.!]*", chunk):
            s = normalise(s)
            if re.search(r"\w", s):
                out.append(s)
    return out


def _words(line):
    return [w.strip(_PUNCT) for w in line.split() if w.strip(_PUNCT)]


QUESTION_WORDS = ("कितने", "कितना", "कितनी", "क्या", "कौन", "कौनसा", "कौन-सा", "बताओ", "बताइए", "बताइये")


def classify(line):
    """The addendum's rules, in order:
    a question mark, or a question word (कितने क्या कौन बताओ)  -> assessment_prompt
    the last word is an imperative (ends in -ओ / -ो / -इए / -िए) -> activity_instruction
    anything else                                            -> lesson_script
    """
    words = _words(line)
    if line.rstrip().endswith("?") or any(w in QUESTION_WORDS for w in words):
        return "assessment_prompt"
    if words and re.search(r"(ओ|ो|इए|िए|इये|िये)$", words[-1]):
        return "activity_instruction"
    return "lesson_script"


# ── Lakshya suggestions ───────────────────────────────────────────────────────
NUMBER_WORDS = {
    "शून्य": 0, "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5, "छह": 6, "छः": 6,
    "सात": 7, "आठ": 8, "नौ": 9, "दस": 10, "ग्यारह": 11, "बारह": 12, "तेरह": 13, "चौदह": 14,
    "पंद्रह": 15, "सोलह": 16, "सत्रह": 17, "अठारह": 18, "उन्नीस": 19, "बीस": 20,
    "तीस": 30, "चालीस": 40, "पचास": 50, "साठ": 60, "सत्तर": 70, "अस्सी": 80, "नब्बे": 90, "सौ": 100,
}
NUMERACY_STEMS = ("जोड़", "घटा", "गिन", "गिनती", "संख्या", "अंक", "गुणा", "बराबर", "ज़्यादा",
                  "ज्यादा", "कम", "आकार", "बचे", "हटा", "मिला")
LITERACY_STEMS = ("अक्षर", "शब्द", "पढ़", "वाक्य", "कहानी", "लिख", "ध्वनि", "आवाज़", "सुन", "कविता",
                  "समझ")                     # "read with meaning" (NIPUN G2/G3 literacy)
ADD = ("जोड़", "मिला")
SUBTRACT = ("घटा", "हटा", "बचे")
SEQUENCE = ("क्रम", "पहले", "बाद", "आकार")


def _is_number(w):
    return w in NUMBER_WORDS or bool(re.fullmatch(r"[0-9०-९᱐-᱙]+", w))


def _has(words, stems):
    return any(w.startswith(s) or s in w for w in words for s in stems)


def suggest(grade, lines):
    """{"domain", "lakshya_ids", "why"}: a suggestion only. The teacher confirms.

    Domain: numbers and जोड़/घटा/गिन… count for numeracy; अक्षर/शब्द/पढ़… for
    literacy. The goals are the ones for the lesson's grade in that domain,
    with a few keyword rules (addition, subtraction, letters, sequence).
    """
    words = [w for line in lines for w in _words(line)]
    # एक is also the article "a" (एक गाँव में), so it is no evidence of numeracy.
    num = (sum(_is_number(w) and w != "एक" for w in words)
           + sum(_has([w], NUMERACY_STEMS) for w in words))
    lit = sum(_has([w], LITERACY_STEMS) for w in words)
    grade = str(grade)
    if not num and not lit:
        return {"domain": None, "lakshya_ids": [], "counts": {"numeracy": 0, "literacy": 0},
                "why": "No number or reading words found; choose the goals yourself."}
    st = STAGE.get(grade, "G1")
    if num >= lit:
        domain = "numeracy"
        if st == "BV":
            ids = ["NIPUN-BV-NUM-2" if _has(words, SEQUENCE) else "NIPUN-BV-NUM-1"]
        elif st == "G1":
            ids = ["NIPUN-G1-NUM-2" if _has(words, ADD + SUBTRACT) else "NIPUN-G1-NUM-1"]
        elif st == "G2":
            ids = (["NIPUN-G2-NUM-2"] if _has(words, SUBTRACT) else
                   ["NIPUN-G1-NUM-2"] if _has(words, ADD) else ["NIPUN-G2-NUM-1"])
        else:
            ids = (["NIPUN-G3-NUM-2"] if _has(words, ("गुणा",)) else
                   ["NIPUN-G2-NUM-2"] if _has(words, SUBTRACT) else
                   ["NIPUN-G1-NUM-2"] if _has(words, ADD) else ["NIPUN-G3-NUM-1"])
        why = f"{num} number or maths words"
    else:
        domain = "literacy"
        letters = _has(words, ("अक्षर", "ध्वनि", "आवाज़"))
        if st == "BV":
            ids = ["NIPUN-BV-LIT-1" if letters else "NIPUN-BV-LIT-2"]
        elif st == "G1":
            ids = ["NIPUN-BV-LIT-1" if letters else "NIPUN-G1-LIT-1"]
        else:
            ids = [f"NIPUN-{st}-LIT-1"]
        why = f"{lit} reading or writing words"
    # "why" is for logs and tests; the UI builds its own sentence from "counts".
    return {"domain": domain, "lakshya_ids": ids, "counts": {"numeracy": num, "literacy": lit},
            "why": f"{why}; grade {grade}"}


def draft(item):
    """One draft lesson for the teacher to check: typed lines and suggested goals."""
    lines = split(item["text"])
    return {"grade": item["grade"] if item["grade"] in GRADES else "1",
            "title": item["title"][:MAX_TITLE],
            "lines": [{"hindi": l, "type": classify(l), "answer": ""} for l in lines[:MAX_LINES]],
            "truncated": len(lines) > MAX_LINES,
            "suggested": suggest(item["grade"], lines)}


# ── Flashcards ────────────────────────────────────────────────────────────────
# Nouns a card can show, with a picture. The Santali on a card comes from the
# word list or the model at /flashcards time, labelled with its source.
NOUN_EMOJI = {
    "पत्थर": "🪨", "आम": "🥭", "हाथ": "✋", "उंगली": "☝️", "उंगलियां": "🖐️", "किताब": "📕",
    "माँ": "👩", "पानी": "💧", "घर": "🏠", "पेड़": "🌳", "सूरज": "☀️", "चाँद": "🌙",
    "गाय": "🐄", "फूल": "🌸", "मछली": "🐟", "चिड़िया": "🐦", "बिल्ली": "🐈", "कुत्ता": "🐕",
    "केला": "🍌", "केले": "🍌", "अंडा": "🥚", "गेंद": "⚽", "कलम": "🖊️", "पत्ता": "🍃", "पत्ते": "🍃",
    "मोर": "🦚", "बकरी": "🐐", "सेब": "🍎", "कुर्सी": "🪑", "थैला": "🎒", "बच्चा": "🧒",
    "बच्चे": "🧒", "रोटी": "🫓", "दूध": "🥛", "आँख": "👁️", "कान": "👂", "नाक": "👃",
    "गोल": "⭕", "चौकोर": "🟦", "त्रिकोण": "🔺", "तिकोन": "🔺", "रेखा": "➖", "तारा": "⭐",
    "लाल": "🔴", "नीला": "🔵", "हरा": "🟢", "पीला": "🟡", "काला": "⚫", "सफेद": "⚪",
}
MAX_CARDS = 12


def flashcard_words(lines):
    """[{"hi", "emoji", "n"}]: the numbers and known nouns in the lesson, once each."""
    cards, seen = [], set()
    for line in lines:
        for w in _words(line):
            if w in seen:
                continue
            if _is_number(w):
                n = NUMBER_WORDS.get(w)
                if n is None:
                    n = int(w.translate(str.maketrans("०१२३४५६७८९᱐᱑᱒᱓᱔᱕᱖᱗᱘᱙", "01234567890123456789")))
                card = {"hi": w, "emoji": "🔵", "n": n} if 0 < n <= 10 else {"hi": w, "emoji": "🔢"}
            elif w in NOUN_EMOJI:
                card = {"hi": w, "emoji": NOUN_EMOJI[w]}
            else:
                continue
            seen.add(w)
            cards.append(card)
            if len(cards) == MAX_CARDS:
                return cards
    return cards


# ── The lesson ────────────────────────────────────────────────────────────────
def validate(body):
    """Check a teacher-confirmed draft. Returns (grade, title, lines, ids) or raises."""
    grade = str(body.get("grade", ""))
    if grade not in GRADES:
        raise CurriculumError("Grade must be Balvatika (0) or 1, 2, 3.", "grade")
    title = normalise(str(body.get("title") or ""))
    if not title:
        raise CurriculumError("Give the lesson a title.", "title")
    if len(title) > MAX_TITLE:
        raise CurriculumError(f"The title is longer than {MAX_TITLE} characters.", "title_long", {'n': MAX_TITLE})
    lines = body.get("lines") or []
    if not isinstance(lines, list) or not lines:
        raise CurriculumError("The lesson has no lines.", "no_lines")
    if len(lines) > MAX_LINES:
        raise CurriculumError(f"A lesson can have at most {MAX_LINES} lines.", "too_many_lines", {'n': MAX_LINES})
    clean = []
    for i, l in enumerate(lines, 1):
        if not isinstance(l, dict):
            raise CurriculumError(f"Line {i} is not valid.", "line_bad", {'n': i})
        hindi = normalise(str(l.get("hindi") or ""))
        if not hindi:
            continue
        if not _DEVANAGARI.search(hindi):
            raise CurriculumError(f"Line {i} is not in Hindi (Devanagari): {hindi[:40]}", "line_not_hindi", {'n': i})
        if len(hindi) > MAX_LINE_CHARS:
            raise CurriculumError(f"Line {i} is longer than {MAX_LINE_CHARS} characters.", "line_long", {'n': i})
        t = l.get("type") or classify(hindi)
        if t not in TYPES:
            raise CurriculumError(f"Line {i} has an unknown type: {t}", "line_type", {'n': i})
        clean.append({"hindi": hindi, "type": t, "answer": normalise(str(l.get("answer") or ""))})
    if not clean:
        raise CurriculumError("The lesson has no lines.", "no_lines")
    if body.get("lakshya_confirmed") is not True:
        raise CurriculumError("Confirm the NIPUN goals before creating the lesson.", "confirm")
    ids = body.get("lakshya_ids") or []
    if not ids:
        raise CurriculumError("Choose at least one NIPUN goal.", "no_goals")
    for lid in ids:
        if not lakshya.get(lid):
            raise CurriculumError(f"Unknown NIPUN goal: {lid}", "goal_unknown")
    domains = {lakshya.get(lid)["domain"] for lid in ids}
    if len(domains) > 1:
        raise CurriculumError("Choose goals from one domain: literacy or numeracy.", "goal_domains")
    return grade, title, clean, list(dict.fromkeys(ids))


def answer_key(answer):
    """accept_answers from the teacher's expected answer. Several right answers
    are separated by "/", e.g. "एक सौ बीस / 120". A number word or a number
    also accepts the same number in any digit script."""
    answers = [a.strip() for a in re.split(r"[/|]", answer or "") if a.strip(_PUNCT + " ")]
    if not answers:
        return None
    key = {"hi": [], "sat": [], "sat_sources": {}, "review_status": "pending_native_review"}
    digits = []
    for a in answers:
        w = a.strip(_PUNCT)
        if w in NUMBER_WORDS:
            digits.append(str(NUMBER_WORDS[w]))
        if re.fullmatch(r"[0-9]+", w):
            digits.append(w)
        else:
            key["hi"].append(a)
    if digits:
        key["digits"] = list(dict.fromkeys(digits))
    return key


def build_lesson(grade, title, lines, ids):
    """The lesson without its Santali; app.py fills in santali, source and audio."""
    return {
        "title": title,
        "competency": lakshya.get(ids[0])["text"],
        "lakshya_ids": ids,
        "domain": lakshya.get(ids[0])["domain"],
        "mapping": "suggested from keywords, confirmed by the teacher",
        "review_status": "pending_native_review",
        "imported": True,
        "steps": [{"type": l["type"], "hindi": l["hindi"], "note": "",
                   **({"accept_answers": answer_key(l["answer"])}
                      if l["type"] == "assessment_prompt" and l["answer"] else {})}
                  for l in lines],
        "flashcards": flashcard_words([l["hindi"] for l in lines]),
    }
