"""
업무보고서 PDF 생성 (fpdf2)
============================
/api/governance/report 의 집계 dict 를 감독당국 업무보고서 서식에 준하는
A4 문서로 렌더한다. 한글은 리포에 커밋된 Pretendard 정적 TTF
(backend/assets/fonts/, PretendardVariable 에서 wght 400/700 인스턴스 추출,
SIL OFL 1.1)를 임베드해 배포 환경(리눅스)에서도 동일하게 출력된다.
"""
from pathlib import Path

from fpdf import FPDF

FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"

MINT = (0, 137, 123)          # iM 민트 (#00897B 계열, 인쇄 대비 확보)
GRAY_LINE = (210, 214, 218)
GRAY_TEXT = (110, 116, 122)
FILL_HEAD = (238, 246, 244)   # 표 머리행 배경
FILL_STRIPE = (248, 250, 250)

EOK = 1e8


def _eok(v: float, digits: int = 0) -> str:
    """원 → 억원 문자열 (표 컬럼용 - 헤더에 단위 명시)"""
    return f"{v / EOK:,.{digits}f}"


def _amt(v: float) -> str:
    """원 → 단위 포함 금액 문자열. 1조 이상은 조 단위 (요약 지표용)"""
    if abs(v) >= 1e12:
        cho = v / 1e12
        return f"{cho:,.1f} 조원" if abs(cho) >= 10 else f"{cho:,.2f} 조원"
    return f"{v / EOK:,.0f} 억원"


class ReportPDF(FPDF):
    def __init__(self):
        super().__init__("P", "mm", "A4")
        self.set_auto_page_break(auto=True, margin=18)
        self.add_font("PD", "", str(FONT_DIR / "Pretendard-Regular.ttf"))
        self.add_font("PD", "B", str(FONT_DIR / "Pretendard-Bold.ttf"))
        self.doc_title = "여신 업무보고서"

    def header(self):
        if self.page_no() > 1:
            self.set_font("PD", "", 8)
            self.set_text_color(*GRAY_TEXT)
            self.cell(0, 5, f"iM뱅크 CLMS · {self.doc_title}", align="L")
            self.cell(0, 5, f"- {self.page_no()} -", align="R",
                      new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(*GRAY_LINE)
            self.line(10, 13, 200, 13)
            self.ln(4)
            self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-14)
        self.set_font("PD", "", 7)
        self.set_text_color(*GRAY_TEXT)
        self.cell(0, 4, "본 보고서는 모의 데이터 기반 PoC 산출물로, 의사결정·보고·공시에 인용할 수 없습니다.",
                  align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 4, "© 2026 yalkongs · iM뱅크 CLMS PoC", align="C")
        self.set_text_color(0, 0, 0)

    # ── 구성 요소 ────────────────────────────────────────────
    def section_title(self, title: str):
        # 제목만 페이지 끝에 남는 고아를 막는다 - 첫 내용 행까지 들어갈 여백 확보
        if self.get_y() > 235:
            self.add_page()
        self.ln(2)
        self.set_fill_color(*MINT)
        self.rect(10, self.get_y() + 1, 1.6, 5, "F")
        self.set_x(14)
        self.set_font("PD", "B", 11)
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def table(self, headers, widths, aligns, rows, bold_last=False):
        self.set_draw_color(*GRAY_LINE)
        self.set_line_width(0.2)
        # 머리행
        self.set_font("PD", "B", 8.5)
        self.set_fill_color(*FILL_HEAD)
        for h, w, a in zip(headers, widths, aligns):
            self.cell(w, 6.5, h, border="TB", align=a, fill=True)
        self.ln()
        # 본문행
        for i, row in enumerate(rows):
            is_last = i == len(rows) - 1
            self.set_font("PD", "B" if (bold_last and is_last) else "", 8.5)
            if i % 2 == 1 and not (bold_last and is_last):
                self.set_fill_color(*FILL_STRIPE)
                fill = True
            else:
                fill = False
            border = "B" if not is_last else "TB" if bold_last else "B"
            for v, w, a in zip(row, widths, aligns):
                self.cell(w, 6, str(v), border=border, align=a, fill=fill)
            self.ln()
        self.ln(2)

    def kv_grid(self, items, cols=3):
        """(label, value) 목록을 격자로 - 요약 지표용"""
        w = 190 / cols
        for i in range(0, len(items), cols):
            if self.get_y() > 252:      # 라벨-값 쌍이 페이지 경계에서 갈라지지 않게
                self.add_page()
            chunk = items[i:i + cols]
            self.set_font("PD", "", 8)
            self.set_text_color(*GRAY_TEXT)
            for label, _ in chunk:
                self.cell(w, 4.5, label, align="L")
            self.ln()
            self.set_font("PD", "B", 11)
            self.set_text_color(20, 24, 28)
            for _, value in chunk:
                self.cell(w, 6.5, value, align="L")
            self.ln(8)
        self.set_text_color(0, 0, 0)


def build_report_pdf(data: dict) -> bytes:
    s = data["sections"]
    pdf = ReportPDF()
    pdf.doc_title = data["report_title"]
    pdf.add_page()

    # ── 표지부: 제목 + 문서번호 + 결재란
    pdf.set_font("PD", "", 8.5)
    pdf.set_text_color(*GRAY_TEXT)
    pdf.cell(95, 5, f"문서번호 {data['doc_no']}", align="L")
    # 결재란 (담당/검토/승인)
    x0 = pdf.get_x() + 35
    y0 = pdf.get_y()
    pdf.set_draw_color(*GRAY_LINE)
    for j, role in enumerate(["담당", "검토", "승인"]):
        pdf.set_xy(x0 + j * 20, y0)
        pdf.set_font("PD", "", 7.5)
        pdf.cell(20, 5, role, border=1, align="C")
        pdf.set_xy(x0 + j * 20, y0 + 5)
        pdf.cell(20, 13, "", border=1)
    pdf.set_xy(10, y0 + 20)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("PD", "B", 20)
    pdf.cell(0, 11, data["report_title"], align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("PD", "", 10)
    pdf.set_text_color(*GRAY_TEXT)
    pdf.cell(0, 6, f"{data['period']} · 기준일 {data['base_date']} · iM뱅크 CLMS",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.set_draw_color(*MINT)
    pdf.set_line_width(0.6)
    pdf.line(10, pdf.get_y() + 2, 200, pdf.get_y() + 2)
    pdf.ln(7)

    # ── 총괄
    sm = s["summary"]
    pdf.section_title("총괄")
    pdf.kv_grid([
        ("총여신 잔액", _amt(sm['total_outstanding'])),
        ("여신 건수 / 차주 수", f"{sm['facility_count']:,} 건 / {sm['borrower_count']:,} 개사"),
        ("당년 신규취급(YTD)", f"{_amt(sm['new_amount'])} ({sm['new_count']}건)"),
        ("고정이하여신비율(NPL)", f"{sm['npl_ratio']:.2f} %"),
        ("연체율(30일+)", f"{sm['delinquency_rate']:.3f} %"),
        ("BIS 자기자본비율", f"{sm['bis_ratio']:.2f} %"),
    ], cols=3)

    # ── 1. 자산건전성
    c = s["classification"]
    pdf.section_title(c["title"])
    rows = [
        [r["grade"], f"{r['count']:,}", _eok(r["exposure"]), f"{r['share']:.2f}%",
         ("+" if r["change"] > 0 else "") + _eok(r["change"], 1) if r["change"] else "-",
         _eok(r["required_provision"], 1)]
        for r in c["rows"]
    ]
    rows.append(["합계", f"{sum(r['count'] for r in c['rows']):,}", _eok(c["total_exposure"]),
                 "100.00%", "", _eok(sum(r["required_provision"] for r in c["rows"]), 1)])
    pdf.table(
        ["분류", "건수", "잔액(억원)", "비중", "증감(억원)", "필요충당금(억원)"],
        [30, 22, 36, 24, 36, 42],
        ["L", "R", "R", "R", "R", "R"],
        rows, bold_last=True,
    )
    pdf.set_font("PD", "", 8.5)
    prev = f" (직전 분류 {c['prev_date']} 대비)" if c.get("prev_date") else ""
    pdf.cell(0, 5, f"※ 고정이하여신 {_eok(c['npl_exposure'])} 억원, NPL 비율 {c['npl_ratio']:.2f}%{prev}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    # ── 2. 연체
    d = s["delinquency"]
    pdf.section_title(d["title"])
    pdf.table(
        ["연체 구간(DPD)", "건수", "잔액(억원)"],
        [60, 40, 90],
        ["L", "R", "R"],
        [[b["label"], f"{b['count']:,}", _eok(b["amount"], 1)] for b in d["buckets"]],
    )
    pdf.set_font("PD", "", 8.5)
    pdf.cell(0, 5,
             f"※ 연체율 30일+ {d['delinquency_rate']:.3f}% · 90일+ {d['delinquency_rate_3m']:.3f}% · "
             f"워크아웃 이관임박(DPD 75~89) {d['transfer_imminent_count']}건 {_eok(d['transfer_imminent_amount'], 1)}억원",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    # ── 3. 충당금
    p = s["provision"]
    pdf.section_title(p["title"])
    stage_names = {1: "Stage 1 (12개월 ECL)", 2: "Stage 2 (전 생애 ECL)", 3: "Stage 3 (신용손상)"}
    pdf.table(
        ["구분", "건수", "EAD(억원)", "ECL(억원)"],
        [70, 30, 45, 45],
        ["L", "R", "R", "R"],
        [[stage_names.get(st["stage"], f"Stage {st['stage']}"), f"{st['count']:,}",
          _eok(st["ead"]), _eok(st["ecl"], 1)] for st in p["stages"]],
    )
    pdf.set_font("PD", "", 8.5)
    pdf.cell(0, 5,
             f"※ 감독규정 최저적립액 {_eok(p['regulatory_minimum'], 1)}억원 vs IFRS9 ECL {_eok(p['ifrs9_ecl'], 1)}억원 "
             f"→ 대손준비금 {_eok(p['loan_loss_reserve'], 1)}억원 · NPL 커버리지 {p['coverage_ratio']:.1f}%",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    # ── 4. 자본
    cp = s["capital"]
    pdf.section_title(cp["title"])
    chg = f" (직전 대비 {cp['bis_change']:+.2f}%p)" if cp.get("bis_change") is not None else ""
    pdf.kv_grid([
        ("BIS 비율", f"{cp['bis_ratio']:.2f} %{chg}"),
        ("Tier1 비율", f"{cp['tier1_ratio']:.2f} %"),
        ("CET1 비율", f"{cp['cet1_ratio']:.2f} %"),
        ("레버리지 비율", f"{cp['leverage_ratio']:.2f} %"),
        ("총자본", _amt(cp['total_capital'])),
        ("총 RWA", _amt(cp['total_rwa'])),
    ], cols=3)

    # ── 5. 포트폴리오
    pf_ = s["portfolio"]
    pdf.section_title(pf_["title"])
    pdf.set_font("PD", "B", 9)
    pdf.cell(0, 6, "업종별 (상위 8개)", new_x="LMARGIN", new_y="NEXT")
    pdf.table(
        ["업종", "건수", "잔액(억원)", "비중", "NPL비율"],
        [56, 24, 40, 30, 40],
        ["L", "R", "R", "R", "R"],
        [[r["name"], f"{r['count']:,}", _eok(r["exposure"]), f"{r['share']:.1f}%",
          f"{r['npl_ratio']:.2f}%"] for r in pf_["by_industry"]],
    )
    pdf.set_font("PD", "B", 9)
    pdf.cell(0, 6, "지역별 · 기업규모별", new_x="LMARGIN", new_y="NEXT")
    reg_lines = [[r["name"], _eok(r["exposure"]), f"{r['share']:.1f}%",
                  f"{r['delinquency_rate']:.3f}%"] for r in pf_["by_region"]]
    pdf.table(["지역", "잔액(억원)", "비중", "연체율"],
              [56, 44, 40, 50], ["L", "R", "R", "R"], reg_lines)
    pdf.table(["기업규모", "건수", "잔액(억원)", "비중"],
              [56, 24, 60, 50], ["L", "R", "R", "R"],
              [[r["name"], f"{r['count']:,}", _eok(r["exposure"]), f"{r['share']:.1f}%"]
               for r in pf_["by_size"]])

    # ── 6. PF
    pj = s["pf"]
    pdf.section_title(pj["title"])
    pdf.kv_grid([
        ("사업장 수", f"{pj['project_count']} 개 (브릿지 {pj['bridge_count']})"),
        ("총 익스포저", _amt(pj['exposure'])),
        ("워치리스트", f"{pj['watchlist_count']} 개"),
        ("공정-분양 괴리 경보(≥30%p)", f"{pj['gap_alert_count']} 개"),
        ("평균 사업장 자기자본비율", f"{pj['avg_equity_ratio']:.1f} %"),
        ("브릿지 익스포저", _amt(pj['bridge_exposure'])),
    ], cols=3)

    # ── 7. 포용금융
    inc = s["inclusive"]
    pdf.section_title(inc["title"])
    pdf.table(
        ["세그먼트", "건수", "잔액(억원)", "비중", "목표", "연체율"],
        [50, 24, 36, 26, 26, 28],
        ["L", "R", "R", "R", "R", "R"],
        [
            ["중신용 기업 (BBB+ 이하)", f"{inc['mid_credit']['count']:,}",
             _eok(inc["mid_credit"]["exposure"]), f"{inc['mid_credit']['share']:.1f}%",
             f"{inc['mid_credit']['target']:.0f}%", f"{inc['mid_credit']['delinquency_rate']:.3f}%"],
            ["개인사업자 (SOHO)", f"{inc['soho']['count']:,}",
             _eok(inc["soho"]["exposure"]), f"{inc['soho']['share']:.1f}%",
             f"{inc['soho']['target']:.0f}%", f"{inc['soho']['delinquency_rate']:.3f}%"],
        ],
    )

    # ── 8. 워크아웃
    w = s["workout"]
    pdf.section_title(w["title"])
    strat = " · ".join(f"{x['name']} {x['count']}" for x in w["by_strategy"]) or "-"
    pdf.kv_grid([
        ("진행 중 케이스", f"{w['active_cases']} 건"),
        ("관리 익스포저", _amt(w['active_exposure'])),
        ("회수 완료(누적)", f"{w['recovered_cases']} 건"),
        ("예상 회수액", f"{_amt(w['expected_recovery'])} ({w['expected_recovery_rate']:.1f}%)"),
        ("전략별 분포", strat),
        ("", ""),
    ], cols=3)

    # ── 9. EWS + 10. 내부통제
    e = s["ews"]
    ic = s["internal_control"]
    pdf.section_title(e["title"])
    pdf.kv_grid([
        ("미해결 경보", f"{e['open_alerts']:,} 건"),
        ("고위험(HIGH/CRITICAL)", f"{e['high_alerts']:,} 건"),
        ("누적 경보", f"{e['total_alerts']:,} 건"),
    ], cols=3)

    pdf.section_title(ic["title"])
    pdf.kv_grid([
        ("코베넌트 위반(미해소)", f"{ic['covenant_breaches']} 건 (중대 {ic['covenant_major']})"),
        ("여신 신청 처리", f"승인 {ic['applications_approved']:,} · 심사중 {ic['applications_reviewing']} · 부결 {ic['applications_rejected']}"),
        ("감사 기록", f"{ic['audit_log_count']:,} 건"),
    ], cols=3)

    return bytes(pdf.output())
