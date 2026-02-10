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


@router.get("/supply-chain/customers")
async def supply_chain_customers(
    region: str = Query(None),
    db: Session = Depends(get_db)
):
    """공급망 모니터링 대상 기업 목록"""
    rc = ""
    rp = {}
    if region:
        rc = " AND c.region = :region"
        rp["region"] = region

    rows = db.execute(text(f"""
        SELECT DISTINCT sc.customer_id, c.customer_name, c.industry_name,
               AVG(sc.chain_default_probability) as avg_cpd,
               COUNT(DISTINCT sc.partner_id) as partner_count
        FROM ews_supply_chain_temporal sc
        JOIN customer c ON sc.customer_id = c.customer_id
        WHERE sc.reference_month = '2026-02'{rc}
        GROUP BY sc.customer_id, c.customer_name, c.industry_name
        ORDER BY avg_cpd DESC
    """), rp)

    return [{"customer_id": r[0], "customer_name": r[1], "industry": r[2],
             "avg_chain_pd": round(r[3], 4), "partner_count": r[4]} for r in rows]


@router.get("/supply-chain/dashboard")
async def supply_chain_dashboard(
    region: str = Query(None),
    db: Session = Depends(get_db)
):
    """공급망 리스크 요약"""
    rc = ""
    rp = {}
    if region:
        rc = " AND c.region = :region"
        rp["region"] = region

    stats = db.execute(text(f"""
        SELECT
            COUNT(DISTINCT sc.customer_id) as monitored,
            COUNT(DISTINCT sc.partner_id) as partner_count,
            AVG(sc.chain_default_probability) as avg_chain_pd,
            SUM(CASE WHEN sc.payment_status = 'DELINQUENT' THEN 1 ELSE 0 END) as delinquent_count,
            SUM(CASE WHEN sc.payment_status = 'DELAYED' THEN 1 ELSE 0 END) as delayed_count,
            SUM(CASE WHEN sc.chain_default_probability > 0.1 THEN 1 ELSE 0 END) as high_risk_count
        FROM ews_supply_chain_temporal sc
        JOIN customer c ON sc.customer_id = c.customer_id
        WHERE sc.reference_month = '2026-02'{rc}
    """), rp).fetchone()

    trend = db.execute(text(f"""
        SELECT sc.reference_month,
               AVG(sc.chain_default_probability) as avg_cpd,
               SUM(CASE WHEN sc.payment_status != 'NORMAL' THEN 1 ELSE 0 END) as problem_count
        FROM ews_supply_chain_temporal sc
        JOIN customer c ON sc.customer_id = c.customer_id
        WHERE 1=1{rc}
        GROUP BY sc.reference_month ORDER BY sc.reference_month
    """), rp)

    trend_data = [{"month": r[0], "avg_chain_pd": round(r[1], 4), "problem_count": r[2]} for r in trend]

    return {
        "monitored_customers": stats[0] if stats else 0,
        "partner_count": stats[1] if stats else 0,
        "avg_chain_default_prob": round(stats[2], 4) if stats and stats[2] else 0,
        "delinquent_count": stats[3] if stats else 0,
        "delayed_count": stats[4] if stats else 0,
        "high_risk_relations": stats[5] if stats else 0,
        "trend": trend_data,
    }


@router.get("/supply-chain/{customer_id}/temporal")
async def supply_chain_temporal(customer_id: str, db: Session = Depends(get_db)):
    """고객별 공급망 시계열"""
    rows = db.execute(text("""
        SELECT sc.reference_month, sc.partner_id, c2.customer_name as partner_name,
               sc.transaction_amount, sc.transaction_change_rate, sc.payment_status,
               sc.partner_credit_grade, sc.chain_default_probability, sc.dependency_ratio
        FROM ews_supply_chain_temporal sc
        JOIN customer c2 ON sc.partner_id = c2.customer_id
        WHERE sc.customer_id = :cid
        ORDER BY sc.reference_month DESC, sc.dependency_ratio DESC
    """), {"cid": customer_id})

    data = [{"month": r[0], "partner_id": r[1], "partner_name": r[2],
             "transaction_amount": r[3], "change_rate": r[4], "payment_status": r[5],
             "partner_grade": r[6], "chain_pd": r[7], "dependency": r[8]} for r in rows]

    name_row = db.execute(text("SELECT customer_name FROM customer WHERE customer_id = :cid"), {"cid": customer_id}).fetchone()
    return {"customer_id": customer_id, "customer_name": name_row[0] if name_row else "", "data": data}


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
    region: str = Query(None),
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
    if region:
        query += " AND c.region = :region"
        params["region"] = region

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
    region: str = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    """종합 EWS 점수 조회 (선행지표 포함)"""
    region_cond = ""
    rp = {}
    if region:
        region_cond = " AND c.region = :region"
        rp["region"] = region

    query = """
        WITH latest AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY score_date DESC, score_id DESC) as rn
            FROM ews_composite_score
        )
        SELECT ecs.score_id, ecs.customer_id, c.customer_name, c.industry_name,
               ecs.score_date, ecs.financial_score, ecs.operational_score,
               ecs.external_score, ecs.supply_chain_score, ecs.composite_score,
               ecs.risk_level, ecs.predicted_default_prob, ecs.recommendation,
               ecs.transaction_score, ecs.public_registry_score, ecs.market_score,
               ecs.news_score, ecs.ews_grade, ecs.score_trend, ecs.previous_composite
        FROM latest ecs
        JOIN customer c ON ecs.customer_id = c.customer_id
        WHERE ecs.rn = 1
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
    if region:
        query += " AND c.region = :region"
        params["region"] = region

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
            "recommendation": row[12],
            "transaction_score": row[13],
            "public_registry_score": row[14],
            "market_score": row[15],
            "news_score": row[16],
            "ews_grade": row[17],
            "score_trend": row[18],
            "previous_composite": row[19],
        })

    # 요약 통계
    summary_result = db.execute(text(f"""
        WITH latest AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY score_date DESC, score_id DESC) as rn
            FROM ews_composite_score
        )
        SELECT ecs.risk_level, COUNT(*) as count,
               AVG(ecs.composite_score) as avg_score,
               AVG(ecs.predicted_default_prob) as avg_pd
        FROM latest ecs
        JOIN customer c ON ecs.customer_id = c.customer_id
        WHERE ecs.rn = 1{region_cond}
        GROUP BY ecs.risk_level
    """), rp)

    summary = {}
    for row in summary_result:
        summary[row[0]] = {
            "count": row[1],
            "avg_score": round(row[2], 1) if row[2] else 0,
            "avg_pd": round(row[3], 4) if row[3] else 0
        }

    return {"scores": scores, "total": len(scores), "summary_by_risk": summary}


@router.get("/dashboard")
async def get_ews_dashboard(
    region: str = Query(None),
    db: Session = Depends(get_db)
):
    """EWS 대시보드 요약"""
    region_cond = ""
    rp = {}
    if region:
        region_cond = " AND c.region = :region"
        rp["region"] = region

    latest_cte = """
        WITH latest AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY score_date DESC, score_id DESC) as rn
            FROM ews_composite_score
        )
    """

    # 위험 등급별 분포
    risk_dist = db.execute(text(f"""
        {latest_cte}
        SELECT ecs.risk_level, COUNT(*) as count
        FROM latest ecs
        JOIN customer c ON ecs.customer_id = c.customer_id
        WHERE ecs.rn = 1{region_cond}
        GROUP BY ecs.risk_level
    """), rp)

    risk_distribution = {row[0]: row[1] for row in risk_dist}

    # 평균 복합점수
    avg_score = db.execute(text(f"""
        {latest_cte}
        SELECT AVG(ecs.composite_score)
        FROM latest ecs
        JOIN customer c ON ecs.customer_id = c.customer_id
        WHERE ecs.rn = 1{region_cond}
    """), rp).fetchone()

    # 외부 신호 총 개수
    signal_count = db.execute(text(f"""
        SELECT COUNT(*)
        FROM ews_external_signal ees
        JOIN customer c ON ees.customer_id = c.customer_id
        WHERE 1=1{region_cond}
    """), rp).fetchone()

    # 최근 외부 신호 (심각도 높은 것)
    recent_signals = db.execute(text(f"""
        SELECT ees.signal_date, c.customer_name, ees.signal_type,
               ees.severity, ees.title
        FROM ews_external_signal ees
        JOIN customer c ON ees.customer_id = c.customer_id
        WHERE ees.severity IN ('HIGH', 'CRITICAL'){region_cond}
        ORDER BY ees.signal_date DESC
        LIMIT 10
    """), rp)

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
    watchlist = db.execute(text(f"""
        {latest_cte}
        SELECT c.customer_id, c.customer_name, c.industry_name,
               ecs.composite_score, ecs.risk_level, ecs.recommendation
        FROM latest ecs
        JOIN customer c ON ecs.customer_id = c.customer_id
        WHERE ecs.rn = 1 AND ecs.risk_level IN ('HIGH', 'CRITICAL'){region_cond}
        ORDER BY ecs.composite_score ASC
        LIMIT 20
    """), rp)

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


# ============================================
# 선행지표 신규 엔드포인트 (15개)
# ============================================

# --- 거래행태 (Transaction Behavior) ---

@router.get("/transaction-behavior/dashboard")
async def transaction_behavior_dashboard(
    region: str = Query(None),
    db: Session = Depends(get_db)
):
    """거래행태 이상 요약"""
    rc = ""
    rp = {}
    if region:
        rc = " AND c.region = :region"
        rp["region"] = region

    # 최근 월 기준 요약
    stats = db.execute(text(f"""
        SELECT
            COUNT(DISTINCT t.customer_id) as total_customers,
            AVG(t.limit_utilization) as avg_utilization,
            AVG(t.payment_delay_days) as avg_delay,
            AVG(t.deposit_outflow_rate) as avg_outflow,
            SUM(CASE WHEN t.limit_utilization > 0.8 THEN 1 ELSE 0 END) as high_util_count,
            SUM(CASE WHEN t.payment_delay_days > 7 THEN 1 ELSE 0 END) as delayed_count,
            SUM(CASE WHEN t.overdraft_count > 0 THEN 1 ELSE 0 END) as overdraft_count,
            SUM(CASE WHEN t.salary_transfer = 0 THEN 1 ELSE 0 END) as no_salary_count
        FROM ews_transaction_behavior t
        JOIN customer c ON t.customer_id = c.customer_id
        WHERE t.reference_month = '2026-02'{rc}
    """), rp).fetchone()

    # 월별 추이
    trend = db.execute(text(f"""
        SELECT t.reference_month,
               AVG(t.limit_utilization) as avg_util,
               AVG(t.payment_delay_days) as avg_delay,
               AVG(t.deposit_outflow_rate) as avg_outflow
        FROM ews_transaction_behavior t
        JOIN customer c ON t.customer_id = c.customer_id
        WHERE 1=1{rc}
        GROUP BY t.reference_month ORDER BY t.reference_month
    """), rp)

    trend_data = [{"month": r[0], "avg_utilization": round(r[1], 4), "avg_delay": round(r[2], 1), "avg_outflow": round(r[3], 4)} for r in trend]

    return {
        "total_customers": stats[0] if stats else 0,
        "avg_utilization": round(stats[1], 4) if stats and stats[1] else 0,
        "avg_delay_days": round(stats[2], 1) if stats and stats[2] else 0,
        "avg_outflow_rate": round(stats[3], 4) if stats and stats[3] else 0,
        "high_utilization_count": stats[4] if stats else 0,
        "delayed_payment_count": stats[5] if stats else 0,
        "overdraft_count": stats[6] if stats else 0,
        "no_salary_count": stats[7] if stats else 0,
        "trend": trend_data,
    }


@router.get("/transaction-behavior/anomalies")
async def transaction_behavior_anomalies(
    region: str = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """거래행태 이상징후 탐지 목록"""
    rc = ""
    rp: dict = {}
    if region:
        rc = " AND c.region = :region"
        rp["region"] = region

    rows = db.execute(text(f"""
        SELECT t.customer_id, c.customer_name, c.industry_name,
               t.reference_month, t.limit_utilization, t.payment_delay_days,
               t.deposit_outflow_rate, t.overdraft_count
        FROM ews_transaction_behavior t
        JOIN customer c ON t.customer_id = c.customer_id
        WHERE t.reference_month = '2026-02'
          AND (t.limit_utilization > 0.8 OR t.payment_delay_days > 7 OR t.overdraft_count > 2){rc}
        ORDER BY t.limit_utilization DESC
        LIMIT :lim
    """), {**rp, "lim": limit})

    items = []
    for r in rows:
        anomalies = []
        if r[4] and r[4] > 0.8: anomalies.append("한도소진율 높음")
        if r[5] and r[5] > 7: anomalies.append("결제지연")
        if r[6] and r[6] > 0.3: anomalies.append("예금유출")
        if r[7] and r[7] > 2: anomalies.append("당좌대월 반복")
        items.append({
            "customer_id": r[0], "customer_name": r[1], "industry_name": r[2],
            "month": r[3], "limit_utilization": r[4], "payment_delay_days": r[5],
            "deposit_outflow_rate": r[6], "overdraft_count": r[7], "anomaly_types": anomalies,
        })

    return {"anomalies": items, "total": len(items)}


@router.get("/transaction-behavior/{customer_id}")
async def transaction_behavior_customer(customer_id: str, db: Session = Depends(get_db)):
    """고객별 거래행태 12개월 시계열"""
    rows = db.execute(text("""
        SELECT t.reference_month, t.avg_balance, t.limit_utilization,
               t.payment_delay_days, t.salary_transfer, t.deposit_outflow_rate,
               t.transaction_count, t.overdraft_count
        FROM ews_transaction_behavior t
        WHERE t.customer_id = :cid
        ORDER BY t.reference_month
    """), {"cid": customer_id})

    data = []
    for r in rows:
        data.append({
            "month": r[0], "avg_balance": r[1], "limit_utilization": r[2],
            "payment_delay_days": r[3], "salary_transfer": r[4],
            "deposit_outflow_rate": r[5], "transaction_count": r[6], "overdraft_count": r[7],
        })

    name_row = db.execute(text("SELECT customer_name FROM customer WHERE customer_id = :cid"), {"cid": customer_id}).fetchone()
    return {"customer_id": customer_id, "customer_name": name_row[0] if name_row else "", "data": data}


# --- 공적정보 (Public Registry) ---

@router.get("/public-registry/customers")
async def public_registry_customers(
    region: str = Query(None),
    db: Session = Depends(get_db)
):
    """공적정보 발생 기업 목록"""
    rc = ""
    rp = {}
    if region:
        rc = " AND c.region = :region"
        rp["region"] = region

    rows = db.execute(text(f"""
        SELECT p.customer_id, c.customer_name, c.industry_name,
               COUNT(*) as event_count,
               SUM(CASE WHEN p.resolved = 0 THEN 1 ELSE 0 END) as unresolved,
               SUM(CASE WHEN p.severity IN ('HIGH','CRITICAL') THEN 1 ELSE 0 END) as severe_count,
               GROUP_CONCAT(DISTINCT p.event_type) as event_types
        FROM ews_public_registry p
        JOIN customer c ON p.customer_id = c.customer_id
        WHERE 1=1{rc}
        GROUP BY p.customer_id, c.customer_name, c.industry_name
        ORDER BY unresolved DESC, severe_count DESC
    """), rp)

    return [{"customer_id": r[0], "customer_name": r[1], "industry": r[2],
             "event_count": r[3], "unresolved": r[4], "severe_count": r[5],
             "event_types": r[6].split(',') if r[6] else []} for r in rows]


@router.get("/public-registry/dashboard")
async def public_registry_dashboard(
    region: str = Query(None),
    db: Session = Depends(get_db)
):
    """공적정보 현황 요약"""
    rc = ""
    rp = {}
    if region:
        rc = " AND c.region = :region"
        rp["region"] = region

    by_type = db.execute(text(f"""
        SELECT p.event_type, COUNT(*) as cnt,
               SUM(CASE WHEN p.severity IN ('HIGH','CRITICAL') THEN 1 ELSE 0 END) as severe
        FROM ews_public_registry p
        JOIN customer c ON p.customer_id = c.customer_id
        WHERE 1=1{rc}
        GROUP BY p.event_type
    """), rp)

    type_stats = [{"event_type": r[0], "count": r[1], "severe_count": r[2]} for r in by_type]

    totals = db.execute(text(f"""
        SELECT COUNT(*) as total, SUM(CASE WHEN resolved = 0 THEN 1 ELSE 0 END) as unresolved,
               COUNT(DISTINCT p.customer_id) as affected_customers
        FROM ews_public_registry p
        JOIN customer c ON p.customer_id = c.customer_id
        WHERE 1=1{rc}
    """), rp).fetchone()

    return {
        "total_events": totals[0] if totals else 0,
        "unresolved_events": totals[1] if totals else 0,
        "affected_customers": totals[2] if totals else 0,
        "by_type": type_stats,
    }


@router.get("/public-registry/timeline")
async def public_registry_timeline(
    region: str = Query(None),
    db: Session = Depends(get_db)
):
    """월별 공적정보 이벤트 타임라인"""
    rc = ""
    rp = {}
    if region:
        rc = " AND c.region = :region"
        rp["region"] = region

    rows = db.execute(text(f"""
        SELECT strftime('%Y-%m', p.event_date) as month, p.event_type, COUNT(*) as cnt
        FROM ews_public_registry p
        JOIN customer c ON p.customer_id = c.customer_id
        WHERE 1=1{rc}
        GROUP BY month, p.event_type
        ORDER BY month
    """), rp)

    timeline = []
    for r in rows:
        timeline.append({"month": r[0], "event_type": r[1], "count": r[2]})

    return {"timeline": timeline}


@router.get("/public-registry/{customer_id}")
async def public_registry_customer(customer_id: str, db: Session = Depends(get_db)):
    """고객별 공적정보 이벤트 이력"""
    rows = db.execute(text("""
        SELECT p.event_date, p.event_type, p.severity, p.description, p.amount, p.resolved, p.resolved_date
        FROM ews_public_registry p WHERE p.customer_id = :cid
        ORDER BY p.event_date DESC
    """), {"cid": customer_id})

    events = [{"event_date": r[0], "event_type": r[1], "severity": r[2], "description": r[3],
               "amount": r[4], "resolved": bool(r[5]), "resolved_date": r[6]} for r in rows]

    name_row = db.execute(text("SELECT customer_name FROM customer WHERE customer_id = :cid"), {"cid": customer_id}).fetchone()
    return {"customer_id": customer_id, "customer_name": name_row[0] if name_row else "", "events": events}


# --- 시장신호 (Market Signals) ---

@router.get("/market-signals/dashboard")
async def market_signals_dashboard(
    region: str = Query(None),
    db: Session = Depends(get_db)
):
    """시장신호 요약 (상장기업 대상)"""
    rc = ""
    rp = {}
    if region:
        rc = " AND c.region = :region"
        rp["region"] = region

    stats = db.execute(text(f"""
        SELECT
            COUNT(DISTINCT m.customer_id) as listed_count,
            AVG(m.distance_to_default) as avg_dd,
            AVG(m.cds_spread) as avg_cds,
            AVG(m.implied_pd) as avg_ipd,
            AVG(m.stock_price_change) as avg_stock_chg,
            SUM(CASE WHEN m.distance_to_default < 2 THEN 1 ELSE 0 END) as low_dd_count,
            SUM(CASE WHEN m.cds_spread > 200 THEN 1 ELSE 0 END) as high_cds_count
        FROM ews_market_signal m
        JOIN customer c ON m.customer_id = c.customer_id
        WHERE m.reference_month = '2026-02'{rc}
    """), rp).fetchone()

    trend = db.execute(text(f"""
        SELECT m.reference_month, AVG(m.distance_to_default), AVG(m.cds_spread),
               AVG(m.implied_pd), AVG(m.stock_price_change)
        FROM ews_market_signal m
        JOIN customer c ON m.customer_id = c.customer_id
        WHERE 1=1{rc}
        GROUP BY m.reference_month ORDER BY m.reference_month
    """), rp)

    trend_data = [{"month": r[0], "avg_dd": round(r[1], 2), "avg_cds": round(r[2], 1),
                   "avg_implied_pd": round(r[3], 4), "avg_stock_change": round(r[4], 2)} for r in trend]

    return {
        "listed_count": stats[0] if stats else 0,
        "avg_distance_to_default": round(stats[1], 2) if stats and stats[1] else 0,
        "avg_cds_spread": round(stats[2], 1) if stats and stats[2] else 0,
        "avg_implied_pd": round(stats[3], 4) if stats and stats[3] else 0,
        "avg_stock_change": round(stats[4], 2) if stats and stats[4] else 0,
        "low_dd_count": stats[5] if stats else 0,
        "high_cds_count": stats[6] if stats else 0,
        "trend": trend_data,
    }


@router.get("/market-signals/alerts")
async def market_signals_alerts(
    region: str = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """시장 경보 목록"""
    rc = ""
    rp: dict = {}
    if region:
        rc = " AND c.region = :region"
        rp["region"] = region

    rows = db.execute(text(f"""
        SELECT m.customer_id, c.customer_name, c.industry_name, m.reference_month,
               m.stock_price_change, m.cds_spread, m.distance_to_default, m.implied_pd
        FROM ews_market_signal m
        JOIN customer c ON m.customer_id = c.customer_id
        WHERE m.reference_month = '2026-02'
          AND (m.distance_to_default < 2 OR m.cds_spread > 200 OR m.stock_price_change < -10){rc}
        ORDER BY m.distance_to_default ASC
        LIMIT :lim
    """), {**rp, "lim": limit})

    alerts = []
    for r in rows:
        reasons = []
        if r[6] and r[6] < 2: reasons.append("DD 낮음")
        if r[5] and r[5] > 200: reasons.append("CDS 높음")
        if r[4] and r[4] < -10: reasons.append("주가 급락")
        alerts.append({
            "customer_id": r[0], "customer_name": r[1], "industry_name": r[2],
            "month": r[3], "stock_price_change": r[4], "cds_spread": r[5],
            "distance_to_default": r[6], "implied_pd": r[7], "alert_reasons": reasons,
        })

    return {"alerts": alerts, "total": len(alerts)}


@router.get("/market-signals/{customer_id}")
async def market_signals_customer(customer_id: str, db: Session = Depends(get_db)):
    """고객별 시장 시계열"""
    rows = db.execute(text("""
        SELECT m.reference_month, m.stock_price_change, m.cds_spread, m.bond_spread,
               m.distance_to_default, m.implied_pd, m.market_cap, m.volatility_30d
        FROM ews_market_signal m WHERE m.customer_id = :cid
        ORDER BY m.reference_month
    """), {"cid": customer_id})

    data = [{"month": r[0], "stock_price_change": r[1], "cds_spread": r[2], "bond_spread": r[3],
             "distance_to_default": r[4], "implied_pd": r[5], "market_cap": r[6], "volatility_30d": r[7]} for r in rows]

    name_row = db.execute(text("SELECT customer_name FROM customer WHERE customer_id = :cid"), {"cid": customer_id}).fetchone()
    return {"customer_id": customer_id, "customer_name": name_row[0] if name_row else "", "data": data}


# --- 뉴스감성 (News Sentiment) ---

@router.get("/news-sentiment/dashboard")
async def news_sentiment_dashboard(
    region: str = Query(None),
    db: Session = Depends(get_db)
):
    """뉴스 감성 요약"""
    rc = ""
    rp = {}
    if region:
        rc = " AND c.region = :region"
        rp["region"] = region

    stats = db.execute(text(f"""
        SELECT
            COUNT(DISTINCT nm.customer_id) as monitored,
            AVG(nm.avg_sentiment) as overall_sentiment,
            AVG(nm.negative_ratio) as avg_neg_ratio,
            SUM(nm.article_count) as total_articles,
            SUM(CASE WHEN nm.avg_sentiment < -0.3 THEN 1 ELSE 0 END) as neg_alert_count
        FROM ews_news_sentiment_monthly nm
        JOIN customer c ON nm.customer_id = c.customer_id
        WHERE nm.reference_month = '2026-02'{rc}
    """), rp).fetchone()

    trend = db.execute(text(f"""
        SELECT nm.reference_month, AVG(nm.avg_sentiment), AVG(nm.negative_ratio),
               SUM(nm.article_count)
        FROM ews_news_sentiment_monthly nm
        JOIN customer c ON nm.customer_id = c.customer_id
        WHERE 1=1{rc}
        GROUP BY nm.reference_month ORDER BY nm.reference_month
    """), rp)

    trend_data = [{"month": r[0], "avg_sentiment": round(r[1], 3), "avg_negative_ratio": round(r[2], 3),
                   "article_count": r[3]} for r in trend]

    return {
        "monitored_customers": stats[0] if stats else 0,
        "overall_sentiment": round(stats[1], 3) if stats and stats[1] else 0,
        "avg_negative_ratio": round(stats[2], 3) if stats and stats[2] else 0,
        "total_articles": stats[3] if stats else 0,
        "negative_alert_count": stats[4] if stats else 0,
        "trend": trend_data,
    }


@router.get("/news-sentiment/feed")
async def news_sentiment_feed(
    region: str = Query(None),
    sentiment: Optional[str] = None,
    limit: int = Query(30, le=100),
    db: Session = Depends(get_db)
):
    """뉴스 피드"""
    rc = ""
    rp: dict = {}
    if region:
        rc = " AND c.region = :region"
        rp["region"] = region

    sent_cond = ""
    if sentiment == "negative":
        sent_cond = " AND n.sentiment_score < -0.2"
    elif sentiment == "positive":
        sent_cond = " AND n.sentiment_score > 0.2"

    rows = db.execute(text(f"""
        SELECT n.publish_date, n.headline, n.source, n.sentiment_score, n.category,
               n.customer_id, c.customer_name
        FROM ews_news_sentiment n
        JOIN customer c ON n.customer_id = c.customer_id
        WHERE 1=1{rc}{sent_cond}
        ORDER BY n.publish_date DESC
        LIMIT :lim
    """), {**rp, "lim": limit})

    feed = [{"date": r[0], "headline": r[1], "source": r[2], "sentiment": r[3],
             "category": r[4], "customer_id": r[5], "customer_name": r[6]} for r in rows]

    return {"feed": feed, "total": len(feed)}


@router.get("/news-sentiment/{customer_id}")
async def news_sentiment_customer(customer_id: str, db: Session = Depends(get_db)):
    """고객별 뉴스/감성"""
    monthly = db.execute(text("""
        SELECT reference_month, article_count, avg_sentiment, negative_ratio, positive_ratio, dominant_category
        FROM ews_news_sentiment_monthly WHERE customer_id = :cid ORDER BY reference_month
    """), {"cid": customer_id})

    monthly_data = [{"month": r[0], "article_count": r[1], "avg_sentiment": r[2],
                     "negative_ratio": r[3], "positive_ratio": r[4], "dominant_category": r[5]} for r in monthly]

    articles = db.execute(text("""
        SELECT publish_date, headline, source, sentiment_score, category
        FROM ews_news_sentiment WHERE customer_id = :cid
        ORDER BY publish_date DESC LIMIT 20
    """), {"cid": customer_id})

    article_list = [{"date": r[0], "headline": r[1], "source": r[2], "sentiment": r[3], "category": r[4]} for r in articles]

    name_row = db.execute(text("SELECT customer_name FROM customer WHERE customer_id = :cid"), {"cid": customer_id}).fetchone()
    return {"customer_id": customer_id, "customer_name": name_row[0] if name_row else "",
            "monthly": monthly_data, "recent_articles": article_list}


# --- 통합 대시보드 ---

@router.get("/integrated-dashboard")
async def integrated_dashboard(
    region: str = Query(None),
    db: Session = Depends(get_db)
):
    """5채널 통합 대시보드"""
    rc = ""
    rp = {}
    if region:
        rc = " AND c.region = :region"
        rp["region"] = region

    # latest composite score per customer
    latest_cte = """
        WITH latest AS (
            SELECT ecs.*, ROW_NUMBER() OVER (PARTITION BY ecs.customer_id ORDER BY ecs.score_date DESC, ecs.score_id DESC) as rn
            FROM ews_composite_score ecs
        )
    """

    # EWS 등급 분포
    grade_dist = db.execute(text(f"""
        {latest_cte}
        SELECT l.ews_grade, COUNT(*) FROM latest l
        JOIN customer c ON l.customer_id = c.customer_id
        WHERE l.rn = 1 AND l.ews_grade IS NOT NULL{rc}
        GROUP BY l.ews_grade
    """), rp)
    grade_distribution = {r[0]: r[1] for r in grade_dist}

    # 5채널 평균 점수
    channel_avg = db.execute(text(f"""
        {latest_cte}
        SELECT
            AVG(l.transaction_score) as txn,
            AVG(l.public_registry_score) as pub,
            AVG(l.market_score) as mkt,
            AVG(l.news_score) as news,
            AVG(l.supply_chain_score) as sc,
            AVG(l.financial_score) as fin,
            AVG(l.composite_score) as composite,
            COUNT(*) as total
        FROM latest l
        JOIN customer c ON l.customer_id = c.customer_id
        WHERE l.rn = 1{rc}
    """), rp).fetchone()

    # 추세별 분포
    trend_dist = db.execute(text(f"""
        {latest_cte}
        SELECT l.score_trend, COUNT(*) FROM latest l
        JOIN customer c ON l.customer_id = c.customer_id
        WHERE l.rn = 1 AND l.score_trend IS NOT NULL{rc}
        GROUP BY l.score_trend
    """), rp)
    trend_distribution = {r[0]: r[1] for r in trend_dist}

    # 12개월 시그널 타임라인 (월별 등급별 고객수)
    signal_timeline = db.execute(text(f"""
        SELECT t.reference_month,
               SUM(CASE WHEN ecs.ews_grade = 'CRITICAL' THEN 1 ELSE 0 END) as critical,
               SUM(CASE WHEN ecs.ews_grade = 'WARNING' THEN 1 ELSE 0 END) as warning,
               SUM(CASE WHEN ecs.ews_grade = 'WATCH' THEN 1 ELSE 0 END) as watch,
               AVG(t.limit_utilization) as avg_util
        FROM ews_transaction_behavior t
        JOIN ews_composite_score ecs ON t.customer_id = ecs.customer_id
        JOIN customer c ON t.customer_id = c.customer_id
        WHERE 1=1{rc}
        GROUP BY t.reference_month ORDER BY t.reference_month
    """), rp)

    timeline_data = [{"month": r[0], "critical": r[1], "warning": r[2], "watch": r[3],
                      "avg_utilization": round(r[4], 4) if r[4] else 0} for r in signal_timeline]

    # 워치리스트 (WARNING + CRITICAL 상위 20)
    watchlist = db.execute(text(f"""
        {latest_cte}
        SELECT c.customer_id, c.customer_name, c.industry_name,
               l.composite_score, l.ews_grade, l.score_trend,
               l.transaction_score, l.public_registry_score, l.market_score, l.news_score
        FROM latest l
        JOIN customer c ON l.customer_id = c.customer_id
        WHERE l.rn = 1 AND l.ews_grade IN ('WARNING', 'CRITICAL'){rc}
        ORDER BY l.composite_score ASC LIMIT 20
    """), rp)

    watch_list = [{
        "customer_id": r[0], "customer_name": r[1], "industry_name": r[2],
        "composite_score": r[3], "ews_grade": r[4], "score_trend": r[5],
        "transaction_score": r[6], "public_registry_score": r[7],
        "market_score": r[8], "news_score": r[9],
    } for r in watchlist]

    return {
        "grade_distribution": grade_distribution,
        "channel_scores": {
            "transaction": round(channel_avg[0], 1) if channel_avg and channel_avg[0] else 0,
            "public_registry": round(channel_avg[1], 1) if channel_avg and channel_avg[1] else 0,
            "market": round(channel_avg[2], 1) if channel_avg and channel_avg[2] else 0,
            "news": round(channel_avg[3], 1) if channel_avg and channel_avg[3] else 0,
            "supply_chain": round(channel_avg[4], 1) if channel_avg and channel_avg[4] else 0,
            "financial": round(channel_avg[5], 1) if channel_avg and channel_avg[5] else 0,
            "composite": round(channel_avg[6], 1) if channel_avg and channel_avg[6] else 0,
        },
        "total_monitored": channel_avg[7] if channel_avg else 0,
        "trend_distribution": trend_distribution,
        "signal_timeline": timeline_data,
        "watchlist": watch_list,
    }
