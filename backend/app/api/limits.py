"""
한도관리 API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..core.database import get_db

router = APIRouter(prefix="/api/limits", tags=["Limits"])


@router.get("")
def get_all_limits(db: Session = Depends(get_db)):
    """전체 한도 현황"""
    results = db.execute(text("""
        SELECT ld.limit_id, ld.limit_name, ld.limit_type, ld.dimension_type,
               ld.dimension_code, ld.limit_amount, ld.warning_level, ld.alert_level,
               ld.critical_level, le.exposure_amount, le.reserved_amount,
               le.available_amount, le.utilization_rate, le.status,
               CASE
                   WHEN ld.dimension_type = 'INDUSTRY' THEN im.industry_name
                   WHEN ld.dimension_type = 'SINGLE' THEN '동일인'
                   WHEN ld.dimension_type = 'GROUP' THEN '동일그룹'
                   ELSE ld.dimension_code
               END as target_name
        FROM limit_definition ld
        LEFT JOIN limit_exposure le ON ld.limit_id = le.limit_id
        LEFT JOIN industry_master im ON ld.dimension_code = im.industry_code
        WHERE ld.status = 'ACTIVE'
        ORDER BY ld.limit_type, le.utilization_rate DESC
    """)).fetchall()

    return [
        {
            "limit_id": r[0],
            "limit_name": r[1],
            "limit_type": r[2],
            "dimension_type": r[3],
            "dimension_code": r[4],
            "limit_amount": r[5],
            "warning_level": r[6],
            "warning_threshold": r[6],  # 프론트엔드 호환
            "alert_level": r[7],
            "critical_level": r[8],
            "critical_threshold": r[8],  # 프론트엔드 호환
            "exposure_amount": r[9] or 0,
            "current_usage": r[9] or 0,  # 프론트엔드 호환
            "reserved_amount": r[10] or 0,
            "available_amount": r[11] or (r[5] - (r[9] or 0)),
            "utilization_rate": r[12] or 0,
            "status": r[13] or "NORMAL",
            "target_name": r[14] or r[4],  # 프론트엔드 호환
            "target_id": r[4]  # 프론트엔드 호환
        }
        for r in results
    ]


@router.get("/summary")
def get_limits_summary(db: Session = Depends(get_db)):
    """한도 현황 요약"""

    # 상태별 카운트
    by_status = db.execute(text("""
        SELECT le.status, COUNT(*) as count
        FROM limit_exposure le
        GROUP BY le.status
    """)).fetchall()

    # 유형별 현황
    by_type = db.execute(text("""
        SELECT ld.limit_type, COUNT(*) as count,
               SUM(ld.limit_amount) as total_limit,
               SUM(le.exposure_amount) as total_exposure
        FROM limit_definition ld
        LEFT JOIN limit_exposure le ON ld.limit_id = le.limit_id
        WHERE ld.status = 'ACTIVE'
        GROUP BY ld.limit_type
    """)).fetchall()

    # 위험 한도 (사용률 90% 이상)
    critical_limits = db.execute(text("""
        SELECT ld.limit_id, ld.limit_name, ld.dimension_code,
               ld.limit_amount, le.exposure_amount, le.utilization_rate
        FROM limit_definition ld
        JOIN limit_exposure le ON ld.limit_id = le.limit_id
        WHERE le.utilization_rate >= 90
        ORDER BY le.utilization_rate DESC
    """)).fetchall()

    return {
        "by_status": {r[0]: r[1] for r in by_status},
        "by_type": [
            {
                "type": r[0],
                "count": r[1],
                "total_limit": r[2],
                "total_exposure": r[3],
                "utilization": r[3] / r[2] * 100 if r[2] else 0
            }
            for r in by_type
        ],
        "critical_limits": [
            {
                "limit_id": r[0],
                "limit_name": r[1],
                "dimension_code": r[2],
                "limit_amount": r[3],
                "exposure_amount": r[4],
                "utilization_rate": r[5]
            }
            for r in critical_limits
        ]
    }


@router.get("/industry")
def get_industry_limits(db: Session = Depends(get_db)):
    """산업별 한도 현황"""
    results = db.execute(text("""
        SELECT ld.limit_id, ld.limit_name, ld.dimension_code,
               im.industry_name, ld.limit_amount,
               le.exposure_amount, le.utilization_rate, le.status,
               irs.strategy_code
        FROM limit_definition ld
        LEFT JOIN limit_exposure le ON ld.limit_id = le.limit_id
        LEFT JOIN industry_master im ON ld.dimension_code = im.industry_code
        LEFT JOIN (
            SELECT DISTINCT industry_code, strategy_code
            FROM industry_rating_strategy
            WHERE rating_bucket = 'AAA_AA'
        ) irs ON ld.dimension_code = irs.industry_code
        WHERE ld.dimension_type = 'INDUSTRY' AND ld.status = 'ACTIVE'
        ORDER BY le.utilization_rate DESC
    """)).fetchall()

    return [
        {
            "limit_id": r[0],
            "limit_name": r[1],
            "industry_code": r[2],
            "industry_name": r[3],
            "limit_amount": r[4],
            "limit": r[4],  # 프론트엔드 호환
            "exposure_amount": r[5] or 0,
            "current": r[5] or 0,  # 프론트엔드 호환
            "utilization_rate": r[6] or 0,
            "status": r[7] or "NORMAL",
            "strategy_code": r[8]
        }
        for r in results
    ]


@router.get("/check")
def check_limits(
    customer_id: str,
    amount: float,
    industry_code: str = None,
    db: Session = Depends(get_db)
):
    """한도 점검"""

    results = []

    # 동일인 한도
    single_limit = db.execute(text("""
        SELECT ld.limit_id, ld.limit_name, ld.limit_amount,
               COALESCE(SUM(f.outstanding_amount), 0) as current_exposure
        FROM limit_definition ld
        LEFT JOIN facility f ON f.customer_id = :cust_id AND f.status = 'ACTIVE'
        WHERE ld.limit_type = 'REGULATORY' AND ld.dimension_type = 'SINGLE'
        GROUP BY ld.limit_id
    """), {"cust_id": customer_id}).fetchone()

    if single_limit:
        available = single_limit[2] - single_limit[3]
        results.append({
            "limit_type": "동일인 한도",
            "limit_amount": single_limit[2],
            "current_exposure": single_limit[3],
            "requested_amount": amount,
            "available": available,
            "after_exposure": single_limit[3] + amount,
            "utilization_after": (single_limit[3] + amount) / single_limit[2] * 100,
            "status": "OK" if amount <= available else "EXCEEDED",
            "is_sufficient": amount <= available
        })

    # 산업별 한도
    if industry_code:
        industry_limit = db.execute(text("""
            SELECT ld.limit_id, ld.limit_name, ld.limit_amount,
                   le.exposure_amount
            FROM limit_definition ld
            LEFT JOIN limit_exposure le ON ld.limit_id = le.limit_id
            WHERE ld.dimension_type = 'INDUSTRY' AND ld.dimension_code = :ind_code
        """), {"ind_code": industry_code}).fetchone()

        if industry_limit:
            current = industry_limit[3] or 0
            available = industry_limit[2] - current
            results.append({
                "limit_type": "산업한도",
                "limit_amount": industry_limit[2],
                "current_exposure": current,
                "requested_amount": amount,
                "available": available,
                "after_exposure": current + amount,
                "utilization_after": (current + amount) / industry_limit[2] * 100,
                "status": "OK" if amount <= available else "EXCEEDED",
                "is_sufficient": amount <= available
            })

    all_sufficient = all(r["is_sufficient"] for r in results)

    return {
        "checks": results,
        "overall_status": "OK" if all_sufficient else "LIMIT_EXCEEDED",
        "can_proceed": all_sufficient
    }


@router.get("/customers")
def get_customers_for_limit_check(db: Session = Depends(get_db)):
    """한도 체크용 고객 목록"""
    results = db.execute(text("""
        SELECT c.customer_id, c.customer_name, c.industry_code, c.industry_name,
               c.size_category, COALESCE(SUM(f.outstanding_amount), 0) as total_exposure
        FROM customer c
        LEFT JOIN facility f ON c.customer_id = f.customer_id AND f.status = 'ACTIVE'
        GROUP BY c.customer_id
        ORDER BY c.customer_name
        LIMIT 100
    """)).fetchall()

    return [
        {
            "customer_id": r[0],
            "customer_name": r[1],
            "industry_code": r[2],
            "industry_name": r[3],
            "size_category": r[4],
            "current_exposure": r[5]
        }
        for r in results
    ]


@router.get("/reservations")
def get_reservations(db: Session = Depends(get_db)):
    """한도 예약 현황"""
    results = db.execute(text("""
        SELECT lr.reservation_id, lr.limit_id, ld.limit_name,
               lr.application_id, lr.reserved_amount, lr.reserved_at,
               lr.expires_at, lr.status
        FROM limit_reservation lr
        JOIN limit_definition ld ON lr.limit_id = ld.limit_id
        WHERE lr.status = 'ACTIVE'
        ORDER BY lr.reserved_at DESC
    """)).fetchall()

    return [
        {
            "reservation_id": r[0],
            "limit_id": r[1],
            "limit_name": r[2],
            "application_id": r[3],
            "reserved_amount": r[4],
            "reserved_at": r[5],
            "expires_at": r[6],
            "status": r[7]
        }
        for r in results
    ]


@router.get("/trend/{limit_id}")
def get_limit_trend(limit_id: str, db: Session = Depends(get_db)):
    """한도 사용률 추이 (가상 데이터)"""
    # 실제로는 일별 스냅샷이 필요하지만 데모용으로 가상 생성
    import random
    from datetime import datetime, timedelta

    limit_info = db.execute(text("""
        SELECT ld.limit_amount, le.exposure_amount
        FROM limit_definition ld
        LEFT JOIN limit_exposure le ON ld.limit_id = le.limit_id
        WHERE ld.limit_id = :lid
    """), {"lid": limit_id}).fetchone()

    if not limit_info:
        return []

    current_util = (limit_info[1] or 0) / limit_info[0] * 100

    # 30일 추이 생성
    trend = []
    for i in range(30):
        date = datetime.now() - timedelta(days=29-i)
        # 현재값을 기준으로 약간의 변동
        util = current_util * random.uniform(0.9, 1.05)
        trend.append({
            "date": date.strftime("%Y-%m-%d"),
            "utilization_rate": min(util, 100)
        })

    return trend
