-- 여신통제 확장 테이블 정본 DDL
-- (seed_governance_extensions.py 의 IF NOT EXISTS 생성과 동일 - 신규 DB 재구축 시 이 파일 적용)
CREATE TABLE IF NOT EXISTS policy_exception (
    exception_id   TEXT PRIMARY KEY,
    application_id TEXT REFERENCES loan_application(application_id),
    customer_id    TEXT REFERENCES customer(customer_id),
    rule_ref       TEXT NOT NULL,
    rule_version   TEXT,
    reason         TEXT NOT NULL,
    mitigation     TEXT,
    approver_level TEXT,
    approver_name  TEXT,
    approved_at    DATE,
    valid_until    DATE,
    review_date    DATE,
    status         TEXT DEFAULT 'ACTIVE',
    outcome        TEXT,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ews_action (
    action_id    TEXT PRIMARY KEY,
    alert_id     TEXT REFERENCES ews_alert(alert_id),
    customer_id  TEXT,
    step_no      INTEGER,
    step         TEXT,
    owner        TEXT,
    due_date     DATE,
    status       TEXT DEFAULT 'OPEN',
    action_taken TEXT,
    completed_at DATE,
    escalated    INTEGER DEFAULT 0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS rate_reduction_request (
    request_id      TEXT PRIMARY KEY,
    customer_id     TEXT REFERENCES customer(customer_id),
    facility_id     TEXT REFERENCES facility(facility_id),
    request_date    DATE NOT NULL,
    grounds         TEXT,
    grounds_detail  TEXT,
    due_date        DATE,
    status          TEXT DEFAULT 'RECEIVED',
    old_rate        REAL,
    proposed_rate   REAL,
    decided_rate    REAL,
    decision_reason TEXT,
    decided_at      DATE,
    notified_at     DATE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_polex_app    ON policy_exception(application_id);
CREATE INDEX IF NOT EXISTS idx_ewsact_alert ON ews_action(alert_id);
CREATE INDEX IF NOT EXISTS idx_rrr_status   ON rate_reduction_request(status, due_date);
