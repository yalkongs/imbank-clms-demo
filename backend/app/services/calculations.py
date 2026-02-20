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


def calculate_economic_capital(rwa: float, capital_ratio: float = 0.105) -> float:
    """경제적 자본(EC) 계산 — BIS 최소 8% + 자본보전완충 2.5% = 10.5%"""
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


# ============================================================
# Phase 1 추가: 재무제표 분석 / 그룹여신 / 코베넌트
# ============================================================

# 재무비율 기준값 (심사 기준)
FINANCIAL_BENCHMARKS = {
    'debt_ratio':      {'threshold': 200.0, 'operator': 'LE', 'label': '부채비율(%)'},
    'current_ratio':   {'threshold': 100.0, 'operator': 'GE', 'label': '유동비율(%)'},
    'ier':             {'threshold': 1.5,   'operator': 'GE', 'label': '이자보상배율(배)'},
    'debt_dependency': {'threshold': 50.0,  'operator': 'LE', 'label': '차입금의존도(%)'},
    'dscr':            {'threshold': 1.25,  'operator': 'GE', 'label': 'DSCR(배)'},
    'op_margin':       {'threshold': 0.0,   'operator': 'GE', 'label': '영업이익률(%)'},
}

# 코베넌트 코드 → 재무비율 매핑
COVENANT_METRIC_MAP = {
    'FC01': 'debt_ratio',
    'FC02': 'dscr',
    'FC03': 'ier',
    'FC04': 'current_ratio',
    'FC05': 'net_debt_ebitda',
}


def calculate_dscr(ebitda: float, annual_principal: float, interest_expense: float) -> float:
    """
    DSCR (Debt Service Coverage Ratio) 채무상환능력비율
    DSCR = EBITDA / (연간 원금상환액 + 이자비용)
    기준: ≥ 1.25 (정상), ≥ 1.0 (최소), < 1.0 (위험)
    """
    denominator = annual_principal + interest_expense
    if denominator <= 0:
        return 0.0
    return round(ebitda / denominator, 4)


def calculate_altman_z(stmt: dict) -> tuple:
    """
    Altman Z'-Score (비상장 기업 수정 모델)
    Z' = 0.717×X1 + 0.847×X2 + 3.107×X3 + 0.420×X4 + 0.998×X5

    X1 = 운전자본 / 총자산
    X2 = 이익잉여금 / 총자산
    X3 = EBIT(영업이익) / 총자산
    X4 = 자기자본 / 총부채
    X5 = 매출액 / 총자산

    판정: Z' > 2.9 → SAFE, 1.23~2.9 → GREY, < 1.23 → DANGER

    Returns:
        (z_score: float, signal: str)
    """
    total_assets = stmt.get('total_assets', 0) or 0
    if total_assets <= 0:
        return 0.0, 'GREY'

    working_capital  = stmt.get('working_capital', 0) or 0
    retained_earning = stmt.get('retained_earning', 0) or 0
    operating_profit = stmt.get('operating_profit', 0) or 0
    equity           = stmt.get('equity', 0) or 0
    total_debt       = stmt.get('total_debt', 0) or 0
    revenue          = stmt.get('revenue', 0) or 0

    x1 = working_capital / total_assets
    x2 = retained_earning / total_assets
    x3 = operating_profit / total_assets
    x4 = equity / total_debt if total_debt > 0 else 0
    x5 = revenue / total_assets

    z = 0.717 * x1 + 0.847 * x2 + 3.107 * x3 + 0.420 * x4 + 0.998 * x5
    z = round(z, 4)

    if z > 2.9:
        signal = 'SAFE'
    elif z >= 1.23:
        signal = 'GREY'
    else:
        signal = 'DANGER'

    return z, signal


def calculate_financial_ratios(stmt: dict, prev_stmt: dict = None,
                                annual_principal: float = None) -> dict:
    """
    재무비율 자동 산출

    Args:
        stmt: 당기 재무제표 dict
        prev_stmt: 전기 재무제표 dict (성장률 계산용)
        annual_principal: 연간 원금상환 예정액 (DSCR 계산용)

    Returns:
        재무비율 dict + 신호등(pass/warning/fail)
    """
    total_assets     = stmt.get('total_assets') or 0
    current_assets   = stmt.get('current_assets') or 0
    total_debt       = stmt.get('total_debt') or 0
    current_debt     = stmt.get('current_debt') or 0
    total_borrowing  = stmt.get('total_borrowing') or 0
    equity           = stmt.get('equity') or 0
    operating_profit = stmt.get('operating_profit') or 0
    interest_expense = stmt.get('interest_expense') or 0
    ebitda           = stmt.get('ebitda') or 0
    net_profit       = stmt.get('net_profit') or 0
    revenue          = stmt.get('revenue') or 0
    retained_earning = stmt.get('retained_earning') or 0
    working_capital  = stmt.get('working_capital') or 0
    operating_cf     = stmt.get('operating_cf') or 0

    # 안정성
    debt_ratio      = round(total_debt / equity * 100, 2) if equity > 0 else None
    current_ratio   = round(current_assets / current_debt * 100, 2) if current_debt > 0 else None
    ier             = round(operating_profit / interest_expense, 2) if interest_expense > 0 else None
    debt_dependency = round(total_borrowing / total_assets * 100, 2) if total_assets > 0 else None

    # 현금흐름
    _principal = annual_principal or (total_borrowing * 0.1)  # 미제공 시 총차입금의 10% 추정
    dscr        = calculate_dscr(ebitda, _principal, interest_expense)
    ocf_ratio   = round(operating_cf / total_debt * 100, 2) if total_debt > 0 else None

    # 수익성
    op_margin = round(operating_profit / revenue * 100, 2) if revenue > 0 else None
    roa       = round(net_profit / total_assets * 100, 2) if total_assets > 0 else None
    roe       = round(net_profit / equity * 100, 2) if equity > 0 else None

    # 성장성 (전기 대비)
    revenue_growth = None
    op_growth      = None
    if prev_stmt:
        prev_revenue = prev_stmt.get('revenue') or 0
        prev_op      = prev_stmt.get('operating_profit') or 0
        if prev_revenue and prev_revenue != 0:
            revenue_growth = round((revenue - prev_revenue) / abs(prev_revenue) * 100, 2)
        if prev_op and prev_op != 0:
            op_growth = round((operating_profit - prev_op) / abs(prev_op) * 100, 2)

    # Altman Z'-Score
    altman_z, risk_signal = calculate_altman_z(stmt)

    # 신호등 판정
    def _signal(value, benchmark_key):
        if value is None:
            return 'N/A'
        b = FINANCIAL_BENCHMARKS.get(benchmark_key)
        if not b:
            return 'N/A'
        op = b['operator']
        th = b['threshold']
        if op == 'LE':
            if value <= th * 0.8:  return 'pass'
            if value <= th:         return 'warning'
            return 'fail'
        elif op == 'GE':
            if value >= th * 1.5:  return 'pass'
            if value >= th:         return 'warning'
            return 'fail'
        return 'N/A'

    return {
        'debt_ratio':      {'value': debt_ratio,      'signal': _signal(debt_ratio, 'debt_ratio')},
        'current_ratio':   {'value': current_ratio,   'signal': _signal(current_ratio, 'current_ratio')},
        'ier':             {'value': ier,             'signal': _signal(ier, 'ier')},
        'debt_dependency': {'value': debt_dependency, 'signal': _signal(debt_dependency, 'debt_dependency')},
        'dscr':            {'value': dscr,            'signal': _signal(dscr, 'dscr')},
        'ocf_ratio':       {'value': ocf_ratio,       'signal': 'N/A'},
        'op_margin':       {'value': op_margin,       'signal': _signal(op_margin, 'op_margin')},
        'roa':             {'value': roa,             'signal': 'N/A'},
        'roe':             {'value': roe,             'signal': 'N/A'},
        'revenue_growth':  {'value': revenue_growth,  'signal': 'N/A'},
        'op_growth':       {'value': op_growth,       'signal': 'N/A'},
        'altman_z':        {'value': altman_z,        'signal': risk_signal},
    }


def check_covenant_compliance(covenant: dict, financial_ratios: dict) -> dict:
    """
    코베넌트 이행 자동 체크 (재무 코베넌트용)

    Args:
        covenant: 코베넌트 정보 (covenant_code, operator, threshold_value)
        financial_ratios: calculate_financial_ratios() 결과 또는 단순 {metric: value}

    Returns:
        {result, actual_value, breach_severity, message}
    """
    code      = covenant.get('covenant_code', '')
    operator  = covenant.get('operator', 'GE')
    threshold = covenant.get('threshold_value')

    if threshold is None:
        return {'result': 'PENDING', 'actual_value': None,
                'breach_severity': None, 'message': '임계값 미설정'}

    metric = COVENANT_METRIC_MAP.get(code)
    if not metric:
        return {'result': 'PENDING', 'actual_value': None,
                'breach_severity': None, 'message': '자동 점검 불가 (정성 항목)'}

    # 비율 딕셔너리에서 값 추출 (calculate_financial_ratios 반환형 대응)
    raw = financial_ratios.get(metric)
    if isinstance(raw, dict):
        actual = raw.get('value')
    else:
        actual = raw

    if actual is None:
        return {'result': 'PENDING', 'actual_value': None,
                'breach_severity': None, 'message': '실측값 없음'}

    # 이행 판정
    if operator == 'LE':
        passed = actual <= threshold
    elif operator == 'GE':
        passed = actual >= threshold
    else:
        passed = (actual == threshold)

    if passed:
        return {'result': 'PASS', 'actual_value': actual,
                'breach_severity': None, 'message': '이행'}

    # 위반 심각도 판정 (임계값 대비 이탈 비율)
    if threshold != 0:
        deviation_pct = abs(actual - threshold) / abs(threshold) * 100
    else:
        deviation_pct = 100.0

    if deviation_pct <= 10:
        severity = 'MINOR'
    elif deviation_pct <= 25:
        severity = 'MAJOR'
    else:
        severity = 'EVENT_OF_DEFAULT'

    return {
        'result': 'BREACH',
        'actual_value': actual,
        'breach_severity': severity,
        'deviation_pct': round(deviation_pct, 2),
        'message': f'위반: 실측={actual}, 기준={threshold} ({operator}), 이탈={deviation_pct:.1f}%'
    }


def calculate_group_pd(member_pds: list, member_exposures: list) -> float:
    """
    그룹 가중평균 PD (익스포저 기준)
    최열위(최대 PD) 원칙 적용: max(가중평균PD, 최열위 계열사 PD)
    """
    if not member_pds or not member_exposures:
        return 0.0

    total_exposure = sum(member_exposures)
    if total_exposure <= 0:
        return max(member_pds)

    weighted_pd = sum(pd * exp for pd, exp in zip(member_pds, member_exposures)) / total_exposure
    # 최열위 원칙: 가중평균과 최대 PD 중 큰 값 (보수적)
    return round(max(weighted_pd, max(member_pds) * 0.7), 6)


# ============================================================
# Phase 2 추가: 자산건전성 분류 / IFRS9 ECL / 연체 관리
# ============================================================

# 금감원 5단계 충당금 적립률
PROVISION_RATES = {
    'NORMAL':         0.005,   # 0.5%
    'PRECAUTIONARY':  0.02,    # 2% (최소, 최대 5%)
    'SUBSTANDARD':    0.20,    # 20%
    'DOUBTFUL':       0.50,    # 50%
    'LOSS':           1.00,    # 100%
}

# 분류 우선순위 (가장 불리한 것 적용)
_CLASS_ORDER = ['NORMAL', 'PRECAUTIONARY', 'SUBSTANDARD', 'DOUBTFUL', 'LOSS']


def _class_rank(cls: str) -> int:
    try:
        return _CLASS_ORDER.index(cls)
    except ValueError:
        return 0


def classify_asset_by_dpd(dpd: int) -> str:
    """DPD 기준 자산건전성 분류"""
    if dpd <= 0:
        return 'NORMAL'
    elif dpd <= 30:
        return 'PRECAUTIONARY'
    elif dpd <= 90:
        return 'SUBSTANDARD'
    elif dpd <= 180:
        return 'DOUBTFUL'
    else:
        return 'LOSS'


def classify_asset_by_pd(pd: float) -> str:
    """PD 기준 자산건전성 분류"""
    if pd < 0.03:
        return 'NORMAL'
    elif pd < 0.10:
        return 'PRECAUTIONARY'
    elif pd < 0.20:
        return 'SUBSTANDARD'
    elif pd < 0.50:
        return 'DOUBTFUL'
    else:
        return 'LOSS'


def classify_asset_by_ews(ews_score: float) -> str:
    """EWS 종합점수 기준 자산건전성 분류
    EWS는 조기경보 지표 — 최대 요주의(PRECAUTIONARY)까지만 영향.
    고정(SUBSTANDARD) 이상은 DPD/PD 기준으로만 결정.
    """
    if ews_score >= 60:
        return 'NORMAL'
    else:
        return 'PRECAUTIONARY'


def classify_asset(dpd: int, pd: float, ews_score: float = None) -> dict:
    """
    금감원 기준 5단계 자산건전성 분류
    보수주의 원칙: DPD / PD / EWS 중 가장 불리한 등급 적용

    Returns:
        {classification, dpd_class, pd_class, ews_class, final_basis, provision_rate}
    """
    dpd_class = classify_asset_by_dpd(dpd)
    pd_class  = classify_asset_by_pd(pd)
    ews_class = classify_asset_by_ews(ews_score) if ews_score is not None else 'NORMAL'

    ranks = {
        'DPD': _class_rank(dpd_class),
        'PD':  _class_rank(pd_class),
        'EWS': _class_rank(ews_class),
    }
    final_basis = max(ranks, key=ranks.get)
    classes = {'DPD': dpd_class, 'PD': pd_class, 'EWS': ews_class}
    final_class = classes[final_basis]

    return {
        'classification':   final_class,
        'dpd_based_class':  dpd_class,
        'pd_based_class':   pd_class,
        'ews_based_class':  ews_class,
        'final_class_basis': final_basis,
        'provision_rate':   PROVISION_RATES[final_class],
    }


def determine_sicr(pd_original: float, pd_current: float,
                   ews_score: float = None, dpd: int = 0,
                   grade_drop_notches: int = 0) -> dict:
    """
    SICR (Significant Increase in Credit Risk) 판별
    — IFRS 9 Stage 1 → Stage 2 이동 트리거

    SICR 조건 (OR):
      1. PD 2배 이상 상승
      2. 등급 2 notch 이상 하락
      3. EWS 점수 WATCH 이하 (< 55점)
      4. DPD ≥ 30일

    Returns:
        {sicr: bool, reasons: list[str], recommended_stage: int}
    """
    reasons = []

    if pd_original and pd_original > 0:
        if pd_current >= pd_original * 2.0:
            reasons.append('PD_DOUBLED')

    if grade_drop_notches >= 2:
        reasons.append('GRADE_DROP_2NOTCH')

    if ews_score is not None and ews_score < 55:
        reasons.append('EWS_WATCH')

    if dpd >= 30:
        reasons.append('DPD_30')

    sicr = len(reasons) > 0

    # Stage 결정
    if dpd >= 90 or pd_current >= 0.20:
        stage = 3
    elif sicr:
        stage = 2
    else:
        stage = 1

    return {
        'sicr': sicr,
        'reasons': reasons,
        'recommended_stage': stage,
    }


def calculate_ecl_stage1(pd_12m: float, lgd: float, ead: float,
                          discount_factor: float = 0.97) -> float:
    """
    Stage 1 ECL: 12개월 기대신용손실
    ECL = PD_12M × LGD × EAD × DF

    discount_factor: 기본 0.97 (약 0.5년 할인, 금리 6% 기준)
    """
    return round(pd_12m * lgd * ead * discount_factor, 2)


def calculate_ecl_stage2(pd_current: float, lgd: float, ead: float,
                          remaining_months: int,
                          annual_pd_multiplier: float = 1.0) -> float:
    """
    Stage 2 ECL: 잔존 전 기간 기대신용손실
    단순화 모델: Lifetime ECL = Σ_t (conditional PD_t × LGD × EAD_t × DF_t)
    conditional PD_t ≈ PD_annual × (1-PD_annual)^(t-1)

    Returns: Lifetime ECL
    """
    if remaining_months <= 0 or pd_current <= 0:
        return calculate_ecl_stage1(pd_current, lgd, ead)

    risk_free_rate_monthly = 0.005  # 연 6% / 12
    pd_annual = min(pd_current * annual_pd_multiplier, 0.99)
    pd_monthly = 1 - (1 - pd_annual) ** (1 / 12)

    ecl = 0.0
    survival = 1.0
    for t in range(1, remaining_months + 1):
        cond_pd = pd_monthly * survival
        df = 1 / (1 + risk_free_rate_monthly) ** t
        ecl += cond_pd * lgd * ead * df
        survival *= (1 - pd_monthly)

    return round(ecl, 2)


def calculate_ecl_stage3(ead: float, expected_recovery: float,
                          recovery_months: int = 24,
                          discount_rate_annual: float = 0.06) -> float:
    """
    Stage 3 ECL: 신용 손상 (개별 평가)
    ECL = EAD - PV(예상 현금회수액)

    expected_recovery: 예상 총 회수액
    recovery_months: 예상 회수 기간 (월)
    """
    if expected_recovery <= 0:
        return round(ead, 2)

    monthly_rate = discount_rate_annual / 12
    if recovery_months > 0 and monthly_rate > 0:
        # 균등 분할 회수 가정
        monthly_payment = expected_recovery / recovery_months
        pv_recovery = sum(
            monthly_payment / (1 + monthly_rate) ** t
            for t in range(1, recovery_months + 1)
        )
    else:
        pv_recovery = expected_recovery

    ecl = max(ead - pv_recovery, 0.0)
    return round(ecl, 2)


def determine_delinquency_stage(dpd: int) -> str:
    """
    DPD 기준 연체 단계 분류
    EARLY(1-30) / MID(31-60) / LATE(61-90) / NPL(91-180) / WRITEOFF(181+)
    """
    if dpd <= 0:
        return 'CURRENT'
    elif dpd <= 30:
        return 'EARLY'
    elif dpd <= 60:
        return 'MID'
    elif dpd <= 90:
        return 'LATE'
    elif dpd <= 180:
        return 'NPL'
    else:
        return 'WRITEOFF'
