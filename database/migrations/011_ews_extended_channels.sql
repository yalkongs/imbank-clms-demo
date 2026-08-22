-- EWS 8채널 확장 (docs/EWS_8CHANNEL_DESIGN_2026-08-21.md Phase 1)
-- 신규 채널: 카드매출(CARD_SALES) · 고용(EMPLOYMENT) · 상거래연체(B2B_DELINQ)

-- 원천 3종
CREATE TABLE IF NOT EXISTS ews_card_sales_monthly (
    record_id   TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    month       TEXT NOT NULL,              -- YYYY-MM
    card_sales_amount    REAL,
    active_merchant_days INTEGER,
    mom_change_pct       REAL,
    yoy_change_pct       REAL,
    industry_percentile  REAL,              -- 동업종 대비 상대 위치 (상권·계절 효과 분리)
    UNIQUE(customer_id, month)
);
CREATE TABLE IF NOT EXISTS ews_employment_monthly (
    record_id   TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    month       TEXT NOT NULL,
    insured_count          INTEGER,
    insured_change_3m      INTEGER,
    premium_arrears_months INTEGER DEFAULT 0,
    UNIQUE(customer_id, month)
);
CREATE TABLE IF NOT EXISTS ews_b2b_delinquency (
    event_id    TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    event_date  DATE NOT NULL,
    counterparty_count INTEGER DEFAULT 1,
    overdue_amount     REAL,
    overdue_days       INTEGER,
    event_type  TEXT,                       -- PAYMENT_DELAY | NOTE_EXTENSION | COMMERCIAL_DEFAULT
    resolved_date DATE
);
CREATE INDEX IF NOT EXISTS ix_b2b_cust ON ews_b2b_delinquency(customer_id, event_date);

-- 월별 채널 점수 (8채널 공통 - 선행성 백테스트의 원장)
CREATE TABLE IF NOT EXISTS ews_channel_score_monthly (
    customer_id TEXT NOT NULL,
    month       TEXT NOT NULL,
    channel     TEXT NOT NULL,
    score       REAL NOT NULL,
    PRIMARY KEY (customer_id, month, channel)
);

-- 동의 관리 (신용정보법 §32·§33) - 만료 채널은 자동 결측 전환
CREATE TABLE IF NOT EXISTS ews_channel_consent (
    consent_id  TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    channel     TEXT NOT NULL,
    legal_basis TEXT,                       -- 신용정보법 동의 | 마이데이터 | CB집중(동의불요)
    consent_date DATE,
    expiry_date  DATE,
    status      TEXT NOT NULL DEFAULT 'ACTIVE',   -- ACTIVE | EXPIRED | WITHDRAWN
    UNIQUE(customer_id, channel)
);

-- 종합점수 테이블에 신규 채널 점수·커버리지 컬럼
ALTER TABLE ews_composite_score ADD COLUMN card_sales_score REAL;
ALTER TABLE ews_composite_score ADD COLUMN employment_score REAL;
ALTER TABLE ews_composite_score ADD COLUMN b2b_delinq_score REAL;
ALTER TABLE ews_composite_score ADD COLUMN channel_coverage TEXT;   -- JSON {channel: OK|MISSING|NO_CONSENT|CONSENT_EXPIRED}

-- 검증 지표에 오경보율 (탐지율과 반드시 쌍으로 봐야 하는 지표)
ALTER TABLE ews_validation_metrics ADD COLUMN false_alarm_rate_pct REAL;

-- 채널 가중치 규정 정본 (생성기 하드코딩 → rule_register 이관)
-- 변경은 가중치 승인 API(부서장 이상 + 감사기록)로만 새 버전 발효
INSERT OR IGNORE INTO rule_register
    (rule_id, domain, name, basis, version, valid_from, params_json, applied_in)
VALUES (
    'RULE_EWS_WEIGHTS', 'EWS', 'EWS 채널 가중치 (세그먼트별)',
    '내부 모형 거버넌스 - 채널 선행성 백테스트 근거',
    'v3.0 (8채널)', '2026-08-22',
    '{"LISTED":{"transaction":0.20,"card_sales":0.0,"b2b_delinq":0.10,"employment":0.05,"public":0.10,"market":0.15,"news":0.10,"supply":0.15,"financial":0.15},'
    || '"UNLISTED":{"transaction":0.20,"card_sales":0.05,"b2b_delinq":0.15,"employment":0.10,"public":0.15,"market":0.0,"news":0.10,"supply":0.10,"financial":0.15},'
    || '"SOHO":{"transaction":0.20,"card_sales":0.20,"b2b_delinq":0.10,"employment":0.05,"public":0.10,"market":0.0,"news":0.05,"supply":0.05,"financial":0.25}}',
    'services/ews_channels.py recompute_composite'
);
