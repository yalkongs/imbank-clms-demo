"""
감사 추적 헬퍼
==============
audit_log 테이블은 스키마에 정의만 되어 있고 어디서도 쓰이지 않았다.
책무구조도 시대에 "누가 언제 무엇을 바꿨는가"를 증빙 못 하는 여신 시스템은
성립하지 않으므로, 모든 의미 있는 쓰기 API 가 이 헬퍼를 거치도록 한다.

PoC 라 인증이 없으므로 user_id 는 호출부가 넘기는 값(기본 '김여신')을 쓴다.
실제 시스템에서는 인증 컨텍스트에서 주입한다.
"""
import json
import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import AS_OF_STR


def record_audit(
    db: Session,
    action_type: str,
    target_entity: str,
    target_id: str,
    before: dict | None = None,
    after: dict | None = None,
    user_id: str = "김여신",
    user_dept: str = "여신심사부",
    critical: bool = False,
) -> None:
    """감사 기록 1건 삽입.

    critical=False: 실패해도 본 트랜잭션을 깨지 않는다 (조회성 부가 기록).
    critical=True : 승인 같은 핵심 행위 - 감사기록 실패는 은폐하지 않고
                    예외를 올려 전체 트랜잭션을 롤백시킨다 (제3자 리뷰 P0-1)."""
    try:
        db.execute(text("""
            INSERT INTO audit_log
            (log_id, log_timestamp, user_id, user_dept, action_type,
             target_entity, target_id, before_value, after_value, ip_address)
            VALUES (:id, :ts, :uid, :dept, :action, :entity, :tid, :before, :after, :ip)
        """), {
            "id": f"AUD_{uuid.uuid4().hex[:12].upper()}",
            # 감사 시각은 실제 처리 시각이어야 하므로 기준일이 아니라 now 를 쓴다
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "uid": user_id,
            "dept": user_dept,
            "action": action_type,
            "entity": target_entity,
            "tid": target_id,
            "before": json.dumps(before, ensure_ascii=False) if before else None,
            "after": json.dumps(after, ensure_ascii=False) if after else None,
            "ip": "127.0.0.1",
        })
    except Exception:
        # critical 행위(승인 등)의 감사기록 실패는 은폐하지 않는다 - 롤백 유도
        if critical:
            raise
        # 부가 기록 실패는 업무 처리를 막지 않는다 (실제 시스템은 outbox·경보 필요)
        pass
