"""
지역별 산업 포트폴리오 집계 헬퍼
region 필터 지정 시 customer+facility+risk_parameter 테이블에서 직접 집계
region=None이면 기존 portfolio_summary 테이블 사용
"""
from sqlalchemy.orm import Session
from sqlalchemy import text


VALID_REGIONS = {'CAPITAL', 'DAEGU_GB', 'BUSAN_GN'}

# RAROC 계산용 비용률 상수 (calculations.py calculate_raroc()와 일관)
FUNDING_RATE = 0.043   # 조달비용 4.3% (기본 3.5% + FTP 0.8%)
OPEX_RATE = 0.005      # 운영비 0.5%
COST_RATE = FUNDING_RATE + OPEX_RATE  # 4.8%


def get_industry_portfolio(db: Session, region: str = None):
    """
    산업별 포트폴리오 지표를 반환.
    region이 None이면 portfolio_summary 테이블에서 조회 (기존 로직).
    region이 지정되면 customer+facility+risk_parameter JOIN으로 직접 집계.
    """
    if not region:
        rows = db.execute(text("""
            SELECT segment_code, segment_name,
                   exposure_count, total_exposure, total_rwa, total_el,
                   avg_pd, avg_lgd, weighted_rate, total_revenue, raroc
            FROM portfolio_summary
            WHERE segment_type = 'INDUSTRY'
            ORDER BY total_exposure DESC
        """)).fetchall()
        return [_format_row(r) for r in rows]

    if region not in VALID_REGIONS:
        return []

    rows = db.execute(text("""
        SELECT
            c.industry_code,
            c.industry_name,
            COUNT(DISTINCT c.customer_id) as exposure_count,
            COALESCE(SUM(f.outstanding_amount), 0) as total_exposure,
            COALESCE(SUM(rp.rwa), 0) as total_rwa,
            COALESCE(SUM(rp.expected_loss), 0) as total_el,
            AVG(COALESCE(rp.pit_pd, rp.ttc_pd)) as avg_pd,
            AVG(rp.lgd) as avg_lgd,
            AVG(f.final_rate) as weighted_rate,
            COALESCE(SUM(f.outstanding_amount * f.final_rate), 0) as total_revenue,
            CASE
                WHEN SUM(rp.rwa) * 0.105 > 0
                THEN (SUM(f.outstanding_amount * f.final_rate) - SUM(f.outstanding_amount) * :cost_rate - SUM(rp.expected_loss)) / (SUM(rp.rwa) * 0.105)
                ELSE 0
            END as raroc
        FROM customer c
        JOIN facility f ON c.customer_id = f.customer_id AND f.status = 'ACTIVE'
        LEFT JOIN loan_application la ON f.application_id = la.application_id
        LEFT JOIN risk_parameter rp ON la.application_id = rp.application_id
        WHERE c.region = :region
        GROUP BY c.industry_code, c.industry_name
        ORDER BY total_exposure DESC
    """), {"region": region, "cost_rate": COST_RATE}).fetchall()

    return [_format_dynamic_row(r) for r in rows]


def get_industry_portfolio_for_efficiency(db: Session, region: str = None):
    """
    자본 효율성 분석용 산업별 데이터.
    segment_type, segment_code 등 efficiency 엔드포인트가 기대하는 형식으로 반환.
    """
    if not region:
        rows = db.execute(text("""
            SELECT segment_type, segment_code, segment_name,
                   total_exposure, total_rwa, total_el, total_revenue, raroc
            FROM portfolio_summary
            WHERE segment_type = 'INDUSTRY'
            ORDER BY raroc DESC
        """)).fetchall()
        return rows  # raw rows 반환 (기존 코드 호환)

    if region not in VALID_REGIONS:
        return []

    rows = db.execute(text("""
        SELECT
            'INDUSTRY' as segment_type,
            c.industry_code as segment_code,
            c.industry_name as segment_name,
            COALESCE(SUM(f.outstanding_amount), 0) as total_exposure,
            COALESCE(SUM(rp.rwa), 0) as total_rwa,
            COALESCE(SUM(rp.expected_loss), 0) as total_el,
            COALESCE(SUM(f.outstanding_amount * f.final_rate), 0) as total_revenue,
            CASE
                WHEN SUM(rp.rwa) * 0.105 > 0
                THEN (SUM(f.outstanding_amount * f.final_rate) - SUM(f.outstanding_amount) * :cost_rate - SUM(rp.expected_loss)) / (SUM(rp.rwa) * 0.105)
                ELSE 0
            END as raroc
        FROM customer c
        JOIN facility f ON c.customer_id = f.customer_id AND f.status = 'ACTIVE'
        LEFT JOIN loan_application la ON f.application_id = la.application_id
        LEFT JOIN risk_parameter rp ON la.application_id = rp.application_id
        WHERE c.region = :region
        GROUP BY c.industry_code, c.industry_name
        ORDER BY raroc DESC
    """), {"region": region, "cost_rate": COST_RATE}).fetchall()
    return rows


def get_industry_portfolio_with_rwa_density(db: Session, region: str = None):
    """
    RWA 밀도 분석용 산업별 데이터.
    capital_optimizer의 rwa-optimization 엔드포인트용.
    """
    if not region:
        return db.execute(text("""
            SELECT segment_name, segment_code, total_exposure, total_rwa,
                   ROUND(total_rwa * 100.0 / NULLIF(total_exposure, 0), 2) as rwa_density,
                   raroc
            FROM portfolio_summary
            WHERE segment_type = 'INDUSTRY'
            ORDER BY total_rwa * 100.0 / NULLIF(total_exposure, 0) DESC
        """)).fetchall()

    if region not in VALID_REGIONS:
        return []

    return db.execute(text("""
        SELECT
            c.industry_name as segment_name,
            c.industry_code as segment_code,
            COALESCE(SUM(f.outstanding_amount), 0) as total_exposure,
            COALESCE(SUM(rp.rwa), 0) as total_rwa,
            ROUND(COALESCE(SUM(rp.rwa), 0) * 100.0 / NULLIF(SUM(f.outstanding_amount), 0), 2) as rwa_density,
            CASE
                WHEN SUM(rp.rwa) * 0.105 > 0
                THEN (SUM(f.outstanding_amount * f.final_rate) - SUM(f.outstanding_amount) * :cost_rate - SUM(rp.expected_loss)) / (SUM(rp.rwa) * 0.105)
                ELSE 0
            END as raroc
        FROM customer c
        JOIN facility f ON c.customer_id = f.customer_id AND f.status = 'ACTIVE'
        LEFT JOIN loan_application la ON f.application_id = la.application_id
        LEFT JOIN risk_parameter rp ON la.application_id = rp.application_id
        WHERE c.region = :region
        GROUP BY c.industry_code, c.industry_name
        ORDER BY rwa_density DESC
    """), {"region": region, "cost_rate": COST_RATE}).fetchall()


def get_concentration_by_region(db: Session, region: str = None):
    """
    집중도 분석용 region 필터가 적용된 쿼리 조건 반환.
    region이 None이면 빈 문자열 (기존 동작).
    """
    if not region or region not in VALID_REGIONS:
        return "", {}
    return "AND c.region = :region", {"region": region}


def get_portfolio_aggregates(db: Session, region: str = None):
    """
    포트폴리오 전체 집계 (efficiency-dashboard 등에서 사용).
    """
    if not region:
        return db.execute(text("""
            SELECT (SUM(total_revenue) - SUM(total_exposure) * :cost_rate - SUM(total_el)) / NULLIF(SUM(total_rwa) * 0.105, 0) as portfolio_raroc,
                   SUM(total_exposure) as total_exposure,
                   SUM(total_rwa) as total_rwa,
                   SUM(total_el) as total_el
            FROM portfolio_summary WHERE segment_type = 'INDUSTRY'
        """), {"cost_rate": COST_RATE}).fetchone()

    if region not in VALID_REGIONS:
        return None

    return db.execute(text("""
        SELECT
            CASE
                WHEN SUM(rp.rwa) * 0.105 > 0
                THEN (SUM(f.outstanding_amount * f.final_rate) - SUM(f.outstanding_amount) * :cost_rate - SUM(rp.expected_loss)) / (SUM(rp.rwa) * 0.105)
                ELSE 0
            END as portfolio_raroc,
            COALESCE(SUM(f.outstanding_amount), 0) as total_exposure,
            COALESCE(SUM(rp.rwa), 0) as total_rwa,
            COALESCE(SUM(rp.expected_loss), 0) as total_el
        FROM customer c
        JOIN facility f ON c.customer_id = f.customer_id AND f.status = 'ACTIVE'
        LEFT JOIN loan_application la ON f.application_id = la.application_id
        LEFT JOIN risk_parameter rp ON la.application_id = rp.application_id
        WHERE c.region = :region
    """), {"region": region, "cost_rate": COST_RATE}).fetchone()


def get_rwa_density_aggregate(db: Session, region: str = None):
    """RWA 밀도 평균 (efficiency-dashboard용)."""
    if not region:
        return db.execute(text("""
            SELECT SUM(total_rwa) / SUM(total_exposure) as avg_density
            FROM portfolio_summary WHERE segment_type = 'INDUSTRY'
        """)).fetchone()

    if region not in VALID_REGIONS:
        return None

    return db.execute(text("""
        SELECT COALESCE(SUM(rp.rwa), 0) / NULLIF(SUM(f.outstanding_amount), 0) as avg_density
        FROM customer c
        JOIN facility f ON c.customer_id = f.customer_id AND f.status = 'ACTIVE'
        LEFT JOIN loan_application la ON f.application_id = la.application_id
        LEFT JOIN risk_parameter rp ON la.application_id = rp.application_id
        WHERE c.region = :region
    """), {"region": region}).fetchone()


def _format_row(r):
    """portfolio_summary 행 포맷"""
    return {
        "segment_code": r[0],
        "segment_name": r[1],
        "exposure_count": r[2],
        "total_exposure": float(r[3]) if r[3] else 0,
        "total_rwa": float(r[4]) if r[4] else 0,
        "total_el": float(r[5]) if r[5] else 0,
        "avg_pd": float(r[6]) if r[6] else 0,
        "avg_lgd": float(r[7]) if r[7] else 0,
        "weighted_rate": float(r[8]) if r[8] else 0,
        "total_revenue": float(r[9]) if r[9] else 0,
        "raroc": float(r[10]) if r[10] else 0,
    }


def _format_dynamic_row(r):
    """동적 집계 행 포맷"""
    return {
        "segment_code": r[0],
        "segment_name": r[1],
        "exposure_count": r[2],
        "total_exposure": float(r[3]) if r[3] else 0,
        "total_rwa": float(r[4]) if r[4] else 0,
        "total_el": float(r[5]) if r[5] else 0,
        "avg_pd": float(r[6]) if r[6] else 0,
        "avg_lgd": float(r[7]) if r[7] else 0,
        "weighted_rate": float(r[8]) if r[8] else 0,
        "total_revenue": float(r[9]) if r[9] else 0,
        "raroc": float(r[10]) if r[10] else 0,
    }
