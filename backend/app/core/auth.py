"""
인증·전결의 서버측 결정
========================
승인자·부서·전결권은 클라이언트가 보내는 파라미터가 아니라
로그인 사용자(user_account)에서 서버가 결정한다 (제3자 리뷰 P0-1).

토큰: HMAC 서명 stateless 토큰 (user_id.exp.sig) - 재기동에도 유효.
PoC 한계: SECRET 기본값 사용 시 운영 보안 아님 (데모 계정·PIN 은 화면에 공개).
"""
import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text

from .database import get_db

SECRET = os.getenv("CLMS_AUTH_SECRET", "clms-poc-secret-2026").encode()
TOKEN_TTL = 12 * 3600


@dataclass
class User:
    user_id: str
    name: str
    dept: str
    approval_level: str


def _sign(payload: str) -> str:
    return hmac.new(SECRET, payload.encode(), hashlib.sha256).hexdigest()[:32]


def issue_token(user_id: str) -> str:
    exp = int(time.time()) + TOKEN_TTL
    payload = f"{user_id}.{exp}"
    return f"{payload}.{_sign(payload)}"


def verify_token(token: str) -> Optional[str]:
    try:
        user_id, exp, sig = token.rsplit(".", 2)
        payload = f"{user_id}.{exp}"
        if not hmac.compare_digest(_sign(payload), sig):
            return None
        if int(exp) < time.time():
            return None
        return user_id
    except Exception:
        return None


def check_pin(db: Session, user_id: str, pin: str) -> Optional[User]:
    row = db.execute(text("""
        SELECT user_id, name, dept, approval_level, pin_hash
        FROM user_account WHERE user_id = :u AND active = 1
    """), {"u": user_id}).fetchone()
    if not row:
        return None
    if hashlib.sha256(f"{user_id}:{pin}".encode()).hexdigest() != row[4]:
        return None
    return User(row[0], row[1], row[2], row[3])


def _load_user(db: Session, user_id: str) -> Optional[User]:
    row = db.execute(text("""
        SELECT user_id, name, dept, approval_level
        FROM user_account WHERE user_id = :u AND active = 1
    """), {"u": user_id}).fetchone()
    return User(*row) if row else None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """쓰기 작업 필수 의존성 - 미인증 401"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "로그인이 필요합니다 (우측 상단 사용자 메뉴에서 데모 계정으로 로그인)")
    user_id = verify_token(auth[7:])
    if not user_id:
        raise HTTPException(401, "토큰이 유효하지 않습니다 - 다시 로그인해 주세요")
    user = _load_user(db, user_id)
    if not user:
        raise HTTPException(401, "사용자를 찾을 수 없습니다")
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """조회 화면용 - 로그인 시 사용자 컨텍스트, 아니면 None"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    user_id = verify_token(auth[7:])
    return _load_user(db, user_id) if user_id else None
