"""
모델 추론 API
신용평가 모형 실행 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..core.database import get_db
from ..services.credit_models import (
    CreditModelService,
    CorporateRatingInput,
    RetailRatingInput,
    LGDInput,
    EADInput
)

router = APIRouter(prefix="/api/models/inference", tags=["Model Inference"])

# 모델 서비스 인스턴스
model_service = CreditModelService()


# =============================================================================
# 요청/응답 스키마
# =============================================================================

class CorporateRatingRequest(BaseModel):
    """기업신용평가 요청"""
    # 재무 정보
    total_assets: float = Field(..., description="총자산 (원)")
    total_liabilities: float = Field(..., description="총부채 (원)")
    total_equity: float = Field(..., description="자기자본 (원)")
    sales: float = Field(..., description="매출액 (원)")
    operating_income: float = Field(..., description="영업이익 (원)")
    net_income: float = Field(..., description="당기순이익 (원)")
    ebitda: float = Field(..., description="EBITDA (원)")
    interest_expense: float = Field(default=0, description="이자비용 (원)")
    current_assets: float = Field(..., description="유동자산 (원)")
    current_liabilities: float = Field(..., description="유동부채 (원)")
    cash_and_equivalents: float = Field(default=0, description="현금성자산 (원)")

    # 비재무 정보
    years_in_business: int = Field(..., description="업력 (년)")
    industry_code: str = Field(..., description="산업코드")
    is_listed: bool = Field(default=False, description="상장 여부")
    has_external_audit: bool = Field(default=True, description="외부감사 여부")
    ceo_experience_years: int = Field(default=10, description="대표이사 경력 (년)")

    # 거래 정보
    months_with_bank: int = Field(default=12, description="거래기간 (월)")
    overdraft_count_12m: int = Field(default=0, description="최근 12개월 연체횟수")
    max_overdraft_days: int = Field(default=0, description="최장 연체일수")


class RetailRatingRequest(BaseModel):
    """소호신용평가 요청"""
    business_type: str = Field(..., description="사업자 유형 (INDIVIDUAL/CORPORATION)")
    annual_sales: float = Field(..., description="연매출 (원)")
    years_in_business: int = Field(..., description="업력 (년)")
    industry_code: str = Field(..., description="산업코드")
    employee_count: int = Field(default=1, description="종업원 수")

    owner_age: int = Field(default=45, description="대표자 나이")
    owner_credit_score: int = Field(..., description="대표자 개인신용점수")

    total_debt: float = Field(default=0, description="총 부채")
    monthly_income: float = Field(default=0, description="월 소득")

    months_with_bank: int = Field(default=12, description="거래기간 (월)")
    average_balance: float = Field(default=0, description="평균잔액")
    overdraft_count_12m: int = Field(default=0, description="최근 12개월 연체횟수")
    max_overdraft_days: int = Field(default=0, description="최장 연체일수")

    has_collateral: bool = Field(default=False, description="담보 여부")
    collateral_value: float = Field(default=0, description="담보 가치")


class LGDRequest(BaseModel):
    """LGD 모형 요청"""
    exposure_amount: float = Field(..., description="익스포저 금액")
    collateral_type: str = Field(default="NONE", description="담보 유형")
    collateral_value: float = Field(default=0, description="담보 감정가")
    collateral_ratio: float = Field(default=0, description="담보비율 (LTV)")
    borrower_type: str = Field(default="CORPORATE", description="채무자 유형")
    seniority: str = Field(default="SENIOR", description="채무 순위")
    industry_code: str = Field(default="IND001", description="산업코드")
    economic_cycle: str = Field(default="NORMAL", description="경기 사이클")
    facility_type: str = Field(default="TERM_LOAN", description="여신 유형")


class EADRequest(BaseModel):
    """EAD 모형 요청"""
    committed_amount: float = Field(..., description="약정금액")
    outstanding_amount: float = Field(..., description="현재잔액")
    facility_type: str = Field(default="TERM_LOAN", description="여신 유형")
    months_to_maturity: int = Field(default=12, description="잔여 만기 (월)")
    utilization_history: Optional[List[float]] = Field(default=None, description="과거 사용률")
    customer_rating: str = Field(default="BBB", description="고객 신용등급")
    is_distressed: bool = Field(default=False, description="부실 징후 여부")


class FullAssessmentRequest(BaseModel):
    """전체 신용평가 요청"""
    customer_type: str = Field(..., description="고객 유형 (CORPORATE/RETAIL)")
    rating_input: Dict[str, Any] = Field(..., description="등급평가 입력")
    lgd_input: Dict[str, Any] = Field(..., description="LGD 입력")
    ead_input: Dict[str, Any] = Field(..., description="EAD 입력")


# =============================================================================
# API 엔드포인트
# =============================================================================

@router.post("/corporate-rating")
def run_corporate_rating(request: CorporateRatingRequest):
    """
    기업신용평가 모형 실행 (MDL_CORP_RATING)

    재무비율, 비재무 요소, 행동 데이터를 분석하여 신용등급 및 PD 산출
    """
    try:
        result = model_service.run_corporate_rating(request.dict())
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/retail-rating")
def run_retail_rating(request: RetailRatingRequest):
    """
    소호신용평가 모형 실행 (MDL_RETAIL_RATING)

    개인사업자/소호 고객의 신용도 평가
    """
    try:
        result = model_service.run_retail_rating(request.dict())
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/lgd")
def run_lgd_model(request: LGDRequest):
    """
    LGD 모형 실행 (MDL_LGD)

    담보, 채무자 특성, 경기상황을 고려한 부도시손실률 추정
    """
    try:
        result = model_service.run_lgd(request.dict())
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ead")
def run_ead_model(request: EADRequest):
    """
    EAD/CCF 모형 실행 (MDL_EAD)

    여신 유형별 신용환산율(CCF)을 적용하여 부도시 익스포저 추정
    """
    try:
        result = model_service.run_ead(request.dict())
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/full-assessment")
def run_full_assessment(request: FullAssessmentRequest):
    """
    전체 신용평가 실행

    PD, LGD, EAD를 모두 산출하고 RWA/EL까지 계산
    """
    try:
        result = model_service.run_full_assessment(
            customer_type=request.customer_type,
            rating_input=request.rating_input,
            lgd_input=request.lgd_input,
            ead_input=request.ead_input
        )
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sample-inputs")
def get_sample_inputs():
    """
    모형별 샘플 입력 데이터 제공
    """
    return {
        "corporate_rating": {
            "total_assets": 100_000_000_000,
            "total_liabilities": 60_000_000_000,
            "total_equity": 40_000_000_000,
            "sales": 80_000_000_000,
            "operating_income": 8_000_000_000,
            "net_income": 5_000_000_000,
            "ebitda": 12_000_000_000,
            "interest_expense": 2_000_000_000,
            "current_assets": 30_000_000_000,
            "current_liabilities": 20_000_000_000,
            "cash_and_equivalents": 10_000_000_000,
            "years_in_business": 15,
            "industry_code": "IND001",
            "is_listed": True,
            "has_external_audit": True,
            "ceo_experience_years": 20,
            "months_with_bank": 60,
            "overdraft_count_12m": 0,
            "max_overdraft_days": 0
        },
        "retail_rating": {
            "business_type": "INDIVIDUAL",
            "annual_sales": 500_000_000,
            "years_in_business": 8,
            "industry_code": "IND002",
            "employee_count": 5,
            "owner_age": 45,
            "owner_credit_score": 750,
            "total_debt": 100_000_000,
            "monthly_income": 10_000_000,
            "months_with_bank": 36,
            "average_balance": 50_000_000,
            "overdraft_count_12m": 0,
            "max_overdraft_days": 0,
            "has_collateral": True,
            "collateral_value": 200_000_000
        },
        "lgd": {
            "exposure_amount": 10_000_000_000,
            "collateral_type": "REAL_ESTATE",
            "collateral_value": 8_000_000_000,
            "collateral_ratio": 0.8,
            "borrower_type": "CORPORATE",
            "seniority": "SENIOR",
            "industry_code": "IND001",
            "economic_cycle": "NORMAL",
            "facility_type": "TERM_LOAN"
        },
        "ead": {
            "committed_amount": 10_000_000_000,
            "outstanding_amount": 7_000_000_000,
            "facility_type": "REVOLVING",
            "months_to_maturity": 12,
            "utilization_history": [0.6, 0.65, 0.7, 0.68, 0.72, 0.7],
            "customer_rating": "BBB",
            "is_distressed": False
        }
    }


@router.get("/model-info/{model_id}")
def get_model_info(model_id: str, db: Session = Depends(get_db)):
    """
    모형 상세 정보 조회
    """
    model_info = {
        "MDL_CORP_RATING": {
            "model_id": "MDL_CORP_RATING",
            "model_name": "기업신용평가모형",
            "description": "재무비율 분석 + 비재무 요소 + 행동 데이터를 종합하여 신용등급 및 부도확률(PD)을 산출하는 로지스틱 회귀 기반 모형",
            "version": "3.0",
            "methodology": "Logistic Regression + Scorecard Hybrid",
            "input_variables": [
                {"name": "debt_ratio", "type": "Financial", "description": "부채비율"},
                {"name": "current_ratio", "type": "Financial", "description": "유동비율"},
                {"name": "interest_coverage", "type": "Financial", "description": "이자보상배율"},
                {"name": "roa", "type": "Financial", "description": "총자산이익률"},
                {"name": "roe", "type": "Financial", "description": "자기자본이익률"},
                {"name": "operating_margin", "type": "Financial", "description": "영업이익률"},
                {"name": "years_in_business", "type": "Non-Financial", "description": "업력"},
                {"name": "is_listed", "type": "Non-Financial", "description": "상장여부"},
                {"name": "overdraft_count", "type": "Behavioral", "description": "연체횟수"}
            ],
            "output_variables": [
                {"name": "grade", "description": "신용등급 (AAA ~ D)"},
                {"name": "pd", "description": "부도확률 (TTC)"},
                {"name": "pit_pd", "description": "부도확률 (PIT)"},
                {"name": "score_1000", "description": "신용점수 (1000점 만점)"}
            ],
            "validation_metrics": {
                "gini": 0.48,
                "ks": 0.38,
                "auroc": 0.74
            }
        },
        "MDL_RETAIL_RATING": {
            "model_id": "MDL_RETAIL_RATING",
            "model_name": "소호신용평가모형",
            "description": "개인사업자/소호 고객의 신용도를 평가하는 스코어카드 모형",
            "version": "3.0",
            "methodology": "Scorecard",
            "input_variables": [
                {"name": "annual_sales", "type": "Financial", "description": "연매출액"},
                {"name": "years_in_business", "type": "Non-Financial", "description": "업력"},
                {"name": "owner_credit_score", "type": "CB", "description": "대표자 CB점수"},
                {"name": "dti", "type": "Financial", "description": "부채비율"},
                {"name": "relationship_length", "type": "Behavioral", "description": "거래기간"},
                {"name": "overdraft_history", "type": "Behavioral", "description": "연체이력"}
            ],
            "output_variables": [
                {"name": "grade", "description": "신용등급"},
                {"name": "pd", "description": "부도확률"},
                {"name": "score_100", "description": "신용점수 (100점 만점)"}
            ],
            "validation_metrics": {
                "gini": 0.47,
                "ks": 0.36,
                "auroc": 0.73
            }
        },
        "MDL_LGD": {
            "model_id": "MDL_LGD",
            "model_name": "LGD 모형",
            "description": "담보, 채무자 특성, 경기상황을 고려한 부도시손실률 추정",
            "version": "3.0",
            "methodology": "Workout LGD + Downturn Adjustment",
            "input_variables": [
                {"name": "collateral_type", "type": "Collateral", "description": "담보유형"},
                {"name": "collateral_value", "type": "Collateral", "description": "담보가치"},
                {"name": "seniority", "type": "Facility", "description": "채무순위"},
                {"name": "economic_cycle", "type": "Macro", "description": "경기사이클"}
            ],
            "output_variables": [
                {"name": "lgd", "description": "부도시손실률"},
                {"name": "downturn_lgd", "description": "스트레스 LGD"},
                {"name": "recovery_rate", "description": "회수율"}
            ],
            "validation_metrics": {
                "rmse": 0.12,
                "mae": 0.09
            }
        },
        "MDL_EAD": {
            "model_id": "MDL_EAD",
            "model_name": "EAD/CCF 모형",
            "description": "여신 유형별 신용환산율(CCF)을 적용하여 부도시 익스포저 추정",
            "version": "3.0",
            "methodology": "CCF Regression",
            "input_variables": [
                {"name": "committed_amount", "type": "Facility", "description": "약정금액"},
                {"name": "outstanding_amount", "type": "Facility", "description": "사용금액"},
                {"name": "facility_type", "type": "Facility", "description": "여신유형"},
                {"name": "customer_rating", "type": "Rating", "description": "고객등급"},
                {"name": "months_to_maturity", "type": "Facility", "description": "잔여만기"}
            ],
            "output_variables": [
                {"name": "ead", "description": "부도시익스포저"},
                {"name": "ccf", "description": "신용환산율"}
            ],
            "validation_metrics": {
                "rmse": 0.08,
                "mae": 0.06
            }
        }
    }

    if model_id not in model_info:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    return model_info[model_id]


@router.post("/batch-rating")
def run_batch_rating(
    customer_ids: List[str],
    db: Session = Depends(get_db)
):
    """
    배치 신용평가 실행

    여러 고객에 대해 한번에 신용평가 수행
    """
    results = []

    for customer_id in customer_ids[:10]:  # 최대 10건
        # 고객 정보 조회
        customer = db.execute(text("""
            SELECT c.customer_id, c.customer_name, c.industry_code,
                   c.total_assets, c.total_liabilities, c.total_equity,
                   c.sales, c.operating_income, c.net_income,
                   c.years_in_business, c.is_listed
            FROM customer c
            WHERE c.customer_id = :cid
        """), {"cid": customer_id}).fetchone()

        if customer:
            try:
                # 간이 입력 데이터 구성
                input_data = {
                    "total_assets": float(customer[3]) if customer[3] else 100_000_000_000,
                    "total_liabilities": float(customer[4]) if customer[4] else 60_000_000_000,
                    "total_equity": float(customer[5]) if customer[5] else 40_000_000_000,
                    "sales": float(customer[6]) if customer[6] else 80_000_000_000,
                    "operating_income": float(customer[7]) if customer[7] else 8_000_000_000,
                    "net_income": float(customer[8]) if customer[8] else 5_000_000_000,
                    "ebitda": float(customer[7]) * 1.5 if customer[7] else 12_000_000_000,
                    "interest_expense": float(customer[4]) * 0.03 if customer[4] else 2_000_000_000,
                    "current_assets": float(customer[3]) * 0.3 if customer[3] else 30_000_000_000,
                    "current_liabilities": float(customer[4]) * 0.4 if customer[4] else 20_000_000_000,
                    "cash_and_equivalents": float(customer[3]) * 0.1 if customer[3] else 10_000_000_000,
                    "years_in_business": int(customer[9]) if customer[9] else 10,
                    "industry_code": customer[2] or "IND001",
                    "is_listed": bool(customer[10]) if customer[10] else False,
                    "has_external_audit": True,
                    "ceo_experience_years": 15,
                    "months_with_bank": 36,
                    "overdraft_count_12m": 0,
                    "max_overdraft_days": 0
                }

                result = model_service.run_corporate_rating(input_data)
                results.append({
                    "customer_id": customer_id,
                    "customer_name": customer[1],
                    "success": True,
                    "grade": result['grade'],
                    "pd": result['pd'],
                    "score": result['score_1000']
                })
            except Exception as e:
                results.append({
                    "customer_id": customer_id,
                    "customer_name": customer[1] if customer else "Unknown",
                    "success": False,
                    "error": str(e)
                })
        else:
            results.append({
                "customer_id": customer_id,
                "success": False,
                "error": "Customer not found"
            })

    return {
        "total_requested": len(customer_ids),
        "total_processed": len(results),
        "results": results
    }
