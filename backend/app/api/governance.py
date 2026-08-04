"""
거버넌스 API — 감사 추적 · 전결 규정 · 업무보고서
==================================================
내부통제 실효성을 화면으로 증빙한다.
  · 감사 추적   : 모든 의미 있는 쓰기(승인·분류실행·ECL 재산출)의 이력
  · 전결 규정   : approval_authority — 승인 API 가 실제로 검증에 쓰는 정본
  · 업무보고서  : 감독당국 업무보고서 서식에 준하는 종합 집계 (11개 부문)
                  + PDF 다운로드 (서버 생성, Pretendard 임베드)
"""
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..core.config import AS_OF_STR, AS_OF_DATE

router = APIRouter(prefix="/api/governance", tags=["Governance"])

MONTH_START = AS_OF_DATE.replace(day=1).isoformat()
YEAR_START = AS_OF_DATE.replace(month=1, day=1).isoformat()

REGION_LABELS = {"CAPITAL": "수도권", "DAEGU_GB": "대구경북", "BUSAN_GN": "부산경남"}
SIZE_LABELS = {"LARGE": "대기업", "MEDIUM": "중견기업", "SMALL": "중소기업", "SOHO": "개인사업자"}
STRATEGY_LABELS = {"NORMALIZATION": "정상화", "RESTRUCTURE": "재구조화", "SALE": "매각",
                   "LEGAL_RECOVERY": "법적회수", "WRITE_OFF": "상각"}

# 포용금융 판정 — inclusive_finance.py 와 동일 기준을 쓴다
MID_CREDIT_GRADES = ("BBB+", "BBB", "BBB-", "BB+", "BB", "BB-", "B+", "B", "B-")
_GRADE_LIST = ",".join(f"'{g}'" for g in MID_CREDIT_GRADES)
LATEST_GRADE_JOIN = """
    LEFT JOIN (
        SELECT customer_id, final_grade,
               ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY rating_date DESC) rn
        FROM credit_rating_result
    ) g ON c.customer_id = g.customer_id AND g.rn = 1
"""


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


def _classification_section(db: Session) -> dict:
    """1. 자산건전성 — 시설별 최신 분류 + 직전 스냅샷 대비 증감"""
    cls_rows = db.execute(text("""
        SELECT ac.classification, COUNT(*), SUM(ac.exposure_at_class),
               SUM(ac.required_provision)
        FROM asset_classification ac
        JOIN (SELECT facility_id, MAX(base_date) AS latest
              FROM asset_classification GROUP BY facility_id) mx
          ON ac.facility_id = mx.facility_id AND ac.base_date = mx.latest
        GROUP BY ac.classification
    """)).fetchall()

    # 직전 스냅샷 (전 분류 기준일) — 증감 비교용
    dates = db.execute(text(
        "SELECT DISTINCT base_date FROM asset_classification ORDER BY base_date DESC LIMIT 2"
    )).fetchall()
    prev_map: dict = {}
    if len(dates) > 1:
        prev_rows = db.execute(text("""
            SELECT classification, SUM(exposure_at_class)
            FROM asset_classification WHERE base_date = :d GROUP BY classification
        """), {"d": dates[1][0]}).fetchall()
        prev_map = {r[0]: r[1] or 0 for r in prev_rows}

    order = ["NORMAL", "PRECAUTIONARY", "SUBSTANDARD", "DOUBTFUL", "LOSS"]
    labels = {"NORMAL": "정상", "PRECAUTIONARY": "요주의", "SUBSTANDARD": "고정",
              "DOUBTFUL": "회수의문", "LOSS": "추정손실"}
    cls_map = {r[0]: r for r in cls_rows}
    total_exp = sum((r[2] or 0) for r in cls_rows) or 1
    npl_exp = sum((cls_map[k][2] or 0) for k in ("SUBSTANDARD", "DOUBTFUL", "LOSS") if k in cls_map)

    return {
        "title": "1. 자산건전성 분류 현황",
        "prev_date": dates[1][0] if len(dates) > 1 else None,
        "rows": [
            {
                "grade": labels[k],
                "count": cls_map[k][1] if k in cls_map else 0,
                "exposure": round(cur_exp, 2),
                "share": round(cur_exp / total_exp * 100, 2),
                "change": round(cur_exp - prev_map.get(k, 0), 2),
                "required_provision": round(cls_map[k][3] or 0, 2) if k in cls_map else 0,
            }
            for k in order
            for cur_exp in [(cls_map[k][2] or 0) if k in cls_map else 0]
        ],
        "total_exposure": round(total_exp, 2),
        "npl_exposure": round(npl_exp, 2),
        "npl_ratio": round(npl_exp / total_exp * 100, 2),
    }


@router.get("/report")
def get_business_report(db: Session = Depends(get_db)):
    """업무보고서 집계 — 감독당국 업무보고서 서식에 준하는 11개 부문.

    각 수치는 해당 업무 모듈과 같은 산식을 쓴다 (동일 쿼리 재사용).
    금액 단위: 원 (표시 단계에서 억원 환산).
    """
    # ── 0. 총괄
    base = db.execute(text("""
        SELECT COUNT(*), COUNT(DISTINCT customer_id),
               COALESCE(SUM(outstanding_amount), 0),
               COALESCE(SUM(CASE WHEN contract_date >= :ys THEN outstanding_amount END), 0),
               COALESCE(SUM(CASE WHEN contract_date >= :ys THEN 1 ELSE 0 END), 0)
        FROM facility WHERE status = 'ACTIVE'
    """), {"ys": YEAR_START}).fetchone()

    classification = _classification_section(db)

    # ── 2. 연체 (DPD 버킷)
    buckets = db.execute(text("""
        SELECT
            SUM(CASE WHEN dpd BETWEEN 1 AND 29 THEN 1 ELSE 0 END),
            COALESCE(SUM(CASE WHEN dpd BETWEEN 1 AND 29 THEN outstanding_amount END), 0),
            SUM(CASE WHEN dpd BETWEEN 30 AND 59 THEN 1 ELSE 0 END),
            COALESCE(SUM(CASE WHEN dpd BETWEEN 30 AND 59 THEN outstanding_amount END), 0),
            SUM(CASE WHEN dpd BETWEEN 60 AND 89 THEN 1 ELSE 0 END),
            COALESCE(SUM(CASE WHEN dpd BETWEEN 60 AND 89 THEN outstanding_amount END), 0),
            SUM(CASE WHEN dpd BETWEEN 90 AND 179 THEN 1 ELSE 0 END),
            COALESCE(SUM(CASE WHEN dpd BETWEEN 90 AND 179 THEN outstanding_amount END), 0),
            SUM(CASE WHEN dpd >= 180 THEN 1 ELSE 0 END),
            COALESCE(SUM(CASE WHEN dpd >= 180 THEN outstanding_amount END), 0),
            COALESCE(SUM(outstanding_amount), 0),
            COALESCE(SUM(CASE WHEN dpd >= 30 THEN outstanding_amount END), 0),
            COALESCE(SUM(CASE WHEN dpd >= 90 THEN outstanding_amount END), 0),
            SUM(CASE WHEN dpd BETWEEN 75 AND 89 THEN 1 ELSE 0 END),
            COALESCE(SUM(CASE WHEN dpd BETWEEN 75 AND 89 THEN outstanding_amount END), 0)
        FROM facility WHERE status = 'ACTIVE'
    """)).fetchone()
    total_out = buckets[10] or 1

    # ── 3. 충당금 (감독규정 최저 vs IFRS9 ECL + Stage 구성)
    reg_min = sum(c["required_provision"] for c in classification["rows"])
    stage_rows = db.execute(text("""
        SELECT e.stage, COUNT(*), COALESCE(SUM(e.ead), 0), COALESCE(SUM(e.ecl_final), 0)
        FROM ecl_calculation e
        JOIN (SELECT facility_id, MAX(calc_date) AS latest
              FROM ecl_calculation GROUP BY facility_id) mx
          ON e.facility_id = mx.facility_id AND e.calc_date = mx.latest
        GROUP BY e.stage ORDER BY e.stage
    """)).fetchall()
    ecl_total = sum(r[3] for r in stage_rows)

    # ── 4. 자본 (직전 대비)
    caps = db.execute(text("""
        SELECT base_date, bis_ratio, tier1_ratio, cet1_ratio, leverage_ratio,
               total_capital, total_rwa
        FROM capital_position ORDER BY base_date DESC LIMIT 2
    """)).fetchall()
    cap = caps[0] if caps else None
    cap_prev = caps[1] if len(caps) > 1 else None

    # ── 5. 포트폴리오 (업종·지역·규모)
    ind_rows = db.execute(text("""
        SELECT c.industry_name, COUNT(*), COALESCE(SUM(f.outstanding_amount), 0),
               COALESCE(SUM(CASE WHEN f.classification IN ('SUBSTANDARD','DOUBTFUL','LOSS')
                            THEN f.outstanding_amount END), 0)
        FROM facility f JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.status = 'ACTIVE'
        GROUP BY c.industry_name ORDER BY 3 DESC LIMIT 8
    """)).fetchall()
    reg_rows = db.execute(text("""
        SELECT c.region, COALESCE(SUM(f.outstanding_amount), 0),
               COALESCE(SUM(CASE WHEN f.dpd >= 30 THEN f.outstanding_amount END), 0)
        FROM facility f JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.status = 'ACTIVE' GROUP BY c.region ORDER BY 2 DESC
    """)).fetchall()
    size_rows = db.execute(text("""
        SELECT c.size_category, COUNT(*), COALESCE(SUM(f.outstanding_amount), 0)
        FROM facility f JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.status = 'ACTIVE' GROUP BY c.size_category ORDER BY 3 DESC
    """)).fetchall()

    # ── 6. 부동산PF
    pf = db.execute(text("""
        SELECT COUNT(*), COALESCE(SUM(exposure), 0),
               SUM(CASE WHEN status = 'WATCHLIST' THEN 1 ELSE 0 END),
               SUM(CASE WHEN project_type = 'BRIDGE' THEN 1 ELSE 0 END),
               COALESCE(SUM(CASE WHEN project_type = 'BRIDGE' THEN exposure END), 0),
               COALESCE(AVG(equity_ratio), 0),
               SUM(CASE WHEN project_type = 'MAIN'
                        AND (COALESCE(progress_rate,0) - COALESCE(presale_rate,0)) >= 30
                        THEN 1 ELSE 0 END)
        FROM pf_project WHERE status != 'COMPLETED'
    """)).fetchone()

    # ── 7. 포용금융 (중신용·개인사업자)
    def seg(cond: str):
        r = db.execute(text(f"""
            SELECT COUNT(*), COALESCE(SUM(f.outstanding_amount), 0),
                   COALESCE(SUM(CASE WHEN f.dpd >= 30 THEN f.outstanding_amount END), 0)
            FROM facility f JOIN customer c ON f.customer_id = c.customer_id
            {LATEST_GRADE_JOIN}
            WHERE f.status = 'ACTIVE' AND ({cond})
        """)).fetchone()
        return r
    mid = seg(f"g.final_grade IN ({_GRADE_LIST})")
    soho = seg("c.size_category = 'SOHO'")

    # ── 8. 워크아웃·회수
    wo = db.execute(text("""
        SELECT SUM(CASE WHEN case_status IN ('OPEN','IN_PROGRESS') THEN 1 ELSE 0 END),
               COALESCE(SUM(CASE WHEN case_status IN ('OPEN','IN_PROGRESS') THEN total_exposure END), 0),
               SUM(CASE WHEN case_status = 'RECOVERED' THEN 1 ELSE 0 END),
               COALESCE(SUM(CASE WHEN case_status IN ('OPEN','IN_PROGRESS')
                            THEN expected_recovery_amount END), 0)
        FROM workout_case
    """)).fetchone()
    wo_strat = db.execute(text("""
        SELECT strategy, COUNT(*) FROM workout_case
        WHERE case_status IN ('OPEN','IN_PROGRESS') GROUP BY strategy ORDER BY 2 DESC
    """)).fetchall()

    # ── 9. 조기경보 (EWS)
    ews = db.execute(text("""
        SELECT SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END),
               SUM(CASE WHEN status = 'OPEN' AND severity IN ('HIGH','CRITICAL') THEN 1 ELSE 0 END),
               COUNT(*)
        FROM ews_alert
    """)).fetchone()

    # ── 10. 내부통제
    cov = db.execute(text("""
        SELECT SUM(CASE WHEN cc.result = 'BREACH' THEN 1 ELSE 0 END),
               SUM(CASE WHEN cc.result = 'BREACH'
                        AND cc.breach_severity IN ('MAJOR','EVENT_OF_DEFAULT') THEN 1 ELSE 0 END)
        FROM covenant_check cc
        JOIN (SELECT covenant_id, MAX(check_date) AS latest
              FROM covenant_check GROUP BY covenant_id) mx
          ON cc.covenant_id = mx.covenant_id AND cc.check_date = mx.latest
    """)).fetchone()
    app_rows = db.execute(text("""
        SELECT status, COUNT(*) FROM loan_application GROUP BY status
    """)).fetchall()
    app_map = {r[0]: r[1] for r in app_rows}
    audit_cnt = db.execute(text("SELECT COUNT(*) FROM audit_log")).fetchone()[0]

    return {
        "report_title": "여신 업무보고서",
        "doc_no": f"CLMS-{AS_OF_DATE.strftime('%Y%m')}-001",
        "base_date": AS_OF_STR,
        "period": f"{AS_OF_DATE.year}년 {AS_OF_DATE.month}월",
        "sections": {
            "summary": {
                "title": "총괄",
                "facility_count": base[0],
                "borrower_count": base[1],
                "total_outstanding": round(base[2], 2),
                "new_amount": round(base[3], 2),
                "new_count": base[4],
                "npl_ratio": classification["npl_ratio"],
                "delinquency_rate": round(buckets[11] / total_out * 100, 3),
                "bis_ratio": round((cap[1] or 0) * 100, 2) if cap else 0,
                "ecl_total": round(ecl_total, 2),
            },
            "classification": classification,
            "delinquency": {
                "title": "2. 연체 현황",
                "buckets": [
                    {"label": "1~29일",   "count": buckets[0] or 0, "amount": round(buckets[1], 2)},
                    {"label": "30~59일",  "count": buckets[2] or 0, "amount": round(buckets[3], 2)},
                    {"label": "60~89일",  "count": buckets[4] or 0, "amount": round(buckets[5], 2)},
                    {"label": "90~179일", "count": buckets[6] or 0, "amount": round(buckets[7], 2)},
                    {"label": "180일 이상", "count": buckets[8] or 0, "amount": round(buckets[9], 2)},
                ],
                "delinquent_1m": round(buckets[11], 2),
                "delinquent_3m": round(buckets[12], 2),
                "delinquency_rate": round(buckets[11] / total_out * 100, 3),
                "delinquency_rate_3m": round(buckets[12] / total_out * 100, 3),
                "transfer_imminent_count": buckets[13] or 0,
                "transfer_imminent_amount": round(buckets[14], 2),
            },
            "provision": {
                "title": "3. 대손충당금·대손준비금",
                "regulatory_minimum": round(reg_min, 2),
                "ifrs9_ecl": round(ecl_total, 2),
                "loan_loss_reserve": round(max(reg_min - ecl_total, 0), 2),
                "coverage_ratio": round(ecl_total / classification["npl_exposure"] * 100, 1)
                                  if classification["npl_exposure"] else 0,
                "stages": [
                    {"stage": r[0], "count": r[1], "ead": round(r[2], 2), "ecl": round(r[3], 2)}
                    for r in stage_rows
                ],
                "note": "감독규정 최저적립액이 IFRS9 ECL 을 초과하는 차액은 대손준비금 적립 대상",
            },
            "capital": {
                "title": "4. 자기자본비율",
                "bis_ratio": round((cap[1] or 0) * 100, 2) if cap else 0,
                "tier1_ratio": round((cap[2] or 0) * 100, 2) if cap else 0,
                "cet1_ratio": round((cap[3] or 0) * 100, 2) if cap else 0,
                "leverage_ratio": round((cap[4] or 0) * 100, 2) if cap else 0,
                "total_capital": round(cap[5] or 0, 2) if cap else 0,
                "total_rwa": round(cap[6] or 0, 2) if cap else 0,
                "bis_change": round(((cap[1] or 0) - (cap_prev[1] or 0)) * 100, 2)
                              if cap and cap_prev else None,
            },
            "portfolio": {
                "title": "5. 여신 포트폴리오",
                "by_industry": [
                    {
                        "name": r[0], "count": r[1], "exposure": round(r[2], 2),
                        "share": round(r[2] / (base[2] or 1) * 100, 1),
                        "npl_ratio": round(r[3] / r[2] * 100, 2) if r[2] else 0,
                    }
                    for r in ind_rows
                ],
                "by_region": [
                    {
                        "name": REGION_LABELS.get(r[0], r[0] or "기타"),
                        "exposure": round(r[1], 2),
                        "share": round(r[1] / (base[2] or 1) * 100, 1),
                        "delinquency_rate": round(r[2] / r[1] * 100, 3) if r[1] else 0,
                    }
                    for r in reg_rows
                ],
                "by_size": [
                    {
                        "name": SIZE_LABELS.get(r[0], r[0] or "기타"),
                        "count": r[1], "exposure": round(r[2], 2),
                        "share": round(r[2] / (base[2] or 1) * 100, 1),
                    }
                    for r in size_rows
                ],
            },
            "pf": {
                "title": "6. 부동산PF 사업장",
                "project_count": pf[0] or 0,
                "exposure": round(pf[1], 2),
                "watchlist_count": pf[2] or 0,
                "bridge_count": pf[3] or 0,
                "bridge_exposure": round(pf[4], 2),
                "avg_equity_ratio": round(pf[5], 1),
                "gap_alert_count": pf[6] or 0,
            },
            "inclusive": {
                "title": "7. 포용금융 이행",
                "mid_credit": {
                    "count": mid[0], "exposure": round(mid[1], 2),
                    "share": round(mid[1] / (base[2] or 1) * 100, 1), "target": 20.0,
                    "delinquency_rate": round(mid[2] / mid[1] * 100, 3) if mid[1] else 0,
                },
                "soho": {
                    "count": soho[0], "exposure": round(soho[1], 2),
                    "share": round(soho[1] / (base[2] or 1) * 100, 1), "target": 12.0,
                    "delinquency_rate": round(soho[2] / soho[1] * 100, 3) if soho[1] else 0,
                },
            },
            "workout": {
                "title": "8. 워크아웃·회수",
                "active_cases": wo[0] or 0,
                "active_exposure": round(wo[1], 2),
                "recovered_cases": wo[2] or 0,
                "expected_recovery": round(wo[3], 2),
                "expected_recovery_rate": round(wo[3] / wo[1] * 100, 1) if wo[1] else 0,
                "by_strategy": [
                    {"name": STRATEGY_LABELS.get(r[0], r[0]), "count": r[1]} for r in wo_strat
                ],
            },
            "ews": {
                "title": "9. 조기경보 운영",
                "open_alerts": ews[0] or 0,
                "high_alerts": ews[1] or 0,
                "total_alerts": ews[2] or 0,
            },
            "internal_control": {
                "title": "10. 내부통제",
                "covenant_breaches": cov[0] or 0,
                "covenant_major": cov[1] or 0,
                "applications_total": sum(app_map.values()),
                "applications_approved": app_map.get("APPROVED", 0),
                "applications_reviewing": app_map.get("REVIEWING", 0) + app_map.get("RECEIVED", 0),
                "applications_rejected": app_map.get("REJECTED", 0),
                "audit_log_count": audit_cnt,
            },
        },
    }


@router.get("/report/pdf")
def get_business_report_pdf(db: Session = Depends(get_db)):
    """업무보고서 PDF 다운로드 — /report 와 동일 집계를 서식 문서로 렌더."""
    from ..services.report_pdf import build_report_pdf

    data = get_business_report(db)
    pdf_bytes = build_report_pdf(data)

    filename = f"여신업무보고서_{AS_OF_DATE.strftime('%Y-%m')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                f"attachment; filename=\"report.pdf\"; filename*=UTF-8''{quote(filename)}"
        },
    )
