-- 신용공여 원장 (은행업감독규정 별표2 근사)
-- 난내·난외를 분리하고 신용환산율(CCF)·제외액을 명시해 법정 한도 산정의
-- 정본으로 쓴다. 화면·한도 통제는 이 원장에서 계산한다 (2차 리뷰 P0-2).
CREATE TABLE IF NOT EXISTS credit_exposure_ledger (
    exposure_id   TEXT PRIMARY KEY,
    customer_id   TEXT NOT NULL REFERENCES customer(customer_id),
    facility_id   TEXT,
    exposure_type TEXT NOT NULL,     -- ON_LOAN / OFF_UNDRAWN / OFF_GUARANTEE
    gross_amount  REAL NOT NULL,     -- 원금액
    ccf           REAL NOT NULL,     -- 신용환산율 (별표2 근사: 대출 1.0 / 미사용 0.4 / 보증 1.0)
    exclusion     REAL DEFAULT 0,    -- 제외·공제액
    net_exposure  REAL NOT NULL,     -- (gross - exclusion) * ccf
    as_of_date    DATE,
    rule_ref      TEXT,
    source_ref    TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cel_cust ON credit_exposure_ledger(customer_id);
CREATE INDEX IF NOT EXISTS idx_cel_type ON credit_exposure_ledger(exposure_type);
