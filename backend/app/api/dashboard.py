"""
대시보드 API
전략 대시보드, 요약 정보 제공
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..core.database import get_db

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def _region_filter(alias: str, region: str = None):
    """지역 필터 SQL 조건 생성"""
    if not region:
        return "", {}
    return f" AND {alias}.region = :region", {"region": region}


@router.get("/summary")
def get_dashboard_summary(region: str = Query(None), db: Session = Depends(get_db)):
    """전략 대시보드 요약 정보"""

    region_cond, region_params = _region_filter("c", region)

    # 자본 현황 (은행 전체 - 지역 무관)
    capital = db.execute(text("""
        SELECT * FROM capital_position
        ORDER BY base_date DESC LIMIT 1
    """)).fetchone()

    # 포트폴리오 현황 - 지역 필터 적용
    portfolio = db.execute(text(f"""
        SELECT
            COUNT(DISTINCT f.customer_id) as total_customers,
            SUM(f.approved_amount) as total_exposure,
            AVG(f.final_rate) as avg_rate
        FROM facility f
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.status = 'ACTIVE' {region_cond}
    """), region_params).fetchone()

    # 리스크 파라미터 평균 - 지역 필터 적용
    risk_params = db.execute(text(f"""
        SELECT AVG(rp.ttc_pd), AVG(rp.lgd)
        FROM risk_parameter rp
        JOIN facility f ON rp.application_id = f.application_id
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE 1=1 {region_cond}
    """), region_params).fetchone()

    # 포트폴리오 RAROC = (총이자수익 - 총비용 - 총EL) / (총RWA * 8%)
    avg_raroc = db.execute(text(f"""
        SELECT CASE WHEN SUM(rp.rwa) * 0.08 > 0
            THEN (SUM(f.outstanding_amount * f.final_rate) - SUM(f.outstanding_amount) * 0.048 - SUM(rp.expected_loss))
                 / (SUM(rp.rwa) * 0.08)
            ELSE 0 END
        FROM facility f
        JOIN risk_parameter rp ON f.application_id = rp.application_id
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.status = 'ACTIVE' {region_cond}
    """), region_params).fetchone()

    # 평균 등급 - 지역 필터 적용
    avg_grade = db.execute(text(f"""
        SELECT cr.final_grade, COUNT(*) as cnt
        FROM credit_rating_result cr
        JOIN customer c ON cr.customer_id = c.customer_id
        WHERE 1=1 {region_cond}
        GROUP BY cr.final_grade
        ORDER BY cnt DESC
        LIMIT 1
    """), region_params).fetchone()

    # 대기 심사 현황 - 지역 필터 적용
    pending = db.execute(text(f"""
        SELECT COUNT(*) as count, SUM(la.requested_amount) as amount
        FROM loan_application la
        JOIN customer c ON la.customer_id = c.customer_id
        WHERE la.status IN ('RECEIVED', 'REVIEWING') {region_cond}
    """), region_params).fetchone()

    # 승인/반려 - 지역 필터 적용
    today_approved = db.execute(text(f"""
        SELECT COUNT(*) FROM loan_application la
        JOIN customer c ON la.customer_id = c.customer_id
        WHERE la.status = 'APPROVED' {region_cond}
    """), region_params).fetchone()

    today_rejected = db.execute(text(f"""
        SELECT COUNT(*) FROM loan_application la
        JOIN customer c ON la.customer_id = c.customer_id
        WHERE la.status = 'REJECTED' {region_cond}
    """), region_params).fetchone()

    # 경보 현황
    limit_breaches = db.execute(text("""
        SELECT COUNT(*) FROM limit_exposure WHERE status IN ('WARNING', 'BREACH')
    """)).fetchone()

    model_alerts = db.execute(text("""
        SELECT COUNT(*) FROM model_performance_log WHERE alert_triggered = 1
    """)).fetchone()

    # EWS - 지역 필터 적용
    ews_count = db.execute(text(f"""
        SELECT COUNT(*) FROM ews_alert e
        JOIN customer c ON e.customer_id = c.customer_id
        WHERE e.status = 'OPEN' {region_cond}
    """), region_params).fetchone()

    # DB는 원 단위, 비율은 소수(0.1663)로 저장
    return {
        "capital": {
            "bis_ratio": round(float(capital[10]) * 100, 2) if capital else 0,
            "tier1_ratio": round(float(capital[12]) * 100, 2) if capital else 0,
            "cet1_ratio": round(float(capital[11]) * 100, 2) if capital else 0,
            "leverage_ratio": round(float(capital[13]) * 100, 2) if capital else 0,
            "total_capital": float(capital[5]) if capital else 0,
            "total_rwa": float(capital[9]) if capital else 0
        } if capital else {},
        "portfolio": {
            "total_customers": portfolio[0] if portfolio else 0,
            "total_exposure": float(portfolio[1]) if portfolio and portfolio[1] else 0,
            "avg_rate": float(portfolio[2] * 100) if portfolio and portfolio[2] else 0,
            "weighted_pd": float(risk_params[0]) if risk_params and risk_params[0] else 0.02,
            "weighted_lgd": float(risk_params[1]) if risk_params and risk_params[1] else 0.35,
            "avg_raroc": float(avg_raroc[0]) * 100 if avg_raroc and avg_raroc[0] else 15.0,
            "avg_rating": avg_grade[0] if avg_grade else "BBB"
        },
        "applications": {
            "pending_count": pending[0] if pending else 0,
            "pending_amount": float(pending[1]) if pending and pending[1] else 0,
            "approved_today": today_approved[0] if today_approved else 0,
            "rejected_today": today_rejected[0] if today_rejected else 0
        },
        "alerts": {
            "capital_warnings": 0,
            "limit_breaches": limit_breaches[0] if limit_breaches else 0,
            "model_alerts": model_alerts[0] if model_alerts else 0,
            "ews_triggers": ews_count[0] if ews_count else 0
        }
    }


@router.get("/ews-alerts")
def get_ews_alerts(region: str = Query(None), db: Session = Depends(get_db)):
    """EWS 경보 목록"""
    region_cond, region_params = _region_filter("c", region)

    results = db.execute(text(f"""
        SELECT e.alert_id, e.customer_id, c.customer_name,
               e.alert_date, e.alert_type, e.severity,
               e.description, e.indicator_value, e.threshold_value, e.status
        FROM ews_alert e
        JOIN customer c ON e.customer_id = c.customer_id
        WHERE e.status = 'OPEN' {region_cond}
        ORDER BY
            CASE e.severity
                WHEN 'HIGH' THEN 1
                WHEN 'MEDIUM' THEN 2
                ELSE 3
            END,
            e.alert_date DESC
        LIMIT 20
    """), region_params).fetchall()

    return [
        {
            "alert_id": r[0],
            "customer_id": r[1],
            "customer_name": r[2],
            "alert_date": r[3],
            "alert_type": r[4],
            "severity": r[5],
            "trigger_condition": r[6],
            "current_value": r[7],
            "threshold_value": r[8],
            "status": r[9]
        }
        for r in results
    ]


@router.get("/kpis")
def get_kpis(region: str = Query(None), db: Session = Depends(get_db)):
    """주요 KPI 현황"""
    region_cond, region_params = _region_filter("c", region)

    # 포트폴리오 RAROC - 지역 필터 (summary와 동일한 산출식 사용)
    portfolio_raroc = db.execute(text(f"""
        SELECT CASE WHEN SUM(rp.rwa) * 0.08 > 0
            THEN (SUM(f.outstanding_amount * f.final_rate) - SUM(f.outstanding_amount) * 0.048 - SUM(rp.expected_loss))
                 / (SUM(rp.rwa) * 0.08)
            ELSE 0 END
        FROM facility f
        JOIN risk_parameter rp ON f.application_id = rp.application_id
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.status = 'ACTIVE' {region_cond}
    """), region_params).fetchone()

    # 평균 PD - 지역 필터
    avg_pd = db.execute(text(f"""
        SELECT AVG(rp.ttc_pd) FROM risk_parameter rp
        JOIN facility f ON rp.application_id = f.application_id
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE 1=1 {region_cond}
    """), region_params).fetchone()

    # 평균 LGD - 지역 필터
    avg_lgd = db.execute(text(f"""
        SELECT AVG(rp.lgd) FROM risk_parameter rp
        JOIN facility f ON rp.application_id = f.application_id
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE 1=1 {region_cond}
    """), region_params).fetchone()

    return {
        "portfolio_raroc": float(portfolio_raroc[0]) * 100 if portfolio_raroc and portfolio_raroc[0] else 15.0,
        "avg_pd": float(avg_pd[0]) if avg_pd and avg_pd[0] else 0.02,
        "avg_lgd": float(avg_lgd[0]) if avg_lgd and avg_lgd[0] else 0.35,
        "hurdle_rate": 15.0
    }


@router.get("/capital-trend")
def get_capital_trend(db: Session = Depends(get_db)):
    """자본비율 추이 (은행 전체)"""
    results = db.execute(text("""
        SELECT base_date, bis_ratio, cet1_ratio, tier1_ratio, leverage_ratio
        FROM capital_position
        ORDER BY base_date DESC
        LIMIT 24
    """)).fetchall()

    return [
        {
            "date": r[0][:7] if r[0] else r[0],
            "bis": round(float(r[1]) * 100, 2) if r[1] else 0,
            "cet1": round(float(r[2]) * 100, 2) if r[2] else 0,
            "tier1": round(float(r[3]) * 100, 2) if r[3] else 0,
            "leverage": round(float(r[4]) * 100, 2) if r[4] else 0
        }
        for r in reversed(results)
    ]


@router.get("/portfolio-distribution")
def get_portfolio_distribution(region: str = Query(None), db: Session = Depends(get_db)):
    """포트폴리오 분포 현황"""
    region_cond, region_params = _region_filter("c", region)

    # 산업별 분포
    industry_dist = db.execute(text(f"""
        SELECT c.industry_name, SUM(f.approved_amount) as exposure
        FROM facility f
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.status = 'ACTIVE' {region_cond}
        GROUP BY c.industry_name
        ORDER BY exposure DESC
    """), region_params).fetchall()

    # 등급별 분포
    rating_dist = db.execute(text(f"""
        SELECT cr.final_grade, SUM(f.approved_amount) as exposure
        FROM facility f
        JOIN credit_rating_result cr ON f.customer_id = cr.customer_id
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.status = 'ACTIVE' {region_cond}
        GROUP BY cr.final_grade
        ORDER BY cr.final_grade
    """), region_params).fetchall()

    # 규모별 분포
    size_dist = db.execute(text(f"""
        SELECT c.size_category, SUM(f.approved_amount) as exposure
        FROM facility f
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.status = 'ACTIVE' {region_cond}
        GROUP BY c.size_category
    """), region_params).fetchall()

    return {
        "by_industry": [{"name": r[0], "value": float(r[1]) if r[1] else 0} for r in industry_dist],
        "by_rating": [{"name": r[0], "value": float(r[1]) if r[1] else 0} for r in rating_dist],
        "by_size": [{"name": r[0], "value": float(r[1]) if r[1] else 0} for r in size_dist]
    }
