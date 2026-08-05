"""
승인 시점 불변 스냅샷 (decision_snapshot)
==========================================
승인 순간의 판단 근거 - 자료(회계연도·출처·해시), 등급(모델·버전),
동일차주 범위, 한도 검증, 정책 예외, 승인 체인 - 를 봉인한다.
이후 등급·재무가 갱신돼도 여신철의 '결정 당시 보기'는 변하지 않는다.
(2차 리뷰 P0-3)

무결성: canonical JSON 의 sha256 을 parameters_json.hash 에 저장.
수정 API 는 존재하지 않는다 (불변).
"""
import hashlib
import json
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session


def _canon(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_and_seal_snapshot(db: Session, application_id: str, *,
                            decision: str, approved_amount, approver_name: str,
                            approval_level: str, as_of: str,
                            backfilled: bool = False) -> str | None:
    """승인 확정 트랜잭션 안에서 호출 - 스냅샷 INSERT (commit 은 호출자가)."""
    app = db.execute(text("""
        SELECT la.customer_id, la.application_date, la.requested_amount, la.product_code
        FROM loan_application la WHERE la.application_id = :aid
    """), {"aid": application_id}).fetchone()
    if not app:
        return None
    cust_id, app_date, req_amt, product = app
    app_date = (app_date or as_of)[:10]

    fs = db.execute(text("""
        SELECT stmt_id, fiscal_year, source, audited, revenue, total_assets
        FROM financial_statement
        WHERE customer_id = :cid AND fiscal_year < CAST(substr(:ad,1,4) AS INTEGER)
        ORDER BY fiscal_year DESC LIMIT 1
    """), {"cid": cust_id, "ad": app_date}).fetchone()
    rating = db.execute(text("""
        SELECT rating_id, rating_date, model_id, model_version, final_grade, pd_value
        FROM credit_rating_result
        WHERE customer_id = :cid AND rating_date <= :ad
        ORDER BY rating_date DESC LIMIT 1
    """), {"cid": cust_id, "ad": app_date}).fetchone()
    grp = db.execute(text("""
        SELECT bg.group_id, bg.group_name FROM borrower_group_member m
        JOIN borrower_group bg ON bg.group_id = m.group_id
        WHERE m.customer_id = :cid LIMIT 1
    """), {"cid": cust_id}).fetchone()
    group_total = None
    if grp:
        group_total = db.execute(text("""
            SELECT COALESCE(SUM(l.net_exposure), 0)
            FROM borrower_group_member m
            JOIN credit_exposure_ledger l ON l.customer_id = m.customer_id
            WHERE m.group_id = :g
        """), {"g": grp[0]}).fetchone()[0]
    capital = db.execute(text(
        "SELECT total_capital FROM capital_position ORDER BY base_date DESC LIMIT 1"
    )).fetchone()
    capital = capital[0] if capital else 0
    exceptions = [r[0] for r in db.execute(text("""
        SELECT exception_id FROM policy_exception
        WHERE application_id = :aid OR customer_id = :cid
    """), {"aid": application_id, "cid": cust_id}).fetchall()]
    chain = [
        {"level": r[0], "approver": r[1], "decision": r[2], "at": r[3]}
        for r in db.execute(text("""
            SELECT approval_level, approver_name, decision, decided_at
            FROM approval_history WHERE application_id = :aid ORDER BY decided_at
        """), {"aid": application_id}).fetchall()
    ]

    input_data = {
        "financial_statement": fs and {
            "stmt_id": fs[0], "fiscal_year": fs[1], "source": fs[2] or "미확인",
            "audited": bool(fs[3]), "revenue": fs[4], "total_assets": fs[5],
        },
        "rating": rating and {
            "rating_id": rating[0], "rating_date": rating[1], "model_id": rating[2],
            "model_version": rating[3], "final_grade": rating[4], "pd": rating[5],
        },
        "borrower_scope": {
            "group": grp and {"group_id": grp[0], "group_name": grp[1]},
            "group_total_credit": group_total,
            "capital": capital,
            "vs_capital_pct": round(group_total / capital * 100, 2)
                              if (group_total and capital) else None,
        },
        "limit_check": {
            "requested_amount": req_amt,
            "regulatory_25pct": capital * 0.25,
            "within_limit": (group_total or 0) <= capital * 0.25 if capital else None,
        },
    }
    output_data = {
        "decision": decision, "approved_amount": approved_amount,
        "approval_level": approval_level, "approver": approver_name,
        "product": product,
    }
    params = {
        "rule_versions": {"provision": "은행업감독규정 §29 2026-01", "ecl": "K-IFRS 1109",
                          "authority": "여신전결규정 (approval_authority)",
                          "borrower_scope": "은행법 §35 원장 근사"},
        "backfilled": backfilled,
        "sealed_at": as_of,
    }
    body = {"input": input_data, "output": output_data,
            "exceptions": exceptions, "chain": chain, "params": params}
    digest = hashlib.sha256(_canon(body).encode()).hexdigest()
    params["hash"] = digest

    snap_id = f"SNAP_{uuid.uuid4().hex[:12].upper()}"
    db.execute(text("""
        INSERT INTO decision_snapshot
        (snapshot_id, application_id, snapshot_timestamp, snapshot_type,
         input_data_json, rating_model_id, rating_model_version,
         output_data_json, feature_values_json, parameters_json)
        VALUES (:sid, :aid, :ts, 'APPROVAL', :inp, :mid, :mver, :out, :feat, :par)
    """), {
        "sid": snap_id, "aid": application_id, "ts": as_of,
        "inp": _canon(input_data),
        "mid": rating[2] if rating else None,
        "mver": rating[3] if rating else None,
        "out": _canon(output_data),
        "feat": _canon({"exceptions": exceptions, "chain": chain}),
        "par": _canon(params),
    })
    return snap_id
