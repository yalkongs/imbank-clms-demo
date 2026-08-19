-- P6: 여신 거래 생애주기 씬슬라이스 (기한연장·조건변경)
-- "Credit Lifecycle MS"에 생애주기 *거래*가 0건이던 구조 공백을
-- 두 거래(연장·조건변경)로 얇게 연다. 에버그리닝(만기연장 부실 이연)
-- 통제가 핵심: 연장 심사 시 EWS·분류·약정 이력을 서버가 강제 수집한다.
CREATE TABLE IF NOT EXISTS facility_transaction (
    txn_id                 TEXT PRIMARY KEY,
    facility_id            TEXT NOT NULL,
    customer_id            TEXT NOT NULL,
    txn_type               TEXT NOT NULL,      -- EXTENSION | MODIFICATION
    status                 TEXT NOT NULL DEFAULT 'REQUESTED',  -- REQUESTED → APPROVED | REJECTED
    requested_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    requested_by           TEXT,
    -- 기한연장
    current_maturity       DATE,
    new_maturity           DATE,
    extension_months       INTEGER,
    consecutive_extensions INTEGER DEFAULT 0,  -- 이 건 포함 연속 연장 횟수
    -- 조건변경 (금리·한도)
    change_json            TEXT,
    -- 심사 강제표시 스냅샷 (서버가 수집 - 클라이언트 위조 불가)
    review_json            TEXT,
    evergreen_flags        TEXT,               -- JSON 배열 - 비면 정상
    -- 결재
    decision               TEXT,
    decided_by             TEXT,
    decided_level          TEXT,
    decided_at             TIMESTAMP,
    decision_reason        TEXT
);
CREATE INDEX IF NOT EXISTS ix_ft_facility ON facility_transaction(facility_id);
CREATE INDEX IF NOT EXISTS ix_ft_status   ON facility_transaction(status);
