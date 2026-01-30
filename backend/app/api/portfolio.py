"""
포트폴리오 전략 API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..core.database import get_db

router = APIRouter(prefix="/api/portfolio", tags=["Portfolio"])


@router.get("/strategy-matrix")
def get_strategy_matrix(db: Session = Depends(get_db)):
    """산업-등급 전략 매트릭스"""
    results = db.execute(text("""
        SELECT industry_code, industry_name, rating_bucket, strategy_code, pricing_adj_bp
        FROM industry_rating_strategy
        ORDER BY industry_code, rating_bucket
    """)).fetchall()

    # 매트릭스 형태로 변환
    matrix = {}
    industries = []

    for r in results:
        ind_code = r[0]
        ind_name = r[1]
        rating = r[2]
        strategy = r[3]
        pricing = r[4]

        if ind_code not in matrix:
            matrix[ind_code] = {
                "industry_code": ind_code,
                "industry_name": ind_name,
                "strategies": {}
            }
            industries.append({"code": ind_code, "name": ind_name, "industry_code": ind_code, "industry_name": ind_name})

        # rating_bucket을 개별 등급으로도 매핑
        if rating == "AAA_AA":
            matrix[ind_code]["strategies"]["AAA"] = strategy
            matrix[ind_code]["strategies"]["AA"] = strategy
        elif rating == "A":
            matrix[ind_code]["strategies"]["A"] = strategy
        elif rating == "BBB":
            matrix[ind_code]["strategies"]["BBB"] = strategy
        elif rating == "BB_Below":
            matrix[ind_code]["strategies"]["BB"] = strategy
            matrix[ind_code]["strategies"]["B"] = strategy
            matrix[ind_code]["strategies"]["CCC"] = strategy

        matrix[ind_code]["strategies"][rating] = {
            "code": strategy,
            "pricing_adj_bp": pricing
        }

    # 전략별 익스포저 분포 계산
    strategy_exposure = db.execute(text("""
        SELECT irs.strategy_code, SUM(ps.total_exposure) as exposure
        FROM industry_rating_strategy irs
        JOIN portfolio_summary ps ON irs.industry_code = ps.segment_code
        WHERE ps.segment_type = 'INDUSTRY' AND irs.rating_bucket = 'AAA_AA'
        GROUP BY irs.strategy_code
    """)).fetchall()

    strategy_distribution = [
        {"strategy": r[0], "exposure": r[1] or 0}
        for r in strategy_exposure
    ]

    return {
        "industries": industries,
        "rating_buckets": ["AAA_AA", "A", "BBB", "BB_Below"],
        "matrix": list(matrix.values()),
        "strategy_distribution": strategy_distribution,
        "strategy_definitions": {
            "EXPAND": {"label": "확대", "color": "#22c55e", "description": "적극 확대"},
            "SELECTIVE": {"label": "선별", "color": "#84cc16", "description": "선별적 확대"},
            "MAINTAIN": {"label": "유지", "color": "#eab308", "description": "현상 유지"},
            "REDUCE": {"label": "축소", "color": "#f97316", "description": "점진적 축소"},
            "EXIT": {"label": "퇴출", "color": "#ef4444", "description": "신규 금지"}
        }
    }


@router.get("/summary")
def get_portfolio_summary(db: Session = Depends(get_db)):
    """포트폴리오 요약"""

    # 산업별
    by_industry = db.execute(text("""
        SELECT segment_code, segment_name, exposure_count, total_exposure,
               total_rwa, total_el, avg_pd, avg_lgd, weighted_rate, total_revenue, raroc
        FROM portfolio_summary
        WHERE segment_type = 'INDUSTRY'
        ORDER BY total_exposure DESC
    """)).fetchall()

    # 등급별
    by_rating = db.execute(text("""
        SELECT segment_code, segment_name, exposure_count, total_exposure,
               total_rwa, total_el, avg_pd, avg_lgd, weighted_rate, total_revenue, raroc
        FROM portfolio_summary
        WHERE segment_type = 'RATING'
        ORDER BY segment_code
    """)).fetchall()

    def format_summary(rows):
        return [
            {
                "segment_code": r[0],
                "segment_name": r[1],
                "count": r[2],
                "exposure": r[3],
                "rwa": r[4],
                "el": r[5],
                "avg_pd": r[6],
                "avg_lgd": r[7],
                "avg_rate": r[8],
                "revenue": r[9],
                "raroc": r[10]
            }
            for r in rows
        ]

    return {
        "by_industry": format_summary(by_industry),
        "by_rating": format_summary(by_rating)
    }


@router.get("/concentration")
def get_concentration_analysis(db: Session = Depends(get_db)):
    """집중도 분석"""

    # 상위 10 고객
    top_customers = db.execute(text("""
        SELECT c.customer_id, c.customer_name, c.industry_name,
               SUM(f.outstanding_amount) as exposure
        FROM facility f
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.status = 'ACTIVE'
        GROUP BY c.customer_id
        ORDER BY exposure DESC
        LIMIT 10
    """)).fetchall()

    # 상위 5 그룹
    top_groups = db.execute(text("""
        SELECT bg.group_id, bg.group_name, SUM(f.outstanding_amount) as exposure
        FROM borrower_group bg
        JOIN borrower_group_member bgm ON bg.group_id = bgm.group_id
        JOIN facility f ON bgm.customer_id = f.customer_id
        WHERE f.status = 'ACTIVE'
        GROUP BY bg.group_id
        ORDER BY exposure DESC
        LIMIT 5
    """)).fetchall()

    # 산업별 집중도
    industry_conc = db.execute(text("""
        SELECT c.industry_name, SUM(f.outstanding_amount) as exposure,
               COUNT(DISTINCT c.customer_id) as customer_count
        FROM facility f
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.status = 'ACTIVE'
        GROUP BY c.industry_name
        ORDER BY exposure DESC
    """)).fetchall()

    # 총 익스포저
    total = db.execute(text("""
        SELECT SUM(outstanding_amount) FROM facility WHERE status = 'ACTIVE'
    """)).fetchone()

    total_exposure = total[0] if total[0] else 1

    # 그룹별 계열사 수 조회
    group_member_counts = db.execute(text("""
        SELECT bg.group_id, COUNT(DISTINCT bgm.customer_id) as member_count
        FROM borrower_group bg
        LEFT JOIN borrower_group_member bgm ON bg.group_id = bgm.group_id
        GROUP BY bg.group_id
    """)).fetchall()
    member_count_map = {r[0]: r[1] for r in group_member_counts}

    # HHI 계산 (0-1 스케일)
    hhi_industry = sum([(r[1] / total_exposure) ** 2 for r in industry_conc]) if industry_conc else 0

    return {
        "top_customers": [
            {
                "customer_id": r[0],
                "customer_name": r[1],
                "industry_name": r[2],
                "exposure": r[3],
                "share": r[3] / total_exposure * 100,  # 프론트엔드 호환
                "concentration_pct": r[3] / total_exposure * 100
            }
            for r in top_customers
        ],
        "top_groups": [
            {
                "group_id": r[0],
                "group_name": r[1],
                "exposure": r[2],
                "share": r[2] / total_exposure * 100,  # 프론트엔드 호환
                "member_count": member_count_map.get(r[0], 0),  # 프론트엔드 호환
                "concentration_pct": r[2] / total_exposure * 100
            }
            for r in top_groups
        ],
        "by_industry": [  # 프론트엔드 호환 (industry_concentration 대신)
            {
                "industry_name": r[0],
                "exposure": r[1],
                "customer_count": r[2],
                "share": r[1] / total_exposure * 100,  # 프론트엔드 호환
                "concentration_pct": r[1] / total_exposure * 100
            }
            for r in industry_conc
        ],
        "industry_concentration": [
            {
                "industry_name": r[0],
                "exposure": r[1],
                "customer_count": r[2],
                "concentration_pct": r[1] / total_exposure * 100
            }
            for r in industry_conc
        ],
        "total_exposure": total_exposure,
        "hhi_industry": hhi_industry,  # 프론트엔드 호환 (0-1 스케일)
        "hhi": sum([(r[1] / total_exposure * 100) ** 2 for r in industry_conc])  # HHI 지수 (기존 호환)
    }


@router.get("/exposure-distribution")
def get_exposure_distribution(db: Session = Depends(get_db)):
    """익스포저 분포"""

    # 금액대별 분포
    by_amount = db.execute(text("""
        SELECT
            CASE
                WHEN outstanding_amount < 1000000000 THEN '10억 미만'
                WHEN outstanding_amount < 5000000000 THEN '10~50억'
                WHEN outstanding_amount < 10000000000 THEN '50~100억'
                WHEN outstanding_amount < 50000000000 THEN '100~500억'
                ELSE '500억 이상'
            END as bucket,
            COUNT(*) as count,
            SUM(outstanding_amount) as total
        FROM facility
        WHERE status = 'ACTIVE'
        GROUP BY bucket
        ORDER BY MIN(outstanding_amount)
    """)).fetchall()

    # 만기별 분포
    by_maturity = db.execute(text("""
        SELECT
            CASE
                WHEN julianday(maturity_date) - julianday('now') < 365 THEN '1년 이내'
                WHEN julianday(maturity_date) - julianday('now') < 730 THEN '1~2년'
                WHEN julianday(maturity_date) - julianday('now') < 1095 THEN '2~3년'
                ELSE '3년 초과'
            END as bucket,
            COUNT(*) as count,
            SUM(outstanding_amount) as total
        FROM facility
        WHERE status = 'ACTIVE'
        GROUP BY bucket
    """)).fetchall()

    # 상품별 분포
    by_product = db.execute(text("""
        SELECT p.product_name, COUNT(*) as count, SUM(f.outstanding_amount) as total
        FROM facility f
        JOIN product_master p ON f.product_code = p.product_code
        WHERE f.status = 'ACTIVE'
        GROUP BY f.product_code
        ORDER BY total DESC
    """)).fetchall()

    return {
        "by_amount": [{"bucket": r[0], "count": r[1], "total": r[2]} for r in by_amount],
        "by_maturity": [{"bucket": r[0], "count": r[1], "total": r[2]} for r in by_maturity],
        "by_product": [{"product": r[0], "count": r[1], "total": r[2]} for r in by_product]
    }


@router.get("/industry/{industry_code}")
def get_industry_detail(industry_code: str, db: Session = Depends(get_db)):
    """산업별 상세 현황"""

    # 산업 정보
    industry = db.execute(text("""
        SELECT * FROM industry_master WHERE industry_code = :code
    """), {"code": industry_code}).fetchone()

    # 전략 정보
    strategies = db.execute(text("""
        SELECT rating_bucket, strategy_code, pricing_adj_bp
        FROM industry_rating_strategy
        WHERE industry_code = :code
    """), {"code": industry_code}).fetchall()

    # 포트폴리오 요약
    summary = db.execute(text("""
        SELECT * FROM portfolio_summary
        WHERE segment_type = 'INDUSTRY' AND segment_code = :code
    """), {"code": industry_code}).fetchone()

    # 해당 산업 고객 목록
    customers = db.execute(text("""
        SELECT c.customer_id, c.customer_name, c.size_category,
               cr.final_grade, SUM(f.outstanding_amount) as exposure
        FROM customer c
        LEFT JOIN facility f ON c.customer_id = f.customer_id
        LEFT JOIN credit_rating_result cr ON c.customer_id = cr.customer_id
        WHERE c.industry_code = :code AND f.status = 'ACTIVE'
        GROUP BY c.customer_id
        ORDER BY exposure DESC
        LIMIT 20
    """), {"code": industry_code}).fetchall()

    # 한도 현황
    limit_info = db.execute(text("""
        SELECT ld.limit_amount, le.exposure_amount, le.utilization_rate, le.status
        FROM limit_definition ld
        LEFT JOIN limit_exposure le ON ld.limit_id = le.limit_id
        WHERE ld.dimension_code = :code
    """), {"code": industry_code}).fetchone()

    # 등급별 분포 계산
    grade_distribution = db.execute(text("""
        SELECT cr.final_grade, COUNT(*) as cnt, SUM(f.outstanding_amount) as exposure
        FROM customer c
        JOIN facility f ON c.customer_id = f.customer_id
        LEFT JOIN (
            SELECT customer_id, final_grade
            FROM credit_rating_result
            GROUP BY customer_id
        ) cr ON c.customer_id = cr.customer_id
        WHERE c.industry_code = :code AND f.status = 'ACTIVE'
        GROUP BY cr.final_grade
        ORDER BY cr.final_grade
    """), {"code": industry_code}).fetchall()

    total_exposure = sum(g[2] or 0 for g in grade_distribution) if grade_distribution else 1

    # 평균 등급 계산
    grade_order = ['AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-', 'BBB+', 'BBB', 'BBB-', 'BB+', 'BB', 'BB-', 'B+', 'B', 'B-']
    weighted_grade = 0
    weight_sum = 0
    for g in grade_distribution:
        if g[0] in grade_order and g[2]:
            weighted_grade += grade_order.index(g[0]) * g[2]
            weight_sum += g[2]
    avg_grade_idx = int(weighted_grade / weight_sum) if weight_sum > 0 else 8
    avg_grade = grade_order[min(avg_grade_idx, len(grade_order) - 1)] if grade_distribution else '-'

    industry_name = industry[1] if industry else '알 수 없음'

    return {
        # 프론트엔드 호환: 최상위 레벨에 필드 추가
        "industry_code": industry_code,
        "industry_name": industry_name,
        "total_exposure": summary[6] if summary else 0,
        "avg_grade": avg_grade,
        "avg_raroc": float(summary[13] * 100) if summary and summary[13] else 0,
        "limit_usage": float(limit_info[2]) if limit_info and limit_info[2] else 0,
        "by_grade": [
            {
                "grade": g[0] or '미평가',
                "count": g[1],
                "exposure": g[2] or 0,
                "share": (g[2] or 0) / total_exposure * 100 if total_exposure else 0
            }
            for g in grade_distribution
        ],
        # 기존 구조 유지
        "industry": {
            "code": industry[0] if industry else None,
            "name": industry_name,
            "risk_grade": industry[4] if industry else None,
            "outlook": industry[5] if industry else None
        } if industry else None,
        "strategies": [
            {"rating": s[0], "strategy": s[1], "pricing_adj": s[2]}
            for s in strategies
        ],
        "summary": {
            "count": summary[5] if summary else 0,
            "exposure": summary[6] if summary else 0,
            "rwa": summary[7] if summary else 0,
            "el": summary[8] if summary else 0,
            "avg_pd": summary[9] if summary else 0,
            "raroc": float(summary[13] * 100) if summary and summary[13] else 0
        } if summary else None,
        "customers": [
            {
                "customer_id": c[0],
                "customer_name": c[1],
                "size_category": c[2],
                "grade": c[3],
                "exposure": c[4]
            }
            for c in customers
        ],
        "limit": {
            "limit_amount": limit_info[0] if limit_info else 0,
            "exposure": limit_info[1] if limit_info else 0,
            "utilization": limit_info[2] if limit_info else 0,
            "status": limit_info[3] if limit_info else "N/A"
        } if limit_info else None
    }
