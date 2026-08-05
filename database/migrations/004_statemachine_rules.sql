-- ④ 상태기계·통지·에스컬레이션 + ⑥ 규정 레지스터

-- EWS 기한초과 상향보고 실행 기록 (표시가 아니라 '동작')
CREATE TABLE IF NOT EXISTS ews_escalation (
    escalation_id TEXT PRIMARY KEY,
    action_id     TEXT REFERENCES ews_action(action_id),
    escalated_to  TEXT,               -- 수신 직급
    reason        TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged  INTEGER DEFAULT 0
);

-- 통지 발송 이력 (금리인하 통지 등)
CREATE TABLE IF NOT EXISTS notification_log (
    notification_id TEXT PRIMARY KEY,
    channel         TEXT,             -- MAIL / SMS / PORTAL
    recipient       TEXT,
    subject         TEXT,
    ref_type        TEXT,             -- RATE_REDUCTION / EWS_ESCALATION ...
    ref_id          TEXT,
    status          TEXT DEFAULT 'SENT',   -- SENT / FAILED
    sent_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 금리인하 상태기계 확장 컬럼
ALTER TABLE rate_reduction_request ADD COLUMN supplement_requested_at DATE;
ALTER TABLE rate_reduction_request ADD COLUMN supplement_submitted_at DATE;
ALTER TABLE rate_reduction_request ADD COLUMN supplement_days INTEGER DEFAULT 0;

-- ⑥ 규정 레지스터 - 법령·감독규정·내규의 버전·효력일·산식 파라미터
CREATE TABLE IF NOT EXISTS rule_register (
    rule_id     TEXT PRIMARY KEY,
    domain      TEXT NOT NULL,        -- CLASSIFICATION / LIMIT / RATE / EWS / PF / CAPITAL
    name        TEXT NOT NULL,
    basis       TEXT NOT NULL,        -- 법령·조항
    version     TEXT NOT NULL,
    valid_from  DATE NOT NULL,
    valid_to    DATE,                 -- NULL = 현행
    params_json TEXT,                 -- 산식 파라미터
    applied_in  TEXT,                 -- 적용 모듈·화면
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
