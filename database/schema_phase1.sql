-- ============================================================
-- iM뱅크 CLMS Phase 1 스키마 확장
-- 여신 심사 고도화: 재무제표 분석, 그룹여신, 코베넌트 관리
-- ============================================================

-- 1. 재무제표 (3개년)
CREATE TABLE IF NOT EXISTS financial_statement (
    stmt_id          TEXT PRIMARY KEY,
    customer_id      TEXT NOT NULL,
    fiscal_year      INTEGER NOT NULL,       -- 회계연도 (2023, 2024, 2025)
    stmt_type        TEXT DEFAULT 'ANNUAL',  -- ANNUAL / INTERIM
    -- 손익계산서
    revenue          REAL,   -- 매출액
    operating_profit REAL,   -- 영업이익
    ebitda           REAL,   -- EBITDA (영업이익 + 감가상각비)
    interest_expense REAL,   -- 이자비용
    net_profit       REAL,   -- 당기순이익
    -- 재무상태표
    total_assets     REAL,   -- 총자산
    current_assets   REAL,   -- 유동자산
    total_debt       REAL,   -- 총부채
    current_debt     REAL,   -- 유동부채
    total_borrowing  REAL,   -- 총차입금 (금융기관 차입만)
    equity           REAL,   -- 자기자본
    retained_earning REAL,   -- 이익잉여금
    working_capital  REAL,   -- 운전자본 (유동자산 - 유동부채)
    -- 현금흐름
    operating_cf     REAL,   -- 영업현금흐름
    -- 메타
    audited          INTEGER DEFAULT 0,  -- 외부감사 여부 (1=감사, 0=비감사)
    source           TEXT,               -- 제출 경로 (KED/DART/직접제출)
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
    UNIQUE(customer_id, fiscal_year, stmt_type)
);

-- 2. 재무비율 캐시 (financial_statement 기반 자동 산출)
CREATE TABLE IF NOT EXISTS financial_ratio (
    ratio_id         TEXT PRIMARY KEY,
    customer_id      TEXT NOT NULL,
    fiscal_year      INTEGER NOT NULL,
    -- 안정성 지표
    debt_ratio       REAL,   -- 부채비율 = 총부채/자기자본×100 (기준: ≤200%)
    current_ratio    REAL,   -- 유동비율 = 유동자산/유동부채×100 (기준: ≥100%)
    ier              REAL,   -- 이자보상배율 = 영업이익/이자비용 (기준: ≥1.5)
    debt_dependency  REAL,   -- 차입금의존도 = 총차입금/총자산×100 (기준: ≤50%)
    -- 현금흐름 지표 (핵심)
    dscr             REAL,   -- DSCR = EBITDA/(원금+이자) (기준: ≥1.25)
    ocf_ratio        REAL,   -- 영업현금흐름비율 = 영업CF/총부채
    -- 수익성 지표
    op_margin        REAL,   -- 영업이익률 = 영업이익/매출×100
    roa              REAL,   -- ROA = 당기순이익/총자산×100
    roe              REAL,   -- ROE = 당기순이익/자기자본×100
    -- 성장성 지표
    revenue_growth   REAL,   -- 매출성장률 YoY (%)
    op_growth        REAL,   -- 영업이익성장률 YoY (%)
    -- 신용위험 스코어
    altman_z         REAL,   -- Altman Z'-Score (비상장 기업용)
    risk_signal      TEXT,   -- SAFE / GREY / DANGER
    calc_date        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
    UNIQUE(customer_id, fiscal_year)
);

-- 3. 계열사 간 보증 관계
CREATE TABLE IF NOT EXISTS group_guarantee (
    guarantee_id     TEXT PRIMARY KEY,
    group_id         TEXT NOT NULL,
    guarantor_id     TEXT NOT NULL,      -- 보증인 (customer_id)
    beneficiary_id   TEXT NOT NULL,      -- 피보증인 (customer_id)
    guarantee_type   TEXT,               -- JOINT(연대보증) / INDIVIDUAL(개인보증) / MORTGAGE(담보제공)
    guarantee_amount REAL,               -- 보증 금액
    effective_date   DATE,
    status           TEXT DEFAULT 'ACTIVE',  -- ACTIVE / EXPIRED / CANCELLED
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES borrower_group(group_id),
    FOREIGN KEY (guarantor_id) REFERENCES customer(customer_id),
    FOREIGN KEY (beneficiary_id) REFERENCES customer(customer_id)
);

-- 4. 코베넌트 정의
CREATE TABLE IF NOT EXISTS covenant (
    covenant_id      TEXT PRIMARY KEY,
    facility_id      TEXT NOT NULL,
    application_id   TEXT,
    -- 분류
    covenant_type    TEXT NOT NULL,    -- FINANCIAL / BEHAVIORAL / INFORMATION
    covenant_code    TEXT NOT NULL,    -- FC01, FC02, BC01, IC01 ...
    covenant_name    TEXT NOT NULL,    -- 코베넌트명
    -- 측정 기준 (재무 코베넌트용)
    metric           TEXT,             -- debt_ratio / dscr / ier / current_ratio / ...
    operator         TEXT,             -- LE(≤) / GE(≥) / EQ(=)
    threshold_value  REAL,             -- 임계값
    -- 점검 주기
    check_frequency  TEXT,             -- MONTHLY / QUARTERLY / SEMI / ANNUAL
    next_check_date  DATE,
    -- 관리
    waiver_count     INTEGER DEFAULT 0,
    status           TEXT DEFAULT 'ACTIVE',  -- ACTIVE / WAIVED / BREACHED / EXPIRED
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (facility_id) REFERENCES facility(facility_id)
);

-- 5. 코베넌트 점검 이력
CREATE TABLE IF NOT EXISTS covenant_check (
    check_id         TEXT PRIMARY KEY,
    covenant_id      TEXT NOT NULL,
    check_date       DATE NOT NULL,
    -- 측정 결과
    actual_value     REAL,             -- 실측값 (재무비율 등)
    threshold_value  REAL,             -- 당시 기준값
    result           TEXT,             -- PASS / BREACH / WAIVED / PENDING
    breach_severity  TEXT,             -- MINOR / MAJOR / EVENT_OF_DEFAULT
    -- 조치
    action_taken     TEXT,
    checked_by       TEXT,
    next_check_date  DATE,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (covenant_id) REFERENCES covenant(covenant_id)
);

-- ============================================================
-- 기존 테이블 컬럼 추가
-- ============================================================

-- borrower_group: 그룹 리스크 지표 추가
-- (SQLite는 IF NOT EXISTS를 지원하지 않으므로 스크립트에서 예외 처리)
ALTER TABLE borrower_group ADD COLUMN group_pd REAL;          -- 그룹 가중평균 PD
ALTER TABLE borrower_group ADD COLUMN group_grade TEXT;        -- 최열위 등급 (그룹 전체 기준)
ALTER TABLE borrower_group ADD COLUMN group_limit_ratio REAL;  -- 자기자본 대비 한도 비율 (%)

-- approval_history: 구조화된 조건 JSON 추가 (기존 conditions TEXT는 유지)
ALTER TABLE approval_history ADD COLUMN conditions_json TEXT;  -- 코베넌트 조건 JSON

-- ============================================================
-- 인덱스 생성
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_financial_statement_customer ON financial_statement(customer_id, fiscal_year);
CREATE INDEX IF NOT EXISTS idx_financial_ratio_customer ON financial_ratio(customer_id, fiscal_year);
CREATE INDEX IF NOT EXISTS idx_group_guarantee_group ON group_guarantee(group_id);
CREATE INDEX IF NOT EXISTS idx_covenant_facility ON covenant(facility_id);
CREATE INDEX IF NOT EXISTS idx_covenant_next_check ON covenant(next_check_date, status);
CREATE INDEX IF NOT EXISTS idx_covenant_check_covenant ON covenant_check(covenant_id, check_date);
