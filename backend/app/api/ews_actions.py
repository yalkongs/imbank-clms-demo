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
from ..core.auth import get_current_user, User

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
def complete_action(action_id: str, payload: dict = Body(...), db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
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
                 user_id=current_user.name, user_dept=current_user.dept)
    db.commit()
    return {"action_id": action_id, "status": "DONE", "completed_at": AS_OF_STR}


@router.post("/run-escalation")
def run_escalation(db: Session = Depends(get_db)):
    """기한초과 미결 조치를 실제로 상향보고 처리한다 (멱등).

    조회 시점 계산이 아니라 실행 기록을 남긴다: escalated=1 마킹 +
    ews_escalation 레코드 + 부서장 수신 notification_log.
    앱 기동 시(lifespan)에도 1회 실행되어 스케줄러를 근사한다.
    """
    import uuid as _uuid
    overdue = db.execute(text("""
        SELECT a.action_id, a.step, a.owner, a.due_date, a.customer_id, c.customer_name
        FROM ews_action a
        LEFT JOIN customer c ON c.customer_id = a.customer_id
        WHERE a.status != 'DONE' AND a.due_date < :asof AND a.escalated = 0
    """), {"asof": AS_OF_STR}).fetchall()
    created = []
    for action_id, step, owner, due, cust_id, cust_name in overdue:
        esc_id = f"ESC_{_uuid.uuid4().hex[:10].upper()}"
        db.execute(text("""
            INSERT INTO ews_escalation (escalation_id, action_id, escalated_to, reason)
            VALUES (:e, :a, 'DEPT_HEAD', :r)
        """), {"e": esc_id, "a": action_id,
               "r": f"기한({due}) 초과 - {cust_name or cust_id} '{step}' 미조치"})
        db.execute(text("""
            INSERT INTO notification_log
                (notification_id, channel, recipient, subject, ref_type, ref_id, status)
            VALUES (:n, 'PORTAL', '박부장(부서장)', :subj, 'EWS_ESCALATION', :ref, 'SENT')
        """), {"n": f"NTF_{_uuid.uuid4().hex[:10].upper()}",
               "subj": f"[상향보고] {cust_name or cust_id} EWS 조치 기한초과: {step}",
               "ref": esc_id})
        db.execute(text("UPDATE ews_action SET escalated = 1 WHERE action_id = :a"),
                   {"a": action_id})
        created.append(esc_id)
    db.commit()
    return {"escalated": len(created), "note": "멱등 - 이미 상향보고된 건은 제외"}


@router.get("/escalations")
def list_escalations(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT e.escalation_id, e.reason, e.escalated_to, e.created_at, e.acknowledged,
               n.status AS notify_status
        FROM ews_escalation e
        LEFT JOIN notification_log n ON n.ref_id = e.escalation_id
        ORDER BY e.created_at DESC LIMIT 50
    """)).fetchall()
    return {"escalations": [
        {"escalation_id": r[0], "reason": r[1], "escalated_to": r[2],
         "created_at": r[3], "acknowledged": bool(r[4]), "notify_status": r[5]}
        for r in rows
    ]}
