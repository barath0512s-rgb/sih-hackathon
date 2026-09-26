"""A translation the loop guard flags is not presented as one (no models needed).

Server side: pipeline marks it needs_review, the API adds the nearest verified
sentence. Page side: "check with a native speaker" badge, no auto-play.
The end-to-end API check with the real models is in tests/test_api.py.
"""

import re
from pathlib import Path

from education_glossary import nearest_verified

PAGE = (Path(__file__).resolve().parent.parent / "frontend.html").read_text(encoding="utf-8")


def test_the_nearest_verified_sentence_is_offered():
    n = nearest_verified("आज हम एक से दस तक गिनती सीखेंगे", "hi-to-sat")
    assert n and n["source"] == "आज हम एक से दस तक गिनना सीखेंगे।" and n["similarity"] >= 0.6
    assert nearest_verified("बाज़ार में आज बहुत भीड़ थी और बारिश हो रही थी।", "hi-to-sat") is None


def test_a_flagged_reply_is_never_auto_played():
    voice = re.search(r"function voice\(r\)\{(.*?)\n\}", PAGE, re.S).group(1)
    assert voice.index("if (flagged(r)) return;") < voice.index("play(true)")
    flagged = re.search(r"function flagged\(r\)\{(.*?)\n\}", PAGE, re.S).group(1)
    assert 'badge("review")' in flagged and "play(" not in flagged
    chunk = PAGE[PAGE.index('ev.type === "chunk"'):PAGE.index('ev.type === "done"')]
    assert chunk.index("flagged(ev)") < chunk.index("queuePush")


def test_the_badge_text_exists():
    assert 'src_review:"⚠️ मूल वक्ता से जाँचें"' in PAGE
    assert 'src_review:"⚠️ Check with a native speaker"' in PAGE
