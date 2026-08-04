"""
포트폴리오 맵 API - 기업 다차원 산점도 + what-if 시뮬레이션
=============================================================
여신 보유 기업 전체를 지표 벡터로 일괄 반환해 프론트가 2축 산점도
(X·Y 선택 + 크기=잔액 + 색=범주)로 그린다. what-if 는 선택 기업의
PD·EWS·한도소진율을 모의값으로 바꿨을 때 EL·RAROC·건전성 분류·
필요충당금이 어떻게 움직이는지 기존 계산 모듈(calculations.py)의
동일 산식으로 근사한다 - 실데이터는 변경하지 않는다.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..services.calculations import classify_asset, PROVISION_RATES

router = APIRouter(prefix="/api/portfolio-map", tags=["PortfolioMap"])

# 고객 단위 최신 스냅샷 결합 - 각 지표 테이블에서 최신 1행씩
_BASE_SQL = """
WITH fac AS (
    SELECT customer_id,
           SUM(outstanding_amount)                    AS exposure,
           MAX(dpd)                                   AS max_dpd,
           MAX(CASE classification
                 WHEN 'LOSS' THEN 5 WHEN 'DOUBTFUL' THEN 4
                 WHEN 'SUBSTANDARD' THEN 3 WHEN 'PRECAUTIONARY' THEN 2
                 ELSE 1 END)                          AS worst_rank
    FROM facility WHERE status = 'ACTIVE'
    GROUP BY customer_id
),
rat AS (
    SELECT customer_id, pd_value, final_grade,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY rating_date DESC) rn
    FROM credit_rating_result
),
prof AS (
    SELECT customer_id, raroc, total_profit, economic_capital, loan_el,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY calculation_date DESC) rn
    FROM customer_profitability
),
ews AS (
    SELECT customer_id, composite_score, ews_grade, risk_level,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY score_date DESC) rn
    FROM ews_composite_score
),
txn AS (
    SELECT customer_id, limit_utilization,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY reference_month DESC) rn
    FROM ews_transaction_behavior
),
mkt AS (
    SELECT customer_id, distance_to_default,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY reference_month DESC) rn
    FROM ews_market_signal
),
news AS (
    SELECT customer_id, avg_sentiment,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY reference_month DESC) rn
    FROM ews_news_sentiment_monthly
),
fin AS (
    SELECT customer_id, debt_ratio, ier, altman_z,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY fiscal_year DESC) rn
    FROM financial_ratio
),
ecl AS (
    SELECT e.customer_id, SUM(e.ecl_final) AS ecl_total, AVG(e.lgd) AS lgd_avg
    FROM ecl_calculation e
    JOIN (SELECT facility_id, MAX(calc_date) latest
          FROM ecl_calculation GROUP BY facility_id) mx
      ON e.facility_id = mx.facility_id AND e.calc_date = mx.latest
    GROUP BY e.customer_id
)
SELECT c.customer_id, c.customer_name, c.industry_name, c.region, c.size_category,
       fac.exposure, fac.max_dpd, fac.worst_rank,
       rat.pd_value, rat.final_grade,
       prof.raroc, prof.total_profit, prof.economic_capital, prof.loan_el,
       ews.composite_score, ews.ews_grade,
       txn.limit_utilization,
       mkt.distance_to_default,
       news.avg_sentiment,
       fin.debt_ratio, fin.ier, fin.altman_z,
       ecl.ecl_total, ecl.lgd_avg
FROM fac
JOIN customer c ON c.customer_id = fac.customer_id
LEFT JOIN rat  ON rat.customer_id  = c.customer_id AND rat.rn  = 1
LEFT JOIN prof ON prof.customer_id = c.customer_id AND prof.rn = 1
LEFT JOIN ews  ON ews.customer_id  = c.customer_id AND ews.rn  = 1
LEFT JOIN txn  ON txn.customer_id  = c.customer_id AND txn.rn  = 1
LEFT JOIN mkt  ON mkt.customer_id  = c.customer_id AND mkt.rn  = 1
LEFT JOIN news ON news.customer_id = c.customer_id AND news.rn = 1
LEFT JOIN fin  ON fin.customer_id  = c.customer_id AND fin.rn  = 1
LEFT JOIN ecl  ON ecl.customer_id  = c.customer_id
"""

_CLASS_NAMES = {1: "NORMAL", 2: "PRECAUTIONARY", 3: "SUBSTANDARD", 4: "DOUBTFUL", 5: "LOSS"}


def _row_to_company(r) -> dict:
    exposure = r[5] or 0
    ecl_total = r[22] or 0
    return {
        "customer_id": r[0],
        "name": r[1],
        "industry": r[2],
        "region": r[3],
        "size_category": r[4],
        "exposure": round(exposure, 2),
        "dpd": r[6] or 0,
        "classification": _CLASS_NAMES.get(r[7], "NORMAL"),
        "pd": round((r[8] or 0) * 100, 4),                # %
        "grade": r[9],
        "raroc": round(r[10], 2) if r[10] is not None else None,   # %
        "ews_score": round(r[14], 1) if r[14] is not None else None,
        "ews_grade": r[15],
        "util": round((r[16] or 0) * 100, 1) if r[16] is not None else None,   # %
        "dd": round(r[17], 2) if r[17] is not None else None,      # 상장사만
        "sentiment": round(r[18], 3) if r[18] is not None else None,
        "debt_ratio": round(r[19], 1) if r[19] is not None else None,          # %
        "icr": round(r[20], 2) if r[20] is not None else None,     # 이자보상배율
        "altman_z": round(r[21], 2) if r[21] is not None else None,
        "provision_ratio": round(ecl_total / exposure * 100, 3) if exposure else None,  # %
    }


@router.get("/companies")
def get_map_companies(db: Session = Depends(get_db)):
    """여신 보유 기업 전체의 지표 벡터 (산점도 데이터)"""
    rows = db.execute(text(_BASE_SQL)).fetchall()
    return {
        "count": len(rows),
        "companies": [_row_to_company(r) for r in rows],
    }


@router.get("/history")
def get_map_history(db: Session = Depends(get_db)):
    """타임 슬라이더·궤적용 월별 이력 (최근 12개월).

    월별 데이터가 있는 지표만: 한도소진율·부도거리(DD)·뉴스감성 (각 12개월),
    PD 는 등급 이력의 as-of 값을 월별로 펼친다 (carry-forward).
    EWS 종합점수는 단일 시점만 존재해 시간축 미지원.
    단위는 /companies 와 동일 (%, 점수 등).
    """
    months = [r[0] for r in db.execute(text(
        "SELECT DISTINCT reference_month FROM ews_transaction_behavior ORDER BY 1"
    )).fetchall()][-12:]
    if not months:
        return {"months": [], "series": {}}

    fac_ids = {r[0] for r in db.execute(text(
        "SELECT DISTINCT customer_id FROM facility WHERE status = 'ACTIVE'"
    )).fetchall()}
    idx = {m: i for i, m in enumerate(months)}
    n = len(months)

    series: dict = {cid: {"pd": [None] * n, "util": [None] * n,
                          "dd": [None] * n, "sentiment": [None] * n}
                    for cid in fac_ids}

    def fill(sql: str, key: str, scale: float, digits: int):
        for cid, m, v in db.execute(text(sql)).fetchall():
            if cid in series and m in idx and v is not None:
                series[cid][key][idx[m]] = round(v * scale, digits)

    fill("SELECT customer_id, reference_month, limit_utilization FROM ews_transaction_behavior",
         "util", 100, 1)
    fill("SELECT customer_id, reference_month, distance_to_default FROM ews_market_signal",
         "dd", 1, 2)
    fill("SELECT customer_id, reference_month, avg_sentiment FROM ews_news_sentiment_monthly",
         "sentiment", 1, 3)

    # PD as-of: 등급 이력을 월말 기준 carry-forward 로 펼친다
    ratings = db.execute(text("""
        SELECT customer_id, rating_date, pd_value FROM credit_rating_result
        ORDER BY customer_id, rating_date
    """)).fetchall()
    by_cust: dict = {}
    for cid, rd, pd in ratings:
        if cid in series:
            by_cust.setdefault(cid, []).append((rd[:7], pd))
    for cid, hist in by_cust.items():
        j, cur = 0, None
        for i, m in enumerate(months):
            while j < len(hist) and hist[j][0] <= m:
                cur = hist[j][1]
                j += 1
            series[cid]["pd"][i] = round(cur * 100, 4) if cur is not None else None

    # 앞쪽 결측은 첫 관측값으로 backfill (그 달만 비어 점이 사라지는 것 방지)
    for s in series.values():
        for key in ("pd", "util", "sentiment"):
            arr = s[key]
            first = next((v for v in arr if v is not None), None)
            if first is None:
                continue
            for i in range(n):
                if arr[i] is None:
                    arr[i] = first
                else:
                    break
        # dd 는 비상장사 전체가 None - 그대로 둔다
        if all(v is None for v in s["dd"]):
            s["dd"] = None

    return {"months": months, "series": series}


@router.get("/capital-context")
def get_capital_context(db: Session = Depends(get_db)):
    """what-if 누적 파급의 BIS 근사에 쓰는 자본 현황"""
    cap = db.execute(text("""
        SELECT bis_ratio, total_capital, total_rwa
        FROM capital_position ORDER BY base_date DESC LIMIT 1
    """)).fetchone()
    if not cap:
        return {"bis_ratio": 0, "total_capital": 0, "total_rwa": 0}
    return {
        "bis_ratio": round((cap[0] or 0) * 100, 2),
        "total_capital": cap[1] or 0,
        "total_rwa": cap[2] or 0,
    }


@router.get("/what-if")
def what_if(
    customer_id: str = Query(...),
    pd_sim: float = Query(None, description="모의 PD (%)"),
    ews_sim: float = Query(None, description="모의 EWS 종합점수 (0~100)"),
    util_sim: float = Query(None, description="모의 한도소진율 (%)"),
    db: Session = Depends(get_db),
):
    """선택 기업의 지표를 모의값으로 바꿨을 때의 파급 (PoC 근사 산식).

    실데이터는 변경하지 않는다. 산식은 해당 업무 모듈과 동일 상수를 쓴다:
      · EL      = PD × LGD × EAD            (LGD 는 해당 기업 ECL 계산의 평균)
      · RAROC   = 기존 RAROC + (EL_base - EL_sim) / 경제적자본
      · 분류    = classify_asset(DPD, PD, EWS) - 보수주의 원칙 그대로
      · 충당금  = 잔액 × 분류별 최저적립률 (감독규정)
    """
    row = db.execute(text(_BASE_SQL + " WHERE c.customer_id = :cid"),
                     {"cid": customer_id}).fetchone()
    if not row:
        raise HTTPException(404, "여신 보유 기업이 아닙니다")

    base = _row_to_company(row)
    lgd = row[23] or 0.45
    econ_cap = row[12] or 0
    exposure = base["exposure"]

    pd_base = base["pd"] / 100
    ews_base = base["ews_score"] if base["ews_score"] is not None else 70.0
    util_base = (base["util"] or 100.0) / 100

    pd_new = (pd_sim / 100) if pd_sim is not None else pd_base
    ews_new = ews_sim if ews_sim is not None else ews_base
    util_new = (util_sim / 100) if util_sim is not None else util_base

    # EAD 근사: 한도소진율 변화에 비례해 노출이 움직인다 (0 나눗셈 방지)
    ead_base = exposure
    ead_new = exposure * (util_new / util_base) if util_base > 0 else exposure

    el_base = pd_base * lgd * ead_base
    el_new = pd_new * lgd * ead_new

    raroc_base = base["raroc"] or 0
    raroc_new = raroc_base + ((el_base - el_new) / econ_cap * 100 if econ_cap else 0)

    cls_base = classify_asset(base["dpd"], pd_base, ews_base)
    cls_new = classify_asset(base["dpd"], pd_new, ews_new)

    prov_base = exposure * PROVISION_RATES[cls_base["classification"]]
    prov_new = ead_new * PROVISION_RATES[cls_new["classification"]]

    def pack(el, raroc, cls, prov, ead):
        return {
            "el": round(el, 2),
            "raroc": round(raroc, 2),
            "classification": cls["classification"],
            "class_basis": cls["final_class_basis"],
            "required_provision": round(prov, 2),
            "ead": round(ead, 2),
        }

    return {
        "customer_id": customer_id,
        "name": base["name"],
        "inputs": {
            "pd": round(pd_new * 100, 4), "ews_score": round(ews_new, 1),
            "util": round(util_new * 100, 1), "lgd": round(lgd, 3),
        },
        "base": pack(el_base, raroc_base, cls_base, prov_base, ead_base),
        "sim": pack(el_new, raroc_new, cls_new, prov_new, ead_new),
        "note": "모의 조정입니다 - 실데이터는 변경되지 않습니다 (PoC 근사 산식)",
    }
