"""
손실흡수력 조종석 API (P1)
============================
iM금융 2026.2Q 컨퍼런스콜에서 CRO가 공언한 "NPL커버리지 연말 100% 회복"을
관리하는 화면의 데이터 계층.

설계 원칙 (docs/IMPROVEMENT_RESEARCH_2026-08-19.md P1):
- 은행 레벨 경로 시뮬레이터의 **초기값은 공시 수치**(그룹 82.2%, 부도여신
  6,587억/년 등)를 쓰고, 출처·기준(지주/은행)을 응답에 명시한다.
- CLMS 데모 포트폴리오의 실측(분류별 충당금·적립부족)은 별도 블록으로
  구분해 공시 벤치마크와 섞지 않는다.
- 시뮬레이션은 상태를 바꾸지 않으므로 GET 이다. 저장·실행성 행위가 생기면
  그때 권한·감사기록과 함께 추가한다.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..core.config import AS_OF_DATE

router = APIRouter(prefix="/api/loss-absorption", tags=["Loss Absorption"])

# ── 공시 벤치마크 (2026.2Q 실적 발표·컨퍼런스콜 기준) ───────────────────
# 지주/은행 기준이 다르므로 반드시 구분 표기한다. 은행 단독 CET1 처럼
# 보도가 상충하는 값은 싣지 않는다 (연구 문서 '확인 불가' 원칙).
BENCHMARK = {
    "group_coverage_ex_reserve":    82.2,   # 지주, 대손준비금 제외 (2026.2Q)
    "group_coverage_ex_reserve_1q": 93.6,   # 지주, 직전 분기
    "group_coverage_incl_reserve":  137.0,  # 지주, 대손준비금 포함 (CRO 컨콜 언급)
    "bank_coverage_fy2025":         91.1,   # 은행, 2025 회계연도 말
    "bank_coverage_fy2024":         100.9,  # 은행, 2024 회계연도 말
    "bank_npl_ratio":               0.94,   # 은행, 2026 상반기 말 (%)
    "bank_loans_eok":               602462, # 은행 원화대출금 (2026.6월 말, 억)
    "defaulted_2025_eok":           6587,   # 은행 부도여신 2025 (억)
    "defaulted_2024_eok":           5518,   # 은행 부도여신 2024 (억)
    "credit_cost_rate":             0.41,   # 은행 대손비용률 (2026 상반기, %)
    "target_coverage":              100.0,  # CRO 공언 목표 (제외 기준)
    "target_month":                 "2026-12",
    "source": "iM금융 2026.2Q 실적 발표·컨퍼런스콜 보도 (지주/은행 기준 구분 표기)",
}

# 시뮬레이터 기본 가정 - 화면에 '가정' 배지와 함께 노출하고 조정 가능하게 한다
DEFAULTS = {
    "npl0_eok":          8000,   # 그룹 고정이하여신 가정치 (절대액 미공시 - 조정 가능)
    "inflow_eok":        549,    # 월 신규부실 유입 = 2025 부도여신 6,587억 / 12
    "cure_rate":         0.01,   # 월 자연 정상화·회수율 (NPL 잔액 대비)
    "sale_coverage":     0.60,   # 매각 NPL 에 딸려 나가는 충당금 비율
}

NPL_CLASSES = ("SUBSTANDARD", "DOUBTFUL", "ESTIMATED_LOSS")


def _month_seq(n: int) -> list[str]:
    """AS_OF 다음 달부터 n개월의 YYYY-MM 시퀀스"""
    y, m = AS_OF_DATE.year, AS_OF_DATE.month
    out = []
    for _ in range(n):
        m += 1
        if m > 12:
            m = 1
            y += 1
        out.append(f"{y:04d}-{m:02d}")
    return out


def _months_to_target() -> int:
    ty, tm = (int(x) for x in BENCHMARK["target_month"].split("-"))
    return max((ty - AS_OF_DATE.year) * 12 + (tm - AS_OF_DATE.month), 1)


def _run_path(
    npl0: float, cov0: float, months: int,
    monthly_provision: float, quarterly_writeoff: float,
    npl_sale: float, sale_month: int,
    inflow: float, cure_rate: float, sale_coverage: float,
) -> list[dict]:
    """월별 커버리지 경로. 단위는 억원.

    상각은 충당금 100% 적립분만 소각하므로 NPL·충당금이 같이 줄어
    커버리지가 오르고, 매각은 매각 NPL 의 적립분(sale_coverage)만
    충당금에서 빠져 저커버 자산 제거 효과를 낸다.
    """
    npl = float(npl0)
    prov = cov0 / 100.0 * npl
    seq = _month_seq(months)
    path = []
    for i, ym in enumerate(seq, start=1):
        npl += inflow
        npl -= npl * cure_rate
        prov += monthly_provision
        if i % 3 == 0 and quarterly_writeoff > 0:
            wo = min(quarterly_writeoff, npl * 0.5, prov)
            npl -= wo
            prov -= wo
        if i == sale_month and npl_sale > 0:
            s = min(npl_sale, npl * 0.8)
            npl -= s
            prov -= s * sale_coverage
        npl = max(npl, 1.0)
        prov = max(prov, 0.0)
        path.append({
            "month": ym,
            "npl_eok": round(npl, 1),
            "provision_eok": round(prov, 1),
            "coverage": round(prov / npl * 100, 1),
        })
    return path


def _required_monthly(
    npl0: float, cov0: float, months: int, target: float,
    quarterly_writeoff: float, npl_sale: float, sale_month: int,
    inflow: float, cure_rate: float, sale_coverage: float,
) -> float:
    """연말 목표 커버리지 달성에 필요한 월 적립액 역산 (이분법)"""
    lo, hi = 0.0, 5000.0
    for _ in range(40):
        mid = (lo + hi) / 2
        end = _run_path(npl0, cov0, months, mid, quarterly_writeoff,
                        npl_sale, sale_month, inflow, cure_rate, sale_coverage)[-1]
        if end["coverage"] >= target:
            hi = mid
        else:
            lo = mid
    return round(hi, 0)


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    """공시 벤치마크 + CLMS 데모 포트폴리오 실측 (분류별 충당금·적립부족)"""
    base_date = db.execute(text(
        "SELECT MAX(base_date) FROM asset_classification")).scalar()

    rows = db.execute(text("""
        SELECT classification,
               COUNT(*)                    AS cnt,
               SUM(exposure_at_class)      AS exposure,
               SUM(required_provision)     AS required,
               SUM(existing_provision)     AS existing
        FROM asset_classification
        WHERE base_date = :bd
        GROUP BY classification
    """), {"bd": base_date}).fetchall()

    by_class = {}
    total_exp = total_req = total_ex = 0.0
    npl_exp = npl_req = npl_ex = 0.0
    for r in rows:
        cls = r[0]
        exp = float(r[2] or 0); req = float(r[3] or 0); ex = float(r[4] or 0)
        by_class[cls] = {
            "count": r[1],
            "exposure_eok": round(exp / 1e8, 1),
            "required_eok": round(req / 1e8, 1),
            "existing_eok": round(ex / 1e8, 1),
            "gap_eok": round((req - ex) / 1e8, 1),
        }
        total_exp += exp; total_req += req; total_ex += ex
        if cls in NPL_CLASSES:
            npl_exp += exp; npl_req += req; npl_ex += ex

    # IFRS9 ECL 최신 합계 - 감독 요구액과의 차액이 대손준비금 필요액
    ecl_row = db.execute(text("""
        SELECT SUM(ecl_final) FROM ecl_calculation
        WHERE calc_date = (SELECT MAX(calc_date) FROM ecl_calculation)
    """)).fetchone()
    ecl_total = float(ecl_row[0] or 0)

    # 월별 신규 연체 발생 추이 (부실 유입의 선행 지표)
    formation = db.execute(text("""
        SELECT substr(overdue_date, 1, 7) AS ym,
               COUNT(*) AS cnt,
               SUM(overdue_amount) AS amt
        FROM delinquency_record
        GROUP BY ym ORDER BY ym DESC LIMIT 12
    """)).fetchall()

    months = _months_to_target()
    return {
        "benchmark": BENCHMARK,
        "defaults": {**DEFAULTS, "months_to_target": months,
                     # 현행 페이스: 은행 대손비용률 0.41% 연율을 월 적립액으로 환산
                     "current_pace_eok": round(
                         BENCHMARK["bank_loans_eok"] * BENCHMARK["credit_cost_rate"] / 100 / 12, 0)},
        "portfolio": {
            "base_date": str(base_date),
            "by_class": by_class,
            "total_exposure_eok": round(total_exp / 1e8, 1),
            "npl_exposure_eok": round(npl_exp / 1e8, 1),
            "npl_ratio": round(npl_exp / total_exp * 100, 2) if total_exp else 0,
            "supervisory_required_eok": round(total_req / 1e8, 1),
            "existing_provision_eok": round(total_ex / 1e8, 1),
            "provision_gap_eok": round((total_req - total_ex) / 1e8, 1),
            "ecl_total_eok": round(ecl_total / 1e8, 1),
            # 감독규정 §29 최저적립 vs IFRS9 ECL 이중구조: 미달분이 대손준비금
            "reserve_needed_eok": round(max(total_req - ecl_total, 0) / 1e8, 1),
            "portfolio_coverage": round(total_ex / npl_exp * 100, 1) if npl_exp else None,
        },
        "formation_trend": [
            {"month": r[0], "count": r[1], "amount_eok": round(float(r[2] or 0) / 1e8, 1)}
            for r in reversed(formation)
        ],
    }


@router.get("/simulate")
def simulate_coverage_path(
    monthly_provision: float = Query(None, description="월 충당금 적립액 (억)"),
    quarterly_writeoff: float = Query(0, description="분기 상각 규모 (억)"),
    npl_sale: float = Query(0, description="NPL 매각 규모 (억, 1회)"),
    sale_month: int = Query(3, description="매각 시점 (N개월차)"),
    npl0: float = Query(DEFAULTS["npl0_eok"], description="그룹 고정이하여신 가정 (억)"),
    inflow: float = Query(DEFAULTS["inflow_eok"], description="월 신규부실 유입 (억)"),
    cov0: float = Query(None, description="시작 커버리지 (%, 기본 공시 82.2)"),
):
    """커버리지 경로 시뮬레이션 + 목표 달성 필요 적립액 역산.

    상태를 바꾸지 않는 순수 계산이므로 GET. 초기값은 공시(그룹 82.2%),
    유입은 2025 부도여신 공시(6,587억/12), NPL 절대액은 가정치로
    화면에서 조정 가능하다.
    """
    months = _months_to_target()
    cov0 = cov0 if cov0 is not None else BENCHMARK["group_coverage_ex_reserve"]
    current_pace = BENCHMARK["bank_loans_eok"] * BENCHMARK["credit_cost_rate"] / 100 / 12
    mp = monthly_provision if monthly_provision is not None else current_pace

    common = dict(npl0=npl0, cov0=cov0, months=months,
                  inflow=inflow, cure_rate=DEFAULTS["cure_rate"],
                  sale_coverage=DEFAULTS["sale_coverage"])

    scenario = _run_path(monthly_provision=mp, quarterly_writeoff=quarterly_writeoff,
                         npl_sale=npl_sale, sale_month=sale_month, **common)
    baseline = _run_path(monthly_provision=current_pace, quarterly_writeoff=0,
                         npl_sale=0, sale_month=0, **common)

    required = _required_monthly(
        target=BENCHMARK["target_coverage"],
        quarterly_writeoff=quarterly_writeoff,
        npl_sale=npl_sale, sale_month=sale_month, **common)
    required_provision_only = _required_monthly(
        target=BENCHMARK["target_coverage"],
        quarterly_writeoff=0, npl_sale=0, sale_month=0, **common)

    return {
        "months": months,
        "assumptions": {
            "npl0_eok": npl0, "cov0": cov0, "inflow_eok": inflow,
            "cure_rate": DEFAULTS["cure_rate"],
            "sale_coverage": DEFAULTS["sale_coverage"],
            "current_pace_eok": round(current_pace, 0),
            "note": "초기 커버리지·유입은 공시 기준, NPL 절대액은 가정치 (조정 가능)",
        },
        "scenario_path": scenario,
        "baseline_path": baseline,
        "end_coverage": scenario[-1]["coverage"],
        "hits_target": scenario[-1]["coverage"] >= BENCHMARK["target_coverage"],
        "target": BENCHMARK["target_coverage"],
        "required_monthly_provision_eok": required,
        "required_provision_only_eok": required_provision_only,
        "required_gap_vs_pace_eok": round(required - current_pace, 0),
    }
