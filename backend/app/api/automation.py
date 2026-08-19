"""
자동화 브릿지 API (EWS → Workout 연결)
==========================================
Module 7: 트리거 기반 자동 액션 생성 및 실행

트리거 유형:
  EWS_CRITICAL  → RM 알림 + Workout 예비 케이스 생성
  COVENANT_EOD  → 기한이익상실 예고 + 자산건전성 재분류
  DPD_90        → Workout 자동 이관 + ECL Stage 3 재산출
  CUSTOM        → 수동 트리거

부실전환 확률 모델:
  P(default_90d) = σ(β0 + β1×EWS + β2×DPD + β3×PD + β4×DSCR)
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import date, datetime
import uuid
import math

from ..core.database import get_db
from ..core.auth import get_current_user, User
from ..core.audit import record_audit

router = APIRouter(prefix="/api/automation", tags=["Automation Bridge"])

# ─── 부실전환 확률 모델 계수 (로지스틱 회귀) ──────────────────────────
# 실증 연구 기반 간소화 계수
_BETA = {
    "intercept": -3.5,
    "ews_score": -0.04,   # EWS 점수 낮을수록 부실 위험↑
    "dpd":        0.05,   # DPD 클수록 위험↑
    "pd":        12.0,    # PD 높을수록 위험↑ (0~1 스케일)
    "dscr":      -0.8,    # DSCR 낮을수록 위험↑
}


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def predict_default_prob(ews_score: float = 65, dpd: int = 0,
                          pd: float = 0.02, dscr: float = 1.5) -> float:
    """
    90일 내 부실전환 확률 로지스틱 모델
    Returns: 0~1 확률값
    """
    z = (_BETA["intercept"]
         + _BETA["ews_score"] * ews_score
         + _BETA["dpd"]       * dpd
         + _BETA["pd"]        * pd
         + _BETA["dscr"]      * min(dscr, 5.0))
    return round(_sigmoid(z), 4)


# ─── 트리거 메타 ─────────────────────────────────────────────────────
TRIGGER_META = {
    "EWS_CRITICAL": {
        "label": "EWS 위험 신호",
        "actions": ["NOTIFY_RM", "CREATE_WORKOUT"],
        "priority": "HIGH",
    },
    "COVENANT_EOD": {
        "label": "약정 기한이익상실",
        "actions": ["NOTIFY_RM", "RECLASSIFY", "FREEZE_LIMIT"],
        "priority": "CRITICAL",
    },
    "DPD_90": {
        "label": "DPD 90일 초과",
        "actions": ["CREATE_WORKOUT", "RECLASSIFY", "ECL_RECALC"],
        "priority": "HIGH",
    },
    "CUSTOM": {
        "label": "수동 트리거",
        "actions": ["NOTIFY_RM"],
        "priority": "NORMAL",
    },
}

ACTION_LABELS = {
    "NOTIFY_RM":     "RM 알림 발송",
    "CREATE_WORKOUT": "Workout 케이스 생성",
    "RECLASSIFY":    "자산건전성 재분류",
    "ECL_RECALC":    "ECL Stage 3 재산출",
    "FREEZE_LIMIT":  "한도 동결",
}


@router.get("/dashboard")
def get_automation_dashboard(
    db: Session = Depends(get_db)
):
    """
    자동화 액션 현황 대시보드
    - 트리거별 건수, 처리 현황, 미처리 위급 알림
    """
    # 트리거별 요약
    by_trigger = db.execute(
        text("""
            SELECT trigger_type, action_status, COUNT(*) AS cnt
            FROM automation_action
            GROUP BY trigger_type, action_status
        """)
    ).fetchall()

    trigger_summary = {}
    for r in by_trigger:
        tt = r[0]; st = r[1]; cnt = r[2]
        if tt not in trigger_summary:
            trigger_summary[tt] = {
                "trigger_type": tt,
                "label": TRIGGER_META.get(tt, {}).get("label", tt),
                "PENDING": 0, "EXECUTED": 0, "SKIPPED": 0, "FAILED": 0,
            }
        trigger_summary[tt][st] = trigger_summary[tt].get(st, 0) + cnt

    # 우선순위별 PENDING
    pending = db.execute(
        text("""
            SELECT priority, COUNT(*) AS cnt
            FROM automation_action
            WHERE action_status = 'PENDING'
            GROUP BY priority
            ORDER BY CASE priority
                WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2
                WHEN 'NORMAL' THEN 3 ELSE 4 END
        """)
    ).fetchall()

    # 최근 실행 이력 (10건)
    recent = db.execute(
        text("""
            SELECT
                a.action_id, a.trigger_type, a.action_type,
                a.action_status, a.priority,
                a.customer_id, c.customer_name,
                a.default_probability,
                a.result_summary, a.created_at, a.executed_at
            FROM automation_action a
            LEFT JOIN customer c ON a.customer_id = c.customer_id
            ORDER BY a.created_at DESC
            LIMIT 10
        """)
    ).fetchall()

    recent_list = []
    for r in recent:
        recent_list.append({
            "action_id":     r[0],
            "trigger_type":  r[1],
            "trigger_label": TRIGGER_META.get(r[1], {}).get("label", r[1]),
            "action_type":   r[2],
            "action_label":  ACTION_LABELS.get(r[2], r[2]),
            "action_status": r[3],
            "priority":      r[4],
            "customer_id":   r[5],
            "company_name":  r[6],
            "default_prob":  round((r[7] or 0) * 100, 1),
            "result_summary": r[8],
            "created_at":    str(r[9]),
            "executed_at":   str(r[10]) if r[10] else None,
        })

    total_pending  = sum(r[1] for r in pending)
    critical_count = next((r[1] for r in pending if r[0] == "CRITICAL"), 0)
    high_count     = next((r[1] for r in pending if r[0] == "HIGH"), 0)

    return {
        "total_pending":   total_pending,
        "critical_pending": critical_count,
        "high_pending":    high_count,
        "by_trigger":      list(trigger_summary.values()),
        "pending_by_priority": [{"priority": r[0], "count": r[1]} for r in pending],
        "recent_actions":  recent_list,
    }


@router.get("/pending")
def get_pending_actions(
    priority: Optional[str] = Query(None),
    trigger_type: Optional[str] = Query(None),
    limit: int = Query(50),
    db: Session = Depends(get_db)
):
    """미처리(PENDING) 자동화 액션 목록"""
    where = "WHERE a.action_status = 'PENDING'"
    params: dict = {"lim": limit}
    if priority:
        where += " AND a.priority = :priority"
        params["priority"] = priority
    if trigger_type:
        where += " AND a.trigger_type = :tt"
        params["tt"] = trigger_type

    rows = db.execute(
        text(f"""
            SELECT
                a.action_id, a.trigger_type, a.action_type,
                a.priority, a.customer_id, c.customer_name,
                a.facility_id, a.default_probability,
                a.trigger_source_id, a.created_at
            FROM automation_action a
            LEFT JOIN customer c ON a.customer_id = c.customer_id
            {where}
            ORDER BY
                CASE a.priority
                    WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2
                    WHEN 'NORMAL' THEN 3 ELSE 4 END,
                a.created_at DESC
            LIMIT :lim
        """),
        params
    ).fetchall()

    return {
        "count": len(rows),
        "items": [
            {
                "action_id":     r[0],
                "trigger_type":  r[1],
                "trigger_label": TRIGGER_META.get(r[1], {}).get("label", r[1]),
                "action_type":   r[2],
                "action_label":  ACTION_LABELS.get(r[2], r[2]),
                "priority":      r[3],
                "customer_id":   r[4],
                "company_name":  r[5],
                "facility_id":   r[6],
                "default_prob":  round((r[7] or 0) * 100, 1),
                "trigger_source_id": r[8],
                "created_at":    str(r[9]),
            }
            for r in rows
        ],
    }


@router.post("/execute/{action_id}")
def execute_action(
    action_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    자동화 액션 실행
    - 액션 유형별 실제 처리 수행 후 status EXECUTED로 변경
    - 시설 상태를 바꾸는 액션(한도동결·재분류)은 부서장 이상 전결권 필요
    """
    action = db.execute(
        text("""
            SELECT action_id, trigger_type, action_type,
                   customer_id, facility_id, action_status
            FROM automation_action WHERE action_id = :aid
        """),
        {"aid": action_id}
    ).fetchone()

    if not action:
        raise HTTPException(status_code=404, detail="액션 없음")
    if action[5] != "PENDING":
        raise HTTPException(status_code=400, detail=f"이미 처리됨: {action[5]}")

    cid = action[3]; fid = action[4]; atype = action[2]

    if atype in ("FREEZE_LIMIT", "RECLASSIFY") and \
            current_user.approval_level not in ("DEPT_HEAD", "EXECUTIVE", "COMMITTEE"):
        raise HTTPException(403, f"{atype} 실행은 부서장 이상 전결권자만 가능합니다")
    result_summary = None

    # ── 액션 유형별 처리 ─────────────────────────────────────────────
    if atype == "CREATE_WORKOUT":
        # Workout 케이스 생성 (이미 없는 경우)
        existing = db.execute(
            text("SELECT case_id FROM workout_case WHERE customer_id=:cid AND case_status='OPEN'"),
            {"cid": cid}
        ).fetchone()
        if not existing:
            case_id = str(uuid.uuid4())
            ead_row = db.execute(
                text("SELECT COALESCE(SUM(outstanding_amount),0) FROM facility WHERE customer_id=:cid AND status='ACTIVE'"),
                {"cid": cid}
            ).scalar()
            ead = float(ead_row or 0)
            db.execute(
                text("""
                    INSERT INTO workout_case
                        (case_id, customer_id, facility_id, total_exposure,
                         provision_amount, case_status, strategy,
                         expected_recovery_rate, notes)
                    VALUES
                        (:cid2, :cust, :fid, :exp,
                         :prov, 'OPEN', 'TBD', 0.40,
                         '자동화 트리거에 의한 Workout 케이스 생성')
                """),
                {"cid2": case_id, "cust": cid, "fid": fid, "exp": ead, "prov": ead * 0.5}
            )
            result_summary = f"Workout 케이스 생성: {case_id}"
        else:
            result_summary = f"기존 Workout 케이스 있음 (스킵): {existing[0]}"

    elif atype == "NOTIFY_RM":
        # RM 알림 - 실제 시스템에서는 메시지 발송; 여기선 로그만
        result_summary = f"RM 알림 생성됨 (고객: {cid})"

    elif atype == "RECLASSIFY":
        # 자산건전성 재분류 트리거
        if fid:
            fac = db.execute(
                text("SELECT outstanding_amount, dpd FROM facility WHERE facility_id=:fid"),
                {"fid": fid}
            ).fetchone()
            if fac:
                from ..services.calculations import classify_asset, PROVISION_RATES
                pd_row = db.execute(
                    text("""
                        SELECT rp.ttc_pd FROM risk_parameter rp
                        JOIN loan_application la ON rp.application_id = la.application_id
                        JOIN facility f ON la.application_id = f.application_id
                        WHERE f.facility_id = :fid
                        ORDER BY rp.calc_date DESC LIMIT 1
                    """),
                    {"fid": fid}
                ).fetchone()
                pd_val = float(pd_row[0]) if pd_row else 0.15
                result = classify_asset(fac[1] or 0, pd_val, None)
                cls = result["classification"]
                db.execute(
                    text("UPDATE facility SET classification=:cls WHERE facility_id=:fid"),
                    {"cls": cls, "fid": fid}
                )
                result_summary = f"자산건전성 재분류 완료: {cls}"

    elif atype == "ECL_RECALC":
        # ECL Stage 3 재산출 (간소화: 마킹만)
        result_summary = f"ECL 재산출 요청됨 (여신: {fid})"

    elif atype == "FREEZE_LIMIT":
        # 한도 동결
        if fid:
            db.execute(
                text("UPDATE facility SET status='FROZEN' WHERE facility_id=:fid AND status='ACTIVE'"),
                {"fid": fid}
            )
            result_summary = f"한도 동결 완료 (여신: {fid})"

    # 상태 업데이트
    db.execute(
        text("""
            UPDATE automation_action
            SET action_status='EXECUTED',
                executed_at=CURRENT_TIMESTAMP,
                result_summary=:summary
            WHERE action_id=:aid
        """),
        {"summary": result_summary, "aid": action_id}
    )
    # 시설 상태를 바꾸는 액션은 감사기록 실패 시 실행 자체를 롤백한다
    record_audit(db, "AUTOMATION_EXECUTE", "automation_action", action_id,
                 before={"action_status": "PENDING"},
                 after={"action_status": "EXECUTED", "action_type": atype,
                        "customer_id": cid, "facility_id": fid,
                        "result_summary": result_summary},
                 user_id=current_user.name, user_dept=current_user.dept,
                 critical=atype in ("FREEZE_LIMIT", "RECLASSIFY", "CREATE_WORKOUT"))
    db.commit()

    return {
        "action_id":      action_id,
        "action_type":    atype,
        "action_status":  "EXECUTED",
        "result_summary": result_summary,
    }


@router.post("/trigger/scan")
def scan_and_create_triggers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    트리거 스캔 - 현재 DB 상태를 기반으로 자동화 액션 자동 생성
    1. EWS CRITICAL 고객 스캔
    2. 약정 EVENT_OF_DEFAULT 스캔
    3. DPD 90일+ 여신 스캔
    """
    created = []

    # ── 1. EWS CRITICAL (composite_score < 35) ──────────────────────
    ews_rows = db.execute(
        text("""
            SELECT ecs.customer_id, ecs.composite_score,
                   c.customer_name
            FROM ews_composite_score ecs
            JOIN customer c ON ecs.customer_id = c.customer_id
            JOIN (
                SELECT customer_id, MAX(score_date) AS latest
                FROM ews_composite_score GROUP BY customer_id
            ) mx ON ecs.customer_id = mx.customer_id AND ecs.score_date = mx.latest
            WHERE ecs.composite_score < 35
              AND ecs.customer_id NOT IN (
                  SELECT customer_id FROM automation_action
                  WHERE trigger_type = 'EWS_CRITICAL'
                    AND action_status = 'PENDING'
              )
            LIMIT 50
        """)
    ).fetchall()

    for r in ews_rows:
        cid   = r[0]; ews_score = float(r[1] or 50)
        dp    = predict_default_prob(ews_score=ews_score, dpd=0, pd=0.15, dscr=1.2)
        for atype in TRIGGER_META["EWS_CRITICAL"]["actions"]:
            aid = str(uuid.uuid4())
            db.execute(
                text("""
                    INSERT INTO automation_action
                        (action_id, trigger_type, customer_id,
                         action_type, priority, default_probability)
                    VALUES (:aid, 'EWS_CRITICAL', :cid,
                            :atype, 'HIGH', :dp)
                """),
                {"aid": aid, "cid": cid, "atype": atype, "dp": dp}
            )
            created.append({"trigger": "EWS_CRITICAL", "customer": cid, "action": atype})

    # ── 2. 약정 EVENT_OF_DEFAULT ───────────────────────────────────
    eod_rows = db.execute(
        text("""
            SELECT DISTINCT cc.covenant_id, cv.facility_id,
                   f.customer_id, c.customer_name
            FROM covenant_check cc
            JOIN covenant cv ON cc.covenant_id = cv.covenant_id
            JOIN facility f ON cv.facility_id = f.facility_id
            JOIN customer c ON f.customer_id = c.customer_id
            WHERE cc.breach_severity = 'EVENT_OF_DEFAULT'
              AND cc.result = 'BREACH'
              AND f.customer_id NOT IN (
                  SELECT customer_id FROM automation_action
                  WHERE trigger_type = 'COVENANT_EOD'
                    AND action_status = 'PENDING'
              )
            LIMIT 30
        """)
    ).fetchall()

    for r in eod_rows:
        cid = r[2]; fid = r[1]
        dp  = predict_default_prob(ews_score=45, dpd=0, pd=0.20, dscr=0.8)
        for atype in TRIGGER_META["COVENANT_EOD"]["actions"]:
            aid = str(uuid.uuid4())
            db.execute(
                text("""
                    INSERT INTO automation_action
                        (action_id, trigger_type, trigger_source_id,
                         customer_id, facility_id,
                         action_type, priority, default_probability)
                    VALUES (:aid, 'COVENANT_EOD', :src,
                            :cid, :fid,
                            :atype, 'CRITICAL', :dp)
                """),
                {"aid": aid, "src": r[0], "cid": cid, "fid": fid, "atype": atype, "dp": dp}
            )
            created.append({"trigger": "COVENANT_EOD", "customer": cid, "action": atype})

    # ── 3. DPD 90일+ ──────────────────────────────────────────────
    dpd_rows = db.execute(
        text("""
            SELECT DISTINCT d.facility_id, d.customer_id,
                   d.dpd, c.customer_name
            FROM delinquency_record d
            JOIN customer c ON d.customer_id = c.customer_id
            WHERE d.dpd >= 90 AND d.status = 'OPEN'
              AND d.customer_id NOT IN (
                  SELECT customer_id FROM automation_action
                  WHERE trigger_type = 'DPD_90'
                    AND action_status = 'PENDING'
              )
            LIMIT 30
        """)
    ).fetchall()

    for r in dpd_rows:
        fid = r[0]; cid = r[1]; dpd = r[2]
        dp  = predict_default_prob(ews_score=40, dpd=dpd, pd=0.25, dscr=0.7)
        for atype in TRIGGER_META["DPD_90"]["actions"]:
            aid = str(uuid.uuid4())
            db.execute(
                text("""
                    INSERT INTO automation_action
                        (action_id, trigger_type,
                         customer_id, facility_id,
                         action_type, priority, default_probability)
                    VALUES (:aid, 'DPD_90',
                            :cid, :fid,
                            :atype, 'HIGH', :dp)
                """),
                {"aid": aid, "cid": cid, "fid": fid, "atype": atype, "dp": dp}
            )
            created.append({"trigger": "DPD_90", "customer": cid, "action": atype})

    record_audit(db, "AUTOMATION_SCAN", "automation_action", "BATCH",
                 after={"total_created": len(created)},
                 user_id=current_user.name, user_dept=current_user.dept)
    db.commit()

    return {
        "message":        f"트리거 스캔 완료: {len(created)}건 액션 생성",
        "total_created":  len(created),
        "ews_critical":   len([c for c in created if c["trigger"] == "EWS_CRITICAL"]),
        "covenant_eod":   len([c for c in created if c["trigger"] == "COVENANT_EOD"]),
        "dpd_90":         len([c for c in created if c["trigger"] == "DPD_90"]),
    }


@router.get("/default-probability/{customer_id}")
def get_default_probability(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """
    고객별 부실전환 확률 산출
    - EWS점수 + DPD + PD + DSCR 로지스틱 모델
    """
    # EWS 점수
    ews_row = db.execute(
        text("""
            SELECT composite_score FROM ews_composite_score
            WHERE customer_id=:cid ORDER BY score_date DESC LIMIT 1
        """),
        {"cid": customer_id}
    ).fetchone()
    ews_score = float(ews_row[0]) if ews_row else 65.0

    # 최대 DPD
    dpd_row = db.execute(
        text("SELECT COALESCE(MAX(dpd), 0) FROM facility WHERE customer_id=:cid"),
        {"cid": customer_id}
    ).scalar()
    dpd = int(dpd_row or 0)

    # PD
    pd_row = db.execute(
        text("""
            SELECT rp.ttc_pd FROM risk_parameter rp
            JOIN loan_application la ON rp.application_id = la.application_id
            WHERE la.customer_id=:cid ORDER BY rp.calc_date DESC LIMIT 1
        """),
        {"cid": customer_id}
    ).fetchone()
    pd_val = float(pd_row[0]) if pd_row else 0.03

    # DSCR
    dscr_row = db.execute(
        text("""
            SELECT fr.dscr FROM financial_ratio fr
            WHERE fr.customer_id=:cid ORDER BY fr.fiscal_year DESC LIMIT 1
        """),
        {"cid": customer_id}
    ).fetchone()
    dscr = float(dscr_row[0]) if dscr_row else 1.5

    prob = predict_default_prob(ews_score, dpd, pd_val, dscr)

    # 위험 등급
    if prob >= 0.60:
        risk_grade = "CRITICAL"
    elif prob >= 0.30:
        risk_grade = "HIGH"
    elif prob >= 0.10:
        risk_grade = "MODERATE"
    else:
        risk_grade = "LOW"

    return {
        "customer_id":       customer_id,
        "default_probability": prob,
        "default_prob_pct":  round(prob * 100, 2),
        "risk_grade":        risk_grade,
        "inputs": {
            "ews_score":     round(ews_score, 1),
            "dpd":           dpd,
            "pd_pct":        round(pd_val * 100, 3),
            "dscr":          round(dscr, 2),
        },
        "recommendation": (
            "즉시 Workout 이관 검토" if prob >= 0.60 else
            "집중 모니터링 및 RM 접촉" if prob >= 0.30 else
            "정기 점검 강화" if prob >= 0.10 else
            "정상 모니터링"
        ),
    }


@router.get("/statistics")
def get_automation_statistics(
    days: int = Query(30, description="최근 N일"),
    db: Session = Depends(get_db)
):
    """자동화 효과 통계 - 처리율, 평균 처리 시간, 트리거 추이"""
    from_date = f"date('now', '-{days} days')"

    totals = db.execute(
        text(f"""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN action_status='EXECUTED' THEN 1 ELSE 0 END) AS executed,
                SUM(CASE WHEN action_status='PENDING'  THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN action_status='FAILED'   THEN 1 ELSE 0 END) AS failed
            FROM automation_action
            WHERE created_at >= {from_date}
        """)
    ).fetchone()

    # 트리거별 처리율
    by_type = db.execute(
        text(f"""
            SELECT
                trigger_type,
                COUNT(*) AS total,
                SUM(CASE WHEN action_status='EXECUTED' THEN 1 ELSE 0 END) AS executed
            FROM automation_action
            WHERE created_at >= {from_date}
            GROUP BY trigger_type
        """)
    ).fetchall()

    # 평균 부실전환 확률 (PENDING 건)
    avg_prob = db.execute(
        text("""
            SELECT AVG(default_probability)
            FROM automation_action
            WHERE action_status='PENDING' AND default_probability IS NOT NULL
        """)
    ).scalar()

    total    = totals[0] or 0
    executed = totals[1] or 0

    return {
        "period_days":   days,
        "total":         total,
        "executed":      executed,
        "pending":       totals[2] or 0,
        "failed":        totals[3] or 0,
        "execution_rate": round(executed / total * 100, 1) if total > 0 else 0,
        "avg_default_prob_pct": round(float(avg_prob or 0) * 100, 2),
        "by_trigger_type": [
            {
                "trigger_type": r[0],
                "label": TRIGGER_META.get(r[0], {}).get("label", r[0]),
                "total": r[1],
                "executed": r[2],
                "execution_rate": round((r[2] or 0) / (r[1] or 1) * 100, 1),
            }
            for r in by_type
        ],
    }
