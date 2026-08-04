"""
연체 관리 API
==============
DPD 추적, 연체 단계 관리, 추심 활동 기록, Roll Rate 분석
EWS/Workout 자동 연결 트리거
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import date, timedelta
import uuid

from ..core.database import get_db
from ..core.config import AS_OF_DATE
from ..services.calculations import determine_delinquency_stage

router = APIRouter(prefix="/api/delinquency", tags=["Delinquency Management"])

# 연체 단계 메타
STAGE_META = {
    'CURRENT':  {'ko': '정상',   'color': 'green',  'dpd_range': '0일'},
    'EARLY':    {'ko': '초기연체', 'color': 'yellow', 'dpd_range': '1-30일'},
    'MID':      {'ko': '중기연체', 'color': 'orange', 'dpd_range': '31-60일'},
    'LATE':     {'ko': '장기연체', 'color': 'red',    'dpd_range': '61-90일'},
    'NPL':      {'ko': '부실채권', 'color': 'darkred','dpd_range': '91-180일'},
    'WRITEOFF': {'ko': '상각대상', 'color': 'black',  'dpd_range': '181일+'},
}


@router.get("/dashboard")
def get_delinquency_dashboard(
    db: Session = Depends(get_db)
):
    """
    연체 현황 대시보드
    - DPD 버킷별 잔액·건수, 연체율, 최근 7일 신규 연체
    """
    # 전체 여신 잔액
    total_outstanding = db.execute(
        text("SELECT COALESCE(SUM(outstanding_amount), 0) FROM facility WHERE status='ACTIVE'")
    ).scalar()
    total_outstanding = float(total_outstanding or 0)

    # 연체 단계별 현황
    rows = db.execute(
        text("""
            SELECT
                d.delinquency_stage,
                COUNT(*) AS cnt,
                SUM(d.overdue_amount) AS overdue_amt,
                SUM(f.outstanding_amount) AS exposure
            FROM delinquency_record d
            JOIN facility f ON d.facility_id = f.facility_id
            WHERE d.status = 'OPEN'
            GROUP BY d.delinquency_stage
        """)
    ).fetchall()

    bucket_data = {}
    for r in rows:
        stg = r[0] or 'EARLY'
        bucket_data[stg] = {
            "stage":        stg,
            "label_ko":     STAGE_META.get(stg, {}).get('ko', stg),
            "color":        STAGE_META.get(stg, {}).get('color', 'gray'),
            "dpd_range":    STAGE_META.get(stg, {}).get('dpd_range', ''),
            "count":        r[1],
            "overdue_amt":  round(r[2] or 0, 2),
            "exposure":     round(r[3] or 0, 2),
        }

    # 전체 연체 익스포저 합계
    total_delinquent = sum(b['exposure'] for b in bucket_data.values())
    delinquency_rate = round(total_delinquent / total_outstanding * 100, 3) if total_outstanding > 0 else 0

    # 연체 91일 이상 익스포저.
    # 주의: 이 값은 '연체일수' 기준이라 감독규정상 NPL(고정이하여신비율)과 다르다.
    # 정식 NPL 은 자산건전성 분류의 고정+회수의문+추정손실 기준으로,
    # /api/classification/portfolio 의 npl_ratio 를 쓴다.
    # 응답 필드명은 하위호환을 위해 npl_ratio 를 유지하되 화면 라벨은
    # '91일+ 연체비율' 로 표기한다.
    npl_exposure = sum(
        b['exposure'] for k, b in bucket_data.items() if k in ('NPL', 'WRITEOFF')
    )
    npl_ratio = round(npl_exposure / total_outstanding * 100, 3) if total_outstanding > 0 else 0

    # 최근 7일 신규 연체
    seven_days_ago = (AS_OF_DATE - timedelta(days=7)).strftime('%Y-%m-%d')
    new_7d = db.execute(
        text("""
            SELECT COUNT(*), COALESCE(SUM(overdue_amount), 0)
            FROM delinquency_record
            WHERE overdue_date >= :dt
        """),
        {"dt": seven_days_ago}
    ).fetchone()

    # 오늘 기준 DPD 업데이트 (연체 오픈 건)
    open_records = db.execute(
        text("SELECT delinquency_id, overdue_date FROM delinquency_record WHERE status='OPEN'")
    ).fetchall()
    today = AS_OF_DATE
    for rec in open_records:
        try:
            od = date.fromisoformat(str(rec[1]))
            dpd = (today - od).days
            stage = determine_delinquency_stage(dpd)
            db.execute(
                text("""
                    UPDATE delinquency_record
                    SET dpd=:dpd, delinquency_stage=:stage
                    WHERE delinquency_id=:did
                """),
                {"dpd": dpd, "stage": stage, "did": rec[0]}
            )
        except Exception:
            pass
    db.commit()

    return {
        "total_outstanding":   round(total_outstanding, 2),
        "total_delinquent":    round(total_delinquent, 2),
        "delinquency_rate":    delinquency_rate,
        "npl_exposure":        round(npl_exposure, 2),
        "npl_ratio":           npl_ratio,
        "new_7days":           {"count": new_7d[0], "amount": round(float(new_7d[1]), 2)},
        "buckets":             list(bucket_data.values()),
    }


@router.get("/active")
def get_active_delinquencies(
    stage: Optional[str] = Query(None, description="EARLY/MID/LATE/NPL/WRITEOFF"),
    limit: int = Query(50),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """현재 연체 목록 (status=OPEN)"""
    where = "WHERE d.status = 'OPEN'"
    params: dict = {"lim": limit, "off": offset}
    if stage:
        where += " AND d.delinquency_stage = :stage"
        params["stage"] = stage

    rows = db.execute(
        text(f"""
            SELECT
                d.delinquency_id, d.facility_id, d.customer_id,
                d.overdue_date, d.overdue_amount, d.overdue_type,
                d.dpd, d.delinquency_stage, d.assigned_officer,
                f.outstanding_amount, f.facility_type,
                COALESCE(col.recognized, 0) AS collateral_value,
                c.customer_name, c.industry_name
            FROM delinquency_record d
            JOIN facility f ON d.facility_id = f.facility_id
            JOIN customer c ON d.customer_id = c.customer_id
            LEFT JOIN (
                SELECT facility_id, SUM(recognized_value) AS recognized
                FROM collateral GROUP BY facility_id
            ) col ON f.facility_id = col.facility_id
            {where}
            ORDER BY d.dpd DESC
            LIMIT :lim OFFSET :off
        """),
        params
    ).fetchall()

    items = []
    for r in rows:
        stg  = r[7] or 'EARLY'
        meta = STAGE_META.get(stg, {'ko': stg, 'color': 'gray'})
        items.append({
            "delinquency_id":  r[0],
            "facility_id":     r[1],
            "customer_id":     r[2],
            "company_name":    r[12],
            "industry":        r[13],
            "overdue_date":    str(r[3]),
            "overdue_amount":  round(r[4] or 0, 2),
            "overdue_type":    r[5],
            "dpd":             r[6] or 0,
            "stage":           stg,
            "stage_label":     meta['ko'],
            "stage_color":     meta['color'],
            "outstanding":     round(r[9] or 0, 2),
            "facility_type":   r[10],
            "collateral_value": round(r[11] or 0, 2),
            "unsecured_exposure": round(max((r[9] or 0) - (r[11] or 0), 0), 2),
            "credit_grade":    None,
            "assigned_officer": r[8],
        })

    return {"total": len(items), "items": items}


@router.get("/facility/{facility_id}")
def get_facility_delinquency_history(
    facility_id: str,
    db: Session = Depends(get_db)
):
    """여신별 연체 이력 + 추심 활동"""
    delinquencies = db.execute(
        text("""
            SELECT
                d.delinquency_id, d.overdue_date, d.overdue_amount, d.overdue_type,
                d.dpd, d.delinquency_stage, d.status,
                d.resolved_date, d.resolved_amount, d.resolution_type,
                d.assigned_officer
            FROM delinquency_record d
            WHERE d.facility_id = :fid
            ORDER BY d.overdue_date DESC
        """),
        {"fid": facility_id}
    ).fetchall()

    result = []
    for d in delinquencies:
        did = d[0]
        # 추심 활동 조회
        activities = db.execute(
            text("""
                SELECT activity_type, contact_result, activity_date,
                       promised_date, promised_amount, notes, officer
                FROM collection_activity
                WHERE delinquency_id = :did
                ORDER BY activity_date DESC
            """),
            {"did": did}
        ).fetchall()

        stg  = d[5] or 'EARLY'
        meta = STAGE_META.get(stg, {'ko': stg, 'color': 'gray'})
        result.append({
            "delinquency_id": did,
            "overdue_date":   str(d[1]),
            "overdue_amount": round(d[2] or 0, 2),
            "overdue_type":   d[3],
            "dpd":            d[4] or 0,
            "stage":          stg,
            "stage_label":    meta['ko'],
            "status":         d[6],
            "resolved_date":  str(d[7]) if d[7] else None,
            "resolved_amount": round(d[8] or 0, 2) if d[8] else None,
            "resolution_type": d[9],
            "assigned_officer": d[10],
            "activities": [
                {
                    "type":           a[0],
                    "result":         a[1],
                    "date":           str(a[2]),
                    "promised_date":  str(a[3]) if a[3] else None,
                    "promised_amount": round(a[4] or 0, 2) if a[4] else None,
                    "notes":          a[5],
                    "officer":        a[6],
                }
                for a in activities
            ],
        })

    facility = db.execute(
        text("""
            SELECT f.outstanding_amount, f.facility_type, c.customer_name, f.dpd, f.max_dpd_12m
            FROM facility f JOIN customer c ON f.customer_id = c.customer_id
            WHERE f.facility_id = :fid
        """),
        {"fid": facility_id}
    ).fetchone()

    return {
        "facility_id":   facility_id,
        "company_name":  facility[2] if facility else None,
        "facility_type": facility[1] if facility else None,
        "outstanding":   round(facility[0] or 0, 2) if facility else 0,
        "current_dpd":   facility[3] or 0 if facility else 0,
        "max_dpd_12m":   facility[4] or 0 if facility else 0,
        "delinquencies": result,
    }


@router.get("/transfer-candidates")
def get_transfer_candidates(db: Session = Depends(get_db)):
    """워크아웃 이관 임박 여신 (DPD 75~89) - 90일 도달 시 자동 이관 대상.

    이관 전 마지막 관리 기회를 놓치지 않도록 별도 목록으로 노출한다.
    이관 실행은 기존 POST /api/workout/auto-transfer-npl 을 쓴다.
    """
    rows = db.execute(text("""
        SELECT d.delinquency_id, d.facility_id, c.customer_name, d.dpd,
               d.overdue_amount, f.outstanding_amount,
               COALESCE(col.recognized, 0) AS collateral
        FROM delinquency_record d
        JOIN facility f ON d.facility_id = f.facility_id
        JOIN customer c ON d.customer_id = c.customer_id
        LEFT JOIN (
            SELECT facility_id, SUM(recognized_value) AS recognized
            FROM collateral GROUP BY facility_id
        ) col ON f.facility_id = col.facility_id
        WHERE d.status = 'OPEN' AND d.dpd BETWEEN 75 AND 89
        ORDER BY d.dpd DESC
    """)).fetchall()
    return [
        {
            "delinquency_id": r[0], "facility_id": r[1], "customer_name": r[2],
            "dpd": r[3], "days_to_transfer": 90 - r[3],
            "overdue_amount": round(r[4] or 0, 2),
            "outstanding": round(r[5] or 0, 2),
            "unsecured_exposure": round(max((r[5] or 0) - (r[6] or 0), 0), 2),
        }
        for r in rows
    ]


@router.get("/roll-rate")
def get_roll_rate(
    months: int = Query(6, description="분석 기간 (개월)"),
    db: Session = Depends(get_db)
):
    """
    Roll Rate 분석
    - DPD 버킷별 다음 기간 이동률 (전이 행렬)
    """
    rows = db.execute(
        text("""
            SELECT
                d1.delinquency_stage AS from_stage,
                d2.delinquency_stage AS to_stage,
                COUNT(*) AS cnt
            FROM delinquency_record d1
            JOIN delinquency_record d2 ON d1.facility_id = d2.facility_id
            WHERE d1.delinquency_id != d2.delinquency_id
              AND d2.overdue_date > d1.overdue_date
              AND d2.overdue_date <= date(d1.overdue_date, '+30 days')
            GROUP BY d1.delinquency_stage, d2.delinquency_stage
        """)
    ).fetchall()

    stages = ['EARLY', 'MID', 'LATE', 'NPL', 'WRITEOFF']
    matrix = {s: {t: 0 for t in stages + ['CURED']} for s in stages}

    for r in rows:
        fs = r[0]; ts = r[1]
        if fs in matrix and ts in matrix[fs]:
            matrix[fs][ts] += r[2]

    # 비율 계산
    roll_rates = []
    for fs in stages:
        row_total = sum(matrix[fs].values())
        if row_total == 0:
            continue
        entry = {"from_stage": fs, "from_label": STAGE_META.get(fs, {}).get('ko', fs), "total": row_total}
        for ts in stages + ['CURED']:
            cnt = matrix[fs].get(ts, 0)
            entry[f"to_{ts.lower()}_rate"] = round(cnt / row_total * 100, 1)
            entry[f"to_{ts.lower()}_cnt"]  = cnt
        roll_rates.append(entry)

    return {"roll_rates": roll_rates, "stages": stages}


@router.get("/vintage-by-region")
def get_vintage_by_region(db: Session = Depends(get_db)):
    """지역별 신규취급 빈티지 곡선 - 시중은행 전환 후 수도권 확장 리스크 감시.

    연고지(대구경북)는 관계형 금융 정보가 있어 조기 부실이 낮고, 신규 진출한
    수도권은 초기 부실률이 높게 시작해 심사 데이터가 쌓이며 개선되는지를 본다.
    코호트(취급월)별 MOB 3/6/12 연체율을 지역끼리 비교한다.
    """
    rows = db.execute(text("""
        SELECT vintage_month, cohort_value,
               mob_3_delinquent_rate, mob_6_delinquent_rate, mob_12_delinquent_rate,
               origination_count, origination_amount
        FROM vintage_analysis
        WHERE cohort_type = 'REGION'
        ORDER BY vintage_month, cohort_value
    """)).fetchall()

    labels = {"CAPITAL": "수도권", "DAEGU_GB": "대구경북", "BUSAN_GN": "부산경남"}
    months: dict = {}
    for r in rows:
        m = months.setdefault(r[0], {"month": r[0]})
        code = r[1]
        m[f"{code}_mob3"] = round((r[2] or 0) * 100, 2)
        m[f"{code}_mob6"] = round((r[3] or 0) * 100, 2)
        m[f"{code}_mob12"] = round((r[4] or 0) * 100, 2)

    # 지역별 최근 6개 코호트 평균 (요약 카드용)
    summary = []
    for code, label in labels.items():
        recent = [r for r in rows if r[1] == code][-6:]
        if not recent:
            continue
        summary.append({
            "region": code,
            "region_label": label,
            "avg_mob3": round(sum((r[2] or 0) for r in recent) / len(recent) * 100, 2),
            "avg_mob12": round(sum((r[4] or 0) for r in recent) / len(recent) * 100, 2),
            "cohort_count": len(recent),
        })

    return {"labels": labels, "curve": list(months.values()), "summary": summary}


@router.get("/vintage-delinquency")
def get_vintage_delinquency(
    db: Session = Depends(get_db)
):
    """빈티지별 연체율 곡선 (여신 승인연도별 누적 연체 발생률)"""
    rows = db.execute(
        text("""
            SELECT
                strftime('%Y', f.contract_date) AS vintage_year,
                COUNT(DISTINCT f.facility_id) AS total_facilities,
                COUNT(DISTINCT d.facility_id) AS delinquent_facilities,
                SUM(f.outstanding_amount) AS total_exposure,
                SUM(CASE WHEN d.delinquency_id IS NOT NULL THEN f.outstanding_amount ELSE 0 END) AS delinquent_exposure
            FROM facility f
            LEFT JOIN delinquency_record d ON f.facility_id = d.facility_id
            WHERE f.contract_date IS NOT NULL
            GROUP BY vintage_year
            ORDER BY vintage_year
        """)
    ).fetchall()

    vintages = []
    for r in rows:
        total   = r[1] or 0
        delinq  = r[2] or 0
        exp     = r[3] or 0
        delinq_exp = r[4] or 0
        vintages.append({
            "vintage_year":         r[0],
            "total_facilities":     total,
            "delinquent_facilities": delinq,
            "delinquency_rate_count": round(delinq / total * 100, 2) if total > 0 else 0,
            "total_exposure":       round(exp, 2),
            "delinquent_exposure":  round(delinq_exp, 2),
            "delinquency_rate_amt": round(delinq_exp / exp * 100, 2) if exp > 0 else 0,
        })

    return {"vintages": vintages}


@router.post("/collection-activity")
def record_collection_activity(
    delinquency_id: str,
    facility_id: str,
    activity_type: str,
    contact_result: Optional[str] = None,
    promised_date: Optional[str] = None,
    promised_amount: Optional[float] = None,
    notes: Optional[str] = None,
    officer: Optional[str] = "시스템",
    db: Session = Depends(get_db)
):
    """추심 활동 기록"""
    # 연체 레코드 확인
    delinq = db.execute(
        text("SELECT delinquency_id FROM delinquency_record WHERE delinquency_id=:did"),
        {"did": delinquency_id}
    ).fetchone()
    if not delinq:
        raise HTTPException(status_code=404, detail="연체 레코드 없음")

    activity_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO collection_activity
                (activity_id, delinquency_id, facility_id, activity_date,
                 activity_type, contact_result, promised_date, promised_amount,
                 notes, officer)
            VALUES
                (:aid, :did, :fid, :today,
                 :atype, :result, :pdate, :pamount,
                 :notes, :officer)
        """),
        {
            "aid":     activity_id,
            "did":     delinquency_id,
            "fid":     facility_id,
            "today":   AS_OF_DATE.strftime('%Y-%m-%d'),
            "atype":   activity_type,
            "result":  contact_result,
            "pdate":   promised_date,
            "pamount": promised_amount,
            "notes":   notes,
            "officer": officer,
        }
    )
    db.commit()

    return {
        "message":     "추심 활동 기록 완료",
        "activity_id": activity_id,
        "delinquency_id": delinquency_id,
        "activity_type":  activity_type,
        "contact_result": contact_result,
    }


@router.get("/collection-performance")
def get_collection_performance(
    months: int = Query(12, description="분석 기간(개월)"),
    db: Session = Depends(get_db)
):
    """추심 성과 - 약속이행률, 회수율, 활동 유형별 효과"""
    start_date = (AS_OF_DATE - timedelta(days=months * 30)).strftime('%Y-%m-%d')

    # 활동 유형별 집계
    type_rows = db.execute(
        text("""
            SELECT
                activity_type,
                COUNT(*) AS total,
                SUM(CASE WHEN contact_result = 'REACHED' THEN 1 ELSE 0 END) AS reached,
                SUM(CASE WHEN contact_result = 'PROMISE_TO_PAY' THEN 1 ELSE 0 END) AS promised,
                COALESCE(SUM(promised_amount), 0) AS total_promised
            FROM collection_activity
            WHERE activity_date >= :sd
            GROUP BY activity_type
            ORDER BY total DESC
        """),
        {"sd": start_date}
    ).fetchall()

    by_type = []
    for r in type_rows:
        total = r[1] or 0
        by_type.append({
            "activity_type":    r[0],
            "total":            total,
            "reached":          r[2] or 0,
            "reached_rate":     round((r[2] or 0) / total * 100, 1) if total > 0 else 0,
            "promised":         r[3] or 0,
            "promise_rate":     round((r[3] or 0) / total * 100, 1) if total > 0 else 0,
            "total_promised":   round(float(r[4]), 2),
        })

    # 해결된 연체 현황
    resolved = db.execute(
        text("""
            SELECT
                resolution_type,
                COUNT(*) AS cnt,
                COALESCE(SUM(resolved_amount), 0) AS recovered,
                COALESCE(SUM(overdue_amount), 0) AS original
            FROM delinquency_record
            WHERE status != 'OPEN' AND resolved_date >= :sd
            GROUP BY resolution_type
        """),
        {"sd": start_date}
    ).fetchall()

    recovery_data = []
    total_original  = 0
    total_recovered = 0
    for r in resolved:
        original  = float(r[3] or 0)
        recovered = float(r[2] or 0)
        total_original  += original
        total_recovered += recovered
        recovery_data.append({
            "resolution_type":  r[0],
            "count":            r[1],
            "original_amount":  round(original, 2),
            "recovered_amount": round(recovered, 2),
            "recovery_rate":    round(recovered / original * 100, 2) if original > 0 else 0,
        })

    return {
        "period_months":   months,
        "by_activity_type": by_type,
        "recovery_summary": {
            "total_original":   round(total_original, 2),
            "total_recovered":  round(total_recovered, 2),
            "overall_recovery_rate": round(total_recovered / total_original * 100, 2) if total_original > 0 else 0,
        },
        "by_resolution_type": recovery_data,
    }
