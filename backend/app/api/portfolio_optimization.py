"""
포트폴리오 최적화 API
====================
RAROC 최대화, RWA 최소화, 최적 배분 제안
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
import json
from ..core.database import get_db

router = APIRouter(prefix="/api/portfolio-optimization", tags=["Portfolio Optimization"])


# ============================================
# 기능 설명 (모달용)
# ============================================

FEATURE_DESCRIPTIONS = {
    "optimization_overview": {
        "title": "시나리오 기반 포트폴리오 최적화",
        "description": "수학적 최적화 기법을 활용한 최적 포트폴리오 배분 도출",
        "benefits": [
            "자본 효율성 극대화",
            "리스크 조정 수익 향상",
            "규제 제약 하 최적화"
        ],
        "methodology": """
**최적화 문제 정식화**

포트폴리오 최적화는 다음과 같은 수학적 최적화 문제로 정식화됩니다:

```
Maximize: Portfolio RAROC = Σ(RAROC_i × w_i)

Subject to:
  - Σw_i = 1 (완전 배분)
  - BIS Ratio ≥ 11% (자본 규제)
  - Industry HHI ≤ 25% (집중도 제약)
  - Single Exposure ≤ 10% (단일 차주 한도)
  - w_i ≥ 0 (공매도 불가)
```

**최적화 유형**

1. **RAROC 최대화 (RAROC_MAX)**
   - 목적: 위험 조정 수익률 극대화
   - 고수익/적정위험 자산 선호

2. **RWA 최소화 (RWA_MIN)**
   - 목적: 동일 수익 대비 자본 소요 최소화
   - 저위험 가중치 자산 선호

3. **위험 균등 배분 (RISK_PARITY)**
   - 목적: 각 자산의 위험 기여도 균등화
   - 분산 효과 극대화
"""
    },
    "efficient_frontier": {
        "title": "효율적 프론티어 (Efficient Frontier)",
        "description": "주어진 위험 수준에서 최대 수익을 달성하는 포트폴리오 집합",
        "methodology": """
**Markowitz 포트폴리오 이론**

효율적 프론티어는 위험-수익 평면에서 최적 포트폴리오들의 집합입니다.

```
E(R_p) = Σw_i × E(R_i)        (기대 수익)
σ_p² = ΣΣw_i × w_j × Cov_ij  (분산)
```

**신용 포트폴리오 적용**

| 전통 개념 | 신용 포트폴리오 |
|----------|--------------|
| 기대 수익 | RAROC |
| 분산 | Unexpected Loss |
| 공분산 | 부도 상관관계 |

**자본배분선 (CAL)**
```
RAROC_p = Rf + (E[RAROC] - Rf) / σ × σ_p
```
""",
        "formula": "Portfolio_RAROC = Σ(w_i × RAROC_i) - λ × Σ(w_i × w_j × ρ_ij × UL_i × UL_j)"
    },
    "rebalancing": {
        "title": "포트폴리오 리밸런싱",
        "description": "현재 포트폴리오를 최적 배분으로 조정하는 과정",
        "methodology": """
**리밸런싱 전략**

1. **Threshold-based**
   - 편차가 임계치 초과 시 조정
   - 장점: 불필요한 거래 최소화
   - 임계치: 보통 ±5%

2. **Calendar-based**
   - 정기적 (월/분기) 리밸런싱
   - 장점: 일관성, 예측 가능성

3. **Optimization-based**
   - 거래비용 포함 최적화
   - 장점: 거래비용 효율적

**조정 우선순위**

| 우선순위 | 기준 | 행동 |
|---------|------|------|
| 1 | 규제 위반 | 즉시 조정 |
| 2 | 전략 이탈 ≥10% | 긴급 조정 |
| 3 | 전략 이탈 ≥5% | 계획적 조정 |
| 4 | 최적 대비 편차 | 기회적 조정 |
"""
    }
}


@router.get("/feature-description/{feature_id}")
async def get_feature_description(feature_id: str):
    """기능 설명 조회 (모달용)"""
    if feature_id in FEATURE_DESCRIPTIONS:
        return FEATURE_DESCRIPTIONS[feature_id]
    return {"error": "Feature not found"}


@router.get("/optimization-runs")
async def get_optimization_runs(
    optimization_type: Optional[str] = None,
    limit: int = Query(10, le=50),
    db: Session = Depends(get_db)
):
    """최적화 실행 이력"""
    query = """
        SELECT run_id, run_date, optimization_type, objective_value,
               constraints_json, improvement_pct, status
        FROM portfolio_optimization_run
        WHERE 1=1
    """
    params = {}

    if optimization_type:
        query += " AND optimization_type = :opt_type"
        params["opt_type"] = optimization_type

    query += " ORDER BY run_date DESC LIMIT :limit"
    params["limit"] = limit

    result = db.execute(text(query), params)

    runs = []
    for row in result:
        runs.append({
            "run_id": row[0],
            "run_date": row[1],
            "optimization_type": row[2],
            "objective_value": row[3],
            "constraints": json.loads(row[4]) if row[4] else {},
            "improvement_pct": row[5],
            "status": row[6]
        })

    return {"runs": runs, "total": len(runs)}


@router.get("/optimization-result/{run_id}")
async def get_optimization_result(run_id: str, db: Session = Depends(get_db)):
    """최적화 결과 상세"""
    # 실행 정보
    run = db.execute(text("""
        SELECT run_id, run_date, optimization_type, objective_value,
               constraints_json, input_portfolio_json, optimal_portfolio_json,
               improvement_pct, status
        FROM portfolio_optimization_run
        WHERE run_id = :run_id
    """), {"run_id": run_id}).fetchone()

    if not run:
        return {"error": "Run not found"}

    # 최적 배분
    allocations = db.execute(text("""
        SELECT allocation_id, segment_type, segment_code, segment_name,
               current_exposure, optimal_exposure, change_amount, change_pct,
               current_raroc, optimal_raroc, recommendation, priority
        FROM optimal_allocation
        WHERE run_id = :run_id
        ORDER BY priority ASC
    """), {"run_id": run_id})

    allocation_list = []
    for row in allocations:
        allocation_list.append({
            "allocation_id": row[0],
            "segment_type": row[1],
            "segment_code": row[2],
            "segment_name": row[3],
            "current_exposure": row[4],
            "optimal_exposure": row[5],
            "change_amount": row[6],
            "change_pct": row[7],
            "current_raroc": row[8],
            "optimal_raroc": row[9],
            "recommendation": row[10],
            "priority": row[11]
        })

    return {
        "run_info": {
            "run_id": run[0],
            "run_date": run[1],
            "optimization_type": run[2],
            "objective_value": run[3],
            "constraints": json.loads(run[4]) if run[4] else {},
            "improvement_pct": run[7],
            "status": run[8]
        },
        "input_portfolio": json.loads(run[5]) if run[5] else {},
        "optimal_portfolio": json.loads(run[6]) if run[6] else {},
        "allocations": allocation_list
    }


@router.get("/latest-recommendations")
async def get_latest_recommendations(db: Session = Depends(get_db)):
    """최신 최적화 추천"""
    # 최신 실행
    latest_run = db.execute(text("""
        SELECT run_id, run_date, optimization_type, improvement_pct
        FROM portfolio_optimization_run
        WHERE status = 'COMPLETED'
        ORDER BY run_date DESC
        LIMIT 1
    """)).fetchone()

    if not latest_run:
        return {"error": "No optimization runs found"}

    # 조정 필요 항목 (변경률 절대값 기준 정렬)
    recommendations = db.execute(text("""
        SELECT segment_name, current_exposure, optimal_exposure,
               change_amount, change_pct, current_raroc, optimal_raroc,
               recommendation, priority
        FROM optimal_allocation
        WHERE run_id = :run_id
        AND ABS(change_pct) >= 5
        ORDER BY ABS(change_pct) DESC
    """), {"run_id": latest_run[0]})

    recs = []
    total_increase = 0
    total_decrease = 0

    for row in recommendations:
        recs.append({
            "segment_name": row[0],
            "current_exposure": row[1],
            "optimal_exposure": row[2],
            "change_amount": row[3],
            "change_pct": row[4],
            "current_raroc": row[5],
            "optimal_raroc": row[6],
            "recommendation": row[7],
            "priority": row[8]
        })

        if row[3] > 0:
            total_increase += row[3]
        else:
            total_decrease += abs(row[3])

    return {
        "run_info": {
            "run_id": latest_run[0],
            "run_date": latest_run[1],
            "optimization_type": latest_run[2],
            "improvement_pct": latest_run[3]
        },
        "recommendations": recs,
        "summary": {
            "total_segments_to_adjust": len(recs),
            "total_increase": total_increase,
            "total_decrease": total_decrease
        }
    }


@router.get("/current-vs-optimal")
async def get_current_vs_optimal(db: Session = Depends(get_db)):
    """현재 vs 최적 포트폴리오 비교"""
    # 최신 최적화 결과
    latest = db.execute(text("""
        SELECT oa.segment_name, oa.current_exposure, oa.optimal_exposure,
               oa.change_pct, oa.current_raroc, oa.optimal_raroc
        FROM optimal_allocation oa
        JOIN portfolio_optimization_run por ON oa.run_id = por.run_id
        WHERE por.status = 'COMPLETED'
        AND por.run_date = (SELECT MAX(run_date) FROM portfolio_optimization_run WHERE status = 'COMPLETED')
    """))

    comparison = []
    current_total = 0
    optimal_total = 0
    current_weighted_raroc = 0
    optimal_weighted_raroc = 0

    for row in latest:
        comparison.append({
            "segment_name": row[0],
            "current_exposure": row[1],
            "optimal_exposure": row[2],
            "change_pct": row[3],
            "current_raroc": row[4],
            "optimal_raroc": row[5]
        })
        current_total += row[1]
        optimal_total += row[2]
        if row[1] and row[4]:
            current_weighted_raroc += row[1] * row[4]
        if row[2] and row[5]:
            optimal_weighted_raroc += row[2] * row[5]

    portfolio_metrics = {
        "current": {
            "total_exposure": current_total,
            "weighted_avg_raroc": round(current_weighted_raroc / current_total, 2) if current_total else 0
        },
        "optimal": {
            "total_exposure": optimal_total,
            "weighted_avg_raroc": round(optimal_weighted_raroc / optimal_total, 2) if optimal_total else 0
        }
    }

    return {
        "comparison": comparison,
        "portfolio_metrics": portfolio_metrics,
        "improvement": {
            "raroc_change": portfolio_metrics["optimal"]["weighted_avg_raroc"] - portfolio_metrics["current"]["weighted_avg_raroc"]
        }
    }


@router.get("/constraints")
async def get_optimization_constraints(db: Session = Depends(get_db)):
    """최적화 제약조건 조회"""
    # 현재 규제/내부 한도
    limits = db.execute(text("""
        SELECT limit_type, dimension_type, limit_amount, warning_level, alert_level
        FROM limit_definition
        WHERE status = 'ACTIVE'
        LIMIT 20
    """))

    constraints = []
    for row in limits:
        constraints.append({
            "limit_type": row[0],
            "dimension_type": row[1],
            "limit_amount": row[2],
            "warning_level": row[3],
            "alert_level": row[4]
        })

    # 기본 제약조건
    default_constraints = {
        "bis_ratio_min": 0.11,  # 11%
        "cet1_ratio_min": 0.07,  # 7%
        "hhi_industry_max": 0.25,  # 25%
        "single_borrower_max": 0.10,  # 10%
        "top10_concentration_max": 0.40  # 40%
    }

    return {
        "regulatory_limits": constraints,
        "default_constraints": default_constraints
    }


@router.get("/dashboard")
async def get_optimization_dashboard(db: Session = Depends(get_db)):
    """최적화 대시보드"""
    # 최근 실행 요약
    recent_runs = db.execute(text("""
        SELECT optimization_type, improvement_pct, run_date
        FROM portfolio_optimization_run
        WHERE status = 'COMPLETED'
        ORDER BY run_date DESC
        LIMIT 5
    """))

    runs_summary = []
    for row in recent_runs:
        runs_summary.append({
            "optimization_type": row[0],
            "improvement_pct": row[1],
            "run_date": row[2]
        })

    # 현재 포트폴리오 효율성
    current_efficiency = db.execute(text("""
        SELECT AVG(current_raroc) as avg_current_raroc,
               AVG(optimal_raroc) as avg_optimal_raroc
        FROM optimal_allocation oa
        JOIN portfolio_optimization_run por ON oa.run_id = por.run_id
        WHERE por.run_date = (SELECT MAX(run_date) FROM portfolio_optimization_run)
    """)).fetchone()

    # 조정 필요 세그먼트 수
    adjustment_needed = db.execute(text("""
        SELECT COUNT(*)
        FROM optimal_allocation oa
        JOIN portfolio_optimization_run por ON oa.run_id = por.run_id
        WHERE por.run_date = (SELECT MAX(run_date) FROM portfolio_optimization_run)
        AND ABS(oa.change_pct) >= 5
    """)).scalar()

    return {
        "recent_runs": runs_summary,
        "efficiency_gap": {
            "current_avg_raroc": round(current_efficiency[0], 2) if current_efficiency[0] else 0,
            "optimal_avg_raroc": round(current_efficiency[1], 2) if current_efficiency[1] else 0,
            "improvement_potential": round((current_efficiency[1] or 0) - (current_efficiency[0] or 0), 2)
        },
        "segments_needing_adjustment": adjustment_needed or 0
    }
