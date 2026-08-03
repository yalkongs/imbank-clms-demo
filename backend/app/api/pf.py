"""
부동산PF 사업장 관리 API
========================
2027 시행 예정 PF 제도 개편 대비: 사업장 자기자본비율 수준에 위험가중치·충당금이
연동되는 구조로 바뀐다(자기자본 20% 수준 유도). 사업장 단위의 공정률·분양률·
자기자본비율을 상시 감시하고, 제도 시나리오별 자본·충당금 영향을 시뮬레이션한다.

공정률-분양률 괴리는 PF 부실의 대표 선행신호다 — 골조는 올라가는데 분양이 안 되면
준공 시점에 상환재원이 없다.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..core.config import AS_OF_MONTH

router = APIRouter(prefix="/api/pf", tags=["PF Monitoring"])

REGION_LABELS = {"CAPITAL": "수도권", "DAEGU_GB": "대구경북", "BUSAN_GN": "부산경남"}
PROPERTY_LABELS = {"APT": "아파트", "OFFICETEL": "오피스텔", "LOGISTICS": "물류센터",
                   "COMMERCIAL": "상업시설", "KNOWLEDGE": "지식산업센터"}

# 2027 제도 시나리오 — 사업장 자기자본비율 구간별 위험가중치·충당금률.
# 확정 규정이 아니라 개편 방향(자기자본 20% 유도, 저자본 사업장에 페널티)을
# 반영한 PoC 가정치다. 화면에도 '시나리오 가정' 을 명시한다.
REGULATION_BANDS = [
    {"band": "20% 이상",   "min": 20.0, "max": 999.0, "risk_weight": 0.80, "provision_rate": 0.009},
    {"band": "15~20%",     "min": 15.0, "max": 20.0,  "risk_weight": 1.00, "provision_rate": 0.020},
    {"band": "10~15%",     "min": 10.0, "max": 15.0,  "risk_weight": 1.20, "provision_rate": 0.035},
    {"band": "5~10%",      "min": 5.0,  "max": 10.0,  "risk_weight": 1.50, "provision_rate": 0.060},
    {"band": "5% 미만",    "min": 0.0,  "max": 5.0,   "risk_weight": 2.00, "provision_rate": 0.100},
]
# 현행(개편 전) 기준 가정: 일률 위험가중치 100%, 충당금 정상 기준 0.9%
CURRENT_RISK_WEIGHT = 1.00
CURRENT_PROVISION_RATE = 0.009

GAP_ALERT_THRESHOLD = 30.0   # 공정률-분양률 괴리 경보 기준 (%p)


def _band_for(equity_ratio: float) -> dict:
    for b in REGULATION_BANDS:
        if b["min"] <= equity_ratio < b["max"]:
            return b
    return REGULATION_BANDS[-1]


@router.get("/dashboard")
def get_pf_dashboard(db: Session = Depends(get_db)):
    """PF 포트폴리오 요약 — 익스포저, 유형·지역 분포, 위험 사업장"""
    rows = db.execute(text("""
        SELECT project_type, region, status, exposure, equity_ratio,
               progress_rate, presale_rate
        FROM pf_project WHERE status != 'COMPLETED'
    """)).fetchall()

    total = sum(r[3] for r in rows) or 1
    by_type: dict = {}
    by_region: dict = {}
    watchlist_exp = 0.0
    low_equity_exp = 0.0
    for ptype, region, status, exp, eq, prog, presale in rows:
        by_type[ptype] = by_type.get(ptype, 0) + exp
        by_region[region] = by_region.get(region, 0) + exp
        if status == "WATCHLIST":
            watchlist_exp += exp
        if eq < 10:
            low_equity_exp += exp

    return {
        "as_of_month": AS_OF_MONTH,
        "project_count": len(rows),
        "total_exposure": round(total, 2),
        "watchlist_count": sum(1 for r in rows if r[2] == "WATCHLIST"),
        "watchlist_exposure": round(watchlist_exp, 2),
        "low_equity_share": round(low_equity_exp / total * 100, 1),
        "by_type": [
            {"type": k, "label": "브릿지론" if k == "BRIDGE" else "본PF",
             "exposure": round(v, 2), "share": round(v / total * 100, 1)}
            for k, v in sorted(by_type.items())
        ],
        "by_region": [
            {"region": k, "label": REGION_LABELS.get(k, k),
             "exposure": round(v, 2), "share": round(v / total * 100, 1)}
            for k, v in sorted(by_region.items(), key=lambda x: -x[1])
        ],
    }


@router.get("/projects")
def list_pf_projects(
    region: str = Query(None),
    status: str = Query(None),
    db: Session = Depends(get_db),
):
    """사업장 목록 (공정-분양 괴리 내림차순 — 위험한 것부터)"""
    cond, params = "status != 'COMPLETED'", {}
    if region:
        cond += " AND region = :region"
        params["region"] = region
    if status:
        cond += " AND status = :status"
        params["status"] = status

    rows = db.execute(text(f"""
        SELECT project_id, project_name, project_type, property_type, region,
               developer_name, constructor_name, exposure, equity_ratio,
               progress_rate, presale_rate, ltv, maturity_date, status
        FROM pf_project WHERE {cond}
        ORDER BY (COALESCE(progress_rate,0) - COALESCE(presale_rate,0)) DESC
    """), params).fetchall()

    out = []
    for r in rows:
        gap = round((r[9] or 0) - (r[10] or 0), 1)
        band = _band_for(r[8])
        out.append({
            "project_id": r[0], "project_name": r[1],
            "project_type": r[2], "type_label": "브릿지론" if r[2] == "BRIDGE" else "본PF",
            "property_label": PROPERTY_LABELS.get(r[3], r[3]),
            "region": r[4], "region_label": REGION_LABELS.get(r[4], r[4]),
            "developer": r[5], "constructor": r[6],
            "exposure": round(r[7], 2), "equity_ratio": r[8],
            "equity_band": band["band"],
            "progress_rate": r[9], "presale_rate": r[10],
            "gap": gap, "gap_alert": r[2] == "MAIN" and gap >= GAP_ALERT_THRESHOLD,
            "ltv": r[11], "maturity_date": r[12], "status": r[13],
        })
    return out


@router.get("/projects/{project_id}")
def get_pf_project(project_id: str, db: Session = Depends(get_db)):
    """사업장 상세 + 12개월 공정·분양 추이"""
    row = db.execute(text("""
        SELECT project_id, project_name, project_type, property_type, region,
               developer_name, constructor_name, exposure, equity_ratio,
               progress_rate, presale_rate, ltv, maturity_date, status
        FROM pf_project WHERE project_id = :pid
    """), {"pid": project_id}).fetchone()
    if not row:
        raise HTTPException(404, "사업장을 찾을 수 없습니다")

    trend = db.execute(text("""
        SELECT reference_month, progress_rate, presale_rate
        FROM pf_progress WHERE project_id = :pid ORDER BY reference_month
    """), {"pid": project_id}).fetchall()

    band = _band_for(row[8])
    return {
        "project_id": row[0], "project_name": row[1],
        "type_label": "브릿지론" if row[2] == "BRIDGE" else "본PF",
        "property_label": PROPERTY_LABELS.get(row[3], row[3]),
        "region_label": REGION_LABELS.get(row[4], row[4]),
        "developer": row[5], "constructor": row[6],
        "exposure": round(row[7], 2), "equity_ratio": row[8],
        "equity_band": band["band"],
        "scenario_risk_weight": band["risk_weight"],
        "scenario_provision_rate": band["provision_rate"],
        "progress_rate": row[9], "presale_rate": row[10],
        "ltv": row[11], "maturity_date": row[12], "status": row[13],
        "trend": [
            {"month": t[0], "progress": t[1], "presale": t[2]} for t in trend
        ],
    }


@router.get("/regulation-simulation")
def simulate_regulation(db: Session = Depends(get_db)):
    """2027 제도 시나리오 — 자기자본비율 구간별 RWA·충당금 영향.

    현행(일률 RW 100%) 대비 개편안(구간별 RW·충당금) 적용 시 증감을 사업장
    포트폴리오 전체에 대해 계산한다. 저자본 사업장이 많을수록 부담이 커진다.
    """
    rows = db.execute(text("""
        SELECT exposure, equity_ratio FROM pf_project WHERE status != 'COMPLETED'
    """)).fetchall()

    bands_out = []
    total_exp = current_rwa = scenario_rwa = 0.0
    current_prov = scenario_prov = 0.0
    for b in REGULATION_BANDS:
        exp = sum(r[0] for r in rows if b["min"] <= r[1] < b["max"])
        cnt = sum(1 for r in rows if b["min"] <= r[1] < b["max"])
        s_rwa = exp * b["risk_weight"]
        s_prov = exp * b["provision_rate"]
        c_rwa = exp * CURRENT_RISK_WEIGHT
        c_prov = exp * CURRENT_PROVISION_RATE
        total_exp += exp
        scenario_rwa += s_rwa
        scenario_prov += s_prov
        current_rwa += c_rwa
        current_prov += c_prov
        bands_out.append({
            "band": b["band"], "count": cnt, "exposure": round(exp, 2),
            "risk_weight": b["risk_weight"], "provision_rate": b["provision_rate"],
            "scenario_rwa": round(s_rwa, 2), "scenario_provision": round(s_prov, 2),
        })

    return {
        "note": "확정 규정이 아닌 제도 개편 방향 기반 시나리오 가정",
        "total_exposure": round(total_exp, 2),
        "current":  {"rwa": round(current_rwa, 2), "provision": round(current_prov, 2),
                     "risk_weight": CURRENT_RISK_WEIGHT,
                     "provision_rate": CURRENT_PROVISION_RATE},
        "scenario": {"rwa": round(scenario_rwa, 2), "provision": round(scenario_prov, 2)},
        "delta": {
            "rwa": round(scenario_rwa - current_rwa, 2),
            "rwa_pct": round((scenario_rwa / current_rwa - 1) * 100, 1) if current_rwa else 0,
            "provision": round(scenario_prov - current_prov, 2),
        },
        "bands": bands_out,
    }


@router.get("/alerts")
def get_pf_alerts(db: Session = Depends(get_db)):
    """공정률-분양률 괴리 경보 (본PF, 괴리 30%p 이상)"""
    rows = db.execute(text("""
        SELECT project_id, project_name, region, exposure,
               progress_rate, presale_rate, equity_ratio
        FROM pf_project
        WHERE status != 'COMPLETED' AND project_type = 'MAIN'
          AND (COALESCE(progress_rate,0) - COALESCE(presale_rate,0)) >= :th
        ORDER BY (COALESCE(progress_rate,0) - COALESCE(presale_rate,0)) DESC
    """), {"th": GAP_ALERT_THRESHOLD}).fetchall()

    return [
        {
            "project_id": r[0], "project_name": r[1],
            "region_label": REGION_LABELS.get(r[2], r[2]),
            "exposure": round(r[3], 2),
            "progress_rate": r[4], "presale_rate": r[5],
            "gap": round((r[4] or 0) - (r[5] or 0), 1),
            "equity_ratio": r[6],
            "message": "공정 대비 분양 부진 — 준공 시 상환재원 점검 필요",
        }
        for r in rows
    ]
