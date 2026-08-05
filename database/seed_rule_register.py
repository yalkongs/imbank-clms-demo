#!/usr/bin/env python3
"""
규정 레지스터 시드 - 시스템에 하드코딩돼 있던 산식·임계의 근거를 등록한다.
각 규칙은 domain·근거 법령·버전·효력기간·파라미터·적용 위치를 가진다. 멱등.
"""
import json
import sqlite3
from pathlib import Path

DB = str(Path(__file__).parent / "imbank_demo.db")

RULES = [
    ("RULE_PROV_MIN", "CLASSIFICATION", "자산건전성 분류별 최저적립률",
     "은행업감독규정 §29 · 시행세칙 별표3", "2026-01 개정", "2026-01-01", None,
     {"NORMAL": 0.0085, "PRECAUTIONARY": 0.07, "SUBSTANDARD": 0.20,
      "DOUBTFUL": 0.50, "LOSS": 1.00},
     "calculations.py · 자산건전성 분류 · 업무보고서"),
    ("RULE_DPD_BOUND", "CLASSIFICATION", "연체기간 분류 경계",
     "은행업감독업무시행세칙 별표3", "현행", "2020-01-01", None,
     {"PRECAUTIONARY": 30, "SUBSTANDARD": 90, "LOSS": 365},
     "calculations.py · 연체 관리"),
    ("RULE_EWS_THRESH", "EWS", "EWS 건전성 강등·SICR 임계",
     "내부 조기경보 운영기준", "2026-01 v2", "2026-01-01", None,
     {"PRECAUTIONARY_BELOW": 35, "SICR_BELOW": 55},
     "calculations.py · EWS 조치 · 3체계 대사"),
    ("RULE_LIMIT_GROUP", "LIMIT", "동일차주(그룹) 신용공여 한도",
     "은행법 §35①", "현행", "2010-01-01", None,
     {"ratio": 0.25}, "group_credit · 동일차주 화면"),
    ("RULE_LIMIT_SINGLE", "LIMIT", "동일한 개인·법인 신용공여 한도",
     "은행법 §35③", "현행", "2010-01-01", None,
     {"ratio": 0.20}, "group_credit · 법정 3한도"),
    ("RULE_LIMIT_LARGE", "LIMIT", "거액신용공여 총액 한도",
     "은행법 §35④", "현행", "2010-01-01", None,
     {"trigger_ratio": 0.10, "total_ratio": 5.0}, "group_credit · 법정 3한도"),
    ("RULE_CCF", "LIMIT", "신용공여 신용환산율(CCF) 근사",
     "은행업감독규정 별표2 (PoC 근사)", "근사 v1", "2026-01-01", None,
     {"ON_LOAN": 1.0, "OFF_UNDRAWN": 0.4, "OFF_GUARANTEE": 1.0},
     "credit_exposure_ledger 시드"),
    ("RULE_RATE_SLA", "RATE", "금리인하요구 통지 기한",
     "은행법 시행령 §18-4", "현행", "2019-06-12", None,
     {"biz_days": 10, "exclude_supplement_period": True},
     "rate_reduction · 금리인하요구권 화면"),
    ("RULE_RAROC_HURDLE", "CAPITAL", "RAROC 허들레이트",
     "내부 자본관리지침", "2026-01 v3.1", "2026-01-01", None,
     {"hurdle_pct": 15.0}, "대시보드 · 포트폴리오 맵 · 스트레스"),
    ("RULE_BIS_MIN", "CAPITAL", "최소 자본비율 (규제)",
     "은행업감독규정 §26 (바젤III)", "현행", "2013-12-01", None,
     {"bis": 10.5, "tier1": 8.5, "cet1": 7.0}, "자본관리 · 스트레스 테스트"),
    ("RULE_PF_GAP", "PF", "PF 공정-분양 괴리 경보 기준",
     "내부 PF 취급기준 §2", "2026-01", "2026-01-01", None,
     {"gap_pp": 30}, "PF 사업장 · 업무보고서"),
    ("RULE_PF_EQUITY", "PF", "PF 자기자본비율 연동 (2027 제도 예정)",
     "금융위 PF 제도개선 로드맵", "예정(시뮬레이션)", "2027-01-01", None,
     {"bands": "equity<10%: RW 2.0 ... equity>=20%: RW 0.8"},
     "PF 규제 시뮬레이션 (시행 전 - 화면은 시나리오로만)"),
    ("RULE_SCB", "CAPITAL", "스트레스완충자본(SCB) 산식",
     "은행업감독규정 (경기대응완충자본 연계) - PoC 근사", "근사 v1", "2026-01-01", None,
     {"formula": "min(max(BIS - SEVERE_BIS, 0), 2.5)"},
     "스트레스 테스트"),
    ("RULE_KOKR_HOLIDAY", "RATE", "은행 영업일 캘린더 (2026 공휴일)",
     "관공서의 공휴일에 관한 규정", "2026", "2026-01-01", "2026-12-31",
     {"holidays": ["2026-01-01", "2026-02-16", "2026-02-17", "2026-02-18",
                    "2026-03-01", "2026-03-02", "2026-05-05", "2026-05-24", "2026-05-25",
                    "2026-06-06", "2026-08-15", "2026-08-17", "2026-09-24", "2026-09-25",
                    "2026-09-26", "2026-10-03", "2026-10-05", "2026-10-09", "2026-12-25"]},
     "rate_reduction SLA 계산"),
    ("RULE_INCL_TARGET", "LIMIT", "포용금융 공급 목표",
     "시중은행 전환 인가 조건 (내부 목표)", "2026", "2026-01-01", None,
     {"mid_credit_share": 20.0, "soho_share": 12.0}, "포용금융 이행 화면"),
]


con = sqlite3.connect(DB)
cur = con.cursor()
for r in RULES:
    cur.execute("""
        INSERT OR REPLACE INTO rule_register
        (rule_id, domain, name, basis, version, valid_from, valid_to, params_json, applied_in)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (r[0], r[1], r[2], r[3], r[4], r[5], r[6], json.dumps(r[7], ensure_ascii=False), r[8]))
con.commit()
cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
print(f"규정 레지스터 {len(RULES)}건")
