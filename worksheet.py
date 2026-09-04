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
import datetime, os

# Register Unicode fonts for Ol Chiki (Santali) and Devanagari (Hindi)
_FONT_DIR = os.path.join(os.path.dirname(__file__), "models", "fonts")
_UNICODE_FONT = "Helvetica"          # fallback
_UNICODE_FONT_BOLD = "Helvetica-Bold"
try:
    _olchiki_path = os.path.join(_FONT_DIR, "NotoSansOlChiki-Regular.ttf")
    _deva_path    = os.path.join(_FONT_DIR, "NotoSansDevanagari-Regular.ttf")
    if os.path.exists(_olchiki_path):
        pdfmetrics.registerFont(TTFont("NotoSansOlChiki", _olchiki_path))
    if os.path.exists(_deva_path):
        pdfmetrics.registerFont(TTFont("NotoSansDevanagari", _deva_path))
    _UNICODE_FONT = "NotoSansDevanagari"
    _UNICODE_FONT_BOLD = "NotoSansDevanagari"
    print("  Worksheet: Unicode fonts loaded.")
except Exception as _e:
    print(f"  Worksheet: font load warning ({_e}), falling back to Helvetica")

def ps(name, size, bold=False, color="#111111", align=TA_LEFT):
    # Use Ol Chiki font for labels that may contain Santali; Devanagari for rest
    fname = (_UNICODE_FONT_BOLD if bold else _UNICODE_FONT)
    return ParagraphStyle(name, fontSize=size,
        fontName=fname,
        textColor=colors.HexColor(color),
        alignment=align, spaceAfter=4, leading=size*1.4)

NIPUN = {
    "1": "Recognises letters, numbers 1-20, and simple words in mother tongue",
    "2": "Reads two-syllable words; adds and subtracts single-digit numbers",
    "3": "Reads short paragraphs; multiplication tables 1-5"
}

def generate_worksheet(hindi, santali, grade="2", topic="Lesson",
                       lesson_steps=None, out="vaanisetu_worksheet.pdf"):
    doc = SimpleDocTemplate(out, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    s = []
    H  = ps("H",  16, True,  "#0D2137", TA_CENTER)
    S  = ps("S",  10, False, "#1A5276", TA_CENTER)
    LB = ps("LB", 11, True,  "#0D2137")
    BD = ps("BD", 10, False, "#111111")
    FT = ps("FT",  7, False, "#888888", TA_CENTER)

    s += [
        Paragraph("VaaniSetu — Bilingual Classroom Worksheet", H),
        Paragraph(
            f"Grade {grade}  |  {topic}  |  "
            f"{datetime.date.today().strftime('%d %B %Y')}", S),
        Spacer(1, 0.5*cm),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#AED6F1"),
                   spaceBefore=0, spaceAfter=15),
    ]

    goal = NIPUN.get(str(grade), "Aligned with FLN learning outcomes")
    s.append(Paragraph("<b>NIPUN Bharat Competency Goal:</b>", LB))
    s.append(Paragraph(goal, BD))
    s.append(Spacer(1, 0.8*cm))

    # Master Translation Pair
    s.append(Paragraph("<b>Key Concept Translation:</b>", LB))
    data = [
        [Paragraph("Hindi (Teacher)", LB), Paragraph("Santali (Student)", LB)],
        [Paragraph(hindi, BD), Paragraph(santali, BD)]
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
        s.append(Paragraph("<b>Lesson Progression:</b>", LB))
        h_data = [["Step", "Mode", "Hindi Instruction", "Santali Translation"]]
        for i, stp in enumerate(lesson_steps):
            m = stp['type'].replace('_', ' ').title()
            h_data.append([
                str(i+1), m,
                Paragraph(stp['hindi'], BD),
                Paragraph(stp['santali'], BD)
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
        Paragraph("Generated automatically by VaaniSetu AI Teaching Assistant", FT)
    ]

    doc.build(s)
    return out
