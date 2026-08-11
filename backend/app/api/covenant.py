"""
코베넌트 관리 API
==================
조건부 승인 구조화, 이행 모니터링, 위반 시 기한이익상실 트리거 연동
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import date, timedelta
from ..core.database import get_db
from ..core.config import AS_OF_DATE
from ..core.auth import get_current_user, User
from ..services.calculations import check_covenant_compliance

router = APIRouter(prefix="/api/covenants", tags=["Covenant Management"])

# 코베넌트 유형 메타데이터
COVENANT_TYPES = {
    "FINANCIAL": {
        "codes": {
            "FC01": {"name": "부채비율 제한",    "metric": "debt_ratio",      "unit": "%",  "op": "LE"},
            "FC02": {"name": "DSCR 유지",        "metric": "dscr",            "unit": "배", "op": "GE"},
            "FC03": {"name": "이자보상배율 유지", "metric": "ier",             "unit": "배", "op": "GE"},
            "FC04": {"name": "유동비율 유지",     "metric": "current_ratio",   "unit": "%",  "op": "GE"},
            "FC05": {"name": "순차입/EBITDA",    "metric": "net_debt_ebitda", "unit": "배", "op": "LE"},
        }
    },
    "BEHAVIORAL": {
        "codes": {
            "BC01": {"name": "추가 담보성 채무 제한", "metric": None},
            "BC02": {"name": "자산 처분 제한",        "metric": None},
            "BC03": {"name": "배당 제한",             "metric": None},
            "BC04": {"name": "추가 차입 한도 제한",   "metric": None},
        }
    },
    "INFORMATION": {
        "codes": {
            "IC01": {"name": "분기 재무제표 제출",   "metric": None},
            "IC02": {"name": "연간 감사보고서 제출", "metric": None},
            "IC03": {"name": "중요 사건 즉시 통보",  "metric": None},
        }
    }
}

# 점검 주기별 다음 점검일 계산
FREQUENCY_DAYS = {
    "MONTHLY":    30,
    "QUARTERLY":  91,
    "SEMI":       183,
    "ANNUAL":     365,
}


@router.get("/facility/{facility_id}")
def get_covenants_by_facility(
    facility_id: str,
    db: Session = Depends(get_db)
):
    """여신별 코베넌트 목록 + 최신 점검 결과"""
    facility = db.execute(text("""
        SELECT f.facility_id, f.customer_id, c.customer_name, f.outstanding_amount,
               f.final_rate, f.maturity_date
        FROM facility f
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.facility_id = :fid
    """), {"fid": facility_id}).fetchone()

    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    covenants = db.execute(text("""
        SELECT cv.covenant_id, cv.covenant_type, cv.covenant_code, cv.covenant_name,
               cv.metric, cv.operator, cv.threshold_value, cv.check_frequency,
               cv.next_check_date, cv.waiver_count, cv.status,
               -- 최신 점검 결과
               cc.check_date, cc.actual_value, cc.result, cc.breach_severity
        FROM covenant cv
        LEFT JOIN (
            SELECT covenant_id, check_date, actual_value, result, breach_severity,
                   ROW_NUMBER() OVER (PARTITION BY covenant_id ORDER BY check_date DESC) AS rn
            FROM covenant_check
        ) cc ON cv.covenant_id = cc.covenant_id AND cc.rn = 1
        WHERE cv.facility_id = :fid
        ORDER BY cv.covenant_type, cv.covenant_code
    """), {"fid": facility_id}).fetchall()

    covenant_list = []
    breach_count = 0
    due_count = 0
    today = AS_OF_DATE

    for cv in covenants:
        next_check = cv[8]
        is_due = next_check and date.fromisoformat(str(next_check)) <= today + timedelta(days=30)
        is_breach = cv[13] == 'BREACH'

        if is_breach:
            breach_count += 1
        if is_due:
            due_count += 1

        covenant_list.append({
            "covenant_id":     cv[0],
            "covenant_type":   cv[1],
            "covenant_code":   cv[2],
            "covenant_name":   cv[3],
            "metric":          cv[4],
            "operator":        cv[5],
            "threshold_value": cv[6],
            "check_frequency": cv[7],
            "next_check_date": str(cv[8]) if cv[8] else None,
            "waiver_count":    cv[9],
            "status":          cv[10],
            "last_check": {
                "check_date":     str(cv[11]) if cv[11] else None,
                "actual_value":   cv[12],
                "result":         cv[13],
                "breach_severity": cv[14],
            } if cv[11] else None,
            "is_due_check": is_due,
            "is_breach": is_breach,
        })

    return {
        "facility": {
            "facility_id":    facility[0],
            "customer_id":    facility[1],
            "customer_name":  facility[2],
            "outstanding":    facility[3],
            "rate":           facility[4],
            "maturity_date":  str(facility[5]) if facility[5] else None,
        },
        "covenants": covenant_list,
        "summary": {
            "total":    len(covenant_list),
            "breach":   breach_count,
            "due_soon": due_count,
            "active":   sum(1 for c in covenant_list if c['status'] == 'ACTIVE'),
        }
    }


@router.get("/due-check")
def get_due_covenants(
    days_ahead: int = Query(30, description="앞으로 N일 이내 점검 예정"),
    region: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """점검 예정 코베넌트 목록 (30일 이내)"""
    region_cond = " AND c.region = :region" if region else ""
    cutoff = AS_OF_DATE + timedelta(days=days_ahead)

    rows = db.execute(text(f"""
        SELECT cv.covenant_id, cv.facility_id, cv.covenant_type,
               cv.covenant_code, cv.covenant_name, cv.next_check_date,
               cv.threshold_value, cv.operator, cv.metric, cv.check_frequency,
               f.customer_id, c.customer_name,
               cv.status,
               -- 마지막 점검 결과
               cc.result AS last_result, cc.breach_severity
        FROM covenant cv
        JOIN facility f ON cv.facility_id = f.facility_id
        JOIN customer c ON f.customer_id = c.customer_id
        LEFT JOIN (
            SELECT covenant_id, result, breach_severity,
                   ROW_NUMBER() OVER (PARTITION BY covenant_id ORDER BY check_date DESC) AS rn
            FROM covenant_check
        ) cc ON cv.covenant_id = cc.covenant_id AND cc.rn = 1
        WHERE cv.status = 'ACTIVE'
        AND cv.next_check_date <= :cutoff
        {region_cond}
        ORDER BY cv.next_check_date ASC
    """), {"cutoff": str(cutoff), **({"region": region} if region else {})}).fetchall()

    items = []
    for r in rows:
        overdue = date.fromisoformat(str(r[5])) < AS_OF_DATE if r[5] else False
        items.append({
            "covenant_id":    r[0],
            "facility_id":    r[1],
            "covenant_type":  r[2],
            "covenant_code":  r[3],
            "covenant_name":  r[4],
            "next_check_date": str(r[5]) if r[5] else None,
            "threshold_value": r[6],
            "operator":       r[7],
            "metric":         r[8],
            "check_frequency": r[9],
            "customer_id":    r[10],
            "customer_name":  r[11],
            "status":         r[12],
            "last_result":    r[13],
            "last_severity":  r[14],
            "is_overdue":     overdue,
        })

    return {
        "due_covenants": items,
        "total": len(items),
        "overdue": sum(1 for i in items if i['is_overdue']),
        "cutoff_date": str(cutoff),
    }


@router.post("/check/{covenant_id}")
def run_covenant_check(
    covenant_id: str,
    actual_value: Optional[float] = None,
    checked_by: Optional[str] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    코베넌트 점검 실행
    - 재무 코베넌트: actual_value 입력 또는 financial_ratio 테이블에서 자동 조회
    - 결과에 따라 breach_severity 자동 판정
    - EVENT_OF_DEFAULT 시 EWS 경보 연동
    """
    cov = db.execute(text("""
        SELECT cv.covenant_id, cv.covenant_type, cv.covenant_code, cv.covenant_name,
               cv.metric, cv.operator, cv.threshold_value, cv.check_frequency,
               cv.facility_id, f.customer_id
        FROM covenant cv
        JOIN facility f ON cv.facility_id = f.facility_id
        WHERE cv.covenant_id = :cid
    """), {"cid": covenant_id}).fetchone()

    if not cov:
        raise HTTPException(status_code=404, detail="Covenant not found")

    customer_id = cov[9]
    today = AS_OF_DATE

    # 실측값 자동 조회 (재무 코베넌트 + 값 미입력)
    _actual = actual_value
    if _actual is None and cov[1] == 'FINANCIAL' and cov[4]:
        metric = cov[4]
        ratio_row = db.execute(text(f"""
            SELECT {metric} FROM financial_ratio
            WHERE customer_id = :cid
            ORDER BY fiscal_year DESC LIMIT 1
        """), {"cid": customer_id}).fetchone()
        if ratio_row:
            _actual = ratio_row[0]

    # 이행 판정
    covenant_dict = {
        "covenant_code":  cov[2],
        "operator":       cov[5],
        "threshold_value": cov[6],
    }
    ratio_dict = {cov[4]: _actual} if cov[4] and _actual is not None else {}
    check_result = check_covenant_compliance(covenant_dict, ratio_dict)

    result      = check_result['result']
    severity    = check_result.get('breach_severity')
    message     = check_result.get('message', '')

    # 점검 이력 저장
    check_id = f"CC_{covenant_id}_{today.strftime('%Y%m%d%H%M%S')}"
    freq_days = FREQUENCY_DAYS.get(cov[7], 183)
    next_check = today + timedelta(days=freq_days)

    db.execute(text("""
        INSERT INTO covenant_check
        (check_id, covenant_id, check_date, actual_value, threshold_value,
         result, breach_severity, action_taken, checked_by, next_check_date)
        VALUES (:cid, :covenant_id, :check_date, :actual, :threshold,
                :result, :severity, :action, :checker, :next_check)
    """), {
        "cid": check_id, "covenant_id": covenant_id,
        "check_date": str(today), "actual": _actual,
        "threshold": cov[6], "result": result,
        "severity": severity, "action": notes,
        "checker": checked_by or "SYSTEM",
        "next_check": str(next_check),
    })

    # covenant 상태 및 다음 점검일 업데이트
    new_status = 'BREACHED' if result == 'BREACH' else 'ACTIVE'
    db.execute(text("""
        UPDATE covenant
        SET status = :status, next_check_date = :next_check
        WHERE covenant_id = :cid
    """), {"status": new_status, "next_check": str(next_check), "cid": covenant_id})

    # EVENT_OF_DEFAULT → EWS 경보 생성
    if severity == 'EVENT_OF_DEFAULT':
        _trigger_ews_alert(customer_id, covenant_id, cov[3], db)

    db.commit()

    return {
        "check_id":      check_id,
        "covenant_id":   covenant_id,
        "covenant_name": cov[3],
        "check_date":    str(today),
        "actual_value":  _actual,
        "threshold":     cov[6],
        "result":        result,
        "breach_severity": severity,
        "message":       message,
        "next_check_date": str(next_check),
        "ews_triggered": severity == 'EVENT_OF_DEFAULT',
    }


@router.get("/breach-status")
def get_breach_dashboard(
    region: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """코베넌트 위반 현황 대시보드"""
    region_cond = " AND c.region = :region" if region else ""

    # 위반 현황
    breaches = db.execute(text(f"""
        SELECT cv.covenant_id, cv.covenant_type, cv.covenant_code, cv.covenant_name,
               cv.facility_id, f.customer_id, c.customer_name,
               cc.check_date, cc.actual_value, cc.threshold_value,
               cc.breach_severity
        FROM covenant cv
        JOIN facility f ON cv.facility_id = f.facility_id
        JOIN customer c ON f.customer_id = c.customer_id
        JOIN (
            SELECT covenant_id, check_date, actual_value, threshold_value, breach_severity,
                   ROW_NUMBER() OVER (PARTITION BY covenant_id ORDER BY check_date DESC) AS rn
            FROM covenant_check WHERE result = 'BREACH'
        ) cc ON cv.covenant_id = cc.covenant_id AND cc.rn = 1
        WHERE cv.status = 'BREACHED'
        {region_cond}
        ORDER BY
            CASE cc.breach_severity WHEN 'EVENT_OF_DEFAULT' THEN 1
                                    WHEN 'MAJOR' THEN 2 ELSE 3 END,
            cc.check_date DESC
    """), {"region": region} if region else {}).fetchall()

    breach_list = []
    severity_counts = {"EVENT_OF_DEFAULT": 0, "MAJOR": 0, "MINOR": 0}

    for b in breaches:
        sev = b[10]
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        breach_list.append({
            "covenant_id":    b[0],
            "covenant_type":  b[1],
            "covenant_code":  b[2],
            "covenant_name":  b[3],
            "facility_id":    b[4],
            "customer_id":    b[5],
            "customer_name":  b[6],
            "check_date":     str(b[7]) if b[7] else None,
            "actual_value":   b[8],
            "threshold_value": b[9],
            "breach_severity": sev,
        })

    # 이번 달 점검 통과율
    month_start = AS_OF_DATE.replace(day=1)
    monthly_stats = db.execute(text("""
        SELECT result, COUNT(*) FROM covenant_check
        WHERE check_date >= :start GROUP BY result
    """), {"start": str(month_start)}).fetchall()
    monthly_pass = {r[0]: r[1] for r in monthly_stats}

    return {
        "breach_summary": {
            "total_breach": len(breach_list),
            "event_of_default": severity_counts.get("EVENT_OF_DEFAULT", 0),
            "major": severity_counts.get("MAJOR", 0),
            "minor": severity_counts.get("MINOR", 0),
        },
        "breaches": breach_list,
        "monthly_check_stats": monthly_pass,
    }


@router.get("/history/{covenant_id}")
def get_covenant_history(
    covenant_id: str,
    db: Session = Depends(get_db)
):
    """코베넌트 이행 이력"""
    cov = db.execute(text("""
        SELECT cv.covenant_id, cv.covenant_name, cv.threshold_value, cv.operator,
               cv.check_frequency, cv.status, cv.waiver_count
        FROM covenant cv WHERE cv.covenant_id = :cid
    """), {"cid": covenant_id}).fetchone()

    if not cov:
        raise HTTPException(status_code=404, detail="Covenant not found")

    history = db.execute(text("""
        SELECT check_id, check_date, actual_value, threshold_value,
               result, breach_severity, action_taken, checked_by, next_check_date
        FROM covenant_check
        WHERE covenant_id = :cid
        ORDER BY check_date DESC
    """), {"cid": covenant_id}).fetchall()

    history_list = []
    for h in history:
        history_list.append({
            "check_id":       h[0],
            "check_date":     str(h[1]) if h[1] else None,
            "actual_value":   h[2],
            "threshold_value": h[3],
            "result":         h[4],
            "breach_severity": h[5],
            "action_taken":   h[6],
            "checked_by":     h[7],
            "next_check_date": str(h[8]) if h[8] else None,
        })

    pass_count   = sum(1 for h in history_list if h['result'] == 'PASS')
    breach_count = sum(1 for h in history_list if h['result'] == 'BREACH')

    return {
        "covenant": {
            "covenant_id":   cov[0],
            "covenant_name": cov[1],
            "threshold":     cov[2],
            "operator":      cov[3],
            "frequency":     cov[4],
            "status":        cov[5],
            "waiver_count":  cov[6],
        },
        "history": history_list,
        "stats": {
            "total_checks": len(history_list),
            "pass":   pass_count,
            "breach": breach_count,
            "pass_rate": round(pass_count / len(history_list) * 100, 1) if history_list else None,
        }
    }


@router.post("/waiver/{covenant_id}")
def apply_waiver(
    covenant_id: str,
    reason: str = Query(..., description="웨이버 사유"),
    approved_by: str = Query(None, description="(deprecated) 서버가 인증 사용자로 결정"),
    waiver_period_days: int = Query(90, description="유예 기간 (일)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    코베넌트 웨이버(일시 유예) 신청
    - 위반 상태의 코베넌트에 한해 적용, waiver_count 증가 (반복 웨이버 모니터링)
    - 승인자는 클라이언트 파라미터가 아니라 인증 사용자로 기록하며,
      예외 승인 성격이므로 부서장 이상의 전결권을 요구한다
    """
    if current_user.approval_level not in ("DEPT_HEAD", "EXECUTIVE", "COMMITTEE"):
        raise HTTPException(403, "코베넌트 웨이버는 부서장 이상 전결권자만 승인할 수 있습니다")
    approved_by = current_user.name
    cov = db.execute(text("""
        SELECT covenant_id, covenant_name, status, waiver_count
        FROM covenant WHERE covenant_id = :cid
    """), {"cid": covenant_id}).fetchone()

    if not cov:
        raise HTTPException(status_code=404, detail="Covenant not found")

    today = AS_OF_DATE
    new_next_check = today + timedelta(days=waiver_period_days)

    db.execute(text("""
        UPDATE covenant
        SET status = 'WAIVED',
            waiver_count = waiver_count + 1,
            next_check_date = :next_check
        WHERE covenant_id = :cid
    """), {"next_check": str(new_next_check), "cid": covenant_id})

    # 웨이버 이력을 covenant_check에 기록
    check_id = f"CC_{covenant_id}_WAIVER_{today.strftime('%Y%m%d')}"
    db.execute(text("""
        INSERT OR IGNORE INTO covenant_check
        (check_id, covenant_id, check_date, result, action_taken, checked_by, next_check_date)
        VALUES (:cid, :covenant_id, :date, 'WAIVED', :reason, :approver, :next)
    """), {
        "cid": check_id, "covenant_id": covenant_id,
        "date": str(today), "reason": f"웨이버 승인: {reason}",
        "approver": approved_by, "next": str(new_next_check),
    })

    db.commit()

    return {
        "covenant_id":   covenant_id,
        "covenant_name": cov[1],
        "waiver_applied": True,
        "waiver_count":  (cov[3] or 0) + 1,
        "waiver_reason": reason,
        "approved_by":   approved_by,
        "next_check_date": str(new_next_check),
        "warning": "반복 웨이버 주의 필요" if (cov[3] or 0) >= 2 else None,
    }


def _trigger_ews_alert(customer_id: str, covenant_id: str, covenant_name: str, db: Session):
    """코베넌트 기한이익상실 → EWS 경보 자동 생성"""
    alert_id = f"EWS_COV_{customer_id}_{AS_OF_DATE.strftime('%Y%m%d')}"
    db.execute(text("""
        INSERT OR IGNORE INTO ews_alert
        (alert_id, customer_id, alert_date, alert_type, alert_subtype,
         severity, description, status)
        VALUES (:aid, :cid, :adate, 'COVENANT_BREACH', 'EVENT_OF_DEFAULT',
                'CRITICAL', :desc, 'OPEN')
    """), {
        "aid": alert_id, "cid": customer_id,
        "adate": str(AS_OF_DATE),
        "desc": f"코베넌트 기한이익상실 사유 발생: {covenant_name} (ID: {covenant_id})"
    })
