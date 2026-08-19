"""
여신 거래 생애주기 API (P6 씬슬라이스)
========================================
"Credit **Lifecycle** Management System"에 갱신·연장·조건변경·종결 *거래*가
0건이던 최대 구조 공백을, 기한연장 + 조건변경 재승인 두 거래로 얇게 연다.

에버그리닝 통제가 설계의 중심이다. 기업대출 연체율 2.43%(2026.1Q, 장기평균
1.62% 상회 - 한은 금융안정보고서) 국면에서 만기연장에 의한 부실 이연은
고전적 감독 관심사다. 연장 심사 시 서버가 EWS·건전성 분류·약정 위반·연속
연장 이력을 강제 수집하고, 에버그리닝 플래그가 있으면 부서장 이상 전결로
상향한다 (플래그를 무시한 연장은 존재하되, 반드시 상급자 이름으로 남는다).

통제 완결 원칙: 상태기계(REQUESTED→APPROVED/REJECTED) · 전결권(금액 +
플래그 상향) · 감사기록(critical) 을 갖춰 출고한다.
"""
import json
import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..core.config import AS_OF_DATE
from ..core.auth import get_current_user, User
from ..core.audit import record_audit

router = APIRouter(prefix="/api/lifecycle", tags=["Facility Lifecycle"])

NPL_CLASSES = ("SUBSTANDARD", "DOUBTFUL", "ESTIMATED_LOSS")

# 전결권 (approval_authority 와 동일 스케일)
AUTHORITY_LIMIT = {
    "STAFF": 5e8, "TEAM_LEAD": 50e8, "DEPT_HEAD": 200e8,
    "EXECUTIVE": 1000e8, "COMMITTEE": float("inf"),
}
LEVEL_RANK = {"STAFF": 1, "TEAM_LEAD": 2, "DEPT_HEAD": 3, "EXECUTIVE": 4, "COMMITTEE": 5}


def _assemble_review(db: Session, facility_id: str) -> tuple[dict, list[str]]:
    """연장·조건변경 심사에 강제 표시할 리스크 스냅샷과 에버그리닝 플래그.

    서버가 수집한다 - 클라이언트가 좋은 값만 골라 보낼 수 없다.
    """
    fac = db.execute(text("""
        SELECT f.facility_id, f.customer_id, f.outstanding_amount, f.dpd,
               f.classification, f.maturity_date, c.customer_name
        FROM facility f JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.facility_id = :fid
    """), {"fid": facility_id}).fetchone()
    if not fac:
        raise HTTPException(404, "여신 없음")

    customer_id = fac[1]
    ews = db.execute(text("""
        SELECT composite_score FROM ews_composite_score
        WHERE customer_id = :cid ORDER BY score_date DESC LIMIT 1
    """), {"cid": customer_id}).fetchone()
    ews_score = float(ews[0]) if ews else None

    breach = db.execute(text("""
        SELECT COUNT(*) FROM covenant cv
        WHERE cv.facility_id = :fid AND cv.status = 'BREACHED'
    """), {"fid": facility_id}).scalar() or 0

    prev_ext = db.execute(text("""
        SELECT COALESCE(MAX(consecutive_extensions), 0) FROM facility_transaction
        WHERE facility_id = :fid AND txn_type = 'EXTENSION' AND status = 'APPROVED'
    """), {"fid": facility_id}).scalar() or 0

    flags = []
    if prev_ext >= 1:
        flags.append(f"연속 연장 {prev_ext + 1}회차 - 상환 능력 재검증 필요")
    if fac[3] and fac[3] > 0:
        flags.append(f"연체 중 연장 (DPD {fac[3]}일)")
    if fac[4] and fac[4] != "NORMAL":
        flags.append(f"건전성 {fac[4]} 상태에서 연장")
    if ews_score is not None and ews_score < 50:
        flags.append(f"EWS 악화 상태 (종합 {ews_score:.1f}점)")
    if breach:
        flags.append(f"약정 위반 미치유 {breach}건")

    review = {
        "customer_id": customer_id,
        "customer_name": fac[6],
        "outstanding": float(fac[2] or 0),
        "dpd": fac[3] or 0,
        "classification": fac[4],
        "maturity_date": str(fac[5]) if fac[5] else None,
        "ews_score": ews_score,
        "covenant_breaches": int(breach),
        "prev_extensions": int(prev_ext),
    }
    return review, flags


def _authority_check(user: User, amount: float, flags: list[str]) -> None:
    """금액 전결권 + 에버그리닝 플래그 상향 (플래그 있으면 부서장 이상)"""
    if amount > AUTHORITY_LIMIT.get(user.approval_level, 0):
        raise HTTPException(403, f"{user.approval_level} 전결 한도 초과 - 상위 결재 필요")
    if flags and LEVEL_RANK.get(user.approval_level, 0) < LEVEL_RANK["DEPT_HEAD"]:
        raise HTTPException(
            403, "에버그리닝 플래그가 있는 거래는 부서장 이상만 결재할 수 있습니다")


@router.get("/maturing")
def get_maturing_facilities(
    days_ahead: int = Query(90, le=365),
    db: Session = Depends(get_db),
):
    """만기 도래 여신 (연장 심사 대상 파이프라인)"""
    cutoff = AS_OF_DATE + timedelta(days=days_ahead)
    rows = db.execute(text("""
        SELECT f.facility_id, f.customer_id, c.customer_name, f.facility_type,
               f.outstanding_amount, f.maturity_date, f.dpd, f.classification,
               (SELECT composite_score FROM ews_composite_score e
                WHERE e.customer_id = f.customer_id ORDER BY score_date DESC LIMIT 1),
               (SELECT COALESCE(MAX(consecutive_extensions), 0) FROM facility_transaction t
                WHERE t.facility_id = f.facility_id AND t.txn_type='EXTENSION' AND t.status='APPROVED'),
               (SELECT COUNT(*) FROM facility_transaction t
                WHERE t.facility_id = f.facility_id AND t.status = 'REQUESTED')
        FROM facility f JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.status = 'ACTIVE' AND f.maturity_date BETWEEN :today AND :cutoff
        ORDER BY f.maturity_date ASC LIMIT 100
    """), {"today": str(AS_OF_DATE), "cutoff": str(cutoff)}).fetchall()

    items = []
    for r in rows:
        risk_marks = []
        if r[6] and r[6] > 0:
            risk_marks.append("연체")
        if r[7] and r[7] != "NORMAL":
            risk_marks.append("분류하락")
        if r[8] is not None and float(r[8]) < 50:
            risk_marks.append("EWS악화")
        if (r[9] or 0) >= 1:
            risk_marks.append(f"기연장{r[9]}회")
        items.append({
            "facility_id": r[0], "customer_id": r[1], "customer_name": r[2],
            "facility_type": r[3],
            "outstanding_eok": round(float(r[4] or 0) / 1e8, 1),
            "maturity_date": str(r[5]),
            "days_to_maturity": (date.fromisoformat(str(r[5])) - AS_OF_DATE).days,
            "dpd": r[6] or 0, "classification": r[7],
            "ews_score": float(r[8]) if r[8] is not None else None,
            "prev_extensions": r[9] or 0,
            "pending_txn": bool(r[10]),
            "risk_marks": risk_marks,
        })
    return {"cutoff": str(cutoff), "total": len(items), "facilities": items}


@router.post("/extension/{facility_id}")
def request_extension(
    facility_id: str,
    extension_months: int = Query(12, ge=1, le=60),
    reason: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """기한연장 신청 - 리스크 스냅샷·에버그리닝 플래그를 서버가 강제 수집"""
    dup = db.execute(text("""
        SELECT txn_id FROM facility_transaction
        WHERE facility_id = :fid AND status = 'REQUESTED'
    """), {"fid": facility_id}).fetchone()
    if dup:
        raise HTTPException(409, "이미 심사 중인 거래가 있습니다")

    review, flags = _assemble_review(db, facility_id)
    cur_maturity = review["maturity_date"]
    base = date.fromisoformat(cur_maturity) if cur_maturity else AS_OF_DATE
    new_maturity = base + timedelta(days=extension_months * 30)

    txn_id = f"TXN_{uuid.uuid4().hex[:10].upper()}"
    db.execute(text("""
        INSERT INTO facility_transaction
            (txn_id, facility_id, customer_id, txn_type, status, requested_by,
             current_maturity, new_maturity, extension_months,
             consecutive_extensions, review_json, evergreen_flags)
        VALUES (:tid, :fid, :cid, 'EXTENSION', 'REQUESTED', :rby,
                :cur, :new, :months, :consec, :review, :flags)
    """), {
        "tid": txn_id, "fid": facility_id, "cid": review["customer_id"],
        "rby": current_user.name, "cur": cur_maturity, "new": str(new_maturity),
        "months": extension_months,
        "consec": review["prev_extensions"] + 1,
        "review": json.dumps({**review, "reason": reason}, ensure_ascii=False),
        "flags": json.dumps(flags, ensure_ascii=False),
    })
    record_audit(db, "LIFECYCLE_EXT_REQUEST", "facility_transaction", txn_id,
                 after={"facility_id": facility_id, "months": extension_months,
                        "evergreen_flags": flags},
                 user_id=current_user.name, user_dept=current_user.dept,
                 critical=True)
    db.commit()
    return {"txn_id": txn_id, "evergreen_flags": flags, "review": review,
            "new_maturity": str(new_maturity),
            "requires_dept_head": bool(flags)}


@router.post("/modification/{facility_id}")
def request_modification(
    facility_id: str,
    new_rate: float = Query(None, description="변경 금리 (%)"),
    new_limit_eok: float = Query(None, description="변경 한도 (억)"),
    reason: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """조건변경(금리·한도) 재승인 신청"""
    if new_rate is None and new_limit_eok is None:
        raise HTTPException(422, "변경할 조건(금리 또는 한도)을 지정하세요")
    dup = db.execute(text("""
        SELECT txn_id FROM facility_transaction
        WHERE facility_id = :fid AND status = 'REQUESTED'
    """), {"fid": facility_id}).fetchone()
    if dup:
        raise HTTPException(409, "이미 심사 중인 거래가 있습니다")

    review, flags = _assemble_review(db, facility_id)
    cur = db.execute(text(
        "SELECT final_rate, current_limit FROM facility WHERE facility_id = :fid"),
        {"fid": facility_id}).fetchone()

    change = {}
    if new_rate is not None:
        change["rate"] = {"from": float(cur[0] or 0) * 100, "to": new_rate}
        # 금리 인하 + 리스크 악화 조합은 그 자체가 에버그리닝 신호
        if new_rate < float(cur[0] or 0) * 100 and flags:
            flags.append("리스크 악화 상태에서 금리 인하 - 이연 우대 소지")
    if new_limit_eok is not None:
        change["limit"] = {"from": round(float(cur[1] or 0) / 1e8, 1), "to": new_limit_eok}

    txn_id = f"TXN_{uuid.uuid4().hex[:10].upper()}"
    db.execute(text("""
        INSERT INTO facility_transaction
            (txn_id, facility_id, customer_id, txn_type, status, requested_by,
             change_json, review_json, evergreen_flags)
        VALUES (:tid, :fid, :cid, 'MODIFICATION', 'REQUESTED', :rby,
                :change, :review, :flags)
    """), {
        "tid": txn_id, "fid": facility_id, "cid": review["customer_id"],
        "rby": current_user.name,
        "change": json.dumps(change, ensure_ascii=False),
        "review": json.dumps({**review, "reason": reason}, ensure_ascii=False),
        "flags": json.dumps(flags, ensure_ascii=False),
    })
    record_audit(db, "LIFECYCLE_MOD_REQUEST", "facility_transaction", txn_id,
                 after={"facility_id": facility_id, "change": change,
                        "evergreen_flags": flags},
                 user_id=current_user.name, user_dept=current_user.dept,
                 critical=True)
    db.commit()
    return {"txn_id": txn_id, "change": change, "evergreen_flags": flags,
            "requires_dept_head": bool(flags)}


@router.post("/transactions/{txn_id}/decide")
def decide_transaction(
    txn_id: str,
    decision: str = Query(..., pattern="^(APPROVED|REJECTED)$"),
    reason: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """연장·조건변경 결재 - 금액 전결권 + 에버그리닝 플래그 상향"""
    txn = db.execute(text("""
        SELECT txn_id, facility_id, txn_type, status, new_maturity,
               change_json, evergreen_flags, review_json
        FROM facility_transaction WHERE txn_id = :tid
    """), {"tid": txn_id}).fetchone()
    if not txn:
        raise HTTPException(404, "거래 없음")
    if txn[3] != "REQUESTED":
        raise HTTPException(422, f"이미 처리된 거래입니다: {txn[3]}")

    review = json.loads(txn[7] or "{}")
    flags = json.loads(txn[6] or "[]")
    _authority_check(current_user, review.get("outstanding", 0), flags)

    before = {}
    after = {}
    if decision == "APPROVED":
        if txn[2] == "EXTENSION":
            row = db.execute(text(
                "SELECT maturity_date FROM facility WHERE facility_id = :fid"),
                {"fid": txn[1]}).fetchone()
            before["maturity_date"] = str(row[0]) if row and row[0] else None
            db.execute(text(
                "UPDATE facility SET maturity_date = :m WHERE facility_id = :fid"),
                {"m": txn[4], "fid": txn[1]})
            after["maturity_date"] = txn[4]
        else:
            change = json.loads(txn[5] or "{}")
            row = db.execute(text(
                "SELECT final_rate, current_limit FROM facility WHERE facility_id = :fid"),
                {"fid": txn[1]}).fetchone()
            if "rate" in change:
                before["final_rate"] = float(row[0] or 0)
                db.execute(text(
                    "UPDATE facility SET final_rate = :r WHERE facility_id = :fid"),
                    {"r": change["rate"]["to"] / 100, "fid": txn[1]})
                after["final_rate"] = change["rate"]["to"] / 100
            if "limit" in change:
                before["current_limit"] = float(row[1] or 0)
                db.execute(text(
                    "UPDATE facility SET current_limit = :l WHERE facility_id = :fid"),
                    {"l": change["limit"]["to"] * 1e8, "fid": txn[1]})
                after["current_limit"] = change["limit"]["to"] * 1e8

    db.execute(text("""
        UPDATE facility_transaction
        SET status = :st, decision = :st, decided_by = :by,
            decided_level = :lv, decided_at = CURRENT_TIMESTAMP,
            decision_reason = :reason
        WHERE txn_id = :tid
    """), {"st": decision, "by": current_user.name,
           "lv": current_user.approval_level, "reason": reason, "tid": txn_id})

    record_audit(db, f"LIFECYCLE_{decision}", "facility_transaction", txn_id,
                 before=before,
                 after={**after, "txn_type": txn[2], "evergreen_flags": flags,
                        "reason": reason},
                 user_id=current_user.name, user_dept=current_user.dept,
                 critical=True)
    db.commit()
    return {"txn_id": txn_id, "decision": decision,
            "decided_by": current_user.name,
            "decided_level": current_user.approval_level,
            "facility_updates": after}


@router.get("/transactions")
def list_transactions(
    status: str = Query(None),
    db: Session = Depends(get_db),
):
    """생애주기 거래 목록"""
    cond = "WHERE t.status = :status" if status else ""
    rows = db.execute(text(f"""
        SELECT t.txn_id, t.facility_id, t.customer_id, c.customer_name,
               t.txn_type, t.status, t.requested_at, t.requested_by,
               t.current_maturity, t.new_maturity, t.extension_months,
               t.consecutive_extensions, t.change_json, t.evergreen_flags,
               t.decided_by, t.decided_level, t.decided_at, t.review_json
        FROM facility_transaction t
        JOIN customer c ON t.customer_id = c.customer_id
        {cond}
        ORDER BY t.requested_at DESC LIMIT 50
    """), {"status": status} if status else {}).fetchall()
    return {"transactions": [
        {"txn_id": r[0], "facility_id": r[1], "customer_id": r[2],
         "customer_name": r[3], "txn_type": r[4], "status": r[5],
         "requested_at": str(r[6]), "requested_by": r[7],
         "current_maturity": r[8], "new_maturity": r[9],
         "extension_months": r[10], "consecutive_extensions": r[11],
         "change": json.loads(r[12]) if r[12] else None,
         "evergreen_flags": json.loads(r[13]) if r[13] else [],
         "decided_by": r[14], "decided_level": r[15],
         "decided_at": str(r[16]) if r[16] else None,
         "review": json.loads(r[17]) if r[17] else {}}
        for r in rows
    ]}


@router.get("/evergreening-watch")
def get_evergreening_watch(db: Session = Depends(get_db)):
    """에버그리닝 관제 - 플래그를 안고 승인된 연장·변경의 사후 추적"""
    rows = db.execute(text("""
        SELECT t.txn_id, t.facility_id, c.customer_name, t.txn_type,
               t.evergreen_flags, t.decided_by, t.decided_level, t.decided_at,
               f.dpd, f.classification, t.consecutive_extensions
        FROM facility_transaction t
        JOIN customer c ON t.customer_id = c.customer_id
        JOIN facility f ON t.facility_id = f.facility_id
        WHERE t.status = 'APPROVED' AND t.evergreen_flags != '[]'
        ORDER BY t.decided_at DESC LIMIT 30
    """)).fetchall()
    return {
        "note": "에버그리닝 플래그를 안고 승인된 거래 - 부서장 이상 실명 결재가 강제되며, 사후 건전성 추적 대상",
        "items": [
            {"txn_id": r[0], "facility_id": r[1], "customer_name": r[2],
             "txn_type": r[3], "flags": json.loads(r[4] or "[]"),
             "decided_by": r[5], "decided_level": r[6],
             "decided_at": str(r[7]) if r[7] else None,
             "current_dpd": r[8] or 0, "current_class": r[9],
             "consecutive_extensions": r[10]}
            for r in rows
        ],
    }
