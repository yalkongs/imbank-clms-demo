"""
EWS 조치의무 API
================
경보를 '점수 화면'이 아니라 '조치 의무'로 관리한다 (제3자 리뷰 ⑨).
경보마다 Playbook 단계·담당·기한이 붙고, 기한초과는 자동 상향보고 표시.
조치 완료는 근거 텍스트를 강제하고 감사 기록을 남긴다.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..core.config import AS_OF_STR
from ..core.audit import record_audit

router = APIRouter(prefix="/api/ews-actions", tags=["EWSActions"])


@router.get("/summary")
def get_action_summary(db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT COUNT(*),
               SUM(CASE WHEN status = 'DONE' THEN 1 ELSE 0 END),
               SUM(CASE WHEN status != 'DONE' AND due_date < :asof THEN 1 ELSE 0 END),
               SUM(CASE WHEN escalated = 1 THEN 1 ELSE 0 END)
        FROM ews_action
    """), {"asof": AS_OF_STR}).fetchone()
    total, done, overdue, escalated = row
    return {
        "as_of": AS_OF_STR,
        "total": total or 0,
        "done": done or 0,
        "open": (total or 0) - (done or 0),
        "overdue": overdue or 0,
        "escalated": escalated or 0,
        "completion_rate": round((done or 0) / total * 100, 1) if total else 0,
    }


@router.get("")
def list_actions(db: Session = Depends(get_db)):
    """경보-조치 목록 (경보별 그룹) - 담당·기한·상태·기한초과"""
    rows = db.execute(text("""
        SELECT a.action_id, a.alert_id, a.customer_id, c.customer_name,
               e.alert_type, e.severity, e.alert_date, e.description,
               a.step_no, a.step, a.owner, a.due_date, a.status,
               a.action_taken, a.completed_at, a.escalated
        FROM ews_action a
        JOIN ews_alert e ON e.alert_id = a.alert_id
        LEFT JOIN customer c ON c.customer_id = a.customer_id
        ORDER BY e.alert_date DESC, a.alert_id, a.step_no
    """)).fetchall()
    alerts: dict = {}
    for r in rows:
        a = alerts.setdefault(r[1], {
            "alert_id": r[1], "customer_id": r[2], "customer_name": r[3],
            "alert_type": r[4], "severity": r[5], "alert_date": r[6],
            "description": r[7], "actions": [],
        })
        a["actions"].append({
            "action_id": r[0], "step_no": r[8], "step": r[9], "owner": r[10],
            "due_date": r[11], "status": r[12], "action_taken": r[13],
            "completed_at": r[14], "escalated": bool(r[15]),
            "overdue": r[12] != "DONE" and (r[11] or "9999") < AS_OF_STR,
        })
    return {"as_of": AS_OF_STR, "alerts": list(alerts.values())}


@router.post("/{action_id}/complete")
def complete_action(action_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    """조치 완료 - 조치 내용 필수 (자유 메모가 아니라 근거 강제)"""
    taken = (payload.get("action_taken") or "").strip()
    if len(taken) < 5:
        raise HTTPException(422, "조치 내용을 5자 이상 기록해야 합니다")
    row = db.execute(text(
        "SELECT status, step, customer_id, alert_id, step_no FROM ews_action WHERE action_id = :id"
    ), {"id": action_id}).fetchone()
    if not row:
        raise HTTPException(404, "조치 항목을 찾을 수 없습니다")
    if row[0] == "DONE":
        raise HTTPException(409, "이미 완료된 조치입니다")
    # Playbook 은 순서가 의무다 - 선행단계가 끝나기 전에 후행단계를 닫을 수 없다
    blocker = db.execute(text("""
        SELECT step_no, step FROM ews_action
        WHERE alert_id = :aid AND step_no < :no AND status != 'DONE'
        ORDER BY step_no LIMIT 1
    """), {"aid": row[3], "no": row[4]}).fetchone()
    if blocker:
        raise HTTPException(422, f"선행 단계 미완료: {blocker[0]}단계 '{blocker[1]}' 을 먼저 완료해야 합니다")

    db.execute(text("""
        UPDATE ews_action SET status = 'DONE', action_taken = :taken, completed_at = :at
        WHERE action_id = :id
    """), {"taken": taken, "at": AS_OF_STR, "id": action_id})
    record_audit(db, action_type="EWS_ACTION_DONE", target_entity="ews_action",
                 target_id=action_id, before={"status": row[0]},
                 after={"status": "DONE", "step": row[1], "action_taken": taken[:80]},
                 user_id=payload.get("user", "김여신"), user_dept="여신관리부")
    db.commit()
    return {"action_id": action_id, "status": "DONE", "completed_at": AS_OF_STR}
