"""
대시보드 API
전략 대시보드, 요약 정보 제공
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..core.database import get_db

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """전략 대시보드 요약 정보"""

    # 자본 현황
    capital = db.execute(text("""
        SELECT * FROM capital_position
        ORDER BY base_date DESC LIMIT 1
    """)).fetchone()

    # 포트폴리오 현황 - facility 테이블에서 집계
    portfolio = db.execute(text("""
        SELECT
            COUNT(DISTINCT f.customer_id) as total_customers,
            SUM(f.approved_amount) as total_exposure,
            AVG(f.final_rate) as avg_rate
        FROM facility f
        WHERE f.status = 'ACTIVE'
    """)).fetchone()

    # 리스크 파라미터 평균
    risk_params = db.execute(text("""
        SELECT AVG(ttc_pd), AVG(lgd) FROM risk_parameter
    """)).fetchone()

    # 평균 RAROC
    avg_raroc = db.execute(text("""
        SELECT AVG(raroc) FROM portfolio_summary
    """)).fetchone()

    # 평균 등급
    avg_grade = db.execute(text("""
        SELECT cr.final_grade, COUNT(*) as cnt
        FROM credit_rating_result cr
        GROUP BY cr.final_grade
        ORDER BY cnt DESC
        LIMIT 1
    """)).fetchone()

    # 대기 심사 현황
    pending = db.execute(text("""
        SELECT COUNT(*) as count, SUM(requested_amount) as amount
        FROM loan_application
        WHERE status IN ('RECEIVED', 'REVIEWING')
    """)).fetchone()

    # 오늘 승인/반려
    today_approved = db.execute(text("""
        SELECT COUNT(*) FROM loan_application WHERE status = 'APPROVED'
    """)).fetchone()

    today_rejected = db.execute(text("""
        SELECT COUNT(*) FROM loan_application WHERE status = 'REJECTED'
    """)).fetchone()

    # 경보 현황
    limit_breaches = db.execute(text("""
        SELECT COUNT(*) FROM limit_exposure WHERE status IN ('WARNING', 'BREACH')
    """)).fetchone()

    model_alerts = db.execute(text("""
        SELECT COUNT(*) FROM model_performance_log WHERE alert_triggered = 1
    """)).fetchone()

    ews_count = db.execute(text("""
        SELECT COUNT(*) FROM ews_alert WHERE status = 'OPEN'
    """)).fetchone()

    # 단위 변환: DB는 십억원, 프론트엔드는 원 단위 기대
    UNIT = 1_000_000_000  # 십억원 -> 원

    return {
        "capital": {
            "bis_ratio": float(capital[10]) if capital else 0,  # DB에 이미 % 값으로 저장
            "tier1_ratio": float(capital[12]) if capital else 0,
            "cet1_ratio": float(capital[11]) if capital else 0,
            "leverage_ratio": float(capital[13]) if capital else 0,
            "total_capital": float(capital[5]) * UNIT if capital else 0,
            "total_rwa": float(capital[9]) * UNIT if capital else 0
        } if capital else {},
        "portfolio": {
            "total_customers": portfolio[0] if portfolio else 0,
            "total_exposure": float(portfolio[1]) if portfolio and portfolio[1] else 0,
            "avg_rate": float(portfolio[2] * 100) if portfolio and portfolio[2] else 0,
            "weighted_pd": float(risk_params[0]) if risk_params and risk_params[0] else 0.02,
            "weighted_lgd": float(risk_params[1]) if risk_params and risk_params[1] else 0.35,
            "avg_raroc": float(avg_raroc[0]) if avg_raroc and avg_raroc[0] else 15.0,  # DB에 이미 % 값으로 저장
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
def get_ews_alerts(db: Session = Depends(get_db)):
    """EWS 경보 목록"""
    results = db.execute(text("""
        SELECT e.alert_id, e.customer_id, c.customer_name,
               e.alert_date, e.alert_type, e.severity,
               e.description, e.indicator_value, e.threshold_value, e.status
        FROM ews_alert e
        JOIN customer c ON e.customer_id = c.customer_id
        WHERE e.status = 'OPEN'
        ORDER BY
            CASE e.severity
                WHEN 'HIGH' THEN 1
                WHEN 'MEDIUM' THEN 2
                ELSE 3
            END,
            e.alert_date DESC
        LIMIT 20
    """)).fetchall()

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
def get_kpis(db: Session = Depends(get_db)):
    """주요 KPI 현황"""

    # 포트폴리오 RAROC
    portfolio_raroc = db.execute(text("""
        SELECT AVG(raroc) FROM portfolio_summary
    """)).fetchone()

    # 평균 PD (ttc_pd 컬럼 사용)
    avg_pd = db.execute(text("""
        SELECT AVG(ttc_pd) FROM risk_parameter
    """)).fetchone()

    # 평균 LGD (lgd 컬럼 사용)
    avg_lgd = db.execute(text("""
        SELECT AVG(lgd) FROM risk_parameter
    """)).fetchone()

    return {
        "portfolio_raroc": float(portfolio_raroc[0]) if portfolio_raroc and portfolio_raroc[0] else 15.0,  # DB에 이미 % 값으로 저장
        "avg_pd": float(avg_pd[0]) if avg_pd and avg_pd[0] else 0.02,
        "avg_lgd": float(avg_lgd[0]) if avg_lgd and avg_lgd[0] else 0.35,
        "hurdle_rate": 15.0
    }


@router.get("/capital-trend")
def get_capital_trend(db: Session = Depends(get_db)):
    """자본비율 추이"""
    results = db.execute(text("""
        SELECT base_date, bis_ratio, cet1_ratio, tier1_ratio, leverage_ratio
        FROM capital_position
        ORDER BY base_date DESC
        LIMIT 12
    """)).fetchall()

    return [
        {
            "date": r[0],
            "bis_ratio": float(r[1]) if r[1] else 0,  # DB에 이미 % 값으로 저장
            "cet1_ratio": float(r[2]) if r[2] else 0,
            "tier1_ratio": float(r[3]) if r[3] else 0,
            "leverage_ratio": float(r[4]) if r[4] else 0
        }
        for r in reversed(results)
    ]


@router.get("/portfolio-distribution")
def get_portfolio_distribution(db: Session = Depends(get_db)):
    """포트폴리오 분포 현황"""

    # 산업별 분포
    industry_dist = db.execute(text("""
        SELECT c.industry_name, SUM(f.approved_amount) as exposure
        FROM facility f
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.status = 'ACTIVE'
        GROUP BY c.industry_name
        ORDER BY exposure DESC
    """)).fetchall()

    # 등급별 분포
    rating_dist = db.execute(text("""
        SELECT cr.final_grade, SUM(f.approved_amount) as exposure
        FROM facility f
        JOIN credit_rating_result cr ON f.customer_id = cr.customer_id
        WHERE f.status = 'ACTIVE'
        GROUP BY cr.final_grade
        ORDER BY cr.final_grade
    """)).fetchall()

    # 규모별 분포
    size_dist = db.execute(text("""
        SELECT c.size_category, SUM(f.approved_amount) as exposure
        FROM facility f
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.status = 'ACTIVE'
        GROUP BY c.size_category
    """)).fetchall()

    return {
        "by_industry": [{"name": r[0], "value": float(r[1]) if r[1] else 0} for r in industry_dist],
        "by_rating": [{"name": r[0], "value": float(r[1]) if r[1] else 0} for r in rating_dist],
        "by_size": [{"name": r[0], "value": float(r[1]) if r[1] else 0} for r in size_dist]
    }
