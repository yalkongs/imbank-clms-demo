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
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..core.config import AS_OF_MONTH, as_of_months

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
