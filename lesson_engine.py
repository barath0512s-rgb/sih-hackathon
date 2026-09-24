# lesson_engine.py — NIPUN Bharat FLN lesson templates, grading, sessions
#
# Every lesson carries the NIPUN Lakshya IDs it works towards (nipun/lakshya.py),
# its domain, how closely it fits ("mapping": full or partial) and a review
# status. The lesson's own grade is the class it is written for; a Lakshya can
# belong to an earlier stage when the lesson revises it. docs/lakshya_mapping.md
# explains each choice.

import time as _time

import database
from nipun.lakshya import label
from textnorm import normalize_key

NIPUN_LESSONS = {
    "grade1": {
        "counting_1_10": {
            "title": "Counting 1 to 10",
            "flashcards": [
                {"hi": "एक", "emoji": "🍎", "n": 1}, {"hi": "दो", "emoji": "🍎", "n": 2},
                {"hi": "तीन", "emoji": "🍎", "n": 3}, {"hi": "चार", "emoji": "🍎", "n": 4},
                {"hi": "पांच", "emoji": "🍎", "n": 5}, {"hi": "छह", "emoji": "🌰", "n": 6},
                {"hi": "सात", "emoji": "🌰", "n": 7}, {"hi": "आठ", "emoji": "🌰", "n": 8},
                {"hi": "नौ", "emoji": "🌰", "n": 9}, {"hi": "दस", "emoji": "🌰", "n": 10},
            ],
            "competency": "Counts objects up to 10 and says numbers in order",
            "lakshya_ids": ["NIPUN-BV-NUM-1", "NIPUN-G1-NUM-1"],
            "domain": "numeracy",
            "mapping": "full for BV-NUM-1 (numerals up to 10); partial for G1-NUM-1 (only up to 10 of 99)",
            "review_status": "pending_teacher_review",
            "steps": [
                {"type": "lesson_script",
                 "hindi": "आज हम एक से दस तक गिनना सीखेंगे।",
                 "note": "Show fingers — introduction"},
                {"type": "activity_instruction",
                 "hindi": "अपनी उंगलियां दिखाओ और मेरे साथ गिनो।",
                 "note": "Count together with fingers"},
                {"type": "activity_instruction",
                 "hindi": "अब तुम्हारे सामने पांच पत्थर हैं। उन्हें गिनो।",
                 "note": "Count physical objects"},
                {"type": "assessment_prompt",
                 "hindi": "यहाँ कितने पत्थर हैं? बताओ।",
                 "note": "Hold up 3 objects",
                 "accept_answers": {"digits": ["3"], "hi": ["तीन", "teen"],
                                    "sat": ["ᱯᱮ", "ᱯᱮᱭᱟ"],
                                    "sat_sources": {"ᱯᱮ": "education_glossary", "ᱯᱮᱭᱟ": "IndicTrans2 output"},
                                    "review_status": "pending_native_review"}},
            ]
        },
        "shapes": {
            "title": "Basic Shapes",
            "flashcards": [
                {"hi": "गोल", "emoji": "⭕"}, {"hi": "चौकोर", "emoji": "🟦"},
                {"hi": "तिकोन", "emoji": "🔺"}, {"hi": "तारा", "emoji": "⭐"},
                {"hi": "अंडाकार", "emoji": "🥚"}, {"hi": "रेखा", "emoji": "➖"},
            ],
            "competency": "Identifies circle, square, and triangle",
            "lakshya_ids": ["NIPUN-BV-NUM-2"],
            "domain": "numeracy",
            "mapping": "partial: the lesson names shapes; the goal is arranging shapes in a sequence",
            "review_status": "pending_teacher_review",
            "steps": [
                {"type": "lesson_script",
                 "hindi": "यह गोल है। यह एक वृत्त है।",
                 "note": "Hold up a circle"},
                {"type": "lesson_script",
                 "hindi": "यह चौकोर है। इसके चार कोने हैं।",
                 "note": "Hold up a square"},
                {"type": "activity_instruction",
                 "hindi": "अपने आसपास गोल चीज़ें ढूंढो।",
                 "note": "Find circular objects around classroom"},
                {"type": "assessment_prompt",
                 "hindi": "यह कौन सा आकार है?",
                 "note": "Point to a triangle on the board",
                 "accept_answers": {"hi": ["त्रिकोण", "तिकोन", "त्रिभुज", "trikon", "tikon"],
                                    "sat": ["ᱛᱤᱱ ᱠᱩᱱᱟᱹ ᱪᱤᱛᱟᱹᱨ", "ᱴᱨᱤᱝᱜᱚᱞ", "ᱴᱤᱠᱚᱱ"],
                                    "sat_sources": {"ᱛᱤᱱ ᱠᱩᱱᱟᱹ ᱪᱤᱛᱟᱹᱨ": "education_glossary",
                                                    "ᱴᱨᱤᱝᱜᱚᱞ": "IndicTrans2 output",
                                                    "ᱴᱤᱠᱚᱱ": "IndicTrans2 output"},
                                    "review_status": "pending_native_review"}},
            ]
        }
    },
    "grade2": {
        "addition": {
            "title": "Simple Addition",
            "flashcards": [
                {"hi": "दो और एक तीन", "emoji": "🥭🥭 ➕ 🥭"},
                {"hi": "दो और दो चार", "emoji": "🍌🍌 ➕ 🍌🍌"},
                {"hi": "तीन और दो पांच", "emoji": "🪨🪨🪨 ➕ 🪨🪨"},
                {"hi": "तीन और चार सात", "emoji": "🌼🌼🌼 ➕ 🌼🌼🌼🌼"},
                {"hi": "पांच और पांच दस", "emoji": "✋ ➕ ✋"},
            ],
            "competency": "Adds two single-digit numbers using objects",
            "lakshya_ids": ["NIPUN-G1-NUM-2"],
            "domain": "numeracy",
            "mapping": "full: single-digit addition is 'simple addition' (a Grade 1 goal, revised in Grade 2)",
            "review_status": "pending_teacher_review",
            "steps": [
                {"type": "lesson_script",
                 "hindi": "आज हम जोड़ना सीखेंगे। एक और एक मिलाओ।",
                 "note": "Introduction — show joining of groups"},
                {"type": "activity_instruction",
                 "hindi": "दो आम और तीन आम मिलाओ। कुल कितने हुए? उंगलियों पर गिनो।",
                 "note": "Use objects to add"},
                {"type": "activity_instruction",
                 "hindi": "अब तुम एक जोड़ का सवाल बनाओ।",
                 "note": "Student creates own addition problem"},
                {"type": "assessment_prompt",
                 "hindi": "तीन और चार कितने होते हैं?",
                 "note": "Oral number answer expected",
                 "accept_answers": {"digits": ["7"], "hi": ["सात", "saat"],
                                    "sat": ["ᱮᱭᱟᱭ", "ᱮᱭᱟᱭ ᱜᱚᱴᱟᱝ"],
                                    "sat_sources": {"ᱮᱭᱟᱭ": "education_glossary",
                                                    "ᱮᱭᱟᱭ ᱜᱚᱴᱟᱝ": "IndicTrans2 output"},
                                    "review_status": "pending_native_review"}},
            ]
        },
        "reading_words": {
            "title": "Reading Simple Words",
            "flashcards": [
                {"hi": "माँ", "emoji": "👩"}, {"hi": "पानी", "emoji": "💧"},
                {"hi": "घर", "emoji": "🏠"}, {"hi": "फूल", "emoji": "🌸"},
                {"hi": "किताब", "emoji": "📕"}, {"hi": "गाय", "emoji": "🐄"},
            ],
            "competency": "Reads common two-syllable words aloud",
            "lakshya_ids": ["NIPUN-BV-LIT-2", "NIPUN-G2-LIT-1"],
            "domain": "literacy",
            "mapping": "full for BV-LIT-2 (simple 2-3 letter words); partial for G2-LIT-1 (single words, not text)",
            "review_status": "pending_teacher_review",
            "steps": [
                {"type": "lesson_script",
                 "hindi": "यह शब्द है — माँ। इसे पढ़ो।",
                 "note": "Show word card: माँ"},
                {"type": "activity_instruction",
                 "hindi": "इस शब्द को तीन बार पढ़ो — पानी।",
                 "note": "Choral reading practice"},
                {"type": "assessment_prompt",
                 "hindi": "यह शब्द क्या है? पढ़कर बताओ।",
                 "note": "Hold up word card: घर",
                 # ᱳᱲᱟᱜ is the corrected glossary word (was ᱦᱚᱨᱚ, "person");
                 # ᱚᱲᱟᱜ is the model's spelling of the same word.
                 "accept_answers": {"hi": ["घर", "ghar"],
                                    "sat": ["ᱳᱲᱟᱜ", "ᱚᱲᱟᱜ"],
                                    "sat_sources": {"ᱳᱲᱟᱜ": "education_glossary (corrected 2026-09-24)",
                                                    "ᱚᱲᱟᱜ": "IndicTrans2 output"},
                                    "review_status": "pending_native_review"}},
            ]
        }
    },
    "grade3": {
        "subtraction": {
            "title": "Simple Subtraction",
            "flashcards": [
                {"hi": "पांच में से दो तीन", "emoji": "🪨🪨🪨🪨🪨 ➖ 🪨🪨"},
                {"hi": "चार में से एक तीन", "emoji": "🍬🍬🍬🍬 ➖ 🍬"},
                {"hi": "छह में से तीन तीन", "emoji": "🐟🐟🐟🐟🐟🐟 ➖ 🐟🐟🐟"},
                {"hi": "आठ में से पांच तीन", "emoji": "🌟🌟🌟🌟🌟🌟🌟🌟 ➖ 🌟🌟🌟🌟🌟"},
            ],
            "competency": "Subtracts single-digit numbers using objects",
            "lakshya_ids": ["NIPUN-G1-NUM-2", "NIPUN-G2-NUM-2"],
            "domain": "numeracy",
            "mapping": "full for G1-NUM-2; partial for G2-NUM-2 (single digits only, goal is up to 99)",
            "review_status": "pending_teacher_review",
            "steps": [
                {"type": "lesson_script",
                 "hindi": "आज हम घटाना सीखेंगे। दस में से तीन घटाओ।",
                 "note": "Introduction — remove objects"},
                {"type": "activity_instruction",
                 "hindi": "सात पत्थर लो। तीन हटा दो। अब कितने बचे?",
                 "note": "Concrete subtraction with objects"},
                {"type": "assessment_prompt",
                 "hindi": "आठ में से पांच घटाओ। उत्तर क्या है?",
                 "note": "Oral answer expected",
                 "accept_answers": {"digits": ["3"], "hi": ["तीन", "teen"],
                                    "sat": ["ᱯᱮ", "ᱯᱮᱭᱟ"],
                                    "sat_sources": {"ᱯᱮ": "education_glossary", "ᱯᱮᱭᱟ": "IndicTrans2 output"},
                                    "review_status": "pending_native_review"}},
            ]
        }
    }
}


def get_all_lessons():
    out = []
    for gk, topics in NIPUN_LESSONS.items():
        g = gk.replace("grade", "")
        for tk, lesson in topics.items():
            out.append({
                "grade": g, "topic": tk,
                "title": lesson["title"],
                "competency": lesson["competency"],
                "lakshya_ids": lesson["lakshya_ids"],
                "lakshya": [label(i) for i in lesson["lakshya_ids"]],
                "domain": lesson["domain"],
                "review_status": lesson["review_status"],
                "flashcards": len(lesson.get("flashcards", [])),
                "steps": len(lesson["steps"])
            })
    return out


def get_lesson(grade, topic):
    return NIPUN_LESSONS.get(f"grade{grade}", {}).get(topic)


def grade(step, answer):
    """Grade a child's answer to one lesson step: "green" | "yellow" | "red".

    green   the answer matches an accepted Hindi or Santali answer, or the same
            number in any digit script (7, ७, ᱗)
    yellow  something was said, but not an accepted answer, or the step asks
            no question
    red     nothing was said
    Matching uses textnorm.normalize_key, so spacing, punctuation, nukta and
    chandrabindu differences do not matter.
    """
    key = normalize_key(answer or "")
    if not key:
        return "red"
    acc = step.get("accept_answers")
    if not acc:
        return "yellow"
    if key.isdigit() and key in acc.get("digits", []):
        return "green"
    words = acc.get("hi", []) + acc.get("sat", [])
    if key in {normalize_key(w) for w in words}:
        return "green"
    return "yellow"


class LessonSession:
    """One lesson being taught, with comprehension analytics.

    Every change is written to SQLite as it happens (database.py), so a server
    restart does not lose the lesson: LessonSession.load(sid) rebuilds it.
    """

    def __init__(self, lesson, sid=None, grade_=None, topic=None, _new=True):
        self.lesson       = lesson
        self.sid          = sid
        self.step_idx     = 0
        self.total_steps  = len(lesson["steps"])
        self.translations = []
        self.responses    = []
        self.t_start      = _time.time()
        if sid and _new:
            database.create_session(sid, grade_, topic)

    @classmethod
    def load(cls, sid):
        """Rebuild a session from the database, or None if it does not exist."""
        found = database.load_session(sid)
        if not found:
            return None
        row, events = found
        lesson = get_lesson(row["grade"], row["topic"])
        if not lesson:
            return None
        s = cls(lesson, sid=sid, _new=False)
        s.step_idx = min(row["step_idx"], s.total_steps)
        s.t_start  = row["started_at"]
        for e in events:
            (s.translations if e["kind"] == "translation" else s.responses).append(e["payload"])
        return s

    @property
    def current_step(self):
        if self.step_idx >= self.total_steps:
            return None
        return self.lesson["steps"][self.step_idx]

    def _save_step(self):
        if self.sid:
            database.set_session_step(self.sid, self.step_idx)

    def advance(self):
        self.step_idx = min(self.step_idx + 1, self.total_steps)
        self._save_step()

    def goto(self, step):
        """Jump to a step. Clamped to the lesson."""
        self.step_idx = max(0, min(int(step), self.total_steps - 1))
        self._save_step()

    def record_translation(self, hindi, santali, latency_sec):
        ev = {"step": self.step_idx, "hindi": hindi, "santali": santali,
              "latency": latency_sec}
        self.translations.append(ev)
        if self.sid:
            database.add_session_event(self.sid, "translation", self.step_idx, ev)

    def check_response(self, student_text, step=None):
        """Grade an answer to `step` (default: the current step).

        The step is explicit. It used to be inferred as step_idx - 1, which
        graded the wrong question whenever the UI had not just advanced.
        """
        if step is None:
            step = self.step_idx
        step = int(step)
        if not 0 <= step < self.total_steps:
            raise ValueError(f"step {step} is outside this lesson (0-{self.total_steps - 1})")
        signal = grade(self.lesson["steps"][step], student_text)
        ev = {"step": step, "response": student_text, "signal": signal}
        self.responses.append(ev)
        if self.sid:
            database.add_session_event(self.sid, "response", step, ev)
        return signal

    def summary(self):
        elapsed  = _time.time() - self.t_start
        mins, sc = int(elapsed // 60), int(elapsed % 60)
        green  = sum(1 for r in self.responses if r["signal"] == "green")
        yellow = sum(1 for r in self.responses if r["signal"] == "yellow")
        red    = sum(1 for r in self.responses if r["signal"] == "red")
        total  = len(self.responses)
        pct    = round((green / total) * 100) if total > 0 else 0

        verdict = (
            "Good — students grasped the concept" if pct >= 70 else
            "Partial — repeat key terms next session" if pct >= 40 else
            "Needs reinforcement — revisit this lesson"
        )
        avg_lat = (
            round(sum(t["latency"] for t in self.translations) /
                  len(self.translations), 2)
            if self.translations else 0.0
        )
        return {
            "lesson_title":         self.lesson["title"],
            "competency":           self.lesson["competency"],
            "duration":             f"{mins}m {sc}s",
            "steps_completed":      self.step_idx,
            "total_steps":          self.total_steps,
            "sentences_translated": len(self.translations),
            "avg_latency_sec":      avg_lat,
            "comprehension": {
                "green":         green,
                "yellow":        yellow,
                "red":           red,
                "score_percent": pct,
                "verdict":       verdict
            }
        }
