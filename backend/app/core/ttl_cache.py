"""
경량 TTL 캐시 - 무거운 읽기 전용 집계 응답용
=============================================
데모 DB는 사실상 읽기 전용이라, 대형 집계(포트폴리오 맵 벡터·월별 이력·
업무보고서)를 요청마다 다시 계산할 이유가 없다. 프로세스 내 dict 로
TTL 캐시한다. 승인 등 쓰기가 있어도 TTL(기본 120초) 안에 자연 반영된다.

사용: 엔드포인트 안에서
    cached = ttl_get("key")
    if cached is not None: return cached
    ...  # 무거운 계산
    return ttl_set("key", result)
"""
import time
from typing import Any, Optional

_STORE: dict[str, tuple[float, Any]] = {}
DEFAULT_TTL = 120.0


def ttl_get(key: str) -> Optional[Any]:
    hit = _STORE.get(key)
    if not hit:
        return None
    ts, value = hit
    if time.time() - ts > DEFAULT_TTL:
        _STORE.pop(key, None)
        return None
    return value


def ttl_set(key: str, value: Any) -> Any:
    _STORE[key] = (time.time(), value)
    return value
