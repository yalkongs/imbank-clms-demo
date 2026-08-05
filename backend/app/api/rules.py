"""
규정 레지스터 API
=================
법령·감독규정·내규의 버전·효력일·산식 파라미터를 한 곳에서 관리한다.
화면·산식은 숫자를 하드코딩하는 대신 이 레지스터를 참조한다 (7단계-⑥).
"""
import json
from functools import lru_cache

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db, SessionLocal
from ..core.config import AS_OF_STR

router = APIRouter(prefix="/api/rules", tags=["Rules"])


def _params_display(rule_id: str, p: dict) -> list[str]:
    """파라미터를 사람이 읽는 형태로 - 원시 JSON 노출 방지 (점검 지적 반영)"""
    try:
        if rule_id == "RULE_PROV_MIN":
            ko = {"NORMAL": "정상", "PRECAUTIONARY": "요주의", "SUBSTANDARD": "고정",
                  "DOUBTFUL": "회수의문", "LOSS": "추정손실"}
            return [f"{ko.get(k, k)} {v * 100:g}%" for k, v in p.items()]
        if rule_id == "RULE_DPD_BOUND":
            ko = {"PRECAUTIONARY": "요주의", "SUBSTANDARD": "고정", "LOSS": "추정손실"}
            return [f"{ko.get(k, k)} {v}일 이상" for k, v in p.items()]
        if rule_id == "RULE_EWS_THRESH":
            return [f"요주의 강등: {p['PRECAUTIONARY_BELOW']}점 미만",
                    f"SICR(Stage 2): {p['SICR_BELOW']}점 미만"]
        if rule_id == "RULE_LIMIT_GROUP":
            return [f"자기자본의 {p['ratio'] * 100:g}%"]
        if rule_id == "RULE_LIMIT_SINGLE":
            return [f"자기자본의 {p['ratio'] * 100:g}%"]
        if rule_id == "RULE_LIMIT_LARGE":
            return [f"거액 판정: 자기자본 {p['trigger_ratio'] * 100:g}% 초과",
                    f"총액 한도: 자기자본의 {p['total_ratio'] * 100:g}%"]
        if rule_id == "RULE_CCF":
            ko = {"ON_LOAN": "대출(난내)", "OFF_UNDRAWN": "미사용약정", "OFF_GUARANTEE": "지급보증"}
            return [f"{ko.get(k, k)} {v * 100:g}%" for k, v in p.items()]
        if rule_id == "RULE_RATE_SLA":
            out = [f"통지기한 {p['biz_days']}영업일"]
            if p.get("exclude_supplement_period"):
                out.append("자료보완 기간 제외")
            return out
        if rule_id == "RULE_RAROC_HURDLE":
            return [f"허들 {p['hurdle_pct']:g}%"]
        if rule_id == "RULE_BIS_MIN":
            return [f"BIS {p['bis']:g}%", f"Tier1 {p['tier1']:g}%", f"CET1 {p['cet1']:g}%"]
        if rule_id == "RULE_PF_GAP":
            return [f"공정률-분양률 괴리 {p['gap_pp']}%p 이상 경보"]
        if rule_id == "RULE_PF_EQUITY":
            return [str(p.get("bands", ""))]
        if rule_id == "RULE_SCB":
            return [f"SCB = {p.get('formula', '')}"]
        if rule_id == "RULE_KOKR_HOLIDAY":
            days = p.get("holidays", [])
            return [f"공휴일 {len(days)}일 등록 (주말 별도)"]
        if rule_id == "RULE_INCL_TARGET":
            return [f"중신용 비중 {p['mid_credit_share']:g}%",
                    f"개인사업자 비중 {p['soho_share']:g}%"]
    except Exception:
        pass
    # 폴백: 키-값 나열
    return [f"{k}: {v}" for k, v in p.items()]


@router.get("")
def list_rules(domain: str = Query(None), db: Session = Depends(get_db)):
    cond, params = "1=1", {}
    if domain:
        cond += " AND domain = :d"
        params["d"] = domain
    rows = db.execute(text(f"""
        SELECT rule_id, domain, name, basis, version, valid_from, valid_to,
               params_json, applied_in
        FROM rule_register WHERE {cond}
        ORDER BY domain, valid_from DESC
    """), params).fetchall()
    return {
        "as_of": AS_OF_STR,
        "rules": [
            {"rule_id": r[0], "domain": r[1], "name": r[2], "basis": r[3],
             "version": r[4], "valid_from": r[5], "valid_to": r[6],
             "params": json.loads(r[7] or "{}"),
             "params_display": _params_display(r[0], json.loads(r[7] or "{}")),
             "applied_in": r[8],
             "effective_now": (r[5] or "") <= AS_OF_STR and (r[6] is None or r[6] >= AS_OF_STR)}
            for r in rows
        ],
    }


@router.get("/effective")
def effective_rules(date: str = Query(None), db: Session = Depends(get_db)):
    """특정일 유효 규칙 세트 - 여신철·재계산은 결정일 기준 규칙을 써야 한다"""
    d = date or AS_OF_STR
    rows = db.execute(text("""
        SELECT rule_id, name, version, params_json FROM rule_register
        WHERE valid_from <= :d AND (valid_to IS NULL OR valid_to >= :d)
    """), {"d": d}).fetchall()
    return {
        "date": d,
        "rules": {r[0]: {"name": r[1], "version": r[2],
                         "params": json.loads(r[3] or "{}")} for r in rows},
    }


def get_rule_params(rule_id: str, fallback: dict) -> dict:
    """모듈에서 규정 파라미터 로드 (레지스터 우선, 실패 시 폴백 상수)"""
    try:
        db = SessionLocal()
        row = db.execute(text(
            "SELECT params_json FROM rule_register WHERE rule_id = :r"
        ), {"r": rule_id}).fetchone()
        db.close()
        if row and row[0]:
            return json.loads(row[0])
    except Exception:
        pass
    return fallback
