-- ============================================
-- iM뱅크 CLMS 데모 데이터베이스 스키마
-- ============================================

-- 1. 마스터 테이블
-- ============================================

-- 고객 마스터
CREATE TABLE IF NOT EXISTS customer (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    customer_name_eng TEXT,
    biz_reg_no TEXT UNIQUE NOT NULL,
    corp_reg_no TEXT,
    establish_date DATE,
    industry_code TEXT NOT NULL,
    industry_name TEXT,
    size_category TEXT CHECK(size_category IN ('LARGE','MEDIUM','SMALL','SOHO')),
    asset_size REAL,
    revenue_size REAL,
    employee_count INTEGER,
    listing_status TEXT,
    address TEXT,
    region TEXT,
    rm_id TEXT,
    branch_code TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 차주그룹
CREATE TABLE IF NOT EXISTS borrower_group (
    group_id TEXT PRIMARY KEY,
    group_name TEXT NOT NULL,
    group_type TEXT,
    parent_company_id TEXT,
    total_exposure REAL DEFAULT 0,
    group_limit REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 그룹 멤버
CREATE TABLE IF NOT EXISTS borrower_group_member (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    relationship_type TEXT,
    ownership_pct REAL,
    FOREIGN KEY (group_id) REFERENCES borrower_group(group_id),
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- 산업 마스터
CREATE TABLE IF NOT EXISTS industry_master (
    industry_code TEXT PRIMARY KEY,
    industry_name TEXT NOT NULL,
    industry_large TEXT,
    industry_medium TEXT,
    risk_grade TEXT,
    outlook TEXT
);

-- 상품 마스터
CREATE TABLE IF NOT EXISTS product_master (
    product_code TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    product_type TEXT,
    risk_category TEXT,
    is_active INTEGER DEFAULT 1
);

-- 2. 운영계층 테이블
-- ============================================

-- 여신신청
CREATE TABLE IF NOT EXISTS loan_application (
    application_id TEXT PRIMARY KEY,
    application_date DATE NOT NULL,
    application_type TEXT,
    customer_id TEXT NOT NULL,
    group_id TEXT,
    product_code TEXT NOT NULL,
    requested_amount REAL NOT NULL,
    requested_tenor INTEGER,
    requested_rate REAL,
    purpose_code TEXT,
    purpose_detail TEXT,
    collateral_type TEXT,
    collateral_value REAL,
    guarantee_type TEXT,
    status TEXT DEFAULT 'RECEIVED',
    current_stage TEXT,
    priority TEXT DEFAULT 'NORMAL',
    assigned_to TEXT,
    branch_code TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
    FOREIGN KEY (product_code) REFERENCES product_master(product_code)
);

-- 신용등급 결과
CREATE TABLE IF NOT EXISTS credit_rating_result (
    rating_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    application_id TEXT,
    rating_date DATE NOT NULL,
    model_id TEXT,
    model_version TEXT,
    raw_score REAL,
    final_grade TEXT NOT NULL,
    grade_notch INTEGER,
    pd_value REAL NOT NULL,
    override_grade TEXT,
    override_reason TEXT,
    override_by TEXT,
    effective_from DATE,
    effective_to DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- 리스크 파라미터
CREATE TABLE IF NOT EXISTS risk_parameter (
    param_id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    calc_date DATE NOT NULL,
    ttc_pd REAL NOT NULL,
    pit_pd REAL,
    lgd REAL NOT NULL,
    ead REAL NOT NULL,
    ccf REAL,
    maturity_years REAL,
    rwa REAL,
    expected_loss REAL,
    unexpected_loss REAL,
    economic_capital REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES loan_application(application_id)
);

-- 담보
CREATE TABLE IF NOT EXISTS collateral (
    collateral_id TEXT PRIMARY KEY,
    application_id TEXT,
    facility_id TEXT,
    collateral_type TEXT NOT NULL,
    collateral_subtype TEXT,
    original_value REAL,
    current_value REAL,
    ltv REAL,
    valuation_date DATE,
    priority_rank INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 여신약정 (Facility)
CREATE TABLE IF NOT EXISTS facility (
    facility_id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    facility_type TEXT,
    product_code TEXT,
    currency_code TEXT DEFAULT 'KRW',
    approved_amount REAL NOT NULL,
    current_limit REAL,
    outstanding_amount REAL DEFAULT 0,
    available_amount REAL,
    rate_type TEXT,
    base_rate_code TEXT,
    spread REAL,
    final_rate REAL,
    contract_date DATE,
    maturity_date DATE,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- 승인 이력
CREATE TABLE IF NOT EXISTS approval_history (
    approval_id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    approval_level TEXT,
    approver_id TEXT,
    approver_name TEXT,
    decision TEXT,
    conditions TEXT,
    comments TEXT,
    decided_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES loan_application(application_id)
);

-- EWS 경보
CREATE TABLE IF NOT EXISTS ews_alert (
    alert_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    facility_id TEXT,
    alert_date DATE NOT NULL,
    alert_type TEXT NOT NULL,
    alert_subtype TEXT,
    severity TEXT,
    indicator_value REAL,
    threshold_value REAL,
    description TEXT,
    status TEXT DEFAULT 'OPEN',
    action_taken TEXT,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- 3. 전술계층 테이블
-- ============================================

-- FTP 금리
CREATE TABLE IF NOT EXISTS ftp_rate (
    ftp_id TEXT PRIMARY KEY,
    effective_date DATE NOT NULL,
    currency_code TEXT DEFAULT 'KRW',
    tenor_months INTEGER NOT NULL,
    base_ftp_rate REAL NOT NULL,
    liquidity_premium REAL DEFAULT 0,
    term_premium REAL DEFAULT 0,
    final_ftp_rate REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 신용스프레드
CREATE TABLE IF NOT EXISTS credit_spread (
    spread_id TEXT PRIMARY KEY,
    effective_date DATE NOT NULL,
    rating_grade TEXT NOT NULL,
    secured_type TEXT NOT NULL,
    tenor_bucket TEXT,
    base_spread REAL NOT NULL,
    el_spread REAL,
    ul_spread REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 가격결정 결과
CREATE TABLE IF NOT EXISTS pricing_result (
    pricing_id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    pricing_date DATE NOT NULL,
    pricing_version INTEGER DEFAULT 1,
    base_rate REAL NOT NULL,
    ftp_spread REAL NOT NULL,
    credit_spread REAL NOT NULL,
    capital_spread REAL NOT NULL,
    opex_spread REAL NOT NULL,
    target_margin REAL,
    strategy_adj REAL DEFAULT 0,
    contribution_adj REAL DEFAULT 0,
    collateral_adj REAL DEFAULT 0,
    competitive_adj REAL DEFAULT 0,
    system_rate REAL NOT NULL,
    proposed_rate REAL,
    final_rate REAL,
    expected_revenue REAL,
    expected_raroc REAL,
    expected_rorwa REAL,
    hurdle_rate REAL,
    raroc_status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES loan_application(application_id)
);

-- 거시경제 지표
CREATE TABLE IF NOT EXISTS macro_indicator (
    indicator_id TEXT PRIMARY KEY,
    indicator_name TEXT NOT NULL,
    indicator_type TEXT,
    source TEXT,
    frequency TEXT,
    unit TEXT
);

-- 거시지표 값
CREATE TABLE IF NOT EXISTS macro_indicator_value (
    value_id TEXT PRIMARY KEY,
    indicator_id TEXT NOT NULL,
    reference_date DATE NOT NULL,
    value REAL NOT NULL,
    previous_value REAL,
    change_rate REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (indicator_id) REFERENCES macro_indicator(indicator_id)
);

-- PIT 조정계수
CREATE TABLE IF NOT EXISTS macro_adjustment_factor (
    factor_id TEXT PRIMARY KEY,
    effective_date DATE NOT NULL,
    segment_type TEXT,
    segment_code TEXT,
    adjustment_factor REAL NOT NULL,
    gdp_sensitivity REAL,
    unemp_sensitivity REAL,
    rate_sensitivity REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. 전략계층 테이블
-- ============================================

-- 자본 포지션
CREATE TABLE IF NOT EXISTS capital_position (
    position_id TEXT PRIMARY KEY,
    base_date DATE NOT NULL,
    cet1_capital REAL,
    at1_capital REAL,
    tier2_capital REAL,
    total_capital REAL,
    credit_rwa REAL,
    market_rwa REAL,
    operational_rwa REAL,
    total_rwa REAL,
    bis_ratio REAL,
    cet1_ratio REAL,
    tier1_ratio REAL,
    leverage_ratio REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 자본예산
CREATE TABLE IF NOT EXISTS capital_budget (
    budget_id TEXT PRIMARY KEY,
    budget_year TEXT NOT NULL,
    budget_quarter TEXT,
    segment_type TEXT NOT NULL,
    segment_code TEXT NOT NULL,
    segment_name TEXT,
    rwa_budget REAL,
    el_budget REAL,
    revenue_target REAL,
    rwa_used REAL DEFAULT 0,
    el_used REAL DEFAULT 0,
    revenue_actual REAL DEFAULT 0,
    raroc_target REAL,
    rorwa_target REAL,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 포트폴리오 전략
CREATE TABLE IF NOT EXISTS portfolio_strategy (
    strategy_id TEXT PRIMARY KEY,
    effective_from DATE NOT NULL,
    effective_to DATE,
    dimension_type TEXT NOT NULL,
    dimension_code TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    new_deal_allowed INTEGER DEFAULT 1,
    max_single_exposure REAL,
    pricing_adjustment REAL DEFAULT 0,
    ltv_cap REAL,
    tenor_cap INTEGER,
    approval_level TEXT,
    special_condition TEXT,
    rationale TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 산업-등급 전략 매트릭스
CREATE TABLE IF NOT EXISTS industry_rating_strategy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    industry_code TEXT NOT NULL,
    industry_name TEXT,
    rating_bucket TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    pricing_adj_bp REAL DEFAULT 0,
    effective_from DATE,
    UNIQUE(industry_code, rating_bucket, effective_from)
);

-- 한도 정의
CREATE TABLE IF NOT EXISTS limit_definition (
    limit_id TEXT PRIMARY KEY,
    limit_name TEXT NOT NULL,
    limit_type TEXT NOT NULL,
    dimension_type TEXT NOT NULL,
    dimension_code TEXT,
    limit_amount REAL NOT NULL,
    limit_unit TEXT NOT NULL,
    base_amount REAL,
    warning_level REAL DEFAULT 80,
    alert_level REAL DEFAULT 90,
    critical_level REAL DEFAULT 95,
    effective_from DATE,
    effective_to DATE,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 한도 사용현황
CREATE TABLE IF NOT EXISTS limit_exposure (
    exposure_id TEXT PRIMARY KEY,
    limit_id TEXT NOT NULL,
    base_date DATE NOT NULL,
    exposure_amount REAL NOT NULL,
    reserved_amount REAL DEFAULT 0,
    available_amount REAL,
    utilization_rate REAL,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (limit_id) REFERENCES limit_definition(limit_id)
);

-- 한도 예약
CREATE TABLE IF NOT EXISTS limit_reservation (
    reservation_id TEXT PRIMARY KEY,
    limit_id TEXT NOT NULL,
    application_id TEXT NOT NULL,
    reserved_amount REAL NOT NULL,
    reserved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    status TEXT DEFAULT 'ACTIVE',
    FOREIGN KEY (limit_id) REFERENCES limit_definition(limit_id)
);

-- 스트레스 시나리오
CREATE TABLE IF NOT EXISTS stress_scenario (
    scenario_id TEXT PRIMARY KEY,
    scenario_name TEXT NOT NULL,
    scenario_type TEXT,
    severity_level TEXT,
    gdp_growth_shock REAL,
    unemployment_shock REAL,
    interest_rate_shock REAL,
    housing_price_shock REAL,
    stock_price_shock REAL,
    fx_rate_shock REAL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 스트레스테스트 결과
CREATE TABLE IF NOT EXISTS stress_test_result (
    result_id TEXT PRIMARY KEY,
    scenario_id TEXT NOT NULL,
    test_date DATE NOT NULL,
    horizon_months INTEGER,
    portfolio_ead REAL,
    stressed_pd REAL,
    stressed_lgd REAL,
    expected_loss REAL,
    unexpected_loss REAL,
    stressed_rwa REAL,
    stressed_bis_ratio REAL,
    stressed_cet1_ratio REAL,
    capital_shortfall REAL,
    segment_detail_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scenario_id) REFERENCES stress_scenario(scenario_id)
);

-- 5. 기반계층 테이블
-- ============================================

-- 모델 레지스트리
CREATE TABLE IF NOT EXISTS model_registry (
    model_id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    model_type TEXT,
    model_purpose TEXT,
    risk_tier TEXT,
    development_date DATE,
    last_validation_date DATE,
    next_validation_date DATE,
    status TEXT DEFAULT 'ACTIVE',
    owner_dept TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 모델 버전
CREATE TABLE IF NOT EXISTS model_version (
    version_id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    version_no TEXT NOT NULL,
    deployment_env TEXT,
    effective_from DATE,
    effective_to DATE,
    performance_metrics TEXT,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_id) REFERENCES model_registry(model_id)
);

-- 모델 성능 로그
CREATE TABLE IF NOT EXISTS model_performance_log (
    log_id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    version_id TEXT,
    monitoring_date DATE NOT NULL,
    segment_type TEXT,
    segment_code TEXT,
    gini_coefficient REAL,
    ks_statistic REAL,
    auroc REAL,
    psi REAL,
    csi REAL,
    predicted_dr REAL,
    actual_dr REAL,
    ar_ratio REAL,
    alert_triggered INTEGER DEFAULT 0,
    alert_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_id) REFERENCES model_registry(model_id)
);

-- Override 모니터링
CREATE TABLE IF NOT EXISTS override_monitoring (
    override_id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    override_type TEXT,
    override_date DATE NOT NULL,
    system_value TEXT,
    override_value TEXT,
    override_direction TEXT,
    notch_change INTEGER,
    override_reason_code TEXT,
    override_reason_text TEXT,
    override_by TEXT,
    approved_by TEXT,
    outcome_date DATE,
    outcome_status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Decision Snapshot
CREATE TABLE IF NOT EXISTS decision_snapshot (
    snapshot_id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    snapshot_timestamp TIMESTAMP NOT NULL,
    snapshot_type TEXT,
    input_data_json TEXT,
    rating_model_id TEXT,
    rating_model_version TEXT,
    output_data_json TEXT,
    feature_values_json TEXT,
    parameters_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 감사 로그
CREATE TABLE IF NOT EXISTS audit_log (
    log_id TEXT PRIMARY KEY,
    log_timestamp TIMESTAMP NOT NULL,
    user_id TEXT NOT NULL,
    user_dept TEXT,
    action_type TEXT NOT NULL,
    target_entity TEXT NOT NULL,
    target_id TEXT,
    before_value TEXT,
    after_value TEXT,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Hurdle Rate
CREATE TABLE IF NOT EXISTS hurdle_rate (
    rate_id TEXT PRIMARY KEY,
    effective_date DATE NOT NULL,
    segment_type TEXT,
    segment_code TEXT,
    hurdle_raroc REAL NOT NULL,
    target_raroc REAL,
    calc_method TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 포트폴리오 현황 (집계)
CREATE TABLE IF NOT EXISTS portfolio_summary (
    summary_id TEXT PRIMARY KEY,
    base_date DATE NOT NULL,
    segment_type TEXT NOT NULL,
    segment_code TEXT NOT NULL,
    segment_name TEXT,
    exposure_count INTEGER,
    total_exposure REAL,
    total_rwa REAL,
    total_el REAL,
    avg_pd REAL,
    avg_lgd REAL,
    weighted_rate REAL,
    total_revenue REAL,
    raroc REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_customer_industry ON customer(industry_code);
CREATE INDEX IF NOT EXISTS idx_customer_size ON customer(size_category);
CREATE INDEX IF NOT EXISTS idx_customer_region ON customer(region);
CREATE INDEX IF NOT EXISTS idx_application_customer ON loan_application(customer_id);
CREATE INDEX IF NOT EXISTS idx_application_status ON loan_application(status);
CREATE INDEX IF NOT EXISTS idx_application_date ON loan_application(application_date);
CREATE INDEX IF NOT EXISTS idx_rating_customer ON credit_rating_result(customer_id);
CREATE INDEX IF NOT EXISTS idx_facility_customer ON facility(customer_id);
CREATE INDEX IF NOT EXISTS idx_facility_status ON facility(status);
