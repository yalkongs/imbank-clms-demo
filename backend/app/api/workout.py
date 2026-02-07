"""
Workout 관리 API
================
부실채권 회수 관리, 시나리오 분석, 채무조정
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from ..core.database import get_db

router = APIRouter(prefix="/api/workout", tags=["Workout Management"])


# ============================================
# 기능 설명 (모달용)
# ============================================

FEATURE_DESCRIPTIONS = {
    "workout_overview": {
        "title": "Workout 관리",
        "description": "부실채권의 체계적 회수 관리 및 손실 최소화",
        "benefits": [
            "회수율 극대화",
            "손실 인식 시점 최적화",
            "LGD 추정 정확도 향상"
        ],
        "methodology": """
**Workout 프로세스**

```
부실 인지 → 전략 수립 → 시나리오 분석 → 실행 → 회수 → 종결
```

**전략 유형**

1. **정상화 (Normalization)**
   - 일시적 유동성 위기
   - 회생 가능성 높음
   - 금리 유예, 일부 감면

2. **채무조정 (Restructuring)**
   - 원금/이자 감면
   - 만기 연장
   - 출자전환

3. **자산매각 (Asset Sale)**
   - 담보 처분
   - NPL 매각
   - 사업부 분리 매각

4. **법적 회수 (Legal Recovery)**
   - 강제집행
   - 파산/회생 절차
   - 소송

5. **대손상각 (Write-off)**
   - 회수 불능 판단
   - 세무/회계 처리
"""
    },
    "recovery_scenario": {
        "title": "회수 시나리오 분석",
        "description": "다양한 회수 전략별 NPV 및 IRR 비교 분석",
        "methodology": """
**시나리오 비교 프레임워크**

각 회수 전략에 대해 현금흐름 기반 NPV를 산출합니다.

```
NPV = Σ(CF_t / (1+r)^t) - Initial_Exposure
```

| 항목 | 정상화 | 채무조정 | 매각 | 법적회수 |
|------|-------|---------|------|---------|
| 회수율 | 80-95% | 50-70% | 40-60% | 30-50% |
| 기간 | 1-3년 | 2-5년 | 6-18개월 | 3-5년 |
| 비용 | 낮음 | 중간 | 중간 | 높음 |

**Expected Value 산출**
```
EV = Σ(Probability_i × NPV_i)
```

**의사결정 기준**
- NPV 최대화
- 회수 확실성
- 기회비용 고려
- 평판 리스크
""",
        "formula": "NPV = Σ(Recovery_CF_t / (1+r)^t) - Legal_Cost - Admin_Cost"
    },
    "debt_restructuring": {
        "title": "채무조정 (Debt Restructuring)",
        "description": "원리금 조건 변경을 통한 채무 정상화",
        "methodology": """
**채무조정 유형**

1. **금리 감면 (Interest Reduction)**
   - 현재 금리 → 인하 금리
   - NPV 손실 = (기존이자 - 신규이자) × 잔존기간

2. **만기 연장 (Maturity Extension)**
   - 상환 부담 완화
   - 시간가치로 인한 손실

3. **원금 감면 (Principal Haircut)**
   - 직접적 원금 삭감
   - 즉시 손실 인식

4. **거치 기간 부여 (Grace Period)**
   - 일정 기간 원리금 유예
   - 기회비용 발생

**NPV 손실 계산**
```
NPV_Loss = PV(Original_CF) - PV(New_CF)
```

**승인 권한**
| Haircut 수준 | 승인 권한 |
|-------------|----------|
| ~10% | 지점장 |
| 10-20% | 여신심사부 |
| 20-30% | 경영진 |
| 30%+ | 이사회 |
"""
    }
}


@router.get("/feature-description/{feature_id}")
async def get_feature_description(feature_id: str):
    """기능 설명 조회 (모달용)"""
    if feature_id in FEATURE_DESCRIPTIONS:
        return FEATURE_DESCRIPTIONS[feature_id]
    return {"error": "Feature not found"}


@router.get("/cases")
async def get_workout_cases(
    status: Optional[str] = None,
    strategy: Optional[str] = None,
    region: str = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """Workout 케이스 목록"""
    region_cond = ""
    rp = {}
    if region:
        region_cond = " AND c.region = :region"
        rp["region"] = region

    query = """
        SELECT wc.case_id, wc.customer_id, c.customer_name, c.industry_name,
               wc.case_open_date, wc.case_status, wc.total_exposure,
               wc.secured_amount, wc.unsecured_amount, wc.provision_amount,
               wc.strategy, wc.expected_recovery_rate, wc.actual_recovery_rate,
               wc.assigned_workout_officer
        FROM workout_case wc
        JOIN customer c ON wc.customer_id = c.customer_id
        WHERE 1=1
    """
    params = {}

    if status:
        query += " AND wc.case_status = :status"
        params["status"] = status
    if strategy:
        query += " AND wc.strategy = :strategy"
        params["strategy"] = strategy

    query += region_cond
    query += " ORDER BY wc.case_open_date DESC LIMIT :limit"
    params["limit"] = limit

    result = db.execute(text(query), {**params, **rp})

    cases = []
    for row in result:
        cases.append({
            "case_id": row[0],
            "customer_id": row[1],
            "customer_name": row[2],
            "industry_name": row[3],
            "case_open_date": row[4],
            "case_status": row[5],
            "total_exposure": row[6],
            "secured_amount": row[7],
            "unsecured_amount": row[8],
            "provision_amount": row[9],
            "strategy": row[10],
            "expected_recovery_rate": row[11],
            "actual_recovery_rate": row[12],
            "assigned_workout_officer": row[13]
        })

    # 상태별 요약
    status_summary = db.execute(text("""
        SELECT case_status, COUNT(*) as count, SUM(total_exposure) as total_exposure
        FROM workout_case wc
        JOIN customer c ON wc.customer_id = c.customer_id
        WHERE 1=1
    """ + region_cond + """
        GROUP BY case_status
    """), rp)

    summary = {}
    for row in status_summary:
        summary[row[0]] = {
            "count": row[1],
            "total_exposure": row[2]
        }

    return {"cases": cases, "total": len(cases), "summary_by_status": summary}


@router.get("/case/{case_id}")
async def get_workout_case_detail(case_id: str, db: Session = Depends(get_db)):
    """Workout 케이스 상세"""
    # 케이스 정보
    case = db.execute(text("""
        SELECT wc.*, c.customer_name, c.industry_name, c.size_category
        FROM workout_case wc
        JOIN customer c ON wc.customer_id = c.customer_id
        WHERE wc.case_id = :case_id
    """), {"case_id": case_id}).fetchone()

    if not case:
        return {"error": "Case not found"}

    # 회수 시나리오
    scenarios = db.execute(text("""
        SELECT scenario_id, scenario_name, scenario_type, recovery_amount,
               recovery_timeline_months, discount_rate, npv, irr,
               legal_cost, admin_cost, probability, expected_value, is_recommended
        FROM recovery_scenario
        WHERE case_id = :case_id
        ORDER BY expected_value DESC
    """), {"case_id": case_id})

    scenario_list = []
    for row in scenarios:
        scenario_list.append({
            "scenario_id": row[0],
            "scenario_name": row[1],
            "scenario_type": row[2],
            "recovery_amount": row[3],
            "recovery_timeline_months": row[4],
            "discount_rate": row[5],
            "npv": row[6],
            "irr": row[7],
            "legal_cost": row[8],
            "admin_cost": row[9],
            "probability": row[10],
            "expected_value": row[11],
            "is_recommended": bool(row[12])
        })

    # 채무조정 이력
    restructurings = db.execute(text("""
        SELECT restructure_id, restructure_date, original_principal, original_rate,
               new_principal, new_rate, haircut_amount, grace_period_months,
               npv_loss, approval_level, status
        FROM debt_restructuring
        WHERE case_id = :case_id
        ORDER BY restructure_date DESC
    """), {"case_id": case_id})

    restructuring_list = []
    for row in restructurings:
        restructuring_list.append({
            "restructure_id": row[0],
            "restructure_date": row[1],
            "original_principal": row[2],
            "original_rate": row[3],
            "new_principal": row[4],
            "new_rate": row[5],
            "haircut_amount": row[6],
            "grace_period_months": row[7],
            "npv_loss": row[8],
            "approval_level": row[9],
            "status": row[10]
        })

    return {
        "case": {
            "case_id": case[0],
            "customer_id": case[1],
            "customer_name": case[18],
            "industry_name": case[19],
            "size_category": case[20],
            "case_open_date": case[3],
            "case_status": case[4],
            "total_exposure": case[5],
            "secured_amount": case[6],
            "unsecured_amount": case[7],
            "provision_amount": case[8],
            "strategy": case[10],
            "expected_recovery": {
                "amount": case[11],
                "rate": case[12],
                "date": case[13]
            },
            "actual_recovery": {
                "amount": case[14],
                "rate": case[15]
            },
            "assigned_officer": case[9],
            "closed_date": case[16]
        },
        "recovery_scenarios": scenario_list,
        "debt_restructurings": restructuring_list
    }


@router.get("/scenarios/{case_id}")
async def get_recovery_scenarios(case_id: str, db: Session = Depends(get_db)):
    """케이스별 회수 시나리오 비교"""
    scenarios = db.execute(text("""
        SELECT scenario_id, scenario_name, scenario_type, recovery_amount,
               recovery_timeline_months, discount_rate, npv, irr,
               legal_cost, admin_cost, opportunity_cost, probability, expected_value,
               is_recommended
        FROM recovery_scenario
        WHERE case_id = :case_id
        ORDER BY npv DESC
    """), {"case_id": case_id})

    scenario_list = []
    best_scenario = None
    best_npv = float('-inf')

    for row in scenarios:
        scenario = {
            "scenario_id": row[0],
            "scenario_name": row[1],
            "scenario_type": row[2],
            "recovery_amount": row[3],
            "recovery_timeline_months": row[4],
            "discount_rate": row[5],
            "npv": row[6],
            "irr": row[7],
            "total_cost": (row[8] or 0) + (row[9] or 0) + (row[10] or 0),
            "probability": row[11],
            "expected_value": row[12],
            "is_recommended": bool(row[13])
        }
        scenario_list.append(scenario)

        if scenario["npv"] and scenario["npv"] > best_npv:
            best_npv = scenario["npv"]
            best_scenario = scenario["scenario_name"]

    return {
        "case_id": case_id,
        "scenarios": scenario_list,
        "recommendation": {
            "best_by_npv": best_scenario,
            "best_npv": best_npv
        }
    }


@router.get("/restructuring-history")
async def get_restructuring_history(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """채무조정 전체 이력"""
    result = db.execute(text("""
        SELECT dr.restructure_id, dr.case_id, c.customer_name,
               dr.restructure_date, dr.original_principal, dr.original_rate,
               dr.new_principal, dr.new_rate, dr.haircut_amount,
               dr.grace_period_months, dr.npv_loss, dr.approval_level, dr.status
        FROM debt_restructuring dr
        JOIN workout_case wc ON dr.case_id = wc.case_id
        JOIN customer c ON wc.customer_id = c.customer_id
        ORDER BY dr.restructure_date DESC
        LIMIT :limit
    """), {"limit": limit})

    restructurings = []
    for row in result:
        restructurings.append({
            "restructure_id": row[0],
            "case_id": row[1],
            "customer_name": row[2],
            "restructure_date": row[3],
            "original_principal": row[4],
            "original_rate": row[5],
            "new_principal": row[6],
            "new_rate": row[7],
            "haircut_amount": row[8],
            "haircut_pct": round((row[8] / row[4] * 100), 1) if row[4] else 0,
            "grace_period_months": row[9],
            "npv_loss": row[10],
            "approval_level": row[11],
            "status": row[12]
        })

    return {"restructurings": restructurings, "total": len(restructurings)}


@router.get("/dashboard")
async def get_workout_dashboard(
    region: str = Query(None),
    db: Session = Depends(get_db)
):
    """Workout 대시보드"""
    region_cond = ""
    rp = {}
    if region:
        region_cond = " AND c.region = :region"
        rp["region"] = region

    # 전체 요약
    summary = db.execute(text("""
        SELECT
            COUNT(*) as total_cases,
            SUM(wc.total_exposure) as total_exposure,
            SUM(wc.provision_amount) as total_provision,
            AVG(wc.expected_recovery_rate) as avg_expected_recovery,
            SUM(CASE WHEN wc.case_status IN ('OPEN', 'IN_PROGRESS') THEN 1 ELSE 0 END) as active_cases
        FROM workout_case wc
        JOIN customer c ON wc.customer_id = c.customer_id
        WHERE 1=1
    """ + region_cond), rp).fetchone()

    # 전략별 분포
    by_strategy = db.execute(text("""
        SELECT wc.strategy, COUNT(*) as count, SUM(wc.total_exposure) as exposure
        FROM workout_case wc
        JOIN customer c ON wc.customer_id = c.customer_id
        WHERE 1=1
    """ + region_cond + """
        GROUP BY wc.strategy
    """), rp)

    strategy_breakdown = []
    for row in by_strategy:
        strategy_breakdown.append({
            "strategy": row[0],
            "count": row[1],
            "exposure": row[2]
        })

    # 최근 종결 케이스 (성과)
    recent_closed = db.execute(text("""
        SELECT c.customer_name, wc.total_exposure, wc.actual_recovery_rate,
               wc.closed_date, wc.strategy
        FROM workout_case wc
        JOIN customer c ON wc.customer_id = c.customer_id
        WHERE wc.case_status IN ('RECOVERED', 'LIQUIDATED')
    """ + region_cond + """
        ORDER BY wc.closed_date DESC
        LIMIT 5
    """), rp)

    recent_recoveries = []
    for row in recent_closed:
        recent_recoveries.append({
            "customer_name": row[0],
            "total_exposure": row[1],
            "recovery_rate": row[2],
            "closed_date": row[3],
            "strategy": row[4]
        })

    return {
        "summary": {
            "total_cases": summary[0],
            "total_exposure": summary[1],
            "total_provision": summary[2],
            "avg_expected_recovery_rate": round(summary[3], 3) if summary[3] else 0,
            "active_cases": summary[4]
        },
        "by_strategy": strategy_breakdown,
        "recent_recoveries": recent_recoveries
    }
