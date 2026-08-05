"""
기업 금리인하요구권 API
=======================
은행법 시행령 §18-4: 재무상태 개선·신용등급 상승 등이 있으면 기업 차주도
금리인하를 요구할 수 있고, 은행은 보완기간 제외 10영업일 이내에 수용 여부와
사유를 통지해야 한다. 이 모듈은 접수→재산정 비교→결정→통지의 법정 절차와
SLA 타이머를 관리한다 (제3자 리뷰 ⑤).
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..core.config import AS_OF_STR, AS_OF_DATE
from ..core.audit import record_audit
from ..core.auth import get_current_user, User

router = APIRouter(prefix="/api/rate-reduction", tags=["RateReduction"])

GROUND_LABELS = {
    "FIN_IMPROVE": "재무상태 개선", "GRADE_UP": "신용등급 상승",
    "REVENUE_UP": "매출 증가·흑자전환", "COLLATERAL_ADD": "담보 보강",
}
STATUS_LABELS = {
    "RECEIVED": "접수", "REVIEWING": "심사중", "ACCEPTED": "수용",
    "PARTIAL": "부분수용", "REJECTED": "거절",
}


def biz_days_between(a: date, b: date) -> int:
    """a→b 남은 영업일 (b<a 면 음수)"""
    if b < a:
        return -biz_days_between(b, a)
    n, d = 0, a
    while d < b:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT status, COUNT(*), AVG(CASE WHEN status IN ('ACCEPTED','PARTIAL')
                                     THEN (old_rate - decided_rate) END)
        FROM rate_reduction_request GROUP BY status
    """)).fetchall()
    by = {r[0]: r[1] for r in rows}
    pending = by.get("RECEIVED", 0) + by.get("REVIEWING", 0)
    decided = by.get("ACCEPTED", 0) + by.get("PARTIAL", 0) + by.get("REJECTED", 0)
    accepted = by.get("ACCEPTED", 0) + by.get("PARTIAL", 0)
    overdue = db.execute(text("""
        SELECT COUNT(*) FROM rate_reduction_request
        WHERE status IN ('RECEIVED','REVIEWING') AND due_date < :asof
    """), {"asof": AS_OF_STR}).fetchone()[0]
    avg_cut = db.execute(text("""
        SELECT AVG(old_rate - decided_rate) FROM rate_reduction_request
        WHERE status IN ('ACCEPTED','PARTIAL')
    """)).fetchone()[0]
    return {
        "as_of": AS_OF_STR,
        "pending": pending,
        "overdue": overdue,
        "decided": decided,
        "acceptance_rate": round(accepted / decided * 100, 1) if decided else 0,
        "avg_cut_bp": round((avg_cut or 0) * 10000, 1),
        "sla_note": "은행법 시행령 §18-4 - 보완기간 제외 10영업일 이내 통지 의무",
    }


@router.get("/requests")
def list_requests(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT r.request_id, r.customer_id, c.customer_name, r.facility_id,
               r.request_date, r.grounds, r.grounds_detail, r.due_date, r.status,
               r.old_rate, r.proposed_rate, r.decided_rate, r.decision_reason,
               r.decided_at, r.notified_at,
               g.final_grade
        FROM rate_reduction_request r
        LEFT JOIN customer c ON c.customer_id = r.customer_id
        LEFT JOIN (SELECT customer_id, final_grade,
                          ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY rating_date DESC) rn
                   FROM credit_rating_result) g
          ON g.customer_id = r.customer_id AND g.rn = 1
        ORDER BY CASE WHEN r.status IN ('RECEIVED','REVIEWING') THEN 0 ELSE 1 END,
                 r.due_date
    """)).fetchall()
    out = []
    for r in rows:
        pending = r[8] in ("RECEIVED", "REVIEWING")
        d_left = None
        if pending and r[7]:
            d_left = biz_days_between(AS_OF_DATE, date.fromisoformat(r[7]))
        out.append({
            "request_id": r[0], "customer_id": r[1], "customer_name": r[2],
            "facility_id": r[3], "request_date": r[4],
            "grounds": r[5], "grounds_label": GROUND_LABELS.get(r[5], r[5]),
            "grounds_detail": r[6], "due_date": r[7],
            "status": r[8], "status_label": STATUS_LABELS.get(r[8], r[8]),
            "old_rate": r[9], "proposed_rate": r[10], "decided_rate": r[11],
            "decision_reason": r[12], "decided_at": r[13], "notified_at": r[14],
            "grade": r[15],
            "biz_days_left": d_left,
            "overdue": pending and d_left is not None and d_left < 0,
        })
    return {"as_of": AS_OF_STR, "requests": out}


@router.post("/requests/{request_id}/decide")
def decide(request_id: str, payload: dict = Body(...), db: Session = Depends(get_db),
           current_user: User = Depends(get_current_user)):
    """수용/부분수용/거절 결정 + 통지 기록. 사유 필수 (설명의무).

    PoC 한계: 통지는 별도 발송 채널 없이 결정과 동시에 기록된다
    (실제 구현 시 RECEIVED→SUPPLEMENT→REVIEWING→DECIDED→NOTIFIED 상태기계와
    발송·수신확인 이력이 필요 - 제3자 리뷰 권고 반영 예정)."""
    decision = payload.get("decision")
    reason = (payload.get("reason") or "").strip()
    new_rate = payload.get("new_rate")
    if decision not in ("ACCEPTED", "PARTIAL", "REJECTED"):
        raise HTTPException(422, "decision 은 ACCEPTED/PARTIAL/REJECTED 중 하나여야 합니다")
    if len(reason) < 5:
        raise HTTPException(422, "결정 사유를 5자 이상 기록해야 합니다 (고객 통지문에 포함)")

    row = db.execute(text("""
        SELECT status, old_rate FROM rate_reduction_request WHERE request_id = :id
    """), {"id": request_id}).fetchone()
    if not row:
        raise HTTPException(404, "요청 건을 찾을 수 없습니다")
    if row[0] not in ("RECEIVED", "REVIEWING"):
        raise HTTPException(409, "이미 처리된 요청입니다")

    old_rate = row[1] or 0
    if decision == "REJECTED":
        decided_rate = old_rate
    else:
        import math
        try:
            decided_rate = float(new_rate)
        except (TypeError, ValueError):
            raise HTTPException(422, "new_rate 가 유효한 숫자가 아닙니다")
        if not math.isfinite(decided_rate):
            raise HTTPException(422, "new_rate 가 유한한 값이 아닙니다")
        if decided_rate <= 0:
            raise HTTPException(422, "금리는 0보다 커야 합니다 (음수·0 금리 불가)")
        if decided_rate >= old_rate:
            raise HTTPException(422, "수용 시 new_rate 는 기존 금리보다 낮아야 합니다")
        if decided_rate < old_rate * 0.5:
            raise HTTPException(422, "기존 금리의 50% 미만 인하는 재산정 오류 가능성 - 별도 승인 필요")

    db.execute(text("""
        UPDATE rate_reduction_request
        SET status = :st, decided_rate = :dr, proposed_rate = :dr,
            decision_reason = :rs, decided_at = :at, notified_at = :at
        WHERE request_id = :id
    """), {"st": decision, "dr": decided_rate, "rs": reason, "at": AS_OF_STR, "id": request_id})
    record_audit(db, action_type="RATE_REDUCTION_DECIDE", target_entity="rate_reduction_request",
                 target_id=request_id, before={"status": row[0], "old_rate": old_rate},
                 after={"status": decision, "decided_rate": decided_rate},
                 user_id=current_user.name, user_dept=current_user.dept)
    db.commit()
    return {"request_id": request_id, "status": decision,
            "decided_rate": decided_rate, "notified_at": AS_OF_STR}
