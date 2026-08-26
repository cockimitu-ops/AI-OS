#!/usr/bin/env python3
"""
Generic prompt-pack PDF builder.

Every product in this line ships the same artifact: a PDF of its module
prompts. This builds all of them from a config dict, so a new product needs
a config file, not a new generator.

Usage:  python3 pack_builder.py packs/pricing.py
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
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Preformatted, Table, TableStyle
)

INK = colors.HexColor("#12161C")
MUTED = colors.HexColor("#5C6470")
RULE = colors.HexColor("#D5D2CA")
CODEBG = colors.HexColor("#F4F3F0")


def styles(accent_hex):
    accent = colors.HexColor(accent_hex)
    return {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=26,
                                leading=30, textColor=INK, spaceAfter=6),
        "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=12, leading=17,
                              textColor=MUTED, spaceAfter=18),
        "eyebrow": ParagraphStyle("eyebrow", fontName="Helvetica-Bold", fontSize=8.5,
                                  leading=12, textColor=accent, spaceAfter=4),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=15, leading=19,
                             textColor=INK, spaceBefore=4, spaceAfter=5),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=15,
                               textColor=INK, spaceAfter=8, alignment=TA_LEFT),
        "note": ParagraphStyle("note", fontName="Helvetica-Oblique", fontSize=9,
                               leading=13, textColor=MUTED, spaceAfter=10),
        "code": ParagraphStyle("code", fontName="Courier", fontSize=8.2, leading=11.4,
                               textColor=INK),
    }


def rule(w=170 * mm):
    t = Table([[""]], colWidths=[w], rowHeights=[0.6])
    t.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 0.6, RULE)]))
    return t


def prompt_block(text, S):
    t = Table([[Preformatted(text.strip(), S["code"])]], colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODEBG),
        ("BOX", (0, 0), (-1, -1), 0.6, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def build(cfg, out_path):
    S = styles(cfg["accent"])
    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"{cfg['product']} — Prompt Pack", author=cfg["product"],
    )
    st = []

    # Cover
    st.append(Spacer(1, 30 * mm))
    st.append(Paragraph(cfg["eyebrow"], S["eyebrow"]))
    st.append(Paragraph(cfg["product"], S["title"]))
    st.append(Paragraph(cfg["subtitle"], S["sub"]))
    st.append(rule())
    st.append(Spacer(1, 8))
    for para in cfg["intro"]:
        st.append(Paragraph(para, S["body"]))
    st.append(Spacer(1, 6))
    st.append(Paragraph(cfg["intro_note"], S["note"]))
    st.append(PageBreak())

    # Modules
    for i, m in enumerate(cfg["modules"]):
        st.append(Paragraph(f"MODULE {i + 1}", S["eyebrow"]))
        st.append(Paragraph(m["title"], S["h2"]))
        st.append(rule())
        st.append(Spacer(1, 7))
        st.append(Paragraph(m["intro"], S["body"]))
        st.append(Spacer(1, 3))
        st.append(prompt_block(m["prompt"], S))
        st.append(Spacer(1, 9))
        st.append(Paragraph(m["tip"], S["note"]))
        st.append(PageBreak())

    # Closing
    st.append(Paragraph(cfg["closing_eyebrow"], S["eyebrow"]))
    st.append(Paragraph(cfg["closing_title"], S["h2"]))
    st.append(rule())
    st.append(Spacer(1, 7))
    for para in cfg["closing"]:
        st.append(Paragraph(para, S["body"]))
    st.append(Spacer(1, 10))
    st.append(rule())
    st.append(Spacer(1, 7))
    st.append(Paragraph(cfg["closing_note"], S["note"]))

    doc.build(st)
    print(f"Built {out_path} ({len(cfg['modules'])} modules)")


def load(path):
    spec = importlib.util.spec_from_file_location("cfg", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CONFIG


if __name__ == "__main__":
    cfg_path = Path(sys.argv[1])
    cfg = load(cfg_path)
    build(cfg, cfg.get("output", f"{cfg_path.stem}-prompt-pack.pdf"))
