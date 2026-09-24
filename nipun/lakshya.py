# nipun/lakshya.py — the NIPUN Bharat Lakshyas (learning goals), quoted verbatim
#
# Source: "NIPUN Bharat — Guidelines for Implementation", Ministry of Education,
# 2021, page 11, "Lakshyas: Learning Goals of the Mission".
# https://static.pib.gov.in/WriteReadData/specificdocs/documents/2021/jul/doc20217531.pdf
#
# The text of each goal is copied exactly, including the document's own
# spelling ("Recognises" / "Recognizes") and punctuation. Do not reword it.
#
# The IDs are ours, not the Ministry's: NIPUN-<stage>-<domain>-<n>, where
#   stage  = BV (Balvatika), G1, G2, G3
#   domain = LIT (literacy), NUM (numeracy)
#   n      = the goal's position in that stage's list on page 11.
# See docs/lakshya_mapping.md for how each lesson maps to these goals.

SOURCE = ("NIPUN Bharat guidelines, Ministry of Education, 2021 "
          "(doc20217531.pdf), p. 11")

LAKSHYAS = {
    "NIPUN-BV-LIT-1": {"stage": "Balvatika", "domain": "literacy",
                       "text": "Recognises letters and corresponding sounds"},
    "NIPUN-BV-LIT-2": {"stage": "Balvatika", "domain": "literacy",
                       "text": "Reads simple words comprising of at least 2 to 3 alphabets."},
    "NIPUN-BV-NUM-1": {"stage": "Balvatika", "domain": "numeracy",
                       "text": "Recognizes and reads numerals up to 10."},
    "NIPUN-BV-NUM-2": {"stage": "Balvatika", "domain": "numeracy",
                       "text": "Arranges numbers/objects/shapes /occurrence of events in a sequence"},

    "NIPUN-G1-LIT-1": {"stage": "Grade 1", "domain": "literacy",
                       "text": "Reads small sentences consisting of at least 4-5 simple words "
                               "in an age appropriate unknown text."},
    "NIPUN-G1-NUM-1": {"stage": "Grade 1", "domain": "numeracy",
                       "text": "Read and write numbers up to 99"},
    "NIPUN-G1-NUM-2": {"stage": "Grade 1", "domain": "numeracy",
                       "text": "Perform simple addition and subtraction"},

    "NIPUN-G2-LIT-1": {"stage": "Grade 2", "domain": "literacy",
                       "text": "Read with meaning"},
    "NIPUN-G2-LIT-2": {"stage": "Grade 2", "domain": "literacy",
                       "text": "45-60 words per minute"},
    "NIPUN-G2-NUM-1": {"stage": "Grade 2", "domain": "numeracy",
                       "text": "Read and write numbers up to 999"},
    "NIPUN-G2-NUM-2": {"stage": "Grade 2", "domain": "numeracy",
                       "text": "Subtract numbers up to 99"},

    "NIPUN-G3-LIT-1": {"stage": "Grade 3", "domain": "literacy",
                       "text": "Read with meaning"},
    "NIPUN-G3-LIT-2": {"stage": "Grade 3", "domain": "literacy",
                       "text": "at least 60 words per minute"},
    "NIPUN-G3-NUM-1": {"stage": "Grade 3", "domain": "numeracy",
                       "text": "Read and write numbers up to 9999"},
    "NIPUN-G3-NUM-2": {"stage": "Grade 3", "domain": "numeracy",
                       "text": "Solve simple multiplication problems"},
}


def get(lid):
    """The goal for an ID, or None."""
    return LAKSHYAS.get(lid)


def label(lid):
    """One line for a worksheet or flashcard: 'NIPUN-G1-NUM-2 (Grade 1, numeracy): …'."""
    g = LAKSHYAS[lid]
    return f"{lid} ({g['stage']}, {g['domain']}): {g['text']}"
