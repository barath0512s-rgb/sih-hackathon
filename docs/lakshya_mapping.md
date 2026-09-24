# Lessons → NIPUN Lakshya mapping

**Source of the goals:** *NIPUN Bharat — Guidelines for Implementation*, Ministry of
Education, 2021, page 11, "Lakshyas: Learning Goals of the Mission"
([doc20217531.pdf](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2021/jul/doc20217531.pdf)).
The goal text in `nipun/lakshya.py` is copied word for word from that page.

**The IDs are ours.** The Ministry does not number the goals. Our scheme is
`NIPUN-<stage>-<domain>-<n>`: stage `BV` (Balvatika), `G1`, `G2` or `G3`; domain
`LIT` or `NUM`; `n` is the goal's position in that stage's list on page 11.

| ID | Stage | Goal (verbatim) |
|---|---|---|
| NIPUN-BV-LIT-1 | Balvatika | Recognises letters and corresponding sounds |
| NIPUN-BV-LIT-2 | Balvatika | Reads simple words comprising of at least 2 to 3 alphabets. |
| NIPUN-BV-NUM-1 | Balvatika | Recognizes and reads numerals up to 10. |
| NIPUN-BV-NUM-2 | Balvatika | Arranges numbers/objects/shapes /occurrence of events in a sequence |
| NIPUN-G1-LIT-1 | Grade 1 | Reads small sentences consisting of at least 4-5 simple words in an age appropriate unknown text. |
| NIPUN-G1-NUM-1 | Grade 1 | Read and write numbers up to 99 |
| NIPUN-G1-NUM-2 | Grade 1 | Perform simple addition and subtraction |
| NIPUN-G2-LIT-1 | Grade 2 | Read with meaning |
| NIPUN-G2-LIT-2 | Grade 2 | 45-60 words per minute |
| NIPUN-G2-NUM-1 | Grade 2 | Read and write numbers up to 999 |
| NIPUN-G2-NUM-2 | Grade 2 | Subtract numbers up to 99 |
| NIPUN-G3-LIT-1 | Grade 3 | Read with meaning |
| NIPUN-G3-LIT-2 | Grade 3 | at least 60 words per minute |
| NIPUN-G3-NUM-1 | Grade 3 | Read and write numbers up to 9999 |
| NIPUN-G3-NUM-2 | Grade 3 | Solve simple multiplication problems |

## How each lesson is tagged

"Full" means the lesson teaches what the goal says. "Partial" means it covers
only part of it. A lesson's grade is the class it is written for. A Lakshya can
come from an earlier stage when the lesson revises that goal.

| Lesson (grade/topic) | Lakshya IDs | Fit | Why |
|---|---|---|---|
| grade1/counting_1_10 | BV-NUM-1, G1-NUM-1 | full, partial | Counts and names numbers up to 10. G1-NUM-1 goes up to 99. |
| grade1/shapes | BV-NUM-2 | partial | Names shapes. The goal is arranging shapes in a sequence. No Lakshya covers naming shapes. |
| grade2/addition | G1-NUM-2 | full | Single-digit addition is "simple addition". It is a Grade 1 goal, revised here. |
| grade2/reading_words | BV-LIT-2, G2-LIT-1 | full, partial | Reads short words. G2-LIT-1 means reading text with meaning, not single words. |
| grade3/subtraction | G1-NUM-2, G2-NUM-2 | full, partial | Single-digit subtraction. G2-NUM-2 goes up to 99. |

**What this shows:** no lesson yet reaches a Grade 3 goal (numbers up to 9999,
multiplication, 60 words per minute). The lesson set covers foundational goals
up to Grade 2.

**Review status:** every lesson is `pending_teacher_review`. A teacher has not
yet checked these mappings.

`tests/test_lakshya.py` checks that every lesson has at least one valid ID, that
the lesson's domain matches its goals, and that the worksheet prints the tag.
