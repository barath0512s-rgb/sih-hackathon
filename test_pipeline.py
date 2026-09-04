# test_pipeline.py — all 7 tests must pass before touching Android

from pipeline import VaaniSetuPipeline
from lesson_engine import get_all_lessons, get_lesson, LessonSession
from worksheet import generate_worksheet
import os, sys

p      = VaaniSetuPipeline()
passed = []
failed = []

def run(name, fn):
    try:
        fn()
        passed.append(name)
        print(f"  PASS  {name}")
    except Exception as e:
        failed.append(name)
        print(f"  FAIL  {name}  —  {e}")

print("\n=== VaaniSetu Pipeline Tests ===\n")

# Store results between tests using a list (avoids Python global scoping issues)
state = {}

def t1():
    sat, en = p.hindi_to_santali("आज हम जोड़ना सीखेंगे।", "lesson_script")
    assert len(sat) > 0, "Empty Santali output"
    assert len(en)  > 0, "Empty English pivot"
    state["sat"] = sat
    state["en"]  = en
    print(f"       Hindi   → English: {en}")
    print(f"       English → Santali: {sat}")

def t2():
    hi = p.santali_to_hindi(state.get("sat","test"))
    assert len(hi) > 0, "Empty reverse translation"
    print(f"       Santali → Hindi: {hi}")

def t3():
    path = p.santali_tts(state.get("sat","ᱫᱳ"))
    assert os.path.exists(path), "Audio file not created"
    kb = os.path.getsize(path) // 1024
    assert kb > 1, f"Audio file too small ({kb} KB) — likely silent"
    print(f"       Audio: {kb} KB")

def t4():
    for mode in ["lesson_script", "activity_instruction", "assessment_prompt"]:
        out, _ = p.hindi_to_santali("यह क्या है?", mode)
        assert len(out) > 0, f"Empty output for mode {mode}"
    print("       All 3 modes produced output")

def t5():
    lessons = get_all_lessons()
    assert len(lessons) >= 5, f"Expected 5+ lessons, got {len(lessons)}"
    lesson = get_lesson("2","addition")
    assert lesson is not None, "Grade 2 addition not found"
    print(f"       {len(lessons)} lessons available")

def t6():
    lesson = get_lesson("2","addition")
    sess   = LessonSession(lesson)
    sess.record_translation("test hi","test sat", 2.1)
    sess.advance()
    # Test green signal
    sig = sess.check_response("7")
    assert sig == "green", f"Expected green for '7', got {sig}"
    # Test red signal
    sig2 = sess.check_response("")
    assert sig2 == "red", f"Expected red for empty, got {sig2}"
    summ = sess.summary()
    assert "comprehension" in summ, "Summary missing comprehension"
    print(f"       Green/Red signals correct. Verdict: {summ['comprehension']['verdict']}")

def t7():
    path = generate_worksheet(
        "आज हम जोड़ना सीखेंगे।",
        state.get("sat","test santali"),
        grade="2", topic="Addition", out="test_ws.pdf")
    assert os.path.exists(path), "PDF not created"
    kb = os.path.getsize(path) // 1024
    assert kb > 5, f"PDF too small ({kb} KB)"
    print(f"       Worksheet: {kb} KB")
    os.remove(path)  # cleanup test file

for name, fn in [
    ("Hindi → Santali translation", t1),
    ("Santali → Hindi (bidirectional)", t2),
    ("Santali TTS audio output", t3),
    ("All 3 FLN content modes", t4),
    ("Lesson engine loads correctly", t5),
    ("Comprehension signals green/red", t6),
    ("Bilingual worksheet PDF", t7),
]:
    run(name, fn)

print(f"\n{'='*40}")
print(f"Passed: {len(passed)}/7")
if failed:
    print(f"FAILED: {', '.join(failed)}")
    print("Fix all failures before Android.")
    sys.exit(1)
else:
    print("ALL TESTS PASSED — run: python app.py")
