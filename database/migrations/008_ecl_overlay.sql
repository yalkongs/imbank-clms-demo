-- P7: ECL 관리자 오버레이 (management overlay)
-- 전망모형 점검체계(2023 은행업감독규정 개정: 매년 독립 검증 → 금감원 제출,
-- 미흡 시 특별대손준비금 적립요구) 대응 - 모형 산출 밖의 경영진 판단 조정은
-- 금액·사유·승인자·존속기한이 기록으로 남아야 검증 가능하다.
CREATE TABLE IF NOT EXISTS ecl_overlay (
    overlay_id    TEXT PRIMARY KEY,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    segment       TEXT NOT NULL,            -- 적용 대상 (PORTFOLIO | 업종코드 등)
    amount        REAL NOT NULL,            -- 조정액 (+적립 / -환입, 원)
    direction     TEXT NOT NULL,            -- ADD | RELEASE
    reason        TEXT NOT NULL,            -- 판단 근거 (필수)
    risk_driver   TEXT,                     -- 지목 리스크 (PF·자영업·금리 등)
    expiry_review DATE,                     -- 재검토 기한 (오버레이는 영구적이면 안 된다)
    status        TEXT NOT NULL DEFAULT 'ACTIVE',   -- ACTIVE | RELEASED
    approved_by   TEXT NOT NULL,
    approved_level TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_overlay_status ON ecl_overlay(status);
