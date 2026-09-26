# worksheet.py — bilingual NIPUN Bharat aligned PDF generator

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable)
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xml.sax.saxutils import escape
import datetime, os, re
import config
from nipun import lakshya

# Fonts. No single bundled font covers Latin, Devanagari and Ol Chiki: the
# Noto Devanagari file has no Latin letters, so English text set in it came out
# blank. Each run of text is set in the font for its script (see _mixed).
_FONT_DIR = str(config.STATIC_DIR / "fonts")   # tracked in git; OFL licences alongside
_SCRIPT_FONTS = {}                              # script -> registered font name


def _register(name, filename, script):
    path = os.path.join(_FONT_DIR, filename)
    if not os.path.exists(path):
        print(f"  Worksheet: {filename} missing, {script} will not render in the PDF")
        return
    pdfmetrics.registerFont(TTFont(name, path))
    # Paragraph markup uses <b>, so the family needs a bold slot even though
    # these are single-weight files, or reportlab raises on every <b>.
    pdfmetrics.registerFontFamily(name, normal=name, bold=name, italic=name, boldItalic=name)
    _SCRIPT_FONTS[script] = name


try:
    _register("NotoSansDevanagari", "NotoSansDevanagari-Regular.ttf", "devanagari")
    _register("NotoSansOlChiki", "NotoSansOlChiki-Regular.ttf", "olchiki")
except Exception as _e:
    print(f"  Worksheet: font load warning ({_e}), Hindi and Santali may not render")

_RUNS = re.compile(r"([ऀ-ॿ᳐-᳿꣠-ꣿ]+)|([᱐-᱿]+)")


def _mixed(text):
    """Escape `text` for a Paragraph and put each Devanagari or Ol Chiki run in
    its own font. Spaces and punctuation between words of one script stay in
    that script's run, so shaping is not broken up."""
    out, pos = [], 0
    text = str(text)
    for m in _RUNS.finditer(text):
        out.append(escape(text[pos:m.start()]))
        script = "devanagari" if m.group(1) else "olchiki"
        font = _SCRIPT_FONTS.get(script)
        run = escape(m.group(0))
        out.append(f'<font name="{font}">{run}</font>' if font else run)
        pos = m.end()
    out.append(escape(text[pos:]))
    return "".join(out)


def P(text, style, bold=False):
    """A Paragraph of plain (unescaped) text in any mix of scripts."""
    body = _mixed(text)
    return Paragraph(f"<b>{body}</b>" if bold else body, style)


def ps(name, size, bold=False, color="#111111", align=TA_LEFT, leading=1.4):
    """Style: Latin base font; Hindi and Santali runs switch font inline."""
    return ParagraphStyle(name, fontSize=size,
        fontName="Helvetica-Bold" if bold else "Helvetica",
        textColor=colors.HexColor(color),
        alignment=align, spaceAfter=4, leading=size*leading)


def ps_sat(name, size, bold=False, color="#111111", align=TA_LEFT):
    """Style for Santali text: Ol Chiki needs a little more line height."""
    return ps(name, size, bold, color, align, leading=1.5)


# Headings in Hindi and Santali: the worksheet goes to the class, not to an
# English reader. The Santali reuses the interface's words where it has them
# (frontend.html) and is on the native-review list (docs/native_review.md).
# The Lakshya text stays as the Ministry wrote it (English), with our ID.
L = {
    "title":     ("द्विभाषी कार्यपत्रक", "ᱠᱟᱹᱢᱤ ᱠᱟᱜᱚᱡ"),
    "grade":     ("कक्षा", "ᱠᱞᱟᱥ"),
    "balvatika": ("बालवाटिका", "ᱵᱟᱞᱣᱟᱴᱤᱠᱟ"),
    "goal":      ("NIPUN लक्ष्य", "NIPUN ᱞᱚᱠᱷᱭᱚ"),
    "no_goal":   ("यह कार्यपत्रक किसी पाठ से नहीं बना है।", ""),
    "source":    ("लक्ष्य का पाठ शिक्षा मंत्रालय के NIPUN भारत दिशानिर्देश (2021), पृष्ठ 11 से ज्यों का त्यों लिया गया है।", ""),
    "key":       ("मुख्य वाक्य", "ᱢᱩᱬᱩᱛ ᱟᱲᱟᱝ"),
    "hindi_col": ("हिंदी (शिक्षक)", "ᱦᱤᱱᱫᱤ (ᱜᱩᱨᱩ)"),
    "sat_col":   ("संताली (बच्चे)", "ᱥᱟᱱᱛᱟᱲᱤ (ᱜᱤᱫᱽᱨᱟᱹ)"),
    "lines":     ("पाठ की पंक्तियाँ", "ᱥᱮᱪᱮᱫ ᱨᱮᱭᱟᱜ ᱟᱲᱟᱝ"),
    "mode":      ("प्रकार", ""),
    "hindi":     ("हिंदी", "ᱦᱤᱱᱫᱤ"),
    "santali":   ("संताली", "ᱥᱟᱱᱛᱟᱲᱤ"),
    "footer":    ("{app} से अपने आप बना। संताली पंक्तियों की मूल वक्ता से समीक्षा अभी बाकी है।", ""),
    "lesson_script":        ("सिखाना", "ᱥᱮᱪᱮᱫ"),
    "activity_instruction": ("करना", "ᱠᱟᱹᱢᱤ"),
    "assessment_prompt":    ("पूछना", "ᱠᱩᱠᱞᱤ"),
}


def both(key, **kw):
    """ "हिंदी / ᱥᱟᱱᱛᱟᱲᱤ", or the Hindi alone where there is no Santali yet."""
    hi, sat = L[key]
    hi = hi.format(**kw)
    return f"{hi} / {sat}" if sat else hi


def generate_worksheet(hindi, santali, grade="2", topic="",
                       lesson_steps=None, out=None, lakshya_ids=None):
    """lakshya_ids: the NIPUN goals the lesson works towards (nipun/lakshya.py).
    None for a sheet made outside a lesson: then no goal is printed."""
    if out is None:
        out = str(config.DATA_DIR / "last_worksheet.pdf")
    doc = SimpleDocTemplate(out, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    s = []
    H   = ps("H",  16, True,  "#0D2137", TA_CENTER)
    S   = ps("S",  10, False, "#1A5276", TA_CENTER)
    LB  = ps("LB", 11, True,  "#0D2137")
    BD  = ps("BD", 10, False, "#111111")
    SAT = ps_sat("SAT", 11, False, "#111111")
    FT  = ps("FT",  7, False, "#888888", TA_CENTER)

    names = config.APP_NAME_LOCAL
    grade_txt = (both("balvatika") if str(grade) in ("0", "Balvatika")
                 else f"{L['grade'][0]} {grade} / {L['grade'][1]} {grade}")
    s += [
        P(f"{' / '.join(n for n in (names['hi'], names['sat']) if n)} — {both('title')}", H),
        P("  |  ".join(x for x in (grade_txt, topic,
                                   datetime.date.today().strftime("%d.%m.%Y")) if x), S),
        Spacer(1, 0.5*cm),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#AED6F1"),
                   spaceBefore=0, spaceAfter=15),
    ]

    s.append(P(both("goal") + ":", LB, bold=True))
    if lakshya_ids:
        for lid in lakshya_ids:
            s.append(P(f"{lid}: {lakshya.get(lid)['text']}", BD))
        s.append(P(both("source"), FT))
    else:
        s.append(P(both("no_goal"), BD))
    s.append(Spacer(1, 0.8*cm))

    # Master Translation Pair
    s.append(P(both("key") + ":", LB, bold=True))
    data = [
        [P(both("hindi_col"), LB, bold=True), P(both("sat_col"), LB, bold=True)],
        [P(hindi or "—", BD),                 P(santali or "—", SAT)]
    ]
    t = Table(data, colWidths=[8.5*cm, 8.5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor("#F2F4F4")),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor("#BDC3C7")),
        ('VALIGN',     (0,0), (-1,-1), 'TOP'),
        ('PADDING',    (0,0), (-1,-1), 8),
    ]))
    s.append(t)
    s.append(Spacer(1, 1*cm))

    # Lesson Step History
    if lesson_steps:
        s.append(P(both("lines") + ":", LB, bold=True))
        h_data = [[P(h, LB, bold=True) for h in
                   ("#", both("mode"), both("hindi"), both("santali"))]]
        for i, stp in enumerate(lesson_steps):
            m = both(stp["type"]) if stp.get("type") in L else stp.get("type", "")
            h_data.append([
                P(str(i+1), BD), P(m, BD),
                P(stp.get('hindi', ''), BD),
                P(stp.get('santali', ''), SAT)
            ])
        ht = Table(h_data, colWidths=[1.2*cm, 3*cm, 6.4*cm, 6.4*cm])
        ht.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F2F4F4")),
            ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor("#BDC3C7")),
            ('VALIGN',     (0,0), (-1,-1), 'TOP'),
            ('PADDING',    (0,0), (-1,-1), 6),
        ]))
        s.append(ht)
        s.append(Spacer(1, 1*cm))

    s += [
        Spacer(1, 2*cm),
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#BDC3C7")),
        P(both("footer", app=names["hi"]), FT)
    ]

    doc.build(s)
    return out
