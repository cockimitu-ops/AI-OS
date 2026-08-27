#!/usr/bin/env python3
"""Generic competitor-analysis report PDF builder.

Every real order under Research_And_Briefing_Gigs delivers the same artifact
shape: cover, executive summary, market overview, per-competitor profiles, a
comparison table, SWOT, and recommendations — Fulfillment_Workflow.md's own
Step 6 structure. This builds all of them from a config dict, so a new order
needs a config file, not a new generator. Mirrors TemplateSales'
_infra/pack_builder.py pattern deliberately, same reasoning: one generator,
reused, not rewritten per report.

Usage:  python3 report_builder.py reports/<name>.py
"""
import sys
import importlib.util
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    ListFlowable, ListItem,
)

# Same palette as TemplateSales' pack_builder.py, kept consistent on purpose -
# a buyer who's seen one product from this line should recognize the other.
INK = colors.HexColor("#12161C")
MUTED = colors.HexColor("#5C6470")
RULE = colors.HexColor("#D5D2CA")
TABLE_HEAD_BG = colors.HexColor("#12161C")
TABLE_ALT_BG = colors.HexColor("#F4F3F0")


def styles(accent_hex):
    accent = colors.HexColor(accent_hex)
    return {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=25,
                                leading=29, textColor=INK, spaceAfter=6),
        "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=12, leading=17,
                              textColor=MUTED, spaceAfter=4),
        "eyebrow": ParagraphStyle("eyebrow", fontName="Helvetica-Bold", fontSize=8.5,
                                  leading=12, textColor=accent, spaceAfter=4),
        "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=17, leading=21,
                             textColor=INK, spaceBefore=2, spaceAfter=8),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13, leading=17,
                             textColor=INK, spaceBefore=10, spaceAfter=5),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9.5, leading=14,
                               textColor=INK, spaceAfter=7, alignment=TA_LEFT),
        "label": ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=9.5,
                                leading=14, textColor=INK),
        "note": ParagraphStyle("note", fontName="Helvetica-Oblique", fontSize=8.5,
                               leading=12, textColor=MUTED, spaceAfter=8),
        "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=7.8, leading=10,
                               textColor=INK),
        "cellhead": ParagraphStyle("cellhead", fontName="Helvetica-Bold", fontSize=7.8,
                                   leading=10, textColor=colors.white),
        "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=9.5,
                                 leading=14, textColor=INK),
    }


def rule(w=170 * mm):
    t = Table([[""]], colWidths=[w], rowHeights=[0.6])
    t.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 0.6, RULE)]))
    return t


def bullets(items, S):
    return ListFlowable(
        [ListItem(Paragraph(i, S["bullet"]), spaceAfter=3) for i in items],
        bulletType="bullet", start="•", leftIndent=12,
    )


def data_table(rows, S, col_widths):
    """rows[0] is the header row. Wraps every cell in a Paragraph so long text
    wraps instead of overflowing the page width."""
    wrapped = [[Paragraph(str(c), S["cellhead"]) for c in rows[0]]]
    for r in rows[1:]:
        wrapped.append([Paragraph(str(c), S["cell"]) for c in r])
    t = Table(wrapped, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEAD_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for i in range(1, len(wrapped)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), TABLE_ALT_BG))
    t.setStyle(TableStyle(style))
    return t


def build(cfg, out_path):
    S = styles(cfg["accent"])
    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=cfg["title"], author=cfg.get("author", "Research & Briefing"),
    )
    st = []

    # Cover
    st.append(Spacer(1, 34 * mm))
    st.append(Paragraph(cfg["eyebrow"], S["eyebrow"]))
    st.append(Paragraph(cfg["title"], S["title"]))
    st.append(Paragraph(cfg["subtitle"], S["sub"]))
    st.append(rule())
    st.append(Spacer(1, 8))
    for para in cfg.get("cover_note", []):
        st.append(Paragraph(para, S["note"]))
    st.append(PageBreak())

    for section in cfg["sections"]:
        st.append(Paragraph(section.get("eyebrow", ""), S["eyebrow"]))
        st.append(Paragraph(section["title"], S["h1"]))
        st.append(rule())
        st.append(Spacer(1, 6))
        for block in section["content"]:
            kind = block["type"]
            if kind == "h2":
                st.append(Paragraph(block["text"], S["h2"]))
            elif kind == "p":
                st.append(Paragraph(block["text"], S["body"]))
            elif kind == "label_p":
                st.append(Paragraph(f'<b>{block["label"]}</b> {block["text"]}',
                                    S["body"]))
            elif kind == "bullets":
                st.append(bullets(block["items"], S))
                st.append(Spacer(1, 6))
            elif kind == "table":
                st.append(data_table(block["rows"], S, block["col_widths"]))
                st.append(Spacer(1, 6))
            elif kind == "note":
                st.append(Paragraph(block["text"], S["note"]))
        st.append(PageBreak())

    doc.build(st)
    print(f"Built {out_path} ({len(cfg['sections'])} sections)")


def load(path):
    spec = importlib.util.spec_from_file_location("cfg", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CONFIG


if __name__ == "__main__":
    cfg_path = Path(sys.argv[1])
    cfg = load(cfg_path)
    build(cfg, cfg.get("output", f"{cfg_path.stem}.pdf"))
