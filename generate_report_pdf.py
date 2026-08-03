#!/usr/bin/env python3
"""
CLMS Technical Report PDF Generator
논문 형식 PDF 생성 (한글 지원)
"""
from fpdf import FPDF
import os

# Font paths - SCDream (has OS/2 table, fpdf2 compatible)
FONT_TITLE = "/Users/yalkongs/Library/Fonts/SCDream6.otf"    # SemiBold - titles
FONT_HEADING = "/Users/yalkongs/Library/Fonts/SCDream5.otf"  # Medium - headings
FONT_BODY = "/Users/yalkongs/Library/Fonts/SCDream3.otf"     # Light - body text
FONT_MONO = "/System/Library/Fonts/Supplemental/NotoSansGothic-Regular.ttf"  # formulas


class CLMSReport(FPDF):
    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        self.set_auto_page_break(auto=True, margin=25)
        # Register Korean fonts
        self.add_font("title", "", FONT_TITLE)
        self.add_font("heading", "", FONT_HEADING)
        self.add_font("body", "", FONT_BODY)
        self.add_font("mono", "", FONT_MONO)
        self.page_count = 0

    def header(self):
        if self.page_no() > 1:
            self.set_font("body", "", 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 5, "iM뱅크 CLMS 기술 보고서", align='L')
            self.cell(0, 5, f"- {self.page_no()} -", align='R', new_x="LMARGIN", new_y="NEXT")
            self.line(10, 12, 200, 12)
            self.ln(3)
            self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font("body", "", 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Copyright (c) 2026 iM Bank. All rights reserved.", align='C')
        self.set_text_color(0, 0, 0)

    # ── helpers ─────────────────────────────────────
    def section_title(self, num, title):
        """Large section heading"""
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

    def subsection_title(self, num, title):
        """Sub-section heading"""
        self.ln(2)
        if self.get_y() > 260:
            self.add_page()
        self.set_font("heading", "", 13)
        self.set_text_color(0, 70, 130)
        self.cell(0, 8, f"{num}  {title}", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def subsubsection(self, title):
        """Sub-sub heading"""
        self.ln(1)
        if self.get_y() > 265:
            self.add_page()
        self.set_font("heading", "", 11)
        self.set_text_color(50, 50, 50)
        self.cell(0, 7, f"  {title}", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
        self.set_text_color(0, 0, 0)

    def body_text(self, text):
        self.set_font("body", "", 10)
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def formula_block(self, lines):
        """Math formula in monospace-like block"""
        self.ln(1)
        self.set_fill_color(245, 245, 250)
        y0 = self.get_y()
        self.set_font("heading", "", 9)
        for line in lines:
            self.set_x(20)
            self.cell(170, 5.5, line, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def table(self, headers, rows, col_widths=None):
        """Draw a table"""
        if self.get_y() > 250:
            self.add_page()
        n = len(headers)
        if col_widths is None:
            w = 190 / n
            col_widths = [w] * n
        # header
        self.set_font("heading", "", 9)
        self.set_fill_color(0, 51, 102)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=1, fill=True, align='C')
        self.ln()
        # rows
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
                    self.cell(col_widths[i], 7, h, border=1, fill=True, align='C')
                self.ln()
                self.set_text_color(0, 0, 0)
                self.set_font("body", "", 9)
            if fill:
                self.set_fill_color(240, 245, 255)
            else:
                self.set_fill_color(255, 255, 255)
            for i, val in enumerate(row):
                align = 'C' if i > 0 and len(str(val)) < 15 else 'L'
                self.cell(col_widths[i], 6.5, str(val), border=1, fill=True, align=align)
            self.ln()
            fill = not fill
        self.ln(2)

    def bullet(self, text, indent=15):
        self.set_font("body", "", 10)
        self.set_x(indent)
        self.cell(5, 5.5, "•")
        self.multi_cell(175 - indent, 5.5, text)


def build_report():
    pdf = CLMSReport()

    # ═══════════════════════════════════════════════
    # TITLE PAGE
    # ═══════════════════════════════════════════════
    pdf.add_page()
    pdf.ln(35)
    pdf.set_font("title", "", 28)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 14, "iM뱅크 CLMS", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("title", "", 20)
    pdf.cell(0, 12, "여신생애주기관리시스템", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("heading", "", 14)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, "기술 보고서", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("heading", "", 11)
    pdf.cell(0, 8, "Credit Lifecycle Management System - Technical Specification & Mathematical Framework", align='C', new_x="LMARGIN", new_y="NEXT")

    pdf.ln(15)
    pdf.set_draw_color(0, 51, 102)
    pdf.set_line_width(0.8)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(15)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("heading", "", 13)
    pdf.cell(0, 8, "iM Bank  황원철", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("heading", "", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, "iM뱅크 디지털금융그룹", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.cell(0, 7, "Version 1.2.0  |  2026년 2월", align='C', new_x="LMARGIN", new_y="NEXT")

    pdf.ln(25)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("heading", "", 10)
    pdf.cell(0, 6, "─── Abstract ───", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("body", "", 10)
    pdf.set_x(25)
    pdf.multi_cell(160, 5.5,
        "본 보고서는 iM뱅크 여신생애주기관리시스템(CLMS)의 기술 사양을 문서화한다. "
        "시스템은 Basel II/III 내부등급법(IRB) 기반의 신용리스크 계량화 체계를 채택하며, "
        "19개 화면, 133개 API 엔드포인트, 49개 데이터 테이블로 구성된다. "
        "핵심 수리 모형으로 IRB RWA 산출, RAROC 가격결정, 5채널 선행지표 기반 "
        "조기경보시스템(EWS), 포트폴리오 최적화, 스트레스 테스트 등을 포함하며, "
        "각 모형의 수학적 산출식과 시스템 가정치를 상세히 기술한다.",
        align='J')

    # ═══════════════════════════════════════════════
    # TABLE OF CONTENTS
    # ═══════════════════════════════════════════════
    pdf.add_page()
    pdf.set_font("title", "", 18)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 12, "목  차", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    toc = [
        ("1", "서론", "시스템 개요, 범위, 이론적 기반"),
        ("2", "시스템 아키텍처", "기술 스택, 프론트엔드, 백엔드, DB 구조"),
        ("3", "데이터 모델", "49개 테이블 분류, 핵심 관계, 데이터 규모"),
        ("4", "핵심 수리 모형", "RWA(IRB), EL, EC, RAROC, Pricing, 자본비율"),
        ("5", "메뉴별 기능 및 산출식", "19개 화면 상세 (15개 절)"),
        ("6", "시스템 상수 및 가정치", "비용률, FTP, Basel 파라미터, 스트레스"),
        ("7", "데이터 생성 방법론", "시드 데이터, 확장 데이터, EWS 선행지표"),
        ("8", "모형 한계 및 향후 과제", "6가지 한계점, 6가지 향후 과제"),
        ("A", "부록: API 엔드포인트 목록", "133개 전체 목록"),
    ]
    pdf.set_font("body", "", 11)
    pdf.set_text_color(0, 0, 0)
    for num, title, desc in toc:
        pdf.set_x(20)
        pdf.cell(12, 7, num)
        pdf.cell(60, 7, title)
        pdf.set_font("body", "", 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(100, 7, desc, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("body", "", 11)
        pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    # ═══════════════════════════════════════════════
    # 1. 서론
    # ═══════════════════════════════════════════════
    pdf.add_page()
    pdf.section_title("1", "서론")

    pdf.subsection_title("1.1", "시스템 개요")
    pdf.body_text(
        "iM뱅크 CLMS(Credit Lifecycle Management System)는 여신(대출)의 전체 생애주기를 "
        "통합 관리하는 시스템으로, 신용리스크 측정·한도관리·가격결정·포트폴리오 최적화·조기경보 등 "
        "은행 여신업무의 핵심 기능을 포괄한다. 본 시스템은 Basel II/III 내부등급법(IRB) 기반의 "
        "리스크 계량화 체계를 채택하며, 19개 화면, 133개 이상의 API 엔드포인트, 49개 데이터 "
        "테이블로 구성된다."
    )

    pdf.subsection_title("1.2", "시스템의 범위")
    pdf.table(
        ["영역", "기능"],
        [
            ["전략계층", "대시보드, 자본관리, 포트폴리오 전략, 스트레스 테스트, 자본 최적화"],
            ["전술계층", "한도관리, 동적한도, 여신심사, 가격결정(What-if)"],
            ["운영계층", "고객관리, 여신실행, 담보관리, 부실채권(Workout)"],
            ["분석계층", "조기경보(EWS), 모델관리(MRM), 고객수익성, 포트폴리오 최적화, ESG, ALM"],
        ],
        [35, 155]
    )

    pdf.subsection_title("1.3", "이론적 기반")
    pdf.body_text("본 시스템의 신용리스크 모형은 다음의 학술적·규제적 프레임워크에 기초한다:")
    refs = [
        "Basel II/III IRB Approach (BCBS, 2006; 2017) - 자본요구량 산출 공식",
        "Vasicek (1991/2002) Single-Factor Model - 자산상관계수 및 자본요구량 도출",
        "Merton (1974) Structural Model - 기업가치 기반 부도확률 이론",
        "KMV Model (Crosbie & Bohn, 2003) - Distance-to-Default 개념",
        "RiskMetrics (J.P. Morgan, 1996) - 시장리스크 측정 방법론",
        "Altman Z-Score (1968) - 재무비율 기반 부실예측",
    ]
    for r in refs:
        pdf.bullet(r)

    # ═══════════════════════════════════════════════
    # 2. 시스템 아키텍처
    # ═══════════════════════════════════════════════
    pdf.add_page()
    pdf.section_title("2", "시스템 아키텍처")

    pdf.subsection_title("2.1", "기술 스택")
    pdf.table(
        ["계층", "기술", "상세"],
        [
            ["Frontend", "React 18 + TypeScript", "Vite, Tailwind CSS, Recharts, Lucide React"],
            ["Backend", "FastAPI (Python 3.11+)", "SQLAlchemy, 18 API Routers, 133 Endpoints"],
            ["Database", "SQLite", "49 Tables, ~1,010 Customers, 3 Regions"],
            ["수리엔진", "calculations.py", "IRB RWA, RAROC, Pricing, Stress PD"],
        ],
        [30, 55, 105]
    )

    pdf.subsection_title("2.2", "프론트엔드 라우팅 (19개 화면)")
    pdf.table(
        ["경로", "화면명", "설명"],
        [
            ["/", "전략 대시보드", "자본·포트폴리오·EWS 종합 현황"],
            ["/applications", "여신심사", "신청서 관리, What-if 시뮬레이션"],
            ["/capital", "자본관리", "BIS비율, RWA 구성, 시뮬레이션"],
            ["/capital-optimizer", "자본 효율성", "RWA밀도, 리밸런싱 추천"],
            ["/portfolio", "포트폴리오 전략", "전략 매트릭스, 집중도(HHI)"],
            ["/portfolio-optimization", "포트폴리오 최적화", "RAROC극대화, RWA최소화, Risk Parity"],
            ["/limits", "한도관리", "다차원 한도, 소진율, 경보"],
            ["/dynamic-limits", "동적한도", "경기순환 연동 자동 조정"],
            ["/stress-test", "스트레스 테스트", "5단계 시나리오 분석"],
            ["/models", "모델관리(MRM)", "백테스트, Override, 빈티지"],
            ["/customers", "고객관리", "통합 조회, 업종·규모 필터"],
            ["/ews-advanced", "조기경보(EWS)", "6개 탭: 통합·거래·공적·시장·뉴스·공급망"],
            ["/customer-profitability", "고객수익성", "RBC, CLV, Cross-sell"],
            ["/collateral-monitoring", "담보 모니터링", "LTV, 시세지수 연동"],
            ["/workout", "부실채권", "회수 시나리오, NPV"],
            ["/esg", "ESG 리스크", "E/S/G 점수, 녹색금융"],
            ["/alm", "ALM", "금리갭, 듀레이션, EVE"],
        ],
        [45, 40, 105]
    )

    pdf.subsection_title("2.3", "백엔드 API 모듈")
    pdf.table(
        ["모듈", "엔드포인트 수", "담당 기능"],
        [
            ["dashboard.py", "5", "전략 대시보드"],
            ["applications.py", "7", "여신심사"],
            ["capital.py", "6", "자본관리"],
            ["capital_optimizer.py", "5", "자본 효율성"],
            ["portfolio.py", "6", "포트폴리오 전략"],
            ["portfolio_optimization.py", "7", "포트폴리오 최적화"],
            ["limits.py", "7", "한도관리"],
            ["dynamic_limits.py", "7", "동적한도"],
            ["stress_test.py", "4", "스트레스 테스트"],
            ["models.py", "12", "모델관리(MRM)"],
            ["customers.py", "4", "고객관리"],
            ["ews_advanced.py", "24", "조기경보(EWS)"],
            ["customer_profitability.py", "6", "고객수익성"],
            ["collateral_monitoring.py", "6", "담보관리"],
            ["workout.py", "6", "부실채권"],
            ["esg.py", "6", "ESG 리스크"],
            ["alm.py", "7", "ALM"],
            ["model_inference.py", "8", "모델 추론"],
            ["합계", "133", ""],
        ],
        [50, 30, 110]
    )

    # ═══════════════════════════════════════════════
    # 3. 데이터 모델
    # ═══════════════════════════════════════════════
    pdf.add_page()
    pdf.section_title("3", "데이터 모델")

    pdf.subsection_title("3.1", "테이블 분류 체계 (49개)")
    pdf.table(
        ["계층", "테이블 수", "주요 테이블"],
        [
            ["마스터", "5", "customer(18col), borrower_group, industry_master"],
            ["운영", "7", "facility(17col), loan_application(20col), risk_parameter(13col)"],
            ["전술", "6", "ftp_rate, pricing_result(23col), credit_spread"],
            ["전략", "9", "capital_position(13col), stress_scenario, limit_definition"],
            ["기반", "8", "model_registry, model_performance_log(15col), portfolio_summary"],
            ["EWS 확장", "6", "ews_transaction_behavior, ews_market_signal, ews_composite_score"],
            ["기타 확장", "8", "dynamic_limit_rule, customer_profitability(27col)"],
        ],
        [30, 25, 135]
    )

    pdf.subsection_title("3.2", "데이터 규모")
    pdf.table(
        ["구분", "건수", "비고"],
        [
            ["고객", "~1,010", "3개 지역 (수도권/대구경북/부산경남)"],
            ["여신 (facility)", "~1,200", "ACTIVE 상태"],
            ["리스크 파라미터", "~1,500", "PD, LGD, EAD, RWA, EL"],
            ["EWS 거래행태", "~12,120", "1,010고객 × 12개월"],
            ["EWS 시장신호", "~3,636", "303 상장기업 × 12개월"],
            ["EWS 뉴스감성", "~17,170", "기사 + 월별 집계"],
            ["EWS 공급망", "~11,976", "거래처별 시계열"],
            ["EWS 공적정보", "~900", "이벤트 기반"],
            ["합계", "~50,000+", ""],
        ],
        [45, 30, 115]
    )

    pdf.subsection_title("3.3", "핵심 관계도")
    pdf.body_text(
        "customer(1) ── (N) facility(1) ── (1) loan_application ── (1) risk_parameter\n"
        "customer(1) ── (N) credit_rating_result\n"
        "customer(1) ── (N) ews_composite_score\n"
        "customer(1) ── (N) ews_transaction_behavior / ews_market_signal / ews_public_registry\n"
        "customer(1) ── (N) customer_profitability"
    )

    # ═══════════════════════════════════════════════
    # 4. 핵심 수리 모형
    # ═══════════════════════════════════════════════
    pdf.add_page()
    pdf.section_title("4", "핵심 수리 모형")

    # 4.1 RWA
    pdf.subsection_title("4.1", "RWA 산출 - Basel IRB 공식")
    pdf.body_text(
        "Basel II/III 내부등급법(Foundation IRB)에 의한 자본요구량(K) 및 위험가중자산(RWA) "
        "산출식이다. Vasicek(2002)의 단일요인 모형에 기초한다."
    )

    pdf.subsubsection("자산상관계수 (Asset Correlation, R)")
    pdf.formula_block([
        "R = 0.12 × (1 - e^(-50·PD)) / (1 - e^(-50))",
        "  + 0.24 × [1 - (1 - e^(-50·PD)) / (1 - e^(-50))]",
        "",
        "범위: 0.12 ≤ R ≤ 0.24  (PD↑ → R↓)",
    ])

    pdf.subsubsection("만기조정 계수 (Maturity Adjustment, b)")
    pdf.formula_block([
        "b = (0.11852 - 0.05478 × ln(max(PD, 0.0001)))²",
    ])

    pdf.subsubsection("자본요구량 (Capital Requirement, K)")
    pdf.formula_block([
        "K = LGD × [ Φ( Φ⁻¹(PD)/√(1-R) + √(R/(1-R)) × Φ⁻¹(0.999) ) - PD × LGD ]",
        "",
        "K_adj = K × (1 + (M - 2.5) × b) / (1 - 1.5 × b)",
        "",
        "  Φ   : 표준정규분포 CDF",
        "  Φ⁻¹ : 표준정규분포 역함수 (quantile function)",
        "  M   : 잔존만기 (기본값: 2.5년)",
    ])

    pdf.subsubsection("위험가중자산 (RWA)")
    pdf.formula_block([
        "RWA = K_adj × 12.5 × EAD",
        "",
        "  12.5 = 1 / 0.08 (최소자본비율 8%의 역수)",
    ])
    pdf.body_text("구현: backend/app/services/calculations.py:27-89")

    # 4.2 EL
    pdf.subsection_title("4.2", "예상손실 (Expected Loss, EL)")
    pdf.formula_block([
        "EL = PD × LGD × EAD",
        "",
        "  PD  : 부도확률 (연간, TTC 또는 PIT)",
        "  LGD : 부도시손실률 (0 ~ 1)",
        "  EAD : 부도시익스포저 (원)",
    ])

    # 4.3 EC
    pdf.subsection_title("4.3", "경제적 자본 (Economic Capital, EC)")
    pdf.formula_block([
        "EC = RWA × 10.5%",
        "",
        "  BIS 최소 자본비율 8% + 자본보전완충자본 2.5% = 10.5%",
    ])

    # 4.4 RAROC
    pdf.subsection_title("4.4", "RAROC (Risk-Adjusted Return on Capital)")

    pdf.subsubsection("기본 공식")
    pdf.formula_block([
        "RAROC = (이자수익 - 조달비용 - 운영비 - EL) / EC",
    ])

    pdf.subsubsection("개별 건별 (What-if 분석)")
    pdf.formula_block([
        "RAROC = (A × r_final - A × r_FTP - A × r_opex - PD × LGD × A)",
        "        / (RWA(PD, LGD, A, M) × 0.105)",
        "",
        "  A       : 대출금액",
        "  r_final : 최종 적용금리 (연율)",
        "  r_FTP   : 내부자금이전가격 (테너별)",
        "  r_opex  : 운영비율 (0.5%)",
        "  M       : 대출만기 (년)",
    ])

    pdf.subsubsection("포트폴리오 수준 (대시보드)")
    pdf.formula_block([
        "RAROC_port = [ Σ(Oi × ri) - ΣOi × 0.048 - ΣELi ] / (ΣRWA_i × 0.105)",
        "",
        "  Oi    : i번째 여신 잔액 (outstanding_amount)",
        "  ri    : i번째 여신 최종금리 (final_rate)",
        "  0.048 : 총비용률 (조달 4.3% + 운영 0.5%)",
    ])
    pdf.body_text("구현: backend/app/services/calculations.py:102-153, backend/app/api/dashboard.py:53-62")

    # 4.5 Pricing
    pdf.subsection_title("4.5", "가격결정 (Pricing) 모형")

    pdf.subsubsection("금리 구성요소")
    pdf.formula_block([
        "r_final = r_base + s_FTP + s_credit + s_opex + s_margin + adj_strategy + adj_collateral",
    ])

    pdf.subsubsection("신용스프레드 분해")
    pdf.formula_block([
        "s_credit = s_EL + s_UL",
        "s_EL = PD × LGD",
        "s_UL = s_EL × 0.5 × r_hurdle",
        "",
        "  r_base   : 기준금리 (3.5%)",
        "  s_FTP    : FTP 스프레드 (0.5%)",
        "  s_opex   : 운영비 스프레드 (0.2%)",
        "  s_margin : 목표마진 (1.0%)",
        "  r_hurdle : 허들레이트 (12%)",
    ])

    pdf.subsubsection("전략별 가감 조정")
    pdf.table(
        ["전략코드", "가감(bp)", "설명"],
        [
            ["EXPAND", "-20", "확대 전략: 금리 인하"],
            ["SELECTIVE", "0", "선별적"],
            ["MAINTAIN", "+10", "유지"],
            ["REDUCE", "+30", "축소"],
            ["EXIT", "+100", "퇴출: 금리 인상"],
        ],
        [40, 30, 120]
    )
    pdf.body_text("담보 가감: 담보 있으면 -30bp, 무담보 0bp")
    pdf.body_text("구현: backend/app/services/calculations.py:156-205")

    # 4.6 Capital Ratios
    pdf.subsection_title("4.6", "자본비율 체계")
    pdf.formula_block([
        "BIS Ratio      = (CET1 + AT1 + T2) / (RWA_credit + RWA_market + RWA_operational)",
        "CET1 Ratio     = CET1 Capital / Total RWA",
        "Tier1 Ratio    = (CET1 + AT1) / Total RWA",
        "Leverage Ratio = Tier1 Capital / Total Exposure",
    ])

    # ═══════════════════════════════════════════════
    # 5. 메뉴별 기능 및 산출식
    # ═══════════════════════════════════════════════
    pdf.add_page()
    pdf.section_title("5", "메뉴별 기능 및 산출식")

    # 5.1 Dashboard
    pdf.subsection_title("5.1", "전략 대시보드 (Dashboard)")
    pdf.body_text(
        "자본현황 StatCard, 포트폴리오 KPI, EWS 경보 요약, 자본비율 추이 차트, "
        "포트폴리오 분포 차트로 구성. 모든 지표에 customer.region 기반 필터 적용 "
        "(자본현황 제외 - 은행 전체)."
    )
    pdf.table(
        ["지표", "산출식", "데이터 소스"],
        [
            ["BIS 비율", "capital_position.bis_ratio × 100", "capital_position"],
            ["총 익스포저", "SUM(facility.approved_amount)", "facility"],
            ["평균금리", "AVG(facility.final_rate) × 100", "facility"],
            ["가중PD", "AVG(risk_parameter.ttc_pd)", "risk_parameter"],
            ["포트폴리오 RAROC", "4.4절 포트폴리오 공식", "facility + risk_parameter"],
            ["대표등급", "MODE(final_grade)", "credit_rating_result"],
        ],
        [40, 85, 65]
    )

    # 5.2 Stress Test
    pdf.subsection_title("5.2", "스트레스 테스트")
    pdf.subsubsection("시나리오별 충격 계수")
    pdf.table(
        ["강도", "PD 배수", "LGD 배수", "RWA 배수"],
        [
            ["BASELINE", "1.0", "1.0", "1.0"],
            ["MILD", "1.3", "1.1", "1.1"],
            ["MODERATE", "1.8", "1.3", "1.25"],
            ["SEVERE", "2.5", "1.5", "1.4"],
            ["EXTREME", "3.5", "1.8", "1.6"],
        ],
        [47, 47, 48, 48]
    )

    pdf.subsubsection("스트레스 PD 산출")
    pdf.formula_block([
        "PD_stressed = min(PD_base × F_PD × S_industry, 0.30)",
        "LGD_stressed = min(LGD_base × F_LGD, 0.70)",
        "BIS_stressed = Total Capital / RWA_stressed",
    ])

    pdf.subsubsection("산업별 민감도 계수")
    pdf.table(
        ["산업", "민감도", "산업", "민감도"],
        [
            ["금융", "0.8", "부동산", "1.1"],
            ["IT", "0.8", "숙박/관광", "1.5"],
            ["제조", "1.0", "항공", "1.8"],
            ["건설", "1.0", "의료", "0.9"],
            ["도소매", "1.0", "기타", "1.0"],
        ],
        [47, 47, 48, 48]
    )

    # 5.3 MRM
    pdf.subsection_title("5.3", "모델관리 - MRM (Model Risk Management)")
    pdf.subsubsection("등록 모델 (5개)")
    pdf.table(
        ["모델 ID", "명칭", "유형"],
        [
            ["MDL_CORP_RATING", "기업 신용평가", "PD"],
            ["MDL_RETAIL_RATING", "소호 신용평가", "PD"],
            ["MDL_LGD", "부도시손실률", "LGD"],
            ["MDL_EAD", "부도시익스포저", "EAD"],
            ["MDL_PRICING", "가격결정", "Pricing"],
        ],
        [55, 80, 55]
    )

    pdf.subsubsection("성능 지표 및 경보 기준")
    pdf.table(
        ["지표", "설명", "경보 기준"],
        [
            ["Gini 계수", "판별력", "Warning < 0.40, Critical < 0.35"],
            ["KS 통계량", "Kolmogorov-Smirnov", "높을수록 양호"],
            ["AUROC", "ROC 곡선 하 면적", "> 0.70"],
            ["PSI", "모집단 안정성 지수", "Warning > 0.10, Critical > 0.25"],
            ["AR Ratio", "실적/예측 비율", "Warning: <0.80 or >1.20"],
        ],
        [35, 70, 85]
    )

    pdf.subsubsection("PD 백테스트 - 이항검정")
    pdf.formula_block([
        "p-value = P(X ≥ k | n, PD_predicted)",
        "X ~ Binomial(n, PD_predicted)",
        "",
        "신뢰수준: 95%, Warning: p < 0.05, Fail: p < 0.01",
    ])

    pdf.subsubsection("Override 임계치")
    pdf.table(
        ["지표", "기준"],
        [
            ["최대 재조정률", "15%"],
            ["최대 상향 비율", "50%"],
            ["Type I 오류 (상향→부도)", "≤ 5%"],
            ["Type II 오류 (하향→정상)", "≤ 20%"],
            ["최소 정확도", "≥ 70%"],
        ],
        [95, 95]
    )

    # 5.4 EWS
    pdf.add_page()
    pdf.subsection_title("5.4", "조기경보시스템 - EWS (Early Warning System)")
    pdf.body_text(
        "6개 탭으로 구성된 다채널 선행지표 기반 조기경보 체계. 5개 선행성 데이터 채널과 "
        "기존 재무비율 채널을 결합하여 종합점수를 산출한다."
    )

    pdf.subsubsection("5채널 선행지표 체계")
    pdf.table(
        ["채널", "데이터 소스", "선행성", "이론적 근거"],
        [
            ["거래행태", "자행 입출금·결제", "3-6개월", "유동성 악화 선행 신호"],
            ["공적정보", "세금체납·가압류·감사의견", "1-3개월", "법적·재무적 위기 신호"],
            ["시장신호", "주가·CDS·DD (상장)", "즉시-1개월", "Merton 구조모형"],
            ["뉴스감성", "NLP 감성분석", "1-3개월", "시장심리 반영"],
            ["공급망", "거래처 리스크 전이", "3-6개월", "연쇄부도 이론"],
            ["재무비율", "재무제표 기반", "후행", "전통적 신용분석"],
        ],
        [30, 55, 30, 75]
    )

    pdf.subsubsection("채널별 점수 산출")
    pdf.body_text("거래행태 점수 (0-100):")
    pdf.formula_block([
        "S_txn = 100 - (U_limit × 40 + D_payment × 0.5 + R_outflow × 30 + N_overdraft × 5)",
        "",
        "  U_limit    : 한도소진율 (0~1)",
        "  D_payment  : 결제지연일수",
        "  R_outflow  : 예금유출률 (0~1)",
        "  N_overdraft: 당좌부도 횟수",
    ])

    pdf.body_text("공적정보 점수 (0-100):")
    pdf.formula_block([
        "S_pub = 100 - (N_unresolved × 15 + N_severe × 20)",
    ])

    pdf.body_text("시장신호 점수 (0-100, 상장기업만):")
    pdf.formula_block([
        "S_mkt = DD × 15 + max(0, 50 - S_CDS × 0.1) - PD_implied × 100",
        "",
        "  DD        : Distance-to-Default",
        "  S_CDS     : CDS 스프레드 (bp)",
        "  PD_implied: 시장내재 부도확률",
    ])

    pdf.body_text("뉴스감성 점수 (0-100):")
    pdf.formula_block([
        "S_news = 50 + avg_sentiment × 50 - R_negative × 30",
    ])

    pdf.subsubsection("종합점수 산출 (Composite Score)")
    pdf.body_text("상장기업:")
    pdf.formula_block([
        "S = 0.25×S_txn + 0.15×S_pub + 0.15×S_mkt + 0.15×S_news + 0.15×S_supply + 0.15×S_fin",
    ])
    pdf.body_text("비상장기업:")
    pdf.formula_block([
        "S = 0.30×S_txn + 0.20×S_pub + 0.20×S_news + 0.15×S_supply + 0.15×S_fin",
    ])

    pdf.subsubsection("EWS 등급 분류")
    pdf.table(
        ["등급", "점수 범위", "관리 조치"],
        [
            ["NORMAL", "≥ 75", "정기 모니터링"],
            ["WATCH", "55 ≤ S < 75", "관찰 대상 등록, 모니터링 강화"],
            ["WARNING", "35 ≤ S < 55", "여신관리 담당 지정, 한도 동결"],
            ["CRITICAL", "< 35", "여신회수 검토, Workout 이관"],
        ],
        [35, 35, 120]
    )

    pdf.subsubsection("추세 판정")
    pdf.formula_block([
        "ΔS = S_current - S_previous",
        "",
        "IMPROVING     : ΔS > +5",
        "STABLE        : -5 ≤ ΔS ≤ +5",
        "DETERIORATING : ΔS < -5",
    ])

    # 5.5 Customer Profitability
    pdf.subsection_title("5.5", "고객 수익성 (Customer Profitability)")
    pdf.subsubsection("RBC (Relationship-Based Costing) 체계")
    pdf.formula_block([
        "Π_total = Π_loan + Π_deposit + Π_fee + Π_FX",
        "",
        "Π_loan = A × r_final - A × r_funding - EL - EC × r_hurdle",
        "",
        "RAROC_customer = Π_total / EC_total × 100",
    ])

    pdf.subsubsection("고객생애가치 (CLV)")
    pdf.formula_block([
        "CLV = Σ [ Π_t × p_retention^t / (1 + r_discount)^t ]",
        "",
        "  Π_t         : t기 예상 이익",
        "  p_retention  : 유지 확률",
        "  r_discount   : 할인율 (자기자본비용)",
    ])

    # 5.6 ESG
    pdf.subsection_title("5.6", "ESG 리스크")
    pdf.formula_block([
        "S_ESG = 0.35 × S_E + 0.30 × S_S + 0.35 × S_G",
        "",
        "PD_adjusted = PD_base × (1 + adj_ESG)",
    ])
    pdf.table(
        ["ESG 등급", "점수 범위", "PD 가감", "금리 가감"],
        [
            ["A", "≥ 80", "-0.2%p", "-10bp"],
            ["B", "65-79", "-0.1%p", "-5bp"],
            ["C", "50-64", "0", "0"],
            ["D", "35-49", "+0.2%p", "+10bp"],
            ["E", "< 35", "+0.5%p", "+25bp"],
        ],
        [35, 40, 55, 60]
    )

    # 5.7 ALM
    pdf.subsection_title("5.7", "금리리스크 관리 - ALM")
    pdf.formula_block([
        "금리갭:  Gap = A_floating - L_floating",
        "NIM 민감도:  ΔNIM = Gap × Δr / A_total",
        "듀레이션 갭:  D_gap = D_A - (L/A) × D_L",
        "EVE 민감도:  ΔEVE = -D_gap × A × Δr",
    ])
    pdf.body_text("만기 버킷: 1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y, 5Y+")
    pdf.body_text("금리 시나리오: 평행상승/하락, 스티프닝, 플래트닝, 역전 - 헤지 효과성 목표 ≥ 80%")

    # 5.8 Portfolio Optimization
    pdf.subsection_title("5.8", "포트폴리오 최적화")
    pdf.subsubsection("목적함수 - RAROC 극대화")
    pdf.formula_block([
        "max Σ (w_i × RAROC_i)",
        "",
        "제약: Σw_i = 1,  BIS ≥ 11%,  HHI ≤ 0.25,  max(w_i) ≤ 10%,  w_i ≥ 0",
    ])
    pdf.subsubsection("포트폴리오 리스크")
    pdf.formula_block([
        "σ²_p = ΣΣ (w_i × w_j × ρ_ij × UL_i × UL_j)",
        "",
        "Credit Sharpe = (RAROC_portfolio - r_hurdle) / σ_UL",
    ])

    # ═══════════════════════════════════════════════
    # 6. 시스템 상수 및 가정치
    # ═══════════════════════════════════════════════
    pdf.add_page()
    pdf.section_title("6", "시스템 상수 및 가정치")

    pdf.subsection_title("6.1", "비용률 상수")
    pdf.table(
        ["상수", "값", "설명", "적용 위치"],
        [
            ["FUNDING_RATE", "4.3%", "조달비용률", "region_helper.py"],
            ["OPEX_RATE", "0.5%", "운영비율", "calculations.py"],
            ["COST_RATE", "4.8%", "총비용률", "dashboard.py"],
            ["EC_RATIO", "10.5%", "경제적 자본비율 (BIS 8%+보전 2.5%)", "전 모듈"],
            ["HURDLE_RATE", "12%", "자기자본비용", "dashboard.py"],
        ],
        [40, 20, 75, 55]
    )

    pdf.subsection_title("6.2", "FTP 금리 커브 (KRW, 2026-02)")
    pdf.table(
        ["테너", "FTP 금리", "비고"],
        [
            ["3개월", "3.20%", "단기 자금"],
            ["12개월", "3.50%", "1년물"],
            ["24개월", "3.70%", "2년물"],
            ["36개월", "3.85%", "3년물"],
            ["60개월", "4.10%", "5년물"],
        ],
        [40, 40, 110]
    )
    pdf.body_text("원화 스왑금리 기반. 유동성 프리미엄 및 기간 프리미엄 포함. 2026년 2월 기준 한국 시장금리 수준 반영.")

    pdf.subsection_title("6.3", "등급-PD 매핑")
    pdf.table(
        ["등급", "PD", "등급", "PD", "등급", "PD"],
        [
            ["AAA", "0.02%", "A+", "0.15%", "BBB-", "1.85%"],
            ["AA+", "0.04%", "A", "0.25%", "BB+", "3.00%"],
            ["AA", "0.06%", "A-", "0.45%", "BB", "4.80%"],
            ["AA-", "0.10%", "BBB+", "0.70%", "BB-", "7.50%"],
            ["", "", "BBB", "1.15%", "B+", "12.00%"],
            ["", "", "", "", "B / B-", "20% / 30%"],
        ],
        [25, 25, 25, 30, 40, 45]
    )

    pdf.subsection_title("6.4", "포트폴리오 RAROC 실측값 (2026-02)")
    pdf.table(
        ["지역", "RAROC", "비고"],
        [
            ["전체", "11.09%", "포트폴리오 가중평균"],
            ["수도권 (CAPITAL)", "14.13%", "고등급 비중 높음"],
            ["대구경북 (DAEGU_GB)", "10.96%", "중간 수준"],
            ["부산경남 (BUSAN_GN)", "8.34%", "허들레이트(12%) 하회"],
        ],
        [55, 30, 105]
    )

    # ═══════════════════════════════════════════════
    # 7. 데이터 생성 방법론
    # ═══════════════════════════════════════════════
    pdf.add_page()
    pdf.section_title("7", "데이터 생성 방법론")

    pdf.subsection_title("7.1", "기초 데이터 (seed_data.py)")
    pdf.body_text(
        "고객 수: 1,010명 (기업 + 소호). "
        "지역 분포: 수도권(CAPITAL), 대구경북(DAEGU_GB), 부산경남(BUSAN_GN). "
        "산업 분류: 10개 산업. 규모 분류: LARGE, MEDIUM, SMALL, SOHO. "
        "상장기업 비율: ~30%."
    )

    pdf.subsection_title("7.2", "확장 데이터 (generate_extension_data.py)")
    pdf.table(
        ["모듈", "데이터 건수", "주요 가정"],
        [
            ["EWS 지표", "~12,000", "200고객 × 6개월 × 10지표"],
            ["공급망 관계", "500", "의존도 0.1~0.9"],
            ["동적한도", "~200", "24개월 경기순환"],
            ["고객수익성", "1,010", "전 고객 대상, RBC 체계"],
            ["담보", "~6,480", "8지역 × 5유형 × 12개월 + 이력"],
            ["Workout", "30건", "고액 여신(>10B) 대상"],
            ["ESG", "1,060", "전 고객 + 녹색금융 50건"],
            ["ALM", "~180", "8만기버킷 × 7시나리오"],
        ],
        [40, 35, 115]
    )

    pdf.subsection_title("7.3", "EWS 선행지표 데이터 (generate_ews_leading_data.py)")
    pdf.table(
        ["테이블", "건수", "기간"],
        [
            ["ews_transaction_behavior", "~12,120", "12개월 (2025-03~2026-02)"],
            ["ews_public_registry", "~900", "이벤트 기반"],
            ["ews_market_signal", "~3,636", "상장 303사 × 12개월"],
            ["ews_news_sentiment", "~5,050", "기사 단위"],
            ["ews_news_sentiment_monthly", "~12,120", "월별 집계"],
            ["ews_supply_chain_temporal", "~11,976", "거래처별 시계열"],
            ["합계", "~45,800", ""],
        ],
        [65, 30, 95]
    )
    pdf.body_text("신용등급 기반 위험 프로파일로 일관된 상관관계 생성. 결정적 ID 포맷 사용 (UUID 충돌 방지).")

    pdf.subsection_title("7.4", "규모별 승수")
    pdf.table(
        ["규모", "승수", "적용"],
        [
            ["LARGE", "5.0x", "익스포저, 수익 규모"],
            ["MEDIUM", "2.0x", ""],
            ["SMALL", "1.0x", "기준"],
            ["SOHO", "0.5x", ""],
        ],
        [40, 40, 110]
    )

    # ═══════════════════════════════════════════════
    # 8. 한계 및 향후 과제
    # ═══════════════════════════════════════════════
    pdf.add_page()
    pdf.section_title("8", "모형 한계 및 향후 과제")

    pdf.subsection_title("8.1", "모형 한계")
    limitations = [
        "단일요인 모형(Single-Factor Model): 자산상관 구조가 단일 체계요인에만 의존. 산업간·지역간 상이한 상관 구조를 완전히 포착하지 못함.",
        "상관계수의 정적 가정: 자산상관계수 R이 PD만의 함수. 위기 시 상관관계 급등(correlation smile) 현상 미반영.",
        "LGD의 경기순환 비의존: LGD가 고정값. 실제로는 경기 하강기 LGD 상승(downturn LGD) 경향 존재.",
        "FTP 커브의 정적 가정: FTP 금리 고정. 시장금리 변동에 따른 동적 조정 미반영.",
        "EWS 가중치의 전문가 판단 의존: 5채널 가중치가 통계적 최적화가 아닌 전문가 판단 기반. 데이터 기반 재보정 필요.",
        "포트폴리오 최적화의 선형 가정: 비선형 리스크 특성(꼬리 리스크, 극단 손실) 충분히 미반영.",
    ]
    for i, l in enumerate(limitations, 1):
        pdf.bullet(f"[{i}] {l}")

    pdf.subsection_title("8.2", "향후 과제")
    futures = [
        "다요인 모형(Multi-Factor Model) 도입: 산업별·지역별 상관 구조 세분화",
        "기계학습 기반 EWS: 채널 가중치 데이터 기반 자동 보정 (LASSO, Random Forest 등)",
        "동적 FTP: 실시간 시장금리 연동 FTP 커브 자동 업데이트",
        "Downturn LGD 모형: PIT LGD 추정을 위한 경기순환 조정 모형",
        "CVA/DVA 통합: 거래상대방 신용리스크 가치조정 반영",
        "IFRS 9 통합: 기대신용손실(ECL) 산출과 3-Stage 분류 체계 연동",
    ]
    for i, f in enumerate(futures, 1):
        pdf.bullet(f"[{i}] {f}")

    # ═══════════════════════════════════════════════
    # References
    # ═══════════════════════════════════════════════
    pdf.ln(8)
    pdf.subsection_title("", "참고문헌")
    references = [
        "[1] BCBS (2006). \"International Convergence of Capital Measurement and Capital Standards: A Revised Framework.\" Basel Committee on Banking Supervision.",
        "[2] BCBS (2017). \"Basel III: Finalising Post-Crisis Reforms.\" Basel Committee on Banking Supervision.",
        "[3] Vasicek, O. (2002). \"The Distribution of Loan Portfolio Value.\" Risk, 15(12), 160-162.",
        "[4] Merton, R.C. (1974). \"On the Pricing of Corporate Debt: The Risk Structure of Interest Rates.\" Journal of Finance, 29(2), 449-470.",
        "[5] Crosbie, P. & Bohn, J. (2003). \"Modeling Default Risk.\" Moody's KMV.",
        "[6] Altman, E.I. (1968). \"Financial Ratios, Discriminant Analysis and the Prediction of Corporate Bankruptcy.\" Journal of Finance, 23(4), 589-609.",
        "[7] J.P. Morgan (1996). \"RiskMetrics - Technical Document.\" 4th Edition.",
        "[8] Gordy, M.B. (2003). \"A Risk-Factor Model Foundation for Ratings-Based Bank Capital Rules.\" Journal of Financial Intermediation, 12, 199-232.",
    ]
    pdf.set_font("body", "", 9)
    for ref in references:
        pdf.set_x(15)
        pdf.multi_cell(175, 5, ref)
        pdf.ln(1)

    # ═══════════════════════════════════════════════
    # Appendix: API Endpoints
    # ═══════════════════════════════════════════════
    pdf.add_page()
    pdf.section_title("A", "부록: 주요 API 엔드포인트 목록")
    pdf.body_text("총 133개 엔드포인트. 대부분 ?region=CAPITAL|DAEGU_GB|BUSAN_GN 파라미터 지원.")

    api_groups = [
        ("Dashboard (5)", [
            ["GET", "/api/dashboard/summary", "대시보드 요약"],
            ["GET", "/api/dashboard/ews-alerts", "EWS 경보"],
            ["GET", "/api/dashboard/kpis", "KPI 현황"],
            ["GET", "/api/dashboard/capital-trend", "자본비율 추이"],
            ["GET", "/api/dashboard/portfolio-distribution", "포트폴리오 분포"],
        ]),
        ("Applications (7)", [
            ["GET", "/api/applications/", "여신신청 목록"],
            ["GET", "/api/applications/pending", "대기 심사"],
            ["POST", "/api/applications/simulate", "What-if 시뮬레이션"],
            ["POST", "/api/applications/{id}/approve", "승인/반려"],
        ]),
        ("EWS Advanced (24)", [
            ["GET", "/api/ews-advanced/integrated-dashboard", "통합 대시보드"],
            ["GET", "/api/ews-advanced/composite-scores", "종합점수"],
            ["GET", "/api/ews-advanced/transaction-behavior/dashboard", "거래행태"],
            ["GET", "/api/ews-advanced/transaction-behavior/anomalies", "이상징후"],
            ["GET", "/api/ews-advanced/public-registry/dashboard", "공적정보"],
            ["GET", "/api/ews-advanced/market-signals/dashboard", "시장신호"],
            ["GET", "/api/ews-advanced/news-sentiment/dashboard", "뉴스감성"],
            ["GET", "/api/ews-advanced/supply-chain/dashboard", "공급망"],
        ]),
        ("Models/MRM (12)", [
            ["GET", "/api/models/", "모델 목록"],
            ["GET", "/api/models/performance", "성능 로그"],
            ["GET", "/api/models/backtest-summary", "백테스트 요약"],
            ["GET", "/api/models/override-performance", "Override 성과"],
            ["GET", "/api/models/vintage-analysis", "빈티지 분석"],
        ]),
        ("기타 모듈 (64)", [
            ["GET", "/api/capital/position", "자본 포지션"],
            ["GET", "/api/capital-optimizer/efficiency-dashboard", "자본 효율성"],
            ["GET", "/api/portfolio/strategy-matrix", "전략 매트릭스"],
            ["GET", "/api/portfolio/concentration", "집중도(HHI)"],
            ["GET", "/api/stress-test/scenarios", "스트레스 시나리오"],
            ["POST", "/api/stress-test/run", "스트레스 실행"],
            ["GET", "/api/limits/", "한도 목록"],
            ["GET", "/api/portfolio-optimization/dashboard", "최적화 대시보드"],
        ]),
    ]
    for group_name, endpoints in api_groups:
        pdf.subsubsection(group_name)
        pdf.table(
            ["Method", "Endpoint", "설명"],
            endpoints,
            [20, 120, 50]
        )

    # ═══════════════════════════════════════════════
    # Save
    # ═══════════════════════════════════════════════
    output_path = os.path.join(os.path.dirname(__file__), "CLMS_Technical_Report.pdf")
    pdf.output(output_path)
    print(f"PDF saved: {output_path}")
    print(f"Pages: {pdf.page_no()}")


if __name__ == "__main__":
    build_report()
