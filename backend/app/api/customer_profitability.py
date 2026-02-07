"""
고객 관계 기반 수익성 (RBC) API
================================
고객 생애가치, 종합 수익성, Cross-sell 기회 분석
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from ..core.database import get_db

router = APIRouter(prefix="/api/customer-profitability", tags=["Customer Profitability"])


# ============================================
# 기능 설명 (모달용)
# ============================================

FEATURE_DESCRIPTIONS = {
    "rbc_overview": {
        "title": "고객 관계 기반 수익성 (RBC: Relationship-Based Costing)",
        "description": "건별 수익성을 넘어 고객과의 전체 거래 관계에서 발생하는 종합 수익을 분석",
        "benefits": [
            "전략적 고객 식별 및 우선순위화",
            "고객별 맞춤 가격/서비스 전략",
            "이탈 방지 및 관계 강화"
        ],
        "methodology": """
**RBC 분석 프레임워크**

전통적인 건별 수익성 분석의 한계를 극복하고, 고객과의 종합적인 관계 가치를 측정합니다.

**수익 구성 요소**

1. **여신 수익 (Loan Revenue)**
   - 이자 수익
   - 수수료 수익
   - (-) 자금 조달 비용
   - (-) 예상 손실 (EL)
   - (-) 자본 비용 (Economic Capital × Hurdle Rate)

2. **수신 수익 (Deposit Revenue)**
   - FTP 스프레드 수익
   - (-) 운영 비용

3. **수수료 수익 (Fee Revenue)**
   - 송금, 보증, 자문 등

4. **외환/파생 수익 (FX/Derivatives)**
   - 환전 마진
   - 파생상품 수익

**종합 RAROC**
```
Customer RAROC = (Total Profit) / (Total Economic Capital)
```
"""
    },
    "clv": {
        "title": "고객 생애가치 (CLV: Customer Lifetime Value)",
        "description": "고객과의 전체 거래 기간 동안 예상되는 순현재가치",
        "methodology": """
**CLV 산출 모형**

```
CLV = Σ(Expected_Profit_t × Retention_Prob_t) / (1 + r)^t
```

**구성 요소**

| 요소 | 설명 | 산출 방식 |
|------|------|----------|
| Expected Profit | 기대 이익 | 현재 수익 × 성장률 |
| Retention Probability | 유지 확률 | 이탈 예측 모형 |
| Discount Rate | 할인율 | 자기자본비용 |
| Time Horizon | 예측 기간 | 5-10년 |

**CLV 점수 해석**
- 80-100: 핵심 전략 고객 (VIP 관리)
- 60-79: 성장 잠재 고객 (확대 전략)
- 40-59: 유지 고객 (효율적 관리)
- 0-39: 재평가 필요 고객 (구조조정 검토)
""",
        "formula": "CLV = Σ(Profit_t × Retention^t) / (1+r)^t"
    },
    "cross_sell": {
        "title": "Cross-sell 기회 분석",
        "description": "기존 고객에게 추가 상품을 판매할 기회를 식별하고 우선순위화",
        "methodology": """
**Cross-sell 확률 모형**

고객의 특성과 거래 패턴을 기반으로 추가 상품 구매 확률을 예측합니다.

**예측 변수**
- 현재 보유 상품 구성
- 거래 규모 및 빈도
- 업종 및 규모
- 유사 고객 패턴

**우선순위 점수**
```
Priority = Probability × Expected_Revenue × Margin
```

**활용 방안**
1. RM에게 타겟 고객 및 상품 추천
2. 캠페인 대상 선정
3. 가격 협상 시 번들 오퍼 제안
"""
    },
    "churn_prediction": {
        "title": "이탈 예측 (Churn Prediction)",
        "description": "고객 이탈 위험을 사전에 예측하여 선제적 관계 관리",
        "methodology": """
**이탈 예측 지표**

| 지표 | 설명 | 이탈 신호 |
|------|------|----------|
| 거래 빈도 변화 | 최근 6개월 추이 | 감소 |
| 잔액 변동 | 예금/대출 잔액 추이 | 급감 |
| 채널 이용 | 모바일/인터넷 뱅킹 | 감소 |
| 민원/불만 | 최근 접촉 기록 | 증가 |
| 경쟁사 접촉 | 외부 정보 | 포착 시 고위험 |

**Churn Risk Score**
```
Churn_Risk = 1 - Retention_Probability
```

- 0.0-0.2: 안정
- 0.2-0.4: 관심 필요
- 0.4-0.6: 경고
- 0.6+: 즉시 조치
"""
    }
}


@router.get("/feature-description/{feature_id}")
async def get_feature_description(feature_id: str):
    """기능 설명 조회 (모달용)"""
    if feature_id in FEATURE_DESCRIPTIONS:
        return FEATURE_DESCRIPTIONS[feature_id]
    return {"error": "Feature not found"}


@router.get("/rankings")
async def get_profitability_rankings(
    sort_by: str = Query("total_profit", description="정렬 기준: total_profit, raroc, clv_score"),
    limit: int = Query(50, le=200),
    min_raroc: Optional[float] = None,
    region: str = Query(None),
    db: Session = Depends(get_db)
):
    """고객 수익성 순위"""
    valid_sorts = ["total_profit", "raroc", "clv_score", "total_revenue", "churn_risk_score"]
    if sort_by not in valid_sorts:
        sort_by = "total_profit"

    region_cond = ""
    rp = {}
    if region:
        region_cond = " AND c.region = :region"
        rp["region"] = region

    query = f"""
        SELECT cp.customer_id, c.customer_name, c.industry_name, c.size_category,
               cp.total_revenue, cp.total_cost, cp.total_profit,
               cp.loan_profit, cp.deposit_profit, cp.fee_profit, cp.fx_profit,
               cp.economic_capital, cp.raroc,
               cp.clv_score, cp.retention_probability, cp.cross_sell_potential, cp.churn_risk_score
        FROM customer_profitability cp
        JOIN customer c ON cp.customer_id = c.customer_id
        WHERE 1=1{region_cond}
    """
    params = {**rp}

    if min_raroc is not None:
        query += " AND cp.raroc >= :min_raroc"
        params["min_raroc"] = min_raroc

    query += f" ORDER BY cp.{sort_by} DESC LIMIT :limit"
    params["limit"] = limit

    result = db.execute(text(query), params)

    rankings = []
    for i, row in enumerate(result, 1):
        rankings.append({
            "rank": i,
            "customer_id": row[0],
            "customer_name": row[1],
            "industry_name": row[2],
            "size_category": row[3],
            "total_revenue": row[4],
            "total_cost": row[5],
            "total_profit": row[6],
            "profit_breakdown": {
                "loan": row[7],
                "deposit": row[8],
                "fee": row[9],
                "fx": row[10]
            },
            "economic_capital": row[11],
            "raroc": row[12],
            "clv_score": row[13],
            "retention_probability": row[14],
            "cross_sell_potential": row[15],
            "churn_risk_score": row[16]
        })

    return {"rankings": rankings, "total": len(rankings), "sort_by": sort_by}


@router.get("/customer/{customer_id}")
async def get_customer_profitability(customer_id: str, db: Session = Depends(get_db)):
    """고객 상세 수익성 분석"""
    result = db.execute(text("""
        SELECT cp.*, c.customer_name, c.industry_name, c.size_category,
               c.revenue_size, c.asset_size
        FROM customer_profitability cp
        JOIN customer c ON cp.customer_id = c.customer_id
        WHERE cp.customer_id = :customer_id
    """), {"customer_id": customer_id}).fetchone()

    if not result:
        return {"error": "Customer not found"}

    # Cross-sell 기회 조회
    cross_sell = db.execute(text("""
        SELECT product_type, probability, expected_revenue, priority_score, status
        FROM cross_sell_opportunity
        WHERE customer_id = :customer_id
        ORDER BY priority_score DESC
    """), {"customer_id": customer_id})

    opportunities = []
    for row in cross_sell:
        opportunities.append({
            "product_type": row[0],
            "probability": row[1],
            "expected_revenue": row[2],
            "priority_score": row[3],
            "status": row[4]
        })

    return {
        "customer_info": {
            "customer_id": result[1],
            "customer_name": result[27],
            "industry_name": result[28],
            "size_category": result[29],
            "revenue_size": result[30],
            "asset_size": result[31]
        },
        "profitability": {
            "calculation_date": result[2],
            "loan": {
                "revenue": result[3],
                "cost": result[4],
                "el": result[5],
                "capital_cost": result[6],
                "profit": result[7]
            },
            "deposit": {
                "revenue": result[8],
                "cost": result[9],
                "profit": result[10]
            },
            "fee": {
                "revenue": result[11],
                "cost": result[12],
                "profit": result[13]
            },
            "fx": {
                "revenue": result[14],
                "cost": result[15],
                "profit": result[16]
            },
            "total": {
                "revenue": result[17],
                "cost": result[18],
                "profit": result[19]
            },
            "economic_capital": result[20],
            "raroc": result[21]
        },
        "lifecycle_metrics": {
            "clv_score": result[22],
            "retention_probability": result[23],
            "cross_sell_potential": result[24],
            "churn_risk_score": result[25]
        },
        "cross_sell_opportunities": opportunities
    }


@router.get("/cross-sell-opportunities")
async def get_cross_sell_opportunities(
    status: Optional[str] = None,
    product_type: Optional[str] = None,
    min_probability: Optional[float] = None,
    region: str = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    """Cross-sell 기회 목록"""
    region_cond = ""
    rp = {}
    if region:
        region_cond = " AND c.region = :region"
        rp["region"] = region

    query = f"""
        SELECT cso.opportunity_id, cso.customer_id, c.customer_name, c.industry_name,
               cso.product_type, cso.probability, cso.expected_revenue,
               cso.priority_score, cso.status, cso.assigned_rm,
               cp.total_profit, cp.raroc
        FROM cross_sell_opportunity cso
        JOIN customer c ON cso.customer_id = c.customer_id
        LEFT JOIN customer_profitability cp ON cso.customer_id = cp.customer_id
        WHERE 1=1{region_cond}
    """
    params = {**rp}

    if status:
        query += " AND cso.status = :status"
        params["status"] = status
    if product_type:
        query += " AND cso.product_type = :product_type"
        params["product_type"] = product_type
    if min_probability is not None:
        query += " AND cso.probability >= :min_probability"
        params["min_probability"] = min_probability

    query += " ORDER BY cso.priority_score DESC LIMIT :limit"
    params["limit"] = limit

    result = db.execute(text(query), params)

    opportunities = []
    for row in result:
        opportunities.append({
            "opportunity_id": row[0],
            "customer_id": row[1],
            "customer_name": row[2],
            "industry_name": row[3],
            "product_type": row[4],
            "probability": row[5],
            "expected_revenue": row[6],
            "priority_score": row[7],
            "status": row[8],
            "assigned_rm": row[9],
            "customer_total_profit": row[10],
            "customer_raroc": row[11]
        })

    # 상품별 요약
    product_summary = db.execute(text("""
        SELECT product_type, COUNT(*) as count,
               AVG(probability) as avg_prob,
               SUM(expected_revenue) as total_expected_revenue
        FROM cross_sell_opportunity
        GROUP BY product_type
        ORDER BY total_expected_revenue DESC
    """))

    summary_by_product = []
    for row in product_summary:
        summary_by_product.append({
            "product_type": row[0],
            "count": row[1],
            "avg_probability": round(row[2], 2) if row[2] else 0,
            "total_expected_revenue": row[3]
        })

    return {
        "opportunities": opportunities,
        "total": len(opportunities),
        "summary_by_product": summary_by_product
    }


@router.get("/churn-risk")
async def get_churn_risk_customers(
    min_risk: float = Query(0.3, description="최소 이탈 위험 점수"),
    region: str = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """이탈 위험 고객 목록"""
    region_cond = ""
    rp = {}
    if region:
        region_cond = " AND c.region = :region"
        rp["region"] = region

    result = db.execute(text(f"""
        SELECT cp.customer_id, c.customer_name, c.industry_name,
               cp.total_profit, cp.raroc, cp.clv_score,
               cp.retention_probability, cp.churn_risk_score
        FROM customer_profitability cp
        JOIN customer c ON cp.customer_id = c.customer_id
        WHERE cp.churn_risk_score >= :min_risk{region_cond}
        ORDER BY cp.churn_risk_score DESC
        LIMIT :limit
    """), {"min_risk": min_risk, "limit": limit, **rp})

    at_risk_customers = []
    for row in result:
        # 이탈 시 손실 추정
        potential_loss = row[3] * 5  # 5년 이익 기준

        at_risk_customers.append({
            "customer_id": row[0],
            "customer_name": row[1],
            "industry_name": row[2],
            "total_profit": row[3],
            "raroc": row[4],
            "clv_score": row[5],
            "retention_probability": row[6],
            "churn_risk_score": row[7],
            "potential_loss": round(potential_loss, 0),
            "risk_level": "CRITICAL" if row[7] >= 0.6 else "HIGH" if row[7] >= 0.4 else "MEDIUM"
        })

    return {
        "at_risk_customers": at_risk_customers,
        "total": len(at_risk_customers),
        "total_potential_loss": sum(c["potential_loss"] for c in at_risk_customers)
    }


@router.get("/dashboard")
async def get_profitability_dashboard(
    region: str = Query(None),
    db: Session = Depends(get_db)
):
    """수익성 대시보드"""
    region_cond = ""
    rp = {}
    if region:
        region_cond = " AND c.region = :region"
        rp["region"] = region

    # 전체 요약
    summary = db.execute(text(f"""
        SELECT
            COUNT(DISTINCT cp.customer_id) as customer_count,
            SUM(cp.total_revenue) as total_revenue,
            SUM(cp.total_profit) as total_profit,
            AVG(cp.raroc) as avg_raroc,
            AVG(cp.clv_score) as avg_clv,
            SUM(CASE WHEN cp.churn_risk_score >= 0.4 THEN 1 ELSE 0 END) as high_churn_count
        FROM customer_profitability cp
        JOIN customer c ON cp.customer_id = c.customer_id
        WHERE 1=1{region_cond}
    """), rp).fetchone()

    # 규모별 수익성
    by_size = db.execute(text(f"""
        SELECT c.size_category,
               COUNT(DISTINCT cp.customer_id) as count,
               SUM(cp.total_profit) as total_profit,
               AVG(cp.raroc) as avg_raroc
        FROM customer_profitability cp
        JOIN customer c ON cp.customer_id = c.customer_id
        WHERE 1=1{region_cond}
        GROUP BY c.size_category
    """), rp)

    size_breakdown = []
    for row in by_size:
        size_breakdown.append({
            "size_category": row[0],
            "count": row[1],
            "total_profit": row[2],
            "avg_raroc": round(row[3], 2) if row[3] else 0
        })

    # Top 10 고객
    top_customers = db.execute(text(f"""
        SELECT c.customer_name, cp.total_profit, cp.raroc
        FROM customer_profitability cp
        JOIN customer c ON cp.customer_id = c.customer_id
        WHERE 1=1{region_cond}
        ORDER BY cp.total_profit DESC
        LIMIT 10
    """), rp)

    top_10 = []
    for row in top_customers:
        top_10.append({
            "customer_name": row[0],
            "total_profit": row[1],
            "raroc": round(row[2], 2) if row[2] else 0
        })

    return {
        "summary": {
            "customer_count": summary[0],
            "total_revenue": summary[1],
            "total_profit": summary[2],
            "avg_raroc": round(summary[3], 2) if summary[3] else 0,
            "avg_clv_score": round(summary[4], 1) if summary[4] else 0,
            "high_churn_risk_count": summary[5]
        },
        "by_size_category": size_breakdown,
        "top_10_customers": top_10
    }
