"""Clause streaming (Phase L2): how an utterance is cut into chunks. No models."""

import streaming as s


def test_short_lines_are_never_split():
    # Classroom lines stay whole, even with "और" inside.
    assert s.chunks("तीन और चार कितने होते हैं?") == ["तीन और चार कितने होते हैं?"]
    assert s.chunks("दो आम और तीन आम मिलाओ।") == ["दो आम और तीन आम मिलाओ।"]


def test_sentence_ends_always_split():
    assert s.chunks("आज हम जोड़ना सीखेंगे। एक और एक मिलाओ।") == ["आज हम जोड़ना सीखेंगे।", "एक और एक मिलाओ।"]


def test_long_sentences_split_at_clause_words_without_tiny_parts():
    text = "ऐसा माना जाता है कि पेरिस के निवासी अहंकारी असभ्य और अभिमानी होते हैं"
    parts = s.chunks(text)
    assert parts == ["ऐसा माना जाता है", "कि पेरिस के निवासी अहंकारी असभ्य और अभिमानी होते हैं"]
    assert " ".join(parts) == text


def test_no_chunk_starts_with_an_auxiliary_or_postposition():
    text = "कुछ अणुओं में अस्थिर केंद्रक होता है जिसका मतलब यह है कि उनमें थोड़े या बिना किसी झटके से टूटने की प्रवृत्ति होती है"
    parts = s.chunks(text)
    assert len(parts) > 1 and " ".join(parts) == text
    for p in parts[1:]:
        assert p.split()[0] not in s.NEVER_START, p
    for p in parts:
        assert len(p.split()) <= s.MAX_WORDS


def test_nothing_is_lost_or_reordered():
    text = "यह एक बहुत लंबा वाक्य है जिसमें कोई विराम नहीं है और जो बस चलता ही जाता है बिना रुके आगे तक"
    assert " ".join(s.chunks(text)) == text
