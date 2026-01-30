"""
스트레스 테스트 API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from ..core.database import get_db
from ..services.calculations import calculate_stress_pd

router = APIRouter(prefix="/api/stress-test", tags=["Stress Test"])


@router.get("/scenarios")
def get_scenarios(db: Session = Depends(get_db)):
    """스트레스 시나리오 목록"""
    results = db.execute(text("""
        SELECT scenario_id, scenario_name, scenario_type, severity_level,
               gdp_growth_shock, unemployment_shock, interest_rate_shock,
               housing_price_shock, stock_price_shock, fx_rate_shock, description
        FROM stress_scenario
        ORDER BY
            CASE severity_level
                WHEN 'BASELINE' THEN 1
                WHEN 'MILD' THEN 2
                WHEN 'MODERATE' THEN 3
                WHEN 'SEVERE' THEN 4
                WHEN 'EXTREME' THEN 5
            END
    """)).fetchall()

    # 충격 계수 매핑
    stress_factors = {
        'BASELINE': {'pd': 1.0, 'lgd': 1.0, 'rwa': 1.0},
        'MILD': {'pd': 1.3, 'lgd': 1.1, 'rwa': 1.1},
        'MODERATE': {'pd': 1.8, 'lgd': 1.3, 'rwa': 1.25},
        'SEVERE': {'pd': 2.5, 'lgd': 1.5, 'rwa': 1.4},
        'EXTREME': {'pd': 3.5, 'lgd': 1.8, 'rwa': 1.6}
    }

    return [
        {
            "scenario_id": r[0],
            "scenario_name": r[1],
            "scenario_type": r[2],
            "severity": r[3],
            "pd_stress_factor": stress_factors.get(r[3], stress_factors['MODERATE'])['pd'],
            "lgd_stress_factor": stress_factors.get(r[3], stress_factors['MODERATE'])['lgd'],
            "rwa_stress_factor": stress_factors.get(r[3], stress_factors['MODERATE'])['rwa'],
            "description": r[10],
            "macro_assumptions": {
                "GDP성장률": f"{r[4] or 0:+.1f}%p",
                "실업률": f"{r[5] or 0:+.1f}%p",
                "금리": f"{r[6] or 0:+.1f}%p",
                "주택가격": f"{r[7] or 0:+.0f}%",
                "주가": f"{r[8] or 0:+.0f}%"
            }
        }
        for r in results
    ]


@router.get("/results/{scenario_id}")
def get_scenario_result(scenario_id: str, db: Session = Depends(get_db)):
    """특정 시나리오 상세 결과"""

    # 시나리오 정보
    scenario = db.execute(text("""
        SELECT scenario_id, scenario_name, severity_level, description
        FROM stress_scenario WHERE scenario_id = :sid
    """), {"sid": scenario_id}).fetchone()

    if not scenario:
        return {"error": "Scenario not found"}

    # 충격 계수
    stress_factors = {
        'BASELINE': {'pd': 1.0, 'lgd': 1.0, 'rwa': 1.0},
        'MILD': {'pd': 1.3, 'lgd': 1.1, 'rwa': 1.1},
        'MODERATE': {'pd': 1.8, 'lgd': 1.3, 'rwa': 1.25},
        'SEVERE': {'pd': 2.5, 'lgd': 1.5, 'rwa': 1.4},
        'EXTREME': {'pd': 3.5, 'lgd': 1.8, 'rwa': 1.6}
    }
    factors = stress_factors.get(scenario[2], stress_factors['MODERATE'])

    # 현재 자본 포지션
    capital = db.execute(text("""
        SELECT total_capital, cet1_capital, cet1_capital + at1_capital as tier1_capital, total_rwa, bis_ratio, tier1_ratio
        FROM capital_position ORDER BY base_date DESC LIMIT 1
    """)).fetchone()

    if not capital:
        return {"error": "No capital data"}

    total_capital = float(capital[0])
    base_rwa = float(capital[3])
    base_bis = float(capital[4])
    base_tier1 = float(capital[5])

    # 포트폴리오 집계
    portfolio = db.execute(text("""
        SELECT SUM(f.approved_amount), AVG(rp.ttc_pd), AVG(rp.lgd), SUM(rp.rwa)
        FROM facility f
        LEFT JOIN risk_parameter rp ON f.application_id = rp.application_id
        WHERE f.status = 'ACTIVE'
    """)).fetchone()

    total_exposure = float(portfolio[0]) if portfolio[0] else 5000000000000
    base_pd = float(portfolio[1]) if portfolio[1] else 0.02
    base_lgd = float(portfolio[2]) if portfolio[2] else 0.40
    portfolio_rwa = float(portfolio[3]) if portfolio[3] else base_rwa * 0.8

    # 스트레스 적용
    stressed_pd = min(base_pd * factors['pd'], 0.30)
    stressed_lgd = min(base_lgd * factors['lgd'], 0.70)
    stressed_rwa = base_rwa * factors['rwa']

    base_el = base_pd * base_lgd * total_exposure
    stressed_el = stressed_pd * stressed_lgd * total_exposure

    rwa_increase = stressed_rwa - base_rwa
    el_increase = stressed_el - base_el

    stressed_bis = total_capital / stressed_rwa
    stressed_tier1 = float(capital[2]) / stressed_rwa if capital[2] else stressed_bis * 0.85

    # 산업별 영향 계산
    industries = db.execute(text("""
        SELECT c.industry_code, c.industry_name,
               SUM(f.approved_amount) as exposure,
               AVG(rp.ttc_pd) as avg_pd,
               SUM(rp.rwa) as total_rwa
        FROM facility f
        JOIN customer c ON f.customer_id = c.customer_id
        LEFT JOIN risk_parameter rp ON f.application_id = rp.application_id
        WHERE f.status = 'ACTIVE'
        GROUP BY c.industry_code, c.industry_name
        ORDER BY total_rwa DESC
    """)).fetchall()

    # 산업별 민감도
    industry_sensitivity = {
        'IND001': 0.8, 'IND002': 0.8, 'IND003': 1.0, 'IND004': 1.0,
        'IND005': 1.0, 'IND006': 0.9, 'IND007': 1.1, 'IND008': 1.5,
        'IND009': 1.8, 'IND010': 1.0
    }

    industry_results = []
    for ind in industries:
        ind_code = ind[0]
        ind_name = ind[1]
        ind_exposure = float(ind[2]) if ind[2] else 0
        ind_pd = float(ind[3]) if ind[3] else base_pd
        ind_rwa = float(ind[4]) if ind[4] else ind_exposure * 0.5

        sensitivity = industry_sensitivity.get(ind_code, 1.0)
        ind_stressed_pd = min(ind_pd * factors['pd'] * sensitivity, 0.30)
        ind_stressed_rwa = ind_rwa * (1 + (factors['rwa'] - 1) * sensitivity)
        rwa_increase_rate = ((ind_stressed_rwa / ind_rwa) - 1) * 100 if ind_rwa > 0 else 0

        industry_results.append({
            "industry_code": ind_code,
            "industry_name": ind_name,
            "exposure": ind_exposure,
            "base_pd": ind_pd,
            "stressed_pd": ind_stressed_pd,
            "pd_stress_impact": ind_stressed_pd - ind_pd,
            "base_rwa": ind_rwa,
            "stressed_rwa": ind_stressed_rwa,
            "rwa_increase_rate": rwa_increase_rate,
            "sensitivity": sensitivity
        })

    return {
        "scenario": {
            "scenario_id": scenario[0],
            "scenario_name": scenario[1],
            "severity": scenario[2],
            "description": scenario[3]
        },
        "summary": {
            "base_rwa": base_rwa,
            "stressed_rwa": stressed_rwa,
            "rwa_increase": rwa_increase,
            "rwa_increase_rate": ((stressed_rwa / base_rwa) - 1) * 100 if base_rwa > 0 else 0,
            "base_el": base_el,
            "stressed_el": stressed_el,
            "el_increase": el_increase,
            "base_bis_ratio": base_bis * 100,
            "stressed_bis_ratio": stressed_bis * 100,
            "capital_ratio_impact": (stressed_bis - base_bis) * 100,
            "base_tier1_ratio": base_tier1 * 100,
            "stressed_tier1_ratio": stressed_tier1 * 100
        },
        "by_industry": sorted(industry_results, key=lambda x: x['rwa_increase_rate'], reverse=True)
    }


@router.post("/run")
def run_stress_test(
    scenario_id: str,
    custom_factor: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """스트레스 테스트 실행 (시뮬레이션)"""
    # /results/{scenario_id}와 동일한 로직 사용
    return get_scenario_result(scenario_id, db)


@router.get("/comparison")
def compare_scenarios(db: Session = Depends(get_db)):
    """시나리오간 비교"""

    scenarios = db.execute(text("""
        SELECT scenario_id, scenario_name, severity_level
        FROM stress_scenario
        ORDER BY
            CASE severity_level
                WHEN 'BASELINE' THEN 1
                WHEN 'MILD' THEN 2
                WHEN 'MODERATE' THEN 3
                WHEN 'SEVERE' THEN 4
                WHEN 'EXTREME' THEN 5
            END
    """)).fetchall()

    # 현재 자본 포지션
    capital = db.execute(text("""
        SELECT total_capital, total_rwa FROM capital_position
        ORDER BY base_date DESC LIMIT 1
    """)).fetchone()

    total_capital = float(capital[0]) if capital else 2500000000000
    base_rwa = float(capital[1]) if capital else 16500000000000

    stress_factors = {
        'BASELINE': 1.0, 'MILD': 1.1, 'MODERATE': 1.25, 'SEVERE': 1.4, 'EXTREME': 1.6
    }

    results = []
    for s in scenarios:
        factor = stress_factors.get(s[2], 1.25)
        stressed_rwa = base_rwa * factor
        stressed_bis = total_capital / stressed_rwa

        results.append({
            "scenario_id": s[0],
            "scenario_name": s[1],
            "severity": s[2],
            "stressed_rwa": stressed_rwa,
            "stressed_bis_ratio": stressed_bis * 100,
            "meets_minimum": stressed_bis >= 0.105
        })

    return results
