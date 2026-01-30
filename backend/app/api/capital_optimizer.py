"""
자본활용성 최적화 API
- RWA 최적화 엔진
- 자본배분 최적화
- 동적 가격제안
- 포트폴리오 리밸런싱 제안
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..core.database import get_db
from typing import List, Optional
import math

router = APIRouter(prefix="/api/capital-optimizer", tags=["Capital Optimizer"])


# ===== 1. RWA 최적화 분석 =====
@router.get("/rwa-optimization")
def get_rwa_optimization_analysis(db: Session = Depends(get_db)):
    """
    RWA 최적화 기회 분석
    - RWA 밀도가 높은 세그먼트 식별
    - 담보 활용 최적화 기회
    - 등급 개선 대상 식별
    """

    # 1. 산업별 RWA 밀도 분석
    industry_density = db.execute(text("""
        SELECT segment_name, segment_code, total_exposure, total_rwa,
               ROUND(total_rwa * 100.0 / NULLIF(total_exposure, 0), 2) as rwa_density,
               raroc
        FROM portfolio_summary
        WHERE segment_type = 'INDUSTRY'
        ORDER BY total_rwa * 100.0 / NULLIF(total_exposure, 0) DESC
    """)).fetchall()

    # 2. 등급별 RWA 밀도 분석
    rating_density = db.execute(text("""
        SELECT segment_name, segment_code, total_exposure, total_rwa,
               ROUND(total_rwa * 100.0 / NULLIF(total_exposure, 0), 2) as rwa_density,
               avg_pd, avg_lgd
        FROM portfolio_summary
        WHERE segment_type = 'RATING'
        ORDER BY segment_code
    """)).fetchall()

    # 3. 담보 미활용 여신 (높은 LGD)
    high_lgd_exposures = db.execute(text("""
        SELECT la.application_id, c.customer_name, c.industry_name,
               la.requested_amount, COALESCE(rp.pit_pd, rp.ttc_pd) as pd, rp.lgd, rp.rwa,
               cr.final_grade
        FROM loan_application la
        JOIN customer c ON la.customer_id = c.customer_id
        JOIN risk_parameter rp ON la.application_id = rp.application_id
        LEFT JOIN credit_rating_result cr ON la.application_id = cr.application_id
        WHERE rp.lgd > 0.45 AND la.status = 'APPROVED'
        ORDER BY rp.lgd DESC, la.requested_amount DESC
        LIMIT 20
    """)).fetchall()

    # 4. 등급 업그레이드 잠재 고객 (BBB급 중 재무개선 가능성)
    upgrade_candidates = db.execute(text("""
        SELECT c.customer_id, c.customer_name, c.industry_name,
               cr.final_grade, cr.pd_value,
               SUM(f.outstanding_amount) as total_exposure,
               c.asset_size, c.revenue_size
        FROM customer c
        JOIN credit_rating_result cr ON c.customer_id = cr.customer_id
        LEFT JOIN facility f ON c.customer_id = f.customer_id AND f.status = 'ACTIVE'
        WHERE cr.final_grade IN ('BBB+', 'BBB', 'BBB-')
        AND cr.rating_date = (SELECT MAX(rating_date) FROM credit_rating_result WHERE customer_id = c.customer_id)
        AND c.asset_size > 100000000000  -- 1000억 이상
        GROUP BY c.customer_id
        HAVING SUM(f.outstanding_amount) > 10000000000  -- 100억 이상 익스포저
        ORDER BY SUM(f.outstanding_amount) DESC
        LIMIT 15
    """)).fetchall()

    # 5. RWA 절감 기회 계산
    total_rwa = sum(r[3] for r in industry_density if r[3])
    high_density_rwa = sum(r[3] for r in industry_density if r[4] and r[4] > 60)  # 60% 이상

    # 담보 추가시 LGD 35%로 가정한 RWA 절감 잠재액
    potential_lgd_reduction = sum(
        (r[5] - 0.35) / r[5] * r[6] if r[5] and r[6] and r[5] > 0.35 else 0
        for r in high_lgd_exposures
    )

    # 등급 1단계 개선시 RWA 절감 (PD 30% 감소 가정)
    potential_upgrade_benefit = sum(
        r[5] * 0.15 if r[5] else 0  # 익스포저의 15% RWA 절감 가정
        for r in upgrade_candidates
    )

    return {
        "summary": {
            "total_portfolio_rwa": total_rwa,
            "high_density_segment_rwa": high_density_rwa,
            "high_density_ratio": round(high_density_rwa * 100 / total_rwa, 1) if total_rwa else 0,
            "potential_rwa_reduction": {
                "collateral_optimization": potential_lgd_reduction,
                "rating_upgrade": potential_upgrade_benefit,
                "total_opportunity": potential_lgd_reduction + potential_upgrade_benefit
            }
        },
        "industry_analysis": [
            {
                "industry": r[0],
                "industry_code": r[1],
                "exposure": r[2],
                "rwa": r[3],
                "rwa_density": r[4],
                "raroc": round(r[5] * 100, 2) if r[5] else 0,
                "optimization_priority": "HIGH" if r[4] and r[4] > 65 else "MEDIUM" if r[4] and r[4] > 50 else "LOW"
            }
            for r in industry_density
        ],
        "rating_analysis": [
            {
                "rating_bucket": r[0],
                "exposure": r[2],
                "rwa": r[3],
                "rwa_density": r[4],
                "avg_pd": round(r[5] * 100, 3) if r[5] else 0,
                "avg_lgd": round(r[6] * 100, 1) if r[6] else 0
            }
            for r in rating_density
        ],
        "collateral_opportunities": [
            {
                "application_id": r[0],
                "customer_name": r[1],
                "industry": r[2],
                "exposure": r[3],
                "current_lgd": round(r[5] * 100, 1) if r[5] else 0,
                "current_rwa": r[6],
                "potential_rwa_if_collateralized": round(r[6] * 0.35 / r[5], 0) if r[5] and r[5] > 0 else 0,
                "rwa_savings": round(r[6] * (1 - 0.35 / r[5]), 0) if r[5] and r[5] > 0.35 else 0,
                "grade": r[7]
            }
            for r in high_lgd_exposures[:10]
        ],
        "upgrade_candidates": [
            {
                "customer_id": r[0],
                "customer_name": r[1],
                "industry": r[2],
                "current_grade": r[3],
                "current_pd": round(r[4] * 100, 3) if r[4] else 0,
                "total_exposure": r[5],
                "asset_size": r[6],
                "revenue_size": r[7],
                "recommendation": "재무개선 모니터링 대상"
            }
            for r in upgrade_candidates
        ]
    }


# ===== 2. 자본배분 최적화 =====
@router.get("/allocation-optimizer")
def get_allocation_optimization(db: Session = Depends(get_db)):
    """
    자본배분 최적화 분석
    - 세그먼트별 RAROC 대비 자본배분 적정성
    - 자본예산 재배분 제안
    - 효율적 프론티어 분석
    """

    # 현재 자본예산 현황
    budgets = db.execute(text("""
        SELECT segment_name, segment_code, segment_type,
               rwa_budget, rwa_used, raroc_target,
               revenue_target, revenue_actual
        FROM capital_budget
        WHERE status = 'ACTIVE'
        ORDER BY segment_type, rwa_budget DESC
    """)).fetchall()

    # 산업별 실제 RAROC
    industry_raroc = db.execute(text("""
        SELECT segment_name, segment_code, total_exposure, total_rwa, raroc
        FROM portfolio_summary
        WHERE segment_type = 'INDUSTRY'
    """)).fetchall()

    # 허들레이트
    hurdle = db.execute(text("""
        SELECT hurdle_raroc, target_raroc FROM hurdle_rate
        WHERE segment_type IS NULL LIMIT 1
    """)).fetchone()

    hurdle_rate = hurdle[0] if hurdle else 0.12
    target_rate = hurdle[1] if hurdle else 0.15

    # 자본배분 효율성 계산
    allocation_efficiency = []
    total_rwa_budget = sum(b[3] for b in budgets if b[3])
    total_rwa_used = sum(b[4] for b in budgets if b[4])

    # 산업별 RAROC 매핑
    raroc_map = {r[1]: r[4] for r in industry_raroc}

    for b in budgets:
        if b[2] == 'INDUSTRY':
            actual_raroc = raroc_map.get(b[1], 0) or 0
            budget_utilization = (b[4] / b[3] * 100) if b[3] and b[3] > 0 else 0

            # 효율성 점수: RAROC / 허들레이트 * 예산활용률
            efficiency_score = (actual_raroc / hurdle_rate * budget_utilization / 100) if hurdle_rate > 0 else 0

            # 배분 제안
            if actual_raroc > target_rate and budget_utilization > 80:
                recommendation = "EXPAND"
                reason = "고수익 & 고활용 - 추가 배분 권장"
            elif actual_raroc > target_rate and budget_utilization < 60:
                recommendation = "PROMOTE"
                reason = "고수익 & 저활용 - 영업 강화 필요"
            elif actual_raroc < hurdle_rate and budget_utilization > 80:
                recommendation = "REDUCE"
                reason = "저수익 & 고활용 - 배분 축소 검토"
            elif actual_raroc < hurdle_rate:
                recommendation = "RESTRUCTURE"
                reason = "저수익 - 포트폴리오 재조정 필요"
            else:
                recommendation = "MAINTAIN"
                reason = "적정 수준 유지"

            allocation_efficiency.append({
                "segment": b[0],
                "segment_code": b[1],
                "rwa_budget": b[3],
                "rwa_used": b[4],
                "utilization_rate": round(budget_utilization, 1),
                "raroc_target": round(b[5] * 100, 1) if b[5] else 0,
                "raroc_actual": round(actual_raroc * 100, 2) if actual_raroc else 0,
                "efficiency_score": round(efficiency_score, 2),
                "recommendation": recommendation,
                "reason": reason
            })

    # 재배분 시뮬레이션
    reallocation_suggestions = []
    expand_candidates = [a for a in allocation_efficiency if a["recommendation"] == "EXPAND"]
    reduce_candidates = [a for a in allocation_efficiency if a["recommendation"] in ["REDUCE", "RESTRUCTURE"]]

    # 축소 대상에서 확대 대상으로 재배분
    for reduce in reduce_candidates:
        excess_rwa = reduce["rwa_used"] * 0.2  # 20% 축소
        for expand in expand_candidates:
            if excess_rwa > 0:
                reallocation_suggestions.append({
                    "from_segment": reduce["segment"],
                    "to_segment": expand["segment"],
                    "rwa_amount": excess_rwa,
                    "expected_raroc_gain": round((expand["raroc_actual"] - reduce["raroc_actual"]), 2),
                    "reason": f"{reduce['segment']} RAROC {reduce['raroc_actual']:.1f}% → {expand['segment']} RAROC {expand['raroc_actual']:.1f}%"
                })
                excess_rwa = 0

    return {
        "summary": {
            "total_rwa_budget": total_rwa_budget,
            "total_rwa_used": total_rwa_used,
            "overall_utilization": round(total_rwa_used * 100 / total_rwa_budget, 1) if total_rwa_budget else 0,
            "hurdle_rate": round(hurdle_rate * 100, 1),
            "target_rate": round(target_rate * 100, 1),
            "expand_candidates": len(expand_candidates),
            "reduce_candidates": len(reduce_candidates)
        },
        "allocation_analysis": sorted(allocation_efficiency, key=lambda x: x["efficiency_score"], reverse=True),
        "reallocation_suggestions": reallocation_suggestions,
        "efficient_frontier": {
            "current_portfolio_raroc": round(sum(a["raroc_actual"] * a["rwa_used"] for a in allocation_efficiency) / total_rwa_used, 2) if total_rwa_used else 0,
            "optimal_portfolio_raroc": round(sum(a["raroc_actual"] * a["rwa_used"] for a in allocation_efficiency if a["recommendation"] != "REDUCE") / sum(a["rwa_used"] for a in allocation_efficiency if a["recommendation"] != "REDUCE"), 2) if any(a["recommendation"] != "REDUCE" for a in allocation_efficiency) else 0
        }
    }


# ===== 3. 동적 가격제안 =====
@router.get("/pricing-suggestion/{application_id}")
def get_dynamic_pricing_suggestion(
    application_id: str,
    target_raroc: Optional[float] = Query(None, description="목표 RAROC (%)"),
    db: Session = Depends(get_db)
):
    """
    신규 여신에 대한 동적 가격 제안
    - 목표 RAROC 달성을 위한 최소 금리 계산
    - 경쟁력 있는 금리 범위 제시
    - 조건별 시나리오 분석
    """

    # 신청 정보 조회
    app_info = db.execute(text("""
        SELECT la.application_id, la.requested_amount, la.requested_tenor, la.requested_rate,
               c.customer_name, c.industry_code, c.industry_name, c.size_category,
               COALESCE(rp.pit_pd, rp.ttc_pd) as pd, rp.lgd, rp.ead, rp.rwa,
               cr.final_grade
        FROM loan_application la
        JOIN customer c ON la.customer_id = c.customer_id
        LEFT JOIN risk_parameter rp ON la.application_id = rp.application_id
        LEFT JOIN credit_rating_result cr ON la.application_id = cr.application_id
        WHERE la.application_id = :app_id
    """), {"app_id": application_id}).fetchone()

    if not app_info:
        return {"error": "Application not found"}

    # 기존 pricing 조회
    existing_pricing = db.execute(text("""
        SELECT base_rate, ftp_spread, credit_spread, opex_spread, target_margin,
               strategy_adj, collateral_adj, system_rate, final_rate,
               expected_raroc, hurdle_rate, raroc_status
        FROM pricing_result
        WHERE application_id = :app_id
        ORDER BY pricing_version DESC LIMIT 1
    """), {"app_id": application_id}).fetchone()

    # 허들레이트
    hurdle = db.execute(text("""
        SELECT hurdle_raroc, target_raroc FROM hurdle_rate
        WHERE (segment_type = 'SIZE' AND segment_code = :size) OR segment_type IS NULL
        ORDER BY segment_type DESC LIMIT 1
    """), {"size": app_info[7]}).fetchone()

    hurdle_rate = hurdle[0] if hurdle else 0.12
    default_target = hurdle[1] if hurdle else 0.15

    # 전략 조정값 조회
    strategy = db.execute(text("""
        SELECT strategy_code, pricing_adj_bp
        FROM industry_rating_strategy
        WHERE industry_code = :ind_code AND rating_bucket = :rating_bucket
        LIMIT 1
    """), {
        "ind_code": app_info[5],
        "rating_bucket": get_rating_bucket(app_info[12]) if app_info[12] else "BBB"
    }).fetchone()

    # 계산용 파라미터
    pd = app_info[8] or 0.02
    lgd = app_info[9] or 0.45
    ead = app_info[10] or app_info[1]
    rwa = app_info[11] or ead * 0.5
    tenor = app_info[2] or 12

    # 기본 금리 구성요소
    base_rate = 0.035  # 정책금리 3.5%
    ftp_spread = 0.008  # FTP 0.8%
    opex_spread = 0.002  # 운영비 0.2%

    # EL 스프레드 = PD * LGD (연환산)
    el_spread = pd * lgd

    # UL 스프레드 계산 (자본비용)
    ec = rwa * 0.08  # 경제적 자본 = RWA * 8%
    ul_spread = (ec * (target_raroc or default_target)) / ead if ead > 0 else 0

    # 전략 조정
    strategy_adj = (strategy[1] / 10000) if strategy else 0

    # 최소 필요 금리 (허들레이트 충족)
    min_rate_for_hurdle = base_rate + ftp_spread + el_spread + (ec * hurdle_rate / ead if ead > 0 else 0) + opex_spread

    # 목표 RAROC 달성 금리
    target_raroc_pct = target_raroc / 100 if target_raroc else default_target
    rate_for_target = base_rate + ftp_spread + el_spread + (ec * target_raroc_pct / ead if ead > 0 else 0) + opex_spread

    # 시나리오별 금리-RAROC 분석
    scenarios = []
    for rate_adj in [-0.005, -0.003, 0, 0.003, 0.005, 0.01]:
        test_rate = rate_for_target + rate_adj
        # RAROC 계산: (이자수익 - 조달비용 - 운영비용 - EL) / EC
        interest_income = ead * test_rate
        funding_cost = ead * (base_rate + ftp_spread)
        operating_cost = ead * opex_spread
        expected_loss = ead * el_spread
        net_income = interest_income - funding_cost - operating_cost - expected_loss
        calc_raroc = net_income / ec if ec > 0 else 0

        scenarios.append({
            "rate": round(test_rate * 100, 2),
            "raroc": round(calc_raroc * 100, 2),
            "net_income": round(net_income / 100000000, 2),  # 억원
            "meets_hurdle": calc_raroc >= hurdle_rate,
            "meets_target": calc_raroc >= target_raroc_pct
        })

    # 담보 추가시 시나리오
    collateral_scenarios = []
    for target_lgd in [0.45, 0.35, 0.25, 0.15]:
        # 담보로 LGD 개선시 RWA 변화
        new_rwa = calculate_irb_rwa(pd, target_lgd, ead, tenor / 12)
        new_ec = new_rwa * 0.08
        new_el_spread = pd * target_lgd
        new_min_rate = base_rate + ftp_spread + new_el_spread + (new_ec * hurdle_rate / ead if ead > 0 else 0) + opex_spread

        collateral_scenarios.append({
            "lgd": round(target_lgd * 100, 0),
            "rwa": round(new_rwa / 100000000, 1),  # 억원
            "rwa_change": round((new_rwa - rwa) / 100000000, 1),
            "min_rate_for_hurdle": round(new_min_rate * 100, 2),
            "rate_reduction": round((min_rate_for_hurdle - new_min_rate) * 100, 2)
        })

    return {
        "application_info": {
            "application_id": app_info[0],
            "customer_name": app_info[4],
            "industry": app_info[6],
            "size_category": app_info[7],
            "credit_grade": app_info[12],
            "requested_amount": app_info[1],
            "requested_tenor": app_info[2],
            "requested_rate": round(app_info[3] * 100, 2) if app_info[3] else None
        },
        "risk_parameters": {
            "pd": round(pd * 100, 3),
            "lgd": round(lgd * 100, 1),
            "ead": ead,
            "rwa": rwa,
            "economic_capital": ec
        },
        "pricing_components": {
            "base_rate": round(base_rate * 100, 2),
            "ftp_spread": round(ftp_spread * 100, 2),
            "el_spread": round(el_spread * 100, 3),
            "ul_spread": round(ul_spread * 100, 3),
            "opex_spread": round(opex_spread * 100, 2),
            "strategy_adjustment": round(strategy_adj * 100, 2),
            "strategy_code": strategy[0] if strategy else "MAINTAIN"
        },
        "rate_recommendations": {
            "hurdle_rate": round(hurdle_rate * 100, 1),
            "target_rate": round(default_target * 100, 1),
            "minimum_rate_for_hurdle": round(min_rate_for_hurdle * 100, 2),
            "rate_for_target_raroc": round(rate_for_target * 100, 2),
            "competitive_range": {
                "floor": round((rate_for_target - 0.003) * 100, 2),
                "suggested": round(rate_for_target * 100, 2),
                "ceiling": round((rate_for_target + 0.005) * 100, 2)
            }
        },
        "existing_pricing": {
            "final_rate": round(existing_pricing[8] * 100, 2) if existing_pricing and existing_pricing[8] else None,
            "expected_raroc": round(existing_pricing[9] * 100, 2) if existing_pricing and existing_pricing[9] else None,
            "raroc_status": existing_pricing[11] if existing_pricing else None
        } if existing_pricing else None,
        "rate_raroc_scenarios": scenarios,
        "collateral_impact_scenarios": collateral_scenarios
    }


# ===== 4. 포트폴리오 리밸런싱 제안 =====
@router.get("/rebalancing-suggestions")
def get_rebalancing_suggestions(db: Session = Depends(get_db)):
    """
    포트폴리오 리밸런싱 제안
    - 전략 매트릭스 기반 조정 방향
    - 집중도 리스크 해소 방안
    - 자본효율성 개선 액션플랜
    """

    # 산업별 현황과 전략
    industry_status = db.execute(text("""
        SELECT ps.segment_name, ps.segment_code, ps.total_exposure, ps.total_rwa, ps.raroc,
               irs.strategy_code, irs.pricing_adj_bp,
               ld.limit_amount, le.exposure_amount, le.utilization_rate
        FROM portfolio_summary ps
        LEFT JOIN industry_rating_strategy irs ON ps.segment_code = irs.industry_code AND irs.rating_bucket = 'A'
        LEFT JOIN limit_definition ld ON ld.dimension_type = 'INDUSTRY' AND ld.dimension_code = ps.segment_code
        LEFT JOIN limit_exposure le ON ld.limit_id = le.limit_id
        WHERE ps.segment_type = 'INDUSTRY'
        ORDER BY ps.total_exposure DESC
    """)).fetchall()

    # 집중도 분석
    total_exposure = sum(r[2] for r in industry_status if r[2])
    hhi = sum((r[2] / total_exposure * 100) ** 2 for r in industry_status if r[2] and total_exposure > 0)

    # 리밸런싱 제안 생성
    rebalancing_actions = []

    for ind in industry_status:
        exposure = ind[2] or 0
        rwa = ind[3] or 0
        raroc = ind[4] or 0
        strategy = ind[5] or "MAINTAIN"
        utilization = ind[9] or 0
        concentration = (exposure / total_exposure * 100) if total_exposure > 0 else 0
        rwa_density = (rwa / exposure * 100) if exposure > 0 else 0

        action = {
            "industry": ind[0],
            "industry_code": ind[1],
            "current_exposure": exposure,
            "concentration": round(concentration, 1),
            "rwa_density": round(rwa_density, 1),
            "raroc": round(raroc * 100, 2) if raroc else 0,
            "strategy": strategy,
            "limit_utilization": round(utilization * 100, 1) if utilization else 0,
            "actions": [],
            "priority": "LOW"
        }

        # 액션 생성 로직
        # 1. EXIT 전략인데 익스포저가 있는 경우
        if strategy == "EXIT" and exposure > 0:
            action["actions"].append({
                "type": "REDUCE_EXPOSURE",
                "description": "EXIT 전략 산업 - 만기 도래건 비연장, 신규 취급 중단",
                "target": "익스포저 50% 이상 축소"
            })
            action["priority"] = "HIGH"

        # 2. REDUCE 전략이면서 집중도 10% 초과
        elif strategy == "REDUCE" and concentration > 10:
            action["actions"].append({
                "type": "REDUCE_CONCENTRATION",
                "description": "REDUCE 전략 & 고집중도 - 단계적 익스포저 축소",
                "target": f"집중도 {concentration:.1f}% → 8% 이하"
            })
            action["priority"] = "HIGH"

        # 3. 한도 사용률 90% 초과
        elif utilization and utilization > 0.9:
            action["actions"].append({
                "type": "LIMIT_ALERT",
                "description": "한도 임박 - 신규 취급 제한 또는 한도 증액 검토",
                "target": f"사용률 {utilization*100:.0f}% → 80% 이하 유지"
            })
            action["priority"] = "HIGH"

        # 4. RAROC이 허들레이트 미달
        elif raroc and raroc < 0.12:
            action["actions"].append({
                "type": "IMPROVE_PROFITABILITY",
                "description": "수익성 개선 필요 - 금리 인상 또는 저수익 건 EXIT",
                "target": f"RAROC {raroc*100:.1f}% → 12% 이상"
            })
            action["priority"] = "MEDIUM"

        # 5. EXPAND 전략이면서 RAROC 양호
        elif strategy == "EXPAND" and raroc and raroc > 0.15:
            action["actions"].append({
                "type": "EXPAND",
                "description": "우량 세그먼트 - 적극적 영업 확대",
                "target": "영업 타겟 마케팅 강화"
            })
            action["priority"] = "MEDIUM"

        # 6. RWA 밀도가 높은 경우
        elif rwa_density > 65:
            action["actions"].append({
                "type": "OPTIMIZE_RWA",
                "description": "RWA 밀도 개선 - 담보 확보 또는 등급 개선",
                "target": f"RWA 밀도 {rwa_density:.0f}% → 50% 이하"
            })
            action["priority"] = "MEDIUM"

        if action["actions"]:
            rebalancing_actions.append(action)

    # 우선순위별 정렬
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    rebalancing_actions.sort(key=lambda x: priority_order.get(x["priority"], 2))

    return {
        "portfolio_summary": {
            "total_exposure": total_exposure,
            "industry_count": len(industry_status),
            "hhi_index": round(hhi, 1),
            "concentration_status": "HIGH" if hhi > 1500 else "MODERATE" if hhi > 1000 else "LOW"
        },
        "rebalancing_actions": rebalancing_actions,
        "summary_by_priority": {
            "high": len([a for a in rebalancing_actions if a["priority"] == "HIGH"]),
            "medium": len([a for a in rebalancing_actions if a["priority"] == "MEDIUM"]),
            "low": len([a for a in rebalancing_actions if a["priority"] == "LOW"])
        },
        "strategic_recommendations": [
            {
                "category": "자본효율성",
                "recommendation": "RWA 밀도 65% 초과 산업 담보 확보 강화",
                "expected_impact": "RWA 10-15% 절감 가능"
            },
            {
                "category": "수익성",
                "recommendation": "RAROC 12% 미달 세그먼트 가격 재조정",
                "expected_impact": "포트폴리오 RAROC 2-3%p 개선"
            },
            {
                "category": "리스크관리",
                "recommendation": "EXIT/REDUCE 전략 산업 익스포저 관리",
                "expected_impact": "리스크 집중도 완화"
            }
        ]
    }


# ===== 5. 자본효율성 종합 대시보드 =====
@router.get("/efficiency-dashboard")
def get_efficiency_dashboard(db: Session = Depends(get_db)):
    """
    자본효율성 종합 대시보드
    - 핵심 KPI
    - 개선 기회 요약
    - 실행 우선순위
    """

    # 자본 포지션
    capital = db.execute(text("""
        SELECT total_capital, total_rwa, bis_ratio, cet1_ratio
        FROM capital_position ORDER BY base_date DESC LIMIT 1
    """)).fetchone()

    # 포트폴리오 RAROC
    portfolio_raroc = db.execute(text("""
        SELECT SUM(total_revenue) / SUM(total_rwa * 0.08) as portfolio_raroc,
               SUM(total_exposure) as total_exposure,
               SUM(total_rwa) as total_rwa,
               SUM(total_el) as total_el
        FROM portfolio_summary WHERE segment_type = 'INDUSTRY'
    """)).fetchone()

    # RAROC 분포
    raroc_dist = db.execute(text("""
        SELECT
            SUM(CASE WHEN expected_raroc >= 0.15 THEN 1 ELSE 0 END) as above_target,
            SUM(CASE WHEN expected_raroc >= 0.12 AND expected_raroc < 0.15 THEN 1 ELSE 0 END) as meet_hurdle,
            SUM(CASE WHEN expected_raroc < 0.12 THEN 1 ELSE 0 END) as below_hurdle,
            COUNT(*) as total
        FROM pricing_result
    """)).fetchone()

    # 자본예산 소진율
    budget_util = db.execute(text("""
        SELECT SUM(rwa_used) / SUM(rwa_budget) as utilization
        FROM capital_budget WHERE status = 'ACTIVE'
    """)).fetchone()

    # RWA 밀도 (평균)
    rwa_density = db.execute(text("""
        SELECT SUM(total_rwa) / SUM(total_exposure) as avg_density
        FROM portfolio_summary WHERE segment_type = 'INDUSTRY'
    """)).fetchone()

    # 한도 경보 현황
    limit_alerts = db.execute(text("""
        SELECT COUNT(*) as alert_count
        FROM limit_exposure WHERE status IN ('WARNING', 'ALERT')
    """)).fetchone()

    return {
        "capital_metrics": {
            "total_capital": capital[0] if capital else 0,
            "total_rwa": capital[1] if capital else 0,
            "bis_ratio": round(capital[2] * 100, 2) if capital and capital[2] else 0,
            "cet1_ratio": round(capital[3] * 100, 2) if capital and capital[3] else 0,
            "capital_buffer": round((capital[2] - 0.105) * capital[1], 0) if capital else 0  # 규제 대비 여유
        },
        "efficiency_metrics": {
            "portfolio_raroc": round(portfolio_raroc[0] * 100, 2) if portfolio_raroc and portfolio_raroc[0] else 0,
            "rwa_density": round(rwa_density[0] * 100, 1) if rwa_density and rwa_density[0] else 0,
            "budget_utilization": round(budget_util[0] * 100, 1) if budget_util and budget_util[0] else 0,
            "expected_loss_rate": round(portfolio_raroc[3] / portfolio_raroc[1] * 100, 3) if portfolio_raroc and portfolio_raroc[1] else 0
        },
        "deal_quality": {
            "above_target": raroc_dist[0] if raroc_dist else 0,
            "meet_hurdle": raroc_dist[1] if raroc_dist else 0,
            "below_hurdle": raroc_dist[2] if raroc_dist else 0,
            "total_deals": raroc_dist[3] if raroc_dist else 0,
            "quality_ratio": round((raroc_dist[0] + raroc_dist[1]) / raroc_dist[3] * 100, 1) if raroc_dist and raroc_dist[3] else 0
        },
        "alerts": {
            "limit_warnings": limit_alerts[0] if limit_alerts else 0
        },
        "optimization_opportunities": {
            "rwa_reduction_potential": "15-20%",
            "raroc_improvement_potential": "2-3%p",
            "key_actions": [
                "담보 확보를 통한 LGD 개선",
                "저수익 세그먼트 가격 재조정",
                "고밀도 산업 익스포저 관리"
            ]
        }
    }


# ===== 유틸리티 함수 =====
def get_rating_bucket(grade: str) -> str:
    """신용등급을 버킷으로 변환"""
    if not grade:
        return "BBB"
    if grade.startswith("AAA") or grade.startswith("AA"):
        return "AAA_AA"
    elif grade.startswith("A"):
        return "A"
    elif grade.startswith("BBB"):
        return "BBB"
    else:
        return "BB_Below"


def calculate_irb_rwa(pd: float, lgd: float, ead: float, maturity: float) -> float:
    """Basel II IRB 방식 RWA 계산"""
    from scipy.stats import norm

    # PD 범위 제한
    pd = max(0.0003, min(pd, 1.0))

    # 상관계수 R
    r = 0.12 * (1 - math.exp(-50 * pd)) / (1 - math.exp(-50)) + \
        0.24 * (1 - (1 - math.exp(-50 * pd)) / (1 - math.exp(-50)))

    # 만기조정 b
    b = (0.11852 - 0.05478 * math.log(pd)) ** 2

    # 만기 제한
    m = max(1, min(maturity, 5))

    # K 계산
    try:
        k = lgd * norm.cdf(
            (1 / math.sqrt(1 - r)) * norm.ppf(pd) +
            math.sqrt(r / (1 - r)) * norm.ppf(0.999)
        ) - pd * lgd

        # 만기조정
        k = k * (1 + (m - 2.5) * b) / (1 - 1.5 * b)

        # RWA
        rwa = k * 12.5 * ead
    except:
        rwa = ead * 0.5  # 기본값

    return rwa
