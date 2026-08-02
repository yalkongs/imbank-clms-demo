"""
IFRS 9 ECL 충당금 산출 API
============================
3단계 기대신용손실(Expected Credit Loss) 체계
Stage 1 (12M ECL) / Stage 2 (Lifetime) / Stage 3 (Impaired)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import date
import uuid

from ..core.database import get_db
from ..core.config import AS_OF_DATE
from ..services.calculations import (
    determine_sicr,
    calculate_ecl_stage1,
    calculate_ecl_stage2,
    calculate_ecl_stage3,
    GRADE_PD_MAP,
)

router = APIRouter(prefix="/api/ecl", tags=["IFRS9 ECL"])

# 거시 시나리오 조정 계수 (베이스라인 = 1.0)
MACRO_SCENARIOS = {
    'base':      {'factor': 1.0,  'label': '기본', 'weight': 0.6},
    'adverse':   {'factor': 1.35, 'label': '비관', 'weight': 0.3},
    'optimistic': {'factor': 0.80, 'label': '낙관', 'weight': 0.1},
}


def _weighted_macro_factor() -> float:
    """시나리오 가중 평균 거시 조정 계수"""
    return sum(s['factor'] * s['weight'] for s in MACRO_SCENARIOS.values())


@router.get("/portfolio-summary")
def get_portfolio_ecl_summary(
    calc_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    포트폴리오 ECL 요약
    — Stage별 잔액, ECL 금액, 커버리지 비율
    """
    if calc_date:
        date_filter = "WHERE e.calc_date = :cd"
        params = {"cd": calc_date}
    else:
        date_filter = """
            JOIN (
                SELECT facility_id, MAX(calc_date) AS latest
                FROM ecl_calculation GROUP BY facility_id
            ) mx ON e.facility_id = mx.facility_id AND e.calc_date = mx.latest
            WHERE 1=1
        """
        params = {}

    rows = db.execute(
        text(f"""
            SELECT
                e.stage,
                COUNT(*) AS cnt,
                SUM(e.ead) AS total_ead,
                SUM(e.ecl_final) AS total_ecl,
                AVG(e.pd_current) AS avg_pd,
                AVG(e.lgd) AS avg_lgd
            FROM ecl_calculation e
            {date_filter}
            GROUP BY e.stage
            ORDER BY e.stage
        """),
        params
    ).fetchall()

    stage_labels = {1: 'Stage 1 (정상)', 2: 'Stage 2 (유의적 증가)', 3: 'Stage 3 (손상)'}
    stage_colors = {1: 'green', 2: 'orange', 3: 'red'}

    total_ead = sum((r[2] or 0) for r in rows)
    total_ecl = sum((r[3] or 0) for r in rows)

    stages = []
    for r in rows:
        ead = r[2] or 0
        ecl = r[3] or 0
        stages.append({
            "stage":       r[0],
            "label":       stage_labels.get(r[0], f'Stage {r[0]}'),
            "color":       stage_colors.get(r[0], 'gray'),
            "count":       r[1],
            "ead":         round(ead, 2),
            "ead_share":   round(ead / total_ead * 100, 2) if total_ead > 0 else 0,
            "ecl":         round(ecl, 2),
            "coverage_rate": round(ecl / ead * 100, 2) if ead > 0 else 0,
            "avg_pd":      round((r[4] or 0) * 100, 3),
            "avg_lgd":     round((r[5] or 0) * 100, 2),
        })

    return {
        "calc_date":    calc_date or "최신",
        "total_ead":    round(total_ead, 2),
        "total_ecl":    round(total_ecl, 2),
        "coverage_rate": round(total_ecl / total_ead * 100, 2) if total_ead > 0 else 0,
        "by_stage":     stages,
    }


@router.get("/facility/{facility_id}")
def get_facility_ecl(
    facility_id: str,
    limit: int = Query(12),
    db: Session = Depends(get_db)
):
    """여신별 ECL 산출 결과 이력"""
    rows = db.execute(
        text("""
            SELECT
                e.ecl_id, e.calc_date, e.stage, e.sicr_triggered, e.sicr_reason,
                e.pd_original, e.pd_current, e.lgd, e.ead, e.remaining_tenor_months,
                e.ecl_base, e.macro_adj_factor, e.ecl_final,
                e.prev_ecl, e.ecl_change,
                e.existing_provision, e.provision_gap,
                f.outstanding_amount, f.facility_type, c.customer_name
            FROM ecl_calculation e
            JOIN facility f ON e.facility_id = f.facility_id
            JOIN customer c ON e.customer_id = c.customer_id
            WHERE e.facility_id = :fid
            ORDER BY e.calc_date DESC
            LIMIT :lim
        """),
        {"fid": facility_id, "lim": limit}
    ).fetchall()

    history = []
    for r in rows:
        history.append({
            "ecl_id":           r[0],
            "calc_date":        str(r[1]),
            "stage":            r[2],
            "sicr_triggered":   bool(r[3]),
            "sicr_reason":      r[4],
            "pd_original":      round((r[5] or 0) * 100, 4),
            "pd_current":       round((r[6] or 0) * 100, 4),
            "lgd":              round((r[7] or 0) * 100, 2),
            "ead":              round(r[8] or 0, 2),
            "remaining_months": r[9],
            "ecl_base":         round(r[10] or 0, 2),
            "macro_factor":     r[11],
            "ecl_final":        round(r[12] or 0, 2),
            "ecl_change":       round(r[14] or 0, 2),
            "existing_provision": round(r[15] or 0, 2),
            "provision_gap":    round(r[16] or 0, 2),
        })

    return {
        "facility_id":  facility_id,
        "company_name": rows[0][19] if rows else None,
        "product_type": rows[0][18] if rows else None,
        "outstanding":  round(rows[0][17] or 0, 2) if rows else 0,
        "history":      history,
    }


@router.get("/stage-migration")
def get_stage_migration(
    db: Session = Depends(get_db)
):
    """Stage 이동 현황 (전월 → 당월 비교)"""
    dates = db.execute(
        text("SELECT DISTINCT calc_date FROM ecl_calculation ORDER BY calc_date DESC LIMIT 2")
    ).fetchall()

    if len(dates) < 2:
        return {"error": "비교 데이터 부족 (최소 2개 기준일 필요)"}

    curr_date = str(dates[0][0])
    prev_date = str(dates[1][0])

    rows = db.execute(
        text("""
            SELECT
                e_prev.stage AS from_stage,
                e_curr.stage AS to_stage,
                COUNT(*) AS cnt,
                SUM(e_curr.ead) AS exposure
            FROM ecl_calculation e_prev
            JOIN ecl_calculation e_curr
                ON e_prev.facility_id = e_curr.facility_id
            WHERE e_prev.calc_date = :pd AND e_curr.calc_date = :cd
            GROUP BY e_prev.stage, e_curr.stage
            ORDER BY e_prev.stage, e_curr.stage
        """),
        {"pd": prev_date, "cd": curr_date}
    ).fetchall()

    matrix = {}
    for r in rows:
        fs = r[0]; ts = r[1]
        if fs not in matrix:
            matrix[fs] = {}
        matrix[fs][ts] = {"count": r[2], "exposure": round(r[3] or 0, 2)}

    # Stage 2/3 신규 진입 건수
    new_stage2 = matrix.get(1, {}).get(2, {}).get("count", 0)
    new_stage3 = (
        matrix.get(1, {}).get(3, {}).get("count", 0)
        + matrix.get(2, {}).get(3, {}).get("count", 0)
    )

    return {
        "prev_date":   prev_date,
        "curr_date":   curr_date,
        "matrix":      matrix,
        "new_stage2":  new_stage2,
        "new_stage3":  new_stage3,
        "cured":       matrix.get(2, {}).get(1, {}).get("count", 0),
    }


@router.get("/provision-adequacy")
def get_provision_adequacy(
    db: Session = Depends(get_db)
):
    """충당금 적정성 분석 — ECL vs 현재 충당금 비교"""
    rows = db.execute(
        text("""
            SELECT
                e.stage,
                SUM(e.ead) AS ead,
                SUM(e.ecl_final) AS ecl,
                SUM(e.existing_provision) AS existing,
                SUM(e.provision_gap) AS gap
            FROM ecl_calculation e
            JOIN (
                SELECT facility_id, MAX(calc_date) AS latest
                FROM ecl_calculation GROUP BY facility_id
            ) mx ON e.facility_id = mx.facility_id AND e.calc_date = mx.latest
            GROUP BY e.stage
        """)
    ).fetchall()

    total_ecl  = sum((r[2] or 0) for r in rows)
    total_prov = sum((r[3] or 0) for r in rows)
    total_gap  = sum((r[4] or 0) for r in rows)

    by_stage = []
    for r in rows:
        ead = r[1] or 0
        ecl = r[2] or 0
        by_stage.append({
            "stage":             r[0],
            "ead":               round(ead, 2),
            "ecl_required":      round(ecl, 2),
            "existing_provision": round(r[3] or 0, 2),
            "provision_gap":     round(r[4] or 0, 2),
            "ecl_rate":          round(ecl / ead * 100, 3) if ead > 0 else 0,
            "adequacy":          "ADEQUATE" if (r[4] or 0) <= 0 else "INSUFFICIENT",
        })

    return {
        "total_ecl_required":   round(total_ecl, 2),
        "total_existing_prov":  round(total_prov, 2),
        "total_gap":            round(total_gap, 2),
        "adequacy_rate":        round(total_prov / total_ecl * 100, 2) if total_ecl > 0 else 0,
        "by_stage":             by_stage,
    }


@router.post("/calculate/{facility_id}")
def calculate_ecl_for_facility(
    facility_id: str,
    calc_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    개별 여신 ECL 재산출
    — PD/LGD 최신값 + SICR 판별 → Stage 결정 → ECL 산출 → 저장
    """
    cd = calc_date or AS_OF_DATE.strftime('%Y-%m-%d')

    fac = db.execute(
        text("""
            SELECT f.facility_id, f.customer_id, f.outstanding_amount,
                   f.dpd, f.contract_date, f.maturity_date,
                   NULL AS credit_grade, rp.ttc_pd AS pd, rp.lgd
            FROM facility f
            JOIN customer c ON f.customer_id = c.customer_id
            -- risk_parameter 는 customer_id 를 갖지 않는다(application_id 기준).
            -- 기존의 c.customer_id = rp.customer_id 조인은 항상 500을 냈다.
            LEFT JOIN risk_parameter rp ON f.application_id = rp.application_id
            WHERE f.facility_id = :fid
        """),
        {"fid": facility_id}
    ).fetchone()

    if not fac:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="여신 없음")

    cid     = fac[1]
    ead     = fac[2] or 0
    dpd     = fac[3] or 0
    pd_curr = fac[7] or GRADE_PD_MAP.get(fac[6] or 'BBB', 0.02)
    lgd     = fac[8] or 0.45

    # 최초 승인 시 PD (이력에서 가져오거나 현재 PD의 70% 추정)
    orig_row = db.execute(
        text("""
            SELECT pd_original FROM ecl_calculation
            WHERE facility_id=:fid ORDER BY calc_date ASC LIMIT 1
        """),
        {"fid": facility_id}
    ).fetchone()
    pd_orig = orig_row[0] if orig_row else pd_curr * 0.7

    # 잔존 기간 (개월)
    remaining_months = 24  # 기본값
    if fac[5]:
        try:
            mat = date.fromisoformat(str(fac[5]))
            today = AS_OF_DATE
            remaining_months = max(0, (mat.year - today.year) * 12 + (mat.month - today.month))
        except Exception:
            pass

    # EWS 점수
    ews_row = db.execute(
        # composite_score 는 ews_alert 가 아니라 ews_composite_score 에 있다.
        # 기존 쿼리는 존재하지 않는 컬럼을 조회해 항상 500을 냈다.
        text("SELECT composite_score FROM ews_composite_score WHERE customer_id=:cid ORDER BY score_date DESC LIMIT 1"),
        {"cid": cid}
    ).fetchone()
    ews_score = float(ews_row[0]) if ews_row else None

    # 등급 낙폭 추정
    grade_order = list(GRADE_PD_MAP.keys())
    curr_grade  = fac[6] or 'BBB'
    orig_grade  = curr_grade  # 단순화
    try:
        drop = grade_order.index(curr_grade) - grade_order.index(orig_grade)
        grade_drop_notches = max(0, drop)
    except ValueError:
        grade_drop_notches = 0

    # 신용손상 증거 (기준서 1109호 부록A) — 워크아웃 진행 건은 채권 양보·
    # 법적회수·상각 등 객관적 손상 사유에 해당한다. 정상화 종결(RECOVERED)은 제외.
    wo_row = db.execute(
        text("""
            SELECT case_status, strategy FROM workout_case
            WHERE facility_id=:fid AND case_status NOT IN ('RECOVERED')
            ORDER BY case_open_date DESC LIMIT 1
        """),
        {"fid": facility_id}
    ).fetchone()
    credit_impaired = wo_row is not None
    impairment_evidence = f"WORKOUT_{wo_row[1]}" if wo_row else None

    sicr_result = determine_sicr(
        pd_orig, pd_curr,
        ews_score=ews_score,
        dpd=dpd,
        grade_drop_notches=grade_drop_notches,
        credit_impaired=credit_impaired,
        impairment_evidence=impairment_evidence,
    )
    stage = sicr_result['recommended_stage']

    # ECL 산출
    macro_factor = _weighted_macro_factor()

    if stage == 1:
        ecl_base = calculate_ecl_stage1(pd_curr, lgd, ead)
    elif stage == 2:
        ecl_base = calculate_ecl_stage2(pd_curr, lgd, ead, remaining_months)
    else:
        expected_recovery = ead * (1 - lgd)
        ecl_base = calculate_ecl_stage3(ead, expected_recovery)

    ecl_final = round(ecl_base * macro_factor, 2)

    # 이전 ECL
    prev_row = db.execute(
        text("SELECT ecl_final FROM ecl_calculation WHERE facility_id=:fid ORDER BY calc_date DESC LIMIT 1"),
        {"fid": facility_id}
    ).fetchone()
    prev_ecl = float(prev_row[0]) if prev_row else None

    # 현재 충당금
    ex_prov = db.execute(
        text("SELECT COALESCE(SUM(provision_amount),0) FROM workout_case WHERE customer_id=:cid"),
        {"cid": cid}
    ).scalar()

    ecl_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO ecl_calculation
                (ecl_id, facility_id, customer_id, calc_date,
                 stage, sicr_triggered, sicr_reason,
                 pd_original, pd_current, lgd, ead, remaining_tenor_months,
                 ecl_base, macro_adj_factor, ecl_final,
                 prev_ecl, ecl_change,
                 existing_provision, provision_gap)
            VALUES
                (:eid, :fid, :cid, :cd,
                 :stage, :sicr, :reasons,
                 :pd_orig, :pd_curr, :lgd, :ead, :months,
                 :ecl_base, :macro, :ecl_final,
                 :prev, :chg,
                 :ex_prov, :gap)
            ON CONFLICT(facility_id, calc_date)
            DO UPDATE SET
                stage=excluded.stage,
                sicr_triggered=excluded.sicr_triggered,
                sicr_reason=excluded.sicr_reason,
                pd_current=excluded.pd_current,
                ecl_base=excluded.ecl_base,
                macro_adj_factor=excluded.macro_adj_factor,
                ecl_final=excluded.ecl_final,
                ecl_change=excluded.ecl_change,
                provision_gap=excluded.provision_gap
        """),
        {
            "eid": ecl_id, "fid": facility_id, "cid": cid, "cd": cd,
            "stage": stage,
            "sicr":    1 if sicr_result['sicr'] else 0,
            "reasons": ",".join(sicr_result['reasons']),
            "pd_orig": pd_orig, "pd_curr": pd_curr, "lgd": lgd,
            "ead": ead, "months": remaining_months,
            "ecl_base": ecl_base, "macro": macro_factor,
            "ecl_final": ecl_final,
            "prev": prev_ecl, "chg": round(ecl_final - (prev_ecl or 0), 2),
            "ex_prov": float(ex_prov or 0),
            "gap": round(ecl_final - float(ex_prov or 0), 2),
        }
    )
    db.commit()

    return {
        "facility_id":   facility_id,
        "calc_date":     cd,
        "stage":         stage,
        "sicr":          sicr_result,
        "pd_current":    round(pd_curr * 100, 4),
        "lgd":           round(lgd * 100, 2),
        "ead":           round(ead, 2),
        "ecl_base":      round(ecl_base, 2),
        "macro_factor":  round(macro_factor, 4),
        "ecl_final":     ecl_final,
        "prev_ecl":      round(prev_ecl, 2) if prev_ecl else None,
        "ecl_change":    round(ecl_final - (prev_ecl or 0), 2),
    }


@router.get("/trend")
def get_ecl_trend(
    quarters: int = Query(8, description="조회 분기 수"),
    db: Session = Depends(get_db)
):
    """ECL 추이 (분기별 Stage별 ECL 합계)"""
    rows = db.execute(
        text("""
            SELECT
                strftime('%Y-Q', calc_date) ||
                CASE CAST(strftime('%m', calc_date) AS INTEGER)
                    WHEN 1 THEN '1' WHEN 2 THEN '1' WHEN 3 THEN '1'
                    WHEN 4 THEN '2' WHEN 5 THEN '2' WHEN 6 THEN '2'
                    WHEN 7 THEN '3' WHEN 8 THEN '3' WHEN 9 THEN '3'
                    ELSE '4' END AS quarter,
                stage,
                SUM(ecl_final) AS total_ecl,
                COUNT(*) AS cnt
            FROM ecl_calculation
            GROUP BY quarter, stage
            ORDER BY quarter DESC
            LIMIT :lim
        """),
        {"lim": quarters * 3}
    ).fetchall()

    timeline = {}
    for r in rows:
        q  = r[0]; st = r[1]
        if q not in timeline:
            timeline[q] = {"quarter": q}
        timeline[q][f"stage{st}_ecl"] = round(r[2] or 0, 2)

    trend = sorted(timeline.values(), key=lambda x: x["quarter"])[-quarters:]
    return {"trend": trend}


@router.get("/macro-sensitivity")
def get_macro_sensitivity(
    facility_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """거시 시나리오별 ECL 민감도"""
    if facility_id:
        row = db.execute(
            text("""
                SELECT ecl_base FROM ecl_calculation
                WHERE facility_id=:fid ORDER BY calc_date DESC LIMIT 1
            """),
            {"fid": facility_id}
        ).fetchone()
        base_ecl = float(row[0]) if row else 0
    else:
        base_ecl = db.execute(
            text("""
                SELECT COALESCE(SUM(ecl_base), 0) FROM ecl_calculation
                JOIN (
                    SELECT facility_id, MAX(calc_date) AS latest
                    FROM ecl_calculation GROUP BY facility_id
                ) mx USING (facility_id)
                WHERE ecl_calculation.calc_date = mx.latest
            """)
        ).scalar()
        base_ecl = float(base_ecl or 0)

    scenarios = []
    for key, sc in MACRO_SCENARIOS.items():
        ecl_adj = round(base_ecl * sc['factor'], 2)
        scenarios.append({
            "scenario":     key,
            "label":        sc['label'],
            "factor":       sc['factor'],
            "weight":       sc['weight'],
            "ecl_adjusted": ecl_adj,
            "ecl_delta":    round(ecl_adj - base_ecl, 2),
            "delta_pct":    round((sc['factor'] - 1) * 100, 1),
        })

    weighted_ecl = round(sum(s['ecl_adjusted'] * MACRO_SCENARIOS[k]['weight']
                              for k, s in zip(MACRO_SCENARIOS.keys(), scenarios)), 2)

    return {
        "base_ecl":       round(base_ecl, 2),
        "weighted_ecl":   weighted_ecl,
        "scenarios":      scenarios,
        "scope":          facility_id or "portfolio",
    }
