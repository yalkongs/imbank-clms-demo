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
             "params": json.loads(r[7] or "{}"), "applied_in": r[8],
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
