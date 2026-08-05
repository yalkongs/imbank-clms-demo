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
from ..core.audit import record_audit
from ..core.config import AS_OF_DATE
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
    """최신 EWS 종합점수 조회 (ews_composite_score 테이블)"""
    row = db.execute(
        text("""
            SELECT composite_score FROM ews_composite_score
            WHERE customer_id = :cid
            ORDER BY score_date DESC LIMIT 1
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
    - 5단계 분류별 잔액, 건수, 충당금 필요액 요약
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
                f.facility_type, f.outstanding_amount, NULL AS credit_grade,
                c.customer_name
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
        "facility_type":  rows[0][16] if rows else None,
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
                f.facility_id, f.facility_type, f.outstanding_amount,
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
    - 모든 ACTIVE 여신에 대해 DPD/PD/EWS 기반 분류 산출 후 저장
    """
    bd = base_date or AS_OF_DATE.strftime('%Y-%m-%d')

    # 대상 여신 조회
    facilities = db.execute(
        text("""
            SELECT
                f.facility_id, f.customer_id, f.outstanding_amount,
                f.dpd, f.classification,
                NULL AS credit_grade,
                rp.ttc_pd
            FROM facility f
            JOIN customer c ON f.customer_id = c.customer_id
            LEFT JOIN loan_application la ON f.application_id = la.application_id
            LEFT JOIN risk_parameter rp ON la.application_id = rp.application_id
            WHERE f.status = 'ACTIVE'
        """)
    ).fetchall()

    # 담보 회수예상가액 (인정가액 합계) - 3개월 이상 연체 건의 분할분류에 쓴다.
    # 시행세칙 별표3: 회수예상가액 해당분은 고정, 초과분은 회수의문/추정손실.
    recoverable_map = {
        r[0]: float(r[1] or 0)
        for r in db.execute(text("""
            SELECT facility_id, SUM(recognized_value)
            FROM collateral WHERE facility_id IS NOT NULL
            GROUP BY facility_id
        """)).fetchall()
    }

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

        result = classify_asset(
            dpd, pd_val, ews_score,
            exposure=exposure,
            recoverable_value=recoverable_map.get(fid, 0.0),
        )

        cls         = result['classification']
        prov_rate   = result['provision_rate']
        # 분할분류가 적용된 건은 구간별 합계를, 아니면 단일 요율로 산출한다.
        req_prov    = result.get('required_provision')
        if req_prov is None:
            req_prov = round(exposure * prov_rate, 2)
        # 현재 충당금: 직전 기록의 existing_provision 사용 (없으면 필요충당금의 80%)
        ex_prov_row = db.execute(
            text("""
                SELECT existing_provision FROM asset_classification
                WHERE facility_id=:fid ORDER BY base_date DESC LIMIT 1
            """),
            {"fid": fid}
        ).fetchone()
        if ex_prov_row and ex_prov_row[0] is not None:
            # 직전 충당금 대비 이번 필요충당금 변동분의 80%를 적립으로 가정
            ex_prov = round(min(float(ex_prov_row[0]) * 1.05, req_prov * 0.90), 2)
        else:
            ex_prov = round(req_prov * 0.80, 2)
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

    record_audit(db, "CLASSIFICATION_RUN", "asset_classification", bd,
                 after={"inserted": inserted, "updated": updated})
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
    - from_date → to_date 기간 중 분류 변동 현황
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
    """충당금 부족액 분석 - 분류별 TOP 20 부족 여신"""
    rows = db.execute(
        text("""
            SELECT
                ac.facility_id, c.customer_name, c.industry_name,
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


# ─────────────────────────────────────────────────────────
# 3체계 대사표 (제3자 리뷰 ⑧): 감독분류 × IFRS9 Stage × EWS 등급을
# 하나로 합치지 않고 병렬 대사한다. 불일치는 자동 설명 코드를 부여하고,
# 설명이 안 되는 조합만 '개별 검토' 로 표기한다.
# ─────────────────────────────────────────────────────────

_RECON_CLS_ORDER = ["NORMAL", "PRECAUTIONARY", "SUBSTANDARD", "DOUBTFUL", "LOSS"]
_RECON_CLS_KO = {"NORMAL": "정상", "PRECAUTIONARY": "요주의", "SUBSTANDARD": "고정",
                 "DOUBTFUL": "회수의문", "LOSS": "추정손실"}


def _recon_explain(cls: str, stage: int, ews_grade: str, dpd: int) -> tuple[str, bool]:
    """(설명, 개별검토 필요 여부). 세 체계는 목적이 달라 불일치 자체는 정상이다."""
    npl = cls in ("SUBSTANDARD", "DOUBTFUL", "LOSS")
    if cls == "NORMAL" and stage == 2:
        return "SICR 선행 인식 - 회계(전 생애 ECL)가 감독분류보다 먼저 반응 (정상 작동)", False
    if cls == "PRECAUTIONARY" and stage == 2:
        return "요주의·Stage 2 정합", False
    if npl and stage == 3:
        return "신용손상·고정이하 정합", False
    if cls == "NORMAL" and stage == 1:
        return "정합", False
    if cls == "PRECAUTIONARY" and stage == 1:
        return "감독 보수주의(DPD 30일+) 선행 - SICR 미충족. ECL 개별 재검토 권고", True
    if npl and stage < 3:
        return "감독분류 부실인데 회계 손상 미인식 - 즉시 개별 검토 대상", True
    if cls == "NORMAL" and stage == 3:
        return "회계 손상인데 감독분류 정상 - 분류 재실행 필요", True
    return "기타 조합 - 개별 검토", True


@router.get("/reconciliation")
def get_reconciliation(db: Session = Depends(get_db)):
    """시설별 최신 감독분류·Stage·EWS 를 병렬 대사"""
    rows = db.execute(text("""
        SELECT ac.facility_id, ac.customer_id, c.customer_name,
               ac.classification, ac.dpd, ac.exposure_at_class,
               e.stage, e.sicr_reason,
               ew.ews_grade, ew.composite_score
        FROM asset_classification ac
        JOIN (SELECT facility_id, MAX(base_date) latest
              FROM asset_classification GROUP BY facility_id) mx
          ON mx.facility_id = ac.facility_id AND mx.latest = ac.base_date
        LEFT JOIN (SELECT e1.facility_id, e1.stage, e1.sicr_reason
                   FROM ecl_calculation e1
                   JOIN (SELECT facility_id, MAX(calc_date) latest
                         FROM ecl_calculation GROUP BY facility_id) m2
                     ON m2.facility_id = e1.facility_id AND m2.latest = e1.calc_date) e
          ON e.facility_id = ac.facility_id
        LEFT JOIN (SELECT customer_id, ews_grade, composite_score,
                          ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY score_date DESC) rn
                   FROM ews_composite_score) ew
          ON ew.customer_id = ac.customer_id AND ew.rn = 1
        LEFT JOIN customer c ON c.customer_id = ac.customer_id
    """)).fetchall()

    matrix: dict = {}
    mismatches = []
    consistent = 0
    for fac_id, cust_id, cname, cls, dpd, exp, stage, sicr, ews_g, ews_s in rows:
        stage = stage or 1
        key = (cls, stage)
        cell = matrix.setdefault(key, {"count": 0, "exposure": 0.0})
        cell["count"] += 1
        cell["exposure"] += exp or 0
        explain, needs_review = _recon_explain(cls, stage, ews_g or "", dpd or 0)
        if cls == "NORMAL" and stage == 1:
            consistent += 1
        else:
            mismatches.append({
                "facility_id": fac_id, "customer_id": cust_id, "customer_name": cname,
                "classification": _RECON_CLS_KO.get(cls, cls), "stage": stage,
                "sicr_reason": sicr, "ews_grade": ews_g, "ews_score": ews_s,
                "dpd": dpd, "exposure": round(exp or 0, 2),
                "explanation": explain, "needs_review": needs_review,
            })
    mismatches.sort(key=lambda m: (not m["needs_review"], -m["exposure"]))

    return {
        "matrix": [
            {"classification": _RECON_CLS_KO[c], "stage": s,
             "count": matrix[(c, s)]["count"],
             "exposure": round(matrix[(c, s)]["exposure"], 2)}
            for c in _RECON_CLS_ORDER for s in (1, 2, 3) if (c, s) in matrix
        ],
        "total": len(rows),
        "consistent": consistent,
        "mismatch_count": len(mismatches),
        "needs_review_count": sum(1 for m in mismatches if m["needs_review"]),
        "mismatches": mismatches[:60],
        "note": "세 체계(감독분류·IFRS9 Stage·EWS)는 목적이 달라 단일 등급으로 통합하지 않고 "
                "병렬 대사한다. 불일치 중 규정상 자연스러운 조합은 설명 코드로, "
                "그 외는 개별 검토로 표기.",
    }
