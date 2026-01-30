"""
신용평가 모델 모듈
MDL_CORP_RATING, MDL_RETAIL_RATING, MDL_LGD, MDL_EAD 구현
"""
import math
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum


# =============================================================================
# 공통 상수 및 유틸리티
# =============================================================================

class RatingGrade(Enum):
    """신용등급 Enum"""
    AAA = ('AAA', 1, 0.0002)
    AA_PLUS = ('AA+', 2, 0.0004)
    AA = ('AA', 3, 0.0006)
    AA_MINUS = ('AA-', 4, 0.0010)
    A_PLUS = ('A+', 5, 0.0015)
    A = ('A', 6, 0.0025)
    A_MINUS = ('A-', 7, 0.0045)
    BBB_PLUS = ('BBB+', 8, 0.0070)
    BBB = ('BBB', 9, 0.0115)
    BBB_MINUS = ('BBB-', 10, 0.0185)
    BB_PLUS = ('BB+', 11, 0.0300)
    BB = ('BB', 12, 0.0480)
    BB_MINUS = ('BB-', 13, 0.0750)
    B_PLUS = ('B+', 14, 0.1200)
    B = ('B', 15, 0.2000)
    B_MINUS = ('B-', 16, 0.3000)
    CCC = ('CCC', 17, 0.5000)
    CC = ('CC', 18, 0.7500)
    C = ('C', 19, 0.9000)
    D = ('D', 20, 1.0000)

    def __init__(self, grade_str: str, notch: int, pd: float):
        self.grade_str = grade_str
        self.notch = notch
        self.pd = pd


GRADE_PD_MAP = {g.grade_str: g.pd for g in RatingGrade}
NOTCH_GRADE_MAP = {g.notch: g.grade_str for g in RatingGrade}


def sigmoid(x: float) -> float:
    """Sigmoid 함수"""
    return 1 / (1 + math.exp(-x))


def normalize(value: float, min_val: float, max_val: float) -> float:
    """정규화 (0~1 범위)"""
    if max_val <= min_val:
        return 0.5
    return max(0, min(1, (value - min_val) / (max_val - min_val)))


# =============================================================================
# MDL_CORP_RATING: 기업신용평가모형
# =============================================================================

@dataclass
class CorporateRatingInput:
    """기업신용평가 입력 데이터"""
    # 재무 정보 (Financial)
    total_assets: float  # 총자산 (원)
    total_liabilities: float  # 총부채 (원)
    total_equity: float  # 자기자본 (원)
    sales: float  # 매출액 (원)
    operating_income: float  # 영업이익 (원)
    net_income: float  # 당기순이익 (원)
    ebitda: float  # EBITDA (원)
    interest_expense: float  # 이자비용 (원)
    current_assets: float  # 유동자산 (원)
    current_liabilities: float  # 유동부채 (원)
    cash_and_equivalents: float  # 현금성자산 (원)

    # 비재무 정보 (Non-Financial)
    years_in_business: int  # 업력 (년)
    industry_code: str  # 산업코드
    is_listed: bool = False  # 상장 여부
    has_external_audit: bool = True  # 외부감사 여부
    ceo_experience_years: int = 10  # 대표이사 경력 (년)

    # 거래 정보 (Behavioral)
    months_with_bank: int = 12  # 거래기간 (월)
    overdraft_count_12m: int = 0  # 최근 12개월 연체횟수
    max_overdraft_days: int = 0  # 최장 연체일수


class CorporateRatingModel:
    """
    기업신용평가모형 (MDL_CORP_RATING)

    재무비율 분석 + 비재무 요소 + 행동 데이터를 종합하여
    신용등급 및 부도확률(PD)을 산출하는 로지스틱 회귀 기반 모형
    """

    MODEL_ID = "MDL_CORP_RATING"
    MODEL_VERSION = "3.0"

    # 모형 계수 (가중치)
    COEFFICIENTS = {
        # 재무비율 (Financial Ratios) - 베이스라인
        'debt_ratio': -0.8,  # 부채비율 (낮을수록 좋음)
        'current_ratio': 0.5,  # 유동비율 (높을수록 좋음)
        'interest_coverage': 0.7,  # 이자보상배율 (높을수록 좋음)
        'roa': 0.6,  # ROA (높을수록 좋음)
        'roe': 0.4,  # ROE (높을수록 좋음)
        'operating_margin': 0.5,  # 영업이익률 (높을수록 좋음)
        'sales_growth': 0.3,  # 매출성장률 (높을수록 좋음)
        'ebitda_margin': 0.4,  # EBITDA 마진 (높을수록 좋음)
        'cash_ratio': 0.3,  # 현금비율 (높을수록 좋음)

        # 비재무 (Non-Financial)
        'years_in_business': 0.4,  # 업력 (길수록 좋음)
        'is_listed': 0.5,  # 상장 여부
        'has_audit': 0.3,  # 외부감사 여부
        'ceo_experience': 0.2,  # 대표 경력

        # 행동 (Behavioral)
        'relationship_length': 0.3,  # 거래기간
        'overdraft_penalty': -1.5,  # 연체 페널티

        # 산업 조정 (Industry Adjustment)
        'industry_factor': 0.5,
    }

    # 산업별 리스크 계수
    INDUSTRY_RISK = {
        'IND001': 0.8,   # 반도체 - 저위험
        'IND002': 0.85,  # IT서비스 - 저위험
        'IND003': 1.0,   # 자동차부품 - 중위험
        'IND004': 1.0,   # 기계장비 - 중위험
        'IND005': 1.0,   # 화학 - 중위험
        'IND006': 0.9,   # 바이오헬스 - 중저위험
        'IND007': 1.1,   # 유통 - 중고위험
        'IND008': 1.3,   # 건설 - 고위험
        'IND009': 1.5,   # 부동산PF - 고위험
        'IND010': 1.1,   # 무역 - 중고위험
    }

    # 기본 절편 (Intercept)
    INTERCEPT = 0.5

    def __init__(self):
        pass

    def calculate_financial_ratios(self, input_data: CorporateRatingInput) -> Dict[str, float]:
        """재무비율 계산"""
        ratios = {}

        # 안전성 지표
        ratios['debt_ratio'] = (input_data.total_liabilities / input_data.total_equity
                               if input_data.total_equity > 0 else 5.0)
        ratios['current_ratio'] = (input_data.current_assets / input_data.current_liabilities
                                   if input_data.current_liabilities > 0 else 1.0)

        # 이자보상배율
        ratios['interest_coverage'] = (input_data.operating_income / input_data.interest_expense
                                       if input_data.interest_expense > 0 else 10.0)

        # 수익성 지표
        ratios['roa'] = (input_data.net_income / input_data.total_assets
                        if input_data.total_assets > 0 else 0)
        ratios['roe'] = (input_data.net_income / input_data.total_equity
                        if input_data.total_equity > 0 else 0)
        ratios['operating_margin'] = (input_data.operating_income / input_data.sales
                                      if input_data.sales > 0 else 0)
        ratios['ebitda_margin'] = (input_data.ebitda / input_data.sales
                                   if input_data.sales > 0 else 0)

        # 현금비율
        ratios['cash_ratio'] = (input_data.cash_and_equivalents / input_data.current_liabilities
                               if input_data.current_liabilities > 0 else 0.5)

        # 성장성 (매출액 대비 자산 회전율로 대체)
        ratios['sales_growth'] = input_data.sales / input_data.total_assets if input_data.total_assets > 0 else 0.5

        return ratios

    def normalize_ratios(self, ratios: Dict[str, float]) -> Dict[str, float]:
        """재무비율 정규화"""
        normalized = {}

        # 부채비율: 0~500% → 1~0 (낮을수록 좋음)
        normalized['debt_ratio'] = 1 - normalize(ratios['debt_ratio'], 0, 5)

        # 유동비율: 0~300% → 0~1 (높을수록 좋음)
        normalized['current_ratio'] = normalize(ratios['current_ratio'], 0, 3)

        # 이자보상배율: 0~20 → 0~1 (높을수록 좋음)
        normalized['interest_coverage'] = normalize(ratios['interest_coverage'], 0, 20)

        # ROA: -10%~20% → 0~1
        normalized['roa'] = normalize(ratios['roa'], -0.1, 0.2)

        # ROE: -20%~40% → 0~1
        normalized['roe'] = normalize(ratios['roe'], -0.2, 0.4)

        # 영업이익률: -10%~30% → 0~1
        normalized['operating_margin'] = normalize(ratios['operating_margin'], -0.1, 0.3)

        # EBITDA 마진: 0~40% → 0~1
        normalized['ebitda_margin'] = normalize(ratios['ebitda_margin'], 0, 0.4)

        # 현금비율: 0~100% → 0~1
        normalized['cash_ratio'] = normalize(ratios['cash_ratio'], 0, 1)

        # 매출/자산 회전율: 0~2 → 0~1
        normalized['sales_growth'] = normalize(ratios['sales_growth'], 0, 2)

        return normalized

    def calculate_score(self, input_data: CorporateRatingInput) -> Dict:
        """
        신용점수 계산

        Returns:
            Dict with score components, total_score, grade, pd
        """
        # 1. 재무비율 계산 및 정규화
        raw_ratios = self.calculate_financial_ratios(input_data)
        norm_ratios = self.normalize_ratios(raw_ratios)

        # 2. 재무 점수 계산
        financial_score = 0
        financial_details = {}

        for ratio_name, norm_value in norm_ratios.items():
            coef = self.COEFFICIENTS.get(ratio_name, 0)
            contribution = norm_value * coef
            financial_score += contribution
            financial_details[ratio_name] = {
                'raw': raw_ratios.get(ratio_name, 0),
                'normalized': norm_value,
                'coefficient': coef,
                'contribution': contribution
            }

        # 3. 비재무 점수
        nonfinancial_score = 0

        # 업력 (최대 30년까지 반영)
        years_norm = normalize(input_data.years_in_business, 0, 30)
        years_contrib = years_norm * self.COEFFICIENTS['years_in_business']
        nonfinancial_score += years_contrib

        # 상장 여부
        listed_contrib = (1 if input_data.is_listed else 0) * self.COEFFICIENTS['is_listed']
        nonfinancial_score += listed_contrib

        # 외부감사 여부
        audit_contrib = (1 if input_data.has_external_audit else 0) * self.COEFFICIENTS['has_audit']
        nonfinancial_score += audit_contrib

        # 대표 경력
        ceo_norm = normalize(input_data.ceo_experience_years, 0, 30)
        ceo_contrib = ceo_norm * self.COEFFICIENTS['ceo_experience']
        nonfinancial_score += ceo_contrib

        # 4. 행동 점수
        behavioral_score = 0

        # 거래기간
        rel_norm = normalize(input_data.months_with_bank, 0, 120)  # 최대 10년
        rel_contrib = rel_norm * self.COEFFICIENTS['relationship_length']
        behavioral_score += rel_contrib

        # 연체 페널티
        if input_data.overdraft_count_12m > 0 or input_data.max_overdraft_days > 0:
            overdraft_penalty = (input_data.overdraft_count_12m * 0.1 +
                               input_data.max_overdraft_days / 30 * 0.2)
            overdraft_penalty = min(overdraft_penalty, 1.0)
            behavioral_score += overdraft_penalty * self.COEFFICIENTS['overdraft_penalty']

        # 5. 산업 조정
        industry_risk = self.INDUSTRY_RISK.get(input_data.industry_code, 1.0)
        industry_adj = (1 - industry_risk) * self.COEFFICIENTS['industry_factor']

        # 6. 총점 계산
        raw_score = (self.INTERCEPT + financial_score + nonfinancial_score +
                    behavioral_score + industry_adj)

        # 7. PD 변환 (로지스틱 함수)
        # 점수가 높을수록 PD가 낮아지도록
        pd_logit = -2.5 * raw_score + 1.5
        pd = sigmoid(pd_logit)

        # 8. PD를 0.02% ~ 100% 범위로 조정
        pd = max(0.0002, min(1.0, pd))

        # 9. 등급 산출
        grade = self._pd_to_grade(pd)

        # 10. 총점을 1000점 만점 스케일로 변환
        score_1000 = int(max(100, min(1000, (1 - pd) * 1000)))

        return {
            'model_id': self.MODEL_ID,
            'model_version': self.MODEL_VERSION,
            'raw_score': raw_score,
            'score_1000': score_1000,
            'pd': pd,
            'ttc_pd': pd,  # TTC PD
            'pit_pd': pd * industry_risk,  # PIT PD (산업 조정)
            'grade': grade,
            'components': {
                'financial': {
                    'score': financial_score,
                    'details': financial_details
                },
                'nonfinancial': {
                    'score': nonfinancial_score,
                    'years_in_business': years_contrib,
                    'is_listed': listed_contrib,
                    'has_audit': audit_contrib,
                    'ceo_experience': ceo_contrib
                },
                'behavioral': {
                    'score': behavioral_score,
                    'relationship_length': rel_contrib
                },
                'industry_adjustment': industry_adj
            }
        }

    def _pd_to_grade(self, pd: float) -> str:
        """PD를 신용등급으로 변환"""
        for grade_enum in RatingGrade:
            if pd <= grade_enum.pd * 1.3:  # 30% 여유
                return grade_enum.grade_str
        return 'D'


# =============================================================================
# MDL_RETAIL_RATING: 소호/개인사업자 신용평가모형
# =============================================================================

@dataclass
class RetailRatingInput:
    """소호/개인사업자 신용평가 입력 데이터"""
    # 사업자 정보
    business_type: str  # 'INDIVIDUAL', 'CORPORATION'
    annual_sales: float  # 연매출 (원)
    years_in_business: int  # 업력 (년)
    industry_code: str  # 산업코드
    employee_count: int = 1  # 종업원 수

    # 대표자 정보
    owner_age: int = 45  # 대표자 나이
    owner_credit_score: int = 700  # 대표자 개인신용점수 (CB)

    # 재무 정보 (간이)
    total_debt: float = 0  # 총 부채
    monthly_income: float = 0  # 월 소득

    # 거래 정보
    months_with_bank: int = 12
    average_balance: float = 0  # 평균잔액
    overdraft_count_12m: int = 0
    max_overdraft_days: int = 0

    # 담보 정보
    has_collateral: bool = False
    collateral_value: float = 0


class RetailRatingModel:
    """
    소호신용평가모형 (MDL_RETAIL_RATING)

    개인사업자/소호 고객의 신용도를 평가하는 스코어카드 모형
    """

    MODEL_ID = "MDL_RETAIL_RATING"
    MODEL_VERSION = "3.0"

    # 스코어카드 점수표
    SCORECARD = {
        # 연매출 구간
        'sales_bracket': {
            (0, 50_000_000): 30,
            (50_000_000, 100_000_000): 50,
            (100_000_000, 300_000_000): 70,
            (300_000_000, 500_000_000): 85,
            (500_000_000, 1_000_000_000): 95,
            (1_000_000_000, float('inf')): 100
        },
        # 업력 구간
        'years_bracket': {
            (0, 1): 20,
            (1, 3): 40,
            (3, 5): 60,
            (5, 10): 80,
            (10, float('inf')): 100
        },
        # 대표자 CB점수 구간
        'cb_bracket': {
            (0, 500): 10,
            (500, 600): 30,
            (600, 700): 50,
            (700, 800): 75,
            (800, 900): 90,
            (900, 1001): 100
        },
        # 부채비율 구간 (DTI)
        'dti_bracket': {
            (0, 30): 100,
            (30, 50): 80,
            (50, 70): 60,
            (70, 100): 40,
            (100, 150): 20,
            (150, float('inf')): 10
        }
    }

    # 가중치
    WEIGHTS = {
        'sales': 0.20,
        'years': 0.15,
        'cb_score': 0.30,
        'dti': 0.15,
        'relationship': 0.10,
        'behavioral': 0.10
    }

    def __init__(self):
        pass

    def _get_bracket_score(self, value: float, brackets: Dict) -> int:
        """구간별 점수 조회"""
        for (low, high), score in brackets.items():
            if low <= value < high:
                return score
        return 50  # 기본값

    def calculate_score(self, input_data: RetailRatingInput) -> Dict:
        """
        신용점수 계산
        """
        scores = {}

        # 1. 연매출 점수
        scores['sales'] = self._get_bracket_score(
            input_data.annual_sales,
            self.SCORECARD['sales_bracket']
        )

        # 2. 업력 점수
        scores['years'] = self._get_bracket_score(
            input_data.years_in_business,
            self.SCORECARD['years_bracket']
        )

        # 3. CB점수
        scores['cb_score'] = self._get_bracket_score(
            input_data.owner_credit_score,
            self.SCORECARD['cb_bracket']
        )

        # 4. 부채비율 (DTI)
        if input_data.monthly_income > 0:
            dti = (input_data.total_debt / 12) / input_data.monthly_income * 100
        else:
            dti = 100  # 소득 정보 없으면 보수적
        scores['dti'] = self._get_bracket_score(dti, self.SCORECARD['dti_bracket'])

        # 5. 거래관계 점수
        rel_score = min(100, input_data.months_with_bank / 60 * 100)  # 5년 = 100점
        if input_data.average_balance > 10_000_000:
            rel_score = min(100, rel_score + 10)
        scores['relationship'] = rel_score

        # 6. 행동 점수
        behavioral_score = 100
        if input_data.overdraft_count_12m > 0:
            behavioral_score -= min(50, input_data.overdraft_count_12m * 10)
        if input_data.max_overdraft_days > 0:
            behavioral_score -= min(30, input_data.max_overdraft_days)
        scores['behavioral'] = max(0, behavioral_score)

        # 7. 가중평균 점수 계산
        total_score = sum(
            scores[key] * self.WEIGHTS[key]
            for key in self.WEIGHTS.keys()
        )

        # 8. 산업 조정
        industry_risk = CorporateRatingModel.INDUSTRY_RISK.get(input_data.industry_code, 1.0)
        total_score = total_score / industry_risk

        # 9. 담보 가산점
        if input_data.has_collateral and input_data.collateral_value > 0:
            total_score = min(100, total_score + 5)

        # 10. PD 산출
        # 점수 100점 → PD 0.2%, 점수 0점 → PD 30%
        pd = 0.30 * math.exp(-0.05 * total_score)
        pd = max(0.0002, min(0.30, pd))

        # 11. 등급 산출
        grade = self._score_to_grade(total_score)

        return {
            'model_id': self.MODEL_ID,
            'model_version': self.MODEL_VERSION,
            'score_100': round(total_score, 1),
            'score_1000': int(total_score * 10),
            'pd': pd,
            'ttc_pd': pd,
            'pit_pd': pd * industry_risk,
            'grade': grade,
            'components': {
                'sales_score': scores['sales'],
                'years_score': scores['years'],
                'cb_score': scores['cb_score'],
                'dti_score': scores['dti'],
                'relationship_score': scores['relationship'],
                'behavioral_score': scores['behavioral']
            },
            'adjustments': {
                'industry_factor': industry_risk,
                'collateral_bonus': 5 if input_data.has_collateral else 0
            }
        }

    def _score_to_grade(self, score: float) -> str:
        """점수를 등급으로 변환"""
        if score >= 95: return 'AAA'
        if score >= 90: return 'AA+'
        if score >= 85: return 'AA'
        if score >= 80: return 'AA-'
        if score >= 75: return 'A+'
        if score >= 70: return 'A'
        if score >= 65: return 'A-'
        if score >= 60: return 'BBB+'
        if score >= 55: return 'BBB'
        if score >= 50: return 'BBB-'
        if score >= 45: return 'BB+'
        if score >= 40: return 'BB'
        if score >= 35: return 'BB-'
        if score >= 30: return 'B+'
        if score >= 25: return 'B'
        if score >= 20: return 'B-'
        if score >= 15: return 'CCC'
        if score >= 10: return 'CC'
        if score >= 5: return 'C'
        return 'D'


# =============================================================================
# MDL_LGD: 부도시손실률 모형
# =============================================================================

@dataclass
class LGDInput:
    """LGD 모형 입력 데이터"""
    exposure_amount: float  # 익스포저 금액

    # 담보 정보
    collateral_type: str  # 'NONE', 'REAL_ESTATE', 'DEPOSIT', 'GUARANTEE', 'EQUIPMENT', 'INVENTORY'
    collateral_value: float = 0  # 담보 감정가
    collateral_ratio: float = 0  # 담보비율 (LTV)

    # 채무자 정보
    borrower_type: str = 'CORPORATE'  # 'CORPORATE', 'RETAIL'
    seniority: str = 'SENIOR'  # 'SENIOR', 'SUBORDINATED'

    # 산업/경기 정보
    industry_code: str = 'IND001'
    economic_cycle: str = 'NORMAL'  # 'EXPANSION', 'NORMAL', 'RECESSION'

    # 여신 정보
    facility_type: str = 'TERM_LOAN'  # 'TERM_LOAN', 'REVOLVING', 'GUARANTEE'


class LGDModel:
    """
    LGD 모형 (MDL_LGD)

    담보, 채무자 특성, 경기상황을 고려한 부도시손실률 추정
    """

    MODEL_ID = "MDL_LGD"
    MODEL_VERSION = "3.0"

    # 담보 유형별 기본 회수율
    COLLATERAL_RECOVERY_RATES = {
        'NONE': 0.25,           # 무담보: 25% 회수
        'REAL_ESTATE': 0.70,    # 부동산: 70% 회수
        'DEPOSIT': 0.95,        # 예금담보: 95% 회수
        'GUARANTEE': 0.60,      # 보증: 60% 회수
        'EQUIPMENT': 0.45,      # 기계장비: 45% 회수
        'INVENTORY': 0.35,      # 재고자산: 35% 회수
    }

    # 담보 유형별 처분비용률
    DISPOSAL_COSTS = {
        'NONE': 0.05,
        'REAL_ESTATE': 0.10,
        'DEPOSIT': 0.01,
        'GUARANTEE': 0.03,
        'EQUIPMENT': 0.15,
        'INVENTORY': 0.20,
    }

    # 경기 사이클 조정
    CYCLE_ADJUSTMENTS = {
        'EXPANSION': 0.85,   # 호황기: LGD 15% 감소
        'NORMAL': 1.00,      # 정상기
        'RECESSION': 1.25,   # 불황기: LGD 25% 증가
    }

    # 채무 순위 조정
    SENIORITY_ADJUSTMENTS = {
        'SENIOR': 1.00,
        'SUBORDINATED': 1.30,  # 후순위: LGD 30% 증가
    }

    def __init__(self):
        pass

    def calculate_lgd(self, input_data: LGDInput) -> Dict:
        """
        LGD 계산

        LGD = 1 - Recovery Rate
        Recovery Rate = (담보회수 + 무담보회수 - 처분비용) / EAD
        """
        # 1. 담보 회수액 계산
        collateral_recovery_rate = self.COLLATERAL_RECOVERY_RATES.get(
            input_data.collateral_type, 0.25
        )

        # 담보가치 대비 회수
        secured_amount = min(input_data.collateral_value, input_data.exposure_amount)
        secured_recovery = secured_amount * collateral_recovery_rate

        # 2. 무담보 부분 회수 (25% 가정)
        unsecured_amount = max(0, input_data.exposure_amount - input_data.collateral_value)
        unsecured_recovery = unsecured_amount * 0.25

        # 3. 처분비용
        disposal_cost_rate = self.DISPOSAL_COSTS.get(input_data.collateral_type, 0.05)
        disposal_costs = secured_amount * disposal_cost_rate

        # 4. 총 회수액
        total_recovery = secured_recovery + unsecured_recovery - disposal_costs

        # 5. 기본 회수율
        base_recovery_rate = total_recovery / input_data.exposure_amount if input_data.exposure_amount > 0 else 0.25
        base_recovery_rate = max(0, min(1, base_recovery_rate))

        # 6. 기본 LGD
        base_lgd = 1 - base_recovery_rate

        # 7. 경기 조정
        cycle_adj = self.CYCLE_ADJUSTMENTS.get(input_data.economic_cycle, 1.0)

        # 8. 순위 조정
        seniority_adj = self.SENIORITY_ADJUSTMENTS.get(input_data.seniority, 1.0)

        # 9. 산업 조정
        industry_risk = CorporateRatingModel.INDUSTRY_RISK.get(input_data.industry_code, 1.0)

        # 10. 최종 LGD
        final_lgd = base_lgd * cycle_adj * seniority_adj * (0.8 + 0.2 * industry_risk)
        final_lgd = max(0.05, min(0.95, final_lgd))  # 5% ~ 95% 범위

        # 11. Downturn LGD (스트레스 LGD)
        downturn_lgd = final_lgd * 1.25  # 25% 상향
        downturn_lgd = min(0.95, downturn_lgd)

        return {
            'model_id': self.MODEL_ID,
            'model_version': self.MODEL_VERSION,
            'lgd': final_lgd,
            'downturn_lgd': downturn_lgd,
            'recovery_rate': 1 - final_lgd,
            'components': {
                'secured_recovery': secured_recovery,
                'unsecured_recovery': unsecured_recovery,
                'disposal_costs': disposal_costs,
                'total_recovery': total_recovery,
                'base_lgd': base_lgd
            },
            'adjustments': {
                'cycle_factor': cycle_adj,
                'seniority_factor': seniority_adj,
                'industry_factor': industry_risk
            },
            'collateral_analysis': {
                'collateral_type': input_data.collateral_type,
                'collateral_value': input_data.collateral_value,
                'secured_portion': secured_amount / input_data.exposure_amount if input_data.exposure_amount > 0 else 0,
                'collateral_recovery_rate': collateral_recovery_rate
            }
        }


# =============================================================================
# MDL_EAD: 부도시익스포저 모형
# =============================================================================

@dataclass
class EADInput:
    """EAD 모형 입력 데이터"""
    # 약정 정보
    committed_amount: float  # 약정금액
    outstanding_amount: float  # 현재잔액 (사용액)

    # 여신 유형
    facility_type: str  # 'TERM_LOAN', 'REVOLVING', 'GUARANTEE', 'TRADE_FINANCE'

    # 거래 정보
    months_to_maturity: int = 12  # 잔여 만기 (월)
    utilization_history: List[float] = None  # 과거 사용률 추이

    # 고객 정보
    customer_rating: str = 'BBB'  # 고객 신용등급
    is_distressed: bool = False  # 부실 징후 여부


class EADModel:
    """
    EAD/CCF 모형 (MDL_EAD)

    여신 유형별 신용환산율(CCF)을 적용하여 부도시 익스포저 추정
    """

    MODEL_ID = "MDL_EAD"
    MODEL_VERSION = "3.0"

    # 여신 유형별 기본 CCF
    BASE_CCF = {
        'TERM_LOAN': 1.00,       # 확정대출: 100%
        'REVOLVING': 0.75,       # 한도대출: 75%
        'GUARANTEE': 0.50,       # 지급보증: 50%
        'TRADE_FINANCE': 0.20,   # 무역금융: 20%
        'CREDIT_CARD': 0.80,     # 신용카드: 80%
        'OVERDRAFT': 0.70,       # 당좌대출: 70%
    }

    # 등급별 CCF 조정
    RATING_CCF_ADJ = {
        'AAA': 0.90, 'AA+': 0.92, 'AA': 0.94, 'AA-': 0.96,
        'A+': 0.98, 'A': 1.00, 'A-': 1.02,
        'BBB+': 1.04, 'BBB': 1.06, 'BBB-': 1.08,
        'BB+': 1.10, 'BB': 1.12, 'BB-': 1.14,
        'B+': 1.16, 'B': 1.18, 'B-': 1.20,
    }

    def __init__(self):
        pass

    def calculate_ead(self, input_data: EADInput) -> Dict:
        """
        EAD 계산

        EAD = Outstanding + CCF × (Committed - Outstanding)
        """
        # 1. 현재 사용액
        outstanding = input_data.outstanding_amount

        # 2. 미사용 약정액
        undrawn = max(0, input_data.committed_amount - outstanding)

        # 3. 기본 CCF
        base_ccf = self.BASE_CCF.get(input_data.facility_type, 0.75)

        # 4. 등급 조정
        rating_adj = self.RATING_CCF_ADJ.get(input_data.customer_rating, 1.06)

        # 5. 만기 조정 (잔여만기가 짧을수록 CCF 낮음)
        if input_data.months_to_maturity <= 3:
            maturity_adj = 0.80
        elif input_data.months_to_maturity <= 6:
            maturity_adj = 0.90
        elif input_data.months_to_maturity <= 12:
            maturity_adj = 0.95
        else:
            maturity_adj = 1.00

        # 6. 사용률 패턴 조정
        utilization_adj = 1.0
        if input_data.utilization_history:
            avg_util = sum(input_data.utilization_history) / len(input_data.utilization_history)
            if avg_util > 0.8:  # 평균 사용률이 80% 이상이면
                utilization_adj = 1.10  # CCF 10% 상향
            elif avg_util < 0.3:  # 평균 사용률이 30% 미만이면
                utilization_adj = 0.90  # CCF 10% 하향

        # 7. 부실징후 조정
        distress_adj = 1.30 if input_data.is_distressed else 1.00

        # 8. 최종 CCF
        final_ccf = base_ccf * rating_adj * maturity_adj * utilization_adj * distress_adj
        final_ccf = max(0.10, min(1.00, final_ccf))

        # 9. EAD 계산
        ead = outstanding + final_ccf * undrawn

        # 10. 확정대출의 경우 약정액 = EAD
        if input_data.facility_type == 'TERM_LOAN':
            ead = input_data.committed_amount
            final_ccf = 1.00

        return {
            'model_id': self.MODEL_ID,
            'model_version': self.MODEL_VERSION,
            'ead': ead,
            'ccf': final_ccf,
            'components': {
                'outstanding': outstanding,
                'undrawn': undrawn,
                'committed': input_data.committed_amount,
                'undrawn_ead': final_ccf * undrawn
            },
            'adjustments': {
                'base_ccf': base_ccf,
                'rating_adj': rating_adj,
                'maturity_adj': maturity_adj,
                'utilization_adj': utilization_adj,
                'distress_adj': distress_adj
            },
            'utilization_rate': outstanding / input_data.committed_amount if input_data.committed_amount > 0 else 0
        }


# =============================================================================
# 통합 모델 인터페이스
# =============================================================================

class CreditModelService:
    """
    신용모형 서비스
    모든 모형을 통합 관리하고 호출
    """

    def __init__(self):
        self.corp_rating_model = CorporateRatingModel()
        self.retail_rating_model = RetailRatingModel()
        self.lgd_model = LGDModel()
        self.ead_model = EADModel()

    def run_corporate_rating(self, input_data: Dict) -> Dict:
        """기업신용평가 실행"""
        corp_input = CorporateRatingInput(**input_data)
        return self.corp_rating_model.calculate_score(corp_input)

    def run_retail_rating(self, input_data: Dict) -> Dict:
        """소호신용평가 실행"""
        retail_input = RetailRatingInput(**input_data)
        return self.retail_rating_model.calculate_score(retail_input)

    def run_lgd(self, input_data: Dict) -> Dict:
        """LGD 모형 실행"""
        lgd_input = LGDInput(**input_data)
        return self.lgd_model.calculate_lgd(lgd_input)

    def run_ead(self, input_data: Dict) -> Dict:
        """EAD 모형 실행"""
        ead_input = EADInput(**input_data)
        return self.ead_model.calculate_ead(ead_input)

    def run_full_assessment(
        self,
        customer_type: str,  # 'CORPORATE' or 'RETAIL'
        rating_input: Dict,
        lgd_input: Dict,
        ead_input: Dict
    ) -> Dict:
        """
        전체 신용평가 실행
        PD, LGD, EAD를 모두 산출하고 RWA/EL까지 계산
        """
        # 1. 등급/PD 산출
        if customer_type == 'CORPORATE':
            rating_result = self.run_corporate_rating(rating_input)
        else:
            rating_result = self.run_retail_rating(rating_input)

        pd = rating_result['pd']

        # 2. LGD 산출
        lgd_result = self.run_lgd(lgd_input)
        lgd = lgd_result['lgd']

        # 3. EAD 산출
        ead_result = self.run_ead(ead_input)
        ead = ead_result['ead']

        # 4. EL 계산
        el = pd * lgd * ead

        # 5. RWA 계산 (calculations.py의 함수 사용)
        from .calculations import calculate_rwa
        rwa = calculate_rwa(pd, lgd, ead)

        return {
            'rating': rating_result,
            'lgd': lgd_result,
            'ead': ead_result,
            'risk_metrics': {
                'pd': pd,
                'lgd': lgd,
                'ead': ead,
                'el': el,
                'rwa': rwa,
                'el_rate': el / ead if ead > 0 else 0,
                'rw': rwa / ead if ead > 0 else 0  # Risk Weight
            }
        }
