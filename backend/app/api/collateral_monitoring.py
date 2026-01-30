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
    region_code: Optional[str] = None,
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

    if region_code:
        query += " AND region_code = :region_code"
        params["region_code"] = region_code
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
    latest_by_region = db.execute(text("""
        SELECT region_code, property_type, index_value, mom_change
        FROM real_estate_index
        WHERE reference_date = (SELECT MAX(reference_date) FROM real_estate_index)
        ORDER BY region_code, property_type
    """))

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
async def get_ltv_analysis(db: Session = Depends(get_db)):
    """LTV 분포 분석"""
    # LTV 구간별 분포
    ltv_distribution = db.execute(text("""
        SELECT
            CASE
                WHEN ltv < 0.5 THEN '0-50%'
                WHEN ltv < 0.6 THEN '50-60%'
                WHEN ltv < 0.7 THEN '60-70%'
                WHEN ltv < 0.8 THEN '70-80%'
                ELSE '80%+'
            END as ltv_bucket,
            COUNT(*) as count,
            SUM(current_value) as total_collateral_value
        FROM collateral
        WHERE ltv IS NOT NULL
        GROUP BY ltv_bucket
        ORDER BY ltv_bucket
    """))

    distribution = []
    for row in ltv_distribution:
        distribution.append({
            "ltv_bucket": row[0],
            "count": row[1],
            "total_collateral_value": row[2]
        })

    # 담보 유형별 평균 LTV
    by_type = db.execute(text("""
        SELECT collateral_type, AVG(ltv) as avg_ltv, COUNT(*) as count
        FROM collateral
        WHERE ltv IS NOT NULL
        GROUP BY collateral_type
    """))

    by_collateral_type = []
    for row in by_type:
        by_collateral_type.append({
            "collateral_type": row[0],
            "avg_ltv": round(row[1], 3) if row[1] else 0,
            "count": row[2]
        })

    # 고 LTV 담보 (80% 이상)
    high_ltv = db.execute(text("""
        SELECT c.collateral_id, c.collateral_type, c.current_value, c.ltv,
               f.outstanding_amount, cust.customer_name
        FROM collateral c
        LEFT JOIN facility f ON c.facility_id = f.facility_id
        LEFT JOIN customer cust ON f.customer_id = cust.customer_id
        WHERE c.ltv >= 0.8
        ORDER BY c.ltv DESC
        LIMIT 20
    """))

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


@router.get("/dashboard")
async def get_collateral_dashboard(db: Session = Depends(get_db)):
    """담보 모니터링 대시보드"""
    # 전체 담보 요약
    summary = db.execute(text("""
        SELECT
            COUNT(*) as total_count,
            SUM(current_value) as total_value,
            AVG(ltv) as avg_ltv,
            SUM(CASE WHEN ltv >= 0.8 THEN 1 ELSE 0 END) as high_ltv_count
        FROM collateral
        WHERE current_value > 0
    """)).fetchone()

    # 미해결 경보
    open_alerts = db.execute(text("""
        SELECT severity, COUNT(*) as count
        FROM collateral_alert
        WHERE status != 'RESOLVED'
        GROUP BY severity
    """))

    alerts_by_severity = {row[0]: row[1] for row in open_alerts}

    # 최근 가치 변동 (하락)
    recent_declines = db.execute(text("""
        SELECT c.collateral_type, cust.customer_name,
               cvh.change_pct, cvh.valuation_date
        FROM collateral_valuation_history cvh
        JOIN collateral c ON cvh.collateral_id = c.collateral_id
        LEFT JOIN facility f ON c.facility_id = f.facility_id
        LEFT JOIN customer cust ON f.customer_id = cust.customer_id
        WHERE cvh.change_pct < -5
        ORDER BY cvh.valuation_date DESC
        LIMIT 10
    """))

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
