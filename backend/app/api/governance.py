"""
거버넌스 API — 감사 추적 · 전결 규정 · 업무보고서
==================================================
내부통제 실효성을 화면으로 증빙한다.
  · 감사 추적   : 모든 의미 있는 쓰기(승인·분류실행·ECL 재산출)의 이력
  · 전결 규정   : approval_authority — 승인 API 가 실제로 검증에 쓰는 정본
  · 업무보고서  : 감독당국 보고 서식에 준하는 건전성·충당금·자본 집계
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..core.config import AS_OF_STR, AS_OF_DATE

router = APIRouter(prefix="/api/governance", tags=["Governance"])


@router.get("/audit-logs")
def get_audit_logs(
    limit: int = Query(50, le=200),
    action_type: str = Query(None),
    db: Session = Depends(get_db),
):
    """감사 기록 조회 (최신순)"""
    cond, params = "1=1", {"lim": limit}
    if action_type:
        cond += " AND action_type = :at"
        params["at"] = action_type

    rows = db.execute(text(f"""
        SELECT log_id, log_timestamp, user_id, user_dept, action_type,
               target_entity, target_id, before_value, after_value
        FROM audit_log WHERE {cond}
        ORDER BY log_timestamp DESC LIMIT :lim
    """), params).fetchall()

    total = db.execute(text("SELECT COUNT(*) FROM audit_log")).fetchone()[0]
    return {
        "total": total,
        "logs": [
            {
                "log_id": r[0], "timestamp": r[1], "user_id": r[2],
                "user_dept": r[3], "action_type": r[4],
                "target_entity": r[5], "target_id": r[6],
                "before": r[7], "after": r[8],
            }
            for r in rows
        ],
    }


@router.get("/approval-authority")
def get_approval_authority(db: Session = Depends(get_db)):
    """전결 규정 조회 — 승인 API 검증에 쓰는 정본"""
    rows = db.execute(text("""
        SELECT authority_level, authority_name, amount_limit, effective_from
        FROM approval_authority WHERE status = 'ACTIVE' ORDER BY display_order
    """)).fetchall()
    return [
        {
            "level": r[0], "name": r[1],
            "amount_limit": r[2],
            "limit_label": "무제한" if r[2] is None else f"{r[2]/1e8:,.0f}억원",
            "effective_from": r[3],
        }
        for r in rows
    ]


@router.get("/report")
def get_business_report(db: Session = Depends(get_db)):
    """업무보고서 집계 — 자산건전성·연체·충당금·자본을 보고 서식 형태로.

    각 수치는 해당 업무 모듈과 같은 산식을 쓴다 (동일 쿼리 재사용).
    """
    # 1. 자산건전성 (최신 분류)
    cls_rows = db.execute(text("""
        SELECT ac.classification, COUNT(*), SUM(ac.exposure_at_class),
               SUM(ac.required_provision), SUM(ac.existing_provision)
        FROM asset_classification ac
        JOIN (SELECT facility_id, MAX(base_date) AS latest
              FROM asset_classification GROUP BY facility_id) mx
          ON ac.facility_id = mx.facility_id AND ac.base_date = mx.latest
        GROUP BY ac.classification
    """)).fetchall()
    order = ["NORMAL", "PRECAUTIONARY", "SUBSTANDARD", "DOUBTFUL", "LOSS"]
    labels = {"NORMAL": "정상", "PRECAUTIONARY": "요주의", "SUBSTANDARD": "고정",
              "DOUBTFUL": "회수의문", "LOSS": "추정손실"}
    cls_map = {r[0]: r for r in cls_rows}
    total_exp = sum((r[2] or 0) for r in cls_rows) or 1
    npl_exp = sum((cls_map[k][2] or 0) for k in ("SUBSTANDARD", "DOUBTFUL", "LOSS") if k in cls_map)

    classification = [
        {
            "grade": labels[k],
            "count": cls_map[k][1] if k in cls_map else 0,
            "exposure": round(cls_map[k][2] or 0, 2) if k in cls_map else 0,
            "share": round((cls_map[k][2] or 0) / total_exp * 100, 2) if k in cls_map else 0,
            "required_provision": round(cls_map[k][3] or 0, 2) if k in cls_map else 0,
        }
        for k in order
    ]

    # 2. 연체
    delinq = db.execute(text("""
        SELECT
            COALESCE(SUM(CASE WHEN dpd >= 30 THEN outstanding_amount END), 0),
            COALESCE(SUM(CASE WHEN dpd >= 90 THEN outstanding_amount END), 0),
            COALESCE(SUM(outstanding_amount), 0)
        FROM facility WHERE status = 'ACTIVE'
    """)).fetchone()

    # 3. 충당금 적정성 (감독규정 최저 vs IFRS9 ECL)
    reg_min = sum(c["required_provision"] for c in classification)
    ecl = db.execute(text("""
        SELECT COALESCE(SUM(e.ecl_final), 0)
        FROM ecl_calculation e
        JOIN (SELECT facility_id, MAX(calc_date) AS latest
              FROM ecl_calculation GROUP BY facility_id) mx
          ON e.facility_id = mx.facility_id AND e.calc_date = mx.latest
    """)).fetchone()[0]

    # 4. 자본
    cap = db.execute(text("""
        SELECT bis_ratio, tier1_ratio, cet1_ratio, leverage_ratio,
               total_capital, total_rwa
        FROM capital_position ORDER BY base_date DESC LIMIT 1
    """)).fetchone()

    return {
        "report_title": "여신 업무보고서",
        "base_date": AS_OF_STR,
        "period": f"{AS_OF_DATE.year}년 {AS_OF_DATE.month}월",
        "sections": {
            "classification": {
                "title": "1. 자산건전성 분류 현황",
                "rows": classification,
                "total_exposure": round(total_exp, 2),
                "npl_ratio": round(npl_exp / total_exp * 100, 2),
            },
            "delinquency": {
                "title": "2. 연체 현황",
                "delinquent_1m": round(delinq[0], 2),
                "delinquent_3m": round(delinq[1], 2),
                "delinquency_rate": round(delinq[0] / delinq[2] * 100, 3) if delinq[2] else 0,
            },
            "provision": {
                "title": "3. 대손충당금 적립 현황",
                "regulatory_minimum": round(reg_min, 2),
                "ifrs9_ecl": round(ecl, 2),
                "loan_loss_reserve": round(max(reg_min - ecl, 0), 2),
                "note": "감독규정 최저적립액이 IFRS9 ECL 을 초과하는 차액은 대손준비금 적립 대상",
            },
            "capital": {
                "title": "4. 자기자본비율 현황",
                "bis_ratio": round((cap[0] or 0) * 100, 2) if cap else 0,
                "tier1_ratio": round((cap[1] or 0) * 100, 2) if cap else 0,
                "cet1_ratio": round((cap[2] or 0) * 100, 2) if cap else 0,
                "leverage_ratio": round((cap[3] or 0) * 100, 2) if cap else 0,
                "total_capital": round(cap[4] or 0, 2) if cap else 0,
                "total_rwa": round(cap[5] or 0, 2) if cap else 0,
            },
        },
    }
