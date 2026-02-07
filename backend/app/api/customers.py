"""
고객 관리 API
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..core.database import get_db

router = APIRouter(prefix="/api/customers", tags=["Customers"])


@router.get("")
def get_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    industry_code: str = Query(None),
    size_category: str = Query(None),
    sort_by: str = Query("customer_name"),
    sort_order: str = Query("asc"),
    db: Session = Depends(get_db)
):
    """전체 고객 목록 조회 (페이징, 검색, 필터링)"""

    # 기본 쿼리 - 실제 customer 테이블 컬럼에 맞춤
    base_query = """
        SELECT c.customer_id, c.customer_name, c.biz_reg_no,
               c.industry_code, c.industry_name, c.size_category,
               c.establish_date, c.address,
               cr.final_grade as credit_rating, cr.pd_value as probability_default,
               cr.rating_date,
               COALESCE(SUM(f.outstanding_amount), 0) as total_exposure,
               COUNT(DISTINCT CASE WHEN f.status = 'ACTIVE' THEN f.facility_id END) as facility_count
        FROM customer c
        LEFT JOIN credit_rating_result cr ON c.customer_id = cr.customer_id
            AND cr.rating_date = (SELECT MAX(rating_date) FROM credit_rating_result WHERE customer_id = c.customer_id)
        LEFT JOIN facility f ON c.customer_id = f.customer_id AND f.status = 'ACTIVE'
    """

    conditions = []
    params = {}

    # 검색 조건
    if search:
        conditions.append("(c.customer_name LIKE :search OR c.customer_id LIKE :search OR c.biz_reg_no LIKE :search)")
        params["search"] = f"%{search}%"

    # 업종 필터
    if industry_code:
        conditions.append("c.industry_code = :industry_code")
        params["industry_code"] = industry_code

    # 규모 필터
    if size_category:
        conditions.append("c.size_category = :size_category")
        params["size_category"] = size_category

    # WHERE 절 조합
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    # GROUP BY
    group_by = " GROUP BY c.customer_id"

    # 정렬
    valid_sort_columns = ["customer_name", "customer_id", "industry_name", "total_exposure", "credit_rating"]
    if sort_by not in valid_sort_columns:
        sort_by = "customer_name"
    sort_direction = "DESC" if sort_order.lower() == "desc" else "ASC"

    # total_exposure는 집계 후 정렬해야 하므로 특별 처리
    if sort_by == "total_exposure":
        order_clause = f" ORDER BY total_exposure {sort_direction}"
    elif sort_by == "credit_rating":
        order_clause = f" ORDER BY cr.final_grade {sort_direction}"
    else:
        order_clause = f" ORDER BY c.{sort_by} {sort_direction}"

    # 페이징
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    # 전체 건수 조회
    count_query = f"""
        SELECT COUNT(DISTINCT c.customer_id)
        FROM customer c
        {where_clause}
    """
    total_count = db.execute(text(count_query), params).scalar() or 0

    # 데이터 조회
    data_query = base_query + where_clause + group_by + order_clause + " LIMIT :limit OFFSET :offset"
    results = db.execute(text(data_query), params).fetchall()

    customers = [
        {
            "customer_id": r[0],
            "customer_name": r[1],
            "business_number": r[2],
            "industry_code": r[3],
            "industry_name": r[4],
            "size_category": r[5],
            "establishment_date": str(r[6]) if r[6] else None,
            "address": r[7],
            "credit_rating": r[8],
            "probability_default": r[9],
            "rating_date": str(r[10]) if r[10] else None,
            "total_exposure": r[11],
            "facility_count": r[12]
        }
        for r in results
    ]

    return {
        "data": customers,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size
        }
    }


@router.get("/summary")
def get_customers_summary(db: Session = Depends(get_db)):
    """고객 현황 요약"""

    # 전체 고객 수
    total_count = db.execute(text("SELECT COUNT(*) FROM customer")).scalar()

    # 규모별 분포
    by_size = db.execute(text("""
        SELECT size_category, COUNT(*) as count
        FROM customer
        WHERE size_category IS NOT NULL
        GROUP BY size_category
    """)).fetchall()

    # 업종별 상위 10개
    by_industry = db.execute(text("""
        SELECT industry_code, industry_name, COUNT(*) as count
        FROM customer
        WHERE industry_code IS NOT NULL
        GROUP BY industry_code
        ORDER BY count DESC
        LIMIT 10
    """)).fetchall()

    # 신용등급별 분포
    by_rating = db.execute(text("""
        SELECT cr.final_grade, COUNT(DISTINCT c.customer_id) as count
        FROM customer c
        LEFT JOIN credit_rating_result cr ON c.customer_id = cr.customer_id
            AND cr.rating_date = (SELECT MAX(rating_date) FROM credit_rating_result WHERE customer_id = c.customer_id)
        WHERE cr.final_grade IS NOT NULL
        GROUP BY cr.final_grade
        ORDER BY cr.final_grade
    """)).fetchall()

    # 총 여신잔액
    total_exposure = db.execute(text("""
        SELECT COALESCE(SUM(outstanding_amount), 0)
        FROM facility
        WHERE status = 'ACTIVE'
    """)).scalar()

    return {
        "total_customers": total_count,
        "total_exposure": total_exposure,
        "by_size": [{"size_category": r[0], "count": r[1]} for r in by_size],
        "by_industry": [{"industry_code": r[0], "industry_name": r[1], "count": r[2]} for r in by_industry],
        "by_rating": [{"rating": r[0], "count": r[1]} for r in by_rating]
    }


@router.get("/industries")
def get_industries(db: Session = Depends(get_db)):
    """업종 목록 (필터용)"""
    results = db.execute(text("""
        SELECT DISTINCT industry_code, industry_name, COUNT(*) as customer_count
        FROM customer
        WHERE industry_code IS NOT NULL
        GROUP BY industry_code
        ORDER BY industry_name
    """)).fetchall()

    return [
        {
            "industry_code": r[0],
            "industry_name": r[1],
            "customer_count": r[2]
        }
        for r in results
    ]


@router.get("/{customer_id}")
def get_customer_detail(customer_id: str, db: Session = Depends(get_db)):
    """고객 상세 정보"""

    # 기본 정보 - 실제 customer 테이블 컬럼에 맞춤
    customer = db.execute(text("""
        SELECT c.customer_id, c.customer_name, c.biz_reg_no,
               c.industry_code, c.industry_name, c.size_category,
               c.establish_date, c.address, c.employee_count,
               c.asset_size, c.revenue_size
        FROM customer c
        WHERE c.customer_id = :cust_id
    """), {"cust_id": customer_id}).fetchone()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # 신용등급 이력 - credit_rating_result 테이블 사용
    ratings = db.execute(text("""
        SELECT final_grade, pd_value, model_id, rating_date, override_reason
        FROM credit_rating_result
        WHERE customer_id = :cust_id
        ORDER BY rating_date DESC
        LIMIT 10
    """), {"cust_id": customer_id}).fetchall()

    # 여신 현황 - 실제 facility 테이블 컬럼에 맞춤
    facilities = db.execute(text("""
        SELECT f.facility_id, f.facility_type, p.product_name,
               f.current_limit, f.outstanding_amount, f.available_amount,
               f.final_rate, f.contract_date, f.maturity_date, f.status
        FROM facility f
        LEFT JOIN product_master p ON f.product_code = p.product_code
        WHERE f.customer_id = :cust_id
        ORDER BY f.status DESC, f.outstanding_amount DESC
    """), {"cust_id": customer_id}).fetchall()

    # 여신 합계
    facility_summary = db.execute(text("""
        SELECT
            COUNT(*) as total_count,
            COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as active_count,
            COALESCE(SUM(CASE WHEN status = 'ACTIVE' THEN current_limit END), 0) as total_limit,
            COALESCE(SUM(CASE WHEN status = 'ACTIVE' THEN outstanding_amount END), 0) as total_outstanding,
            COALESCE(SUM(CASE WHEN status = 'ACTIVE' THEN available_amount END), 0) as total_available
        FROM facility
        WHERE customer_id = :cust_id
    """), {"cust_id": customer_id}).fetchone()

    # RWA 정보 - loan_application + risk_parameter에서 조회
    rwa_info = db.execute(text("""
        SELECT COALESCE(SUM(rp.rwa), 0) as total_rwa,
               COALESCE(SUM(rp.ead), 0) as total_ead,
               COALESCE(SUM(rp.expected_loss), 0) as total_el
        FROM loan_application la
        JOIN risk_parameter rp ON la.application_id = rp.application_id
        WHERE la.customer_id = :cust_id
    """), {"cust_id": customer_id}).fetchone()

    # 담보 정보
    collaterals = db.execute(text("""
        SELECT col.collateral_id, col.collateral_type, col.collateral_subtype,
               col.original_value, col.current_value, col.ltv, col.valuation_date,
               col.priority_rank, f.facility_id
        FROM collateral col
        JOIN facility f ON col.facility_id = f.facility_id
        WHERE f.customer_id = :cust_id
        ORDER BY col.current_value DESC
    """), {"cust_id": customer_id}).fetchall()

    # 여신 신청 이력
    applications = db.execute(text("""
        SELECT la.application_id, la.application_date, la.application_type,
               p.product_name, la.requested_amount, la.status, la.current_stage,
               la.purpose_detail
        FROM loan_application la
        LEFT JOIN product_master p ON la.product_code = p.product_code
        WHERE la.customer_id = :cust_id
        ORDER BY la.application_date DESC
        LIMIT 20
    """), {"cust_id": customer_id}).fetchall()

    # 한도 관련 정보
    limit_info = db.execute(text("""
        SELECT ld.limit_name, ld.limit_amount, le.exposure_amount, le.utilization_rate
        FROM limit_definition ld
        LEFT JOIN limit_exposure le ON ld.limit_id = le.limit_id
        WHERE ld.dimension_type = 'INDUSTRY' AND ld.dimension_code = :ind_code
    """), {"ind_code": customer[3]}).fetchone()

    return {
        "basic_info": {
            "customer_id": customer[0],
            "customer_name": customer[1],
            "business_number": customer[2],
            "industry_code": customer[3],
            "industry_name": customer[4],
            "size_category": customer[5],
            "establishment_date": str(customer[6]) if customer[6] else None,
            "address": customer[7],
            "employees": customer[8]
        },
        "financials": {
            "total_assets": customer[9],
            "annual_revenue": customer[10]
        },
        "credit_ratings": [
            {
                "rating": r[0],
                "pd": r[1],
                "lgd": 0.45,  # 기본값
                "rating_date": str(r[3]) if r[3] else None,
                "model_type": r[2],
                "rating_reason": r[4]
            }
            for r in ratings
        ],
        "facilities": [
            {
                "facility_id": f[0],
                "facility_type": f[1],
                "product_name": f[2] or f[1],
                "limit_amount": f[3],
                "outstanding_amount": f[4],
                "available_amount": f[5],
                "interest_rate": f[6],
                "start_date": str(f[7]) if f[7] else None,
                "maturity_date": str(f[8]) if f[8] else None,
                "status": f[9]
            }
            for f in facilities
        ],
        "facility_summary": {
            "total_count": facility_summary[0] if facility_summary else 0,
            "active_count": facility_summary[1] if facility_summary else 0,
            "total_limit": facility_summary[2] if facility_summary else 0,
            "total_outstanding": facility_summary[3] if facility_summary else 0,
            "total_available": facility_summary[4] if facility_summary else 0
        },
        "risk_metrics": {
            "total_rwa": rwa_info[0] if rwa_info else 0,
            "total_ead": rwa_info[1] if rwa_info else 0,
            "total_el": rwa_info[2] if rwa_info else 0
        },
        "industry_limit": {
            "limit_name": limit_info[0] if limit_info else None,
            "limit_amount": limit_info[1] if limit_info else None,
            "exposure_amount": limit_info[2] if limit_info else None,
            "utilization_rate": limit_info[3] if limit_info else None
        } if limit_info else None,
        "collaterals": [
            {
                "collateral_id": c[0],
                "collateral_type": c[1],
                "collateral_subtype": c[2],
                "original_value": c[3],
                "current_value": c[4],
                "ltv": c[5],
                "valuation_date": str(c[6]) if c[6] else None,
                "priority_rank": c[7],
                "facility_id": c[8]
            }
            for c in collaterals
        ],
        "applications": [
            {
                "application_id": a[0],
                "application_date": str(a[1]) if a[1] else None,
                "application_type": a[2],
                "product_name": a[3],
                "requested_amount": a[4],
                "status": a[5],
                "current_stage": a[6],
                "purpose_detail": a[7]
            }
            for a in applications
        ]
    }
