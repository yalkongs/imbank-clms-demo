"""
전자 여신철 (Credit Case File) API
===================================
"왜 승인했는가"를 사후에 재현하는 의사결정 증거 패키지.
한 신청 건에 대해 차주·자료 근거(기준일·출처)·모델 산출(버전)·심사 판단·
정책 예외·승인 체인(전결)·실행·사후관리를 하나의 응답으로 조립한다.

모든 산출값에는 기준일·버전이 붙는다 - 제3자 리뷰 P0 '전자 여신철'의
PoC 최소 조각. 데이터는 기존 테이블에서 조립하며 새 원장을 만들지 않는다.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..core.config import AS_OF_STR
from ..core.audit import record_audit
from ..core.auth import get_current_user, User

router = APIRouter(prefix="/api/credit-case", tags=["CreditCase"])

# 적용 규정 레지스터 - 하드코딩된 산식이 어느 규정·버전을 따르는지 명시
APPLIED_RULES = [
    {"rule": "자산건전성 분류·최저적립률", "basis": "은행업감독규정 §29 · 시행세칙 별표3", "version": "2026-01 개정"},
    {"rule": "기대신용손실(ECL)", "basis": "K-IFRS 제1109호", "version": "B5.5 적용"},
    {"rule": "전결권 검증", "basis": "여신전결규정", "version": "approval_authority 정본"},
    {"rule": "RAROC·자본배분", "basis": "내부 자본관리지침", "version": "2026-01 v3.1"},
]


@router.get("/exceptions")
def list_policy_exceptions(db: Session = Depends(get_db)):
    """정책 예외 전체 목록 (보고·감사 화면용) - 구조화된 예외 관리 대장"""
    rows = db.execute(text("""
        SELECT pe.exception_id, pe.application_id, pe.customer_id, c.customer_name,
               pe.rule_ref, pe.rule_version, pe.reason, pe.mitigation,
               pe.approver_level, pe.approver_name, pe.approved_at,
               pe.valid_until, pe.review_date, pe.status, pe.outcome
        FROM policy_exception pe
        LEFT JOIN customer c ON c.customer_id = pe.customer_id
        ORDER BY CASE pe.status WHEN 'ACTIVE' THEN 0 WHEN 'EXPIRED' THEN 1 ELSE 2 END,
                 pe.review_date
    """)).fetchall()
    out = []
    for r in rows:
        out.append({
            "exception_id": r[0], "application_id": r[1], "customer_id": r[2],
            "customer_name": r[3], "rule_ref": r[4], "rule_version": r[5],
            "reason": r[6], "mitigation": r[7], "approver_level": r[8],
            "approver_name": r[9], "approved_at": r[10], "valid_until": r[11],
            "review_date": r[12], "status": r[13], "outcome": r[14],
            "review_due": r[13] == "ACTIVE" and (r[12] or "") <= AS_OF_STR,
        })
    return {
        "as_of": AS_OF_STR,
        "total": len(out),
        "active": sum(1 for x in out if x["status"] == "ACTIVE"),
        "review_due": sum(1 for x in out if x["review_due"]),
        "exceptions": out,
    }


@router.get("/{application_id}")
def get_case_file(application_id: str, db: Session = Depends(get_db)):
    """여신철 - 판단의 전 과정을 한 번에 재현"""
    app_row = db.execute(text("""
        SELECT la.application_id, la.application_date, la.application_type,
               la.customer_id, la.product_code, la.requested_amount, la.requested_tenor,
               la.requested_rate, la.purpose_code, la.status, la.current_stage, la.branch_code,
               pm.product_name
        FROM loan_application la
        LEFT JOIN product_master pm ON pm.product_code = la.product_code
        WHERE la.application_id = :aid
    """), {"aid": application_id}).fetchone()
    if not app_row:
        raise HTTPException(404, "신청 건을 찾을 수 없습니다")
    cust_id = app_row[3]

    cust = db.execute(text("""
        SELECT customer_name, biz_reg_no, industry_name, region, size_category,
               listing_status, establish_date
        FROM customer WHERE customer_id = :cid
    """), {"cid": cust_id}).fetchone()

    grp = db.execute(text("""
        SELECT bg.group_id, bg.group_name
        FROM borrower_group_member m JOIN borrower_group bg ON bg.group_id = m.group_id
        WHERE m.customer_id = :cid LIMIT 1
    """), {"cid": cust_id}).fetchone()

    # 자료 근거 - 무엇을(출처), 언제 기준(기준일)으로 썼는가
    fs = db.execute(text("""
        SELECT fiscal_year, stmt_type, source, audited, revenue, total_assets, total_debt, equity
        FROM financial_statement
        WHERE customer_id = :cid AND fiscal_year < CAST(substr(:ad, 1, 4) AS INTEGER)
        ORDER BY fiscal_year DESC LIMIT 1
    """), {"cid": cust_id, "ad": (app_row[1] or AS_OF_STR)[:10]}).fetchone()
    if fs is None:
        fs = db.execute(text("""
            SELECT fiscal_year, stmt_type, source, audited, revenue, total_assets, total_debt, equity
            FROM financial_statement WHERE customer_id = :cid
            ORDER BY fiscal_year DESC LIMIT 1
        """), {"cid": cust_id}).fetchone()
    fr = db.execute(text("""
        SELECT fiscal_year, debt_ratio, ier, dscr, calc_date
        FROM financial_ratio WHERE customer_id = :cid ORDER BY fiscal_year DESC LIMIT 1
    """), {"cid": cust_id}).fetchone()

    # 모델 산출 - 버전 포함
    # as-of 원칙: 신청일 이전에 존재하던 최신 등급만 '판단 근거'다.
    # (사후 산출 등급이 여신철에 섞이면 재현이 아니라 결과론이 된다)
    app_date = (app_row[1] or AS_OF_STR)[:10]
    rating = db.execute(text("""
        SELECT rating_date, model_id, model_version, raw_score, final_grade, pd_value,
               override_grade, override_reason, override_by
        FROM credit_rating_result
        WHERE customer_id = :cid AND rating_date <= :ad
        ORDER BY rating_date DESC LIMIT 1
    """), {"cid": cust_id, "ad": app_date}).fetchone()
    rating_after = None
    if rating is None:
        rating_after = db.execute(text("""
            SELECT rating_date, model_id, model_version, raw_score, final_grade, pd_value,
                   override_grade, override_reason, override_by
            FROM credit_rating_result WHERE customer_id = :cid
            ORDER BY rating_date DESC LIMIT 1
        """), {"cid": cust_id}).fetchone()
    rp = db.execute(text("""
        SELECT calc_date, ttc_pd, pit_pd, lgd, ead, rwa, expected_loss, economic_capital
        FROM risk_parameter WHERE application_id = :aid LIMIT 1
    """), {"aid": application_id}).fetchone()

    # 승인 체인 (전결)
    approvals = db.execute(text("""
        SELECT approval_level, approver_name, decision, conditions, comments, decided_at
        FROM approval_history WHERE application_id = :aid ORDER BY decided_at
    """), {"aid": application_id}).fetchall()

    # 정책 예외
    exceptions = db.execute(text("""
        SELECT rule_ref, rule_version, reason, mitigation, approver_level, approver_name,
               approved_at, valid_until, review_date, status, outcome
        FROM policy_exception
        WHERE application_id = :aid OR customer_id = :cid
        ORDER BY approved_at DESC
    """), {"aid": application_id, "cid": cust_id}).fetchall()

    # 실행 - 시설·담보·현재 상태
    facilities = db.execute(text("""
        SELECT facility_id, product_code, approved_amount, outstanding_amount,
               final_rate, contract_date, maturity_date, status, dpd, classification
        FROM facility WHERE application_id = :aid
    """), {"aid": application_id}).fetchall()
    collaterals = db.execute(text("""
        SELECT collateral_type, current_value, recognition_ratio, recognized_value,
               ltv, valuation_date
        FROM collateral WHERE application_id = :aid
    """), {"aid": application_id}).fetchall()

    # 사후관리 - 코베넌트·EWS·감사 흔적
    covenants = db.execute(text("""
        SELECT cv.covenant_name, cv.threshold_value, cc.actual_value, cc.result, cc.check_date
        FROM covenant cv
        JOIN facility f ON f.facility_id = cv.facility_id
        LEFT JOIN (SELECT covenant_id, actual_value, result, check_date,
                          ROW_NUMBER() OVER (PARTITION BY covenant_id ORDER BY check_date DESC) rn
                   FROM covenant_check) cc
          ON cc.covenant_id = cv.covenant_id AND cc.rn = 1
        WHERE f.customer_id = :cid LIMIT 8
    """), {"cid": cust_id}).fetchall()
    audits = db.execute(text("""
        SELECT log_timestamp, user_id, action_type, after_value
        FROM audit_log WHERE target_id = :aid ORDER BY log_timestamp DESC LIMIT 10
    """), {"aid": application_id}).fetchall()
    ews = db.execute(text("""
        SELECT composite_score, ews_grade, score_date FROM ews_composite_score
        WHERE customer_id = :cid ORDER BY score_date DESC LIMIT 1
    """), {"cid": cust_id}).fetchone()

    return {
        "as_of": AS_OF_STR,
        "application": {
            "application_id": app_row[0], "application_date": app_row[1],
            "type": app_row[2], "product_code": app_row[4], "product_name": app_row[12],
            "requested_amount": app_row[5], "tenor": app_row[6], "requested_rate": app_row[7],
            "purpose": app_row[8], "status": app_row[9], "stage": app_row[10],
            "branch": app_row[11],
        },
        "borrower": cust and {
            "customer_id": cust_id, "name": cust[0], "biz_reg_no": cust[1],
            "industry": cust[2], "region": cust[3], "size": cust[4],
            "listing": cust[5], "established": cust[6],
            "group": grp and {"group_id": grp[0], "group_name": grp[1]},
        },
        "data_basis": {
            "financial_statement": fs and {
                "fiscal_year": fs[0], "type": fs[1], "source": fs[2] or "미확인",
                "audited": bool(fs[3]), "revenue": fs[4], "total_assets": fs[5],
                "total_debt": fs[6], "equity": fs[7],
            },
            "financial_ratio": fr and {
                "fiscal_year": fr[0], "debt_ratio": fr[1], "icr": fr[2],
                "dscr": fr[3], "calc_date": fr[4],
            },
        },
        "as_of_basis": {
            "principle": "자료 근거·모델 산출은 신청일 이전(as-of) 자료로 재구성, "
                         "사후관리 섹션만 현재 기준",
            "application_date": app_date,
            "rating_after_decision": bool(rating is None and rating_after),
        },
        "model_outputs": {
            "rating": (lambda r: r and {
                "rating_date": r[0], "model_id": r[1], "model_version": r[2],
                "raw_score": r[3], "final_grade": r[4], "pd": r[5],
                "as_of_application": rating is not None,
                "override": r[6] and {"grade": r[6], "reason": r[7], "by": r[8]},
            })(rating or rating_after),
            "risk_parameter": rp and {
                "calc_date": rp[0], "ttc_pd": rp[1], "pit_pd": rp[2], "lgd": rp[3],
                "ead": rp[4], "rwa": rp[5], "expected_loss": rp[6], "economic_capital": rp[7],
            },
        },
        "approvals": [
            {"level": a[0], "approver": a[1], "decision": a[2],
             "conditions": a[3], "comments": a[4], "decided_at": a[5]}
            for a in approvals
        ],
        "exceptions": [
            {"rule_ref": e[0], "rule_version": e[1], "reason": e[2], "mitigation": e[3],
             "approver_level": e[4], "approver_name": e[5], "approved_at": e[6],
             "valid_until": e[7], "review_date": e[8], "status": e[9], "outcome": e[10]}
            for e in exceptions
        ],
        "execution": {
            "facilities": [
                {"facility_id": f[0], "product": f[1], "approved": f[2], "outstanding": f[3],
                 "rate": f[4], "contract_date": f[5], "maturity": f[6], "status": f[7],
                 "dpd": f[8], "classification": f[9]}
                for f in facilities
            ],
            "collaterals": [
                {"type": c[0], "value": c[1], "recognition_ratio": c[2],
                 "recognized": c[3], "ltv": c[4], "valuation_date": c[5]}
                for c in collaterals
            ],
        },
        "post_management": {
            "covenants": [
                {"type": c[0], "threshold": c[1], "actual": c[2], "result": c[3], "checked": c[4]}
                for c in covenants
            ],
            "ews": ews and {"score": ews[0], "grade": ews[1], "score_date": ews[2]},
            "audit_trail": [
                {"at": a[0], "user": a[1], "action": a[2], "detail": a[3]}
                for a in audits
            ],
        },
        "applied_rules": APPLIED_RULES,
    }


@router.post("/{application_id}/exceptions")
def create_policy_exception(
    application_id: str,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """정책 예외 등록 - 자유 메모가 아니라 규정·사유·완화수단·재검토일 구조 강제"""
    required = ["rule_ref", "reason", "mitigation", "approver_level", "valid_until", "review_date"]
    missing = [k for k in required if not payload.get(k)]
    if missing:
        raise HTTPException(422, f"필수 항목 누락: {', '.join(missing)}")
    cust = db.execute(text(
        "SELECT customer_id FROM loan_application WHERE application_id = :aid"
    ), {"aid": application_id}).fetchone()
    if not cust:
        raise HTTPException(404, "신청 건을 찾을 수 없습니다")

    import uuid
    ex_id = f"PEX_{uuid.uuid4().hex[:10].upper()}"
    db.execute(text("""
        INSERT INTO policy_exception
            (exception_id, application_id, customer_id, rule_ref, rule_version, reason,
             mitigation, approver_level, approver_name, approved_at, valid_until,
             review_date, status)
        VALUES (:id, :aid, :cid, :rule, :ver, :reason, :mit, :lvl, :name, :at, :until, :rev, 'ACTIVE')
    """), {
        "id": ex_id, "aid": application_id, "cid": cust[0],
        "rule": payload["rule_ref"], "ver": payload.get("rule_version", "현행"),
        "reason": payload["reason"], "mit": payload["mitigation"],
        "lvl": current_user.approval_level, "name": current_user.name,
        "at": AS_OF_STR, "until": payload["valid_until"], "rev": payload["review_date"],
    })
    record_audit(db, user_id=current_user.name, user_dept=current_user.dept,
                 action_type="POLICY_EXCEPTION", target_entity="policy_exception",
                 target_id=ex_id, after={"rule": payload["rule_ref"], "app": application_id})
    db.commit()
    return {"exception_id": ex_id, "status": "ACTIVE"}
