"""
통합 의무관리함 (Obligation Inbox)
===================================
정책 예외 재검토, 승인조건 이행, EWS 조치, 코베넌트 점검, 금리인하 SLA 를
하나의 '의무' 목록으로 통합한다 (7단계-⑤). 각 의무는 소스 화면으로
딥링크되며, 완료 처리는 각 소스 API 가 담당한다.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..core.config import AS_OF_STR

router = APIRouter(prefix="/api/obligations", tags=["Obligations"])


@router.get("")
def list_obligations(db: Session = Depends(get_db)):
    items = []

    # ① 정책 예외 재검토
    for r in db.execute(text("""
        SELECT pe.exception_id, c.customer_name, pe.rule_ref, pe.review_date
        FROM policy_exception pe LEFT JOIN customer c ON c.customer_id = pe.customer_id
        WHERE pe.status = 'ACTIVE'
    """)).fetchall():
        items.append({
            "type": "POLICY_EXCEPTION", "type_ko": "정책 예외 재검토",
            "ref_id": r[0], "subject": f"{r[1]} - {r[2]}",
            "owner": "여신심사부", "due_date": r[3],
            "overdue": (r[3] or "9999") < AS_OF_STR,
            "link": "/governance",
        })

    # ② EWS 조치
    for r in db.execute(text("""
        SELECT a.action_id, c.customer_name, a.step, a.owner, a.due_date, a.escalated
        FROM ews_action a LEFT JOIN customer c ON c.customer_id = a.customer_id
        WHERE a.status != 'DONE'
    """)).fetchall():
        items.append({
            "type": "EWS_ACTION", "type_ko": "EWS 조치",
            "ref_id": r[0], "subject": f"{r[1]} - {r[2]}",
            "owner": r[3], "due_date": r[4],
            "overdue": (r[4] or "9999") < AS_OF_STR,
            "escalated": bool(r[5]),
            "link": "/ews-advanced",
        })

    # ③ 금리인하 SLA
    for r in db.execute(text("""
        SELECT r.request_id, c.customer_name, r.status, r.due_date
        FROM rate_reduction_request r
        LEFT JOIN customer c ON c.customer_id = r.customer_id
        WHERE r.status IN ('RECEIVED','REVIEWING','SUPPLEMENT')
           OR (r.status IN ('ACCEPTED','PARTIAL','REJECTED') AND r.notified_at IS NULL)
    """)).fetchall():
        pending_notify = r[2] in ("ACCEPTED", "PARTIAL", "REJECTED")
        items.append({
            "type": "RATE_REDUCTION", "type_ko": "금리인하요구",
            "ref_id": r[0],
            "subject": f"{r[1]} - " + ("통지 발송 필요" if pending_notify else "심사·결정"),
            "owner": "여신심사부", "due_date": r[3],
            "overdue": not pending_notify and (r[3] or "9999") < AS_OF_STR,
            "link": "/rate-reduction",
        })

    # ④ 코베넌트 점검 도래
    for r in db.execute(text("""
        SELECT cv.covenant_id, c.customer_name, cv.covenant_name, cv.next_check_date
        FROM covenant cv
        JOIN facility f ON f.facility_id = cv.facility_id
        LEFT JOIN customer c ON c.customer_id = f.customer_id
        WHERE cv.status = 'ACTIVE' AND cv.next_check_date <= date(:asof, '+30 day')
        LIMIT 40
    """), {"asof": AS_OF_STR}).fetchall():
        items.append({
            "type": "COVENANT_CHECK", "type_ko": "코베넌트 점검",
            "ref_id": r[0], "subject": f"{r[1]} - {r[2]}",
            "owner": "담당 RM", "due_date": r[3],
            "overdue": (r[3] or "9999") < AS_OF_STR,
            "link": "/covenant",
        })

    # ⑤ 조건부 승인 조건 이행
    for r in db.execute(text("""
        SELECT ah.application_id, c.customer_name, ah.conditions, ah.decided_at
        FROM approval_history ah
        JOIN loan_application la ON la.application_id = ah.application_id
        LEFT JOIN customer c ON c.customer_id = la.customer_id
        WHERE ah.conditions IS NOT NULL AND ah.conditions != ''
          AND la.status IN ('APPROVED','CONDITIONAL','DISBURSED')
        ORDER BY ah.decided_at DESC LIMIT 30
    """)).fetchall():
        items.append({
            "type": "APPROVAL_CONDITION", "type_ko": "승인조건 이행",
            "ref_id": r[0], "subject": f"{r[1]} - {r[2][:40]}",
            "owner": "담당 RM",
            "due_date": (r[3] or AS_OF_STR)[:10],
            "overdue": False,
            "link": f"/credit-case/{r[0]}",
        })

    items.sort(key=lambda x: (not x["overdue"], x["due_date"] or "9999"))
    by_type: dict = {}
    for it in items:
        t = by_type.setdefault(it["type_ko"], {"total": 0, "overdue": 0})
        t["total"] += 1
        t["overdue"] += 1 if it["overdue"] else 0

    return {
        "as_of": AS_OF_STR,
        "total": len(items),
        "overdue": sum(1 for i in items if i["overdue"]),
        "by_type": by_type,
        "items": items[:200],
    }
