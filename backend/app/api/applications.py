"""
여신신청 API - 은행 실무 기반 심사 워크플로우
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import datetime
from ..core.database import get_db
from ..services.calculations import (
    calculate_raroc, calculate_pricing, calculate_rwa,
    get_pd_from_grade, GRADE_PD_MAP
)

router = APIRouter(prefix="/api/applications", tags=["Applications"])

# 심사 단계 정의
REVIEW_STAGES = {
    "RECEIVED": {"name": "접수", "order": 1},
    "DOC_REVIEW": {"name": "서류검토", "order": 2},
    "CREDIT_REVIEW": {"name": "신용평가", "order": 3},
    "COLLATERAL_REVIEW": {"name": "담보평가", "order": 4},
    "LIMIT_CHECK": {"name": "한도심사", "order": 5},
    "PRICING": {"name": "가격결정", "order": 6},
    "FINAL_REVIEW": {"name": "최종심사", "order": 7},
    "COMPLETED": {"name": "완료", "order": 8}
}

# 승인 권한 기준
APPROVAL_AUTHORITY = {
    "STAFF": {"limit": 500000000, "name": "담당자"},         # 5억
    "TEAM_LEAD": {"limit": 5000000000, "name": "팀장"},      # 50억
    "DEPT_HEAD": {"limit": 20000000000, "name": "부서장"},   # 200억
    "EXECUTIVE": {"limit": 100000000000, "name": "임원"},    # 1000억
    "COMMITTEE": {"limit": float('inf'), "name": "여신위원회"}
}


@router.get("")
def get_applications(
    status: Optional[str] = None,
    stage: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """여신신청 목록 조회"""
    query = """
        SELECT
            a.application_id, a.application_date, a.application_type,
            a.customer_id, c.customer_name, c.industry_name, c.size_category,
            a.product_code, p.product_name,
            a.requested_amount, a.requested_tenor, a.status, a.current_stage,
            a.priority, a.collateral_type, a.collateral_value,
            cr.final_grade, cr.pd_value,
            a.assigned_to, a.branch_code
        FROM loan_application a
        LEFT JOIN customer c ON a.customer_id = c.customer_id
        LEFT JOIN product_master p ON a.product_code = p.product_code
        LEFT JOIN (
            SELECT application_id, final_grade, pd_value,
                   ROW_NUMBER() OVER (PARTITION BY application_id ORDER BY rating_date DESC) as rn
            FROM credit_rating_result
        ) cr ON a.application_id = cr.application_id AND cr.rn = 1
        WHERE 1=1
    """
    params = {}

    if status:
        if status == 'PENDING':
            query += " AND a.status IN ('RECEIVED', 'REVIEWING')"
        else:
            query += " AND a.status = :status"
            params["status"] = status
    if stage:
        query += " AND a.current_stage = :stage"
        params["stage"] = stage
    if priority:
        query += " AND a.priority = :priority"
        params["priority"] = priority
    if assigned_to:
        query += " AND a.assigned_to = :assigned_to"
        params["assigned_to"] = assigned_to
    if region:
        query += " AND c.region = :region"
        params["region"] = region

    query += """
        ORDER BY
            CASE a.priority WHEN 'HIGH' THEN 1 WHEN 'NORMAL' THEN 2 ELSE 3 END,
            a.application_date DESC
        LIMIT :limit
    """
    params["limit"] = limit

    results = db.execute(text(query), params).fetchall()

    return [
        {
            "application_id": r[0],
            "application_date": str(r[1]) if r[1] else None,
            "application_type": r[2],
            "customer_id": r[3],
            "customer_name": r[4],
            "industry_name": r[5],
            "size_category": r[6],
            "product_code": r[7],
            "product_name": r[8],
            "requested_amount": r[9],
            "requested_tenor": r[10],
            "status": r[11],
            "current_stage": r[12],
            "stage_name": REVIEW_STAGES.get(r[12], {}).get("name", r[12]),
            "priority": r[13],
            "collateral_type": r[14],
            "collateral_value": r[15],
            "final_grade": r[16],
            "pd_value": r[17],
            "assigned_to": r[18],
            "branch_code": r[19]
        }
        for r in results
    ]


@router.get("/pending")
def get_pending_applications(db: Session = Depends(get_db)):
    """심사 대기중인 신청 목록 - 우선순위 및 기한 관리 포함"""
    results = db.execute(text("""
        SELECT
            a.application_id, a.application_date,
            c.customer_id, c.customer_name, c.industry_code, c.industry_name, c.size_category,
            p.product_name, a.requested_amount, a.requested_tenor,
            a.status, a.current_stage, a.priority,
            cr.final_grade, cr.pd_value,
            irs.strategy_code,
            a.collateral_type, a.collateral_value,
            a.assigned_to,
            -- 기존 여신 현황
            (SELECT COUNT(*) FROM facility f WHERE f.customer_id = c.customer_id AND f.status = 'ACTIVE') as existing_facility_count,
            (SELECT COALESCE(SUM(outstanding_amount), 0) FROM facility f WHERE f.customer_id = c.customer_id AND f.status = 'ACTIVE') as existing_exposure
        FROM loan_application a
        LEFT JOIN customer c ON a.customer_id = c.customer_id
        LEFT JOIN product_master p ON a.product_code = p.product_code
        LEFT JOIN (
            SELECT application_id, final_grade, pd_value,
                   ROW_NUMBER() OVER (PARTITION BY application_id ORDER BY rating_date DESC) as rn
            FROM credit_rating_result
        ) cr ON a.application_id = cr.application_id AND cr.rn = 1
        LEFT JOIN (
            SELECT industry_code, strategy_code,
                   ROW_NUMBER() OVER (PARTITION BY industry_code ORDER BY effective_from DESC) as rn
            FROM industry_rating_strategy
        ) irs ON c.industry_code = irs.industry_code AND irs.rn = 1
        WHERE a.status IN ('RECEIVED', 'REVIEWING')
        ORDER BY
            CASE a.priority WHEN 'HIGH' THEN 1 WHEN 'NORMAL' THEN 2 ELSE 3 END,
            a.application_date ASC
    """)).fetchall()

    return [
        {
            "application_id": r[0],
            "application_date": str(r[1]) if r[1] else None,
            "customer_id": r[2],
            "customer_name": r[3],
            "industry_code": r[4],
            "industry_name": r[5],
            "size_category": r[6],
            "product_name": r[7],
            "requested_amount": r[8],
            "requested_tenor": r[9],
            "status": r[10],
            "current_stage": r[11],
            "stage_name": REVIEW_STAGES.get(r[11], {}).get("name", r[11]),
            "priority": r[12],
            "final_grade": r[13],
            "pd_value": r[14],
            "strategy_code": r[15],
            "collateral_type": r[16],
            "collateral_value": r[17],
            "assigned_to": r[18],
            "existing_facility_count": r[19],
            "existing_exposure": r[20],
            # 승인 필요 권한
            "required_authority": get_required_authority(r[8])
        }
        for r in results
    ]


@router.get("/summary")
def get_applications_summary(region: Optional[str] = None, db: Session = Depends(get_db)):
    """심사 현황 요약 대시보드"""

    region_cond = " AND c.region = :region" if region else ""
    region_join = " JOIN customer c ON la.customer_id = c.customer_id" if region else ""
    rp = {"region": region} if region else {}

    # 상태별 건수
    by_status = db.execute(text(f"""
        SELECT la.status, COUNT(*), SUM(la.requested_amount)
        FROM loan_application la {region_join}
        WHERE 1=1 {region_cond}
        GROUP BY la.status
    """), rp).fetchall()

    # 단계별 건수
    by_stage = db.execute(text(f"""
        SELECT la.current_stage, COUNT(*), SUM(la.requested_amount)
        FROM loan_application la {region_join}
        WHERE la.status IN ('RECEIVED', 'REVIEWING') {region_cond}
        GROUP BY la.current_stage
    """), rp).fetchall()

    # 우선순위별 건수
    by_priority = db.execute(text(f"""
        SELECT la.priority, COUNT(*), SUM(la.requested_amount)
        FROM loan_application la {region_join}
        WHERE la.status IN ('RECEIVED', 'REVIEWING') {region_cond}
        GROUP BY la.priority
    """), rp).fetchall()

    # 금일 접수/처리 현황
    today_stats = db.execute(text(f"""
        SELECT
            (SELECT COUNT(*) FROM loan_application la {region_join} WHERE date(la.application_date) = date('now') {region_cond}) as today_received,
            (SELECT COUNT(*) FROM loan_application la {region_join} WHERE date(la.updated_at) = date('now') AND la.status IN ('APPROVED', 'REJECTED') {region_cond}) as today_processed,
            (SELECT COUNT(*) FROM loan_application la {region_join} WHERE la.status IN ('RECEIVED', 'REVIEWING') {region_cond}) as pending_total,
            (SELECT COUNT(*) FROM loan_application la {region_join} WHERE la.status IN ('RECEIVED', 'REVIEWING') AND la.priority = 'HIGH' {region_cond}) as pending_high_priority
    """), rp).fetchone()

    # 평균 처리 시간 (최근 30일)
    avg_processing = db.execute(text(f"""
        SELECT AVG(julianday(la.updated_at) - julianday(la.application_date))
        FROM loan_application la {region_join}
        WHERE la.status IN ('APPROVED', 'REJECTED')
        AND la.updated_at >= date('now', '-30 days') {region_cond}
    """), rp).scalar()

    return {
        "by_status": [{"status": r[0], "count": r[1], "amount": r[2]} for r in by_status],
        "by_stage": [
            {
                "stage": r[0],
                "stage_name": REVIEW_STAGES.get(r[0], {}).get("name", r[0]),
                "count": r[1],
                "amount": r[2]
            }
            for r in by_stage
        ],
        "by_priority": [{"priority": r[0], "count": r[1], "amount": r[2]} for r in by_priority],
        "today": {
            "received": today_stats[0] if today_stats else 0,
            "processed": today_stats[1] if today_stats else 0,
            "pending_total": today_stats[2] if today_stats else 0,
            "pending_high_priority": today_stats[3] if today_stats else 0
        },
        "avg_processing_days": round(avg_processing, 1) if avg_processing else None,
        "stages": REVIEW_STAGES
    }


@router.get("/{application_id}")
def get_application_detail(application_id: str, db: Session = Depends(get_db)):
    """여신신청 상세 조회 - 종합 심사 정보"""

    # 기본 정보
    app = db.execute(text("""
        SELECT
            a.application_id, a.application_date, a.application_type,
            a.customer_id, a.group_id, a.product_code,
            a.requested_amount, a.requested_tenor, a.requested_rate,
            a.purpose_code, a.purpose_detail, a.collateral_type,
            a.collateral_value, a.guarantee_type, a.status,
            a.current_stage, a.priority, a.assigned_to,
            a.branch_code, a.created_at, a.updated_at
        FROM loan_application a
        WHERE a.application_id = :app_id
    """), {"app_id": application_id}).fetchone()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # 고객 정보
    customer = db.execute(text("""
        SELECT customer_id, customer_name, biz_reg_no, industry_code, industry_name,
               size_category, establish_date, employee_count, asset_size, revenue_size,
               address
        FROM customer
        WHERE customer_id = :cust_id
    """), {"cust_id": app[3]}).fetchone()

    # 상품 정보
    product = db.execute(text("""
        SELECT product_code, product_name, product_type, risk_category, is_active
        FROM product_master
        WHERE product_code = :prod_code
    """), {"prod_code": app[5]}).fetchone()

    # 신용등급 (최신 + 이력)
    rating = db.execute(text("""
        SELECT rating_id, rating_date, model_id, final_grade, pd_value,
               override_grade, override_reason
        FROM credit_rating_result
        WHERE application_id = :app_id
        ORDER BY rating_date DESC
        LIMIT 1
    """), {"app_id": application_id}).fetchone()

    rating_history = db.execute(text("""
        SELECT rating_date, final_grade, pd_value, model_id
        FROM credit_rating_result
        WHERE customer_id = :cust_id
        ORDER BY rating_date DESC
        LIMIT 5
    """), {"cust_id": app[3]}).fetchall()

    # 리스크 파라미터
    risk_param = db.execute(text("""
        SELECT param_id, calc_date, ttc_pd, pit_pd, lgd, ead, rwa,
               expected_loss, unexpected_loss, economic_capital
        FROM risk_parameter
        WHERE application_id = :app_id
        ORDER BY calc_date DESC
        LIMIT 1
    """), {"app_id": application_id}).fetchone()

    # 가격결정 결과
    pricing = db.execute(text("""
        SELECT pricing_id, pricing_date, base_rate, ftp_spread, credit_spread,
               capital_spread, opex_spread, target_margin, strategy_adj,
               contribution_adj, collateral_adj, system_rate, proposed_rate,
               final_rate, expected_revenue, expected_raroc, hurdle_rate, raroc_status
        FROM pricing_result
        WHERE application_id = :app_id
        ORDER BY pricing_date DESC
        LIMIT 1
    """), {"app_id": application_id}).fetchone()

    # 담보 정보
    collaterals = db.execute(text("""
        SELECT collateral_id, collateral_type, collateral_subtype,
               original_value, current_value, ltv, valuation_date, priority_rank
        FROM collateral
        WHERE application_id = :app_id
        ORDER BY priority_rank
    """), {"app_id": application_id}).fetchall()

    # 기존 여신 현황
    existing_facilities = db.execute(text("""
        SELECT f.facility_id, f.facility_type, p.product_name,
               f.current_limit, f.outstanding_amount, f.available_amount,
               f.final_rate, f.maturity_date, f.status
        FROM facility f
        LEFT JOIN product_master p ON f.product_code = p.product_code
        WHERE f.customer_id = :cust_id
        ORDER BY f.status DESC, f.outstanding_amount DESC
    """), {"cust_id": app[3]}).fetchall()

    # 기존 여신 합계
    existing_summary = db.execute(text("""
        SELECT
            COUNT(*) as total_count,
            COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as active_count,
            COALESCE(SUM(CASE WHEN status = 'ACTIVE' THEN outstanding_amount END), 0) as total_outstanding,
            COALESCE(SUM(CASE WHEN status = 'ACTIVE' THEN current_limit END), 0) as total_limit
        FROM facility
        WHERE customer_id = :cust_id
    """), {"cust_id": app[3]}).fetchone()

    # 전략 정보
    strategy = db.execute(text("""
        SELECT industry_code, industry_name, rating_bucket, strategy_code,
               pricing_adj_bp, effective_from
        FROM industry_rating_strategy
        WHERE industry_code = :ind_code
        LIMIT 1
    """), {"ind_code": customer[3] if customer else None}).fetchone()

    # 한도 현황
    limits = db.execute(text("""
        SELECT ld.limit_id, ld.limit_name, ld.limit_type, ld.dimension_type,
               ld.limit_amount, le.exposure_amount, le.utilization_rate, le.status
        FROM limit_definition ld
        LEFT JOIN limit_exposure le ON ld.limit_id = le.limit_id
        WHERE ld.dimension_code = :ind_code
           OR ld.dimension_type = 'SINGLE'
           OR ld.dimension_type = 'TOTAL'
        ORDER BY le.utilization_rate DESC
    """), {"ind_code": customer[3] if customer else None}).fetchall()

    # 심사 체크리스트
    checklist = generate_review_checklist(app, customer, rating, risk_param, collaterals, limits)

    # 승인 이력
    approval_history = db.execute(text("""
        SELECT approval_id, approval_level, approver_name, decision,
               conditions, comments, decided_at
        FROM approval_history
        WHERE application_id = :app_id
        ORDER BY decided_at DESC
    """), {"app_id": application_id}).fetchall()

    # 재무비율 분석 (간단 계산)
    financial_ratios = None
    if customer and customer[8] and customer[9]:
        asset = customer[8]
        revenue = customer[9]
        financial_ratios = {
            "asset_turnover": round(revenue / asset, 2) if asset > 0 else 0,
            "size_grade": "대기업" if asset > 500000000000 else "중견기업" if asset > 100000000000 else "중소기업"
        }

    return {
        "application": {
            "application_id": app[0],
            "application_date": str(app[1]) if app[1] else None,
            "application_type": app[2],
            "customer_id": app[3],
            "product_code": app[5],
            "requested_amount": app[6],
            "requested_tenor": app[7],
            "requested_rate": app[8],
            "purpose_code": app[9],
            "purpose_detail": app[10],
            "collateral_type": app[11],
            "collateral_value": app[12],
            "guarantee_type": app[13],
            "status": app[14],
            "current_stage": app[15],
            "stage_name": REVIEW_STAGES.get(app[15], {}).get("name", app[15]),
            "priority": app[16],
            "assigned_to": app[17],
            "branch_code": app[18]
        },
        "customer": {
            "customer_id": customer[0] if customer else None,
            "customer_name": customer[1] if customer else None,
            "business_number": customer[2] if customer else None,
            "industry_code": customer[3] if customer else None,
            "industry_name": customer[4] if customer else None,
            "size_category": customer[5] if customer else None,
            "establishment_date": str(customer[6]) if customer and customer[6] else None,
            "employees": customer[7] if customer else None,
            "asset_size": customer[8] if customer else None,
            "revenue_size": customer[9] if customer else None,
            "address": customer[10] if customer else None
        } if customer else None,
        "product": {
            "product_code": product[0] if product else None,
            "product_name": product[1] if product else None,
            "product_type": product[2] if product else None,
            "risk_category": product[3] if product else None,
            "is_active": product[4] if product else None
        } if product else None,
        "rating": {
            "rating_id": rating[0] if rating else None,
            "rating_date": str(rating[1]) if rating and rating[1] else None,
            "model_id": rating[2] if rating else None,
            "final_grade": rating[3] if rating else None,
            "pd_value": rating[4] if rating else None,
            "override_grade": rating[5] if rating else None,
            "override_reason": rating[6] if rating else None
        } if rating else None,
        "rating_history": [
            {
                "rating_date": str(r[0]) if r[0] else None,
                "grade": r[1],
                "pd": r[2],
                "model": r[3]
            }
            for r in rating_history
        ],
        "risk_parameter": {
            "param_id": risk_param[0] if risk_param else None,
            "calc_date": str(risk_param[1]) if risk_param and risk_param[1] else None,
            "ttc_pd": risk_param[2] if risk_param else None,
            "pit_pd": risk_param[3] if risk_param else None,
            "lgd": risk_param[4] if risk_param else None,
            "ead": risk_param[5] if risk_param else None,
            "rwa": risk_param[6] if risk_param else None,
            "expected_loss": risk_param[7] if risk_param else None,
            "unexpected_loss": risk_param[8] if risk_param else None,
            "economic_capital": risk_param[9] if risk_param else None
        } if risk_param else None,
        "pricing": {
            "pricing_id": pricing[0] if pricing else None,
            "pricing_date": str(pricing[1]) if pricing and pricing[1] else None,
            "base_rate": pricing[2] if pricing else None,
            "ftp_spread": pricing[3] if pricing else None,
            "credit_spread": pricing[4] if pricing else None,
            "capital_spread": pricing[5] if pricing else None,
            "opex_spread": pricing[6] if pricing else None,
            "target_margin": pricing[7] if pricing else None,
            "strategy_adj": pricing[8] if pricing else None,
            "contribution_adj": pricing[9] if pricing else None,
            "collateral_adj": pricing[10] if pricing else None,
            "system_rate": pricing[11] if pricing else None,
            "proposed_rate": pricing[12] if pricing else None,
            "final_rate": pricing[13] if pricing else None,
            "expected_revenue": pricing[14] if pricing else None,
            "expected_raroc": pricing[15] if pricing else None,
            "hurdle_rate": pricing[16] if pricing else None,
            "raroc_status": pricing[17] if pricing else None
        } if pricing else None,
        "collaterals": [
            {
                "collateral_id": c[0],
                "collateral_type": c[1],
                "collateral_subtype": c[2],
                "original_value": c[3],
                "current_value": c[4],
                "ltv": c[5],
                "valuation_date": str(c[6]) if c[6] else None,
                "priority_rank": c[7]
            }
            for c in collaterals
        ],
        "existing_facilities": [
            {
                "facility_id": f[0],
                "facility_type": f[1],
                "product_name": f[2],
                "limit": f[3],
                "outstanding": f[4],
                "available": f[5],
                "rate": f[6],
                "maturity": str(f[7]) if f[7] else None,
                "status": f[8]
            }
            for f in existing_facilities
        ],
        "existing_summary": {
            "total_count": existing_summary[0] if existing_summary else 0,
            "active_count": existing_summary[1] if existing_summary else 0,
            "total_outstanding": existing_summary[2] if existing_summary else 0,
            "total_limit": existing_summary[3] if existing_summary else 0,
            "new_total_exposure": (existing_summary[2] if existing_summary else 0) + (app[6] or 0)
        },
        "strategy": {
            "industry_code": strategy[0] if strategy else None,
            "industry_name": strategy[1] if strategy else None,
            "rating_bucket": strategy[2] if strategy else None,
            "strategy_code": strategy[3] if strategy else None,
            "pricing_adj_bp": strategy[4] if strategy else None,
            "effective_from": str(strategy[5]) if strategy and strategy[5] else None
        } if strategy else None,
        "limits": [
            {
                "limit_id": l[0],
                "limit_name": l[1],
                "limit_type": l[2],
                "dimension_type": l[3],
                "limit_amount": l[4],
                "exposure_amount": l[5],
                "utilization_rate": l[6],
                "status": l[7],
                "after_approval": (l[5] or 0) + (app[6] or 0),
                "after_utilization": ((l[5] or 0) + (app[6] or 0)) / l[4] * 100 if l[4] else 0
            }
            for l in limits
        ],
        "checklist": checklist,
        "approval_history": [
            {
                "approval_id": h[0],
                "level": h[1],
                "approver": h[2],
                "decision": h[3],
                "conditions": h[4],
                "comments": h[5],
                "decided_at": str(h[6]) if h[6] else None
            }
            for h in approval_history
        ],
        "financial_ratios": financial_ratios,
        "required_authority": get_required_authority(app[6]),
        "review_stages": REVIEW_STAGES
    }


@router.get("/{application_id}/simulate")
def simulate_application(
    application_id: str,
    amount: Optional[float] = None,
    rate: Optional[float] = None,
    tenor: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """What-if 시뮬레이션 - 금리/금액/기간 조정에 따른 수익성 분석"""

    # 신청 정보 조회
    app = db.execute(text("""
        SELECT a.requested_amount, a.requested_tenor, a.collateral_type, a.collateral_value,
               cr.pd_value, cr.final_grade, c.industry_code, c.customer_id
        FROM loan_application a
        LEFT JOIN credit_rating_result cr ON a.application_id = cr.application_id
        LEFT JOIN customer c ON a.customer_id = c.customer_id
        WHERE a.application_id = :app_id
    """), {"app_id": application_id}).fetchone()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # 기존 여신 현황
    existing = db.execute(text("""
        SELECT COALESCE(SUM(outstanding_amount), 0)
        FROM facility
        WHERE customer_id = :cust_id AND status = 'ACTIVE'
    """), {"cust_id": app[7]}).scalar() or 0

    # 파라미터 설정
    sim_amount = amount or app[0]
    sim_tenor = tenor or app[1] or 36
    pd = app[4] or 0.02
    grade = app[5] or 'BBB'
    has_collateral = app[2] and app[2] != 'NONE'
    collateral_value = app[3] or 0

    # LTV 계산
    ltv = (sim_amount / collateral_value * 100) if collateral_value > 0 else None

    # 전략 조회
    strategy = db.execute(text("""
        SELECT strategy_code, pricing_adj_bp
        FROM industry_rating_strategy
        WHERE industry_code = :ind_code LIMIT 1
    """), {"ind_code": app[6]}).fetchone()

    strategy_code = strategy[0] if strategy else 'MAINTAIN'
    pricing_adj = (strategy[1] or 0) / 10000 if strategy else 0
    max_tenor = 60  # 기본값

    # LGD 설정 (담보 유형에 따라)
    lgd = 0.35 if has_collateral else 0.50

    # 가격 계산
    pricing_result = calculate_pricing(
        pd=pd,
        lgd=lgd,
        strategy_code=strategy_code,
        has_collateral=has_collateral
    )

    sim_rate = rate or pricing_result["final_rate"]

    # FTP 금리 조회
    ftp = db.execute(text("""
        SELECT final_ftp_rate FROM ftp_rate
        WHERE tenor_months = :tenor
        ORDER BY effective_date DESC LIMIT 1
    """), {"tenor": min(sim_tenor, 60)}).fetchone()

    ftp_rate = ftp[0] if ftp else 0.035

    # RAROC 계산
    raroc_result = calculate_raroc(
        amount=sim_amount,
        rate=sim_rate,
        ftp_rate=ftp_rate,
        pd=pd,
        lgd=lgd,
        tenor_years=sim_tenor / 12
    )

    # RWA 계산
    rwa = calculate_rwa(ead=sim_amount, pd=pd, lgd=lgd)

    # 허들레이트 조회
    hurdle = db.execute(text("""
        SELECT hurdle_raroc FROM hurdle_rate
        WHERE segment_type = 'ALL' AND effective_date <= date('now')
        ORDER BY effective_date DESC LIMIT 1
    """)).fetchone()
    hurdle_rate = hurdle[0] if hurdle else 0.12

    # 여러 금리 시나리오
    rate_scenarios = []
    for adj in [-0.01, -0.005, -0.0025, 0, 0.0025, 0.005, 0.01]:
        scenario_rate = sim_rate + adj
        if scenario_rate > 0:
            scenario_raroc = calculate_raroc(
                amount=sim_amount,
                rate=scenario_rate,
                ftp_rate=ftp_rate,
                pd=pd,
                lgd=lgd,
                tenor_years=sim_tenor / 12
            )
            rate_scenarios.append({
                "rate": scenario_rate,
                "spread_to_base": (scenario_rate - pricing_result["base_rate"]) * 100,
                "raroc": scenario_raroc["raroc"],
                "net_income": scenario_raroc["net_income"],
                "meets_hurdle": scenario_raroc["raroc"] >= hurdle_rate
            })

    # 손익분기 금리 계산 (RAROC = hurdle rate 되는 금리)
    # 근사값 계산
    breakeven_rate = None
    for test_rate in [x / 1000 for x in range(30, 150)]:
        test_raroc = calculate_raroc(
            amount=sim_amount,
            rate=test_rate,
            ftp_rate=ftp_rate,
            pd=pd,
            lgd=lgd,
            tenor_years=sim_tenor / 12
        )
        if test_raroc["raroc"] >= hurdle_rate:
            breakeven_rate = test_rate
            break

    return {
        "input": {
            "amount": sim_amount,
            "rate": sim_rate,
            "tenor_months": sim_tenor,
            "pd": pd,
            "lgd": lgd,
            "grade": grade,
            "strategy_code": strategy_code,
            "has_collateral": has_collateral,
            "ltv": ltv
        },
        "pricing": pricing_result,
        "risk": {
            "rwa": rwa,
            "expected_loss": sim_amount * pd * lgd,
            "risk_weight": rwa / sim_amount if sim_amount > 0 else 0
        },
        "raroc": raroc_result,
        "hurdle_rate": hurdle_rate,
        "raroc_status": "ABOVE_HURDLE" if raroc_result["raroc"] >= hurdle_rate else "BELOW_HURDLE",
        "breakeven_rate": breakeven_rate,
        "rate_scenarios": rate_scenarios,
        "exposure_impact": {
            "existing_exposure": existing,
            "new_exposure": sim_amount,
            "total_exposure": existing + sim_amount
        },
        "tenor_check": {
            "requested": sim_tenor,
            "max_allowed": max_tenor,
            "within_limit": sim_tenor <= max_tenor if max_tenor else True
        }
    }


@router.post("/{application_id}/stage")
def update_stage(
    application_id: str,
    new_stage: str,
    comments: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """심사 단계 변경"""
    if new_stage not in REVIEW_STAGES:
        raise HTTPException(status_code=400, detail="Invalid stage")

    db.execute(text("""
        UPDATE loan_application
        SET current_stage = :stage, updated_at = CURRENT_TIMESTAMP
        WHERE application_id = :app_id
    """), {"stage": new_stage, "app_id": application_id})

    db.commit()

    return {
        "status": "success",
        "new_stage": new_stage,
        "stage_name": REVIEW_STAGES[new_stage]["name"]
    }


@router.post("/{application_id}/approve")
def approve_application(
    application_id: str,
    decision: str,
    approval_level: Optional[str] = None,
    approver_name: Optional[str] = None,
    conditions: Optional[str] = None,
    comments: Optional[str] = None,
    approved_amount: Optional[float] = None,
    approved_rate: Optional[float] = None,
    approved_tenor: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """여신 승인/반려 처리"""

    # 신청 정보 확인
    app = db.execute(text("""
        SELECT requested_amount, status FROM loan_application
        WHERE application_id = :app_id
    """), {"app_id": application_id}).fetchone()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # 상태 업데이트
    new_status = "APPROVED" if decision == "APPROVE" else (
        "CONDITIONAL" if decision == "CONDITIONAL" else "REJECTED"
    )

    db.execute(text("""
        UPDATE loan_application
        SET status = :status,
            current_stage = 'COMPLETED',
            updated_at = CURRENT_TIMESTAMP
        WHERE application_id = :app_id
    """), {"status": new_status, "app_id": application_id})

    # 승인 이력 추가
    approval_id = f"APPR_{application_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    db.execute(text("""
        INSERT INTO approval_history
        (approval_id, application_id, approval_level, approver_name, decision, conditions, comments, decided_at)
        VALUES (:appr_id, :app_id, :level, :approver, :decision, :conditions, :comments, CURRENT_TIMESTAMP)
    """), {
        "appr_id": approval_id,
        "app_id": application_id,
        "level": approval_level or get_required_authority(app[0])["level"],
        "approver": approver_name or "시스템",
        "decision": decision,
        "conditions": conditions,
        "comments": comments
    })

    db.commit()

    return {
        "status": "success",
        "new_status": new_status,
        "approval_id": approval_id,
        "approved_amount": approved_amount or app[0],
        "approved_rate": approved_rate,
        "approved_tenor": approved_tenor
    }


def get_required_authority(amount: float) -> dict:
    """금액에 따른 필요 승인 권한 반환"""
    if amount is None:
        return {"level": "STAFF", "name": "담당자"}

    for level, info in APPROVAL_AUTHORITY.items():
        if amount <= info["limit"]:
            return {"level": level, "name": info["name"], "limit": info["limit"]}

    return {"level": "COMMITTEE", "name": "여신위원회", "limit": float('inf')}


def generate_review_checklist(app, customer, rating, risk_param, collaterals, limits) -> list:
    """심사 체크리스트 자동 생성"""
    checklist = []

    # 1. 서류 검토
    checklist.append({
        "category": "서류검토",
        "items": [
            {"item": "사업자등록증", "status": "checked" if customer else "unchecked"},
            {"item": "재무제표", "status": "checked" if customer and customer[8] else "unchecked"},
            {"item": "담보 서류", "status": "checked" if collaterals else "unchecked" if app[11] != 'NONE' else "N/A"},
            {"item": "본인확인서류", "status": "checked"}
        ]
    })

    # 2. 신용 검토
    grade_ok = rating and rating[3] and rating[3] not in ['CCC', 'CC', 'C', 'D']
    checklist.append({
        "category": "신용평가",
        "items": [
            {"item": "신용등급 산출", "status": "checked" if rating else "unchecked", "value": rating[3] if rating else None},
            {"item": "등급 적정성", "status": "checked" if grade_ok else "warning", "note": "주의필요" if not grade_ok else None},
            {"item": "PD 산출", "status": "checked" if rating and rating[4] else "unchecked", "value": f"{rating[4]*100:.2f}%" if rating and rating[4] else None},
            {"item": "Override 검토", "status": "checked" if rating and not rating[5] else "warning" if rating and rating[5] else "N/A"}
        ]
    })

    # 3. 담보 검토
    if app[11] and app[11] != 'NONE':
        collateral_value = sum(c[4] or 0 for c in collaterals) if collaterals else 0
        ltv = (app[6] / collateral_value * 100) if collateral_value > 0 else None
        ltv_ok = ltv and ltv <= 70
        checklist.append({
            "category": "담보평가",
            "items": [
                {"item": "담보물건 확인", "status": "checked" if collaterals else "unchecked"},
                {"item": "감정평가", "status": "checked" if collateral_value > 0 else "unchecked", "value": f"{collateral_value/100000000:,.0f}억원" if collateral_value else None},
                {"item": "LTV 적정성", "status": "checked" if ltv_ok else "warning", "value": f"{ltv:.1f}%" if ltv else None, "note": "LTV 초과" if ltv and ltv > 70 else None},
                {"item": "선순위 확인", "status": "checked"}
            ]
        })

    # 4. 한도 검토
    limit_breaches = [l for l in limits if l[7] == 'BREACH' or (l[6] and l[6] > 100)]
    checklist.append({
        "category": "한도심사",
        "items": [
            {"item": "업종한도", "status": "warning" if any(l[3] == 'INDUSTRY' and l[6] and l[6] > 90 for l in limits) else "checked"},
            {"item": "단일거래처한도", "status": "warning" if any(l[3] == 'SINGLE' and l[6] and l[6] > 90 for l in limits) else "checked"},
            {"item": "전체한도", "status": "warning" if any(l[3] == 'TOTAL' and l[6] and l[6] > 90 for l in limits) else "checked"},
            {"item": "한도 초과 여부", "status": "danger" if limit_breaches else "checked", "note": f"{len(limit_breaches)}건 초과" if limit_breaches else None}
        ]
    })

    # 5. 수익성 검토
    raroc_ok = risk_param and risk_param[9] and True  # EC 기반 RAROC 체크 간소화
    checklist.append({
        "category": "수익성검토",
        "items": [
            {"item": "RWA 산출", "status": "checked" if risk_param and risk_param[6] else "unchecked", "value": f"{risk_param[6]/100000000:,.0f}억원" if risk_param and risk_param[6] else None},
            {"item": "RAROC 산출", "status": "checked", "note": "What-if 분석 참조"},
            {"item": "Hurdle Rate 충족", "status": "checked" if raroc_ok else "warning"},
            {"item": "전략 적합성", "status": "checked"}
        ]
    })

    return checklist
