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
