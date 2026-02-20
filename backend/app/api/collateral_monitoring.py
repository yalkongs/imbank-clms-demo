"""
담보 가치 실시간 모니터링 API
==============================
담보 가치 변동 추적, LTV 관리, 부동산 시세 연동
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from ..core.database import get_db

router = APIRouter(prefix="/api/collateral-monitoring", tags=["Collateral Monitoring"])


# ============================================
# 기능 설명 (모달용)
# ============================================

FEATURE_DESCRIPTIONS = {
    "collateral_overview": {
        "title": "담보 가치 실시간 모니터링",
        "description": "담보 가치의 실시간 변동을 추적하고 LTV 관리를 통한 손실 완화",
        "benefits": [
            "LTV 변동의 실시간 감지",
            "선제적 추가담보 징구",
            "LGD 추정 정확도 향상"
        ],
        "methodology": """
**담보 모니터링 체계**

1. **부동산 담보**
   - 공시지가, 실거래가 연동 자동 재평가
   - 지역별/용도별 시세 변동 추적
   - KB시세, 국토부 실거래가 API 연동

2. **유가증권 담보**
   - 실시간 시가 반영 (장중 업데이트)
   - 변동성 급등 시 추가 담보 트리거

3. **재고자산 담보**
   - 업종별 재고 가치 하락률 적용
   - 진부화 위험 자동 평가

**LTV 경보 체계**
| LTV 구간 | 상태 | 조치 |
|---------|------|------|
| ~60% | 정상 | 정기 모니터링 |
| 60-70% | 주의 | 월별 모니터링 강화 |
| 70-80% | 경고 | 추가 담보 징구 검토 |
| 80%+ | 위험 | 추가 담보 징구 또는 대출 축소 |
"""
    },
    "ltv_management": {
        "title": "LTV (Loan-to-Value) 관리",
        "description": "담보 대비 대출 비율 관리를 통한 손실 완화",
        "methodology": """
**LTV 산출**

```
LTV = Outstanding Loan / Collateral Value × 100%
```

**동적 LTV 관리**

담보 가치 하락 시 LTV가 상승하므로, 지속적인 모니터링이 필요합니다.

```
New_LTV = Original_Loan / (Original_Value × (1 + Price_Change))
```

**시나리오 분석**
| 가격 변동 | LTV 60% → | LTV 70% → | LTV 80% → |
|----------|----------|----------|----------|
| -10% | 66.7% | 77.8% | 88.9% |
| -20% | 75.0% | 87.5% | 100.0% |
| -30% | 85.7% | 100.0% | 114.3% |

**Haircut 설정**
담보 유형별 변동성을 고려한 할인율(Haircut) 적용
- 부동산: 20-30%
- 상장주식: 30-40%
- 비상장주식: 40-50%
- 재고자산: 30-50%
""",
        "formula": "LTV = Loan_Outstanding / Collateral_Value × 100%"
    },
    "real_estate_index": {
        "title": "부동산 시세 인덱스",
        "description": "지역별/유형별 부동산 시세 동향 추적",
        "methodology": """
**시세 인덱스 구성**

| 유형 | 설명 | 데이터 소스 |
|------|------|------------|
| APT | 아파트 | KB시세, 실거래가 |
| OFFICE | 오피스 | 상업용 부동산 지수 |
| RETAIL | 상가 | 상업용 부동산 지수 |
| INDUSTRIAL | 공장 | 산업용 부동산 지수 |
| LAND | 토지 | 공시지가, 실거래가 |

**변동성 분석**
- 30일 변동성: 최근 30일 일별 변동률의 표준편차
- 전월비 (MoM): 전월 대비 변동률
- 전년비 (YoY): 전년 동월 대비 변동률

**활용**
1. 담보 자동 재평가
2. 지역별 담보 선호도 조정
3. 업종별 담보 정책 수립
"""
    }
}


@router.get("/feature-description/{feature_id}")
async def get_feature_description(feature_id: str):
    """기능 설명 조회 (모달용)"""
    if feature_id in FEATURE_DESCRIPTIONS:
        return FEATURE_DESCRIPTIONS[feature_id]
    return {"error": "Feature not found"}


@router.get("/real-estate-index")
async def get_real_estate_index(
    region: Optional[str] = None,
    property_type: Optional[str] = None,
    months: int = Query(12, le=24),
    db: Session = Depends(get_db)
):
    """부동산 시세 인덱스 조회"""
    query = """
        SELECT index_id, reference_date, region_code, property_type,
               index_value, mom_change, yoy_change, volatility_30d, forecast_3m
        FROM real_estate_index
        WHERE 1=1
    """
    params = {}

    if region:
        query += " AND region_code = :region_code"
        params["region_code"] = region
    if property_type:
        query += " AND property_type = :property_type"
        params["property_type"] = property_type

    query += " ORDER BY reference_date DESC, region_code, property_type"

    result = db.execute(text(query), params)

    indices = []
    for row in result:
        indices.append({
            "index_id": row[0],
            "reference_date": row[1],
            "region_code": row[2],
            "property_type": row[3],
            "index_value": row[4],
            "mom_change": row[5],
            "yoy_change": row[6],
            "volatility_30d": row[7],
            "forecast_3m": row[8]
        })

    # 지역별 최신 인덱스 요약
    summary_query = """
        SELECT region_code, property_type, index_value, mom_change
        FROM real_estate_index
        WHERE reference_date = (SELECT MAX(reference_date) FROM real_estate_index)
    """
    summary_params = {}
    if region:
        summary_query += " AND region_code = :region_code"
        summary_params["region_code"] = region
    summary_query += " ORDER BY region_code, property_type"
    latest_by_region = db.execute(text(summary_query), summary_params)

    summary = {}
    for row in latest_by_region:
        if row[0] not in summary:
            summary[row[0]] = {}
        summary[row[0]][row[1]] = {
            "index": row[2],
            "mom_change": row[3]
        }

    return {"indices": indices, "latest_by_region": summary}


@router.get("/valuation-history/{collateral_id}")
async def get_valuation_history(collateral_id: str, db: Session = Depends(get_db)):
    """담보 가치 이력 조회"""
    # 담보 기본 정보
    collateral = db.execute(text("""
        SELECT c.collateral_id, c.collateral_type, c.collateral_subtype,
               c.original_value, c.current_value, c.ltv, c.valuation_date,
               f.facility_id, f.outstanding_amount, f.approved_amount,
               cust.customer_name
        FROM collateral c
        LEFT JOIN facility f ON c.facility_id = f.facility_id
        LEFT JOIN customer cust ON f.customer_id = cust.customer_id
        WHERE c.collateral_id = :collateral_id
    """), {"collateral_id": collateral_id}).fetchone()

    if not collateral:
        return {"error": "Collateral not found"}

    # 가치 이력
    history = db.execute(text("""
        SELECT valuation_id, valuation_date, valuation_type, valuation_source,
               previous_value, current_value, change_pct, market_condition,
               ltv_before, ltv_after, alert_triggered
        FROM collateral_valuation_history
        WHERE collateral_id = :collateral_id
        ORDER BY valuation_date DESC
    """), {"collateral_id": collateral_id})

    valuations = []
    for row in history:
        valuations.append({
            "valuation_id": row[0],
            "valuation_date": row[1],
            "valuation_type": row[2],
            "valuation_source": row[3],
            "previous_value": row[4],
            "current_value": row[5],
            "change_pct": row[6],
            "market_condition": row[7],
            "ltv_before": row[8],
            "ltv_after": row[9],
            "alert_triggered": bool(row[10])
        })

    return {
        "collateral": {
            "collateral_id": collateral[0],
            "collateral_type": collateral[1],
            "collateral_subtype": collateral[2],
            "original_value": collateral[3],
            "current_value": collateral[4],
            "current_ltv": collateral[5],
            "last_valuation_date": collateral[6],
            "facility_id": collateral[7],
            "outstanding_amount": collateral[8],
            "approved_amount": collateral[9],
            "customer_name": collateral[10]
        },
        "valuation_history": valuations
    }


@router.get("/alerts")
async def get_collateral_alerts(
    status: Optional[str] = Query(None, description="OPEN, IN_PROGRESS, RESOLVED"),
    severity: Optional[str] = Query(None, description="LOW, MEDIUM, HIGH, CRITICAL"),
    alert_type: Optional[str] = None,
    region: str = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    """담보 경보 조회"""
    query = """
        SELECT ca.alert_id, ca.collateral_id, c.collateral_type,
               ca.alert_date, ca.alert_type, ca.severity,
               ca.current_ltv, ca.threshold_ltv, ca.value_change_pct,
               ca.required_action, ca.status,
               f.facility_id, cust.customer_name
        FROM collateral_alert ca
        JOIN collateral c ON ca.collateral_id = c.collateral_id
        LEFT JOIN facility f ON c.facility_id = f.facility_id
        LEFT JOIN customer cust ON f.customer_id = cust.customer_id
        WHERE 1=1
    """
    params = {}

    if status:
        query += " AND ca.status = :status"
        params["status"] = status
    if severity:
        query += " AND ca.severity = :severity"
        params["severity"] = severity
    if alert_type:
        query += " AND ca.alert_type = :alert_type"
        params["alert_type"] = alert_type
    if region:
        query += " AND cust.region = :region"
        params["region"] = region

    query += " ORDER BY ca.alert_date DESC LIMIT :limit"
    params["limit"] = limit

    result = db.execute(text(query), params)

    alerts = []
    for row in result:
        alerts.append({
            "alert_id": row[0],
            "collateral_id": row[1],
            "collateral_type": row[2],
            "alert_date": row[3],
            "alert_type": row[4],
            "severity": row[5],
            "current_ltv": row[6],
            "threshold_ltv": row[7],
            "value_change_pct": row[8],
            "required_action": row[9],
            "status": row[10],
            "facility_id": row[11],
            "customer_name": row[12]
        })

    # 경보 유형별 요약
    summary = db.execute(text("""
        SELECT alert_type, severity, COUNT(*) as count
        FROM collateral_alert
        WHERE status != 'RESOLVED'
        GROUP BY alert_type, severity
    """))

    summary_by_type = {}
    for row in summary:
        if row[0] not in summary_by_type:
            summary_by_type[row[0]] = {}
        summary_by_type[row[0]][row[1]] = row[2]

    return {
        "alerts": alerts,
        "total": len(alerts),
        "summary_by_type": summary_by_type
    }


@router.get("/ltv-analysis")
async def get_ltv_analysis(
    region: str = Query(None),
    db: Session = Depends(get_db)
):
    """LTV 분포 분석"""
    region_cond = ""
    rp = {}
    if region:
        region_cond = " AND c.region = :region"
        rp["region"] = region

    # LTV 구간별 분포
    ltv_distribution = db.execute(text("""
        SELECT
            CASE
                WHEN col.ltv < 0.5 THEN '0-50%'
                WHEN col.ltv < 0.6 THEN '50-60%'
                WHEN col.ltv < 0.7 THEN '60-70%'
                WHEN col.ltv < 0.8 THEN '70-80%'
                ELSE '80%+'
            END as ltv_bucket,
            COUNT(*) as count,
            SUM(col.current_value) as total_collateral_value
        FROM collateral col
        JOIN facility f ON col.facility_id = f.facility_id
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE col.ltv IS NOT NULL
    """ + region_cond + """
        GROUP BY ltv_bucket
        ORDER BY ltv_bucket
    """), rp)

    distribution = []
    for row in ltv_distribution:
        distribution.append({
            "ltv_bucket": row[0],
            "count": row[1],
            "total_collateral_value": row[2]
        })

    # 담보 유형별 평균 LTV
    by_type = db.execute(text("""
        SELECT col.collateral_type, AVG(col.ltv) as avg_ltv, COUNT(*) as count
        FROM collateral col
        JOIN facility f ON col.facility_id = f.facility_id
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE col.ltv IS NOT NULL
    """ + region_cond + """
        GROUP BY col.collateral_type
    """), rp)

    by_collateral_type = []
    for row in by_type:
        by_collateral_type.append({
            "collateral_type": row[0],
            "avg_ltv": round(row[1], 3) if row[1] else 0,
            "count": row[2]
        })

    # 고 LTV 담보 (80% 이상)
    high_ltv = db.execute(text("""
        SELECT col.collateral_id, col.collateral_type, col.current_value, col.ltv,
               f.outstanding_amount, c.customer_name
        FROM collateral col
        JOIN facility f ON col.facility_id = f.facility_id
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE col.ltv >= 0.8
    """ + region_cond + """
        ORDER BY col.ltv DESC
        LIMIT 20
    """), rp)

    high_ltv_collaterals = []
    for row in high_ltv:
        high_ltv_collaterals.append({
            "collateral_id": row[0],
            "collateral_type": row[1],
            "current_value": row[2],
            "ltv": row[3],
            "outstanding_amount": row[4],
            "customer_name": row[5]
        })

    return {
        "ltv_distribution": distribution,
        "by_collateral_type": by_collateral_type,
        "high_ltv_collaterals": high_ltv_collaterals
    }


@router.get("/customers")
async def get_collateral_customers(
    search: Optional[str] = Query(None),
    collateral_type: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    sort_by: str = Query("total_value", description="total_value, recognized_value, avg_ltv, margin, count"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """담보 보유 고객 목록 (담보건수, 총가치, 인정가액, 평균LTV, 담보여력 요약)"""
    base_where = "WHERE col.current_value > 0"
    params: dict = {}

    if search:
        base_where += " AND (c.customer_name LIKE :search OR c.customer_id LIKE :search)"
        params["search"] = f"%{search}%"
    if collateral_type:
        base_where += " AND col.collateral_type = :collateral_type"
        params["collateral_type"] = collateral_type
    if region:
        base_where += " AND c.region = :region"
        params["region"] = region

    sort_map = {
        "total_value": "total_value",
        "recognized_value": "total_recognized",
        "avg_ltv": "avg_ltv",
        "margin": "total_margin",
        "count": "collateral_count",
    }
    sort_col = sort_map.get(sort_by, "total_value")
    order = "DESC" if sort_order.lower() == "desc" else "ASC"

    # Total count
    count_q = f"""
        SELECT COUNT(DISTINCT c.customer_id)
        FROM collateral col
        JOIN facility f ON col.facility_id = f.facility_id
        JOIN customer c ON f.customer_id = c.customer_id
        {base_where}
    """
    total_count = db.execute(text(count_q), params).scalar() or 0

    # Customer list
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    query = f"""
        SELECT c.customer_id, c.customer_name, c.industry_name, c.size_category, c.region,
               COUNT(col.collateral_id) as collateral_count,
               SUM(col.current_value) as total_value,
               SUM(COALESCE(col.recognized_value, col.current_value * 0.7)) as total_recognized,
               AVG(col.ltv) as avg_ltv,
               SUM(COALESCE(col.collateral_margin, 0)) as total_margin
        FROM collateral col
        JOIN facility f ON col.facility_id = f.facility_id
        JOIN customer c ON f.customer_id = c.customer_id
        {base_where}
        GROUP BY c.customer_id, c.customer_name, c.industry_name, c.size_category, c.region
        ORDER BY {sort_col} {order}
        LIMIT :limit OFFSET :offset
    """
    result = db.execute(text(query), params)

    customers = []
    for row in result:
        customers.append({
            "customer_id": row[0],
            "customer_name": row[1],
            "industry_name": row[2],
            "size_category": row[3],
            "region": row[4],
            "collateral_count": row[5],
            "total_value": row[6],
            "total_recognized": row[7],
            "avg_ltv": round(row[8], 4) if row[8] else 0,
            "total_margin": row[9],
        })

    # Summary stats
    summary_params: dict = {}
    summary_where = "WHERE col.current_value > 0"
    if region:
        summary_where += " AND c.region = :region"
        summary_params["region"] = region
    if collateral_type:
        summary_where += " AND col.collateral_type = :collateral_type"
        summary_params["collateral_type"] = collateral_type

    summary = db.execute(text(f"""
        SELECT COUNT(DISTINCT c.customer_id) as customer_count,
               SUM(col.current_value) as total_value,
               SUM(COALESCE(col.recognized_value, col.current_value * 0.7)) as total_recognized,
               AVG(col.ltv) as avg_ltv
        FROM collateral col
        JOIN facility f ON col.facility_id = f.facility_id
        JOIN customer c ON f.customer_id = c.customer_id
        {summary_where}
    """), summary_params).fetchone()

    # Collateral type distribution - 유형 필터와 무관하게 항상 전체 유형 표시
    type_where = "WHERE col.current_value > 0"
    type_params: dict = {}
    if region:
        type_where += " AND c.region = :region"
        type_params["region"] = region
    type_dist = db.execute(text(f"""
        SELECT col.collateral_type, COUNT(*) as cnt
        FROM collateral col
        JOIN facility f ON col.facility_id = f.facility_id
        JOIN customer c ON f.customer_id = c.customer_id
        {type_where}
        GROUP BY col.collateral_type ORDER BY cnt DESC
    """), type_params)
    type_distribution = [{"type": row[0], "count": row[1]} for row in type_dist]

    return {
        "customers": customers,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size,
        "summary": {
            "customer_count": summary[0] if summary else 0,
            "total_value": summary[1] if summary else 0,
            "total_recognized": summary[2] if summary else 0,
            "avg_ltv": round(summary[3], 4) if summary and summary[3] else 0,
        },
        "type_distribution": type_distribution,
    }


@router.get("/customer/{customer_id}")
async def get_customer_collateral_detail(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """고객별 담보 상세 (전체 담보 목록 + 가격 산정 정보 + 알림)"""
    # Customer info
    cust = db.execute(text("""
        SELECT customer_id, customer_name, industry_name, size_category, region
        FROM customer WHERE customer_id = :cid
    """), {"cid": customer_id}).fetchone()

    if not cust:
        return {"error": "Customer not found"}

    # All collaterals for this customer
    collaterals_result = db.execute(text("""
        SELECT col.collateral_id, col.collateral_type, col.collateral_subtype,
               col.original_value, col.current_value, col.ltv,
               col.appraisal_value, col.market_value, col.recognition_ratio,
               col.recognized_value, col.prior_lien_amount, col.collateral_margin,
               col.appraiser, col.last_appraisal_date, col.location_address, col.description,
               col.valuation_date, col.facility_id,
               f.outstanding_amount, f.approved_amount
        FROM collateral col
        JOIN facility f ON col.facility_id = f.facility_id
        WHERE f.customer_id = :cid AND col.current_value > 0
        ORDER BY col.current_value DESC
    """), {"cid": customer_id})

    collaterals = []
    total_value = 0
    total_recognized = 0
    total_margin = 0
    for row in collaterals_result:
        coll = {
            "collateral_id": row[0],
            "collateral_type": row[1],
            "collateral_subtype": row[2],
            "original_value": row[3],
            "current_value": row[4],
            "ltv": row[5],
            "appraisal_value": row[6],
            "market_value": row[7],
            "recognition_ratio": row[8],
            "recognized_value": row[9],
            "prior_lien_amount": row[10],
            "collateral_margin": row[11],
            "appraiser": row[12],
            "last_appraisal_date": row[13],
            "location_address": row[14],
            "description": row[15],
            "valuation_date": row[16],
            "facility_id": row[17],
            "outstanding_amount": row[18],
            "approved_amount": row[19],
        }
        collaterals.append(coll)
        total_value += row[4] or 0
        total_recognized += row[9] or (row[4] or 0) * 0.7
        total_margin += row[11] or 0

    # Alerts for this customer's collaterals
    alerts_result = db.execute(text("""
        SELECT ca.alert_id, ca.collateral_id, ca.alert_date, ca.alert_type,
               ca.severity, ca.current_ltv, ca.threshold_ltv, ca.value_change_pct,
               ca.required_action, ca.status
        FROM collateral_alert ca
        JOIN collateral col ON ca.collateral_id = col.collateral_id
        JOIN facility f ON col.facility_id = f.facility_id
        WHERE f.customer_id = :cid
        ORDER BY ca.alert_date DESC
        LIMIT 20
    """), {"cid": customer_id})

    alerts = []
    for row in alerts_result:
        alerts.append({
            "alert_id": row[0],
            "collateral_id": row[1],
            "alert_date": row[2],
            "alert_type": row[3],
            "severity": row[4],
            "current_ltv": row[5],
            "threshold_ltv": row[6],
            "value_change_pct": row[7],
            "required_action": row[8],
            "status": row[9],
        })

    avg_ltv = 0
    if collaterals:
        ltv_vals = [c["ltv"] for c in collaterals if c["ltv"] is not None]
        avg_ltv = sum(ltv_vals) / len(ltv_vals) if ltv_vals else 0

    return {
        "customer": {
            "customer_id": cust[0],
            "customer_name": cust[1],
            "industry_name": cust[2],
            "size_category": cust[3],
            "region": cust[4],
        },
        "summary": {
            "collateral_count": len(collaterals),
            "total_value": total_value,
            "total_recognized": total_recognized,
            "avg_ltv": round(avg_ltv, 4),
            "total_margin": total_margin,
        },
        "collaterals": collaterals,
        "alerts": alerts,
    }


@router.get("/dashboard")
async def get_collateral_dashboard(
    region: str = Query(None),
    db: Session = Depends(get_db)
):
    """담보 모니터링 대시보드"""
    region_cond = ""
    rp = {}
    if region:
        region_cond = " AND c.region = :region"
        rp["region"] = region

    # 전체 담보 요약
    summary = db.execute(text("""
        SELECT
            COUNT(*) as total_count,
            SUM(col.current_value) as total_value,
            AVG(col.ltv) as avg_ltv,
            SUM(CASE WHEN col.ltv >= 0.8 THEN 1 ELSE 0 END) as high_ltv_count
        FROM collateral col
        JOIN facility f ON col.facility_id = f.facility_id
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE col.current_value > 0
    """ + region_cond), rp).fetchone()

    # 미해결 경보
    open_alerts = db.execute(text("""
        SELECT ca.severity, COUNT(*) as count
        FROM collateral_alert ca
        JOIN collateral col ON ca.collateral_id = col.collateral_id
        JOIN facility f ON col.facility_id = f.facility_id
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE ca.status != 'RESOLVED'
    """ + region_cond + """
        GROUP BY ca.severity
    """), rp)

    alerts_by_severity = {row[0]: row[1] for row in open_alerts}

    # 최근 가치 변동 (하락)
    recent_declines = db.execute(text("""
        SELECT col.collateral_type, c.customer_name,
               cvh.change_pct, cvh.valuation_date
        FROM collateral_valuation_history cvh
        JOIN collateral col ON cvh.collateral_id = col.collateral_id
        JOIN facility f ON col.facility_id = f.facility_id
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE cvh.change_pct < -5
    """ + region_cond + """
        ORDER BY cvh.valuation_date DESC
        LIMIT 10
    """), rp)

    significant_declines = []
    for row in recent_declines:
        significant_declines.append({
            "collateral_type": row[0],
            "customer_name": row[1],
            "change_pct": row[2],
            "valuation_date": row[3]
        })

    return {
        "summary": {
            "total_collaterals": summary[0],
            "total_value": summary[1],
            "avg_ltv": round(summary[2], 3) if summary[2] else 0,
            "high_ltv_count": summary[3]
        },
        "open_alerts_by_severity": alerts_by_severity,
        "recent_significant_declines": significant_declines
    }
