"""
그룹여신 통합심사 API
=====================
borrower_group 테이블 활성화 - 계열사 합산 익스포저, 보증 관계, 그룹 한도 관리
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from ..core.database import get_db
from ..services.calculations import calculate_group_pd

router = APIRouter(prefix="/api/group-credit", tags=["Group Credit"])


@router.get("/group/{group_id}")
def get_group_overview(
    group_id: str,
    db: Session = Depends(get_db)
):
    """
    그룹 전체 현황
    - 계열사 목록 및 개별 여신 현황
    - 그룹 합산 익스포저 및 한도 사용률
    - 그룹 내 최열위 등급
    """
    group = db.execute(text("""
        SELECT group_id, group_name, group_type, parent_company_id,
               total_exposure, group_limit, group_pd, group_grade, group_limit_ratio
        FROM borrower_group
        WHERE group_id = :gid
    """), {"gid": group_id}).fetchone()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # 계열사 목록 및 여신 현황
    members = db.execute(text("""
        SELECT
            bgm.customer_id, bgm.relationship_type, bgm.ownership_pct,
            c.customer_name, c.industry_name, c.size_category,
            cr.final_grade, cr.pd_value,
            COALESCE(SUM(f.outstanding_amount), 0) AS outstanding,
            COALESCE(SUM(f.current_limit), 0)      AS total_limit,
            COUNT(f.facility_id)                   AS facility_count
        FROM borrower_group_member bgm
        JOIN customer c ON bgm.customer_id = c.customer_id
        LEFT JOIN (
            SELECT customer_id, final_grade, pd_value,
                   ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY rating_date DESC) AS rn
            FROM credit_rating_result
        ) cr ON c.customer_id = cr.customer_id AND cr.rn = 1
        LEFT JOIN facility f ON c.customer_id = f.customer_id AND f.status = 'ACTIVE'
        WHERE bgm.group_id = :gid
        GROUP BY bgm.customer_id, bgm.relationship_type, bgm.ownership_pct,
                 c.customer_name, c.industry_name, c.size_category,
                 cr.final_grade, cr.pd_value
        ORDER BY outstanding DESC
    """), {"gid": group_id}).fetchall()

    member_list = []
    pds = []
    exposures = []

    for m in members:
        outstanding = m[8]
        pd_val = m[7] or 0.05
        member_list.append({
            "customer_id":       m[0],
            "relationship_type": m[1],
            "ownership_pct":     m[2],
            "customer_name":     m[3],
            "industry_name":     m[4],
            "size_category":     m[5],
            "grade":             m[6],
            "pd":                m[7],
            "outstanding":       outstanding,
            "total_limit":       m[9],
            "facility_count":    m[10],
        })
        pds.append(pd_val)
        exposures.append(outstanding)

    # 그룹 합산 통계
    total_outstanding = sum(exposures)
    group_limit_amt = group[5] or 0
    utilization = (total_outstanding / group_limit_amt * 100) if group_limit_amt > 0 else None

    # 그룹 PD (가중평균 + 최열위)
    group_pd = calculate_group_pd(pds, exposures) if pds else None
    worst_grade = min(  # 신용등급 내림차순 정렬에서 최하위
        [m[6] for m in members if m[6]],
        key=_grade_order,
        default=None
    )

    # 보증 관계 수
    guarantee_count = db.execute(text("""
        SELECT COUNT(*) FROM group_guarantee
        WHERE group_id = :gid AND status = 'ACTIVE'
    """), {"gid": group_id}).scalar() or 0

    return {
        "group": {
            "group_id":    group[0],
            "group_name":  group[1],
            "group_type":  group[2],
            "parent_id":   group[3],
            "group_limit": group[5],
            "group_pd":    group_pd,
            "worst_grade": worst_grade,
        },
        "exposure_summary": {
            "total_outstanding": total_outstanding,
            "group_limit":       group_limit_amt,
            "utilization_pct":   round(utilization, 2) if utilization else None,
            "status": _exposure_status(utilization),
            "member_count":      len(member_list),
            "guarantee_count":   guarantee_count,
        },
        "members": member_list,
    }


@router.get("/customer/{customer_id}")
def get_customer_group(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """고객이 속한 그룹 조회"""
    memberships = db.execute(text("""
        SELECT bgm.group_id, bgm.relationship_type, bgm.ownership_pct,
               bg.group_name, bg.group_type, bg.group_limit, bg.total_exposure
        FROM borrower_group_member bgm
        JOIN borrower_group bg ON bgm.group_id = bg.group_id
        WHERE bgm.customer_id = :cid
    """), {"cid": customer_id}).fetchall()

    if not memberships:
        return {"customer_id": customer_id, "groups": [],
                "message": "소속 그룹 없음"}

    groups = []
    for m in memberships:
        groups.append({
            "group_id":         m[0],
            "relationship_type": m[1],
            "ownership_pct":    m[2],
            "group_name":       m[3],
            "group_type":       m[4],
            "group_limit":      m[5],
            "group_total_exposure": m[6],
        })

    return {"customer_id": customer_id, "groups": groups}


@router.get("/limit-check/{group_id}")
def check_group_limit(
    group_id: str,
    new_amount: float = Query(0, description="신규 신청 금액"),
    db: Session = Depends(get_db)
):
    """
    그룹 한도 체크
    - 현재 그룹 익스포저 + 신규 신청액 vs 그룹 한도
    - 규제 한도 (자기자본의 25%) 체크
    """
    group = db.execute(text("""
        SELECT group_id, group_name, total_exposure, group_limit
        FROM borrower_group WHERE group_id = :gid
    """), {"gid": group_id}).fetchone()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # 현재 실제 여신 합산 (DB 실시간)
    actual_exposure = db.execute(text("""
        SELECT COALESCE(SUM(f.outstanding_amount), 0)
        FROM facility f
        JOIN borrower_group_member bgm ON f.customer_id = bgm.customer_id
        WHERE bgm.group_id = :gid AND f.status = 'ACTIVE'
    """), {"gid": group_id}).scalar() or 0

    group_limit = group[3] or 0
    after_exposure = actual_exposure + new_amount
    utilization_after = (after_exposure / group_limit * 100) if group_limit > 0 else None

    # 자기자본 기준 규제 한도 (은행 BIS 자본 기준)
    bank_capital = db.execute(text("""
        SELECT total_capital FROM capital_position
        ORDER BY base_date DESC LIMIT 1
    """)).scalar() or 0
    regulatory_limit = bank_capital * 0.25  # 자기자본의 25%

    result = {
        "group_id": group_id,
        "group_name": group[1],
        "current_exposure": actual_exposure,
        "new_amount": new_amount,
        "exposure_after": after_exposure,
        "group_limit": group_limit,
        "utilization_pct_before": round(actual_exposure / group_limit * 100, 2) if group_limit > 0 else None,
        "utilization_pct_after": round(utilization_after, 2) if utilization_after else None,
        "group_limit_status": _exposure_status(utilization_after),
        "regulatory": {
            "bank_capital": bank_capital,
            "regulatory_limit_25pct": regulatory_limit,
            "exposure_after": after_exposure,
            "regulatory_ok": after_exposure <= regulatory_limit if regulatory_limit > 0 else True,
            "regulatory_utilization": round(after_exposure / regulatory_limit * 100, 2) if regulatory_limit > 0 else None,
        },
        "approval_required": after_exposure > group_limit if group_limit > 0 else False,
    }
    return result


@router.get("/concentration")
def get_group_concentration(
    region: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """그룹별 익스포저 집중도 - TOP 10"""
    region_cond = " AND c.region = :region" if region else ""

    rows = db.execute(text(f"""
        SELECT bg.group_id, bg.group_name, bg.group_limit,
               COALESCE(SUM(f.outstanding_amount), 0) AS group_exposure,
               COUNT(DISTINCT f.customer_id) AS member_count
        FROM borrower_group bg
        JOIN borrower_group_member bgm ON bg.group_id = bgm.group_id
        JOIN customer c ON bgm.customer_id = c.customer_id
        LEFT JOIN facility f ON c.customer_id = f.customer_id AND f.status = 'ACTIVE'
        WHERE 1=1 {region_cond}
        GROUP BY bg.group_id, bg.group_name, bg.group_limit
        ORDER BY group_exposure DESC
        LIMIT 10
    """), {"region": region} if region else {}).fetchall()

    # 전체 포트폴리오 익스포저
    total_portfolio = db.execute(text("""
        SELECT COALESCE(SUM(outstanding_amount), 0)
        FROM facility WHERE status = 'ACTIVE'
    """)).scalar() or 0

    items = []
    for r in rows:
        exposure = r[3]
        concentration = (exposure / total_portfolio * 100) if total_portfolio > 0 else 0
        util = (exposure / r[2] * 100) if r[2] else None
        items.append({
            "group_id": r[0],
            "group_name": r[1],
            "group_limit": r[2],
            "group_exposure": exposure,
            "member_count": r[4],
            "concentration_pct": round(concentration, 2),
            "limit_utilization": round(util, 1) if util else None,
        })

    return {
        "top_groups": items,
        "total_portfolio_exposure": total_portfolio,
    }


@router.get("/guarantee-network/{group_id}")
def get_guarantee_network(
    group_id: str,
    db: Session = Depends(get_db)
):
    """계열사 간 보증 관계망 (그래프 시각화용)"""
    guarantees = db.execute(text("""
        SELECT gg.guarantee_id, gg.guarantor_id, gg.beneficiary_id,
               gg.guarantee_type, gg.guarantee_amount, gg.status,
               c1.customer_name AS guarantor_name,
               c2.customer_name AS beneficiary_name
        FROM group_guarantee gg
        JOIN customer c1 ON gg.guarantor_id = c1.customer_id
        JOIN customer c2 ON gg.beneficiary_id = c2.customer_id
        WHERE gg.group_id = :gid AND gg.status = 'ACTIVE'
    """), {"gid": group_id}).fetchall()

    # 노드 (고객)
    node_ids = set()
    edges = []
    for g in guarantees:
        node_ids.add(g[1])
        node_ids.add(g[2])
        edges.append({
            "guarantee_id":    g[0],
            "from":            g[1],
            "to":              g[2],
            "guarantee_type":  g[3],
            "guarantee_amount": g[4],
            "from_name":       g[6],
            "to_name":         g[7],
        })

    # 노드별 여신 현황
    nodes = []
    for cid in node_ids:
        row = db.execute(text("""
            SELECT c.customer_name, cr.final_grade,
                   COALESCE(SUM(f.outstanding_amount), 0) AS outstanding
            FROM customer c
            LEFT JOIN credit_rating_result cr ON c.customer_id = cr.customer_id
                AND cr.rating_date = (SELECT MAX(rating_date)
                                      FROM credit_rating_result WHERE customer_id = c.customer_id)
            LEFT JOIN facility f ON c.customer_id = f.customer_id AND f.status = 'ACTIVE'
            WHERE c.customer_id = :cid
            GROUP BY c.customer_name, cr.final_grade
            LIMIT 1
        """), {"cid": cid}).fetchone()
        if row:
            nodes.append({
                "id": cid, "name": row[0], "grade": row[1], "outstanding": row[2]
            })

    # 상호보증 탐지
    mutual_guarantees = []
    edge_pairs = {(e['from'], e['to']) for e in edges}
    for e in edges:
        if (e['to'], e['from']) in edge_pairs:
            mutual_guarantees.append(f"{e['from_name']} ↔ {e['to_name']}")

    return {
        "group_id": group_id,
        "nodes": nodes,
        "edges": edges,
        "mutual_guarantees": list(set(mutual_guarantees)),
        "total_guarantee_amount": sum(e['guarantee_amount'] or 0 for e in edges),
    }


@router.post("/simulate/{application_id}")
def simulate_group_limit(
    application_id: str,
    db: Session = Depends(get_db)
):
    """신규 신청 승인 시 그룹 한도 영향 시뮬레이션"""
    app = db.execute(text("""
        SELECT a.customer_id, a.requested_amount, a.group_id
        FROM loan_application a
        WHERE a.application_id = :app_id
    """), {"app_id": application_id}).fetchone()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    customer_id = app[0]
    requested = app[1] or 0
    group_id = app[2]

    if not group_id:
        # 그룹 미설정 - borrower_group_member 조회
        membership = db.execute(text("""
            SELECT group_id FROM borrower_group_member
            WHERE customer_id = :cid LIMIT 1
        """), {"cid": customer_id}).fetchone()
        group_id = membership[0] if membership else None

    if not group_id:
        return {
            "application_id": application_id,
            "group_id": None,
            "message": "차주가 그룹에 속하지 않음 - 그룹 한도 체크 불필요",
        }

    result = check_group_limit.__wrapped__(group_id, requested, db) \
        if hasattr(check_group_limit, '__wrapped__') \
        else db.execute  # fallback

    # 직접 계산
    group = db.execute(text("""
        SELECT group_id, group_name, total_exposure, group_limit
        FROM borrower_group WHERE group_id = :gid
    """), {"gid": group_id}).fetchone()

    actual_exposure = db.execute(text("""
        SELECT COALESCE(SUM(f.outstanding_amount), 0)
        FROM facility f
        JOIN borrower_group_member bgm ON f.customer_id = bgm.customer_id
        WHERE bgm.group_id = :gid AND f.status = 'ACTIVE'
    """), {"gid": group_id}).scalar() or 0

    group_limit = group[3] or 0
    after = actual_exposure + requested
    util_after = (after / group_limit * 100) if group_limit > 0 else None

    bank_capital = db.execute(text("""
        SELECT total_capital FROM capital_position ORDER BY base_date DESC LIMIT 1
    """)).scalar() or 0
    reg_limit = bank_capital * 0.25

    return {
        "application_id": application_id,
        "group_id": group_id,
        "group_name": group[1],
        "before": {
            "exposure": actual_exposure,
            "utilization": round(actual_exposure / group_limit * 100, 2) if group_limit > 0 else None,
        },
        "after": {
            "exposure": after,
            "utilization": round(util_after, 2) if util_after else None,
            "status": _exposure_status(util_after),
        },
        "group_limit": group_limit,
        "regulatory_limit_25pct": reg_limit,
        "regulatory_ok": after <= reg_limit if reg_limit > 0 else True,
        "approval_flag": after > group_limit if group_limit > 0 else False,
    }


def _grade_order(grade: str) -> int:
    """신용등급 → 순서 (나쁠수록 높은 숫자)"""
    order = ['AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-',
             'BBB+', 'BBB', 'BBB-', 'BB+', 'BB', 'BB-',
             'B+', 'B', 'B-', 'CCC', 'CC', 'C', 'D']
    try:
        return order.index(grade)
    except ValueError:
        return 99


def _exposure_status(utilization_pct: Optional[float]) -> str:
    if utilization_pct is None:
        return 'UNKNOWN'
    if utilization_pct >= 100:
        return 'BREACH'
    if utilization_pct >= 90:
        return 'CRITICAL'
    if utilization_pct >= 80:
        return 'WARNING'
    return 'NORMAL'


# ─────────────────────────────────────────────────────────
# 동일차주 규제 범위 엔진 v1 - 신용공여 원장(credit_exposure_ledger) 기반
# (2차 리뷰 P0-2 반영)
#
# 원장은 난내(ON_LOAN)·난외(OFF_UNDRAWN·OFF_GUARANTEE)를 CCF 적용 후
# net_exposure 로 보유한다. 여기서는 원장 합산으로 법정 3개 한도를 통제한다:
#   · 동일차주(그룹) 25%           - 은행법 §35①
#   · 동일한 개인·법인(단일) 20%   - 은행법 §35③
#   · 거액신용공여 총액 500%       - 은행법 §35④ (자기자본 10% 초과 건 합계)
# 계열사 간 보증(group_guarantee)은 익스포저가 아니라 동일차주 구성·
# 위험전이 판단 자료로만 쓴다.
# ─────────────────────────────────────────────────────────

LIMIT_GROUP_RATIO = 0.25     # 동일차주(그룹)
LIMIT_SINGLE_RATIO = 0.20    # 동일한 개인·법인
LIMIT_LARGE_TRIGGER = 0.10   # 거액신용공여 판정 기준
LIMIT_LARGE_TOTAL = 5.00     # 거액신용공여 총액 한도 (자기자본의 500%)
INTERNAL_ALERT_RATIO = 0.15  # 내부 조기경보 (법정한도와 별개)


def _capital(db) -> float:
    row = db.execute(text(
        "SELECT total_capital FROM capital_position ORDER BY base_date DESC LIMIT 1"
    )).fetchone()
    return row[0] if row else 0.0


def _ledger_by_customer(db) -> dict:
    """고객별 원장 합산 {cust: {ON_LOAN, OFF_UNDRAWN, OFF_GUARANTEE, total}}"""
    out: dict = {}
    for cust, etype, net in db.execute(text("""
        SELECT customer_id, exposure_type, SUM(net_exposure)
        FROM credit_exposure_ledger GROUP BY customer_id, exposure_type
    """)).fetchall():
        d = out.setdefault(cust, {"ON_LOAN": 0.0, "OFF_UNDRAWN": 0.0,
                                  "OFF_GUARANTEE": 0.0, "total": 0.0})
        d[etype] = net or 0.0
        d["total"] += net or 0.0
    return out


@router.get("/statutory-limits")
def statutory_limits(db: Session = Depends(get_db)):
    """법정 3개 한도 통제 현황 (신용공여 원장 기반)"""
    capital = _capital(db)
    ledger = _ledger_by_customer(db)

    # ① 동일차주(그룹) 25%
    group_rows = db.execute(text("""
        SELECT bg.group_id, bg.group_name, m.customer_id
        FROM borrower_group bg JOIN borrower_group_member m ON m.group_id = bg.group_id
    """)).fetchall()
    group_sum: dict = {}
    grouped_customers = set()
    for gid, gname, cust in group_rows:
        g = group_sum.setdefault(gid, {"group_id": gid, "group_name": gname, "total": 0.0})
        g["total"] += ledger.get(cust, {}).get("total", 0.0)
        grouped_customers.add(cust)
    groups = sorted(group_sum.values(), key=lambda x: -x["total"])
    for g in groups:
        g["vs_capital_pct"] = round(g["total"] / capital * 100, 2) if capital else 0
        g["breach"] = g["total"] > capital * LIMIT_GROUP_RATIO

    # ② 동일한 개인·법인 20% (그룹 무관 단일 차주)
    singles = sorted(
        ({"customer_id": c, "total": v["total"]} for c, v in ledger.items()),
        key=lambda x: -x["total"])[:10]
    names = {r[0]: r[1] for r in db.execute(text(
        "SELECT customer_id, customer_name FROM customer WHERE customer_id IN ({})".format(
            ",".join(f"'{s['customer_id']}'" for s in singles) or "''")
    )).fetchall()}
    for s_ in singles:
        s_["name"] = names.get(s_["customer_id"], s_["customer_id"])
        s_["vs_capital_pct"] = round(s_["total"] / capital * 100, 2) if capital else 0
        s_["breach"] = s_["total"] > capital * LIMIT_SINGLE_RATIO

    # ③ 거액신용공여 총액 (자기자본 10% 초과 차주·그룹의 합 ≤ 500%)
    large_units = []
    for g in groups:
        if g["total"] > capital * LIMIT_LARGE_TRIGGER:
            large_units.append({"unit": g["group_name"], "total": g["total"]})
    for c, v in ledger.items():
        if c not in grouped_customers and v["total"] > capital * LIMIT_LARGE_TRIGGER:
            large_units.append({"unit": names.get(c, c), "total": v["total"]})
    large_total = sum(u["total"] for u in large_units)

    return {
        "capital": capital,
        "basis": "신용공여 원장(credit_exposure_ledger) - 난내·난외 CCF 적용 합산 (별표2 근사)",
        "controls": [
            {
                "key": "same_borrower_group",
                "name": "동일차주(그룹) 한도", "basis": "은행법 §35① - 자기자본의 25%",
                "limit": capital * LIMIT_GROUP_RATIO,
                "current": groups[0]["total"] if groups else 0,
                "current_label": groups[0]["group_name"] if groups else "-",
                "utilization_pct": round((groups[0]["total"] if groups else 0)
                                         / (capital * LIMIT_GROUP_RATIO) * 100, 1) if capital else 0,
                "breach": any(g["breach"] for g in groups),
                "top": groups[:5],
            },
            {
                "key": "same_person",
                "name": "동일한 개인·법인 한도", "basis": "은행법 §35③ - 자기자본의 20%",
                "limit": capital * LIMIT_SINGLE_RATIO,
                "current": singles[0]["total"] if singles else 0,
                "current_label": singles[0]["name"] if singles else "-",
                "utilization_pct": round((singles[0]["total"] if singles else 0)
                                         / (capital * LIMIT_SINGLE_RATIO) * 100, 1) if capital else 0,
                "breach": any(x["breach"] for x in singles),
                "top": singles[:5],
            },
            {
                "key": "large_exposure_total",
                "name": "거액신용공여 총액 한도",
                "basis": "은행법 §35④ - 자기자본 10% 초과 건 합계 ≤ 자기자본의 500%",
                "limit": capital * LIMIT_LARGE_TOTAL,
                "current": large_total,
                "current_label": f"{len(large_units)}개 거액차주",
                "utilization_pct": round(large_total / (capital * LIMIT_LARGE_TOTAL) * 100, 1)
                                   if capital else 0,
                "breach": large_total > capital * LIMIT_LARGE_TOTAL,
                "top": sorted(large_units, key=lambda x: -x["total"])[:5],
            },
        ],
        "disclaimer": "신용환산율·제외항목은 별표2의 근사(PoC)이며, 실제 산정은 "
                      "감독규정 정본과 준법 부서 해석을 따라야 한다.",
    }


@router.get("/regulatory-scope")
def regulatory_scope_overview(db: Session = Depends(get_db)):
    """그룹별 동일차주 합산 (원장 기반) - 난내·난외 분해 포함"""
    capital = _capital(db)
    ledger = _ledger_by_customer(db)
    rows = db.execute(text("""
        SELECT bg.group_id, bg.group_name, m.customer_id
        FROM borrower_group bg JOIN borrower_group_member m ON m.group_id = bg.group_id
    """)).fetchall()
    guar = {r[0]: r[1] or 0 for r in db.execute(text("""
        SELECT group_id, SUM(guarantee_amount) FROM group_guarantee
        WHERE status = 'ACTIVE' OR status IS NULL GROUP BY group_id
    """)).fetchall()}

    agg: dict = {}
    for gid, gname, cust in rows:
        g = agg.setdefault(gid, {"group_id": gid, "group_name": gname, "members": 0,
                                 "on_loan": 0.0, "off_undrawn": 0.0, "off_guarantee": 0.0})
        g["members"] += 1
        led = ledger.get(cust, {})
        g["on_loan"] += led.get("ON_LOAN", 0.0)
        g["off_undrawn"] += led.get("OFF_UNDRAWN", 0.0)
        g["off_guarantee"] += led.get("OFF_GUARANTEE", 0.0)

    groups = []
    for g in agg.values():
        total = g["on_loan"] + g["off_undrawn"] + g["off_guarantee"]
        groups.append({
            **{k: round(v, 2) if isinstance(v, float) else v for k, v in g.items()},
            "total_credit": round(total, 2),
            "intra_group_guarantees": round(guar.get(g["group_id"], 0), 2),
            "vs_capital_pct": round(total / capital * 100, 2) if capital else 0,
            "regulatory_breach": total > capital * LIMIT_GROUP_RATIO,
            "internal_alert": total > capital * INTERNAL_ALERT_RATIO,
        })
    groups.sort(key=lambda x: -x["total_credit"])
    return {
        "capital": capital,
        "regulatory_limit": {"ratio": LIMIT_GROUP_RATIO * 100, "amount": capital * LIMIT_GROUP_RATIO,
                             "basis": "은행법 §35① 동일차주 25% (원장 기반 - 별표2 근사)"},
        "internal_limit": {"ratio": INTERNAL_ALERT_RATIO * 100, "amount": capital * INTERNAL_ALERT_RATIO,
                           "basis": "내부 조기경보 기준 (법정 동일인 20% 한도와 별개)"},
        "groups": groups,
        "disclaimer": "신용공여 = 원장 net_exposure 합 (난내 대출 + 미사용약정 CCF 40% + 지급보증 CCF 100%)",
    }


@router.get("/regulatory-scope/{group_id}")
def regulatory_scope_detail(group_id: str, db: Session = Depends(get_db)):
    """동일차주 판단 재현 - 구성원별 포함 근거·원장 분해·위험전이 관계"""
    grp = db.execute(text(
        "SELECT group_id, group_name, group_type FROM borrower_group WHERE group_id = :g"
    ), {"g": group_id}).fetchone()
    if not grp:
        raise HTTPException(404, "차주그룹을 찾을 수 없습니다")
    capital = _capital(db)
    ledger = _ledger_by_customer(db)

    members = db.execute(text("""
        SELECT m.customer_id, c.customer_name, m.relationship_type, m.ownership_pct,
               MIN(f.contract_date)
        FROM borrower_group_member m
        JOIN customer c ON c.customer_id = m.customer_id
        LEFT JOIN facility f ON f.customer_id = m.customer_id AND f.status = 'ACTIVE'
        WHERE m.group_id = :g
        GROUP BY m.customer_id, c.customer_name, m.relationship_type, m.ownership_pct
    """), {"g": group_id}).fetchall()
    guarantees = db.execute(text("""
        SELECT gg.guarantor_id, gc.customer_name, gg.beneficiary_id, bc.customer_name,
               gg.guarantee_type, gg.guarantee_amount, gg.effective_date
        FROM group_guarantee gg
        LEFT JOIN customer gc ON gc.customer_id = gg.guarantor_id
        LEFT JOIN customer bc ON bc.customer_id = gg.beneficiary_id
        WHERE gg.group_id = :g AND (gg.status = 'ACTIVE' OR gg.status IS NULL)
    """), {"g": group_id}).fetchall()

    BASIS = {"PARENT": "모회사 (지배)", "SUBSIDIARY": "자회사 (피지배)",
             "AFFILIATE": "계열회사 (동일 지배하)", "GUARANTOR": "상호보증 (위험공유)"}
    member_list, on_loan, off_und, off_g = [], 0.0, 0.0, 0.0
    for cid, name, rel, pct, first_contract in members:
        led = ledger.get(cid, {})
        on_loan += led.get("ON_LOAN", 0.0)
        off_und += led.get("OFF_UNDRAWN", 0.0)
        off_g += led.get("OFF_GUARANTEE", 0.0)
        member_list.append({
            "customer_id": cid, "name": name,
            "relationship": rel, "basis": BASIS.get(rel, rel or "지분관계"),
            "ownership_pct": pct,
            "loans": round(led.get("ON_LOAN", 0.0), 2),
            "undrawn": round(led.get("OFF_UNDRAWN", 0.0), 2),
            "guarantee": round(led.get("OFF_GUARANTEE", 0.0), 2),
            "effective_from": first_contract,
        })
    total = on_loan + off_und + off_g
    guar_total = sum(g[5] or 0 for g in guarantees)

    return {
        "group": {"group_id": grp[0], "group_name": grp[1], "type": grp[2]},
        "members": member_list,
        "risk_transfer": [
            {"guarantor_id": g[0], "guarantor": g[1], "beneficiary_id": g[2],
             "beneficiary": g[3], "type": g[4], "amount": g[5], "effective_date": g[6]}
            for g in guarantees
        ],
        "aggregation": {
            "loans": round(on_loan, 2), "undrawn": round(off_und, 2),
            "bank_guarantees": round(off_g, 2),
            "intra_group_guarantees": round(guar_total, 2),
            "total_credit": round(total, 2),
            "capital": capital,
            "vs_capital_pct": round(total / capital * 100, 2) if capital else 0,
            "regulatory_limit_pct": LIMIT_GROUP_RATIO * 100,
            "internal_limit_pct": INTERNAL_ALERT_RATIO * 100,
            "note": "신용공여 원장 기반: 난내 대출(CCF 1.0) + 미사용약정(CCF 0.4) + "
                    "은행 지급보증(CCF 1.0). 계열사 간 보증은 위험전이 참고.",
        },
    }
