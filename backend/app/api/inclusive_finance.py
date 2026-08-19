"""
포용금융 이행 현황 API
======================
iM뱅크는 2024.5 시중은행 전환 인가 시 "중신용 중소기업·개인사업자 여신 확대"를
공언했다. 이 모듈은 그 이행 실적을 관리한다 - 핵심은 공급(얼마나 늘렸나)과
건전성(늘린 것의 품질)을 한 화면에서 보는 것이다. 기업 연체율이 1%대인 상황에서
중신용 공급만 밀어붙이면 부실로 돌아오므로, 두 지표는 반드시 같이 봐야 한다.

세그먼트 정의
  · 중신용 기업  : 최신 신용등급 BBB+ 이하 (4등급 이하 상당)
  · 개인사업자   : customer.size_category = 'SOHO'
  (두 세그먼트는 겹칠 수 있다 - SOHO 이면서 중신용인 차주는 양쪽에 집계)
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..core.config import AS_OF_MONTH, as_of_months
from ..core.auth import get_current_user, User
from ..core.audit import record_audit

router = APIRouter(prefix="/api/inclusive", tags=["Inclusive Finance"])

# 중신용 등급 경계 - BBB+ 이하를 중신용으로 본다
MID_CREDIT_GRADES = ("BBB+", "BBB", "BBB-", "BB+", "BB", "BB-", "B+", "B", "B-")

# 인가 시 공언 목표 (사용자 지정 목표치, 2026-08 조정)
TARGETS = {
    "mid_credit_share": 20.0,   # 중신용 여신 비중 목표 (%)
    "soho_share": 12.0,         # 개인사업자 여신 비중 목표 (%)
}

# 세그먼트 조건 SQL 조각 (facility f + customer c + 최신 등급 g 조인 전제)
_GRADE_LIST = ",".join(f"'{g}'" for g in MID_CREDIT_GRADES)
SEGMENT_COND = {
    "MID_CREDIT": f"g.final_grade IN ({_GRADE_LIST})",
    "SOHO": "c.size_category = 'SOHO'",
}

# 최신 등급 서브쿼리 (고객당 1행)
LATEST_GRADE_JOIN = """
    LEFT JOIN (
        SELECT customer_id, final_grade,
               ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY rating_date DESC) rn
        FROM credit_rating_result
    ) g ON c.customer_id = g.customer_id AND g.rn = 1
"""


def _segment_stats(db: Session, cond: str) -> dict:
    """세그먼트의 잔액·건수·연체율·NPL 을 실제 여신에서 집계한다."""
    row = db.execute(text(f"""
        SELECT
            COUNT(*)                                                    AS cnt,
            COALESCE(SUM(f.outstanding_amount), 0)                      AS exposure,
            COALESCE(SUM(CASE WHEN f.dpd >= 30
                              THEN f.outstanding_amount END), 0)        AS delinquent_exp,
            COALESCE(SUM(CASE WHEN f.classification IN
                              ('SUBSTANDARD','DOUBTFUL','LOSS')
                              THEN f.outstanding_amount END), 0)        AS npl_exp
        FROM facility f
        JOIN customer c ON f.customer_id = c.customer_id
        {LATEST_GRADE_JOIN}
        WHERE f.status = 'ACTIVE' AND ({cond})
    """)).fetchone()
    cnt, exposure, delinquent, npl = row
    return {
        "count": cnt,
        "exposure": round(exposure, 2),
        "delinquency_rate": round(delinquent / exposure * 100, 3) if exposure else 0,
        "npl_ratio": round(npl / exposure * 100, 3) if exposure else 0,
    }


@router.get("/summary")
def get_inclusive_summary(db: Session = Depends(get_db)):
    """공급 실적 vs 목표 + 세그먼트 건전성 요약"""
    total = db.execute(text("""
        SELECT COALESCE(SUM(outstanding_amount), 0),
               COALESCE(SUM(CASE WHEN dpd >= 30 THEN outstanding_amount END), 0)
        FROM facility WHERE status = 'ACTIVE'
    """)).fetchone()
    total_exposure, total_delinquent = float(total[0]), float(total[1])

    segments = {}
    for key, cond in SEGMENT_COND.items():
        s = _segment_stats(db, cond)
        share = round(s["exposure"] / total_exposure * 100, 2) if total_exposure else 0
        target = TARGETS["mid_credit_share"] if key == "MID_CREDIT" else TARGETS["soho_share"]
        segments[key] = {
            **s,
            "share": share,
            "target_share": target,
            "achievement": round(share / target * 100, 1) if target else 0,
        }

    return {
        "as_of_month": AS_OF_MONTH,
        "total_exposure": round(total_exposure, 2),
        "total_delinquency_rate": round(total_delinquent / total_exposure * 100, 3)
                                  if total_exposure else 0,
        "segments": segments,
        "note": "목표 비중은 시중은행 전환 인가 시 공언 기준의 PoC 가정치",
    }


@router.get("/trend")
def get_supply_trend(months: int = Query(12, le=24), db: Session = Depends(get_db)):
    """세그먼트별 월별 신규취급액 추이 (contract_date 기준)"""
    month_list = as_of_months(months)
    out = []
    for ym in month_list:
        row = {"month": ym}
        for key, cond in SEGMENT_COND.items():
            v = db.execute(text(f"""
                SELECT COALESCE(SUM(f.approved_amount), 0)
                FROM facility f
                JOIN customer c ON f.customer_id = c.customer_id
                {LATEST_GRADE_JOIN}
                WHERE substr(f.contract_date, 1, 7) = :ym AND ({cond})
            """), {"ym": ym}).fetchone()[0]
            row[key.lower()] = round(float(v or 0), 2)
        total = db.execute(text("""
            SELECT COALESCE(SUM(approved_amount), 0) FROM facility
            WHERE substr(contract_date, 1, 7) = :ym
        """), {"ym": ym}).fetchone()[0]
        row["total"] = round(float(total or 0), 2)
        out.append(row)
    return out


@router.get("/breakdown")
def get_segment_breakdown(db: Session = Depends(get_db)):
    """중신용 세그먼트의 등급별·지역별 분포 (어디서 얼마나 공급되는가)"""
    by_grade = db.execute(text(f"""
        SELECT g.final_grade, COUNT(*), COALESCE(SUM(f.outstanding_amount), 0)
        FROM facility f
        JOIN customer c ON f.customer_id = c.customer_id
        {LATEST_GRADE_JOIN}
        WHERE f.status = 'ACTIVE' AND g.final_grade IN ({_GRADE_LIST})
        GROUP BY g.final_grade ORDER BY 3 DESC
    """)).fetchall()

    by_region = db.execute(text(f"""
        SELECT c.region, COUNT(*), COALESCE(SUM(f.outstanding_amount), 0),
               COALESCE(SUM(CASE WHEN f.dpd >= 30 THEN f.outstanding_amount END), 0)
        FROM facility f
        JOIN customer c ON f.customer_id = c.customer_id
        {LATEST_GRADE_JOIN}
        WHERE f.status = 'ACTIVE'
          AND (({SEGMENT_COND['MID_CREDIT']}) OR ({SEGMENT_COND['SOHO']}))
        GROUP BY c.region ORDER BY 3 DESC
    """)).fetchall()

    region_labels = {"CAPITAL": "수도권", "DAEGU_GB": "대구경북", "BUSAN_GN": "부산경남"}
    return {
        "by_grade": [
            {"grade": r[0], "count": r[1], "exposure": round(r[2], 2)} for r in by_grade
        ],
        "by_region": [
            {
                "region": r[0],
                "region_label": region_labels.get(r[0], r[0]),
                "count": r[1],
                "exposure": round(r[2], 2),
                "delinquency_rate": round(r[3] / r[2] * 100, 3) if r[2] else 0,
            }
            for r in by_region
        ],
    }


# ============================================================
# P4: 개인사업자·소상공인 건전성 세그먼트 심화
# (docs/IMPROVEMENT_RESEARCH_2026-08-19.md - 규제: 개인사업자 연체율 상승,
#  새출발기금 연장·심사강화, 새도약기금 출범 / iM: 중기·소상공인 비중 87.1%)
# ============================================================

# 새출발기금 요건 근사 (제도 기준 - 화면 표기용)
SAECHULBAL = {
    "debt_cap_eok": 15.0,          # 담보 10억 + 무담보 5억
    "npl_dpd": 90,                 # 부실차주: 90일 이상 연체
    "risk_dpd_min": 30,            # 부실우려차주: 30~89일 연체
    "deadline": "2026-12",         # 신청 기한 (연장)
    "note": "사업영위 2020.4~2025.6 · 2026.6 재산심사 강화(가상자산·비상장주식 포함)",
}


@router.get("/soho/dashboard")
def get_soho_dashboard(db: Session = Depends(get_db)):
    """개인사업자(SOHO) 건전성 심화 - 업종×지역 히트맵 + DPD 버킷"""
    heat = db.execute(text("""
        SELECT c.industry_name, c.region,
               COUNT(*), SUM(f.outstanding_amount),
               SUM(CASE WHEN f.dpd > 0 THEN f.outstanding_amount ELSE 0 END)
        FROM facility f
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.status IN ('ACTIVE','FROZEN') AND c.size_category = 'SOHO'
        GROUP BY c.industry_name, c.region
    """)).fetchall()

    by_industry: dict = {}
    for ind, region, cnt, exp, ov in heat:
        cell = by_industry.setdefault(ind, {"industry": ind, "total_eok": 0.0, "cells": {}})
        e = float(exp or 0)
        cell["total_eok"] += round(e / 1e8, 1)
        cell["cells"][region] = {
            "count": cnt,
            "exposure_eok": round(e / 1e8, 1),
            "delinquency_rate": round(float(ov or 0) / e * 100, 2) if e else 0,
        }
    matrix = sorted(by_industry.values(), key=lambda x: -x["total_eok"])

    buckets = db.execute(text("""
        SELECT CASE WHEN f.dpd = 0 THEN '정상'
                    WHEN f.dpd < 30 THEN '1~29일'
                    WHEN f.dpd < 60 THEN '30~59일'
                    WHEN f.dpd < 90 THEN '60~89일'
                    ELSE '90일+' END AS bucket,
               COUNT(*), SUM(f.outstanding_amount)
        FROM facility f
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.status IN ('ACTIVE','FROZEN') AND c.size_category = 'SOHO'
        GROUP BY bucket
    """)).fetchall()
    order = ['정상', '1~29일', '30~59일', '60~89일', '90일+']
    bucket_map = {r[0]: r for r in buckets}

    return {
        "benchmark": {
            "industry_soho_delinquency": 0.84,   # 은행권 개인사업자대출 연체율 (2026.5, 금감원)
            "im_sme_delinquency": 1.26,          # iM뱅크 중소기업 연체율 (2026 상반기 말)
            "policy": SAECHULBAL,
        },
        "matrix": matrix,
        "dpd_buckets": [
            {"bucket": b,
             "count": bucket_map[b][1] if b in bucket_map else 0,
             "exposure_eok": round(float(bucket_map[b][2] or 0) / 1e8, 1) if b in bucket_map else 0}
            for b in order
        ],
    }


@router.get("/soho/restructuring-candidates")
def get_restructuring_candidates(db: Session = Depends(get_db)):
    """새출발기금 요건 매칭 + 은행 자체 프리워크아웃 후보.

    분류 규칙 (제도 근사):
      · 부실차주(90일+) & 총여신 15억 이하  → 새출발기금 안내 대상
      · 부실우려차주(30~89일) & 15억 이하   → 새출발기금(금리조정·유예) 안내
      · 한도 초과 또는 EWS 악화(연체 전)    → 은행 자체 프리워크아웃 우선
    """
    rows = db.execute(text("""
        SELECT c.customer_id, c.customer_name, c.industry_name, c.region,
               SUM(f.outstanding_amount) AS exposure, MAX(f.dpd) AS max_dpd,
               (SELECT composite_score FROM ews_composite_score e
                WHERE e.customer_id = c.customer_id
                ORDER BY score_date DESC LIMIT 1) AS ews_score
        FROM facility f
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.status IN ('ACTIVE','FROZEN') AND c.size_category = 'SOHO'
        GROUP BY c.customer_id
        HAVING max_dpd >= :risk_dpd
            OR (ews_score IS NOT NULL AND ews_score < 45)
        ORDER BY max_dpd DESC, ews_score ASC
        LIMIT 50
    """), {"risk_dpd": SAECHULBAL["risk_dpd_min"]}).fetchall()

    # 이미 연계 등록된 고객은 표시만 바꾼다 (중복 등록 방지)
    referred = {r[0] for r in db.execute(text("""
        SELECT DISTINCT customer_id FROM automation_action
        WHERE action_type = 'RESTRUCTURING_REFERRAL'
          AND action_status IN ('PENDING','EXECUTED')
    """)).fetchall()}

    candidates = []
    for r in rows:
        exposure_eok = float(r[4] or 0) / 1e8
        dpd = int(r[5] or 0)
        within_cap = exposure_eok <= SAECHULBAL["debt_cap_eok"]
        if dpd >= SAECHULBAL["npl_dpd"]:
            category, track = "부실차주", ("새출발기금 (원금감면 심사)" if within_cap else "자체 워크아웃")
        elif dpd >= SAECHULBAL["risk_dpd_min"]:
            category, track = "부실우려차주", ("새출발기금 (금리조정·유예)" if within_cap else "자체 프리워크아웃")
        else:
            category, track = "EWS 악화 (연체 전)", "자체 프리워크아웃 (선제)"
        candidates.append({
            "customer_id": r[0], "customer_name": r[1],
            "industry": r[2], "region": r[3],
            "exposure_eok": round(exposure_eok, 1), "max_dpd": dpd,
            "ews_score": r[6],
            "category": category, "recommended_track": track,
            "within_debt_cap": within_cap,
            "already_referred": r[0] in referred,
        })

    return {
        "policy": SAECHULBAL,
        "candidates": candidates,
        "summary": {
            "total": len(candidates),
            "npl": sum(1 for c in candidates if c["category"] == "부실차주"),
            "at_risk": sum(1 for c in candidates if c["category"] == "부실우려차주"),
            "preemptive": sum(1 for c in candidates if "EWS" in c["category"]),
        },
    }


@router.post("/soho/restructuring-referral")
def create_restructuring_referral(
    customer_id: str = Query(...),
    track: str = Query(..., description="연계 트랙 (새출발기금/자체 프리워크아웃 등)"),
    notes: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """채무조정 연계 등록 - 팀장 이상, 감사기록 필수 (통제 완결 원칙).

    자동화 액션 파이프라인(automation_action)에 태워 후속 실행·추적을
    기존 통제 인프라로 일원화한다.
    """
    if current_user.approval_level not in ("TEAM_LEAD", "DEPT_HEAD", "EXECUTIVE", "COMMITTEE"):
        raise HTTPException(403, "채무조정 연계 등록은 팀장 이상만 가능합니다")

    cust = db.execute(text(
        "SELECT customer_name, size_category FROM customer WHERE customer_id = :cid"),
        {"cid": customer_id}).fetchone()
    if not cust:
        raise HTTPException(404, "고객 없음")
    if cust[1] != "SOHO":
        raise HTTPException(422, "개인사업자(SOHO) 고객만 연계 대상입니다")

    dup = db.execute(text("""
        SELECT action_id FROM automation_action
        WHERE customer_id = :cid AND action_type = 'RESTRUCTURING_REFERRAL'
          AND action_status = 'PENDING'
    """), {"cid": customer_id}).fetchone()
    if dup:
        raise HTTPException(409, "이미 등록된 연계 건이 있습니다")

    action_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO automation_action
            (action_id, trigger_type, customer_id, action_type, priority)
        VALUES (:aid, 'CUSTOM', :cid, 'RESTRUCTURING_REFERRAL', 'HIGH')
    """), {"aid": action_id, "cid": customer_id})

    record_audit(db, "RESTRUCTURING_REFERRAL", "customer", customer_id,
                 after={"track": track, "notes": notes, "action_id": action_id},
                 user_id=current_user.name, user_dept=current_user.dept,
                 critical=True)
    db.commit()

    return {
        "action_id": action_id,
        "customer_id": customer_id,
        "customer_name": cust[0],
        "track": track,
        "registered_by": current_user.name,
    }
