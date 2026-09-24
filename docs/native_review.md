# Items awaiting native Santali review

Nothing below has been checked by a native Santali speaker. Mark each item
confirmed or corrected, and the team will update the code.

## 0. Doubtful word-list entries (review these first)

The word lists in `education_glossary.py` are used **only for flashcards**
until they are reviewed; translation uses whole verified sentences. Every
card or answer that uses an unreviewed entry shows a "review pending" badge.
These six look wrong or are missing:

| Hindi | Card shows now | Source | Why it is doubtful | Correct Santali (reviewer) |
|---|---|---|---|---|
| बच्चा (child) | ᱦᱚᱲ ᱠᱚ (हॉड़् कॉ) | word list | ᱦᱚᱲ ᱠᱚ seems to mean "people", not "child" | |
| कक्षा (classroom) | ᱤᱥᱠᱩᱞ (इस्कुल्) | word list | ᱤᱥᱠᱩᱞ is "school", not "class" | |
| कितना (how much) | ᱡᱚᱛᱚ (जॉतॉ) | word list | ᱡᱚᱛᱚ seems to mean "all"; कुल and कितने map to the same word | |
| दो (two) | ᱵᱟᱨ (बार्) | word list | The model gives ᱱᱚᱶᱟ ᱫᱚ ᱦᱩᱭᱩᱜ ᱠᱟᱱᱟ ("this happens"); confirm ᱵᱟᱨ | |
| आठ (eight) | ᱤᱨᱟᱹᱞ (इरल्) | word list | The model gives "8 ᱜᱚᱴᱟᱝ"; confirm ᱤᱨᱟᱹᱞ | |
| तारा (star) | ᱥᱴᱟᱨ (स्टार्) | model | No word-list entry; the model borrowed English "star" | |

## 1. Glossary changes

See `docs/glossary_changes.md`.

## 2. Santali number words (priority: numbers are central to NIPUN numeracy)

The app speaks every number with these words (`translit/olchiki.number_to_santali`).
Units, 10 and 100 come from the glossary; everything else is composed by rule:
tens as `<unit> ᱜᱮᱞ` (so 20 = ᱵᱟᱨ ᱜᱮᱞ), teens as `ᱜᱮᱞ <unit>`, hundreds as `<unit> ᱥᱟᱭ`.
Numbers above 999 are read digit by digit. **Is the composition right, and is
ᱵᱟᱨ ᱜᱮᱞ the word a child uses for 20?**

| Number | Santali (Ol Chiki) | Spoken as (Devanagari) | Source |
|---|---|---|---|
| 0 | ᱥᱩᱱᱩᱢ | सुनुम् | glossary |
| 1 | ᱢᱤᱫ | मित् | glossary |
| 2 | ᱵᱟᱨ | बार् | glossary |
| 3 | ᱯᱮ | पे | glossary |
| 4 | ᱯᱩᱱ | पुन् | glossary |
| 5 | ᱢᱚᱬᱮ | मॉणे | glossary |
| 6 | ᱛᱩᱨᱩᱭ | तुरुय् | glossary |
| 7 | ᱮᱭᱟᱭ | एयाय् | glossary |
| 8 | ᱤᱨᱟᱹᱞ | इरल् | glossary |
| 9 | ᱟᱨᱮ | आरे | glossary |
| 10 | ᱜᱮᱞ | गेल् | glossary |
| 11 | ᱜᱮᱞ ᱢᱤᱫ | गेल् मित् | glossary |
| 12 | ᱜᱮᱞ ᱵᱟᱨ | गेल् बार् | glossary |
| 13 | ᱜᱮᱞ ᱯᱮ | गेल् पे | glossary |
| 14 | ᱜᱮᱞ ᱯᱩᱱ | गेल् पुन् | glossary |
| 15 | ᱜᱮᱞ ᱢᱚᱬᱮ | गेल् मॉणे | glossary |
| 16 | ᱜᱮᱞ ᱛᱩᱨᱩᱭ | गेल् तुरुय् | composed by rule |
| 17 | ᱜᱮᱞ ᱮᱭᱟᱭ | गेल् एयाय् | composed by rule |
| 18 | ᱜᱮᱞ ᱤᱨᱟᱹᱞ | गेल् इरल् | composed by rule |
| 19 | ᱜᱮᱞ ᱟᱨᱮ | गेल् आरे | composed by rule |
| 20 | ᱵᱟᱨ ᱜᱮᱞ | बार् गेल् | glossary |
| 23 | ᱵᱟᱨ ᱜᱮᱞ ᱯᱮ | बार् गेल् पे | composed by rule |
| 30 | ᱯᱮ ᱜᱮᱞ | पे गेल् | glossary |
| 40 | ᱯᱩᱱ ᱜᱮᱞ | पुन् गेल् | glossary |
| 50 | ᱢᱚᱬᱮ ᱜᱮᱞ | मॉणे गेल् | glossary |
| 99 | ᱟᱨᱮ ᱜᱮᱞ ᱟᱨᱮ | आरे गेल् आरे | composed by rule |
| 100 | ᱥᱟᱭ | साय् | glossary |
| 101 | ᱥᱟᱭ ᱢᱤᱫ | साय् मित् | composed by rule |
| 120 | ᱥᱟᱭ ᱵᱟᱨ ᱜᱮᱞ | साय् बार् गेल् | composed by rule |
| 999 | ᱟᱨᱮ ᱥᱟᱭ ᱟᱨᱮ ᱜᱮᱞ ᱟᱨᱮ | आरे साय् आरे गेल् आरे | composed by rule |

## 3. Transliteration rules for speech

Ol Chiki is converted to Devanagari so the Hindi voice can read it. The eight
phonetic rules in the docstring of `translit/olchiki.py` (vowels ᱚ and ᱟᱹ, checked
stops, ahad, relaa, phaarkaa, ᱶ, numbers, ᱝ, ᱷ) all need confirming, ideally by
listening to the voice read lesson lines.

## 4. Santali answers accepted from children

| Lesson | Question | Accepted Santali answer | Source |
|---|---|---|---|
| 1 counting_1_10 | यहाँ कितने पत्थर हैं? बताओ। | ᱯᱮ | education_glossary |
| 1 counting_1_10 | यहाँ कितने पत्थर हैं? बताओ। | ᱯᱮᱭᱟ | IndicTrans2 output |
| 1 shapes | यह कौन सा आकार है? | ᱛᱤᱱ ᱠᱩᱱᱟᱹ ᱪᱤᱛᱟᱹᱨ | education_glossary |
| 1 shapes | यह कौन सा आकार है? | ᱴᱨᱤᱝᱜᱚᱞ | IndicTrans2 output |
| 1 shapes | यह कौन सा आकार है? | ᱴᱤᱠᱚᱱ | IndicTrans2 output |
| 2 addition | तीन और चार कितने होते हैं? | ᱮᱭᱟᱭ | education_glossary |
| 2 addition | तीन और चार कितने होते हैं? | ᱮᱭᱟᱭ ᱜᱚᱴᱟᱝ | IndicTrans2 output |
| 2 reading_words | यह शब्द क्या है? पढ़कर बताओ। | ᱳᱲᱟᱜ | education_glossary (corrected 2026-09-24) |
| 2 reading_words | यह शब्द क्या है? पढ़कर बताओ। | ᱚᱲᱟᱜ | IndicTrans2 output |
| 3 subtraction | आठ में से पांच घटाओ। उत्तर क्या है? | ᱯᱮ | education_glossary |
| 3 subtraction | आठ में से पांच घटाओ। उत्तर क्या है? | ᱯᱮᱭᱟ | IndicTrans2 output |

## 5. Santali interface text

Every Santali string in `frontend.html` (the `sat:` table) was written without a
native speaker. Some new strings fall back to Hindi on purpose rather than invent Santali.
