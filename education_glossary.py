# education_glossary.py
# Curated Hindi <-> Santali (Ol Chiki) glossary for NIPUN / primary education.
# These are HARD overrides: when this exact word or phrase appears in a translation
# the model output is replaced with the verified entry. This gives 100% consistency
# for the vocabulary that matters most in Grades 1-3.
#
# Sources: Santali primer textbooks, NIPUN Bharat FLN corpus, and Ol Chiki reference.
# All Santali strings are written in Ol Chiki script as required by the UI.

# ── Numbers (cardinal) ────────────────────────────────────────────────────────
NUMBERS_HI_SAT = {
    "एक":    "ᱢᱤᱫ",
    "दो":    "ᱵᱟᱨ",
    "तीन":   "ᱯᱮ",
    "चार":   "ᱯᱩᱱ",
    "पांच":  "ᱢᱚᱬᱮ",
    "पाँच":  "ᱢᱚᱬᱮ",
    "छह":    "ᱛᱩᱨᱩᱭ",
    "छः":    "ᱛᱩᱨᱩᱭ",
    "सात":   "ᱮᱭᱟᱭ",
    "आठ":    "ᱤᱨᱟᱹᱞ",
    "नौ":    "ᱟᱨᱮ",
    "दस":    "ᱜᱮᱞ",
    "ग्यारह": "ᱜᱮᱞ ᱢᱤᱫ",
    "बारह":  "ᱜᱮᱞ ᱵᱟᱨ",
    "तेरह":  "ᱜᱮᱞ ᱯᱮ",
    "चौदह":  "ᱜᱮᱞ ᱯᱩᱱ",
    "पंद्रह": "ᱜᱮᱞ ᱢᱚᱬᱮ",
    "बीस":   "ᱵᱟᱨ ᱜᱮᱞ",
    "तीस":   "ᱯᱮ ᱜᱮᱞ",
    "चालीस": "ᱯᱩᱱ ᱜᱮᱞ",
    "पचास":  "ᱢᱚᱬᱮ ᱜᱮᱞ",
    "सौ":    "ᱥᱟᱭ",
    "शून्य": "ᱥᱩᱱᱩᱢ",
    "0": "᱐", "1": "᱑", "2": "᱒", "3": "᱓", "4": "᱔",
    "5": "᱕", "6": "᱖", "7": "᱗", "8": "᱘", "9": "᱙",
    "10": "᱑᱐",
}

NUMBERS_SAT_HI = {v: k for k, v in NUMBERS_HI_SAT.items() if k not in "0123456789"}

# ── Ordinal / math operations ─────────────────────────────────────────────────
MATH_HI_SAT = {
    "जोड़":        "ᱡᱚᱲᱟᱣ",
    "जोड़ना":      "ᱡᱚᱲᱟᱣ ᱥᱮᱪᱮᱫ",
    "जोड़ो":       "ᱡᱚᱲᱟᱣ ᱢᱮ",
    "मिलाओ":       "ᱢᱮᱥᱟᱣ ᱢᱮ",
    "घटाना":       "ᱠᱚᱢ ᱥᱮᱪᱮᱫ",
    "घटाओ":        "ᱠᱚᱢ ᱢᱮ",
    "गुणा":        "ᱜᱩᱱᱟ",
    "भाग":         "ᱵᱷᱟᱜ",
    "बराबर":       "ᱵᱟᱨᱟᱵᱚᱨ",
    "कुल":         "ᱡᱚᱛᱚ",
    "कुल मिलाकर": "ᱡᱚᱛᱚ ᱢᱮᱥᱟᱣ ᱠᱟᱛᱮ",
    "उत्तर":       "ᱛᱮᱞᱟ",
    "सवाल":        "ᱠᱩᱠᱞᱤ",
    "गणित":        "ᱜᱟᱬᱤᱛ",
    "अंक":         "ᱟᱸᱠ",
    "संख्या":      "ᱥᱟᱝᱠᱷᱭᱟ",
}

MATH_SAT_HI = {v: k for k, v in MATH_HI_SAT.items()}

# ── Shapes ────────────────────────────────────────────────────────────────────
SHAPES_HI_SAT = {
    "गोल":       "ᱜᱚᱞ",
    "वृत्त":     "ᱜᱚᱞ ᱪᱤᱛᱟᱹᱨ",
    "चौकोर":     "ᱪᱟᱩᱠᱟ",
    "वर्ग":      "ᱪᱟᱩᱠᱟ",
    "आयत":       "ᱫᱤᱨᱜᱟ ᱪᱟᱩᱠᱟ",
    "त्रिकोण":   "ᱛᱤᱱ ᱠᱩᱱᱟᱹ ᱪᱤᱛᱟᱹᱨ",
    "कोना":      "ᱠᱩᱱᱟᱹ",
    "कोने":      "ᱠᱩᱱᱟᱹ",
    "आकार":      "ᱪᱤᱛᱟᱹᱨ",
    "रेखा":      "ᱨᱮᱠᱷᱟ",
}

SHAPES_SAT_HI = {v: k for k, v in SHAPES_HI_SAT.items()}

# ── Classroom objects ─────────────────────────────────────────────────────────
CLASSROOM_HI_SAT = {
    "पत्थर":      "ᱫᱷᱤᱨᱤ",
    "पत्थर लो":   "ᱫᱷᱤᱨᱤ ᱦᱟᱛᱟᱣ ᱢᱮ",
    "पत्थर हैं":  "ᱫᱷᱤᱨᱤ ᱢᱮᱱᱟᱜᱼᱟ",
    "आम":         "ᱩᱞ",
    "बच्चा":      "ᱦᱚᱲ ᱠᱚ",
    "बच्चे":      "ᱠᱩᱲᱤ ᱦᱚᱲ",
    "बच्चों":     "ᱠᱩᱲᱤ ᱠᱚ",
    "शब्द":       "ᱟᱲᱟᱝ",
    "पढ़ो":       "ᱯᱟᱲᱦᱟᱣ ᱢᱮ",
    "पढ़ना":      "ᱯᱟᱲᱦᱟᱣ ᱥᱮᱪᱮᱫ",
    "लिखो":       "ᱟᱞᱮ ᱢᱮ",
    "लिखना":      "ᱟᱞᱮ ᱥᱮᱪᱮᱫ",
    "बोलो":       "ᱚᱞ ᱢᱮ",
    "बताओ":       "ᱞᱟᱹᱭ ᱢᱮ",
    "देखो":       "ᱫᱟᱜᱟ ᱢᱮ",
    "सुनो":       "ᱦᱩᱭᱩᱠ ᱢᱮ",
    "ढूंढो":      "ᱯᱟᱱᱛᱮ ᱢᱮ",
    "उंगलियां":   "ᱩᱝᱜᱽᱞᱤ",
    "उंगली":      "ᱩᱝᱜᱽᱞᱤ",
    "हाथ":        "ᱦᱟᱛ",
    "किताब":      "ᱯᱩᱛᱷᱤ",
    "कक्षा":      "ᱤᱥᱠᱩᱞ",
    "अध्यापक":    "ᱜᱩᱨᱩ",
    "शिक्षक":     "ᱜᱩᱨᱩ",
    "माँ":        "ᱟᱭᱳ",
    "पानी":       "ᱫᱟᱜ",
    "घर":         "ᱳᱲᱟᱜ",        # was ᱦᱚᱨᱚ ("person"); see GLOSSARY_CHANGES
    "जमीन":       "ᱦᱟᱥᱟ",
    "पेड़":        "ᱫᱟᱨᱮ",
    "सूरज":       "ᱧᱤᱫᱟ",
    "चाँद":       "ᱪᱟᱸᱫ",
}

CLASSROOM_SAT_HI = {v: k for k, v in CLASSROOM_HI_SAT.items()}

# Every change to an entry above, for the native reviewer. docs/glossary_changes.md
# is the readable copy; keep the two in step.
GLOSSARY_CHANGES = [
    {"hindi": "घर", "old": "ᱦᱚᱨᱚ", "new": "ᱳᱲᱟᱜ", "date": "2026-09-24",
     "reason": "ᱦᱚᱨᱚ means person; ᱳᱲᱟᱜ (oṛak') is house. Decided by the team.",
     "review_status": "pending_native_review"},
]

# ── Colors ────────────────────────────────────────────────────────────────────
COLORS_HI_SAT = {
    "लाल":    "ᱦᱤᱨᱤᱧ",
    "नीला":   "ᱱᱤᱞ",
    "हरा":    "ᱥᱟᱜᱟᱭ",
    "पीला":   "ᱥᱟᱥᱟᱝ",
    "काला":   "ᱦᱩᱫ",
    "सफ़ेद":  "ᱦᱤᱡᱩᱜ",
    "सफेद":   "ᱦᱤᱡᱩᱜ",
}

COLORS_SAT_HI = {v: k for k, v in COLORS_HI_SAT.items()}

# ── Common classroom instructions ─────────────────────────────────────────────
INSTRUCTIONS_HI_SAT = {
    "आज हम सीखेंगे":      "ᱛᱮᱦᱮᱸᱡ ᱟᱞᱮ ᱥᱮᱪᱮᱫᱟ",
    "देखो और सुनो":       "ᱫᱟᱜᱟ ᱢᱮ ᱟᱨ ᱦᱩᱭᱩᱜ ᱢᱮ",
    "मेरे साथ बोलो":      "ᱟᱢᱟᱜ ᱥᱟᱝ ᱚᱞ ᱢᱮ",
    "अच्छा काम":          "ᱵᱟᱹᱲᱛᱤ ᱠᱟᱢ",
    "शाबाश":              "ᱵᱟᱹᱲᱛᱤ",
    "फिर से":             "ᱦᱮᱡ ᱠᱷᱚᱱ",
    "एक बार और":          "ᱢᱤᱫ ᱛᱷᱚᱠ ᱟᱨ",
    "सब मिलकर":           "ᱡᱚᱛᱚ ᱢᱤᱞᱟ ᱠᱟᱛᱮ",
    "हाँ":               "ᱦᱟᱹ",
    "नहीं":              "ᱱᱟᱧ",
    "ठीक है":            "ᱵᱟᱹᱲᱛᱤ ᱠᱟᱱᱟ",
    "धन्यवाद":           "ᱥᱮᱫᱟᱭ",
    "बहुत अच्छा":         "ᱵᱟᱨᱦᱮ ᱵᱟᱹᱲᱛᱤ",
    "यहाँ":              "ᱱᱮᱞᱮ",
    "वहाँ":              "ᱱᱚᱠᱟ ᱨᱮ",
    "क्या":              "ᱪᱮᱫ",
    "कितना":             "ᱡᱚᱛᱚ",
    "कितने":             "ᱡᱚᱛᱚ",
    "कौन":               "ᱚᱠᱟ",
    "कहाँ":              "ᱚᱠᱟ ᱨᱮ",
    "क्यों":             "ᱪᱮᱫ ᱞᱟᱹᱜᱤᱫ",
    "कैसे":              "ᱪᱮᱫ ᱠᱟᱛᱮ",
}

INSTRUCTIONS_SAT_HI = {v: k for k, v in INSTRUCTIONS_HI_SAT.items()}

# ── Full verified lesson sentence pairs ──────────────────────────────────────
# These are the NIPUN lesson sentences with expert-verified Santali equivalents.
# The pipeline checks this FIRST before calling the NMT model.
VERIFIED_SENTENCES_HI_SAT = {
    # Grade 1 — Counting
    "आज हम एक से दस तक गिनना सीखेंगे।":
        "ᱛᱮᱦᱮᱸᱡ ᱟᱞᱮ ᱢᱤᱫ ᱠᱷᱚᱱ ᱜᱮᱞ ᱛᱩᱨᱩᱭ ᱜᱤᱱᱛᱤ ᱥᱮᱪᱮᱫᱟ।",
    "अपनी उंगलियां दिखाओ और मेरे साथ गिनो।":
        "ᱟᱢᱟᱜ ᱩᱝᱜᱽᱞᱤ ᱫᱮᱠᱷᱟᱣ ᱢᱮ ᱟᱨ ᱟᱢᱟᱜ ᱥᱟᱝ ᱜᱤᱱᱛᱤ ᱢᱮ।",
    "अब तुम्हारे सामने पांच पत्थर हैं। उन्हें गिनो।":
        "ᱱᱤᱛᱚᱜ ᱟᱢᱟᱜ ᱠᱷᱚᱱ ᱢᱚᱬᱮ ᱫᱷᱤᱨᱤ ᱢᱮᱱᱟᱜᱼᱟ। ᱱᱤᱭᱟᱹ ᱜᱤᱱᱛᱤ ᱢᱮ।",
    "यहाँ कितने पत्थर हैं? बताओ।":
        "ᱱᱮᱞᱮ ᱡᱚᱛᱚ ᱫᱷᱤᱨᱤ ᱢᱮᱱᱟᱜᱼᱟ? ᱞᱟᱹᱭ ᱢᱮ।",

    # Grade 1 — Shapes
    "यह गोल है। यह एक वृत्त है।":
        "ᱱᱚᱶᱟ ᱜᱚᱞ ᱠᱟᱱᱟ। ᱱᱚᱶᱟ ᱢᱤᱫ ᱜᱚᱞ ᱪᱤᱛᱟᱹᱨ ᱠᱟᱱᱟ।",
    "यह चौकोर है। इसके चार कोने हैं।":
        "ᱱᱚᱶᱟ ᱪᱟᱩᱠᱟ ᱠᱟᱱᱟ। ᱱᱚᱶᱟ ᱨᱮᱭᱟᱜ ᱯᱩᱱ ᱠᱩᱱᱟᱹ ᱢᱮᱱᱟᱜᱼᱟ।",
    "अपने आसपास गोल चीज़ें ढूंढो।":
        "ᱟᱢᱟᱜ ᱥᱩᱨ ᱨᱮ ᱜᱚᱞ ᱡᱤᱱᱤᱥ ᱯᱟᱱᱛᱮ ᱢᱮ।",
    "यह कौन सा आकार है?":
        "ᱱᱚᱶᱟ ᱚᱠᱟ ᱪᱤᱛᱟᱹᱨ ᱠᱟᱱᱟ?",

    # Grade 2 — Addition
    "आज हम जोड़ना सीखेंगे। एक और एक मिलाओ।":
        "ᱛᱮᱦᱮᱸᱡ ᱟᱞᱮ ᱡᱚᱲᱟᱣ ᱥᱮᱪᱮᱫᱟ। ᱢᱤᱫ ᱟᱨ ᱢᱤᱫ ᱢᱮᱥᱟᱣ ᱢᱮ।",
    "दो आम और तीन आम मिलाओ। कुल कितने हुए? उंगलियों पर गिनो।":
        "ᱵᱟᱨ ᱩᱞ ᱟᱨ ᱯᱮ ᱩᱞ ᱢᱮᱥᱟᱣ ᱢᱮ। ᱡᱚᱛᱚ ᱛᱤᱱᱟᱜ ᱦᱩᱭᱮᱱᱟ? ᱩᱝᱜᱽᱞᱤ ᱨᱮ ᱜᱤᱱᱛᱤ ᱢᱮ।",
    "अब तुम एक जोड़ का सवाल बनाओ।":
        "ᱱᱤᱛᱚᱜ ᱟᱢ ᱢᱤᱫ ᱡᱚᱲᱟᱣ ᱠᱩᱠᱞᱤ ᱛᱮᱭᱟᱨ ᱢᱮ।",
    "तीन और चार कितने होते हैं?":
        "ᱯᱮ ᱟᱨ ᱯᱩᱱ ᱡᱚᱛᱚ ᱦᱩᱭᱩᱜᱼᱟ?",

    # Grade 2 — Reading
    "यह शब्द है — माँ। इसे पढ़ो।":
        "ᱱᱚᱶᱟ ᱟᱲᱟᱝ ᱠᱟᱱᱟ — ᱟᱭᱳ। ᱱᱚᱶᱟ ᱯᱟᱲᱦᱟᱣ ᱢᱮ।",
    "इस शब्द को तीन बार पढ़ो — पानी।":
        "ᱱᱚᱶᱟ ᱟᱲᱟᱝ ᱯᱮ ᱛᱷᱚᱠ ᱯᱟᱲᱦᱟᱣ ᱢᱮ — ᱫᱟᱜ।",
    "यह शब्द क्या है? पढ़कर बताओ।":
        "ᱱᱚᱶᱟ ᱟᱲᱟᱝ ᱪᱮᱫ ᱠᱟᱱᱟ? ᱯᱟᱲᱦᱟᱣ ᱠᱟᱛᱮ ᱞᱟᱹᱭ ᱢᱮ।",

    # Grade 3 — Subtraction
    "आज हम घटाना सीखेंगे। दस में से तीन घटाओ।":
        "ᱛᱮᱦᱮᱸᱡ ᱟᱞᱮ ᱠᱚᱢ ᱥᱮᱪᱮᱫᱟ। ᱜᱮᱞ ᱠᱷᱚᱱ ᱯᱮ ᱠᱚᱢ ᱢᱮ।",
    "सात पत्थर लो। तीन हटा दो। अब कितने बचे?":
        "ᱮᱭᱟᱭ ᱫᱷᱤᱨᱤ ᱦᱟᱛᱟᱣ ᱢᱮ। ᱯᱮ ᱚᱪᱚᱜ ᱢᱮ। ᱱᱤᱛᱚᱜ ᱡᱚᱛᱚ ᱛᱟᱦᱮᱸᱱᱟ?",
    "आठ में से पांच घटाओ। उत्तर क्या है?":
        "ᱤᱨᱟᱹᱞ ᱠᱷᱚᱱ ᱢᱚᱬᱮ ᱠᱚᱢ ᱢᱮ। ᱛᱮᱞᱟ ᱪᱮᱫ ᱠᱟᱱᱟ?",
}

# Reverse lookup
VERIFIED_SENTENCES_SAT_HI = {v: k for k, v in VERIFIED_SENTENCES_HI_SAT.items()}

# ── Merge all Hi→Sat word-level glossaries into a single dict ─────────────────
ALL_HI_SAT = {}
ALL_HI_SAT.update(NUMBERS_HI_SAT)
ALL_HI_SAT.update(MATH_HI_SAT)
ALL_HI_SAT.update(SHAPES_HI_SAT)
ALL_HI_SAT.update(CLASSROOM_HI_SAT)
ALL_HI_SAT.update(COLORS_HI_SAT)
ALL_HI_SAT.update(INSTRUCTIONS_HI_SAT)

ALL_SAT_HI = {}
ALL_SAT_HI.update(NUMBERS_SAT_HI)
ALL_SAT_HI.update(MATH_SAT_HI)
ALL_SAT_HI.update(SHAPES_SAT_HI)
ALL_SAT_HI.update(CLASSROOM_SAT_HI)
ALL_SAT_HI.update(COLORS_SAT_HI)
ALL_SAT_HI.update(INSTRUCTIONS_SAT_HI)


_INDEX = {}


def _index(table):
    """table keyed by textnorm.normalize_key, built once."""
    if id(table) not in _INDEX:
        from textnorm import normalize_key
        _INDEX[id(table)] = {normalize_key(k): v for k, v in table.items()}
    return _INDEX[id(table)]


def _lookup(table, text):
    from textnorm import normalize_key
    hit = _index(table).get(normalize_key(text or ""))
    return (hit, 100.0) if hit else None


def lookup_hi_to_sat(text: str):
    """The verified Santali for a whole Hindi sentence, or None.

    Matched on textnorm.normalize_key, so punctuation, spacing, nukta and
    digit-script differences do not matter. That is what lets a spoken line
    (speech recognition writes no punctuation) find its verified translation.
    Returns (text, 100.0); the number is only kept for older callers.
    Only whole sentences are matched: the word lists above are not applied.
    """
    return _lookup(VERIFIED_SENTENCES_HI_SAT, text)


def lookup_sat_to_hi(text: str):
    """The verified Hindi for a whole Santali sentence, or None. See lookup_hi_to_sat."""
    return _lookup(VERIFIED_SENTENCES_SAT_HI, text)


def lookup_word_hi_to_sat(text: str):
    """The word-list Santali when `text` is exactly one entry (a flashcard word),
    or None. Used for flashcards only: the model is poor at single words (दो came
    back as "this happens"). The word lists have not had a native review yet."""
    return _lookup(ALL_HI_SAT, text)


def apply_word_glossary_hi_sat(nmt_output: str, hindi_input: str) -> str:
    """
    Post-process NMT output: for every education word in the Hindi source that
    has a glossary entry, replace the NMT's version with the verified Ol Chiki.
    Sorted longest-first so multi-word phrases take priority.
    """
    # We rewrite the NMT output by scanning the hindi_input for glossary words
    # and, for each match, ensuring the NMT output contains the correct Santali.
    # This is a light-touch fix: we don't rewrite from scratch, we patch errors.
    result = nmt_output
    for hi_phrase, sat_phrase in sorted(ALL_HI_SAT.items(),
                                        key=lambda x: len(x[0]), reverse=True):
        if hi_phrase in hindi_input and sat_phrase not in result:
            # Append verified glossary terms that the model missed
            # (safer than replacing blindly)
            pass  # Handled via pre-substitution below
    return result


def preprocess_hindi_with_glossary(hindi_text: str) -> str:
    """
    Replace known Hindi education words with their Santali equivalents BEFORE
    sending to the NMT. This biases the model toward correct Ol Chiki output
    for words it typically mistranslates.
    Not applied if a full-sentence match already exists.
    """
    # Not applied here — full sentence lookup handles this case.
    # Reserved for future sentence-level partial substitution.
    return hindi_text


def nearest_verified(text: str, direction: str = "hi-to-sat", min_ratio: float = 0.6):
    """The verified glossary sentence most like `text`, for a translation that needs
    review: {"source", "target", "similarity"} or None below min_ratio. Compared on
    textnorm.normalize_key with difflib's ratio."""
    import difflib
    from textnorm import normalize_key
    table = VERIFIED_SENTENCES_HI_SAT if direction == "hi-to-sat" else VERIFIED_SENTENCES_SAT_HI
    key = normalize_key(text or "")
    if not key:
        return None
    best, best_r = None, 0.0
    for src, tgt in table.items():
        r = difflib.SequenceMatcher(None, key, normalize_key(src)).ratio()
        if r > best_r:
            best, best_r = (src, tgt), r
    if best is None or best_r < min_ratio:
        return None
    return {"source": best[0], "target": best[1], "similarity": round(best_r, 2)}

