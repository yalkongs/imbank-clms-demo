"""
자본관리 API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..core.database import get_db
from ..services.calculations import calculate_capital_ratios

router = APIRouter(prefix="/api/capital", tags=["Capital"])


@router.get("/position")
def get_capital_position(db: Session = Depends(get_db)):
    """현재 자본 포지션"""
    result = db.execute(text("""
        SELECT * FROM capital_position
        ORDER BY base_date DESC LIMIT 1
    """)).fetchone()

    if not result:
        return None

    # 데이터가 십억원 단위로 저장되어 있으므로 원 단위로 변환 (십억원 * 1,000,000,000)
    UNIT = 1_000_000_000  # 십억원 -> 원
    return {
        "position_id": result[0],
        "base_date": result[1],
        "cet1_capital": float(result[2]) * UNIT if result[2] else 0,
        "at1_capital": float(result[3]) * UNIT if result[3] else 0,
        "tier1_capital": (float(result[2]) + float(result[3])) * UNIT if result[2] and result[3] else 0,
        "tier2_capital": float(result[4]) * UNIT if result[4] else 0,
        "total_capital": float(result[5]) * UNIT if result[5] else 0,
        "credit_rwa": float(result[6]) * UNIT if result[6] else 0,
        "market_rwa": float(result[7]) * UNIT if result[7] else 0,
        "operational_rwa": float(result[8]) * UNIT if result[8] else 0,
        "total_rwa": float(result[9]) * UNIT if result[9] else 0,
        "bis_ratio": float(result[10]) if result[10] else 0,
        "cet1_ratio": float(result[11]) if result[11] else 0,
        "tier1_ratio": float(result[12]) if result[12] else 0,
        "leverage_ratio": float(result[13]) if result[13] else 0,
        "regulatory_minimums": {
            "bis_ratio": 10.5,
            "cet1_ratio": 7.0,
            "tier1_ratio": 8.5,
            "leverage_ratio": 3.0
        },
        "internal_targets": {
            "bis_ratio": 13.0,
            "cet1_ratio": 10.0,
            "tier1_ratio": 11.0,
            "leverage_ratio": 5.0
        }
    }


@router.get("/trend")
def get_capital_trend(months: int = 12, db: Session = Depends(get_db)):
    """자본비율 추이"""
    results = db.execute(text(f"""
        SELECT base_date, bis_ratio, cet1_ratio, tier1_ratio, leverage_ratio,
               total_capital, total_rwa
        FROM capital_position
        ORDER BY base_date DESC
        LIMIT {months}
    """)).fetchall()

    UNIT = 1_000_000_000  # 십억원 -> 원
    return [
        {
            "period": r[0],
            "bis_ratio": float(r[1]) if r[1] else 0,
            "cet1_ratio": float(r[2]) if r[2] else 0,
            "tier1_ratio": float(r[3]) if r[3] else 0,
            "leverage_ratio": float(r[4]) if r[4] else 0,
            "total_capital": float(r[5]) * UNIT if r[5] else 0,
            "total_rwa": float(r[6]) * UNIT if r[6] else 0
        }
        for r in reversed(results)
    ]


@router.get("/budget")
def get_capital_budget(db: Session = Depends(get_db)):
    """자본예산 현황"""
    results = db.execute(text("""
        SELECT budget_id, segment_type, segment_code, segment_name,
               rwa_budget, rwa_used, el_budget, el_used,
               revenue_target, revenue_actual, raroc_target
        FROM capital_budget
        WHERE status = 'ACTIVE'
        ORDER BY segment_type, segment_code
    """)).fetchall()

    by_segment = [
        {
            "segment": r[3],
            "segment_code": r[2],
            "rwa_budget": float(r[4]) if r[4] else 0,
            "rwa_actual": float(r[5]) if r[5] else 0,
            "el_budget": float(r[6]) if r[6] else 0,
            "el_actual": float(r[7]) if r[7] else 0,
            "revenue_target": float(r[8]) if r[8] else 0,
            "revenue_actual": float(r[9]) if r[9] else 0,
            "raroc_target": float(r[10]) if r[10] else 0
        }
        for r in results
    ]

    return {
        "by_segment": by_segment
    }


@router.get("/rwa-composition")
def get_rwa_composition(db: Session = Depends(get_db)):
    """RWA 구성 분석"""

    # 리스크 유형별
    position = db.execute(text("""
        SELECT credit_rwa, market_rwa, operational_rwa, total_rwa
        FROM capital_position
        ORDER BY base_date DESC LIMIT 1
    """)).fetchone()

    # 산업별 RWA
    by_industry = db.execute(text("""
        SELECT segment_name, total_rwa
        FROM portfolio_summary
        WHERE segment_type = 'INDUSTRY'
        ORDER BY total_rwa DESC
    """)).fetchall()

    # 등급별 RWA
    by_rating = db.execute(text("""
        SELECT segment_name, total_rwa
        FROM portfolio_summary
        WHERE segment_type = 'RATING'
        ORDER BY segment_code
    """)).fetchall()

    return {
        "by_risk_type": [
            {"name": "신용 RWA", "value": position[0] if position else 0},
            {"name": "시장 RWA", "value": position[1] if position else 0},
            {"name": "운영 RWA", "value": position[2] if position else 0}
        ],
        "by_industry": [{"name": r[0], "value": r[1]} for r in by_industry],
        "by_rating": [{"name": r[0], "value": r[1]} for r in by_rating],
        "total_rwa": position[3] if position else 0
    }


@router.get("/simulate")
def simulate_capital_impact(
    new_exposure: float,
    pd: float = 0.02,
    lgd: float = 0.45,
    db: Session = Depends(get_db)
):
    """신규 익스포저의 자본비율 영향 시뮬레이션"""
    from ..services.calculations import calculate_rwa

    # 현재 자본 포지션
    current = db.execute(text("""
        SELECT cet1_capital, at1_capital, tier2_capital,
               credit_rwa, market_rwa, operational_rwa
        FROM capital_position
        ORDER BY base_date DESC LIMIT 1
    """)).fetchone()

    if not current:
        return {"error": "No capital position data"}

    # 신규 RWA 계산
    new_rwa = calculate_rwa(pd, lgd, new_exposure)

    # 현재 비율
    total_capital = current[0] + current[1] + current[2]
    tier1_capital = current[0] + current[1]
    current_total_rwa = current[3] + current[4] + current[5]

    current_bis = total_capital / current_total_rwa
    current_cet1 = current[0] / current_total_rwa

    # 신규 후 비율
    new_total_rwa = current_total_rwa + new_rwa
    new_bis = total_capital / new_total_rwa
    new_cet1 = current[0] / new_total_rwa

    # 자본여력 계산
    current_buffer = total_capital - current_total_rwa * 0.105
    new_buffer = total_capital - new_total_rwa * 0.105

    return {
        "new_exposure": new_exposure,
        "additional_rwa": new_rwa,
        "current_bis_ratio": current_bis * 100,
        "new_bis_ratio": new_bis * 100,
        "bis_ratio_change": (new_bis - current_bis) * 100,
        "capital_buffer_change": new_buffer - current_buffer,
        "current": {
            "total_rwa": current_total_rwa,
            "bis_ratio": current_bis * 100,
            "cet1_ratio": current_cet1 * 100
        },
        "projected": {
            "total_rwa": new_total_rwa,
            "bis_ratio": new_bis * 100,
            "cet1_ratio": new_cet1 * 100
        }
    }


@router.get("/efficiency")
def get_capital_efficiency(db: Session = Depends(get_db)):
    """자본 효율성 분석"""

    # 산업별 RAROC
    by_industry = db.execute(text("""
        SELECT segment_type, segment_code, segment_name,
               total_exposure, total_rwa, total_el, total_revenue, raroc
        FROM portfolio_summary
        WHERE segment_type = 'INDUSTRY'
        ORDER BY raroc DESC
    """)).fetchall()

    # 등급별 RAROC
    by_rating = db.execute(text("""
        SELECT segment_type, segment_code, segment_name,
               total_exposure, total_rwa, total_el, total_revenue, raroc
        FROM portfolio_summary
        WHERE segment_type = 'RATING'
        ORDER BY segment_code
    """)).fetchall()

    # Hurdle Rate
    hurdle = db.execute(text("""
        SELECT hurdle_raroc, target_raroc FROM hurdle_rate
        WHERE segment_type IS NULL LIMIT 1
    """)).fetchone()

    hurdle_rate = hurdle[0] if hurdle else 0.12
    target_rate = hurdle[1] if hurdle else 0.15

    def format_segments(segments):
        result = []
        for s in segments:
            raroc_pct = float(s[7] * 100) if s[7] else 0
            result.append({
                "segment": s[2],
                "segment_code": s[1],
                "exposure": float(s[3]) if s[3] else 0,
                "rwa": float(s[4]) if s[4] else 0,
                "el": float(s[5]) if s[5] else 0,
                "revenue": float(s[6]) if s[6] else 0,
                "raroc": raroc_pct
            })
        return result

    return {
        "hurdle_rate": hurdle_rate * 100,
        "target_rate": target_rate * 100,
        "by_industry": format_segments(by_industry),
        "by_rating": format_segments(by_rating),
        "by_segment": format_segments(by_industry) + format_segments(by_rating)  # 하위호환
    }
