"""
ESG 리스크 통합 API
==================
ESG 평가, 녹색금융, 리스크 프리미엄
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from ..core.database import get_db

router = APIRouter(prefix="/api/esg", tags=["ESG Risk"])


# ============================================
# 기능 설명 (모달용)
# ============================================

FEATURE_DESCRIPTIONS = {
    "esg_overview": {
        "title": "ESG 리스크 통합",
        "description": "환경(E), 사회(S), 지배구조(G) 요소를 신용 위험 평가에 통합",
        "benefits": [
            "지속가능 금융 대응",
            "장기 신용 위험 포착",
            "규제 리스크 선제 대응"
        ],
        "methodology": """
**ESG 통합 프레임워크**

ESG 요소는 장기적으로 기업의 신용 위험에 영향을 미칩니다.

**환경 (Environmental)**
- 탄소 배출량 및 감축 목표
- 에너지 효율성
- 환경 규제 위반 이력
- 녹색 수익 비율

**사회 (Social)**
- 근로자 안전 및 복지
- 노동 관행
- 지역사회 영향
- 공급망 관리

**지배구조 (Governance)**
- 이사회 독립성
- 소유구조 투명성
- 윤리 경영 및 컴플라이언스
- 경영진 보상 구조

**신용 위험 반영**
```
Adjusted_PD = Base_PD × (1 + ESG_Premium)
```

| ESG 등급 | PD 조정 | 금리 조정 |
|---------|--------|----------|
| A | -0.2% | -10bp |
| B | -0.1% | -5bp |
| C | 0% | 0bp |
| D | +0.2% | +10bp |
| E | +0.5% | +25bp |
"""
    },
    "environmental_risk": {
        "title": "환경 리스크 (E)",
        "description": "기후 변화 및 환경 규제에 따른 신용 위험",
        "methodology": """
**환경 리스크 요소**

1. **전환 리스크 (Transition Risk)**
   - 탈탄소 정책 영향
   - 기술 변화 대응
   - 시장 선호 변화

2. **물리적 리스크 (Physical Risk)**
   - 기후 재해 노출
   - 자산 손상 위험
   - 공급망 중단

**탄소 집약도 (Carbon Intensity)**
```
Carbon_Intensity = CO2 Emission / Revenue
```

**업종별 환경 리스크**
| 업종 | 리스크 수준 | 주요 요인 |
|------|-----------|----------|
| 에너지(화석) | 매우 높음 | 전환 리스크 |
| 제조(중공업) | 높음 | 탄소 규제 |
| 부동산 | 중간 | 에너지 효율 |
| IT/서비스 | 낮음 | 간접 영향 |
""",
        "formula": "E_Score = w1×Carbon + w2×Energy_Eff + w3×Incidents + w4×Green_Revenue"
    },
    "green_finance": {
        "title": "녹색금융 (Green Finance)",
        "description": "환경 친화적 사업에 대한 우대 금융",
        "methodology": """
**녹색금융 상품 유형**

1. **녹색채권 (Green Bond)**
   - 친환경 프로젝트 자금 조달
   - 사용처 제한 및 보고 의무

2. **지속가능연계대출 (Sustainability-Linked Loan)**
   - ESG KPI 달성 시 금리 인하
   - 미달성 시 금리 인상

3. **신재생에너지 금융**
   - 태양광, 풍력 등 PF
   - 장기 안정적 현금흐름

**인센티브 구조**
| 상품 유형 | RWA 경감 | 금리 우대 |
|----------|--------|----------|
| 녹색채권 | 10-15% | 5-15bp |
| SLL (KPI 달성) | 5-10% | 5-25bp |
| 신재생에너지 | 10-20% | 10-20bp |

**KPI 예시**
- 탄소 배출 감축률
- 에너지 효율 개선률
- 재활용률 향상
"""
    }
}


@router.get("/feature-description/{feature_id}")
async def get_feature_description(feature_id: str):
    """기능 설명 조회 (모달용)"""
    if feature_id in FEATURE_DESCRIPTIONS:
        return FEATURE_DESCRIPTIONS[feature_id]
    return {"error": "Feature not found"}


@router.get("/assessments")
async def get_esg_assessments(
    esg_grade: Optional[str] = None,
    min_score: Optional[float] = None,
    industry_code: Optional[str] = None,
    region: str = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    """ESG 평가 목록"""
    region_cond = ""
    rp = {}
    if region:
        region_cond = " AND c.region = :region"
        rp["region"] = region

    query = """
        SELECT ea.assessment_id, ea.customer_id, c.customer_name, c.industry_name,
               ea.assessment_date, ea.e_score, ea.s_score, ea.g_score,
               ea.esg_score, ea.esg_grade, ea.esg_trend,
               ea.pd_adjustment, ea.pricing_adjustment_bp,
               ea.carbon_intensity, ea.green_revenue_pct
        FROM esg_assessment ea
        JOIN customer c ON ea.customer_id = c.customer_id
        WHERE 1=1
    """
    query += region_cond
    params = {**rp}

    if esg_grade:
        query += " AND ea.esg_grade = :esg_grade"
        params["esg_grade"] = esg_grade
    if min_score is not None:
        query += " AND ea.esg_score >= :min_score"
        params["min_score"] = min_score
    if industry_code:
        query += " AND c.industry_code = :industry_code"
        params["industry_code"] = industry_code

    query += " ORDER BY ea.esg_score DESC LIMIT :limit"
    params["limit"] = limit

    result = db.execute(text(query), params)

    assessments = []
    for row in result:
        assessments.append({
            "assessment_id": row[0],
            "customer_id": row[1],
            "customer_name": row[2],
            "industry_name": row[3],
            "assessment_date": row[4],
            "e_score": row[5],
            "s_score": row[6],
            "g_score": row[7],
            "esg_score": row[8],
            "esg_grade": row[9],
            "esg_trend": row[10],
            "pd_adjustment": row[11],
            "pricing_adjustment_bp": row[12],
            "carbon_intensity": row[13],
            "green_revenue_pct": row[14]
        })

    return {"assessments": assessments, "total": len(assessments)}


@router.get("/assessment/{customer_id}")
async def get_customer_esg(customer_id: str, db: Session = Depends(get_db)):
    """고객별 ESG 상세"""
    result = db.execute(text("""
        SELECT ea.*, c.customer_name, c.industry_name, c.industry_code
        FROM esg_assessment ea
        JOIN customer c ON ea.customer_id = c.customer_id
        WHERE ea.customer_id = :customer_id
    """), {"customer_id": customer_id}).fetchone()

    if not result:
        return {"error": "ESG assessment not found"}

    # 업종 평균과 비교
    industry_avg = db.execute(text("""
        SELECT AVG(ea.e_score), AVG(ea.s_score), AVG(ea.g_score), AVG(ea.esg_score)
        FROM esg_assessment ea
        JOIN customer c ON ea.customer_id = c.customer_id
        WHERE c.industry_code = :industry_code
    """), {"industry_code": result[23]}).fetchone()

    return {
        "customer": {
            "customer_id": result[1],
            "customer_name": result[21],
            "industry_name": result[22]
        },
        "assessment": {
            "assessment_date": result[2],
            "environmental": {
                "e_score": result[3],
                "carbon_intensity": result[4],
                "energy_efficiency": result[5],
                "environmental_incidents": result[6],
                "green_revenue_pct": result[7]
            },
            "social": {
                "s_score": result[8],
                "employee_safety_score": result[9],
                "labor_practices_score": result[10],
                "community_impact_score": result[11]
            },
            "governance": {
                "g_score": result[12],
                "board_independence": result[13],
                "ownership_transparency": result[14],
                "ethics_compliance_score": result[15]
            },
            "composite": {
                "esg_score": result[16],
                "esg_grade": result[17],
                "esg_trend": result[18]
            },
            "risk_impact": {
                "pd_adjustment": result[19],
                "pricing_adjustment_bp": result[20]
            }
        },
        "industry_comparison": {
            "industry_avg_e": round(industry_avg[0], 1) if industry_avg[0] else 0,
            "industry_avg_s": round(industry_avg[1], 1) if industry_avg[1] else 0,
            "industry_avg_g": round(industry_avg[2], 1) if industry_avg[2] else 0,
            "industry_avg_esg": round(industry_avg[3], 1) if industry_avg[3] else 0,
            "vs_industry_e": round(result[3] - (industry_avg[0] or 0), 1),
            "vs_industry_s": round(result[8] - (industry_avg[1] or 0), 1),
            "vs_industry_g": round(result[12] - (industry_avg[2] or 0), 1)
        }
    }


@router.get("/green-finance")
async def get_green_finance(
    green_category: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """녹색금융 상품 목록"""
    query = """
        SELECT gf.green_id, gf.facility_id, f.approved_amount, f.outstanding_amount,
               c.customer_name, c.industry_name,
               gf.green_category, gf.certification_type, gf.certification_date,
               gf.kpi_metrics_json, gf.rwa_discount_pct, gf.rate_discount_bp,
               gf.verified_by, gf.status
        FROM green_finance gf
        JOIN facility f ON gf.facility_id = f.facility_id
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE 1=1
    """
    params = {}

    if green_category:
        query += " AND gf.green_category = :green_category"
        params["green_category"] = green_category
    if status:
        query += " AND gf.status = :status"
        params["status"] = status

    query += " ORDER BY gf.certification_date DESC"

    result = db.execute(text(query), params)

    green_products = []
    for row in result:
        green_products.append({
            "green_id": row[0],
            "facility_id": row[1],
            "approved_amount": row[2],
            "outstanding_amount": row[3],
            "customer_name": row[4],
            "industry_name": row[5],
            "green_category": row[6],
            "certification_type": row[7],
            "certification_date": row[8],
            "kpi_metrics": row[9],
            "rwa_discount_pct": row[10],
            "rate_discount_bp": row[11],
            "verified_by": row[12],
            "status": row[13]
        })

    # 카테고리별 요약
    summary = db.execute(text("""
        SELECT gf.green_category, COUNT(*) as count,
               SUM(f.outstanding_amount) as total_outstanding,
               AVG(gf.rwa_discount_pct) as avg_rwa_discount
        FROM green_finance gf
        JOIN facility f ON gf.facility_id = f.facility_id
        WHERE gf.status = 'ACTIVE'
        GROUP BY gf.green_category
    """))

    by_category = []
    for row in summary:
        by_category.append({
            "category": row[0],
            "count": row[1],
            "total_outstanding": row[2],
            "avg_rwa_discount": round(row[3], 1) if row[3] else 0
        })

    return {
        "green_products": green_products,
        "total": len(green_products),
        "by_category": by_category
    }


@router.get("/grade-distribution")
async def get_esg_grade_distribution(
    region: str = Query(None),
    db: Session = Depends(get_db)
):
    """ESG 등급 분포"""
    region_cond = ""
    rp = {}
    if region:
        region_cond = " AND c.region = :region"
        rp["region"] = region

    distribution = db.execute(text("""
        SELECT ea.esg_grade, COUNT(*) as count,
               AVG(ea.esg_score) as avg_score,
               SUM(ea.pd_adjustment) / COUNT(*) as avg_pd_adj
        FROM esg_assessment ea
        JOIN customer c ON ea.customer_id = c.customer_id
        WHERE 1=1
    """ + region_cond + """
        GROUP BY ea.esg_grade
        ORDER BY ea.esg_grade
    """), rp)

    grades = []
    for row in distribution:
        grades.append({
            "grade": row[0],
            "count": row[1],
            "avg_score": round(row[2], 1) if row[2] else 0,
            "avg_pd_adjustment": round(row[3], 4) if row[3] else 0
        })

    # 업종별 평균 ESG
    by_industry = db.execute(text("""
        SELECT c.industry_name, AVG(ea.esg_score) as avg_esg,
               AVG(ea.e_score) as avg_e, AVG(ea.carbon_intensity) as avg_carbon
        FROM esg_assessment ea
        JOIN customer c ON ea.customer_id = c.customer_id
        WHERE 1=1
    """ + region_cond + """
        GROUP BY c.industry_name
        ORDER BY avg_esg DESC
        LIMIT 15
    """), rp)

    industry_ranking = []
    for row in by_industry:
        industry_ranking.append({
            "industry_name": row[0],
            "avg_esg_score": round(row[1], 1) if row[1] else 0,
            "avg_e_score": round(row[2], 1) if row[2] else 0,
            "avg_carbon_intensity": round(row[3], 1) if row[3] else 0
        })

    return {
        "grade_distribution": grades,
        "by_industry": industry_ranking
    }


@router.get("/dashboard")
async def get_esg_dashboard(
    region: str = Query(None),
    db: Session = Depends(get_db)
):
    """ESG 대시보드"""
    region_cond = ""
    rp = {}
    if region:
        region_cond = " AND c.region = :region"
        rp["region"] = region

    # 전체 요약
    summary = db.execute(text("""
        SELECT
            COUNT(*) as total_assessed,
            AVG(ea.esg_score) as avg_esg_score,
            AVG(ea.e_score) as avg_e,
            AVG(ea.s_score) as avg_s,
            AVG(ea.g_score) as avg_g,
            SUM(CASE WHEN ea.esg_grade IN ('A', 'B') THEN 1 ELSE 0 END) as high_grade_count,
            SUM(CASE WHEN ea.esg_grade IN ('D', 'E') THEN 1 ELSE 0 END) as low_grade_count
        FROM esg_assessment ea
        JOIN customer c ON ea.customer_id = c.customer_id
        WHERE 1=1
    """ + region_cond), rp).fetchone()

    # 녹색금융 요약
    green_summary = db.execute(text("""
        SELECT
            COUNT(*) as total_green,
            SUM(f.outstanding_amount) as total_green_outstanding,
            AVG(gf.rwa_discount_pct) as avg_rwa_discount
        FROM green_finance gf
        JOIN facility f ON gf.facility_id = f.facility_id
        WHERE gf.status = 'ACTIVE'
    """)).fetchone()

    # 트렌드별 분포
    trend_dist = db.execute(text("""
        SELECT ea.esg_trend, COUNT(*) as count
        FROM esg_assessment ea
        JOIN customer c ON ea.customer_id = c.customer_id
        WHERE 1=1
    """ + region_cond + """
        GROUP BY ea.esg_trend
    """), rp)

    trends = {row[0]: row[1] for row in trend_dist}

    return {
        "summary": {
            "total_assessed": summary[0],
            "avg_esg_score": round(summary[1], 1) if summary[1] else 0,
            "avg_scores": {
                "e": round(summary[2], 1) if summary[2] else 0,
                "s": round(summary[3], 1) if summary[3] else 0,
                "g": round(summary[4], 1) if summary[4] else 0
            },
            "high_grade_count": summary[5],
            "low_grade_count": summary[6]
        },
        "green_finance": {
            "total_products": green_summary[0],
            "total_outstanding": green_summary[1],
            "avg_rwa_discount": round(green_summary[2], 1) if green_summary[2] else 0
        },
        "esg_trends": trends
    }
