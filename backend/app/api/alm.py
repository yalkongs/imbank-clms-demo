"""
금리 리스크 헷지 분석 (ALM) API
================================
금리 갭 분석, 시나리오 분석, 헷지 제안
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from ..core.database import get_db

router = APIRouter(prefix="/api/alm", tags=["ALM - Interest Rate Risk"])


# ============================================
# 기능 설명 (모달용)
# ============================================

FEATURE_DESCRIPTIONS = {
    "alm_overview": {
        "title": "금리 리스크 헷지 분석 (ALM)",
        "description": "자산-부채 금리 미스매치 관리 및 순이자마진(NIM) 안정화",
        "benefits": [
            "금리 변동 리스크 관리",
            "NIM 안정화",
            "자본 적정성 유지"
        ],
        "methodology": """
**ALM (Asset-Liability Management)**

은행의 자산(여신)과 부채(수신)의 금리 특성 차이로 인한 리스크를 관리합니다.

**주요 리스크 유형**

1. **재조정 리스크 (Repricing Risk)**
   - 자산/부채 금리 재조정 시점 불일치
   - 금리 변동 시 NIM 변동

2. **기준금리 리스크 (Basis Risk)**
   - 연동 기준금리 차이 (CD vs 코픽스)
   - 스프레드 변동 위험

3. **수익률 곡선 리스크 (Yield Curve Risk)**
   - 장단기 금리차 변동
   - 스티프닝/플래트닝

4. **옵션성 리스크 (Optionality Risk)**
   - 조기상환, 중도해지
   - 내재옵션 가치 변동

**관리 지표**
- NIM Sensitivity: NIM의 금리 민감도
- EVE Sensitivity: 경제적 가치의 금리 민감도
- Duration Gap: 자산/부채 듀레이션 차이
"""
    },
    "gap_analysis": {
        "title": "금리 갭 분석 (Gap Analysis)",
        "description": "만기별 자산-부채 재조정 시점 차이 분석",
        "methodology": """
**재조정 갭 (Repricing Gap)**

```
Gap = RSA - RSL
```
- RSA: Rate Sensitive Assets (금리민감자산)
- RSL: Rate Sensitive Liabilities (금리민감부채)

**갭의 의미**
| 갭 | 금리 상승 시 | 금리 하락 시 |
|---|-----------|-----------|
| 양(+) | NIM 증가 | NIM 감소 |
| 음(-) | NIM 감소 | NIM 증가 |

**NIM 민감도 계산**
```
ΔNIM = Gap × Δr / Total_Assets
```

**듀레이션 갭 (Duration Gap)**
```
Duration_Gap = D_A - (L/A) × D_L
```
- D_A: 자산 듀레이션
- D_L: 부채 듀레이션
- L/A: 부채/자산 비율

**EVE 민감도**
```
ΔEVE = -Duration_Gap × Assets × Δr
```
""",
        "formula": "Repricing_Gap = Σ(Floating_Assets) - Σ(Floating_Liabilities)"
    },
    "hedge_strategy": {
        "title": "금리 헷지 전략",
        "description": "파생상품을 활용한 금리 리스크 헷지",
        "methodology": """
**주요 헷지 수단**

1. **금리스왑 (IRS: Interest Rate Swap)**
   - 고정↔변동 금리 교환
   - 갭 조정에 효과적
   - 비용: 스왑 스프레드

2. **금리선도 (FRA: Forward Rate Agreement)**
   - 미래 특정 시점 금리 확정
   - 단기 갭 헷지
   - 비용: 선도 프리미엄

3. **금리캡/플로어 (Cap/Floor)**
   - 금리 상한/하한 설정
   - 옵션 프리미엄 지불
   - 비대칭 헷지

4. **스왑션 (Swaption)**
   - 스왑 계약 옵션
   - 불확실성 대응
   - 프리미엄 비용

**헷지 효과성 평가**
```
Hedge_Effectiveness = Δ(Hedged_Position) / Δ(Unhedged_Position)
```

목표: 80% 이상 효과성 유지
"""
    }
}


@router.get("/feature-description/{feature_id}")
async def get_feature_description(feature_id: str):
    """기능 설명 조회 (모달용)"""
    if feature_id in FEATURE_DESCRIPTIONS:
        return FEATURE_DESCRIPTIONS[feature_id]
    return {"error": "Feature not found"}


@router.get("/gap-analysis")
async def get_gap_analysis(db: Session = Depends(get_db)):
    """금리 갭 분석"""
    result = db.execute(text("""
        SELECT gap_id, base_date, bucket,
               fixed_rate_assets, floating_rate_assets, total_assets, asset_duration,
               fixed_rate_liabilities, floating_rate_liabilities, total_liabilities, liability_duration,
               repricing_gap, duration_gap, cumulative_gap,
               nim_sensitivity_100bp, eve_sensitivity_100bp
        FROM interest_rate_gap
        ORDER BY
            CASE bucket
                WHEN '1M' THEN 1
                WHEN '3M' THEN 2
                WHEN '6M' THEN 3
                WHEN '1Y' THEN 4
                WHEN '2Y' THEN 5
                WHEN '3Y' THEN 6
                WHEN '5Y' THEN 7
                ELSE 8
            END
    """))

    gaps = []
    total_repricing_gap = 0
    total_nim_sens = 0

    for row in result:
        total_repricing_gap += row[11] or 0
        total_nim_sens += row[14] or 0

        gaps.append({
            "gap_id": row[0],
            "base_date": row[1],
            "bucket": row[2],
            "assets": {
                "fixed": row[3],
                "floating": row[4],
                "total": row[5],
                "duration": row[6]
            },
            "liabilities": {
                "fixed": row[7],
                "floating": row[8],
                "total": row[9],
                "duration": row[10]
            },
            "gaps": {
                "repricing_gap": row[11],
                "duration_gap": row[12],
                "cumulative_gap": row[13]
            },
            "sensitivity": {
                "nim_100bp": row[14],
                "eve_100bp": row[15]
            }
        })

    return {
        "gaps": gaps,
        "summary": {
            "total_repricing_gap": total_repricing_gap,
            "total_nim_sensitivity_100bp": round(total_nim_sens, 2),
            "gap_assessment": "양수 갭 (금리 상승 시 유리)" if total_repricing_gap > 0 else "음수 갭 (금리 하락 시 유리)"
        }
    }


@router.get("/scenarios")
async def get_interest_rate_scenarios(db: Session = Depends(get_db)):
    """금리 시나리오 목록"""
    result = db.execute(text("""
        SELECT scenario_id, scenario_name, scenario_type,
               short_rate_shock, long_rate_shock, probability
        FROM interest_rate_scenario
        ORDER BY scenario_type
    """))

    scenarios = []
    for row in result:
        scenarios.append({
            "scenario_id": row[0],
            "scenario_name": row[1],
            "scenario_type": row[2],
            "short_rate_shock_bp": row[3],
            "long_rate_shock_bp": row[4],
            "probability": row[5]
        })

    return {"scenarios": scenarios}


@router.get("/scenario-results")
async def get_scenario_results(
    scenario_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """시나리오 분석 결과"""
    query = """
        SELECT asr.result_id, asr.base_date, asr.scenario_id, irs.scenario_name,
               irs.scenario_type, irs.short_rate_shock, irs.long_rate_shock,
               asr.current_nim, asr.stressed_nim, asr.nim_change,
               asr.current_eve, asr.stressed_eve, asr.eve_change, asr.eve_change_pct,
               asr.capital_impact
        FROM alm_scenario_result asr
        JOIN interest_rate_scenario irs ON asr.scenario_id = irs.scenario_id
    """
    params = {}

    if scenario_id:
        query += " WHERE asr.scenario_id = :scenario_id"
        params["scenario_id"] = scenario_id

    query += " ORDER BY asr.base_date DESC, irs.scenario_type"

    result = db.execute(text(query), params)

    results = []
    for row in result:
        results.append({
            "result_id": row[0],
            "base_date": row[1],
            "scenario_id": row[2],
            "scenario_name": row[3],
            "scenario_type": row[4],
            "rate_shock": {
                "short_term_bp": row[5],
                "long_term_bp": row[6]
            },
            "nim_impact": {
                "current": row[7],
                "stressed": row[8],
                "change": row[9]
            },
            "eve_impact": {
                "current": row[10],
                "stressed": row[11],
                "change": row[12],
                "change_pct": row[13]
            },
            "capital_impact": row[14]
        })

    # 시나리오별 영향 요약
    if not scenario_id:
        worst_nim = min(results, key=lambda x: x["nim_impact"]["change"]) if results else None
        worst_eve = min(results, key=lambda x: x["eve_impact"]["change"]) if results else None

        summary = {
            "worst_nim_scenario": worst_nim["scenario_name"] if worst_nim else None,
            "worst_nim_change": worst_nim["nim_impact"]["change"] if worst_nim else None,
            "worst_eve_scenario": worst_eve["scenario_name"] if worst_eve else None,
            "worst_eve_change": worst_eve["eve_impact"]["change"] if worst_eve else None
        }
    else:
        summary = None

    return {"results": results, "summary": summary}


@router.get("/hedge-positions")
async def get_hedge_positions(
    instrument_type: Optional[str] = None,
    status: Optional[str] = Query("ACTIVE"),
    db: Session = Depends(get_db)
):
    """현재 헷지 포지션"""
    query = """
        SELECT position_id, position_date, instrument_type, notional_amount,
               pay_leg, receive_leg, fixed_rate, floating_index, spread,
               maturity_date, mtm_value, delta, dv01, hedge_effectiveness, status
        FROM hedge_position
        WHERE 1=1
    """
    params = {}

    if instrument_type:
        query += " AND instrument_type = :instrument_type"
        params["instrument_type"] = instrument_type
    if status:
        query += " AND status = :status"
        params["status"] = status

    query += " ORDER BY maturity_date"

    result = db.execute(text(query), params)

    positions = []
    total_notional = 0
    total_mtm = 0
    total_dv01 = 0

    for row in result:
        total_notional += row[3] or 0
        total_mtm += row[10] or 0
        total_dv01 += row[12] or 0

        positions.append({
            "position_id": row[0],
            "position_date": row[1],
            "instrument_type": row[2],
            "notional_amount": row[3],
            "pay_leg": row[4],
            "receive_leg": row[5],
            "fixed_rate": row[6],
            "floating_index": row[7],
            "spread": row[8],
            "maturity_date": row[9],
            "mtm_value": row[10],
            "delta": row[11],
            "dv01": row[12],
            "hedge_effectiveness": row[13],
            "status": row[14]
        })

    # 상품별 요약
    by_instrument = db.execute(text("""
        SELECT instrument_type, COUNT(*) as count,
               SUM(notional_amount) as total_notional, SUM(mtm_value) as total_mtm
        FROM hedge_position
        WHERE status = 'ACTIVE'
        GROUP BY instrument_type
    """))

    instrument_summary = []
    for row in by_instrument:
        instrument_summary.append({
            "instrument_type": row[0],
            "count": row[1],
            "total_notional": row[2],
            "total_mtm": row[3]
        })

    return {
        "positions": positions,
        "summary": {
            "total_notional": total_notional,
            "total_mtm": total_mtm,
            "total_dv01": total_dv01,
            "position_count": len(positions)
        },
        "by_instrument": instrument_summary
    }


@router.get("/hedge-recommendations")
async def get_hedge_recommendations(
    status: Optional[str] = Query("PENDING"),
    db: Session = Depends(get_db)
):
    """헷지 제안"""
    query = """
        SELECT recommendation_id, recommendation_date, gap_bucket,
               current_gap, target_gap, recommended_instrument,
               recommended_notional, expected_cost, expected_benefit,
               priority, rationale, status
        FROM hedge_recommendation
    """
    params = {}

    if status:
        query += " WHERE status = :status"
        params["status"] = status

    query += " ORDER BY priority ASC"

    result = db.execute(text(query), params)

    recommendations = []
    for row in result:
        recommendations.append({
            "recommendation_id": row[0],
            "recommendation_date": row[1],
            "gap_bucket": row[2],
            "current_gap": row[3],
            "target_gap": row[4],
            "recommended_instrument": row[5],
            "recommended_notional": row[6],
            "expected_cost": row[7],
            "expected_benefit": row[8],
            "net_benefit": (row[8] or 0) - (row[7] or 0),
            "priority": row[9],
            "rationale": row[10],
            "status": row[11]
        })

    return {"recommendations": recommendations, "total": len(recommendations)}


@router.get("/dashboard")
async def get_alm_dashboard(db: Session = Depends(get_db)):
    """ALM 대시보드"""
    # 갭 요약
    gap_summary = db.execute(text("""
        SELECT SUM(repricing_gap) as total_gap,
               SUM(nim_sensitivity_100bp) as total_nim_sens,
               SUM(eve_sensitivity_100bp) as total_eve_sens
        FROM interest_rate_gap
    """)).fetchone()

    # 헷지 포지션 요약
    hedge_summary = db.execute(text("""
        SELECT COUNT(*) as position_count,
               SUM(notional_amount) as total_notional,
               SUM(mtm_value) as total_mtm,
               AVG(hedge_effectiveness) as avg_effectiveness
        FROM hedge_position
        WHERE status = 'ACTIVE'
    """)).fetchone()

    # 최악 시나리오
    worst_scenario = db.execute(text("""
        SELECT irs.scenario_name, asr.nim_change, asr.eve_change_pct
        FROM alm_scenario_result asr
        JOIN interest_rate_scenario irs ON asr.scenario_id = irs.scenario_id
        ORDER BY asr.eve_change ASC
        LIMIT 1
    """)).fetchone()

    # 보류 중인 헷지 제안
    pending_recommendations = db.execute(text("""
        SELECT COUNT(*), SUM(recommended_notional)
        FROM hedge_recommendation
        WHERE status = 'PENDING'
    """)).fetchone()

    return {
        "gap_summary": {
            "total_repricing_gap": gap_summary[0],
            "nim_sensitivity_100bp": round(gap_summary[1], 2) if gap_summary[1] else 0,
            "eve_sensitivity_100bp": round(gap_summary[2], 2) if gap_summary[2] else 0,
            "risk_assessment": "금리 상승 시 유리" if (gap_summary[0] or 0) > 0 else "금리 하락 시 유리"
        },
        "hedge_positions": {
            "active_count": hedge_summary[0],
            "total_notional": hedge_summary[1],
            "total_mtm": hedge_summary[2],
            "avg_effectiveness": round(hedge_summary[3], 2) if hedge_summary[3] else 0
        },
        "worst_scenario": {
            "scenario_name": worst_scenario[0] if worst_scenario else None,
            "nim_change": worst_scenario[1] if worst_scenario else None,
            "eve_change_pct": worst_scenario[2] if worst_scenario else None
        },
        "pending_recommendations": {
            "count": pending_recommendations[0],
            "total_notional": pending_recommendations[1]
        }
    }
