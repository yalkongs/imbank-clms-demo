"""
금융 계산 서비스 모듈
RAROC, RWA, 가격결정 등 핵심 계산 로직
"""
import math
from typing import Dict, Optional

# 등급별 PD 매핑
GRADE_PD_MAP = {
    'AAA': 0.0002, 'AA+': 0.0004, 'AA': 0.0006, 'AA-': 0.0010,
    'A+': 0.0015, 'A': 0.0025, 'A-': 0.0045,
    'BBB+': 0.0070, 'BBB': 0.0115, 'BBB-': 0.0185,
    'BB+': 0.0300, 'BB': 0.0480, 'BB-': 0.0750,
    'B+': 0.1200, 'B': 0.2000, 'B-': 0.3000
}

# 전략별 가격 조정 (bp)
STRATEGY_PRICING_ADJ = {
    'EXPAND': -20,
    'SELECTIVE': 0,
    'MAINTAIN': 10,
    'REDUCE': 30,
    'EXIT': 100
}


def calculate_rwa(pd: float, lgd: float, ead: float, maturity_years: float = 2.5) -> float:
    """
    IRB 방식 RWA 계산
    Basel II/III 공식 기반 간소화 버전
    """
    # 상관계수 R 계산
    r = 0.12 * (1 - math.exp(-50 * pd)) / (1 - math.exp(-50)) + \
        0.24 * (1 - (1 - math.exp(-50 * pd)) / (1 - math.exp(-50)))

    # 만기조정 b 계산
    b = (0.11852 - 0.05478 * math.log(max(pd, 0.0001))) ** 2

    # 표준정규분포 함수 근사
    def norm_cdf(x):
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def norm_inv(p):
        # Newton-Raphson 근사
        if p <= 0:
            return -3.0
        if p >= 1:
            return 3.0

        a = [0, -3.969683028665376e+01, 2.209460984245205e+02,
             -2.759285104469687e+02, 1.383577518672690e+02,
             -3.066479806614716e+01, 2.506628277459239e+00]
        b = [0, -5.447609879822406e+01, 1.615858368580409e+02,
             -1.556989798598866e+02, 6.680131188771972e+01,
             -1.328068155288572e+01]
        c = [0, -7.784894002430293e-03, -3.223964580411365e-01,
             -2.400758277161838e+00, -2.549732539343734e+00,
             4.374664141464968e+00, 2.938163982698783e+00]
        d = [0, 7.784695709041462e-03, 3.224671290700398e-01,
             2.445134137142996e+00, 3.754408661907416e+00]

        p_low = 0.02425
        p_high = 1 - p_low

        if p < p_low:
            q = math.sqrt(-2 * math.log(p))
            return (((((c[1] * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) * q + c[6]) / \
                   ((((d[1] * q + d[2]) * q + d[3]) * q + d[4]) * q + 1)
        elif p <= p_high:
            q = p - 0.5
            r = q * q
            return (((((a[1] * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * r + a[6]) * q / \
                   (((((b[1] * r + b[2]) * r + b[3]) * r + b[4]) * r + b[5]) * r + 1)
        else:
            q = math.sqrt(-2 * math.log(1 - p))
            return -(((((c[1] * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) * q + c[6]) / \
                    ((((d[1] * q + d[2]) * q + d[3]) * q + d[4]) * q + 1)

    # K 계산 (자본요구량)
    g_pd = norm_inv(pd)
    g_999 = norm_inv(0.999)

    k = lgd * norm_cdf(math.sqrt(1 / (1 - r)) * g_pd + math.sqrt(r / (1 - r)) * g_999) - pd * lgd
    k = k * (1 - 1.5 * b) ** (-1) * (1 + (maturity_years - 2.5) * b)

    # RWA = K * 12.5 * EAD
    rwa = k * 12.5 * ead

    return max(rwa, 0)


def calculate_expected_loss(pd: float, lgd: float, ead: float) -> float:
    """예상손실(EL) 계산"""
    return pd * lgd * ead


def calculate_economic_capital(rwa: float, capital_ratio: float = 0.08) -> float:
    """경제적 자본(EC) 계산"""
    return rwa * capital_ratio


def calculate_raroc(
    amount: float,
    rate: float,
    ftp_rate: float,
    pd: float,
    lgd: float,
    tenor_years: float = 1.0,
    opex_rate: float = 0.005
) -> Dict:
    """
    RAROC 계산 (연간 기준)

    Returns:
        Dict with revenue, cost, el, ec, rwa, raroc
    """
    # EAD (확정대출 가정)
    ead = amount

    # 연간 수익 (금리는 연율이므로 그대로 사용)
    annual_interest_revenue = amount * rate

    # 연간 비용
    annual_funding_cost = amount * ftp_rate
    annual_opex = amount * opex_rate

    # 연간 예상손실 (PD는 연간 부도율)
    annual_el = calculate_expected_loss(pd, lgd, ead)

    # RWA 및 경제적 자본 (만기 반영)
    rwa = calculate_rwa(pd, lgd, ead, tenor_years)
    ec = calculate_economic_capital(rwa)

    # 연간 순이익
    annual_net_income = annual_interest_revenue - annual_funding_cost - annual_opex - annual_el

    # RAROC (연간 수익률)
    raroc = annual_net_income / ec if ec > 0 else 0

    # RoRWA (연간)
    rorwa = annual_net_income / rwa if rwa > 0 else 0

    return {
        "interest_revenue": annual_interest_revenue,
        "funding_cost": annual_funding_cost,
        "opex": annual_opex,
        "expected_loss": annual_el,
        "net_income": annual_net_income,
        "rwa": rwa,
        "economic_capital": ec,
        "raroc": raroc,
        "rorwa": rorwa
    }


def calculate_pricing(
    pd: float,
    lgd: float,
    base_rate: float = 0.035,
    ftp_spread: float = 0.005,
    opex_spread: float = 0.002,
    target_margin: float = 0.01,
    strategy_code: Optional[str] = None,
    has_collateral: bool = False,
    hurdle_rate: float = 0.12
) -> Dict:
    """
    가격결정 (금리 산출)

    Returns:
        Dict with all pricing components and final rate
    """
    # EL 기반 신용스프레드
    el_spread = pd * lgd

    # UL 기반 자본비용 스프레드 (간소화)
    ul_spread = el_spread * 0.5 * hurdle_rate

    credit_spread = el_spread + ul_spread

    # 전략 가감
    strategy_adj = 0
    if strategy_code:
        strategy_adj = STRATEGY_PRICING_ADJ.get(strategy_code, 0) / 10000  # bp to ratio

    # 담보 가감
    collateral_adj = -0.003 if has_collateral else 0

    # 최종 금리
    system_rate = base_rate + ftp_spread + credit_spread + opex_spread + target_margin
    final_rate = system_rate + strategy_adj + collateral_adj

    return {
        "base_rate": base_rate,
        "ftp_spread": ftp_spread,
        "credit_spread": credit_spread,
        "el_spread": el_spread,
        "ul_spread": ul_spread,
        "opex_spread": opex_spread,
        "target_margin": target_margin,
        "strategy_adj": strategy_adj,
        "collateral_adj": collateral_adj,
        "system_rate": system_rate,
        "final_rate": final_rate
    }


def calculate_stress_pd(base_pd: float, scenario_factor: float, industry_sensitivity: float = 1.0) -> float:
    """
    스트레스 상황 PD 계산

    Args:
        base_pd: 기본 PD (TTC)
        scenario_factor: 시나리오 충격 계수 (1.0 = baseline)
        industry_sensitivity: 산업별 민감도

    Returns:
        stressed PD
    """
    stressed_pd = base_pd * scenario_factor * industry_sensitivity
    return min(stressed_pd, 1.0)  # 최대 100%


def calculate_capital_ratios(
    cet1_capital: float,
    at1_capital: float,
    tier2_capital: float,
    credit_rwa: float,
    market_rwa: float,
    operational_rwa: float,
    total_exposure: float
) -> Dict:
    """
    자본비율 계산

    Returns:
        Dict with BIS ratio, CET1 ratio, Tier1 ratio, leverage ratio
    """
    total_capital = cet1_capital + at1_capital + tier2_capital
    tier1_capital = cet1_capital + at1_capital
    total_rwa = credit_rwa + market_rwa + operational_rwa

    bis_ratio = total_capital / total_rwa if total_rwa > 0 else 0
    cet1_ratio = cet1_capital / total_rwa if total_rwa > 0 else 0
    tier1_ratio = tier1_capital / total_rwa if total_rwa > 0 else 0
    leverage_ratio = tier1_capital / total_exposure if total_exposure > 0 else 0

    return {
        "total_capital": total_capital,
        "tier1_capital": tier1_capital,
        "total_rwa": total_rwa,
        "bis_ratio": bis_ratio,
        "cet1_ratio": cet1_ratio,
        "tier1_ratio": tier1_ratio,
        "leverage_ratio": leverage_ratio
    }


def get_grade_from_pd(pd: float) -> str:
    """PD로부터 등급 추정"""
    for grade, grade_pd in sorted(GRADE_PD_MAP.items(), key=lambda x: x[1]):
        if pd <= grade_pd * 1.5:
            return grade
    return 'B-'


def get_pd_from_grade(grade: str) -> float:
    """등급으로부터 PD 조회"""
    return GRADE_PD_MAP.get(grade, 0.10)
