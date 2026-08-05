"""
인증 API - 데모 계정 로그인
============================
공개 PoC 에서 익명 쓰기를 차단하되 체험은 열어둔다:
쓰기 작업은 데모 계정 로그인(서버 검증 PIN)을 요구하고,
승인자·전결권은 토큰의 사용자에서 서버가 결정한다.
"""
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..core.auth import check_pin, issue_token, get_current_user, User

router = APIRouter(prefix="/api/auth", tags=["Auth"])

LEVEL_KO = {"STAFF": "담당자", "TEAM_LEAD": "팀장", "DEPT_HEAD": "부서장",
            "EXECUTIVE": "임원", "COMMITTEE": "여신위원회"}

# PoC 데모용 PIN 힌트 - 실제 시스템이라면 절대 노출 금지
DEMO_PIN_HINTS = {"kim.simsa": "1111", "kim.yeosin": "1234",
                  "park.bujang": "2222", "lee.jeonmu": "3333"}


@router.get("/accounts")
def list_demo_accounts(db: Session = Depends(get_db)):
    """데모 계정 목록 (PIN 힌트 포함 - PoC 전용)"""
    rows = db.execute(text("""
        SELECT user_id, name, dept, approval_level FROM user_account
        WHERE active = 1 ORDER BY CASE approval_level
            WHEN 'STAFF' THEN 0 WHEN 'TEAM_LEAD' THEN 1
            WHEN 'DEPT_HEAD' THEN 2 WHEN 'EXECUTIVE' THEN 3 ELSE 4 END
    """)).fetchall()
    return {
        "note": "PoC 데모 계정입니다 - PIN 이 공개되어 있으며 실제 인증 체계가 아닙니다",
        "accounts": [
            {"user_id": r[0], "name": r[1], "dept": r[2],
             "approval_level": r[3], "level_ko": LEVEL_KO.get(r[3], r[3]),
             "pin_hint": DEMO_PIN_HINTS.get(r[0], "")}
            for r in rows
        ],
    }


@router.post("/login")
def login(payload: dict = Body(...), db: Session = Depends(get_db)):
    user_id = (payload.get("user_id") or "").strip()
    pin = (payload.get("pin") or "").strip()
    user = check_pin(db, user_id, pin)
    if not user:
        raise HTTPException(401, "계정 또는 PIN 이 올바르지 않습니다")
    return {
        "token": issue_token(user.user_id),
        "user": {"user_id": user.user_id, "name": user.name, "dept": user.dept,
                 "approval_level": user.approval_level,
                 "level_ko": LEVEL_KO.get(user.approval_level, user.approval_level)},
    }


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"user_id": user.user_id, "name": user.name, "dept": user.dept,
            "approval_level": user.approval_level,
            "level_ko": LEVEL_KO.get(user.approval_level, user.approval_level)}
