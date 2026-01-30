"""
동적 한도 관리 API
==================
경기 사이클, HHI, 부도율 기반 자동 한도 조정
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from ..core.database import get_db

router = APIRouter(prefix="/api/dynamic-limits", tags=["Dynamic Limits"])


# ============================================
# 기능 설명 (모달용)
# ============================================

FEATURE_DESCRIPTIONS = {
    "dynamic_limits_overview": {
        "title": "동적 한도 관리 (Dynamic Limit Management)",
        "description": "시장 상황과 포트폴리오 리스크에 연동하여 한도를 자동으로 조정하는 시스템",
        "benefits": [
            "경기 변동에 선제적 대응",
            "집중도 리스크 자동 통제",
            "운영 효율성 향상"
        ],
        "methodology": """
**동적 한도 조정 원리**

전통적인 정적 한도 관리는 시장 상황 변화에 늦은 대응을 초래합니다.
동적 한도 관리는 사전 정의된 트리거 조건 충족 시 자동으로 한도를 조정합니다.

**트리거 유형**

1. **경기 사이클 기반 (Cycle-Based)**
   - 경기 침체기: 고위험 업종 한도 자동 축소
   - 경기 확장기: 성장 업종 한도 확대 가능

2. **집중도 기반 (HHI-Based)**
   - 업종 HHI가 임계치 초과 시 신규 한도 동결
   - Top 차주 집중도 급증 시 추가 취급 제한

3. **부도율 기반 (Default Rate-Based)**
   - 특정 업종/등급 부도율 급등 시 한도 축소
   - 연체율 증가 추세 시 모니터링 강화

**조정 프로세스**
```
트리거 발생 → 규칙 매칭 → 조정량 산출 → 승인 → 적용 → 모니터링
```
"""
    },
    "economic_cycle": {
        "title": "경기 사이클 지표",
        "description": "거시경제 지표를 통합하여 현재 경기 국면을 판단",
        "methodology": """
**경기 사이클 4국면**

| 국면 | 특징 | 한도 전략 |
|------|------|----------|
| EXPANSION (확장) | GDP↑, 실업률↓, 신용↑ | 성장 업종 한도 확대 |
| PEAK (정점) | GDP 정체, 인플레 우려 | 리스크 업종 한도 동결 |
| CONTRACTION (수축) | GDP↓, 실업률↑ | 고위험 한도 축소 |
| TROUGH (저점) | GDP 저점, 회복 조짐 | 방어적 운영 |

**국면 판단 지표**
- GDP 성장률
- 실업률
- 기준금리
- 소비자신뢰지수
- 신용스프레드
""",
        "formula": "Cycle_Phase = f(GDP_Growth, Unemployment, Interest_Rate, Confidence_Index)"
    },
    "trigger_rules": {
        "title": "한도 조정 트리거 규칙",
        "description": "자동 한도 조정을 발동하는 조건과 조정 방식",
        "methodology": """
**규칙 구성 요소**

1. **트리거 조건 (Trigger Condition)**
   - 모니터링 지표
   - 임계치
   - 비교 연산 (>, <, =)

2. **조정 행동 (Action)**
   - INCREASE: 한도 증가
   - DECREASE: 한도 감소
   - SUSPEND: 신규 취급 중단

3. **조정 대상 (Target)**
   - INDUSTRY: 업종별 한도
   - SINGLE_BORROWER: 단일 차주 한도
   - RATING: 등급별 한도

**예시 규칙**
```
IF cycle_phase == 'CONTRACTION'
   AND industry_risk_grade IN ('C', 'D')
THEN DECREASE industry_limit BY 15%
```
"""
    }
}


@router.get("/feature-description/{feature_id}")
async def get_feature_description(feature_id: str):
    """기능 설명 조회 (모달용)"""
    if feature_id in FEATURE_DESCRIPTIONS:
        return FEATURE_DESCRIPTIONS[feature_id]
    return {"error": "Feature not found"}


@router.get("/economic-cycle")
async def get_economic_cycle(
    months: int = Query(12, description="조회 기간 (월)"),
    db: Session = Depends(get_db)
):
    """경기 사이클 지표 조회"""
    result = db.execute(text("""
        SELECT cycle_id, reference_date, cycle_phase,
               gdp_growth, unemployment_rate, interest_rate,
               inflation_rate, credit_spread, confidence_index
        FROM economic_cycle
        ORDER BY reference_date DESC
        LIMIT :months
    """), {"months": months})

    cycles = []
    for row in result:
        cycles.append({
            "cycle_id": row[0],
            "reference_date": row[1],
            "cycle_phase": row[2],
            "gdp_growth": row[3],
            "unemployment_rate": row[4],
            "interest_rate": row[5],
            "inflation_rate": row[6],
            "credit_spread": row[7],
            "confidence_index": row[8]
        })

    # 현재 국면
    current_phase = cycles[0]["cycle_phase"] if cycles else "UNKNOWN"

    # 국면별 통계
    phase_stats = db.execute(text("""
        SELECT cycle_phase, COUNT(*) as count,
               AVG(gdp_growth) as avg_gdp,
               AVG(unemployment_rate) as avg_unemployment
        FROM economic_cycle
        GROUP BY cycle_phase
    """))

    phase_summary = {}
    for row in phase_stats:
        phase_summary[row[0]] = {
            "count": row[1],
            "avg_gdp": round(row[2], 2) if row[2] else 0,
            "avg_unemployment": round(row[3], 2) if row[3] else 0
        }

    return {
        "current_phase": current_phase,
        "cycles": cycles,
        "phase_summary": phase_summary
    }


@router.get("/rules")
async def get_dynamic_limit_rules(
    is_active: Optional[bool] = True,
    rule_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """동적 한도 규칙 조회"""
    query = """
        SELECT rule_id, rule_name, rule_type, trigger_condition,
               trigger_threshold, action_type, adjustment_pct,
               target_limit_type, target_dimension, priority,
               is_active, description
        FROM dynamic_limit_rule
        WHERE 1=1
    """
    params = {}

    if is_active is not None:
        query += " AND is_active = :is_active"
        params["is_active"] = 1 if is_active else 0
    if rule_type:
        query += " AND rule_type = :rule_type"
        params["rule_type"] = rule_type

    query += " ORDER BY priority ASC"

    result = db.execute(text(query), params)

    rules = []
    for row in result:
        rules.append({
            "rule_id": row[0],
            "rule_name": row[1],
            "rule_type": row[2],
            "trigger_condition": row[3],
            "trigger_threshold": row[4],
            "action_type": row[5],
            "adjustment_pct": row[6],
            "target_limit_type": row[7],
            "target_dimension": row[8],
            "priority": row[9],
            "is_active": bool(row[10]),
            "description": row[11]
        })

    return {"rules": rules, "total": len(rules)}


@router.get("/adjustments")
async def get_limit_adjustments(
    limit_id: Optional[str] = None,
    status: Optional[str] = None,
    months: int = Query(12, description="조회 기간 (월)"),
    db: Session = Depends(get_db)
):
    """한도 조정 이력 조회"""
    query = """
        SELECT dla.adjustment_id, dla.rule_id, dlr.rule_name,
               dla.limit_id, ld.limit_name, dla.adjustment_date,
               dla.trigger_value, dla.previous_limit, dla.adjusted_limit,
               dla.adjustment_pct, dla.reason, dla.approved_by, dla.status
        FROM dynamic_limit_adjustment dla
        JOIN dynamic_limit_rule dlr ON dla.rule_id = dlr.rule_id
        JOIN limit_definition ld ON dla.limit_id = ld.limit_id
        WHERE 1=1
    """
    params = {}

    if limit_id:
        query += " AND dla.limit_id = :limit_id"
        params["limit_id"] = limit_id
    if status:
        query += " AND dla.status = :status"
        params["status"] = status

    query += " ORDER BY dla.adjustment_date DESC LIMIT 100"

    result = db.execute(text(query), params)

    adjustments = []
    for row in result:
        adjustments.append({
            "adjustment_id": row[0],
            "rule_id": row[1],
            "rule_name": row[2],
            "limit_id": row[3],
            "limit_name": row[4],
            "adjustment_date": row[5],
            "trigger_value": row[6],
            "previous_limit": row[7],
            "adjusted_limit": row[8],
            "adjustment_pct": row[9],
            "reason": row[10],
            "approved_by": row[11],
            "status": row[12]
        })

    # 요약 통계
    summary = db.execute(text("""
        SELECT
            COUNT(*) as total_adjustments,
            SUM(CASE WHEN adjustment_pct > 0 THEN 1 ELSE 0 END) as increases,
            SUM(CASE WHEN adjustment_pct < 0 THEN 1 ELSE 0 END) as decreases,
            AVG(ABS(adjustment_pct)) as avg_adjustment_pct
        FROM dynamic_limit_adjustment
    """))

    summary_row = summary.fetchone()

    return {
        "adjustments": adjustments,
        "total": len(adjustments),
        "summary": {
            "total_adjustments": summary_row[0],
            "increases": summary_row[1],
            "decreases": summary_row[2],
            "avg_adjustment_pct": round(summary_row[3], 1) if summary_row[3] else 0
        }
    }


@router.get("/current-status")
async def get_current_limit_status(db: Session = Depends(get_db)):
    """현재 한도 상태 및 동적 조정 현황"""
    # 업종별 한도 및 조정 현황 - limit_id로 조인
    industry_status = db.execute(text("""
        SELECT ld.dimension_code, ld.limit_name, ld.limit_amount,
               COALESCE(SUM(dla.adjustment_pct), 0) as total_adjustment
        FROM limit_definition ld
        LEFT JOIN dynamic_limit_adjustment dla ON ld.limit_id = dla.limit_id
        WHERE ld.dimension_type = 'INDUSTRY' AND ld.status = 'ACTIVE'
        GROUP BY ld.dimension_code, ld.limit_name, ld.limit_amount
    """))

    status_list = []
    for row in industry_status:
        base_limit = row[2] or 0
        adjustment_pct = row[3] or 0
        adjusted_limit = base_limit * (1 + adjustment_pct / 100)
        status_list.append({
            "industry_code": row[0],
            "industry_name": row[1] or row[0],
            "base_limit": base_limit,
            "current_adjustment": adjustment_pct,
            "adjusted_limit": adjusted_limit
        })

    # 포트폴리오 요약에서 업종 정보 보완 (한도가 없는 경우)
    if not status_list:
        industry_summary = db.execute(text("""
            SELECT segment_code, segment_name, total_exposure, total_rwa
            FROM portfolio_summary
            WHERE segment_type = 'INDUSTRY'
        """))

        for row in industry_summary:
            # 가상의 한도 생성 (실제 한도가 없는 경우)
            base_limit = row[2] * 1.2 if row[2] else 0  # 익스포저의 120%를 기준 한도로
            adjustment = 0
            status_list.append({
                "industry_code": row[0],
                "industry_name": row[1],
                "base_limit": base_limit,
                "current_adjustment": adjustment,
                "adjusted_limit": base_limit
            })

    return {
        "status": status_list
    }


@router.get("/simulation")
async def simulate_limit_adjustment(
    rule_id: str,
    trigger_value: float,
    db: Session = Depends(get_db)
):
    """한도 조정 시뮬레이션"""
    # 규칙 조회
    rule = db.execute(text("""
        SELECT rule_name, rule_type, trigger_threshold, action_type,
               adjustment_pct, target_limit_type, target_dimension
        FROM dynamic_limit_rule
        WHERE rule_id = :rule_id
    """), {"rule_id": rule_id}).fetchone()

    if not rule:
        return {"error": "Rule not found"}

    # 영향받는 한도 조회
    affected_limits = db.execute(text("""
        SELECT limit_id, limit_name, limit_amount
        FROM limit_definition
        WHERE limit_type = :limit_type
        AND status = 'ACTIVE'
    """), {"limit_type": rule[5]})

    simulated_results = []
    for limit in affected_limits:
        original = limit[2]
        adjusted = original * (1 + rule[4] / 100)

        simulated_results.append({
            "limit_id": limit[0],
            "limit_name": limit[1],
            "original_amount": original,
            "adjusted_amount": round(adjusted, 0),
            "change_amount": round(adjusted - original, 0),
            "change_pct": rule[4]
        })

    return {
        "rule": {
            "rule_id": rule_id,
            "rule_name": rule[0],
            "rule_type": rule[1],
            "threshold": rule[2],
            "action": rule[3],
            "adjustment_pct": rule[4]
        },
        "trigger_value": trigger_value,
        "trigger_met": trigger_value >= rule[2] if rule[2] else False,
        "affected_limits": simulated_results,
        "total_impact": sum(r["change_amount"] for r in simulated_results)
    }


@router.get("/simulate-shock")
async def simulate_economic_shock(
    gdp_growth_shock: float = Query(0, description="GDP 성장률 충격 (%p)"),
    interest_rate_shock: float = Query(0, description="금리 충격 (%p)"),
    db: Session = Depends(get_db)
):
    """경기 충격 기반 한도 조정 시뮬레이션"""

    # 현재 경기 사이클
    current_cycle = db.execute(text("""
        SELECT gdp_growth, interest_rate, cycle_phase
        FROM economic_cycle
        ORDER BY reference_date DESC
        LIMIT 1
    """)).fetchone()

    base_gdp = current_cycle[0] if current_cycle else 2.5
    base_rate = current_cycle[1] if current_cycle else 3.5
    current_phase = current_cycle[2] if current_cycle else "EXPANSION"

    # 충격 적용 후 예상 지표
    shocked_gdp = base_gdp + gdp_growth_shock
    shocked_rate = base_rate + interest_rate_shock

    # 새로운 경기 국면 예측
    if shocked_gdp < 0:
        new_phase = "CONTRACTION"
    elif shocked_gdp < 1:
        new_phase = "TROUGH"
    elif shocked_gdp > 3:
        new_phase = "EXPANSION"
    else:
        new_phase = "PEAK"

    # 업종별 한도 및 민감도 조회
    industry_limits = db.execute(text("""
        SELECT ld.dimension_code, ld.limit_name, ld.limit_amount
        FROM limit_definition ld
        WHERE ld.dimension_type = 'INDUSTRY' AND ld.status = 'ACTIVE'
    """))

    # 업종별 민감도 (일부 업종은 경기에 더 민감)
    industry_sensitivity = {
        'IND001': {'gdp': 0.5, 'rate': 0.3},   # 제조업 - 경기 민감
        'IND002': {'gdp': 0.3, 'rate': 0.2},   # 서비스업 - 보통
        'IND003': {'gdp': 0.4, 'rate': 0.6},   # 건설업 - 금리 민감
        'IND004': {'gdp': 0.6, 'rate': 0.4},   # 도소매업 - 경기 민감
        'IND005': {'gdp': 0.2, 'rate': 0.5},   # 금융업 - 금리 민감
        'IND006': {'gdp': 0.3, 'rate': 0.3},   # IT/통신 - 보통
        'IND007': {'gdp': 0.7, 'rate': 0.5},   # 부동산 - 경기+금리
        'IND008': {'gdp': 0.8, 'rate': 0.6},   # 숙박/음식점 - 경기 매우 민감
        'IND009': {'gdp': 0.9, 'rate': 0.7},   # 운수업 - 경기 매우 민감
        'IND010': {'gdp': 0.2, 'rate': 0.2},   # 공공/교육 - 안정적
    }

    results = []
    for row in industry_limits:
        ind_code = row[0]
        ind_name = row[1]
        base_limit = row[2] or 0

        # 민감도 조회 (기본값 적용)
        sensitivity = industry_sensitivity.get(ind_code, {'gdp': 0.4, 'rate': 0.4})

        # 조정률 계산: GDP 하락(-) -> 한도 축소(-), 금리 상승(+) -> 한도 축소(-)
        gdp_impact = gdp_growth_shock * sensitivity['gdp'] * 5  # 1%p GDP 하락 -> 최대 5% 한도 축소
        rate_impact = -interest_rate_shock * sensitivity['rate'] * 3  # 1%p 금리 상승 -> 최대 3% 한도 축소

        total_adjustment = round(gdp_impact + rate_impact, 1)

        # 조정 한도 (-30% ~ +20% 범위로 제한)
        total_adjustment = max(-30, min(20, total_adjustment))

        adjusted_limit = base_limit * (1 + total_adjustment / 100)

        results.append({
            "industry_code": ind_code,
            "industry_name": ind_name,
            "base_limit": base_limit,
            "simulated_adjustment": total_adjustment,
            "adjusted_limit": round(adjusted_limit, 0),
            "gdp_sensitivity": sensitivity['gdp'],
            "rate_sensitivity": sensitivity['rate']
        })

    # 결과가 없으면 포트폴리오 요약에서 업종 정보 가져오기
    if not results:
        industry_summary = db.execute(text("""
            SELECT segment_code, segment_name, total_exposure
            FROM portfolio_summary
            WHERE segment_type = 'INDUSTRY'
        """))

        for row in industry_summary:
            ind_code = row[0]
            ind_name = row[1]
            base_limit = (row[2] or 0) * 1.2  # 익스포저의 120%를 기준 한도로

            sensitivity = industry_sensitivity.get(ind_code, {'gdp': 0.4, 'rate': 0.4})

            gdp_impact = gdp_growth_shock * sensitivity['gdp'] * 5
            rate_impact = -interest_rate_shock * sensitivity['rate'] * 3
            total_adjustment = round(gdp_impact + rate_impact, 1)
            total_adjustment = max(-30, min(20, total_adjustment))

            adjusted_limit = base_limit * (1 + total_adjustment / 100)

            results.append({
                "industry_code": ind_code,
                "industry_name": ind_name,
                "base_limit": base_limit,
                "simulated_adjustment": total_adjustment,
                "adjusted_limit": round(adjusted_limit, 0),
                "gdp_sensitivity": sensitivity['gdp'],
                "rate_sensitivity": sensitivity['rate']
            })

    return {
        "scenario": {
            "gdp_growth_shock": gdp_growth_shock,
            "interest_rate_shock": interest_rate_shock,
            "base_gdp": base_gdp,
            "base_rate": base_rate,
            "shocked_gdp": shocked_gdp,
            "shocked_rate": shocked_rate,
            "current_phase": current_phase,
            "predicted_phase": new_phase
        },
        "results": results,
        "total_base_limit": sum(r["base_limit"] for r in results),
        "total_adjusted_limit": sum(r["adjusted_limit"] for r in results)
    }
