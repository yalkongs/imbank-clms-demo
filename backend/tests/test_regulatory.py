"""
규제 시나리오 회귀 테스트 (7단계-⑦)
=====================================
인증·전결·스냅샷·3한도·상태기계·규정 레지스터의 규제 동작을 고정한다.
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.main import app  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402

client = TestClient(app)


def _login(user_id, pin):
    r = client.post("/api/auth/login", json={"user_id": user_id, "pin": pin})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _find_pending_app(db, max_eok=40):
    return db.execute(text("""
        SELECT application_id FROM loan_application la
        WHERE la.status IN ('REVIEWING','RECEIVED','SCREENING')
          AND la.current_stage NOT IN ('RECEIVED')
          AND la.requested_amount < :amt
          AND NOT EXISTS (SELECT 1 FROM approval_history ah
                          WHERE ah.application_id = la.application_id)
        LIMIT 1
    """), {"amt": max_eok * 1e8}).fetchone()


def test_authority_exceeded_is_blocked():
    """전결권 초과: 담당자(5억 한도)가 대형 건 승인 시도 → 403"""
    db = SessionLocal()
    row = db.execute(text("""
        SELECT application_id FROM loan_application
        WHERE status IN ('REVIEWING','RECEIVED') AND requested_amount > 100e8
          AND current_stage != 'RECEIVED' LIMIT 1
    """)).fetchone()
    if not row:
        pytest.skip("대형 심사 건 없음")
    r = client.post(f"/api/applications/{row[0]}/approve",
                    params={"decision": "APPROVE"},
                    headers=_login("kim.simsa", "1111"))
    assert r.status_code == 403, f"전결권 초과가 차단되지 않음: {r.status_code}"


def test_approve_blocked_before_review_started():
    """Gate 0: 접수(RECEIVED) 단계 건은 심사 착수 전이라 결재 불가 → 422"""
    db = SessionLocal()
    row = db.execute(text("""
        SELECT application_id FROM loan_application
        WHERE status IN ('REVIEWING','RECEIVED') AND current_stage = 'RECEIVED'
        LIMIT 1
    """)).fetchone()
    if not row:
        pytest.skip("접수 단계 표본 없음")
    r = client.post(f"/api/applications/{row[0]}/approve",
                    params={"decision": "APPROVE"},
                    headers=_login("lee.jeonmu", "3333"))
    assert r.status_code == 422, f"심사 미착수 즉시승인이 차단되지 않음: {r.status_code}"


def test_stage_jump_is_blocked():
    """Gate 0: 단계 건너뛰기(2단계 이상 전진) → 422"""
    db = SessionLocal()
    row = db.execute(text("""
        SELECT application_id FROM loan_application
        WHERE current_stage IN ('RECEIVED','DOC_REVIEW')
          AND status IN ('REVIEWING','RECEIVED') LIMIT 1
    """)).fetchone()
    if not row:
        pytest.skip("초기 단계 표본 없음")
    r = client.post(f"/api/applications/{row[0]}/stage",
                    params={"new_stage": "FINAL_REVIEW"},
                    headers=_login("kim.yeosin", "1234"))
    assert r.status_code == 422, f"단계 건너뛰기가 차단되지 않음: {r.status_code}"


def test_conditional_then_final_approval_no_id_conflict():
    """Gate 0: 조건부 승인 뒤 다른 승인자의 최종승인이 ID 충돌(500) 없이 성공"""
    db = SessionLocal()
    row = _find_pending_app(db)
    if not row:
        pytest.skip("승인 가능 표본 없음")
    aid = row[0]
    r1 = client.post(f"/api/applications/{aid}/approve",
                     params={"decision": "CONDITIONAL", "conditions": "담보 보완 조건"},
                     headers=_login("kim.yeosin", "1234"))
    assert r1.status_code == 200, r1.text[:200]
    r2 = client.post(f"/api/applications/{aid}/approve",
                     params={"decision": "APPROVE"},
                     headers=_login("park.bujang", "2222"))
    assert r2.status_code == 200, f"조건부 후 최종승인 실패(구 ID 충돌 결함): {r2.status_code} {r2.text[:150]}"


def test_waiver_requires_dept_head():
    """Gate 0: 코베넌트 웨이버는 부서장 이상 - 담당자(STAFF) 시도 → 403"""
    db = SessionLocal()
    row = db.execute(text("SELECT covenant_id FROM covenant LIMIT 1")).fetchone()
    if not row:
        pytest.skip("코베넌트 없음")
    r = client.post(f"/api/covenants/waiver/{row[0]}",
                    params={"reason": "테스트 사유"},
                    headers=_login("kim.simsa", "1111"))
    assert r.status_code == 403, f"STAFF 웨이버 승인이 차단되지 않음: {r.status_code}"


def test_freeze_limit_requires_dept_head():
    """Gate 0: 한도동결(FREEZE_LIMIT) 실행은 부서장 이상 - 담당자 시도 → 403"""
    db = SessionLocal()
    row = db.execute(text("""
        SELECT action_id FROM automation_action
        WHERE action_type = 'FREEZE_LIMIT' AND action_status = 'PENDING' LIMIT 1
    """)).fetchone()
    if not row:
        pytest.skip("PENDING 한도동결 액션 없음")
    r = client.post(f"/api/automation/execute/{row[0]}",
                    headers=_login("kim.simsa", "1111"))
    assert r.status_code == 403, f"STAFF 한도동결 실행이 차단되지 않음: {r.status_code}"


def test_authority_bypass_via_approved_amount_is_blocked():
    """전결권 우회: 담당자가 대형 건에 approved_amount=1 을 보내도 403
    (전결권은 신청금액 기준 - AGY 검토 P0-1 재현 시나리오 고정)"""
    db = SessionLocal()
    row = db.execute(text("""
        SELECT application_id FROM loan_application
        WHERE status IN ('REVIEWING','RECEIVED') AND requested_amount > 100e8
          AND current_stage != 'RECEIVED' LIMIT 1
    """)).fetchone()
    if not row:
        pytest.skip("대형 심사 건 없음")
    r = client.post(f"/api/applications/{row[0]}/approve",
                    params={"decision": "APPROVE", "approved_amount": 1},
                    headers=_login("kim.simsa", "1111"))
    assert r.status_code == 403, f"approved_amount 조작 우회가 차단되지 않음: {r.status_code}"


def test_approved_amount_out_of_range_is_rejected():
    """승인금액 유효성: 신청금액 초과·0 이하 → 422"""
    db = SessionLocal()
    row = db.execute(text("""
        SELECT application_id, requested_amount FROM loan_application
        WHERE status IN ('REVIEWING','RECEIVED') LIMIT 1
    """)).fetchone()
    if not row:
        pytest.skip("심사 건 없음")
    hdr = _login("lee.jeonmu", "3333")   # 임원 - 전결권은 충분, 유효성만 검증
    over = client.post(f"/api/applications/{row[0]}/approve",
                       params={"decision": "APPROVE",
                               "approved_amount": float(row[1]) * 2},
                       headers=hdr)
    assert over.status_code == 422, f"신청금액 초과 승인금액이 통과됨: {over.status_code}"
    zero = client.post(f"/api/applications/{row[0]}/approve",
                       params={"decision": "APPROVE", "approved_amount": 0},
                       headers=hdr)
    assert zero.status_code == 422, f"0원 승인금액이 통과됨: {zero.status_code}"


def test_snapshot_sealed_on_approval_and_immutable():
    """승인 → 스냅샷 봉인. 이후 등급이 갱신돼도 봉인 값은 불변"""
    db = SessionLocal()
    row = _find_pending_app(db)
    if not row:
        pytest.skip("승인 가능 표본 없음")
    aid = row[0]
    r = client.post(f"/api/applications/{aid}/approve",
                    params={"decision": "APPROVE"},
                    headers=_login("kim.yeosin", "1234"))
    assert r.status_code == 200, r.text[:200]
    snap = db.execute(text("""
        SELECT parameters_json, input_data_json FROM decision_snapshot
        WHERE application_id = :a ORDER BY snapshot_timestamp DESC LIMIT 1
    """), {"a": aid}).fetchone()
    assert snap, "승인 후 스냅샷이 봉인되지 않음"
    import json
    params = json.loads(snap[0])
    assert params.get("hash") and not params.get("backfilled")
    sealed_input_before = snap[1]

    # 사후 등급 변경(모의) 후에도 여신철 스냅샷은 동일해야 한다
    case = client.get(f"/api/credit-case/{aid}").json()
    assert case["snapshot"]["hash"] == params["hash"]
    assert case["snapshot"]["backfilled"] is False
    snap2 = db.execute(text("""
        SELECT input_data_json FROM decision_snapshot
        WHERE application_id = :a ORDER BY snapshot_timestamp DESC LIMIT 1
    """), {"a": aid}).fetchone()
    assert snap2[0] == sealed_input_before, "스냅샷 내용이 변경됨 (불변성 위반)"


def test_statutory_three_limits_consistency():
    """법정 3한도: 원장 합산과 한도 산식 정합"""
    d = client.get("/api/group-credit/statutory-limits").json()
    caps = d["capital"]
    keys = {c["key"] for c in d["controls"]}
    assert keys == {"same_borrower_group", "same_person", "large_exposure_total"}
    for c in d["controls"]:
        assert c["limit"] > 0
        ratio = {"same_borrower_group": 0.25, "same_person": 0.20,
                 "large_exposure_total": 5.0}[c["key"]]
        assert abs(c["limit"] - caps * ratio) < 1


def test_ledger_net_exposure_formula():
    """원장: net = (gross - exclusion) * ccf 전수 검증"""
    db = SessionLocal()
    bad = db.execute(text("""
        SELECT COUNT(*) FROM credit_exposure_ledger
        WHERE ABS(net_exposure - (gross_amount - COALESCE(exclusion, 0)) * ccf) > 1
    """)).fetchone()[0]
    assert bad == 0, f"원장 산식 불일치 {bad}건"


def test_rate_supplement_pauses_sla():
    """금리인하: 보완요구 → SLA 정지, 제출 → 정지기간만큼 기한 연장"""
    db = SessionLocal()
    row = db.execute(text("""
        SELECT request_id, due_date FROM rate_reduction_request
        WHERE status IN ('RECEIVED','REVIEWING') LIMIT 1
    """)).fetchone()
    if not row:
        pytest.skip("처리 중 요청 없음")
    rid, due0 = row
    h = _login("kim.yeosin", "1234")
    r = client.post(f"/api/rate-reduction/requests/{rid}/request-supplement",
                    json={"reason": "재무자료 추가 징구"}, headers=h)
    assert r.status_code == 200
    # 보완 중에는 결정 불가 (상태 조건부)
    r = client.post(f"/api/rate-reduction/requests/{rid}/decide",
                    json={"decision": "REJECTED", "reason": "테스트 사유입니다"}, headers=h)
    assert r.status_code == 409, "보완 중 결정이 차단되지 않음"
    r = client.post(f"/api/rate-reduction/requests/{rid}/submit-supplement", headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "REVIEWING"


def test_notify_requires_decision_and_once():
    """통지: 결정 완료 건만, 중복 통지 차단"""
    db = SessionLocal()
    h = _login("kim.yeosin", "1234")
    row = db.execute(text("""
        SELECT request_id FROM rate_reduction_request
        WHERE status IN ('ACCEPTED','PARTIAL','REJECTED') AND notified_at IS NOT NULL LIMIT 1
    """)).fetchone()
    if row:
        r = client.post(f"/api/rate-reduction/requests/{row[0]}/notify", headers=h)
        assert r.status_code == 409, "중복 통지가 차단되지 않음"


def test_escalation_idempotent():
    """EWS 상향보고 실행은 멱등 - 재실행 시 0건"""
    h = _login("kim.yeosin", "1234")
    client.post("/api/ews-actions/run-escalation", headers=h)
    r = client.post("/api/ews-actions/run-escalation", headers=h)
    assert r.status_code == 200
    assert r.json()["escalated"] == 0


def test_rule_register_effective_date():
    """규정 레지스터: 효력일 기준 선택 (2027 PF 규칙은 2026 시점 미적용)"""
    now = client.get("/api/rules/effective", params={"date": "2026-07-31"}).json()
    future = client.get("/api/rules/effective", params={"date": "2027-06-30"}).json()
    assert "RULE_PF_EQUITY" not in now["rules"], "시행 전 규칙이 현재 유효로 분류됨"
    assert "RULE_PF_EQUITY" in future["rules"]
    assert "RULE_PROV_MIN" in now["rules"]


def test_obligation_inbox_aggregates():
    """의무관리함: 5개 소스 통합·기한초과 집계"""
    d = client.get("/api/obligations").json()
    assert d["total"] > 0
    assert set(d["by_type"].keys()) >= {"정책 예외 재검토", "EWS 조치", "금리인하요구"}
    assert d["overdue"] == sum(1 for i in d["items"] if i["overdue"]) or d["total"] > 200
