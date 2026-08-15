#!/usr/bin/env python3
"""CLMS 데이터 논문 PDF - 데이터 구성 및 생성 방법론"""
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
        self._header_text = "iM뱅크 CLMS 데이터 논문: 데이터 구성 및 생성 방법론"

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
    p.cell(0, 14, "데이터 구성 및 생성 방법론에 관한 연구", align='C', new_x="LMARGIN", new_y="NEXT")
    p.ln(4)
    p.set_font("heading", "", 12)
    p.set_text_color(80, 80, 80)
    p.cell(0, 8, "A Study on Data Architecture and Synthetic Data Generation", align='C', new_x="LMARGIN", new_y="NEXT")
    p.cell(0, 8, "Methodology for Credit Lifecycle Management System", align='C', new_x="LMARGIN", new_y="NEXT")
    p.ln(12)
    p.set_draw_color(0, 51, 102)
    p.set_line_width(0.8)
    p.line(60, p.get_y(), 150, p.get_y())
    p.ln(12)
    p.set_text_color(0, 0, 0)
    p.set_font("heading", "", 14)
    p.cell(0, 8, "iMBank  황원철", align='C', new_x="LMARGIN", new_y="NEXT")
    p.ln(2)
    p.set_font("heading", "", 11)
    p.set_text_color(100, 100, 100)
    p.cell(0, 7, "iM뱅크 디지털금융그룹", align='C', new_x="LMARGIN", new_y="NEXT")
    p.ln(3)
    p.cell(0, 7, "2026년 2월", align='C', new_x="LMARGIN", new_y="NEXT")

    p.ln(20)
    p.set_text_color(0, 0, 0)
    p.set_font("heading", "", 10)
    p.cell(0, 6, chr(9472) * 3 + " Abstract " + chr(9472) * 3, align='C', new_x="LMARGIN", new_y="NEXT")
    p.ln(3)
    p.set_font("body", "", 10)
    p.set_x(25)
    p.multi_cell(160, 5.5,
        "본 논문은 iM뱅크 여신생애주기관리시스템(CLMS) 데모 환경의 데이터 아키텍처와 "
        "합성 데이터 생성 방법론을 기술한다. 시스템은 5계층 아키텍처로 설계된 49개 테이블, "
        "총 35,000건 이상의 정합성 있는 데이터로 구성된다. 기초 데이터(seed_data.py)에서 "
        "1,000명 고객과 1,200건 여신을 생성하고, 확장 데이터(generate_extension_data.py)에서 "
        "EWS, 동적한도, 고객수익성, 담보모니터링, 포트폴리오 최적화, Workout, ESG, ALM의 "
        "8개 고도화 기능 데이터를 추가한다. 지역별 신용등급 차등, 산업별 리스크 프로파일, "
        "담보유형별 인정비율 등 실제 은행 업무의 비즈니스 룰을 데이터에 내재화하였으며, "
        "데이터 생성 순서 및 의존성, 통계적 분포, 품질 관리 방안을 상세히 논의한다.",
        align='J')

    # ── TOC ──
    p.add_page()
    p.set_font("title", "", 18)
    p.set_text_color(0, 51, 102)
    p.cell(0, 12, "목  차", align='C', new_x="LMARGIN", new_y="NEXT")
    p.ln(6)
    toc = [
        ("1", "서론", "연구 목적 및 범위"),
        ("2", "데이터베이스 설계 원칙", "5계층 아키텍처, 정규화, 제약조건"),
        ("3", "스키마 구조", "49개 테이블 상세"),
        ("4", "기초 데이터 생성", "seed_data.py: 고객, 여신, 리스크 파라미터"),
        ("5", "확장 데이터 생성", "8개 고도화 기능별 데이터"),
        ("6", "지역 차등화 설계", "등급·LGD·분포의 지역별 차등"),
        ("7", "비즈니스 룰 내재화", "신용평가, 금리책정, RAROC"),
        ("8", "데이터 품질 및 정합성", "제약조건, 일관성, 재현성"),
        ("9", "데이터 규모 및 분포 요약", "테이블별 건수, 통계적 분포"),
        ("10", "한계 및 향후 과제", ""),
    ]
    p.set_font("body", "", 11)
    p.set_text_color(0, 0, 0)
    for num, title, desc in toc:
        p.set_x(20)
        p.cell(12, 7, num)
        p.cell(55, 7, title)
        p.set_font("body", "", 9)
        p.set_text_color(100, 100, 100)
        p.cell(105, 7, desc, new_x="LMARGIN", new_y="NEXT")
        p.set_font("body", "", 11)
        p.set_text_color(0, 0, 0)

    # ══════════════════════════════════════
    # 1. 서론
    # ══════════════════════════════════════
    p.add_page()
    p.sec("1", "서론")
    p.sub("1.1", "연구 목적")
    p.txt(
        "신용위험관리시스템의 데모 환경 구축에서 가장 중요한 과제 중 하나는 실제 은행 업무를 "
        "충실히 반영하는 합성 데이터의 설계와 생성이다. 본 논문은 iM뱅크 CLMS 데모 시스템의 "
        "데이터 아키텍처 설계 원칙, 합성 데이터 생성 로직, 비즈니스 룰 내재화 방안, "
        "데이터 품질 관리 체계를 체계적으로 문서화함으로써, 시스템의 데이터 기반을 "
        "명확히 하는 것을 목적으로 한다."
    )
    p.sub("1.2", "시스템 개요")
    p.txt(
        "CLMS 데모 시스템은 SQLite 데이터베이스, FastAPI 백엔드, React+TypeScript 프론트엔드로 "
        "구성되며, 49개 테이블에 35,000건 이상의 데이터를 포함한다. 데이터는 기초 데이터 "
        "(seed_data.py)와 확장 데이터(generate_extension_data.py)의 2단계로 생성된다."
    )
    p.tbl(
        ["구분", "스크립트", "주요 생성 내용", "건수"],
        [
            ["기초 데이터", "seed_data.py", "고객, 여신, 리스크 파라미터, 자본", "~5,000"],
            ["확장 데이터", "generate_extension_data.py", "EWS, 한도, 수익성, 담보, Workout 등", "~30,000"],
        ],
        [30, 55, 70, 35]
    )

    # ══════════════════════════════════════
    # 2. 데이터베이스 설계 원칙
    # ══════════════════════════════════════
    p.add_page()
    p.sec("2", "데이터베이스 설계 원칙")

    p.sub("2.1", "5계층 아키텍처")
    p.txt(
        "데이터베이스는 업무 영역과 데이터의 활용 목적에 따라 5개 계층으로 분류된다. "
        "이 계층 구조는 데이터의 흐름과 의존성을 명확히 한다."
    )
    p.tbl(
        ["계층", "역할", "주요 테이블", "건수"],
        [
            ["1단계: 마스터", "기준 데이터 관리", "customer, industry_master, product_master", "~1,020"],
            ["2단계: 운영", "여신 실행 데이터", "facility, loan_application, risk_parameter", "~5,700"],
            ["3단계: 전술", "가격결정·FTP", "ftp_rate, pricing_result, credit_spread", "~1,500"],
            ["4단계: 전략", "자본·한도·포트폴리오", "capital_position, stress_scenario, limit", "~130"],
            ["5단계: 기반", "모델·감사·집계", "model_registry, portfolio_summary", "~100"],
        ],
        [35, 35, 80, 40]
    )

    p.sub("2.2", "설계 원칙")
    p.bullet("정규화: 3NF 수준의 정규화를 기본으로 하되, 집계 테이블(portfolio_summary)은 성능을 위해 비정규화")
    p.bullet("참조 무결성: 모든 FK 제약조건을 schema.sql에서 명시적으로 정의")
    p.bullet("확장성: ALTER TABLE을 통한 점진적 스키마 확장 지원")
    p.bullet("재현성: INSERT OR REPLACE를 사용하여 스크립트 재실행 시 안전성 보장")
    p.bullet("일관성: 트랜잭션 기반 커밋으로 데이터 정합성 유지")

    # ══════════════════════════════════════
    # 3. 스키마 구조
    # ══════════════════════════════════════
    p.add_page()
    p.sec("3", "스키마 구조")

    p.sub("3.1", "마스터 테이블")
    p.subsub("customer (고객 마스터, 18 컬럼)")
    p.tbl(
        ["컬럼", "타입", "설명"],
        [
            ["customer_id", "TEXT PK", "고객 식별자 (CUS + 6자리)"],
            ["customer_name", "TEXT", "고객명"],
            ["biz_reg_no", "TEXT UNIQUE", "사업자등록번호"],
            ["industry_code", "TEXT FK", "산업분류코드"],
            ["size_category", "TEXT", "LARGE/MEDIUM/SMALL/SOHO"],
            ["region", "TEXT", "CAPITAL/DAEGU_GB/BUSAN_GN"],
            ["asset_size", "REAL", "자산규모 (억원)"],
            ["revenue_size", "REAL", "매출규모 (억원)"],
            ["employee_count", "INTEGER", "종업원 수"],
            ["is_listed", "INTEGER", "상장여부 (0/1)"],
            ["rm_id", "TEXT", "RM 담당자 ID"],
            ["branch_code", "TEXT", "영업점 코드"],
        ],
        [40, 35, 115]
    )

    p.subsub("industry_master (산업분류 마스터, 10건)")
    p.tbl(
        ["산업코드", "산업명", "대분류", "리스크 등급", "전망"],
        [
            ["IND001", "반도체", "제조", "LOW", "POSITIVE"],
            ["IND002", "IT서비스", "서비스", "LOW", "POSITIVE"],
            ["IND003", "자동차부품", "제조", "MEDIUM", "STABLE"],
            ["IND004", "철강·소재", "제조", "MEDIUM", "STABLE"],
            ["IND005", "에너지", "에너지", "MEDIUM", "STABLE"],
            ["IND006", "바이오·제약", "서비스", "HIGH", "POSITIVE"],
            ["IND007", "유통·소매", "서비스", "MEDIUM", "NEGATIVE"],
            ["IND008", "건설", "건설", "HIGH", "NEGATIVE"],
            ["IND009", "부동산PF", "금융", "HIGH", "NEGATIVE"],
            ["IND010", "무역", "서비스", "MEDIUM", "STABLE"],
        ],
        [25, 35, 25, 30, 30]
    )

    p.sub("3.2", "운영 테이블")
    p.subsub("facility (여신약정, 17 컬럼)")
    p.tbl(
        ["컬럼", "타입", "설명"],
        [
            ["facility_id", "TEXT PK", "여신 식별자"],
            ["application_id", "TEXT FK", "신청 ID"],
            ["customer_id", "TEXT FK", "고객 ID"],
            ["product_code", "TEXT FK", "상품코드"],
            ["approved_amount", "REAL", "승인금액 (억원)"],
            ["outstanding_amount", "REAL", "잔액 (억원)"],
            ["rate_type", "TEXT", "FIXED/FLOATING"],
            ["base_rate", "REAL", "기준금리 (3.5%)"],
            ["spread", "REAL", "가산금리"],
            ["final_rate", "REAL", "최종금리"],
            ["contract_date", "DATE", "약정일"],
            ["maturity_date", "DATE", "만기일"],
        ],
        [40, 30, 120]
    )

    p.subsub("risk_parameter (리스크 파라미터, 13 컬럼)")
    p.tbl(
        ["컬럼", "타입", "설명"],
        [
            ["ttc_pd", "REAL", "TTC 부도확률"],
            ["pit_pd", "REAL", "PIT 부도확률 (=TTC x 1.1)"],
            ["lgd", "REAL", "부도시손실률"],
            ["ead", "REAL", "부도시익스포저"],
            ["ccf", "REAL", "신용환산계수"],
            ["maturity_years", "REAL", "잔존만기 (년)"],
            ["rwa", "REAL", "위험가중자산"],
            ["expected_loss", "REAL", "예상손실"],
            ["unexpected_loss", "REAL", "비예상손실"],
            ["economic_capital", "REAL", "경제적 자본"],
        ],
        [40, 25, 125]
    )

    p.add_page()
    p.sub("3.3", "확장 테이블 (8개 기능)")
    p.tbl(
        ["기능", "테이블", "건수", "비고"],
        [
            ["EWS 고도화", "ews_indicator, ews_indicator_value", "~12,010", "200고객x6월x10지표"],
            ["", "supply_chain_relation", "500", "거래처 쌍"],
            ["", "ews_external_signal", "300", "외부 신호"],
            ["", "ews_composite_score", "1,000", "전 고객"],
            ["동적한도", "economic_cycle", "24", "월별 경기사이클"],
            ["", "dynamic_limit_rule", "6", "자동조정 규칙"],
            ["", "dynamic_limit_adjustment", "~10", "조정 이력"],
            ["고객수익성", "customer_profitability", "1,000", "전 고객 RBC"],
            ["", "cross_sell_opportunity", "200", "Cross-sell 기회"],
            ["담보관리", "collateral_valuation_history", "~6,600", "담보x6개월"],
            ["", "real_estate_index", "480", "8지역x5유형x12월"],
            ["", "collateral_alert", "~1,000", "경고 발생 건"],
            ["포트폴리오", "portfolio_optimization_run", "5", "5회 실행"],
            ["", "optimal_allocation", "40", "5회x8산업"],
            ["Workout", "workout_case", "30", "고액 여신"],
            ["", "recovery_scenario", "120", "케이스x4시나리오"],
            ["", "debt_restructuring", "~8", "조정 케이스"],
            ["ESG", "esg_assessment", "1,000", "전 고객"],
            ["", "green_finance", "50", "녹색금융"],
            ["ALM", "interest_rate_gap", "8", "만기 버킷별"],
            ["", "hedge_position", "10", "헤지 포지션"],
            ["", "hedge_recommendation", "~4", "헤지 제안"],
        ],
        [30, 60, 30, 70]
    )

    # ══════════════════════════════════════
    # 4. 기초 데이터 생성
    # ══════════════════════════════════════
    p.add_page()
    p.sec("4", "기초 데이터 생성 (seed_data.py)")

    p.sub("4.1", "고객 데이터 생성 (1,000건)")
    p.subsub("규모별 분포")
    p.tbl(
        ["규모", "비율", "건수", "자산규모 (억원)", "직원수"],
        [
            ["LARGE", "10%", "100", "5,000~50,000", "1,000~10,000"],
            ["MEDIUM", "25%", "250", "1,000~5,000", "300~1,000"],
            ["SMALL", "50%", "500", "100~1,000", "50~300"],
            ["SOHO", "15%", "150", "10~100", "5~50"],
        ],
        [30, 20, 25, 55, 60]
    )
    p.subsub("지역 분포 (iM뱅크 거점 고려)")
    p.tbl(
        ["지역", "가중치", "비율", "설명"],
        [
            ["CAPITAL (수도권)", "20", "~20%", "서울, 경기, 인천"],
            ["DAEGU_GB (대구경북)", "70", "~70%", "대구, 포항, 구미, 경주 (본점 소재)"],
            ["BUSAN_GN (부산경남)", "10", "~10%", "부산, 창원, 김해"],
        ],
        [50, 25, 25, 90]
    )
    p.txt(
        "iM뱅크의 영업 거점이 대구·경북 지역에 집중되어 있는 실제 영업 구조를 반영하여, "
        "대구경북 지역의 고객 비중을 70%로 설정하였다. 각 지역에 맞는 실제 주소를 할당한다."
    )

    p.sub("4.2", "여신 데이터 생성")
    p.subsub("기존 포트폴리오 (1,200건)")
    p.txt("고객당 1~2건의 여신이 배정되며, 규모별 금액 범위는 다음과 같다:")
    p.tbl(
        ["규모", "승인금액 범위", "활용률", "테너"],
        [
            ["LARGE", "100~1,000억원", "30~100%", "1~5년"],
            ["MEDIUM", "50~300억원", "30~100%", "1~5년"],
            ["SMALL", "10~100억원", "30~100%", "1~5년"],
            ["SOHO", "1~20억원", "30~100%", "1~5년"],
        ],
        [40, 50, 40, 60]
    )
    p.subsub("신규 심사 건 (10건, 데모용)")
    p.tbl(
        ["고객명", "산업", "규모", "금액", "등급", "전략"],
        [
            ["삼성반도체파트너", "반도체", "LARGE", "200억", "A+", "EXPAND"],
            ["현대차부품", "자동차", "MEDIUM", "100억", "A", "SELECTIVE"],
            ["코리아건설", "건설", "MEDIUM", "80억", "BBB+", "REDUCE"],
            ["강남PF개발", "부동산PF", "MEDIUM", "300억", "BBB-", "EXIT"],
            ["바이오텍", "바이오", "SMALL", "50억", "BB+", "EXPAND"],
            ["IT솔루션", "IT서비스", "SMALL", "25억", "A-", "EXPAND"],
            ["스타트업AI", "IT서비스", "SOHO", "15억", "B+", "SELECTIVE"],
        ],
        [35, 25, 25, 25, 20, 30]
    )

    p.add_page()
    p.sub("4.3", "신용등급 및 리스크 파라미터")
    p.subsub("지역별 등급 분포 가중치")
    p.txt(
        "지역과 규모의 조합에 따라 16단계 등급의 출현 확률을 차등 적용한다. "
        "수도권은 고등급 비중이 높고, 부산경남은 저등급 비중이 높다."
    )
    p.tbl(
        ["지역+규모", "AAA~A 비율", "BBB 비율", "BB~B 비율"],
        [
            ["수도권 LARGE", "~60%", "~25%", "~15%"],
            ["수도권 SMALL", "~35%", "~35%", "~30%"],
            ["대구경북 LARGE", "~38%", "~37%", "~25%"],
            ["대구경북 SMALL", "~25%", "~35%", "~40%"],
            ["부산경남 LARGE", "~25%", "~35%", "~40%"],
            ["부산경남 SOHO", "~2%", "~27%", "~71%"],
        ],
        [50, 45, 50, 45]
    )

    p.subsub("RWA 및 EL 계산 로직")
    p.formula([
        "rwa = outstanding x (0.5 + pd x 10) x (lgd / 0.45)",
        "el = pd x lgd x outstanding",
        "ec = rwa x 0.08",
        "",
        "revenue = outstanding x final_rate",
        "cost = outstanding x 0.048",
        "raroc = (revenue - cost - el) / ec",
    ])

    p.sub("4.4", "담보 데이터 생성 (910건)")
    p.txt(
        "담보가 있는 여신(collateral_type != 'NONE')에 대해 담보 레코드를 생성한다. "
        "담보 시가는 원래 가치의 85~110% 범위에서 변동하며, LTV를 산출한다."
    )
    p.formula([
        "current_value = original_value x uniform(0.85, 1.1)",
        "ltv = outstanding / current_value",
    ])

    p.sub("4.5", "금리 산출 로직")
    p.formula([
        "base_rate = 3.5% (고정)",
        "credit_spread = pd x lgd x 1.5",
        "strategy_adj = uniform(-0.5%, +1.0%)",
        "final_rate = base_rate + credit_spread + strategy_adj + 1.5%",
    ])
    p.txt("최종 금리 범위: 3.5% ~ 8.0%+, 신용등급과 전략에 따라 결정된다.")

    p.sub("4.6", "자본 데이터 (27건)")
    p.txt("iM뱅크 2024년말 공시 데이터를 기준으로 생성한다:")
    p.tbl(
        ["항목", "금액/비율"],
        [
            ["CET1 자본", "6조 8,740억원"],
            ["AT1 자본", "1,440억원"],
            ["Tier2 자본", "9,640억원"],
            ["총 자본", "7조 9,820억원"],
            ["신용위험 RWA", "43.2조원 (90%)"],
            ["시장위험 RWA", "1.2조원"],
            ["운영위험 RWA", "3.6조원"],
            ["총 RWA", "48조원"],
            ["BIS 비율", "16.63%"],
            ["CET1 비율", "14.32%"],
        ],
        [60, 130]
    )
    p.txt("월별 26개월 이력은 기준값에 +/-3% 변동을 부여하여 시계열을 생성한다.")

    p.sub("4.7", "포트폴리오 요약 (15건)")
    p.txt(
        "portfolio_summary는 고정값이 아닌, 실제 DB 데이터를 동적으로 집계하여 생성한다. "
        "산업별 10건 + 등급군별 5건으로 구성된다."
    )
    p.formula([
        "INSERT INTO portfolio_summary",
        "  SELECT industry_code,",
        "    SUM(facility.outstanding_amount),",
        "    SUM(risk_parameter.rwa),",
        "    SUM(risk_parameter.expected_loss),",
        "    AVG(risk_parameter.pit_pd),",
        "    AVG(risk_parameter.lgd)",
        "  FROM customer JOIN facility JOIN risk_parameter",
        "  GROUP BY industry_code",
    ])

    # ══════════════════════════════════════
    # 5. 확장 데이터 생성
    # ══════════════════════════════════════
    p.add_page()
    p.sec("5", "확장 데이터 생성 (generate_extension_data.py)")

    p.sub("5.1", "EWS 고도화")
    p.subsub("선행지표 정의 (10개)")
    p.tbl(
        ["ID", "지표명", "유형", "Warning 임계", "Critical 임계"],
        [
            ["001", "매출채권회전일", "LEAD", "60일", "90일"],
            ["002", "재고자산회전율", "LEAD", "4회", "2회"],
            ["003", "현금흐름커버리지", "COIN", "1.5", "0.8"],
            ["004", "이자보상배율", "COIN", "3.0", "1.5"],
            ["005", "순운전자본비율", "LEAD", "0.1", "-0.05"],
            ["006", "부채비율변화", "LEAD", "15%", "30%"],
            ["007", "공급망리스크", "LEAD", "0.02", "0.05"],
            ["008", "외부등급변화", "COIN", "-1", "-2"],
            ["009", "뉴스감성지수", "LEAD", "-0.3", "-0.6"],
            ["010", "연체발생여부", "LAG", "0", "1"],
        ],
        [20, 40, 25, 40, 40]
    )
    p.txt(
        "지표값은 200명 고객 x 6개월 x 10지표 = 12,000건이 생성된다. "
        "각 지표는 지정된 범위 내에서 균일 분포로 생성되며, 신용등급에 따라 "
        "위험 프로파일이 조정된다."
    )

    p.subsub("공급망 관계 (500건)")
    p.txt(
        "고객 간 거래 관계를 SUPPLIER/BUYER/BOTH 유형으로 생성한다. "
        "의존도(dependency_score: 0.1~0.9), 연간 거래규모(100M~50B원), "
        "매출 비중(1~30%)을 부여한다."
    )

    p.subsub("종합 EWS 점수 (1,000건)")
    p.formula([
        "composite = financial x 0.4 + operational x 0.2",
        "          + external x 0.2 + supply_chain x 0.2",
        "",
        "risk_level: LOW(>=70) / MEDIUM(50-70) / HIGH(30-50) / CRITICAL(<30)",
    ])

    p.sub("5.2", "동적 한도 관리")
    p.subsub("경기 사이클 (24개월)")
    p.txt(
        "6개월 주기로 EXPANSION -> PEAK -> CONTRACTION -> TROUGH 순환. "
        "GDP(2.5%+/-1%), 실업률(3.5%+/-0.5%), 기준금리(3.5%+/-0.3%) 등을 연동 생성한다."
    )
    p.subsub("자동 조정 규칙 (6개)")
    p.tbl(
        ["규칙", "조건", "조정"],
        [
            ["1", "경기 침체기 고위험 업종", "-15%"],
            ["2", "경기 확장기 성장 업종", "+10%"],
            ["3", "업종 HHI > 25%", "신규 동결"],
            ["4", "업종 부도율 > 3%", "-20%"],
            ["5", "금리 급등 (+100bp 이상)", "-10%"],
            ["6", "BB 이하 부도율 > 5%", "-25%"],
        ],
        [20, 95, 75]
    )

    p.add_page()
    p.sub("5.3", "고객 수익성 (RBC)")
    p.txt("전 고객(1,000건)에 대해 수익성 데이터를 생성한다:")
    p.formula([
        "loan_profit = loan_revenue - loan_cost - loan_el - loan_capital_cost",
        "total_profit = loan_profit + deposit_profit + fee_profit + fx_profit",
        "ec = total_loan x uniform(6%, 12%)",
        "RAROC = total_profit / ec",
        "",
        "CLV_score: uniform(30, 100)",
        "retention_prob: uniform(0.6, 0.98)",
        "churn_risk = 1 - retention_prob + noise",
    ])
    p.txt(
        "Cross-sell 기회(200건)는 확률 기반으로 상태(WON/LOST/DECLINED 등)를 "
        "결정하며, priority_score = probability x expected_revenue / 10M으로 우선순위를 산출한다."
    )

    p.sub("5.4", "담보 모니터링")
    p.subsub("담보 유형별 인정비율")
    p.tbl(
        ["유형", "세부", "인정비율"],
        [
            ["부동산", "아파트", "70~80%"],
            ["", "오피스", "60~70%"],
            ["", "상가", "55~65%"],
            ["", "토지", "50~65%"],
            ["", "공장", "45~60%"],
            ["예금", "정기예금", "95~100%"],
            ["", "적금", "90~95%"],
            ["유가증권", "상장주식", "55~65%"],
            ["", "채권", "80~90%"],
            ["동산", "기계설비", "40~55%"],
            ["", "재고자산", "30~45%"],
            ["보증", "신보/기보/보험", "80~95%"],
            ["매출채권", "매출채권/어음", "60~80%"],
            ["IP권", "특허권", "20~40%"],
            ["", "상표권", "15~35%"],
        ],
        [35, 60, 95]
    )
    p.subsub("담보 가치 이력 (담보 x 6개월)")
    p.txt("담보 유형별 변동성을 반영한 시계열 가치 이력을 생성한다:")
    p.tbl(
        ["유형", "변동 범위", "특성"],
        [
            ["부동산", "-10% ~ +5%", "가격 하방 변동 큼"],
            ["예금", "-0.5% ~ +0.5%", "거의 변동 없음"],
            ["유가증권", "-15% ~ +10%", "변동성 가장 높음"],
            ["동산", "-8% ~ +2%", "감가 위주"],
            ["보증", "-1% ~ +1%", "거의 변동 없음"],
            ["매출채권", "-5% ~ +2%", "회수/부실 변동"],
            ["IP권", "-12% ~ +8%", "변동성 큼"],
        ],
        [35, 50, 105]
    )
    p.txt("경고 조건: 가치 변동 < -5% 또는 LTV > 80% 시 alert_triggered = 1")

    p.add_page()
    p.sub("5.5", "포트폴리오 최적화 (5회 실행)")
    p.txt(
        "3가지 최적화 유형(RAROC_MAX, RWA_MIN, RISK_PARITY)으로 실행하며, "
        "현재 대비 +/-20% 범위에서 산업별 배분을 조정한다. "
        "제약조건: BIS >= 11%, HHI <= 25%, 단일 max 10%."
    )

    p.sub("5.6", "Workout (30건)")
    p.txt("단일 고객 익스포저 > 100억원인 30건을 추출하여 Workout 케이스를 생성한다.")
    p.subsub("회수 시나리오 (케이스당 4개 = 120건)")
    p.formula([
        "NPV = recovery_amount / (1.08^(timeline/12))",
        "",
        "정상화: 85% 회수, 24개월",
        "채무조정: 65% 회수, 36개월",
        "자산매각: 50% 회수, 12개월",
        "법적회수: 35% 회수, 48개월",
    ])

    p.sub("5.7", "ESG 리스크 (1,000건)")
    p.txt("업종별 기본 편향을 반영하여 E/S/G 점수를 생성한다:")
    p.tbl(
        ["업종 유형", "E 편향", "S 편향", "G 편향"],
        [
            ["제조", "-10", "0", "+5"],
            ["서비스", "+10", "+5", "+5"],
            ["건설", "-15", "-5", "0"],
            ["부동산", "-5", "0", "-5"],
            ["금융", "+5", "0", "+10"],
        ],
        [50, 45, 50, 45]
    )
    p.formula([
        "ESG_score = E x 0.35 + S x 0.30 + G x 0.35",
        "등급: A(>=80), B(65-79), C(50-64), D(35-49), E(<35)",
    ])

    p.sub("5.8", "ALM (금리리스크)")
    p.txt(
        "자산 50조원, 부채 45조원 기준으로 8개 만기 버킷(1M~5Y+)별 금리갭을 생성한다. "
        "7개 금리 시나리오(평행상승/하락, 스티프닝, 플래트닝, 트위스트)에 대해 "
        "NIM 및 EVE 민감도를 산출한다. 헤지 포지션 10건과 제안 3~4건도 생성한다."
    )

    # ══════════════════════════════════════
    # 6. 지역 차등화 설계
    # ══════════════════════════════════════
    p.add_page()
    p.sec("6", "지역 차등화 설계")
    p.txt(
        "iM뱅크의 실제 영업 구조를 반영하여 수도권/대구경북/부산경남 3개 지역별로 "
        "신용등급 분포, LGD, 담보 인정비율, RAROC 등 주요 지표를 차등 적용하였다."
    )
    p.sub("6.1", "등급 분포 차등")
    p.txt(
        "수도권은 대기업 본사와 우량 고객이 집중되어 고등급 비중이 높고, "
        "부산경남은 중소기업 중심으로 저등급 비중이 높다. 대구경북은 iM뱅크 본점 "
        "소재지로 다양한 고객 구성을 가진다."
    )

    p.sub("6.2", "LGD 차등")
    p.txt(
        "지역별 부동산 가격과 회수 환경의 차이를 반영한다. 수도권은 담보 가치가 높고 "
        "처분이 용이하여 LGD가 낮고, 부산경남은 상대적으로 LGD가 높다."
    )
    p.tbl(
        ["구분", "수도권", "대구경북", "부산경남"],
        [
            ["담보부 LGD", "18~32%", "25~40%", "30~48%"],
            ["무담보 LGD", "38~50%", "45~58%", "50~65%"],
            ["결과 RAROC", "14.13%", "10.96%", "8.34%"],
        ],
        [40, 50, 50, 50]
    )

    # ══════════════════════════════════════
    # 7. 비즈니스 룰 내재화
    # ══════════════════════════════════════
    p.sec("7", "비즈니스 룰 내재화")
    p.txt(
        "데이터 생성 시 다음의 비즈니스 룰을 데이터에 내재화하여, "
        "시스템 시연 시 실제 은행 업무와 유사한 결과를 생성하도록 한다."
    )
    p.tbl(
        ["항목", "로직", "효과"],
        [
            ["신용평가", "규모+지역별 등급분포 -> PD 매핑", "현실적 등급 분포"],
            ["금리책정", "base(3.5%) + credit_spread(pd x lgd x 1.5) + 조정", "위험 반비례 금리"],
            ["RAROC", "(수익-비용-EL)/EC", "수익성 차별화"],
            ["포트폴리오", "산업/등급 기반 DB 집계", "동적 요약 반영"],
            ["EWS 점수", "4채널 가중합", "다차원 위험 평가"],
            ["동적한도", "경기사이클+부도율+HHI 기반", "자동 한도 조정"],
            ["담보 LTV", "recognized = market x ratio", "담보유형별 차등"],
            ["ESG 영향", "ESG score -> PD/금리 가감", "ESG 반영 리스크"],
        ],
        [30, 80, 80]
    )

    # ══════════════════════════════════════
    # 8. 데이터 품질 및 정합성
    # ══════════════════════════════════════
    p.add_page()
    p.sec("8", "데이터 품질 및 정합성")
    p.sub("8.1", "제약조건 관리")
    p.bullet("PRIMARY KEY: 모든 테이블에 고유 식별자 (TEXT PK)")
    p.bullet("FOREIGN KEY: 주요 참조 관계 명시 (customer_id, application_id 등)")
    p.bullet("UNIQUE: 사업자등록번호(biz_reg_no) 중복 방지")
    p.bullet("NOT NULL: 필수 필드에 NULL 제약 적용")

    p.sub("8.2", "데이터 일관성")
    p.bullet("포트폴리오 요약은 DB 실제 데이터에서 동적 집계 (INSERT ... SELECT ... GROUP BY)")
    p.bullet("PIT_PD = TTC_PD x 1.1 관계 유지")
    p.bullet("RWA, EL 등 파생 값은 원본 데이터에서 재계산")
    p.bullet("담보 확장: ALTER TABLE로 점진적 컬럼 추가 후 기존 데이터 갱신")

    p.sub("8.3", "재현성 및 안전성")
    p.bullet("INSERT OR REPLACE: 스크립트 재실행 시 중복 방지")
    p.bullet("트랜잭션 기반 커밋: 데이터 정합성 보장")
    p.bullet("UUID 생성: uuid4()[:8].upper() - 충돌 시 재실행 권장")
    p.bullet("결정적 ID 형식: EWS 지표 등은 규칙 기반 ID로 충돌 방지")

    p.sub("8.4", "데이터 생성 순서 및 의존성")
    p.txt("데이터 생성은 참조 무결성을 보장하는 순서로 수행된다:")
    p.formula([
        "1. schema.sql -> DB 스키마 생성",
        "2. industry_master, product_master -> 마스터 데이터",
        "3. customer (1,000건) -> 고객 생성",
        "4. borrower_group -> 차주 그룹",
        "5. loan_application + facility + credit_rating + risk_parameter -> 여신 생성",
        "6. collateral -> 담보 생성 (facility 참조)",
        "7. capital_position -> 자본 데이터",
        "8. portfolio_summary -> DB 집계 (facility, risk_parameter 참조)",
        "9. model_registry + model_version -> 모델 데이터",
        "10. extension data -> EWS, 한도, 수익성, 담보, Workout, ESG, ALM",
    ])

    # ══════════════════════════════════════
    # 9. 데이터 규모 및 분포 요약
    # ══════════════════════════════════════
    p.add_page()
    p.sec("9", "데이터 규모 및 분포 요약")

    p.sub("9.1", "전체 데이터 규모")
    p.tbl(
        ["카테고리", "테이블 수", "총 레코드 수", "주요 테이블"],
        [
            ["마스터", "5", "~1,020", "customer(1,000)"],
            ["운영", "7", "~5,700", "facility(1,200), risk_parameter(1,210)"],
            ["전술", "6", "~1,500", "pricing_result(1,210)"],
            ["전략", "9", "~130", "capital_position(27)"],
            ["기반", "8", "~100", "model_performance_log(60)"],
            ["EWS 확장", "6", "~13,800", "ews_indicator_value(12,000)"],
            ["기타 확장", "8", "~10,000+", "collateral_valuation_history(6,600)"],
            ["합계", "49", "~35,000+", ""],
        ],
        [35, 25, 35, 95]
    )

    p.sub("9.2", "통계적 분포 특성")
    p.tbl(
        ["항목", "분포 유형", "설명"],
        [
            ["자산규모", "균일분포 (규모별 범위)", "LARGE: 5K~50K, SOHO: 10~100"],
            ["신용등급", "가중 확률 분포", "지역 x 규모별 16등급 가중치"],
            ["LGD", "균일분포 (지역 x 담보별)", "18%~65% 범위"],
            ["금리", "계산 기반", "base + credit_spread + adj"],
            ["담보 가치 변동", "균일분포 (유형별)", "-15%~+10% 범위"],
            ["EWS 지표", "균일분포 (지표별)", "임계값 기반 신호 판정"],
            ["ESG 점수", "정규분포 + 업종 편향", "기본 50~65 + 편향 + 노이즈"],
            ["자본비율", "기준값 +/-3% 변동", "월별 시계열"],
        ],
        [40, 55, 95]
    )

    # ══════════════════════════════════════
    # 10. 한계 및 향후 과제
    # ══════════════════════════════════════
    p.add_page()
    p.sec("10", "한계 및 향후 과제")

    p.sub("10.1", "데이터 한계")
    for l in [
        "합성 데이터의 한계: 실제 은행 데이터의 복잡한 상관 구조와 꼬리 분포를 완전히 재현하지 못함.",
        "균일 분포 의존: 대부분의 연속형 변수가 균일 분포로 생성되어, 실제 데이터의 정규/로그정규 분포 특성 미반영.",
        "시계열 단순성: 자기상관(autocorrelation)과 계절성(seasonality)이 충분히 반영되지 않음.",
        "상관 구조 부재: 변수 간 상관관계(예: GDP 하락 시 PD 상승)가 체계적으로 모델링되지 않음.",
        "UUID 충돌 위험: uuid4()[:8] 사용으로 대규모 생성 시 충돌 가능성 존재.",
        "정적 스냅샷: 시간에 따른 데이터 진화(portfolio aging, rating migration)가 제한적.",
    ]:
        p.bullet(l)

    p.sub("10.2", "향후 과제")
    for f in [
        "Copula 기반 상관 구조: 변수 간 비선형 의존성을 모델링하는 Copula 함수 적용",
        "시계열 모형: ARIMA, GARCH 등을 활용한 현실적 시계열 데이터 생성",
        "Rating Migration Matrix: 실제 등급전이행렬 기반의 동적 신용등급 변화 시뮬레이션",
        "스트레스 시나리오 연동: 거시경제 변수와 개별 리스크 파라미터의 통계적 연계",
        "대규모 데이터셋: 10만+ 고객 규모의 성능 테스트 데이터 생성",
        "데이터 마스킹: 실제 은행 데이터를 익명화하여 활용하는 방안 연구",
    ]:
        p.bullet(f)

    # ── References ──
    p.ln(8)
    p.sub("", "참고문헌")
    refs = [
        '[1] BCBS (2006). "International Convergence of Capital Measurement and Capital Standards." Basel Committee.',
        '[2] Patki, N. et al. (2016). "The Synthetic Data Vault." IEEE DSAA.',
        '[3] Li, J. et al. (2014). "Synthetic Data Generation for Financial Applications." Journal of Banking & Finance.',
        '[4] iM뱅크 (2024). "2024년 경영공시자료." iM금융그룹.',
        '[5] 금융감독원 (2023). "은행업 감독 규정." 금융감독원.',
        '[6] BIS (2019). "The Basel Framework." Bank for International Settlements.',
    ]
    p.set_font("body", "", 9)
    for ref in refs:
        p.set_x(15)
        p.multi_cell(175, 5, ref)
        p.ln(1)

    # 스크립트는 tools/ 로 옮겼지만 산출물은 종전대로 리포 루트에 둔다
    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(_ROOT, "CLMS_Data_Paper.pdf")
    p.output(out)
    print(f"PDF saved: {out} ({p.page_no()} pages)")


if __name__ == "__main__":
    build()
