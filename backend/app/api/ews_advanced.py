"""
EWS 고도화 API
==============
조기경보 시스템 고도화 - 선행지표, 공급망 분석, 외부 신호, 종합 점수
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from ..core.database import get_db

router = APIRouter(prefix="/api/ews-advanced", tags=["EWS Advanced"])


# ============================================
# 기능 설명 (모달용)
# ============================================

FEATURE_DESCRIPTIONS = {
    "ews_overview": {
        "title": "조기경보 시스템 (EWS) 고도화",
        "description": "전통적인 재무지표 기반 EWS를 넘어 선행지표, 공급망 분석, 외부 신호를 통합한 예측적 조기경보 시스템",
        "benefits": [
            "부도 6-12개월 전 조기 포착",
            "포트폴리오 손실 사전 대응",
            "비재무 리스크 조기 감지"
        ],
        "methodology": """
EWS 고도화 시스템은 4가지 차원의 지표를 통합 분석합니다:

1. **재무 선행지표 (Financial Leading Indicators)**
   - 매출채권회전일, 재고자산회전율 등 운전자본 지표
   - 현금흐름커버리지, 이자보상배율 등 유동성 지표
   - 부채비율 변화율 등 레버리지 급변 징후

2. **운영 지표 (Operational Indicators)**
   - 연체 발생 여부 (후행지표)
   - 거래 패턴 변화

3. **외부 신호 (External Signals)**
   - 뉴스 심리 분석 (NLP 기반)
   - 소송, 세금체납, 규제 이슈
   - 외부 신용평가 등급 변동

4. **공급망 위험 (Supply Chain Risk)**
   - 주요 거래처 부도 영향도
   - 연쇄부도 전파 경로 분석
"""
    },
    "leading_indicator": {
        "title": "선행지표 (Leading Indicator)",
        "description": "부도 발생 전 선제적으로 경고 신호를 제공하는 지표",
        "methodology": """
**선행지표의 원리**

선행지표는 기업의 재무적 어려움이 실제 부도로 이어지기 전에 나타나는 징후를 포착합니다.

| 지표 | 산출 방식 | 의미 |
|------|----------|------|
| 매출채권회전일 | 매출채권 ÷ 일평균매출 | 증가 시 현금회수 지연 |
| 재고자산회전율 | 매출원가 ÷ 평균재고 | 감소 시 판매 부진 |
| 현금흐름커버리지 | 영업CF ÷ 단기차입금 | 감소 시 상환능력 약화 |
| 이자보상배율 | EBIT ÷ 이자비용 | 감소 시 이자지급능력 약화 |

**임계치 설정**
- Warning: 업종 평균 대비 1σ 이상 악화
- Critical: 업종 평균 대비 2σ 이상 악화
""",
        "formula": "Signal = Σ(Indicator_i × Weight_i × Severity_i)"
    },
    "supply_chain_analysis": {
        "title": "공급망 연쇄부도 분석",
        "description": "주요 거래처의 부도가 해당 기업에 미치는 영향을 분석",
        "methodology": """
**연쇄부도 전파 모형**

1. **직접 영향 (1차 효과)**
   - 매출처 부도 → 매출채권 손실
   - 공급처 부도 → 생산 차질, 대체 비용 발생

2. **간접 영향 (2차, 3차 효과)**
   - 신뢰도 하락 → 신규 거래처 확보 어려움
   - 신용등급 하락 → 자금조달 비용 상승

**의존도 점수 (Dependency Score)**

```
Dependency = (거래비중 × 대체난이도) / 거래처다각화지수
```

- 거래비중: 해당 거래처가 총매출/매입에서 차지하는 비율
- 대체난이도: 대체 거래처 확보 용이성 (1~5)
- 거래처다각화지수: HHI 지수 기반
""",
        "formula": "Chain_Default_Risk = Σ(Partner_PD_i × Dependency_i × Contagion_Factor)"
    },
    "composite_score": {
        "title": "종합 EWS 점수",
        "description": "다차원 지표를 통합한 종합 위험 점수",
        "methodology": """
**점수 산출 방법**

종합 EWS 점수는 0~100점 척도로 산출되며, 점수가 높을수록 안전합니다.

```
Composite Score = 0.40 × Financial + 0.20 × Operational
                + 0.20 × External + 0.20 × Supply_Chain
```

**위험 등급 분류**
| 등급 | 점수 범위 | 조치 |
|------|----------|------|
| LOW | 70-100 | 정기 모니터링 |
| MEDIUM | 50-69 | 모니터링 주기 단축 |
| HIGH | 30-49 | 워치리스트 편입 |
| CRITICAL | 0-29 | 긴급 실사 및 회수 검토 |
""",
        "formula": "Composite = Σ(Dimension_Score_i × Weight_i)"
    }
}


@router.get("/feature-description/{feature_id}")
async def get_feature_description(feature_id: str):
    """기능 설명 조회 (모달용)"""
    if feature_id in FEATURE_DESCRIPTIONS:
        return FEATURE_DESCRIPTIONS[feature_id]
    return {"error": "Feature not found"}


@router.get("/indicators")
async def get_ews_indicators(db: Session = Depends(get_db)):
    """EWS 선행지표 목록 조회"""
    result = db.execute(text("""
        SELECT indicator_id, indicator_name, indicator_type, category,
               calculation_method, threshold_warning, threshold_critical,
               weight, description
        FROM ews_indicator
        ORDER BY weight DESC
    """))

    indicators = []
    for row in result:
        indicators.append({
            "indicator_id": row[0],
            "indicator_name": row[1],
            "indicator_type": row[2],
            "category": row[3],
            "calculation_method": row[4],
            "threshold_warning": row[5],
            "threshold_critical": row[6],
            "weight": row[7],
            "description": row[8]
        })

    return {"indicators": indicators, "total": len(indicators)}


@router.get("/indicator-values/{customer_id}")
async def get_indicator_values(
    customer_id: str,
    months: int = Query(6, description="조회 기간 (월)"),
    db: Session = Depends(get_db)
):
    """고객별 지표 값 시계열 조회"""
    result = db.execute(text("""
        SELECT eiv.reference_date, ei.indicator_name, ei.indicator_type,
               eiv.value, eiv.previous_value, eiv.change_rate,
               eiv.trend, eiv.signal_level,
               ei.threshold_warning, ei.threshold_critical
        FROM ews_indicator_value eiv
        JOIN ews_indicator ei ON eiv.indicator_id = ei.indicator_id
        WHERE eiv.customer_id = :customer_id
        ORDER BY eiv.reference_date DESC, ei.weight DESC
    """), {"customer_id": customer_id})

    values = []
    for row in result:
        values.append({
            "date": row[0],
            "indicator_name": row[1],
            "indicator_type": row[2],
            "value": row[3],
            "previous_value": row[4],
            "change_rate": row[5],
            "trend": row[6],
            "signal_level": row[7],
            "threshold_warning": row[8],
            "threshold_critical": row[9]
        })

    return {"customer_id": customer_id, "values": values}


@router.get("/supply-chain/{customer_id}")
async def get_supply_chain_risk(customer_id: str, db: Session = Depends(get_db)):
    """공급망 연쇄부도 위험 분석"""
    # 해당 고객의 거래처 조회
    result = db.execute(text("""
        SELECT
            scr.relation_type,
            scr.dependency_score,
            scr.transaction_volume,
            scr.share_of_revenue,
            c.customer_name,
            c.customer_id as partner_id,
            c.industry_name,
            COALESCE(ecs.composite_score, 50) as partner_ews_score,
            COALESCE(ecs.risk_level, 'MEDIUM') as partner_risk_level
        FROM supply_chain_relation scr
        JOIN customer c ON
            CASE WHEN scr.supplier_id = :customer_id THEN scr.buyer_id
                 ELSE scr.supplier_id END = c.customer_id
        LEFT JOIN ews_composite_score ecs ON c.customer_id = ecs.customer_id
        WHERE scr.supplier_id = :customer_id OR scr.buyer_id = :customer_id
        ORDER BY scr.dependency_score DESC
        LIMIT 20
    """), {"customer_id": customer_id})

    partners = []
    total_chain_risk = 0
    for row in result:
        partner_pd = (100 - row[7]) / 100 * 0.1  # EWS 점수를 PD로 변환 (간략화)
        chain_risk = row[1] * partner_pd  # dependency × partner_PD
        total_chain_risk += chain_risk

        partners.append({
            "relation_type": row[0],
            "dependency_score": row[1],
            "transaction_volume": row[2],
            "share_of_revenue": row[3],
            "partner_name": row[4],
            "partner_id": row[5],
            "industry": row[6],
            "partner_ews_score": row[7],
            "partner_risk_level": row[8],
            "chain_risk_contribution": round(chain_risk, 4)
        })

    return {
        "customer_id": customer_id,
        "partners": partners,
        "total_chain_risk": round(total_chain_risk, 4),
        "risk_assessment": "HIGH" if total_chain_risk > 0.05 else "MEDIUM" if total_chain_risk > 0.02 else "LOW"
    }


@router.get("/external-signals")
async def get_external_signals(
    customer_id: Optional[str] = None,
    signal_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """외부 신호 조회"""
    query = """
        SELECT ees.signal_id, ees.customer_id, c.customer_name,
               ees.signal_date, ees.signal_type, ees.signal_source,
               ees.severity, ees.title, ees.description,
               ees.impact_score, ees.verified, ees.action_required
        FROM ews_external_signal ees
        JOIN customer c ON ees.customer_id = c.customer_id
        WHERE 1=1
    """
    params = {}

    if customer_id:
        query += " AND ees.customer_id = :customer_id"
        params["customer_id"] = customer_id
    if signal_type:
        query += " AND ees.signal_type = :signal_type"
        params["signal_type"] = signal_type
    if severity:
        query += " AND ees.severity = :severity"
        params["severity"] = severity

    query += " ORDER BY ees.signal_date DESC LIMIT :limit"
    params["limit"] = limit

    result = db.execute(text(query), params)

    signals = []
    for row in result:
        signals.append({
            "signal_id": row[0],
            "customer_id": row[1],
            "customer_name": row[2],
            "signal_date": row[3],
            "signal_type": row[4],
            "signal_source": row[5],
            "severity": row[6],
            "title": row[7],
            "description": row[8],
            "impact_score": row[9],
            "verified": bool(row[10]),
            "action_required": bool(row[11])
        })

    return {"signals": signals, "total": len(signals)}


@router.get("/composite-scores")
async def get_composite_scores(
    risk_level: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    """종합 EWS 점수 조회"""
    query = """
        SELECT ecs.score_id, ecs.customer_id, c.customer_name, c.industry_name,
               ecs.score_date, ecs.financial_score, ecs.operational_score,
               ecs.external_score, ecs.supply_chain_score, ecs.composite_score,
               ecs.risk_level, ecs.predicted_default_prob, ecs.recommendation
        FROM ews_composite_score ecs
        JOIN customer c ON ecs.customer_id = c.customer_id
        WHERE 1=1
    """
    params = {}

    if risk_level:
        query += " AND ecs.risk_level = :risk_level"
        params["risk_level"] = risk_level
    if min_score is not None:
        query += " AND ecs.composite_score >= :min_score"
        params["min_score"] = min_score
    if max_score is not None:
        query += " AND ecs.composite_score <= :max_score"
        params["max_score"] = max_score

    query += " ORDER BY ecs.composite_score ASC LIMIT :limit"
    params["limit"] = limit

    result = db.execute(text(query), params)

    scores = []
    for row in result:
        scores.append({
            "score_id": row[0],
            "customer_id": row[1],
            "customer_name": row[2],
            "industry_name": row[3],
            "score_date": row[4],
            "financial_score": row[5],
            "operational_score": row[6],
            "external_score": row[7],
            "supply_chain_score": row[8],
            "composite_score": row[9],
            "risk_level": row[10],
            "predicted_default_prob": row[11],
            "recommendation": row[12]
        })

    # 요약 통계
    summary_result = db.execute(text("""
        SELECT risk_level, COUNT(*) as count,
               AVG(composite_score) as avg_score,
               AVG(predicted_default_prob) as avg_pd
        FROM ews_composite_score
        GROUP BY risk_level
    """))

    summary = {}
    for row in summary_result:
        summary[row[0]] = {
            "count": row[1],
            "avg_score": round(row[2], 1) if row[2] else 0,
            "avg_pd": round(row[3], 4) if row[3] else 0
        }

    return {"scores": scores, "total": len(scores), "summary_by_risk": summary}


@router.get("/dashboard")
async def get_ews_dashboard(db: Session = Depends(get_db)):
    """EWS 대시보드 요약"""
    # 위험 등급별 분포
    risk_dist = db.execute(text("""
        SELECT risk_level, COUNT(*) as count
        FROM ews_composite_score
        GROUP BY risk_level
    """))

    risk_distribution = {row[0]: row[1] for row in risk_dist}

    # 평균 복합점수
    avg_score = db.execute(text("""
        SELECT AVG(composite_score) FROM ews_composite_score
    """)).fetchone()

    # 외부 신호 총 개수
    signal_count = db.execute(text("""
        SELECT COUNT(*) FROM ews_external_signal
    """)).fetchone()

    # 최근 외부 신호 (심각도 높은 것)
    recent_signals = db.execute(text("""
        SELECT ees.signal_date, c.customer_name, ees.signal_type,
               ees.severity, ees.title
        FROM ews_external_signal ees
        JOIN customer c ON ees.customer_id = c.customer_id
        WHERE ees.severity IN ('HIGH', 'CRITICAL')
        ORDER BY ees.signal_date DESC
        LIMIT 10
    """))

    critical_signals = []
    for row in recent_signals:
        critical_signals.append({
            "date": row[0],
            "customer_name": row[1],
            "signal_type": row[2],
            "severity": row[3],
            "title": row[4]
        })

    # 워치리스트 (HIGH, CRITICAL)
    watchlist = db.execute(text("""
        SELECT c.customer_id, c.customer_name, c.industry_name,
               ecs.composite_score, ecs.risk_level, ecs.recommendation
        FROM ews_composite_score ecs
        JOIN customer c ON ecs.customer_id = c.customer_id
        WHERE ecs.risk_level IN ('HIGH', 'CRITICAL')
        ORDER BY ecs.composite_score ASC
        LIMIT 20
    """))

    watch_customers = []
    for row in watchlist:
        watch_customers.append({
            "customer_id": row[0],
            "customer_name": row[1],
            "industry_name": row[2],
            "composite_score": row[3],
            "risk_level": row[4],
            "recommendation": row[5]
        })

    return {
        "risk_distribution": risk_distribution,
        "critical_signals": critical_signals,
        "watchlist": watch_customers,
        "total_monitored": sum(risk_distribution.values()),
        "high_risk_count": risk_distribution.get('HIGH', 0) + risk_distribution.get('CRITICAL', 0),
        "active_signals": signal_count[0] if signal_count else 0,
        "avg_composite_score": round(avg_score[0], 1) if avg_score and avg_score[0] else 0
    }
