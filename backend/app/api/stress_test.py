"""
스트레스 테스트 API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from ..core.database import get_db
from ..services.calculations import calculate_stress_pd, calculate_stress_lgd

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

    # DB는 원 단위, 비율은 소수(0.1663)로 저장
    total_capital = float(capital[0])
    base_rwa = float(capital[3])
    base_bis = float(capital[4]) * 100   # 소수 → %
    base_tier1 = float(capital[5]) * 100  # 소수 → %

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

    # 스트레스 적용 - 상한은 calculations 모듈 단일 정의를 따른다
    stressed_pd = calculate_stress_pd(base_pd, factors['pd'])
    stressed_lgd = calculate_stress_lgd(base_lgd, factors['lgd'])
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
        ind_stressed_pd = calculate_stress_pd(ind_pd, factors['pd'], sensitivity)
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

    # stressed_bis는 이미 소수로 계산되었으므로 % 변환 필요
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
            "base_bis_ratio": base_bis,
            "stressed_bis_ratio": stressed_bis * 100,
            "capital_ratio_impact": stressed_bis * 100 - base_bis,
            "base_tier1_ratio": base_tier1,
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

    # DB는 원 단위
    total_capital = float(capital[0]) if capital else 7982000000000
    base_rwa = float(capital[1]) if capital else 48000000000000

    stress_factors = {
        'BASELINE': 1.0, 'MILD': 1.1, 'MODERATE': 1.25, 'SEVERE': 1.4, 'EXTREME': 1.6
    }

    results = []
    for s in scenarios:
        factor = stress_factors.get(s[2], 1.25)
        stressed_rwa = base_rwa * factor
        stressed_bis = total_capital / stressed_rwa  # 소수 결과 (예: 0.145)

        results.append({
            "scenario_id": s[0],
            "scenario_name": s[1],
            "severity": s[2],
            "stressed_rwa": stressed_rwa,
            "stressed_bis_ratio": stressed_bis * 100,  # % 변환
            "meets_minimum": stressed_bis >= 0.105
        })

    return results

@router.get("/stress-capital-buffer")
def get_stress_capital_buffer(db: Session = Depends(get_db)):
    """스트레스완충자본(SCB) 산출 - 스트레스테스트 결과를 자본 요구량으로 연결.

    도입 취지: 위기상황분석 결과 자본비율 하락폭이 큰 은행일수록 평시에
    완충자본을 더 쌓게 한다. 산식(PoC): SCB = min(max(기준 BIS - SEVERE
    시나리오 BIS, 0), 2.5%p). 최종 요구 비율 = 규제최소 10.5% + SCB.
    종전에는 스트레스테스트가 분석 화면에 머물고 자본 요구량으로 이어지지
    않았다.
    """
    cap = db.execute(text("""
        SELECT bis_ratio FROM capital_position ORDER BY base_date DESC LIMIT 1
    """)).fetchone()
    base_bis = round(float(cap[0]) * 100, 2) if cap else 0

    # SEVERE 시나리오 재현 (comparison 과 동일 로직 축약)
    factors = {"pd": 2.5, "lgd": 1.5, "rwa": 1.35}
    capital = db.execute(text("""
        SELECT total_capital, total_rwa FROM capital_position
        ORDER BY base_date DESC LIMIT 1
    """)).fetchone()
    total_capital, base_rwa = float(capital[0]), float(capital[1])
    stressed_bis = round(total_capital / (base_rwa * factors["rwa"]) * 100, 2)

    drop = max(base_bis - stressed_bis, 0)
    scb = round(min(drop, 2.5), 2)
    required = round(10.5 + scb, 2)

    return {
        "base_bis": base_bis,
        "severe_stressed_bis": stressed_bis,
        "bis_drop": round(drop, 2),
        "scb": scb,
        "scb_cap": 2.5,
        "regulatory_minimum": 10.5,
        "required_ratio": required,
        "headroom": round(base_bis - required, 2),
        "meets_requirement": base_bis >= required,
        "note": "SCB = min(max(기준 BIS − SEVERE 스트레스 BIS, 0), 2.5%p) - PoC 산식",
    }

@router.get("/custom")
def run_custom_scenario(
    pd_mult: float = 1.0,        # PD 배수 (1.0~4.0)
    lgd_mult: float = 1.0,       # LGD 배수 (1.0~2.0)
    property_shock: float = 0.0, # 부동산 가격 충격 (%) - 음수
    rate_bp: int = 0,            # 금리 충격 (bp)
    db: Session = Depends(get_db),
):
    """사용자 정의 시나리오 플레이그라운드.

    고정 5개 시나리오와 달리 충격을 직접 조립한다. 계산은 기존 엔진을 재사용:
      · RWA/BIS  : 스트레스 RWA 계수(1 + (pd_mult-1)*0.45)
      · ECL      : PD·LGD 배수에 선형 (Stage 구성 불변 가정)
      · PF       : 부동산 충격이 분양률에 전이 → 괴리 경보 재산출,
                   자기자본비율 하락(가격하락의 절반이 자본 잠식 가정)
      · 이자부담 : 금리 충격 → 평균 이자보상배율 근사 (EBITDA 불변, 이자비용 증가)
    """
    pd_mult = max(0.5, min(pd_mult, 4.0))
    lgd_mult = max(0.5, min(lgd_mult, 2.0))
    property_shock = max(-40.0, min(property_shock, 0.0))
    rate_bp = max(0, min(rate_bp, 400))

    # 자본
    cap = db.execute(text("""
        SELECT total_capital, total_rwa, bis_ratio FROM capital_position
        ORDER BY base_date DESC LIMIT 1
    """)).fetchone()
    total_capital, base_rwa = float(cap[0]), float(cap[1])
    base_bis = round(float(cap[2]) * 100, 2)
    rwa_factor = 1 + (pd_mult - 1) * 0.45
    stressed_bis = round(total_capital / (base_rwa * rwa_factor) * 100, 2)

    # ECL
    base_ecl = float(db.execute(text("""
        SELECT COALESCE(SUM(e.ecl_final), 0) FROM ecl_calculation e
        JOIN (SELECT facility_id, MAX(calc_date) latest
              FROM ecl_calculation GROUP BY facility_id) mx
          ON e.facility_id = mx.facility_id AND e.calc_date = mx.latest
    """)).fetchone()[0])
    stressed_ecl = round(base_ecl * pd_mult * lgd_mult, 2)

    # PF - 부동산 충격 전이
    pf_rows = db.execute(text("""
        SELECT project_type, progress_rate, presale_rate, equity_ratio, exposure
        FROM pf_project WHERE status != 'COMPLETED'
    """)).fetchall()
    base_watch = sum(
        1 for t, pr, ps, eq, _ in pf_rows
        if (t == 'MAIN' and (pr or 0) - (ps or 0) >= 30) or eq < 5)
    stressed_watch = 0
    stressed_low_equity_exp = 0.0
    pf_total = sum(r[4] for r in pf_rows) or 1
    for t, pr, ps, eq, exp in pf_rows:
        # 가격 하락 → 분양률 비례 하락, 자기자본은 하락분의 절반 잠식
        ps2 = max(0.0, (ps or 0) * (1 + property_shock / 100))
        eq2 = max(0.0, eq + property_shock * 0.5)
        if (t == 'MAIN' and (pr or 0) - ps2 >= 30) or eq2 < 5:
            stressed_watch += 1
        if eq2 < 10:
            stressed_low_equity_exp += exp

    # 이자보상배율 근사 - 재무제표 집계
    fin = db.execute(text("""
        SELECT SUM(operating_profit), SUM(interest_expense)
        FROM financial_statement WHERE fiscal_year = (
            SELECT MAX(fiscal_year) FROM financial_statement)
    """)).fetchone()
    op, ie = float(fin[0] or 0), float(fin[1] or 1)
    borrow = float(db.execute(text(
        "SELECT COALESCE(SUM(total_borrowing),0) FROM financial_statement "
        "WHERE fiscal_year = (SELECT MAX(fiscal_year) FROM financial_statement)"
    )).fetchone()[0])
    ie_stressed = ie + borrow * rate_bp / 10000
    icr_base = round(op / ie, 2) if ie else 0
    icr_stressed = round(op / ie_stressed, 2) if ie_stressed else 0

    return {
        "inputs": {"pd_mult": pd_mult, "lgd_mult": lgd_mult,
                   "property_shock": property_shock, "rate_bp": rate_bp},
        "bis": {"base": base_bis, "stressed": stressed_bis,
                "delta": round(stressed_bis - base_bis, 2),
                "breach": stressed_bis < 10.5},
        "ecl": {"base": round(base_ecl, 2), "stressed": stressed_ecl,
                "delta": round(stressed_ecl - base_ecl, 2)},
        "pf": {"base_watchlist": base_watch, "stressed_watchlist": stressed_watch,
               "low_equity_share": round(stressed_low_equity_exp / pf_total * 100, 1)},
        "icr": {"base": icr_base, "stressed": icr_stressed},
        "note": "PoC 근사 산식 - 각 전이 계수는 화면에 명시된 가정을 따른다",
    }
