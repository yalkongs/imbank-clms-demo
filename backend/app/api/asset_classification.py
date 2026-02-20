"""
자산건전성 분류 API
====================
금감원 기준 5단계 분류 자동화 (NORMAL/PRECAUTIONARY/SUBSTANDARD/DOUBTFUL/LOSS)
DPD · PD · EWS 연동, 충당금 부족액 분석
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import date, datetime
import uuid

from ..core.database import get_db
from ..services.calculations import classify_asset, PROVISION_RATES

router = APIRouter(prefix="/api/classification", tags=["Asset Classification"])

# 5단계 분류 레이블
CLASS_LABELS = {
    'NORMAL':        {'ko': '정상',    'color': 'green'},
    'PRECAUTIONARY': {'ko': '요주의',  'color': 'yellow'},
    'SUBSTANDARD':   {'ko': '고정',    'color': 'orange'},
    'DOUBTFUL':      {'ko': '회수의문','color': 'red'},
    'LOSS':          {'ko': '추정손실','color': 'darkred'},
}


def _get_facility_ews(db: Session, customer_id: str) -> Optional[float]:
    """최신 EWS 종합점수 조회"""
    row = db.execute(
        text("""
            SELECT composite_score FROM ews_alert
            WHERE customer_id = :cid
            ORDER BY created_at DESC LIMIT 1
        """),
        {"cid": customer_id}
    ).fetchone()
    return float(row[0]) if row else None


@router.get("/portfolio")
def get_portfolio_classification(
    base_date: Optional[str] = Query(None, description="기준일 (YYYY-MM-DD), 미입력 시 최신"),
    db: Session = Depends(get_db)
):
    """
    포트폴리오 건전성 현황
    — 5단계 분류별 잔액, 건수, 충당금 필요액 요약
    """
    if base_date:
        date_filter = "WHERE ac.base_date = :bd"
        params = {"bd": base_date}
    else:
        # 최신 기준일 기준
        date_filter = """
            JOIN (
                SELECT facility_id, MAX(base_date) AS latest
                FROM asset_classification GROUP BY facility_id
            ) mx ON ac.facility_id = mx.facility_id AND ac.base_date = mx.latest
            WHERE 1=1
        """
        params = {}

    rows = db.execute(
        text(f"""
            SELECT
                ac.classification,
                COUNT(*) AS cnt,
                SUM(ac.exposure_at_class) AS total_exposure,
                SUM(ac.required_provision) AS required_prov,
                SUM(ac.existing_provision) AS existing_prov,
                SUM(ac.provision_gap) AS prov_gap
            FROM asset_classification ac
            {date_filter}
            GROUP BY ac.classification
            ORDER BY
                CASE ac.classification
                    WHEN 'NORMAL' THEN 1
                    WHEN 'PRECAUTIONARY' THEN 2
                    WHEN 'SUBSTANDARD' THEN 3
                    WHEN 'DOUBTFUL' THEN 4
                    WHEN 'LOSS' THEN 5
                END
        """),
        params
    ).fetchall()

    total_exposure = sum((r[2] or 0) for r in rows)
    total_required = sum((r[3] or 0) for r in rows)
    total_existing = sum((r[4] or 0) for r in rows)
    total_gap      = sum((r[5] or 0) for r in rows)

    classification_data = []
    for r in rows:
        cls = r[0]
        meta = CLASS_LABELS.get(cls, {'ko': cls, 'color': 'gray'})
        exp  = r[2] or 0
        classification_data.append({
            "classification": cls,
            "label_ko":       meta['ko'],
            "color":          meta['color'],
            "count":          r[1],
            "exposure":       round(exp, 2),
            "exposure_share": round(exp / total_exposure * 100, 2) if total_exposure > 0 else 0,
            "required_provision": round(r[3] or 0, 2),
            "existing_provision": round(r[4] or 0, 2),
            "provision_gap":  round(r[5] or 0, 2),
            "provision_rate": PROVISION_RATES.get(cls, 0),
        })

    return {
        "base_date":           base_date or "최신",
        "total_exposure":      round(total_exposure, 2),
        "total_required_prov": round(total_required, 2),
        "total_existing_prov": round(total_existing, 2),
        "total_provision_gap": round(total_gap, 2),
        "npl_ratio": round(
            sum(r["exposure"] for r in classification_data
                if r["classification"] in ("SUBSTANDARD", "DOUBTFUL", "LOSS"))
            / total_exposure * 100, 2
        ) if total_exposure > 0 else 0,
        "by_classification": classification_data,
    }


@router.get("/facility/{facility_id}")
def get_facility_classification_history(
    facility_id: str,
    limit: int = Query(24, description="최대 조회 개월"),
    db: Session = Depends(get_db)
):
    """여신별 자산건전성 분류 이력 (월별 추이)"""
    rows = db.execute(
        text("""
            SELECT
                ac.class_id, ac.base_date, ac.classification, ac.prev_class,
                ac.dpd, ac.pd_based_class, ac.ews_based_class, ac.final_class_basis,
                ac.exposure_at_class, ac.provision_rate, ac.required_provision,
                ac.existing_provision, ac.provision_gap,
                ac.classified_by, ac.override_reason, ac.created_at,
                f.product_type, f.outstanding_amount, f.credit_grade,
                c.company_name
            FROM asset_classification ac
            JOIN facility f ON ac.facility_id = f.facility_id
            JOIN customer c ON ac.customer_id = c.customer_id
            WHERE ac.facility_id = :fid
            ORDER BY ac.base_date DESC
            LIMIT :lim
        """),
        {"fid": facility_id, "lim": limit}
    ).fetchall()

    history = []
    for r in rows:
        cls  = r[2]
        meta = CLASS_LABELS.get(cls, {'ko': cls, 'color': 'gray'})
        prev = r[3]
        migration = None
        if prev and prev != cls:
            prev_rank = list(CLASS_LABELS.keys()).index(prev) if prev in CLASS_LABELS else 0
            curr_rank = list(CLASS_LABELS.keys()).index(cls)  if cls  in CLASS_LABELS else 0
            migration = 'DOWNGRADE' if curr_rank > prev_rank else 'UPGRADE'

        history.append({
            "class_id":            r[0],
            "base_date":           str(r[1]),
            "classification":      cls,
            "label_ko":            meta['ko'],
            "color":               meta['color'],
            "prev_classification": prev,
            "migration":           migration,
            "dpd":                 r[4],
            "pd_based_class":      r[5],
            "ews_based_class":     r[6],
            "final_class_basis":   r[7],
            "exposure":            round(r[8] or 0, 2),
            "provision_rate":      round(r[9] or 0, 4),
            "required_provision":  round(r[10] or 0, 2),
            "existing_provision":  round(r[11] or 0, 2),
            "provision_gap":       round(r[12] or 0, 2),
            "classified_by":       r[13],
            "override_reason":     r[14],
        })

    return {
        "facility_id":    facility_id,
        "company_name":   rows[0][19] if rows else None,
        "product_type":   rows[0][16] if rows else None,
        "current_grade":  rows[0][18] if rows else None,
        "outstanding":    round(rows[0][17] or 0, 2) if rows else 0,
        "history":        history,
    }


@router.get("/customer/{customer_id}")
def get_customer_classification(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """고객별 여신 분류 현황 (여신별 최신 분류)"""
    rows = db.execute(
        text("""
            SELECT
                f.facility_id, f.product_type, f.outstanding_amount,
                ac.classification, ac.dpd, ac.exposure_at_class,
                ac.required_provision, ac.provision_gap, ac.base_date
            FROM facility f
            LEFT JOIN (
                SELECT ac1.*
                FROM asset_classification ac1
                JOIN (
                    SELECT facility_id, MAX(base_date) AS latest
                    FROM asset_classification GROUP BY facility_id
                ) mx ON ac1.facility_id = mx.facility_id AND ac1.base_date = mx.latest
            ) ac ON f.facility_id = ac.facility_id
            WHERE f.customer_id = :cid AND f.status = 'ACTIVE'
        """),
        {"cid": customer_id}
    ).fetchall()

    facilities = []
    worst_class = 'NORMAL'
    worst_rank  = 0
    class_order = list(CLASS_LABELS.keys())

    for r in rows:
        cls       = r[3] or 'NORMAL'
        cls_rank  = class_order.index(cls) if cls in class_order else 0
        if cls_rank > worst_rank:
            worst_rank  = cls_rank
            worst_class = cls

        meta = CLASS_LABELS.get(cls, {'ko': cls, 'color': 'gray'})
        facilities.append({
            "facility_id":    r[0],
            "product_type":   r[1],
            "outstanding":    round(r[2] or 0, 2),
            "classification": cls,
            "label_ko":       meta['ko'],
            "color":          meta['color'],
            "dpd":            r[4] or 0,
            "exposure":       round(r[5] or 0, 2),
            "required_prov":  round(r[6] or 0, 2),
            "provision_gap":  round(r[7] or 0, 2),
            "base_date":      str(r[8]) if r[8] else None,
        })

    return {
        "customer_id":         customer_id,
        "facility_count":      len(facilities),
        "worst_classification": worst_class,
        "worst_label_ko":      CLASS_LABELS.get(worst_class, {}).get('ko', worst_class),
        "total_outstanding":   round(sum(f["outstanding"] for f in facilities), 2),
        "total_required_prov": round(sum(f["required_prov"] for f in facilities), 2),
        "total_gap":           round(sum(f["provision_gap"] for f in facilities), 2),
        "facilities":          facilities,
    }


@router.post("/run")
def run_classification(
    base_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    월말 일괄 자산건전성 분류 실행
    — 모든 ACTIVE 여신에 대해 DPD/PD/EWS 기반 분류 산출 후 저장
    """
    bd = base_date or date.today().strftime('%Y-%m-%d')

    # 대상 여신 조회
    facilities = db.execute(
        text("""
            SELECT
                f.facility_id, f.customer_id, f.outstanding_amount,
                f.dpd, f.classification,
                c.credit_grade,
                rp.pd
            FROM facility f
            JOIN customer c ON f.customer_id = c.customer_id
            LEFT JOIN risk_parameter rp ON c.customer_id = rp.customer_id
            WHERE f.status = 'ACTIVE'
        """)
    ).fetchall()

    from ..services.calculations import GRADE_PD_MAP
    inserted = 0
    updated  = 0

    for fac in facilities:
        fid       = fac[0]
        cid       = fac[1]
        exposure  = fac[2] or 0
        dpd       = fac[3] or 0
        pd_val    = fac[6] or GRADE_PD_MAP.get(fac[5] or 'BBB', 0.02)
        ews_score = _get_facility_ews(db, cid)

        result = classify_asset(dpd, pd_val, ews_score)

        cls         = result['classification']
        prov_rate   = result['provision_rate']
        req_prov    = round(exposure * prov_rate, 2)
        # 현재 충당금: workout_case.provision_amount 합산
        ex_prov_row = db.execute(
            text("SELECT COALESCE(SUM(provision_amount),0) FROM workout_case WHERE customer_id=:cid"),
            {"cid": cid}
        ).scalar()
        ex_prov  = float(ex_prov_row or 0)
        prov_gap = round(req_prov - ex_prov, 2)

        # 이전 분류 조회
        prev_row = db.execute(
            text("""
                SELECT classification FROM asset_classification
                WHERE facility_id=:fid ORDER BY base_date DESC LIMIT 1
            """),
            {"fid": fid}
        ).fetchone()
        prev_cls = prev_row[0] if prev_row else None

        class_id = str(uuid.uuid4())
        db.execute(
            text("""
                INSERT INTO asset_classification
                    (class_id, facility_id, customer_id, base_date,
                     classification, prev_class,
                     dpd, pd_based_class, ews_based_class, final_class_basis,
                     exposure_at_class, provision_rate,
                     required_provision, existing_provision, provision_gap,
                     classified_by)
                VALUES
                    (:cid2, :fid, :cust, :bd,
                     :cls, :prev_cls,
                     :dpd, :pd_cls, :ews_cls, :basis,
                     :exp, :prate,
                     :req, :ex, :gap,
                     'SYSTEM')
                ON CONFLICT(facility_id, base_date)
                DO UPDATE SET
                    classification=excluded.classification,
                    prev_class=excluded.prev_class,
                    dpd=excluded.dpd,
                    pd_based_class=excluded.pd_based_class,
                    ews_based_class=excluded.ews_based_class,
                    final_class_basis=excluded.final_class_basis,
                    exposure_at_class=excluded.exposure_at_class,
                    provision_rate=excluded.provision_rate,
                    required_provision=excluded.required_provision,
                    existing_provision=excluded.existing_provision,
                    provision_gap=excluded.provision_gap
            """),
            {
                "cid2": class_id, "fid": fid, "cust": cid, "bd": bd,
                "cls": cls, "prev_cls": prev_cls,
                "dpd": dpd,
                "pd_cls":  result['pd_based_class'],
                "ews_cls": result['ews_based_class'],
                "basis":   result['final_class_basis'],
                "exp":     exposure, "prate": prov_rate,
                "req":     req_prov, "ex":    ex_prov, "gap": prov_gap,
            }
        )
        if prev_cls is None:
            inserted += 1
        else:
            updated += 1

        # facility.classification 동기화
        db.execute(
            text("UPDATE facility SET classification=:cls WHERE facility_id=:fid"),
            {"cls": cls, "fid": fid}
        )

    db.commit()
    return {
        "message":    f"분류 완료: {inserted}건 신규, {updated}건 갱신",
        "base_date":  bd,
        "total":      len(facilities),
        "inserted":   inserted,
        "updated":    updated,
    }


@router.get("/migration-matrix")
def get_migration_matrix(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    분류 이동 행렬 (Migration Matrix)
    — from_date → to_date 기간 중 분류 변동 현황
    """
    # 기간 미지정 시 최근 2개 기준일 자동 선택
    dates = db.execute(
        text("SELECT DISTINCT base_date FROM asset_classification ORDER BY base_date DESC LIMIT 2")
    ).fetchall()

    if len(dates) >= 2:
        to_dt   = to_date   or str(dates[0][0])
        from_dt = from_date or str(dates[1][0])
    elif len(dates) == 1:
        to_dt   = str(dates[0][0])
        from_dt = str(dates[0][0])
    else:
        return {"error": "분류 데이터 없음"}

    rows = db.execute(
        text("""
            SELECT
                a1.classification AS from_class,
                a2.classification AS to_class,
                COUNT(*) AS cnt,
                SUM(a2.exposure_at_class) AS exposure
            FROM asset_classification a1
            JOIN asset_classification a2
                ON a1.facility_id = a2.facility_id
            WHERE a1.base_date = :fd AND a2.base_date = :td
            GROUP BY a1.classification, a2.classification
        """),
        {"fd": from_dt, "td": to_dt}
    ).fetchall()

    matrix = {}
    for r in rows:
        fc = r[0]; tc = r[1]
        if fc not in matrix:
            matrix[fc] = {}
        matrix[fc][tc] = {"count": r[2], "exposure": round(r[3] or 0, 2)}

    class_keys = list(CLASS_LABELS.keys())
    result_matrix = []
    for fc in class_keys:
        row_data = {"from_class": fc, "from_label": CLASS_LABELS.get(fc, {}).get('ko', fc)}
        for tc in class_keys:
            row_data[tc] = matrix.get(fc, {}).get(tc, {"count": 0, "exposure": 0})
        result_matrix.append(row_data)

    return {
        "from_date":   from_dt,
        "to_date":     to_dt,
        "class_keys":  class_keys,
        "matrix":      result_matrix,
    }


@router.get("/provision-gap")
def get_provision_gap_analysis(
    db: Session = Depends(get_db)
):
    """충당금 부족액 분석 — 분류별 TOP 20 부족 여신"""
    rows = db.execute(
        text("""
            SELECT
                ac.facility_id, c.company_name, c.industry,
                ac.classification, ac.exposure_at_class,
                ac.required_provision, ac.existing_provision, ac.provision_gap,
                ac.base_date
            FROM asset_classification ac
            JOIN (
                SELECT facility_id, MAX(base_date) AS latest
                FROM asset_classification GROUP BY facility_id
            ) mx ON ac.facility_id = mx.facility_id AND ac.base_date = mx.latest
            JOIN facility f ON ac.facility_id = f.facility_id
            JOIN customer c ON f.customer_id = c.customer_id
            WHERE ac.provision_gap > 0
            ORDER BY ac.provision_gap DESC
            LIMIT 20
        """)
    ).fetchall()

    items = []
    for r in rows:
        cls  = r[3]
        meta = CLASS_LABELS.get(cls, {'ko': cls, 'color': 'gray'})
        items.append({
            "facility_id":      r[0],
            "company_name":     r[1],
            "industry":         r[2],
            "classification":   cls,
            "label_ko":         meta['ko'],
            "exposure":         round(r[4] or 0, 2),
            "required_provision": round(r[5] or 0, 2),
            "existing_provision": round(r[6] or 0, 2),
            "provision_gap":    round(r[7] or 0, 2),
            "base_date":        str(r[8]),
        })

    summary = db.execute(
        text("""
            SELECT
                COALESCE(SUM(CASE WHEN provision_gap > 0 THEN provision_gap ELSE 0 END), 0)
            FROM asset_classification ac
            JOIN (
                SELECT facility_id, MAX(base_date) AS latest
                FROM asset_classification GROUP BY facility_id
            ) mx ON ac.facility_id = mx.facility_id AND ac.base_date = mx.latest
        """)
    ).scalar()

    return {
        "total_provision_gap": round(float(summary or 0), 2),
        "top20_facilities":    items,
    }


@router.get("/trend")
def get_classification_trend(
    months: int = Query(12, description="조회 개월 수"),
    db: Session = Depends(get_db)
):
    """분류별 월별 추이 (잔액 기준)"""
    rows = db.execute(
        text("""
            SELECT
                base_date,
                classification,
                COUNT(*) AS cnt,
                SUM(exposure_at_class) AS exposure
            FROM asset_classification
            GROUP BY base_date, classification
            ORDER BY base_date DESC
            LIMIT :lim
        """),
        {"lim": months * 5}  # 5개 분류 × N개월
    ).fetchall()

    # 날짜별로 그룹핑
    timeline = {}
    for r in rows:
        bd  = str(r[0])
        cls = r[1]
        if bd not in timeline:
            timeline[bd] = {"base_date": bd}
        timeline[bd][cls] = {
            "count":    r[2],
            "exposure": round(r[3] or 0, 2),
        }

    trend = sorted(timeline.values(), key=lambda x: x["base_date"])[-months:]
    return {"trend": trend}
