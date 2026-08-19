"""
책무구조도 통제증거 체인 API (P5)
==================================
지배구조법 개정(2024.7 시행)으로 은행 임원에게 내부통제 **관리의무**가
부과됐고, 책무구조도는 2025.1 제출이 완료됐다. 실무 쟁점은 "관리의무를
수행했다는 **증거**"다 - 캄보디아 제재에서 금감원이 지적한 것은 "기준은
있었으나 지켜지지 않았다"였고, 배임 4.5년 미적발은 기록 공백의 결과였다.

이 모듈은 여신 관련 책무 항목에 CLMS 통제활동을 매핑하고, 각 책무의
수행 증거(감사기록·활동량)를 자동 집계해 임원별 점검 리포트를 만든다.
QW(감사추적 일원화)가 선행조건 - 감사기록이 없는 통제는 증거가 없다.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db

router = APIRouter(prefix="/api/accountability", tags=["Accountability Map"])

# 감사체계 일원화 시행 시점 - 이 이후 구간에서 증거 커버리지를 판정한다
AUDIT_REGIME_START = "2026-03-01"

# ── 여신 관련 책무 레지스터 ─────────────────────────────────────────
# 책무별로 CLMS 통제활동과 그 증거(audit_log action_type)를 매핑한다.
DUTIES = [
    {
        "duty_id": "D01",
        "title": "여신심사·승인 체계 관리",
        "owner": "이전무", "owner_role": "여신그룹 임원",
        "controls": [
            "서버측 전결권 검증 (금액 기준, 우회 차단)",
            "단계 전이 가드 (심사 없는 승인 422 차단)",
            "승인 시점 심사자료 SHA-256 봉인",
            "승인조건 카탈로그 11종 구조화",
        ],
        "audit_actions": ["LOAN_", "STAGE_", "EXCEPTION_", "SNAPSHOT"],
        "activity_sql": "SELECT COUNT(*) FROM approval_history WHERE decided_at >= :since",
        "activity_label": "결재 처리",
    },
    {
        "duty_id": "D02",
        "title": "자산건전성 분류·충당금 적정성 관리",
        "owner": "박부장", "owner_role": "리스크관리 부서장",
        "controls": [
            "DPD·PD·EWS 3기준 최불리 분류 (분할분류 포함)",
            "감독 §29 최저적립 vs IFRS9 ECL 이중 점검",
            "감독분류×Stage×EWS 3체계 대사",
        ],
        "audit_actions": ["CLASSIFICATION_", "ASSET_", "ECL_"],
        "activity_sql": "SELECT COUNT(*) FROM asset_classification WHERE base_date >= :since",
        "activity_label": "분류 산출",
    },
    {
        "duty_id": "D03",
        "title": "한도·편중리스크 관리",
        "owner": "박부장", "owner_role": "리스크관리 부서장",
        "controls": [
            "승인 연동 한도 예약·해제 (2단계 결재 이중예약 차단)",
            "은행법 §35 법정 3한도 점검 (난내·난외 CCF 합산)",
            "한도동결 실행은 부서장 이상 + 감사기록",
        ],
        "audit_actions": ["AUTOMATION_", "LIMIT_"],
        "activity_sql": "SELECT COUNT(*) FROM limit_reservation WHERE reserved_at >= :since",
        "activity_label": "한도 예약",
    },
    {
        "duty_id": "D04",
        "title": "약정(코베넌트) 이행 관리",
        "owner": "김여신", "owner_role": "여신심사 팀장",
        "controls": [
            "점검 주기 도래 관리 (기한 도래 목록·SLA)",
            "위반 시 심각도 판정·EWS 연동",
            "웨이버는 부서장 이상 + 감사기록 필수 (실패 시 롤백)",
        ],
        "audit_actions": ["COVENANT_"],
        "activity_sql": "SELECT COUNT(*) FROM covenant_check WHERE check_date >= :since",
        "activity_label": "약정 점검",
    },
    {
        "duty_id": "D05",
        "title": "연체·부실채권 회수 관리",
        "owner": "박부장", "owner_role": "여신관리 부서장",
        "controls": [
            "DPD 버킷·Roll Rate 상시 모니터링",
            "추심활동 기록 (담당자 실명)",
            "DPD 90+ 워크아웃 자동 이관 + 감사기록",
        ],
        "audit_actions": ["COLLECTION_", "NPL_"],
        "activity_sql": "SELECT COUNT(*) FROM collection_activity WHERE activity_date >= :since",
        "activity_label": "추심 활동",
    },
    {
        "duty_id": "D06",
        "title": "금리인하요구권 처리 관리",
        "owner": "김여신", "owner_role": "여신심사 팀장",
        "controls": [
            "접수→심사→결정→통지 상태기계 (10영업일 SLA)",
            "보완요청 시 SLA 정지·재개 기록",
            "전 단계 감사기록",
        ],
        "audit_actions": ["RATE_"],
        "activity_sql": "SELECT COUNT(*) FROM rate_reduction_request WHERE request_date >= :since",
        "activity_label": "요구권 접수",
    },
    {
        "duty_id": "D07",
        "title": "조기경보·자동조치 운영",
        "owner": "박부장", "owner_role": "리스크관리 부서장",
        "controls": [
            "5채널 조기경보 상시 산출",
            "조치의무 기한초과 자동 상향보고 (멱등)",
            "자동화 트리거 생성·실행 감사기록",
        ],
        "audit_actions": ["EWS_"],
        "activity_sql": "SELECT COUNT(*) FROM ews_action WHERE created_at >= :since",
        "activity_label": "EWS 조치",
    },
    {
        "duty_id": "D08",
        "title": "모형 리스크 관리 (MRM)",
        "owner": "이전무", "owner_role": "리스크관리 임원",
        "controls": [
            "PD 백테스트 (이항검정)·PSI·빈티지 상시 산출",
            "Override Type I/II 모니터링",
            "Champion-Challenger 운영",
        ],
        "audit_actions": ["MODEL_"],
        "activity_sql": "SELECT COUNT(*) FROM model_performance_log WHERE monitoring_date >= :since",
        "activity_label": "성능 평가",
    },
]


def _duty_evidence(db: Session, duty: dict) -> dict:
    """책무 1건의 증거 집계 - 감사기록 수·최근 활동·원천 활동량"""
    placeholders = ",".join(f"'{a}'" for a in duty["audit_actions"])
    like_conds = " OR ".join(f"action_type LIKE '{a}%'" for a in duty["audit_actions"])
    audit_row = db.execute(text(f"""
        SELECT COUNT(*), MAX(log_timestamp) FROM audit_log
        WHERE action_type IN ({placeholders}) OR {like_conds}
    """)).fetchone()

    try:
        activity = db.execute(
            text(duty["activity_sql"]), {"since": AUDIT_REGIME_START}).scalar() or 0
    except Exception:
        activity = 0

    audit_count = audit_row[0] or 0
    # 증거 상태: 감사기록이 있으면 EVIDENCED, 원천 활동은 있는데 감사기록이
    # 없으면 GAP(통제는 돌지만 증거가 안 남는 상태), 둘 다 없으면 IDLE
    if audit_count > 0:
        status = "EVIDENCED"
    elif activity > 0:
        status = "GAP"
    else:
        status = "IDLE"
    return {
        "audit_count": audit_count,
        "last_audit": str(audit_row[1]) if audit_row[1] else None,
        "activity_count": int(activity),
        "activity_label": duty["activity_label"],
        "status": status,
    }


@router.get("/register")
def get_register(db: Session = Depends(get_db)):
    """책무 레지스터 + 통제활동 매핑 + 증거 집계"""
    duties = []
    for d in DUTIES:
        ev = _duty_evidence(db, d)
        duties.append({
            "duty_id": d["duty_id"], "title": d["title"],
            "owner": d["owner"], "owner_role": d["owner_role"],
            "controls": d["controls"],
            "evidence": ev,
        })
    counts = {"EVIDENCED": 0, "GAP": 0, "IDLE": 0}
    for x in duties:
        counts[x["evidence"]["status"]] += 1
    return {
        "regulatory_context": {
            "law": "지배구조법 개정 2024.7.3 시행 · 책무구조도 2025.1 제출 완료",
            "risk": "'1호 제재' 대기 국면 - 관리의무 수행 증거가 실무 쟁점",
            "im_context": "시중은행 전환 인가 부대조건(내부통제 보고) · 금감원 2026 고강도 점검",
            "audit_regime_start": AUDIT_REGIME_START,
        },
        "duties": duties,
        "summary": {
            "total": len(duties),
            **counts,
            "evidence_rate": round(counts["EVIDENCED"] / len(duties) * 100, 0),
        },
    }


@router.get("/evidence/{duty_id}")
def get_evidence_log(duty_id: str, db: Session = Depends(get_db)):
    """책무별 증거 원장 - 매핑된 감사기록 최근 20건"""
    duty = next((d for d in DUTIES if d["duty_id"] == duty_id), None)
    if not duty:
        raise HTTPException(404, "책무 없음")
    placeholders = ",".join(f"'{a}'" for a in duty["audit_actions"])
    like_conds = " OR ".join(f"action_type LIKE '{a}%'" for a in duty["audit_actions"])
    rows = db.execute(text(f"""
        SELECT log_timestamp, user_id, user_dept, action_type,
               target_entity, target_id, after_value
        FROM audit_log
        WHERE action_type IN ({placeholders}) OR {like_conds}
        ORDER BY log_timestamp DESC LIMIT 20
    """)).fetchall()
    return {
        "duty_id": duty_id, "title": duty["title"],
        "entries": [
            {"timestamp": str(r[0]), "user": r[1], "dept": r[2],
             "action": r[3], "entity": r[4], "target": r[5],
             "detail": r[6]}
            for r in rows
        ],
    }


@router.get("/report")
def get_management_report(db: Session = Depends(get_db)):
    """임원·부서장별 관리의무 점검 리포트 요약"""
    by_owner: dict = {}
    for d in DUTIES:
        ev = _duty_evidence(db, d)
        o = by_owner.setdefault(d["owner"], {
            "owner": d["owner"], "owner_role": d["owner_role"],
            "duties": 0, "evidenced": 0, "gaps": [], "audit_total": 0,
        })
        o["duties"] += 1
        o["audit_total"] += ev["audit_count"]
        if ev["status"] == "EVIDENCED":
            o["evidenced"] += 1
        elif ev["status"] == "GAP":
            o["gaps"].append(d["title"])
    report = []
    for o in by_owner.values():
        rate = round(o["evidenced"] / o["duties"] * 100, 0) if o["duties"] else 0
        report.append({
            **o,
            "evidence_rate": rate,
            "conclusion": (
                "관리의무 수행 증거 충족" if rate >= 100 else
                f"증거 공백 {len(o['gaps'])}건 - 해당 통제의 감사기록 연결 필요"
            ),
        })
    report.sort(key=lambda x: x["owner_role"])
    return {"report": report, "note": "증거 = audit_log 실측 집계 (수기 보고 아님)"}
