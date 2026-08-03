#!/usr/bin/env python3
"""CLMS 기술 논문 PDF - 지표 산출 및 수리 모형의 이론적 배경"""
from fpdf import FPDF
import os

FONT_TITLE = "/Users/yalkongs/Library/Fonts/SCDream6.otf"
FONT_HEADING = "/Users/yalkongs/Library/Fonts/SCDream5.otf"
FONT_BODY = "/Users/yalkongs/Library/Fonts/SCDream3.otf"
FONT_MONO = "/System/Library/Fonts/Supplemental/NotoSansGothic-Regular.ttf"


class Paper(FPDF):
    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        self.set_auto_page_break(auto=True, margin=25)
        self.add_font("title", "", FONT_TITLE)
        self.add_font("heading", "", FONT_HEADING)
        self.add_font("body", "", FONT_BODY)
        self.add_font("mono", "", FONT_MONO)
        self._header_text = "iM뱅크 CLMS 기술 논문: 지표 산출 및 수리 모형"

    def header(self):
        if self.page_no() > 1:
            self.set_font("body", "", 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 5, self._header_text, align='L')
            self.cell(0, 5, f"- {self.page_no()} -", align='R', new_x="LMARGIN", new_y="NEXT")
            self.line(10, 12, 200, 12)
            self.ln(3)
            self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font("body", "", 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, "Copyright (c) 2026 iM Bank. All rights reserved.", align='C')
        self.set_text_color(0, 0, 0)

    def sec(self, num, title):
        self.ln(4)
        if self.get_y() > 250:
            self.add_page()
        self.set_font("title", "", 16)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, f"{num}. {title}", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(0, 51, 102)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)
        self.set_line_width(0.2)

    def sub(self, num, title):
        self.ln(2)
        if self.get_y() > 260:
            self.add_page()
        self.set_font("heading", "", 13)
        self.set_text_color(0, 70, 130)
        self.cell(0, 8, f"{num}  {title}", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def subsub(self, title):
        self.ln(1)
        if self.get_y() > 265:
            self.add_page()
        self.set_font("heading", "", 11)
        self.set_text_color(50, 50, 50)
        self.cell(0, 7, f"  {title}", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
        self.set_text_color(0, 0, 0)

    def txt(self, text):
        self.set_font("body", "", 10)
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def formula(self, lines):
        self.ln(1)
        self.set_fill_color(245, 245, 250)
        self.set_font("heading", "", 9)
        for line in lines:
            self.set_x(20)
            self.cell(170, 5.5, line, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def tbl(self, headers, rows, cw=None):
        if self.get_y() > 250:
            self.add_page()
        n = len(headers)
        if cw is None:
            w = 190 / n
            cw = [w] * n
        self.set_font("heading", "", 9)
        self.set_fill_color(0, 51, 102)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(cw[i], 7, h, border=1, fill=True, align='C')
        self.ln()
        self.set_text_color(0, 0, 0)
        self.set_font("body", "", 9)
        fill = False
        for row in rows:
            if self.get_y() > 270:
                self.add_page()
                self.set_font("heading", "", 9)
                self.set_fill_color(0, 51, 102)
                self.set_text_color(255, 255, 255)
                for i, h in enumerate(headers):
                    self.cell(cw[i], 7, h, border=1, fill=True, align='C')
                self.ln()
                self.set_text_color(0, 0, 0)
                self.set_font("body", "", 9)
            self.set_fill_color(240, 245, 255) if fill else self.set_fill_color(255, 255, 255)
            for i, val in enumerate(row):
                al = 'C' if i > 0 and len(str(val)) < 15 else 'L'
                self.cell(cw[i], 6.5, str(val), border=1, fill=True, align=al)
            self.ln()
            fill = not fill
        self.ln(2)

    def bullet(self, text, indent=15):
        self.set_font("body", "", 10)
        self.set_x(indent)
        self.cell(5, 5.5, chr(8226))
        self.multi_cell(175 - indent, 5.5, text)


def build():
    p = Paper()

    # ── TITLE PAGE ──
    p.add_page()
    p.ln(30)
    p.set_font("title", "", 26)
    p.set_text_color(0, 51, 102)
    p.cell(0, 14, "여신생애주기관리시스템(CLMS)의", align='C', new_x="LMARGIN", new_y="NEXT")
    p.ln(2)
    p.cell(0, 14, "지표 산출 및 수리 모형에 관한 연구", align='C', new_x="LMARGIN", new_y="NEXT")
    p.ln(4)
    p.set_font("heading", "", 12)
    p.set_text_color(80, 80, 80)
    p.cell(0, 8, "A Study on Metrics Calculation and Mathematical Models", align='C', new_x="LMARGIN", new_y="NEXT")
    p.cell(0, 8, "in Credit Lifecycle Management System", align='C', new_x="LMARGIN", new_y="NEXT")
    p.ln(12)
    p.set_draw_color(0, 51, 102)
    p.set_line_width(0.8)
    p.line(60, p.get_y(), 150, p.get_y())
    p.ln(12)
    p.set_text_color(0, 0, 0)
    p.set_font("heading", "", 14)
    p.cell(0, 8, "iMBank  \ud669\uc6d0\ucca0", align='C', new_x="LMARGIN", new_y="NEXT")
    p.ln(2)
    p.set_font("heading", "", 11)
    p.set_text_color(100, 100, 100)
    p.cell(0, 7, "iM\ub4f1\ud06c \ub514\uc9c0\ud138\uae08\uc735\uadf8\ub8f9", align='C', new_x="LMARGIN", new_y="NEXT")
    p.ln(3)
    p.cell(0, 7, "2026\ub144 2\uc6d4", align='C', new_x="LMARGIN", new_y="NEXT")

    p.ln(20)
    p.set_text_color(0, 0, 0)
    p.set_font("heading", "", 10)
    p.cell(0, 6, chr(9472) * 3 + " Abstract " + chr(9472) * 3, align='C', new_x="LMARGIN", new_y="NEXT")
    p.ln(3)
    p.set_font("body", "", 10)
    p.set_x(25)
    p.multi_cell(160, 5.5,
        "\ubcf8 \ub17c\ubb38\uc740 iM\ub4f1\ud06c \uc5ec\uc2e0\uc0dd\uc560\uc8fc\uae30\uad00\ub9ac\uc2dc\uc2a4\ud15c(CLMS)\uc758 \ud575\uc2ec \uc9c0\ud45c \uc0b0\ucd9c \uccb4\uacc4\uc640 \uc218\ub9ac \ubaa8\ud615\uc758 "
        "\uc774\ub860\uc801 \ubc30\uacbd\uc744 \ub2e4\ub8ec\ub2e4. Basel II/III \ub0b4\ubd80\ub4f1\uae09\ubc95(IRB)\uc5d0 \uae30\ubc18\ud55c \uc2e0\uc6a9\ub9ac\uc2a4\ud06c \uacc4\ub7c9\ud654 "
        "\uccb4\uacc4\ub97c \ud575\uc2ec\uc73c\ub85c, Vasicek \ub2e8\uc77c\uc694\uc778 \ubaa8\ud615\uc5d0 \uae30\ucd08\ud55c \uc704\ud5d8\uac00\uc911\uc790\uc0b0(RWA) \uc0b0\ucd9c, "
        "\uc704\ud5d8\uc870\uc815\uc218\uc775\ub960(RAROC) \uae30\ubc18 \uac00\uaca9\uacb0\uc815, 5\ucc44\ub110 \uc120\ud589\uc9c0\ud45c \uc870\uae30\uacbd\ubcf4\uc2dc\uc2a4\ud15c(EWS), "
        "\ud3ec\ud2b8\ud3f4\ub9ac\uc624 \ucd5c\uc801\ud654, \uc2a4\ud2b8\ub808\uc2a4 \ud14c\uc2a4\ud2b8, ALM \uae08\ub9ac\ub9ac\uc2a4\ud06c \uad00\ub9ac \ub4f1\uc758 \uc218\ud559\uc801 "
        "\uc0b0\ucd9c\uc2dd\uacfc \uc2dc\uc2a4\ud15c \uad6c\ud604 \ub0b4\uc6a9\uc744 \uc0c1\uc138\ud788 \uae30\uc220\ud55c\ub2e4. \uac01 \ubaa8\ud615\uc758 \uc774\ub860\uc801 \uadfc\uac70\uc640 "
        "\ud568\uaed8 \uc2dc\uc2a4\ud15c\uc5d0 \uc801\uc6a9\ub41c \uc0c1\uc218\uce58 \ubc0f \uac00\uc815\uce58\ub97c \uba85\uc2dc\ud558\uace0, \ud55c\uacc4\uc810\uacfc \ud5a5\ud6c4 "
        "\uacfc\uc81c\ub97c \ub17c\uc758\ud55c\ub2e4.", align='J')

    # ── TOC ──
    p.add_page()
    p.set_font("title", "", 18)
    p.set_text_color(0, 51, 102)
    p.cell(0, 12, "\ubaa9  \ucc28", align='C', new_x="LMARGIN", new_y="NEXT")
    p.ln(6)
    toc = [
        ("1", "\uc11c\ub860", "\uc5f0\uad6c \ubaa9\uc801 \ubc0f \ubc94\uc704"),
        ("2", "\uc2e0\uc6a9\ub9ac\uc2a4\ud06c \uacc4\ub7c9\ud654 \uc774\ub860", "Vasicek, Merton, Basel IRB"),
        ("3", "\ud575\uc2ec \ub9ac\uc2a4\ud06c \ud30c\ub77c\ubbf8\ud130", "PD, LGD, EAD, EL"),
        ("4", "\uc790\ubcf8\uc694\uad6c\ub7c9 \ubc0f RWA", "\uc790\uc0b0\uc0c1\uad00\uacc4\uc218, \uc790\ubcf8\uc694\uad6c\ub7c9 K, EC"),
        ("5", "RAROC \ubc0f \uac00\uaca9\uacb0\uc815", "FTP, \uae08\ub9ac\uad6c\uc131, \ud5c8\ub4e4\ub808\uc774\ud2b8"),
        ("6", "\uc870\uae30\uacbd\ubcf4\uc2dc\uc2a4\ud15c (EWS)", "5\ucc44\ub110 \uc120\ud589\uc9c0\ud45c, \uc885\ud569\uc810\uc218"),
        ("7", "\uc2a4\ud2b8\ub808\uc2a4 \ud14c\uc2a4\ud2b8", "\uc2dc\ub098\ub9ac\uc624 \ubc0f PD/LGD \ucda9\uaca9"),
        ("8", "\ud3ec\ud2b8\ud3f4\ub9ac\uc624 \ucd5c\uc801\ud654", "RAROC \uadf9\ub300\ud654, HHI \uc81c\uc57d"),
        ("9", "ALM \uae08\ub9ac\ub9ac\uc2a4\ud06c", "\uae08\ub9ac\uac31, \ub4c0\ub808\uc774\uc158, EVE"),
        ("10", "ESG \ub9ac\uc2a4\ud06c \ud1b5\ud569", "ESG \uc810\uc218\ud654, PD \uac00\uac10"),
        ("11", "\ubaa8\ud615 \uac80\uc99d", "Backtest, Vintage, Override"),
        ("12", "\ub2f4\ubcf4 \ubc0f Workout", "LTV, NPV, \ud68c\uc218 \uc2dc\ub098\ub9ac\uc624"),
        ("13", "\uc2dc\uc2a4\ud15c \uc0c1\uc218 \ubc0f \uac00\uc815\uce58", "\ube44\uc6a9\ub960, FTP \ucee4\ube0c, \ub4f1\uae09-PD"),
        ("14", "\ud55c\uacc4 \ubc0f \ud5a5\ud6c4 \uacfc\uc81c", ""),
    ]
    p.set_font("body", "", 11)
    p.set_text_color(0, 0, 0)
    for num, title, desc in toc:
        p.set_x(20)
        p.cell(12, 7, num)
        p.cell(60, 7, title)
        p.set_font("body", "", 9)
        p.set_text_color(100, 100, 100)
        p.cell(100, 7, desc, new_x="LMARGIN", new_y="NEXT")
        p.set_font("body", "", 11)
        p.set_text_color(0, 0, 0)

    # ══════════════════════════════════════
    # 1. 서론
    # ══════════════════════════════════════
    p.add_page()
    p.sec("1", "\uc11c\ub860")
    p.sub("1.1", "\uc5f0\uad6c \ubaa9\uc801")
    p.txt(
        "\uc740\ud589 \uc5ec\uc2e0\uc5c5\ubb34\uc758 \ud575\uc2ec\uc740 \uc2e0\uc6a9\ub9ac\uc2a4\ud06c\uc758 \uc815\ud655\ud55c \uacc4\ub7c9\ud654\uc640 \uc774\ub97c \uae30\ubc18\uc73c\ub85c \ud55c \ud569\ub9ac\uc801 \uc758\uc0ac\uacb0\uc815\uc5d0 \uc788\ub2e4. "
        "\ubcf8 \ub17c\ubb38\uc740 iM\ub4f1\ud06c CLMS\uc758 \ud575\uc2ec \uc9c0\ud45c \uc0b0\ucd9c \uccb4\uacc4\uc640 \uc218\ub9ac \ubaa8\ud615\uc758 \uc774\ub860\uc801 \ubc30\uacbd\uc744 \uccb4\uacc4\uc801\uc73c\ub85c "
        "\ubb38\uc11c\ud654\ud568\uc73c\ub85c\uc368, \uc2dc\uc2a4\ud15c\uc758 \uc218\ud559\uc801 \uae30\ucd08\uc640 \uad6c\ud604 \ub0b4\uc6a9\uc744 \uba85\ud655\ud788 \ud558\ub294 \uac83\uc744 \ubaa9\uc801\uc73c\ub85c \ud55c\ub2e4."
    )
    p.sub("1.2", "\uc5f0\uad6c \ubc94\uc704")
    p.txt(
        "\ubcf8 \ub17c\ubb38\uc758 \ubc94\uc704\ub294 \ub2e4\uc74c\uacfc \uac19\ub2e4: (1) Basel IRB \uae30\ubc18 RWA \uc0b0\ucd9c \ubaa8\ud615, "
        "(2) RAROC \ubc0f \uac00\uaca9\uacb0\uc815 \ubaa8\ud615, (3) \ub2e4\ucc44\ub110 \uc870\uae30\uacbd\ubcf4\uc2dc\uc2a4\ud15c, (4) \uc2a4\ud2b8\ub808\uc2a4 \ud14c\uc2a4\ud2b8, "
        "(5) \ud3ec\ud2b8\ud3f4\ub9ac\uc624 \ucd5c\uc801\ud654, (6) ALM \uae08\ub9ac\ub9ac\uc2a4\ud06c, (7) ESG \ub9ac\uc2a4\ud06c \ud1b5\ud569, "
        "(8) \ubaa8\ud615 \uac80\uc99d \uccb4\uacc4. \uac01 \ubaa8\ud615\uc758 \uc218\ud559\uc801 \uc0b0\ucd9c\uc2dd\uacfc \ud568\uaed8 \uc2dc\uc2a4\ud15c \uad6c\ud604 \ucf54\ub4dc\uc640\uc758 "
        "\ub300\uc751 \uad00\uacc4\ub97c \uc81c\uc2dc\ud55c\ub2e4."
    )
    p.sub("1.3", "\uc774\ub860\uc801 \uae30\ubc18")
    p.txt("\ubcf8 \uc2dc\uc2a4\ud15c\uc740 \ub2e4\uc74c\uc758 \ud559\uc220\uc801\xb7\uaddc\uc81c\uc801 \ud504\ub808\uc784\uc6cc\ud06c\uc5d0 \uae30\ucd08\ud55c\ub2e4:")
    for r in [
        "Basel II/III IRB Approach (BCBS, 2006; 2017) - \uc790\ubcf8\uc694\uad6c\ub7c9 \uc0b0\ucd9c \uacf5\uc2dd",
        "Vasicek (1991/2002) Single-Factor Model - \uc790\uc0b0\uc0c1\uad00\uacc4\uc218 \ubc0f \uc790\ubcf8\uc694\uad6c\ub7c9 \ub3c4\ucd9c",
        "Merton (1974) Structural Model - \uae30\uc5c5\uac00\uce58 \uae30\ubc18 \ubd80\ub3c4\ud655\ub960 \uc774\ub860",
        "KMV Model (Crosbie & Bohn, 2003) - Distance-to-Default \uac1c\ub150",
        "Markowitz (1952) Portfolio Theory - \ud3ec\ud2b8\ud3f4\ub9ac\uc624 \ucd5c\uc801\ud654 \uc774\ub860",
        "Altman Z-Score (1968) - \uc7ac\ubb34\ube44\uc728 \uae30\ubc18 \ubd80\uc2e4\uc608\uce21",
    ]:
        p.bullet(r)

    # ══════════════════════════════════════
    # 2. 신용리스크 계량화 이론
    # ══════════════════════════════════════
    p.add_page()
    p.sec("2", "\uc2e0\uc6a9\ub9ac\uc2a4\ud06c \uacc4\ub7c9\ud654 \uc774\ub860")

    p.sub("2.1", "Vasicek \ub2e8\uc77c\uc694\uc778 \ubaa8\ud615 (Single-Factor Model)")
    p.txt(
        "Vasicek(2002)\uc758 \ub2e8\uc77c\uc694\uc778 \ubaa8\ud615\uc740 Basel II IRB \uacf5\uc2dd\uc758 \uc774\ub860\uc801 \uae30\ucd08\ub97c \uc81c\uacf5\ud55c\ub2e4. "
        "\uc774 \ubaa8\ud615\uc5d0\uc11c \ucc44\ubb34\uc790 i\uc758 \uc790\uc0b0\uac00\uce58 \uc218\uc775\ub960 X_i\ub294 \ub2e4\uc74c\uacfc \uac19\uc774 \ud45c\ud604\ub41c\ub2e4:"
    )
    p.formula([
        "X_i = \u221aR \u00d7 Z + \u221a(1-R) \u00d7 \u03b5_i",
        "",
        "  Z    : \uccb4\uacc4\uc694\uc778 (systematic factor), Z ~ N(0,1)",
        "  \u03b5_i  : \uace0\uc720\uc694\uc778 (idiosyncratic factor), \u03b5_i ~ N(0,1)",
        "  R    : \uc790\uc0b0\uc0c1\uad00\uacc4\uc218 (asset correlation)",
    ])
    p.txt(
        "\ucc44\ubb34\uc790 i\ub294 X_i < \u03a6\u207b\u00b9(PD_i)\uc77c \ub54c \ubd80\ub3c4\ud55c\ub2e4. \uccb4\uacc4\uc694\uc778 Z\uac00 \uc5b4\ub5a4 \uc218\uc900 z\ub85c "
        "\uc2e4\ud604\ub41c \uc870\uac74\uc5d0\uc11c\uc758 \uc870\uac74\ubd80 \ubd80\ub3c4\ud655\ub960\uc740:"
    )
    p.formula([
        "PD(z) = \u03a6( (\u03a6\u207b\u00b9(PD) - \u221aR \u00d7 z) / \u221a(1-R) )",
    ])
    p.txt(
        "Basel II\ub294 99.9% \uc2e0\ub8b0\uc218\uc900\uc5d0\uc11c\uc758 \uc190\uc2e4\uc744 \uae30\uc900\uc73c\ub85c \uc790\ubcf8\uc694\uad6c\ub7c9\uc744 \uc0b0\uc815\ud55c\ub2e4. "
        "\uc989, z = \u03a6\u207b\u00b9(0.999)\ub97c \ub300\uc785\ud558\uc5ec \ucd5c\uc545 \uc2dc\ub098\ub9ac\uc624 \uc870\uac74\ubd80 \ubd80\ub3c4\ud655\ub960\uc744 \uad6c\ud55c\ub2e4."
    )

    p.sub("2.2", "Merton \uad6c\uc870\ubaa8\ud615 (Structural Model)")
    p.txt(
        "Merton(1974)\uc758 \uad6c\uc870\ubaa8\ud615\uc5d0\uc11c \uae30\uc5c5\uc758 \uc790\uc0b0\uac00\uce58 V(t)\ub294 \uae30\ud558\ube0c\ub77c\uc6b4\uc6b4\ub3d9\uc744 \ub530\ub974\uba70, "
        "\uc790\uc0b0\uac00\uce58\uac00 \ubd80\ucc44\uc758 \uc561\uba74\uac00 D \uc774\ud558\ub85c \ud558\ub77d\ud560 \ub54c \ubd80\ub3c4\uac00 \ubc1c\uc0dd\ud55c\ub2e4. "
        "\uc774\ub85c\ubd80\ud130 Distance-to-Default(DD)\uac00 \ub3c4\ucd9c\ub41c\ub2e4:"
    )
    p.formula([
        "DD = (ln(V/D) + (\u03bc - \u03c3\u00b2/2) \u00d7 T) / (\u03c3 \u00d7 \u221aT)",
        "",
        "  V : \uc790\uc0b0\uc758 \uc2dc\uc7a5\uac00\uce58",
        "  D : \ubd80\ucc44\uc758 \uc561\uba74\uac00",
        "  \u03bc : \uc790\uc0b0\uc218\uc775\ub960 \uae30\ub300\uac12",
        "  \u03c3 : \uc790\uc0b0\uc218\uc775\ub960 \ubcc0\ub3d9\uc131",
        "  T : \uc794\uc874\ub9cc\uae30",
    ])
    p.txt(
        "\ubcf8 \uc2dc\uc2a4\ud15c\uc758 EWS \uc2dc\uc7a5\uc2e0\ud638 \ubaa8\ub4c8\uc5d0\uc11c DD \uac12\uc744 \ud65c\uc6a9\ud558\uc5ec "
        "\uc0c1\uc7a5\uae30\uc5c5\uc758 \ubd80\ub3c4\ub9ac\uc2a4\ud06c\ub97c \ud3c9\uac00\ud55c\ub2e4."
    )

    p.sub("2.3", "Basel IRB \uccb4\uacc4")
    p.txt(
        "Basel II/III \ub0b4\ubd80\ub4f1\uae09\ubc95(Internal Ratings-Based Approach)\uc740 \uc740\ud589\uc774 "
        "\uc790\uccb4\uc801\uc73c\ub85c \uc0b0\ucd9c\ud55c PD, LGD, EAD, M(Maturity)\uc744 \ud65c\uc6a9\ud558\uc5ec "
        "\uc704\ud5d8\uac00\uc911\uc790\uc0b0(RWA)\uacfc \uc790\ubcf8\uc694\uad6c\ub7c9\uc744 \uc0b0\uc815\ud558\ub294 \ubc29\ubc95\ub860\uc774\ub2e4. "
        "\ubcf8 \uc2dc\uc2a4\ud15c\uc740 Foundation IRB \uc811\uadfc\ubc95\uc744 \uae30\ubc18\uc73c\ub85c \ud55c\ub2e4."
    )

    # ══════════════════════════════════════
    # 3. 핵심 리스크 파라미터
    # ══════════════════════════════════════
    p.add_page()
    p.sec("3", "\ud575\uc2ec \ub9ac\uc2a4\ud06c \ud30c\ub77c\ubbf8\ud130")

    p.sub("3.1", "\ubd80\ub3c4\ud655\ub960 (Probability of Default, PD)")
    p.txt(
        "\ubd80\ub3c4\ud655\ub960(PD)\uc740 \ucc44\ubb34\uc790\uac00 \ud5a5\ud6c4 1\ub144 \ub0b4 \ucc44\ubb34\ub97c \uc774\ud589\ud558\uc9c0 \ubabb\ud560 \ud655\ub960\uc744 \ub098\ud0c0\ub0b8\ub2e4. "
        "\uc2dc\uc2a4\ud15c\uc740 TTC(Through-the-Cycle) PD\uc640 PIT(Point-in-Time) PD\ub97c \ubaa8\ub450 \uad00\ub9ac\ud55c\ub2e4."
    )
    p.formula([
        "PIT_PD = TTC_PD \u00d7 \u03b1_cycle",
        "",
        "  \u03b1_cycle : \uacbd\uae30\uc21c\ud658 \uc870\uc815\uacc4\uc218 (\uae30\ubcf8\uac12 1.1)",
    ])
    p.txt("16\ub2e8\uacc4 \uc2e0\uc6a9\ub4f1\uae09 \uccb4\uacc4\uc5d0 \ub530\ub978 PD \ub9e4\ud551:")
    p.tbl(
        ["\ub4f1\uae09", "PD", "\ub4f1\uae09", "PD", "\ub4f1\uae09", "PD"],
        [
            ["AAA", "0.02%", "A+", "0.15%", "BB+", "3.00%"],
            ["AA+", "0.04%", "A", "0.25%", "BB", "4.80%"],
            ["AA", "0.06%", "A-", "0.45%", "BB-", "7.50%"],
            ["AA-", "0.10%", "BBB+", "0.70%", "B+", "12.00%"],
            ["", "", "BBB", "1.15%", "B", "20.00%"],
            ["", "", "BBB-", "1.85%", "B-", "30.00%"],
        ],
        [25, 25, 25, 30, 40, 45]
    )

    p.sub("3.2", "\ubd80\ub3c4\uc2dc\uc190\uc2e4\ub960 (Loss Given Default, LGD)")
    p.txt(
        "LGD\ub294 \ubd80\ub3c4 \ubc1c\uc0dd \uc2dc \uc2e4\uc81c \uc190\uc2e4\ub960\uc744 \ub098\ud0c0\ub0b4\uba70, \ub2f4\ubcf4\uc758 \uc720\ubb34\uc640 \uc9c0\uc5ed\uc5d0 \ub530\ub77c \ucc28\ub4f1 \uc801\uc6a9\ub41c\ub2e4."
    )
    p.tbl(
        ["\uad6c\ubd84", "\uc218\ub3c4\uad8c", "\ub300\uad6c\uacbd\ubd81", "\ubd80\uc0b0\uacbd\ub0a8"],
        [
            ["\ub2f4\ubcf4\ubd80 (\uc800)", "18%", "25%", "30%"],
            ["\ub2f4\ubcf4\ubd80 (\uace0)", "32%", "40%", "48%"],
            ["\ubb34\ub2f4\ubcf4 (\uc800)", "38%", "45%", "50%"],
            ["\ubb34\ub2f4\ubcf4 (\uace0)", "50%", "58%", "65%"],
        ],
        [50, 45, 50, 45]
    )

    p.sub("3.3", "\ubd80\ub3c4\uc2dc\uc775\uc2a4\ud3ec\uc800 (Exposure at Default, EAD)")
    p.formula([
        "EAD = Outstanding + Unutilized \u00d7 CCF",
        "",
        "  Outstanding : \ud604\uc7ac \ub300\ucd9c \uc794\uc561",
        "  Unutilized  : \ubbf8\uc0ac\uc6a9 \ud55c\ub3c4\uc561",
        "  CCF         : \uc2e0\uc6a9\ud658\uc0b0\uacc4\uc218 (Credit Conversion Factor, 0.5~1.5)",
    ])

    p.sub("3.4", "\uc608\uc0c1\uc190\uc2e4 (Expected Loss, EL)")
    p.formula([
        "EL = PD \u00d7 LGD \u00d7 EAD",
        "",
        "\uc608\uc0c1\uc190\uc2e4 \uc2a4\ud504\ub808\ub4dc (bp) = PD \u00d7 LGD \u00d7 10,000",
    ])
    p.txt(
        "\uc608\uc0c1\uc190\uc2e4\uc740 \ud1b5\uacc4\uc801\uc73c\ub85c \uc608\uce21\ub418\ub294 \ud3c9\uade0 \uc190\uc2e4\ub85c, \ub300\uc190\ucda9\ub2f9\uae08\uc73c\ub85c \ucee4\ubc84\ud574\uc57c \ud55c\ub2e4. "
        "\uc608\uc0c1\uc190\uc2e4\uc744 \ucd08\uacfc\ud558\ub294 \ube44\uc608\uc0c1\uc190\uc2e4(UL)\uc740 \uc790\ubcf8\uc73c\ub85c \ucee4\ubc84\ud55c\ub2e4."
    )

    # ══════════════════════════════════════
    # 4. 자본요구량 및 RWA
    # ══════════════════════════════════════
    p.add_page()
    p.sec("4", "\uc790\ubcf8\uc694\uad6c\ub7c9 \ubc0f RWA")

    p.sub("4.1", "\uc790\uc0b0\uc0c1\uad00\uacc4\uc218 (Asset Correlation, R)")
    p.txt("Basel IRB \uacf5\uc2dd\uc5d0\uc11c \uc790\uc0b0\uc0c1\uad00\uacc4\uc218\ub294 PD\uc758 \ud568\uc218\ub85c \uacb0\uc815\ub41c\ub2e4:")
    p.formula([
        "R = 0.12 \u00d7 (1 - e^(-50\u00b7PD)) / (1 - e^(-50))",
        "  + 0.24 \u00d7 [1 - (1 - e^(-50\u00b7PD)) / (1 - e^(-50))]",
        "",
        "\ubc94\uc704: 0.12 \u2264 R \u2264 0.24",
        "PD\uac00 \ub192\uc744\uc218\ub85d R\uc774 \ub0ae\uc544\uc9c0\ub294 \uad6c\uc870 (\uace0\ub4f1\uae09 \uae30\uc5c5\uc77c\uc218\ub85d \uccb4\uacc4\uc801 \uc704\ud5d8 \ub178\ucd9c \ud07c)",
    ])

    p.sub("4.2", "\ub9cc\uae30\uc870\uc815 \uacc4\uc218 (Maturity Adjustment, b)")
    p.formula([
        "b = (0.11852 - 0.05478 \u00d7 ln(max(PD, 0.0001)))\u00b2",
    ])

    p.sub("4.3", "\uc790\ubcf8\uc694\uad6c\ub7c9 (Capital Requirement, K)")
    p.formula([
        "K = LGD \u00d7 [ \u03a6( \u03a6\u207b\u00b9(PD)/\u221a(1-R) + \u221a(R/(1-R)) \u00d7 \u03a6\u207b\u00b9(0.999) ) - PD \u00d7 LGD ]",
        "",
        "K_adj = K \u00d7 (1 + (M - 2.5) \u00d7 b) / (1 - 1.5 \u00d7 b)",
        "",
        "  \u03a6   : \ud45c\uc900\uc815\uaddc\ubd84\ud3ec CDF",
        "  \u03a6\u207b\u00b9 : \ud45c\uc900\uc815\uaddc\ubd84\ud3ec \uc5ed\ud568\uc218",
        "  M   : \uc794\uc874\ub9cc\uae30 (\uae30\ubcf8\uac12: 2.5\ub144)",
    ])
    p.txt(
        "\uc774 \uacf5\uc2dd\uc740 99.9% \uc2e0\ub8b0\uc218\uc900 \uc870\uac74\ubd80 \uc190\uc2e4\uc5d0\uc11c EL\uc744 \ucc28\uac10\ud55c \uac83\uc73c\ub85c, "
        "Gordy(2003)\uac00 \uc99d\uba85\ud55c \ub300\uaddc\ubaa8 \ud3ec\ud2b8\ud3f4\ub9ac\uc624\uc758 \uc810\uadfc\uc801 \ub2e8\uc77c\uc694\uc778 \ud2b9\uc131\uc5d0 \uae30\ucd08\ud55c\ub2e4."
    )

    p.sub("4.4", "\uc704\ud5d8\uac00\uc911\uc790\uc0b0 (RWA)")
    p.formula([
        "RWA = K_adj \u00d7 12.5 \u00d7 EAD",
        "",
        "  12.5 = 1 / 0.08 (\ucd5c\uc18c\uc790\ubcf8\ube44\uc728 8%\uc758 \uc5ed\uc218)",
    ])
    p.txt("\uad6c\ud604 \ucf54\ub4dc (backend/app/services/calculations.py):")
    p.formula([
        "# \uac04\ub7b5\ud654\ub41c RWA \uc0b0\ucd9c",
        "rwa = outstanding \u00d7 (0.5 + pd \u00d7 10) \u00d7 (lgd / 0.45)",
    ])

    p.sub("4.5", "\uacbd\uc81c\uc801 \uc790\ubcf8 (Economic Capital, EC)")
    p.formula([
        "EC = RWA \u00d7 10.5%",
        "",
        "  BIS \ucd5c\uc18c \uc790\ubcf8\ube44\uc728 8% + \uc790\ubcf8\ubcf4\uc804\uc644\ucda9\uc790\ubcf8 2.5% = 10.5%",
    ])

    # ══════════════════════════════════════
    # 5. RAROC 및 가격결정
    # ══════════════════════════════════════
    p.add_page()
    p.sec("5", "RAROC \ubc0f \uac00\uaca9\uacb0\uc815")

    p.sub("5.1", "RAROC \uae30\ubcf8 \uacf5\uc2dd")
    p.txt(
        "RAROC(Risk-Adjusted Return on Capital)\uc740 \uc704\ud5d8\uc744 \ubc18\uc601\ud55c \uc218\uc775\ub960\ub85c, "
        "\uc5ec\uc2e0 \uc758\uc0ac\uacb0\uc815\uc758 \ud575\uc2ec \uc9c0\ud45c\uc774\ub2e4."
    )
    p.formula([
        "RAROC = (\uc774\uc790\uc218\uc775 - \uc870\ub2ec\ube44\uc6a9 - \uc6b4\uc601\ube44 - EL) / EC",
    ])
    p.subsub("\uac1c\ubcc4 \uac74\ubcc4 (What-if \ubd84\uc11d)")
    p.formula([
        "RAROC = (A \u00d7 r_final - A \u00d7 r_FTP - A \u00d7 r_opex - PD \u00d7 LGD \u00d7 A)",
        "        / (RWA(PD, LGD, A, M) \u00d7 0.105)",
        "",
        "  A       : \ub300\ucd9c\uae08\uc561",
        "  r_final : \ucd5c\uc885 \uc801\uc6a9\uae08\ub9ac (\uc5f0\uc728)",
        "  r_FTP   : \ub0b4\ubd80\uc790\uae08\uc774\uc804\uac00\uaca9 (\ud14c\ub108\ubcc4)",
        "  r_opex  : \uc6b4\uc601\ube44\uc728 (0.5%)",
    ])

    p.subsub("\ud3ec\ud2b8\ud3f4\ub9ac\uc624 \uc218\uc900 (\ub300\uc2dc\ubcf4\ub4dc)")
    p.formula([
        "RAROC_port = [ \u03a3(O_i \u00d7 r_i) - \u03a3O_i \u00d7 0.048 - \u03a3EL_i ] / (\u03a3RWA_i \u00d7 0.105)",
        "",
        "  O_i   : i\ubc88\uc9f8 \uc5ec\uc2e0 \uc794\uc561",
        "  r_i   : i\ubc88\uc9f8 \uc5ec\uc2e0 \ucd5c\uc885\uae08\ub9ac",
        "  0.048 : \ucd1d\ube44\uc6a9\ub960 (\uc870\ub2ec 4.3% + \uc6b4\uc601 0.5%)",
    ])
    p.txt("\ud5c8\ub4e4\ub808\uc774\ud2b8(Hurdle Rate): 12%. RAROC\uc774 \ud5c8\ub4e4\ub808\uc774\ud2b8\ub97c \ucd08\uacfc\ud574\uc57c \uacbd\uc81c\uc801 \ubd80\uac00\uac00\uce58\ub97c \ucc3d\ucd9c\ud55c\ub2e4.")

    p.sub("5.2", "FTP (Funds Transfer Pricing) \uccb4\uacc4")
    p.txt("\ub0b4\ubd80\uc790\uae08\uc774\uc804\uac00\uaca9(FTP)\uc740 \ud14c\ub108\ubcc4 \uc2dc\uc7a5\uae08\ub9ac\ub97c \ubc18\uc601\ud55c\ub2e4:")
    p.tbl(
        ["\ud14c\ub108", "FTP \uae08\ub9ac", "\uad6c\uc131"],
        [
            ["3\uac1c\uc6d4", "3.20%", "\uae30\ubcf8\uae08\ub9ac + \uc720\ub3d9\uc131 \ud504\ub9ac\ubbf8\uc5c4"],
            ["12\uac1c\uc6d4", "3.50%", "+ \uae30\uac04 \ud504\ub9ac\ubbf8\uc5c4"],
            ["24\uac1c\uc6d4", "3.70%", ""],
            ["36\uac1c\uc6d4", "3.85%", ""],
            ["60\uac1c\uc6d4", "4.10%", "\uc7a5\uae30 \uae30\uac04 \ud504\ub9ac\ubbf8\uc5c4 \ubc18\uc601"],
        ],
        [40, 40, 110]
    )

    p.sub("5.3", "\uae08\ub9ac \uad6c\uc131\uc694\uc18c \ubd84\ud574")
    p.formula([
        "r_final = r_base + s_FTP + s_credit + s_opex + s_margin + adj_strategy + adj_collateral",
        "",
        "s_credit = s_EL + s_UL = PD \u00d7 LGD + (PD \u00d7 LGD \u00d7 0.5 \u00d7 r_hurdle)",
    ])
    p.tbl(
        ["\uad6c\uc131\uc694\uc18c", "\uac12", "\uc124\uba85"],
        [
            ["r_base", "3.5%", "\uae30\uc900\uae08\ub9ac"],
            ["s_FTP", "3.2~4.1%", "\ud14c\ub108\ubcc4 FTP"],
            ["s_credit", "PD\u00d7LGD\u00d71.5", "\uc2e0\uc6a9\uc2a4\ud504\ub808\ub4dc"],
            ["s_opex", "0.2%", "\uc6b4\uc601\ube44 \uc2a4\ud504\ub808\ub4dc"],
            ["s_margin", "1.0%", "\ubaa9\ud45c\ub9c8\uc9c4"],
            ["adj_strategy", "-20~+100bp", "\uc804\ub7b5\ubcc4 \uac00\uac10"],
            ["adj_collateral", "-30bp~0", "\ub2f4\ubcf4 \uc6b0\ub300"],
        ],
        [40, 40, 110]
    )

    # ══════════════════════════════════════
    # 6. EWS
    # ══════════════════════════════════════
    p.add_page()
    p.sec("6", "\uc870\uae30\uacbd\ubcf4\uc2dc\uc2a4\ud15c (EWS)")

    p.sub("6.1", "5\ucc44\ub110 \uc120\ud589\uc9c0\ud45c \uccb4\uacc4")
    p.txt(
        "EWS\ub294 \ucc44\ubb34\uc790\uc758 \uc2e0\uc6a9\uc545\ud654\ub97c \uc0ac\uc804\uc5d0 \ud0d0\uc9c0\ud558\uae30 \uc704\ud55c \ub2e4\ucc44\ub110 \uc120\ud589\uc9c0\ud45c \uae30\ubc18 \uccb4\uacc4\uc774\ub2e4. "
        "\uc804\ud1b5\uc801\uc778 \uc7ac\ubb34\ube44\uc728 \ubd84\uc11d\uc744 \ub118\uc5b4 5\uac1c\uc758 \uc120\ud589\uc131 \ub370\uc774\ud130 \ucc44\ub110\uc744 \ud1b5\ud569\ud55c\ub2e4."
    )
    p.tbl(
        ["\ucc44\ub110", "\ub370\uc774\ud130 \uc18c\uc2a4", "\uc120\ud589\uc131", "\uc774\ub860\uc801 \uadfc\uac70"],
        [
            ["\uac70\ub798\ud589\ud0dc", "\uc790\ud589 \uc785\ucd9c\uae08\xb7\uacb0\uc81c", "3-6\uac1c\uc6d4", "\uc720\ub3d9\uc131 \uc545\ud654 \uc120\ud589 \uc2e0\ud638"],
            ["\uacf5\uc801\uc815\ubcf4", "\uc138\uae08\uccb4\ub0a9\xb7\uac00\uc555\ub958\xb7\uac10\uc0ac\uc758\uacac", "1-3\uac1c\uc6d4", "\ubc95\uc801\xb7\uc7ac\ubb34\uc801 \uc704\uae30 \uc2e0\ud638"],
            ["\uc2dc\uc7a5\uc2e0\ud638", "\uc8fc\uac00\xb7CDS\xb7DD (\uc0c1\uc7a5)", "\uc989\uc2dc-1\uac1c\uc6d4", "Merton \uad6c\uc870\ubaa8\ud615"],
            ["\ub274\uc2a4\uac10\uc131", "NLP \uac10\uc131\ubd84\uc11d", "1-3\uac1c\uc6d4", "\uc2dc\uc7a5\uc2ec\ub9ac \ubc18\uc601"],
            ["\uacf5\uae09\ub9dd", "\uac70\ub798\ucc98 \ub9ac\uc2a4\ud06c \uc804\uc774", "3-6\uac1c\uc6d4", "\uc5f0\uc1c4\ubd80\ub3c4 \uc774\ub860"],
        ],
        [30, 55, 30, 75]
    )

    p.sub("6.2", "\ucc44\ub110\ubcc4 \uc810\uc218 \uc0b0\ucd9c")
    p.subsub("\uac70\ub798\ud589\ud0dc \uc810\uc218 (0-100)")
    p.formula([
        "S_txn = 100 - (U_limit \u00d7 40 + D_payment \u00d7 0.5 + R_outflow \u00d7 30 + N_overdraft \u00d7 5)",
        "",
        "  U_limit    : \ud55c\ub3c4\uc18c\uc9c4\uc728 (0~1)",
        "  D_payment  : \uacb0\uc81c\uc9c0\uc5f0\uc77c\uc218",
        "  R_outflow  : \uc608\uae08\uc720\ucd9c\ub960 (0~1)",
        "  N_overdraft: \ub2f9\uc88c\ubd80\ub3c4 \ud69f\uc218",
    ])
    p.subsub("\uc2dc\uc7a5\uc2e0\ud638 \uc810\uc218 (0-100, \uc0c1\uc7a5\uae30\uc5c5)")
    p.formula([
        "S_mkt = DD \u00d7 15 + max(0, 50 - S_CDS \u00d7 0.1) - PD_implied \u00d7 100",
    ])
    p.subsub("\uacf5\uae09\ub9dd \uc804\uc774 \ub9ac\uc2a4\ud06c")
    p.formula([
        "Chain_Default_Risk = \u03a3(Partner_PD_i \u00d7 Dependency_Ratio_i)",
        "",
        "Dependency_Ratio = (Transaction_Share \u00d7 Substitution_Difficulty)",
        "                   / Trade_Diversification_Index",
    ])

    p.sub("6.3", "\uc885\ud569\uc810\uc218 \uc0b0\ucd9c")
    p.subsub("\uc0c1\uc7a5\uae30\uc5c5")
    p.formula([
        "S = 0.25\u00d7S_txn + 0.15\u00d7S_pub + 0.15\u00d7S_mkt + 0.15\u00d7S_news + 0.15\u00d7S_supply + 0.15\u00d7S_fin",
    ])
    p.subsub("\ube44\uc0c1\uc7a5\uae30\uc5c5")
    p.formula([
        "S = 0.30\u00d7S_txn + 0.20\u00d7S_pub + 0.20\u00d7S_news + 0.15\u00d7S_supply + 0.15\u00d7S_fin",
    ])
    p.tbl(
        ["\ub4f1\uae09", "\uc810\uc218 \ubc94\uc704", "\uad00\ub9ac \uc870\uce58"],
        [
            ["NORMAL", "\u2265 75", "\uc815\uae30 \ubaa8\ub2c8\ud130\ub9c1"],
            ["WATCH", "55 \u2264 S < 75", "\uad00\ucc30 \ub300\uc0c1, \ubaa8\ub2c8\ud130\ub9c1 \uac15\ud654"],
            ["WARNING", "35 \u2264 S < 55", "\uc5ec\uc2e0\uad00\ub9ac \ub2f4\ub2f9 \uc9c0\uc815, \ud55c\ub3c4 \ub3d9\uacb0"],
            ["CRITICAL", "< 35", "\uc5ec\uc2e0\ud68c\uc218 \uac80\ud1a0, Workout \uc774\uad00"],
        ],
        [35, 35, 120]
    )

    # ══════════════════════════════════════
    # 7. 스트레스 테스트
    # ══════════════════════════════════════
    p.add_page()
    p.sec("7", "\uc2a4\ud2b8\ub808\uc2a4 \ud14c\uc2a4\ud2b8")
    p.txt(
        "\uc2a4\ud2b8\ub808\uc2a4 \ud14c\uc2a4\ud2b8\ub294 \uac00\uc0c1\uc758 \uc704\uae30 \uc0c1\ud669\uc5d0\uc11c \ud3ec\ud2b8\ud3f4\ub9ac\uc624\uc758 \uc190\uc2e4\uacfc \uc790\ubcf8 \uc801\uc815\uc131\uc744 \ud3c9\uac00\ud55c\ub2e4."
    )
    p.sub("7.1", "\uc2dc\ub098\ub9ac\uc624 \uc124\uacc4")
    p.tbl(
        ["\uac15\ub3c4", "GDP", "\uc2e4\uc5c5\ub960", "\uae08\ub9ac", "\uc8fc\ud0dd", "\uc8fc\uac00", "\ud658\uc728"],
        [
            ["BASELINE", "+2.5%", "3.5%", "0", "+3%", "+5%", "0"],
            ["MILD", "+0.5%", "4.5%", "+50bp", "-5%", "-10%", "+5%"],
            ["MODERATE", "-1.0%", "6.0%", "+100bp", "-15%", "-25%", "+10%"],
            ["SEVERE", "-3.0%", "8.0%", "+150bp", "-30%", "-40%", "+15%"],
            ["EXTREME", "-5.0%", "10.0%", "+200bp", "-40%", "-50%", "+20%"],
        ],
        [30, 25, 25, 25, 25, 30, 30]
    )

    p.sub("7.2", "\ucda9\uaca9 \uc801\uc6a9 \uc0b0\uc2dd")
    p.formula([
        "PD_stressed = min(PD_base \u00d7 F_PD \u00d7 S_industry, 0.30)",
        "LGD_stressed = min(LGD_base \u00d7 (1 + (F-1) \u00d7 0.3), 0.70)",
        "RWA_stressed = RWA_base \u00d7 (1 + (F-1) \u00d7 0.2)",
        "",
        "  F: \uc2dc\ub098\ub9ac\uc624\ubcc4 \ucda9\uaca9\uacc4\uc218 (BASE:1.0 ~ EXTREME:3.5)",
        "  S_industry: \uc0b0\uc5c5\ubcc4 \ubbfc\uac10\ub3c4 \uacc4\uc218",
    ])
    p.formula([
        "\uc790\ubcf8\ubd80\uc871\uc561 = max(0, 0.08 \u00d7 RWA_stressed - Total_Capital)",
        "BIS_stressed = Total_Capital / RWA_stressed",
    ])

    # ══════════════════════════════════════
    # 8. 포트폴리오 최적화
    # ══════════════════════════════════════
    p.sec("8", "\ud3ec\ud2b8\ud3f4\ub9ac\uc624 \ucd5c\uc801\ud654")
    p.sub("8.1", "\ubaa9\uc801\ud568\uc218 - RAROC \uadf9\ub300\ud654")
    p.formula([
        "max \u03a3(w_i \u00d7 RAROC_i)",
        "",
        "\uc81c\uc57d: \u03a3w_i = 1,  BIS \u2265 11%,  HHI \u2264 0.25,  max(w_i) \u2264 10%,  w_i \u2265 0",
    ])
    p.sub("8.2", "\uc9d1\uc911\ub3c4 \uce21\uc815 (HHI)")
    p.formula([
        "HHI = \u03a3(Exposure_i / Total_Exposure)\u00b2",
        "",
        "HHI < 0.15 : \ubd84\uc0b0\ud654 \uc591\ud638",
        "0.15 \u2264 HHI < 0.25 : \uc911\uac04 \uc9d1\uc911",
        "HHI \u2265 0.25 : \uace0\ub3c4 \uc9d1\uc911 (\uaddc\uc81c \uc6b0\ub824)",
    ])
    p.sub("8.3", "\ud3ec\ud2b8\ud3f4\ub9ac\uc624 \ub9ac\uc2a4\ud06c")
    p.formula([
        "\u03c3\u00b2_p = \u03a3\u03a3(w_i \u00d7 w_j \u00d7 \u03c1_ij \u00d7 UL_i \u00d7 UL_j)",
        "",
        "Credit Sharpe = (RAROC_portfolio - r_hurdle) / \u03c3_UL",
    ])

    # ══════════════════════════════════════
    # 9. ALM
    # ══════════════════════════════════════
    p.add_page()
    p.sec("9", "ALM \uae08\ub9ac\ub9ac\uc2a4\ud06c \uad00\ub9ac")
    p.sub("9.1", "\uae08\ub9ac\uac31 \ubd84\uc11d (Interest Rate Gap)")
    p.formula([
        "Gap_i = Floating_Assets_i - Floating_Liabilities_i",
        "Cumulative_Gap = \u03a3(Gap_i) from bucket 0 to i",
        "",
        "\ubc84\ucf13: 1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y, 5Y+",
    ])
    p.sub("9.2", "\ub4c0\ub808\uc774\uc158 \uac31 (Duration Gap)")
    p.formula([
        "D_gap = D_A - (L/A) \u00d7 D_L",
        "",
        "  D_A : \uc790\uc0b0 \ub4c0\ub808\uc774\uc158",
        "  D_L : \ubd80\ucc44 \ub4c0\ub808\uc774\uc158",
        "  L/A : \ubd80\ucc44/\uc790\uc0b0 \ube44\uc728",
    ])
    p.sub("9.3", "NIM \ubc0f EVE \ubbfc\uac10\ub3c4")
    p.formula([
        "\u0394NIM = Gap \u00d7 \u0394r / A_total",
        "\u0394EVE = -D_gap \u00d7 A \u00d7 \u0394r",
        "",
        "\ud5e4\uc9c0 \ud6a8\uacfc\uc131 \ubaa9\ud45c: \u2265 80%",
    ])

    # ══════════════════════════════════════
    # 10. ESG
    # ══════════════════════════════════════
    p.sec("10", "ESG \ub9ac\uc2a4\ud06c \ud1b5\ud569")
    p.formula([
        "S_ESG = 0.35 \u00d7 S_E + 0.30 \u00d7 S_S + 0.35 \u00d7 S_G",
        "",
        "PD_adjusted = PD_base \u00d7 (1 + adj_ESG)",
    ])
    p.tbl(
        ["ESG \ub4f1\uae09", "\uc810\uc218", "PD \uac00\uac10", "\uae08\ub9ac \uac00\uac10"],
        [
            ["A", "\u2265 80", "-0.2%p", "-10bp"],
            ["B", "65-79", "-0.1%p", "-5bp"],
            ["C", "50-64", "0", "0"],
            ["D", "35-49", "+0.2%p", "+10bp"],
            ["E", "< 35", "+0.5%p", "+25bp"],
        ],
        [35, 40, 55, 60]
    )
    p.txt(
        "\ub179\uc0c9\uae08\uc735 \ub300\ucd9c\uc5d0 \ub300\ud574\uc11c\ub294 RWA \ud560\uc778(0~15%)\uc774 \uc801\uc6a9\ub41c\ub2e4: "
        "Green_RWA = Base_RWA \u00d7 (1 - RWA_Discount%)"
    )

    # ══════════════════════════════════════
    # 11. 모형 검증
    # ══════════════════════════════════════
    p.add_page()
    p.sec("11", "\ubaa8\ud615 \uac80\uc99d")

    p.sub("11.1", "PD \ubc31\ud14c\uc2a4\ud2b8 - \uc774\ud56d\uac80\uc815")
    p.formula([
        "H\u2080: Actual_PD = Predicted_PD",
        "X ~ Binomial(n, PD_predicted)",
        "p-value = P(X \u2265 k | n, PD_predicted)",
        "",
        "p-value < 0.01 \u2192 FAIL",
        "0.01 \u2264 p < 0.05 \u2192 WARNING",
        "p-value \u2265 0.05 \u2192 PASS",
    ])

    p.sub("11.2", "\ubaa8\ud615 \uc131\ub2a5 \uc9c0\ud45c")
    p.tbl(
        ["\uc9c0\ud45c", "\uc124\uba85", "\uacbd\ubcf4 \uae30\uc900"],
        [
            ["Gini \uacc4\uc218", "\ud310\ubcc4\ub825 (0~1)", "Warning < 0.40, Critical < 0.35"],
            ["KS \ud1b5\uacc4\ub7c9", "Kolmogorov-Smirnov", "\ub192\uc744\uc218\ub85d \uc591\ud638"],
            ["AUROC", "ROC \uace1\uc120 \ud558 \uba74\uc801", "> 0.70"],
            ["PSI", "\ubaa8\uc9d1\ub2e8 \uc548\uc815\uc131 \uc9c0\uc218", "Warning > 0.10, Critical > 0.25"],
            ["AR Ratio", "\uc2e4\uc801/\uc608\uce21 \ube44\uc728", "Warning: <0.80 or >1.20"],
        ],
        [35, 65, 90]
    )
    p.txt("PSI \uc0b0\ucd9c\uc2dd:")
    p.formula([
        "PSI = \u03a3 (Actual_i% - Expected_i%) \u00d7 ln(Actual_i% / Expected_i%)",
    ])

    p.sub("11.3", "\ube48\ud2f0\uc9c0 \ubd84\uc11d (Vintage Analysis)")
    p.txt("\ucf54\ud638\ud2b8\ubcc4 \uc2dc\uacc4\uc5f4 \uc2e0\uc6a9\uc131\uacfc \ucd94\uc801:")
    p.formula([
        "MOB-3 \uc5f0\uccb4\uc728: 3\uac1c\uc6d4 \uc774\uc0c1 \uc5f0\uccb4 \ube44\uc728",
        "MOB-12 \ubd80\ub3c4\uc728: 12\uac1c\uc6d4 \ub0b4 \ubd80\ub3c4 \ube44\uc728 \u2248 \uc2e4\ud604 PD",
        "MOB-24 \ubd80\ub3c4\uc728: 24\uac1c\uc6d4 \ub0b4 \ubd80\ub3c4 \ube44\uc728",
        "\ub204\uc801\uc190\uc2e4\uc728: \uc2e4\ud604\ub41c \ucd1d \uc190\uc2e4 \ube44\uc728",
    ])

    p.sub("11.4", "Override \ubaa8\ub2c8\ud130\ub9c1")
    p.tbl(
        ["\uc9c0\ud45c", "\uae30\uc900"],
        [
            ["\ucd5c\ub300 \uc7ac\uc870\uc815\ub960", "15%"],
            ["\ucd5c\ub300 \uc0c1\ud5a5 \ube44\uc728", "50%"],
            ["Type I \uc624\ub958 (\uc0c1\ud5a5\u2192\ubd80\ub3c4)", "\u2264 5%"],
            ["Type II \uc624\ub958 (\ud558\ud5a5\u2192\uc815\uc0c1)", "\u2264 20%"],
            ["\ucd5c\uc18c \uc815\ud655\ub3c4", "\u2265 70%"],
        ],
        [95, 95]
    )

    # ══════════════════════════════════════
    # 12. 담보 및 Workout
    # ══════════════════════════════════════
    p.add_page()
    p.sec("12", "\ub2f4\ubcf4 \ubc0f Workout")
    p.sub("12.1", "LTV (Loan-to-Value) \uad00\ub9ac")
    p.formula([
        "LTV = Outstanding / Collateral_Value \u00d7 100%",
        "",
        "\ub3d9\uc801 LTV: New_LTV = Loan / (Original_Value \u00d7 (1 + Price_Change%))",
    ])
    p.tbl(
        ["LTV \ubc94\uc704", "\uc0c1\ud0dc", "\uc870\uce58"],
        [
            ["\u226460%", "NORMAL", "\uc815\uae30 \ubaa8\ub2c8\ud130\ub9c1"],
            ["60-70%", "CAUTION", "\uc6d4\ubcc4 \uac15\ud654 \ubaa8\ub2c8\ud130\ub9c1"],
            ["70-80%", "WARNING", "\ucd94\uac00 \ub2f4\ubcf4 \uac80\ud1a0"],
            [">80%", "CRITICAL", "\ub2f4\ubcf4 \uc694\uad6c \ub610\ub294 \uc5ec\uc2e0 \ucd95\uc18c"],
        ],
        [40, 40, 110]
    )

    p.sub("12.2", "\ub2f4\ubcf4 \uc778\uc815\ube44\uc728")
    p.tbl(
        ["\ub2f4\ubcf4\uc720\ud615", "\uc138\ubd80\uc720\ud615", "\uc778\uc815\ube44\uc728"],
        [
            ["\ubd80\ub3d9\uc0b0", "\uc544\ud30c\ud2b8/\uc624\ud53c\uc2a4/\uc0c1\uac00/\ud1a0\uc9c0/\uacf5\uc7a5", "45~80%"],
            ["\uc608\uae08", "\uc815\uae30\uc608\uae08/\uc801\uae08/CD", "90~100%"],
            ["\uc720\uac00\uc99d\uad8c", "\uc0c1\uc7a5\uc8fc\uc2dd/\ucc44\uad8c/\ud3b8\ub4dc", "50~90%"],
            ["\ub3d9\uc0b0", "\uae30\uacc4/\uc7ac\uace0/\ucc28\ub7c9/\uc120\ubc15", "30~65%"],
            ["\ubcf4\uc99d", "\uc2e0\ubcf4/\uae30\ubcf4/\ubcf4\ud5d8", "80~95%"],
            ["\ub9e4\ucd9c\ucc44\uad8c", "\ub9e4\ucd9c\ucc44\uad8c/\uc5b4\uc74c", "60~80%"],
            ["IP\uad8c", "\ud2b9\ud5c8\uad8c/\uc0c1\ud45c\uad8c", "15~40%"],
        ],
        [40, 75, 75]
    )

    p.sub("12.3", "Workout \ud68c\uc218 \uc2dc\ub098\ub9ac\uc624 NPV")
    p.formula([
        "NPV = \u03a3(Recovery_CF_t / (1+r)^t) - Legal_Cost - Admin_Cost",
        "",
        "  r = \ud560\uc778\uc728 (8%)",
    ])
    p.tbl(
        ["\uc804\ub7b5", "\ud68c\uc218\uc728", "\uae30\uac04", "\uc124\uba85"],
        [
            ["\uc815\uc0c1\ud654", "85%", "24\uac1c\uc6d4", "\uc790\uccb4 \uc815\uc0c1\ud654 \uc9c0\uc6d0"],
            ["\ucc44\ubb34\uc870\uc815", "65%", "36\uac1c\uc6d4", "\uc6d0\uae08/\uae08\ub9ac \uc870\uc815"],
            ["\uc790\uc0b0\ub9e4\uac01", "50%", "12\uac1c\uc6d4", "\ub2f4\ubcf4 \ucc98\ubd84"],
            ["\ubc95\uc801\ud68c\uc218", "35%", "48\uac1c\uc6d4", "\ubc95\uc801 \uc808\ucc28"],
        ],
        [40, 30, 30, 90]
    )

    # ══════════════════════════════════════
    # 13. 시스템 상수 및 가정치
    # ══════════════════════════════════════
    p.add_page()
    p.sec("13", "\uc2dc\uc2a4\ud15c \uc0c1\uc218 \ubc0f \uac00\uc815\uce58")

    p.sub("13.1", "\ube44\uc6a9\ub960 \uc0c1\uc218")
    p.tbl(
        ["\uc0c1\uc218", "\uac12", "\uc124\uba85", "\uc801\uc6a9 \uc704\uce58"],
        [
            ["FUNDING_RATE", "4.3%", "\uc870\ub2ec\ube44\uc6a9\ub960", "region_helper.py"],
            ["OPEX_RATE", "0.5%", "\uc6b4\uc601\ube44\uc728", "calculations.py"],
            ["COST_RATE", "4.8%", "\ucd1d\ube44\uc6a9\ub960 (4.3%+0.5%)", "dashboard.py"],
            ["EC_RATIO", "10.5%", "\uacbd\uc81c\uc801 \uc790\ubcf8\ube44\uc728", "\uc804 \ubaa8\ub4c8"],
            ["HURDLE_RATE", "12%", "\uc790\uae30\uc790\ubcf8\ube44\uc6a9", "dashboard.py"],
        ],
        [40, 20, 75, 55]
    )

    p.sub("13.2", "\uc790\ubcf8\ube44\uc728 \uccb4\uacc4")
    p.tbl(
        ["\uc9c0\ud45c", "\uaddc\uc81c \ucd5c\uc18c", "\ub0b4\ubd80 \ubaa9\ud45c"],
        [
            ["BIS \ube44\uc728", "10.5%", "13.0%"],
            ["CET1 \ube44\uc728", "7.0%", "10.0%"],
            ["Tier1 \ube44\uc728", "8.5%", "11.0%"],
            ["\ub808\ubc84\ub9ac\uc9c0 \ube44\uc728", "3.0%", "5.0%"],
        ],
        [60, 65, 65]
    )

    p.sub("13.3", "\ud3ec\ud2b8\ud3f4\ub9ac\uc624 RAROC \uc2e4\uce21\uac12 (2026-02)")
    p.tbl(
        ["\uc9c0\uc5ed", "RAROC", "\ube44\uace0"],
        [
            ["\uc804\uccb4", "11.09%", "\ud3ec\ud2b8\ud3f4\ub9ac\uc624 \uac00\uc911\ud3c9\uade0"],
            ["\uc218\ub3c4\uad8c (CAPITAL)", "14.13%", "\uace0\ub4f1\uae09 \ube44\uc911 \ub192\uc74c"],
            ["\ub300\uad6c\uacbd\ubd81 (DAEGU_GB)", "10.96%", "\uc911\uac04 \uc218\uc900"],
            ["\ubd80\uc0b0\uacbd\ub0a8 (BUSAN_GN)", "8.34%", "\ud5c8\ub4e4\ub808\uc774\ud2b8(12%) \ud558\ud68c"],
        ],
        [55, 30, 105]
    )

    # ══════════════════════════════════════
    # 14. 한계 및 향후 과제
    # ══════════════════════════════════════
    p.add_page()
    p.sec("14", "\ud55c\uacc4 \ubc0f \ud5a5\ud6c4 \uacfc\uc81c")

    p.sub("14.1", "\ubaa8\ud615 \ud55c\uacc4")
    for l in [
        "\ub2e8\uc77c\uc694\uc778 \ubaa8\ud615(Single-Factor Model): \uc790\uc0b0\uc0c1\uad00 \uad6c\uc870\uac00 \ub2e8\uc77c \uccb4\uacc4\uc694\uc778\uc5d0\ub9cc \uc758\uc874. \uc0b0\uc5c5\uac04\xb7\uc9c0\uc5ed\uac04 \uc0c1\uc774\ud55c \uc0c1\uad00 \uad6c\uc870\ub97c \uc644\uc804\ud788 \ud3ec\ucc29\ud558\uc9c0 \ubabb\ud568.",
        "\uc0c1\uad00\uacc4\uc218\uc758 \uc815\uc801 \uac00\uc815: \uc790\uc0b0\uc0c1\uad00\uacc4\uc218 R\uc774 PD\ub9cc\uc758 \ud568\uc218. \uc704\uae30 \uc2dc \uc0c1\uad00\uad00\uacc4 \uae09\ub4f1(correlation smile) \ud604\uc0c1 \ubbf8\ubc18\uc601.",
        "LGD\uc758 \uacbd\uae30\uc21c\ud658 \ube44\uc758\uc874: LGD\uac00 \uace0\uc815\uac12. \uc2e4\uc81c\ub85c\ub294 \uacbd\uae30 \ud558\uac15\uae30 LGD \uc0c1\uc2b9(downturn LGD) \uacbd\ud5a5 \uc874\uc7ac.",
        "FTP \ucee4\ube0c\uc758 \uc815\uc801 \uac00\uc815: FTP \uae08\ub9ac \uace0\uc815. \uc2dc\uc7a5\uae08\ub9ac \ubcc0\ub3d9\uc5d0 \ub530\ub978 \ub3d9\uc801 \uc870\uc815 \ubbf8\ubc18\uc601.",
        "EWS \uac00\uc911\uce58\uc758 \uc804\ubb38\uac00 \ud310\ub2e8 \uc758\uc874: 5\ucc44\ub110 \uac00\uc911\uce58\uac00 \ud1b5\uacc4\uc801 \ucd5c\uc801\ud654\uac00 \uc544\ub2cc \uc804\ubb38\uac00 \ud310\ub2e8 \uae30\ubc18.",
        "\ud3ec\ud2b8\ud3f4\ub9ac\uc624 \ucd5c\uc801\ud654\uc758 \uc120\ud615 \uac00\uc815: \ube44\uc120\ud615 \ub9ac\uc2a4\ud06c \ud2b9\uc131(\uaf2c\ub9ac \ub9ac\uc2a4\ud06c, \uadf9\ub2e8 \uc190\uc2e4) \ucda9\ubd84\ud788 \ubbf8\ubc18\uc601.",
    ]:
        p.bullet(l)

    p.sub("14.2", "\ud5a5\ud6c4 \uacfc\uc81c")
    for f in [
        "\ub2e4\uc694\uc778 \ubaa8\ud615(Multi-Factor Model) \ub3c4\uc785: \uc0b0\uc5c5\ubcc4\xb7\uc9c0\uc5ed\ubcc4 \uc0c1\uad00 \uad6c\uc870 \uc138\ubd84\ud654",
        "\uae30\uacc4\ud559\uc2b5 \uae30\ubc18 EWS: \ucc44\ub110 \uac00\uc911\uce58 \ub370\uc774\ud130 \uae30\ubc18 \uc790\ub3d9 \ubcf4\uc815 (LASSO, Random Forest \ub4f1)",
        "\ub3d9\uc801 FTP: \uc2e4\uc2dc\uac04 \uc2dc\uc7a5\uae08\ub9ac \uc5f0\ub3d9 FTP \ucee4\ube0c \uc790\ub3d9 \uc5c5\ub370\uc774\ud2b8",
        "Downturn LGD \ubaa8\ud615: PIT LGD \ucd94\uc815\uc744 \uc704\ud55c \uacbd\uae30\uc21c\ud658 \uc870\uc815 \ubaa8\ud615",
        "CVA/DVA \ud1b5\ud569: \uac70\ub798\uc0c1\ub300\ubc29 \uc2e0\uc6a9\ub9ac\uc2a4\ud06c \uac00\uce58\uc870\uc815 \ubc18\uc601",
        "IFRS 9 \ud1b5\ud569: \uae30\ub300\uc2e0\uc6a9\uc190\uc2e4(ECL) \uc0b0\ucd9c\uacfc 3-Stage \ubd84\ub958 \uccb4\uacc4 \uc5f0\ub3d9",
    ]:
        p.bullet(f)

    # ── References ──
    p.ln(8)
    p.sub("", "\ucc38\uace0\ubb38\ud5cc")
    refs = [
        '[1] BCBS (2006). "International Convergence of Capital Measurement and Capital Standards." Basel Committee.',
        '[2] BCBS (2017). "Basel III: Finalising Post-Crisis Reforms." Basel Committee.',
        '[3] Vasicek, O. (2002). "The Distribution of Loan Portfolio Value." Risk, 15(12), 160-162.',
        '[4] Merton, R.C. (1974). "On the Pricing of Corporate Debt." Journal of Finance, 29(2), 449-470.',
        '[5] Gordy, M.B. (2003). "A Risk-Factor Model Foundation for Ratings-Based Bank Capital Rules." JFI, 12, 199-232.',
        '[6] Crosbie, P. & Bohn, J. (2003). "Modeling Default Risk." Moody\'s KMV.',
        '[7] Altman, E.I. (1968). "Financial Ratios, Discriminant Analysis and Corporate Bankruptcy." JoF, 23(4).',
        '[8] Markowitz, H. (1952). "Portfolio Selection." Journal of Finance, 7(1), 77-91.',
        '[9] J.P. Morgan (1996). "RiskMetrics - Technical Document." 4th Edition.',
    ]
    p.set_font("body", "", 9)
    for ref in refs:
        p.set_x(15)
        p.multi_cell(175, 5, ref)
        p.ln(1)

    out = os.path.join(os.path.dirname(__file__), "CLMS_Technical_Paper.pdf")
    p.output(out)
    print(f"PDF saved: {out} ({p.page_no()} pages)")


if __name__ == "__main__":
    build()
