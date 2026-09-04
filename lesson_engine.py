# lesson_engine.py — NIPUN Bharat FLN lesson templates
# This is VaaniSetu's biggest differentiator vs all other teams

import time as _time

NIPUN_LESSONS = {
    "grade1": {
        "counting_1_10": {
            "title": "Counting 1 to 10",
            "competency": "Counts objects up to 10 and says numbers in order",
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
                 "accept_answers": ["3", "तीन", "teen"]},
            ]
        },
        "shapes": {
            "title": "Basic Shapes",
            "competency": "Identifies circle, square, and triangle",
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
                 "note": "Point to a triangle on the board"},
            ]
        }
    },
    "grade2": {
        "addition": {
            "title": "Simple Addition",
            "competency": "Adds two single-digit numbers using objects",
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
                 "accept_answers": ["7", "सात", "saat"]},
            ]
        },
        "reading_words": {
            "title": "Reading Simple Words",
            "competency": "Reads common two-syllable words aloud",
            "steps": [
                {"type": "lesson_script",
                 "hindi": "यह शब्द है — माँ। इसे पढ़ो।",
                 "note": "Show word card: माँ"},
                {"type": "activity_instruction",
                 "hindi": "इस शब्द को तीन बार पढ़ो — पानी।",
                 "note": "Choral reading practice"},
                {"type": "assessment_prompt",
                 "hindi": "यह शब्द क्या है? पढ़कर बताओ।",
                 "note": "Hold up word card: घर"},
            ]
        }
    },
    "grade3": {
        "subtraction": {
            "title": "Simple Subtraction",
            "competency": "Subtracts single-digit numbers using objects",
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
                 "accept_answers": ["3", "तीन", "teen"]},
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
                "steps": len(lesson["steps"])
            })
    return out


def get_lesson(grade, topic):
    return NIPUN_LESSONS.get(f"grade{grade}", {}).get(topic)


class LessonSession:
    """Tracks one complete lesson session with comprehension analytics."""

    def __init__(self, lesson):
        self.lesson       = lesson
        self.step_idx     = 0
        self.total_steps  = len(lesson["steps"])
        self.translations = []
        self.responses    = []
        self.t_start      = _time.time()

    @property
    def current_step(self):
        if self.step_idx >= self.total_steps:
            return None
        return self.lesson["steps"][self.step_idx]

    def advance(self):
        self.step_idx = min(self.step_idx + 1, self.total_steps)

    def record_translation(self, hindi, santali, latency_sec):
        self.translations.append({
            "step":    self.step_idx,
            "hindi":   hindi,
            "santali": santali,
            "latency": latency_sec
        })

    def check_response(self, student_text):
        """
        Evaluates student response. Returns "green" | "yellow" | "red".
        Uses the previous step's expected answers (after advance() is called).
        """
        # Use the step that was just completed (step_idx - 1, clamped to 0)
        step_idx = max(self.step_idx - 1, 0)
        if step_idx >= self.total_steps:
            signal = "yellow"
        else:
            step = self.lesson["steps"][step_idx]
            if "accept_answers" not in step:
                # Non-assessment step — any response is yellow (acknowledged)
                signal = "yellow"
            else:
                cleaned  = student_text.strip().lower()
                accepted = [a.lower() for a in step["accept_answers"]]
                if cleaned in accepted:
                    signal = "green"
                elif len(cleaned) > 0:
                    signal = "yellow"
                else:
                    signal = "red"

        self.responses.append({
            "step":     step_idx,
            "response": student_text,
            "signal":   signal
        })
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
