-- ============================================================
-- iM뱅크 CLMS Phase 2 DB 스키마
-- 부실 관리 핵심: 자산건전성 분류 / IFRS9 ECL / 연체 관리
-- ============================================================

-- ------------------------------------------------------------
-- Module 4: 자산건전성 분류 (Asset Classification)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS asset_classification (
    class_id          TEXT PRIMARY KEY,
    facility_id       TEXT NOT NULL,
    customer_id       TEXT NOT NULL,
    base_date         DATE NOT NULL,
    -- 금감원 5단계: NORMAL / PRECAUTIONARY / SUBSTANDARD / DOUBTFUL / LOSS
    classification    TEXT NOT NULL DEFAULT 'NORMAL',
    prev_class        TEXT,
    -- 분류 근거
    dpd               INTEGER DEFAULT 0,
    pd_based_class    TEXT,     -- PD 기준 분류
    ews_based_class   TEXT,     -- EWS 기준 분류
    final_class_basis TEXT,     -- 최종 채택 기준: DPD / PD / EWS / MANUAL
    -- 충당금
    exposure_at_class REAL,
    provision_rate    REAL,
    required_provision REAL,
    existing_provision REAL,
    provision_gap     REAL,     -- 양수: 부족, 음수: 초과
    -- 메타
    classified_by     TEXT DEFAULT 'SYSTEM',
    override_reason   TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(facility_id, base_date)
);

CREATE INDEX IF NOT EXISTS idx_asset_class_facility
    ON asset_classification(facility_id);
CREATE INDEX IF NOT EXISTS idx_asset_class_customer
    ON asset_classification(customer_id);
CREATE INDEX IF NOT EXISTS idx_asset_class_date
    ON asset_classification(base_date);
CREATE INDEX IF NOT EXISTS idx_asset_class_type
    ON asset_classification(classification);

-- facility 테이블 컬럼 추가 (연체 정보)
ALTER TABLE facility ADD COLUMN dpd INTEGER DEFAULT 0;
ALTER TABLE facility ADD COLUMN max_dpd_12m INTEGER DEFAULT 0;
ALTER TABLE facility ADD COLUMN first_delinquency_date DATE;
ALTER TABLE facility ADD COLUMN classification TEXT DEFAULT 'NORMAL';

-- ------------------------------------------------------------
-- Module 5: IFRS 9 ECL 충당금 산출 (Expected Credit Loss)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ecl_calculation (
    ecl_id              TEXT PRIMARY KEY,
    facility_id         TEXT NOT NULL,
    customer_id         TEXT NOT NULL,
    calc_date           DATE NOT NULL,
    -- Stage 분류
    stage               INTEGER NOT NULL,   -- 1, 2, 3
    sicr_triggered      INTEGER DEFAULT 0,  -- SICR 발생 여부 (Stage 2 이상)
    sicr_reason         TEXT,               -- PD_DOUBLED / GRADE_DROP / EWS_WATCH / DPD_30
    -- 파라미터
    pd_original         REAL,    -- 최초 승인 시 PD
    pd_current          REAL,    -- 현재 PD
    lgd                 REAL,
    ead                 REAL,
    remaining_tenor_months INTEGER,
    -- ECL 산출
    ecl_base            REAL,    -- 거시 조정 전 ECL
    macro_adj_factor    REAL DEFAULT 1.0,
    ecl_final           REAL,
    -- 전기 비교
    prev_ecl            REAL,
    ecl_change          REAL,    -- ecl_final - prev_ecl
    -- 충당금 대비
    existing_provision  REAL,
    provision_gap       REAL,    -- ecl_final - existing_provision
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(facility_id, calc_date)
);

CREATE INDEX IF NOT EXISTS idx_ecl_facility
    ON ecl_calculation(facility_id);
CREATE INDEX IF NOT EXISTS idx_ecl_customer
    ON ecl_calculation(customer_id);
CREATE INDEX IF NOT EXISTS idx_ecl_date
    ON ecl_calculation(calc_date);
CREATE INDEX IF NOT EXISTS idx_ecl_stage
    ON ecl_calculation(stage);

-- ------------------------------------------------------------
-- Module 6: 연체 관리 (Delinquency Management)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS delinquency_record (
    delinquency_id    TEXT PRIMARY KEY,
    facility_id       TEXT NOT NULL,
    customer_id       TEXT NOT NULL,
    overdue_date      DATE NOT NULL,       -- 최초 연체 발생일
    overdue_amount    REAL NOT NULL,
    overdue_type      TEXT,                -- PRINCIPAL / INTEREST / BOTH
    dpd               INTEGER DEFAULT 0,   -- Days Past Due (현재)
    resolved_date     DATE,
    resolved_amount   REAL,
    resolution_type   TEXT,               -- PAID / RESTRUCTURED / WORKOUT / WRITEOFF
    status            TEXT DEFAULT 'OPEN', -- OPEN / RESOLVED / WORKOUT
    -- DPD 단계: EARLY(1-30) / MID(31-60) / LATE(61-90) / NPL(91-180) / WRITEOFF(181+)
    delinquency_stage TEXT,
    assigned_officer  TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_delinquency_facility
    ON delinquency_record(facility_id);
CREATE INDEX IF NOT EXISTS idx_delinquency_customer
    ON delinquency_record(customer_id);
CREATE INDEX IF NOT EXISTS idx_delinquency_status
    ON delinquency_record(status);
CREATE INDEX IF NOT EXISTS idx_delinquency_stage
    ON delinquency_record(delinquency_stage);

CREATE TABLE IF NOT EXISTS collection_activity (
    activity_id     TEXT PRIMARY KEY,
    delinquency_id  TEXT NOT NULL,
    facility_id     TEXT NOT NULL,
    activity_date   DATE NOT NULL,
    -- CALL / LETTER / VISIT / SMS / EMAIL / LEGAL_NOTICE
    activity_type   TEXT NOT NULL,
    -- REACHED / NO_ANSWER / PROMISE_TO_PAY / REFUSED / LEFT_MESSAGE
    contact_result  TEXT,
    promised_date   DATE,
    promised_amount REAL,
    notes           TEXT,
    officer         TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_collection_delinquency
    ON collection_activity(delinquency_id);
CREATE INDEX IF NOT EXISTS idx_collection_facility
    ON collection_activity(facility_id);
CREATE INDEX IF NOT EXISTS idx_collection_date
    ON collection_activity(activity_date);
