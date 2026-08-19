"""
CET1 12.3% 경로 API (P2)
==========================
CFO가 공언한 밸류업 1차 목표(CET1 12.3%)를 규제 일정 위에서 관리한다.

규제 근거 (docs/IMPROVEMENT_RESEARCH_2026-08-19.md P2):
- 바젤III output floor 경과규정: 내부등급법 RWA 하한이 표준방법 대비
  60% → 65%(2026) → 70%(2027) → 72.5%(2028)로 단계 상향.
- 생산적 금융 대전환: 주담대 위험가중치 하한 상향 발표(15→20%, 25% 검토
  - 시행 시점 미확인), 주식 RW 인하. 여기서는 **시나리오 입력**으로만
  다룬다 (기업여신 시스템에 가계여신 기능을 만드는 것이 아님).
- SCB 는 2년째 시행 유예 상태라 '시행 시' 가정 밴드로만 표시한다.

수치 기준: capital_position 은 데모 DB 실측(iM 실측 규모로 보정된 값),
정책 파라미터(성장률·배당성향·SA 배수)는 조정 가능한 가정치다.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db

router = APIRouter(prefix="/api/cet1-path", tags=["CET1 Path"])

# output floor 경과규정 (바젤III 최종안 국내 조기 시행 - 2022.11 자본하한 도입)
OUTPUT_FLOOR = {2025: 0.60, 2026: 0.65, 2027: 0.70, 2028: 0.725}

TARGETS = {
    "valueup_cet1": 12.3,        # 밸류업 1차 목표 (CFO 공언, 지주 기준)
    "disclosed_group_cet1": 12.27,  # 지주 CET1 공시 (2026.6월 말)
    "regulatory_min": 8.0,       # 4.5 + 자본보전 2.5 + CCyB 1.0 (D-SIB 아님)
    "scb_assumed": 1.0,          # SCB 시행 시 가정 부과율 (시행 미확정 - 가정)
    "net_income_eok": 3895,      # iM뱅크 2025 연간 순이익 (공시)
}


def _latest_position(db: Session):
    row = db.execute(text("""
        SELECT base_date, cet1_capital, credit_rwa, market_rwa,
               operational_rwa, total_rwa, cet1_ratio, bis_ratio
        FROM capital_position ORDER BY base_date DESC LIMIT 1
    """)).fetchone()
    return {
        "base_date":      str(row[0]),
        "cet1_capital":   float(row[1]),
        "credit_rwa":     float(row[2]),
        "market_rwa":     float(row[3]),
        "operational_rwa": float(row[4]),
        "total_rwa":      float(row[5]),
        "cet1_ratio":     round(float(row[6]) * 100, 2),
        "bis_ratio":      round(float(row[7]) * 100, 2),
    }


@router.get("/projection")
def get_cet1_projection(
    asset_growth: float = Query(4.0, description="연 자산(RWA) 성장률 %"),
    payout_ratio: float = Query(30.0, description="배당성향 % (유보율 = 100-배당성향)"),
    sa_multiplier: float = Query(1.45, description="표준방법 RWA / 내부등급법 RWA 배수 (가정)"),
    net_income_eok: float = Query(TARGETS["net_income_eok"], description="연 순이익 (억)"),
    db: Session = Depends(get_db),
):
    """output floor 단계 상향(65→70→72.5%)을 반영한 연도별 CET1 경로.

    floor 는 신용리스크 RWA 에만 적용: floored = max(IRB, floor% × SA).
    SA 배수(중소기업 위주 포트폴리오는 1.4~1.6)가 클수록 2027~28년에
    floor 가 물리며 RWA 가 점프한다.
    """
    pos = _latest_position(db)
    g = asset_growth / 100.0
    retain = net_income_eok * 1e8 * (1 - payout_ratio / 100.0)

    cet1 = pos["cet1_capital"]
    credit = pos["credit_rwa"]
    market = pos["market_rwa"]
    op = pos["operational_rwa"]

    path = []
    for year in (2026, 2027, 2028):
        floor_pct = OUTPUT_FLOOR[year]
        if year > 2026:
            credit *= (1 + g)
            market *= (1 + g)
            op *= (1 + g)
            cet1 += retain
        sa_rwa = credit * sa_multiplier
        floored_credit = max(credit, floor_pct * sa_rwa)
        addon = floored_credit - credit
        total = floored_credit + market + op
        ratio = cet1 / total * 100
        # 목표 미달 시 필요한 조치 환산
        capital_shortfall = max(TARGETS["valueup_cet1"] / 100 * total - cet1, 0)
        rwa_cut_needed = max(total - cet1 / (TARGETS["valueup_cet1"] / 100), 0)
        path.append({
            "year": year,
            "floor_pct": floor_pct * 100,
            "floor_binding": addon > 0,
            "floor_addon_rwa_eok": round(addon / 1e8, 0),
            "credit_rwa_eok": round(floored_credit / 1e8, 0),
            "total_rwa_eok": round(total / 1e8, 0),
            "cet1_capital_eok": round(cet1 / 1e8, 0),
            "cet1_ratio": round(ratio, 2),
            "meets_target": ratio >= TARGETS["valueup_cet1"],
            "capital_shortfall_eok": round(capital_shortfall / 1e8, 0),
            "rwa_cut_needed_eok": round(rwa_cut_needed / 1e8, 0),
        })

    return {
        "position": {**{k: (round(v / 1e8, 0) if k.endswith(('capital', 'rwa')) else v)
                        for k, v in pos.items()}},
        "targets": TARGETS,
        "assumptions": {
            "asset_growth": asset_growth, "payout_ratio": payout_ratio,
            "sa_multiplier": sa_multiplier, "net_income_eok": net_income_eok,
            "note": "성장률·배당성향·SA 배수는 가정치 - output floor 일정은 경과규정 확정치",
        },
        "path": path,
        "requirement_bands": {
            "regulatory_min": TARGETS["regulatory_min"],
            "with_scb_assumed": TARGETS["regulatory_min"] + TARGETS["scb_assumed"],
            "scb_note": "스트레스완충자본은 2년째 시행 유예 - 시행 시 가정 1.0%p",
        },
    }


@router.get("/rw-scenario")
def get_rw_scenario(
    mortgage_exposure_eok: float = Query(120000, description="주담대 익스포저 가정 (억)"),
    mortgage_rw_from: float = Query(20.0, description="주담대 RW 현행 하한 %"),
    mortgage_rw_to: float = Query(25.0, description="주담대 RW 검토 하한 %"),
    equity_rwa_relief_eok: float = Query(5000, description="주식 RW 인하 등 완화 효과 (억, 가정)"),
    corporate_avg_rw: float = Query(65.0, description="기업여신 평균 RW %"),
    db: Session = Depends(get_db),
):
    """생산적 금융 대전환 위험가중치 시나리오 - 가계→기업 자본 재배분 환산.

    주담대 RW 상향(발표 20%, 25% 추가 검토 - 시행 시점 미확인)은 가계 RWA 를
    늘려 가계 확대를 억제하고, 그 자본 여력을 기업(생산적 부문)으로 돌리는
    정책 패키지다. 주담대 익스포저는 은행 공시에 세분류가 없어 가정치를 쓴다.
    """
    pos = _latest_position(db)

    mortgage_rwa_delta = mortgage_exposure_eok * (mortgage_rw_to - mortgage_rw_from) / 100.0
    net_rwa_delta = mortgage_rwa_delta - equity_rwa_relief_eok

    target = TARGETS["valueup_cet1"] / 100.0
    # RWA 순증이 목표비율 유지에 요구하는 추가 자본
    capital_impact_eok = net_rwa_delta * target
    # 주식 RW 완화로 풀리는 RWA 를 기업여신으로 환산 (평균 RW 65% 가정)
    corporate_capacity_eok = equity_rwa_relief_eok / (corporate_avg_rw / 100.0)

    new_total_rwa = pos["total_rwa"] + net_rwa_delta * 1e8
    new_ratio = pos["cet1_capital"] / new_total_rwa * 100

    return {
        "current": {"cet1_ratio": pos["cet1_ratio"], "total_rwa_eok": round(pos["total_rwa"] / 1e8, 0)},
        "scenario": {
            "mortgage_exposure_eok": mortgage_exposure_eok,
            "mortgage_rw_change": f"{mortgage_rw_from}% → {mortgage_rw_to}%",
            "mortgage_rwa_delta_eok": round(mortgage_rwa_delta, 0),
            "equity_rwa_relief_eok": equity_rwa_relief_eok,
            "net_rwa_delta_eok": round(net_rwa_delta, 0),
            "cet1_ratio_after": round(new_ratio, 2),
            "capital_impact_eok": round(capital_impact_eok, 0),
            "corporate_capacity_eok": round(corporate_capacity_eok, 0),
        },
        "policy_note": (
            "주담대 RW 하한 상향은 2025.9 생산적 금융 대전환 회의에서 발표(15→20%), "
            "25% 추가 상향은 검토 단계 - 시행 시점 미확인. 주담대 익스포저는 가정치."
        ),
    }
