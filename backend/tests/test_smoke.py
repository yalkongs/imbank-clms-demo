"""
전 API 스모크 테스트
====================
파라미터 없는 GET 전수(약 135개)를 돌려 다음 회귀를 잡는다.
  · 라우트 순서 문제 (파라미터 라우트가 정적 경로를 가로채는 사고 - 실제 발생 이력)
  · 배포 의존성 누락 (fpdf2 미설치로 PDF 500 - 실제 발생 이력)
  · 시드 재생성 후 특정 화면의 전부-0 응답

실행: cd backend && python -m pytest tests -q
"""
import os
import re
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.main import app  # noqa: E402

client = TestClient(app)


def _auth_headers(user_id="kim.yeosin", pin="1234"):
    r = client.post("/api/auth/login", json={"user_id": user_id, "pin": pin})
    assert r.status_code == 200, f"데모 로그인 실패: {r.text[:120]}"
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _parameterless_get_paths():
    # FastAPI 버전에 따라 include_router 가 중첩 보관되므로 OpenAPI 스펙에서 수집.
    # 필수 쿼리 파라미터가 있는 엔드포인트(검색·what-if 등)는 인자 없이 422 가 정상이라 제외.
    spec = app.openapi()
    out = []
    for path, ops in spec["paths"].items():
        get = ops.get("get")
        if not get or not path.startswith("/api/") or "{" in path:
            continue
        if any(p.get("required") for p in get.get("parameters", [])):
            continue
        if path == "/api/auth/me":            # 인증 필수 GET
            continue
        out.append(path)
    return sorted(out)


ALL_GETS = _parameterless_get_paths()


def test_route_census():
    """엔드포인트 수가 갑자기 줄면 라우터 등록 누락을 의심한다"""
    assert len(ALL_GETS) >= 120, f"파라미터 없는 GET 이 {len(ALL_GETS)}개뿐"


@pytest.mark.parametrize("path", ALL_GETS)
def test_get_ok(path):
    r = client.get(path)
    assert r.status_code == 200, f"{path} -> {r.status_code}: {r.text[:200]}"


def test_previously_shadowed_model_routes():
    """/{model_id} 가 정적 경로를 가로채던 회귀 방지 - 각 응답의 고유 필드를 확인"""
    checks = {
        "/api/models/lgd-backtest": "mean_error_pct",
        "/api/models/recovery-analytics": "total_recovered",
        "/api/models/recovery-timeline": "duration_buckets",
        "/api/models/ews-validation": "available",
    }
    for path, field in checks.items():
        body = client.get(path).json()
        assert field in body, f"{path} 응답에 {field} 없음 - 라우트 가로채기 의심: {list(body)[:6]}"


def test_report_pdf_renders():
    """fpdf2 미설치·폰트 누락 회귀 방지"""
    r = client.get("/api/governance/report/pdf")
    assert r.status_code == 200
    assert r.content[:5] == b"%PDF-", "PDF 매직 바이트가 아님"
    assert len(r.content) > 10_000


def test_dashboard_not_all_zero():
    """시드 사고(WAL 미체크포인트 등)로 화면 전부-0 이 되는 회귀 방지"""
    p = client.get("/api/dashboard/summary").json()["portfolio"]
    assert p["total_customers"] > 0 and p["total_exposure"] > 0


def test_read_only_guard():
    """READ_ONLY=true 에서 쓰기 차단 (미들웨어는 기동 시 결정되므로 별도 앱으로 검증)"""
    os.environ["READ_ONLY"] = "true"
    for mod in list(sys.modules):
        if mod == "app.main":
            del sys.modules[mod]
    try:
        from app.main import app as ro_app
        ro = TestClient(ro_app)
        r = ro.post("/api/applications/APP_X/approve", params={"decision": "APPROVED"})
        assert r.status_code in (401, 403), f"읽기 전용인데 쓰기가 {r.status_code}"
        assert ro.get("/health").status_code == 200
    finally:
        os.environ.pop("READ_ONLY", None)
        for mod in list(sys.modules):
            if mod == "app.main":
                del sys.modules[mod]


# ── 신규 여신통제 기능의 핵심 동작 (경로 파라미터·POST 포함) ──────────

def test_case_file_as_of_rating():
    """여신철: 승인 건 표본에서 등급이 신청일 이전(as-of)인지 확인"""
    from app.core.database import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    apps = db.execute(text("""
        SELECT ah.application_id FROM approval_history ah
        GROUP BY ah.application_id LIMIT 5
    """)).fetchall()
    assert apps, "결재 이력 표본 없음"
    for (aid,) in apps:
        body = client.get(f"/api/credit-case/{aid}").json()
        rating = body["model_outputs"]["rating"]
        if rating and rating.get("as_of_application"):
            assert rating["rating_date"][:10] <= body["as_of_basis"]["application_date"], \
                f"{aid}: 사후 등급이 as-of 근거로 표시됨"


def test_ews_action_sequence_guard():
    """EWS: 선행단계 미완료 상태에서 후행단계 완료 시도 → 422"""
    from app.core.database import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    row = db.execute(text("""
        SELECT a3.action_id FROM ews_action a3
        WHERE a3.status != 'DONE'
          AND EXISTS (SELECT 1 FROM ews_action p
                      WHERE p.alert_id = a3.alert_id AND p.step_no < a3.step_no
                        AND p.status != 'DONE')
        LIMIT 1
    """)).fetchone()
    if not row:
        pytest.skip("후행 대기 단계 표본 없음")
    r = client.post(f"/api/ews-actions/{row[0]}/complete",
                    json={"action_taken": "순서 위반 시도 테스트"},
                    headers=_auth_headers())
    assert r.status_code == 422, f"선행단계 가드 미작동: {r.status_code}"


def test_rate_reduction_rejects_invalid_rates():
    """금리인하: 음수·NaN·기존 초과 금리는 422"""
    from app.core.database import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    row = db.execute(text("""
        SELECT request_id, old_rate FROM rate_reduction_request
        WHERE status IN ('RECEIVED','REVIEWING') LIMIT 1
    """)).fetchone()
    if not row:
        pytest.skip("처리 중 요청 표본 없음")
    rid, old = row
    for bad in (-0.01, 0, old * 1.5, "NaN"):
        r = client.post(f"/api/rate-reduction/requests/{rid}/decide",
                        json={"decision": "ACCEPTED", "new_rate": bad,
                              "reason": "유효성 테스트 사유입니다"},
                        headers=_auth_headers())
        assert r.status_code == 422, f"{bad} 통과됨 ({r.status_code})"


def test_reconciliation_separates_natural_diff():
    """대사표: '자연스러운 차이'와 '검토 필요' 분리 응답"""
    body = client.get("/api/classification/reconciliation").json()
    assert "natural_diff_count" in body and "needs_review_count" in body
    assert body["natural_diff_count"] + body["needs_review_count"] == body["mismatch_count"]


def test_borrower_scope_excludes_intra_group_guarantees():
    """동일차주: 계열사 보증은 신용공여 합산에서 제외 (목록·상세 일치)"""
    ov = client.get("/api/group-credit/regulatory-scope").json()
    g = ov["groups"][0]
    detail = client.get(f"/api/group-credit/regulatory-scope/{g['group_id']}").json()
    agg = detail["aggregation"]
    assert abs(agg["total_credit"] - (agg["loans"] + agg["undrawn"])) < 1, \
        "보증이 신용공여에 합산됨"
    assert abs(g["total_credit"] - agg["total_credit"]) < 1, "목록·상세 합산 불일치"


def test_write_requires_auth():
    """미인증 쓰기는 401 - 공개 배포에서 익명 쓰기 차단"""
    r = client.post("/api/ews-actions/X/complete", json={"action_taken": "test"})
    assert r.status_code == 401


def test_approver_is_server_decided():
    """승인자·전결권은 클라이언트 파라미터가 아니라 토큰 사용자로 결정"""
    from app.core.database import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    row = db.execute(text("""
        SELECT la.application_id FROM loan_application la
        WHERE la.status IN ('REVIEWING','RECEIVED','SCREENING')
          AND la.current_stage NOT IN ('RECEIVED')
          AND la.requested_amount < 50e8
          AND NOT EXISTS (SELECT 1 FROM approval_history ah
                          WHERE ah.application_id = la.application_id)
        LIMIT 1
    """)).fetchone()
    if not row:
        pytest.skip("승인 가능 표본 없음")
    aid = row[0]
    # 클라이언트가 EXECUTIVE 를 사칭해도 서버는 토큰(TEAM_LEAD)으로 기록해야 한다
    r = client.post(f"/api/applications/{aid}/approve",
                    params={"decision": "APPROVE", "approval_level": "EXECUTIVE",
                            "approver_name": "가짜임원"},
                    headers=_auth_headers("kim.yeosin", "1234"))
    assert r.status_code == 200, r.text[:200]
    rec = db.execute(text("""
        SELECT approval_level, approver_name FROM approval_history
        WHERE application_id = :a ORDER BY decided_at DESC LIMIT 1
    """), {"a": aid}).fetchone()
    assert rec[0] == "TEAM_LEAD" and rec[1] == "김여신", f"사칭 값이 기록됨: {rec}"
