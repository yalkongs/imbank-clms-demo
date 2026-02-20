-- ============================================================
-- iM뱅크 CLMS Phase 3 DB 스키마
-- EWS→Workout 자동화 브릿지 / LGD 백테스트
-- ============================================================

-- ------------------------------------------------------------
-- Module 7: 자동화 액션 (Automation Action)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS automation_action (
    action_id         TEXT PRIMARY KEY,
    -- 트리거 정보
    trigger_type      TEXT NOT NULL,     -- EWS_CRITICAL / COVENANT_EOD / DPD_90 / CUSTOM
    trigger_source_id TEXT,              -- ews_alert.alert_id / covenant_check.check_id 등
    -- 대상
    customer_id       TEXT NOT NULL,
    facility_id       TEXT,
    -- 액션 정보
    action_type       TEXT NOT NULL,     -- CREATE_WORKOUT / NOTIFY_RM / RECLASSIFY / ECL_RECALC / FREEZE_LIMIT
    action_status     TEXT DEFAULT 'PENDING',   -- PENDING / EXECUTED / SKIPPED / FAILED
    priority          TEXT DEFAULT 'NORMAL',    -- LOW / NORMAL / HIGH / CRITICAL
    -- 부실전환 확률 (로지스틱 모델)
    default_probability REAL,           -- P(default_90d)
    -- 실행 결과
    result_summary    TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_at       TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_automation_customer
    ON automation_action(customer_id);
CREATE INDEX IF NOT EXISTS idx_automation_trigger
    ON automation_action(trigger_type);
CREATE INDEX IF NOT EXISTS idx_automation_status
    ON automation_action(action_status);
CREATE INDEX IF NOT EXISTS idx_automation_created
    ON automation_action(created_at);
