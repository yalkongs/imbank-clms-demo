-- ============================================
-- iM뱅크 CLMS 확장 스키마 (8개 신규 기능)
-- ============================================
-- 작성일: 2024-01-30
-- 목적: 고도화 기능 지원을 위한 추가 테이블

-- ============================================
-- 1. 조기경보 시스템 (EWS) 고도화
-- ============================================

-- EWS 선행지표 정의
CREATE TABLE IF NOT EXISTS ews_indicator (
    indicator_id TEXT PRIMARY KEY,
    indicator_name TEXT NOT NULL,
    indicator_type TEXT NOT NULL,  -- FINANCIAL, OPERATIONAL, EXTERNAL, SUPPLY_CHAIN
    category TEXT,  -- LEAD (선행), COINCIDENT (동행), LAG (후행)
    calculation_method TEXT,
    threshold_warning REAL,
    threshold_critical REAL,
    weight REAL DEFAULT 1.0,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- EWS 지표 값 (고객별 시계열)
CREATE TABLE IF NOT EXISTS ews_indicator_value (
    value_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    indicator_id TEXT NOT NULL,
    reference_date DATE NOT NULL,
    value REAL NOT NULL,
    previous_value REAL,
    change_rate REAL,
    trend TEXT,  -- UP, DOWN, STABLE
    signal_level TEXT,  -- NORMAL, WARNING, CRITICAL
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
    FOREIGN KEY (indicator_id) REFERENCES ews_indicator(indicator_id)
);

-- 공급망 관계 (연쇄부도 분석용)
CREATE TABLE IF NOT EXISTS supply_chain_relation (
    relation_id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL,
    buyer_id TEXT NOT NULL,
    relation_type TEXT,  -- SUPPLIER, BUYER, BOTH
    dependency_score REAL,  -- 0~1 (의존도)
    transaction_volume REAL,  -- 연간 거래 규모
    share_of_revenue REAL,  -- 매출 비중
    effective_from DATE,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES customer(customer_id),
    FOREIGN KEY (buyer_id) REFERENCES customer(customer_id)
);

-- EWS 외부 신호 (뉴스, 소송 등)
CREATE TABLE IF NOT EXISTS ews_external_signal (
    signal_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    signal_date DATE NOT NULL,
    signal_type TEXT NOT NULL,  -- NEWS, LAWSUIT, TAX_DELINQUENT, PARTNER_DEFAULT, RATING_DOWNGRADE
    signal_source TEXT,
    severity TEXT,  -- LOW, MEDIUM, HIGH, CRITICAL
    title TEXT,
    description TEXT,
    impact_score REAL,
    verified INTEGER DEFAULT 0,
    action_required INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- 종합 EWS 점수
CREATE TABLE IF NOT EXISTS ews_composite_score (
    score_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    score_date DATE NOT NULL,
    financial_score REAL,
    operational_score REAL,
    external_score REAL,
    supply_chain_score REAL,
    composite_score REAL NOT NULL,
    risk_level TEXT NOT NULL,  -- LOW, MEDIUM, HIGH, CRITICAL
    predicted_default_prob REAL,
    recommendation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- ============================================
-- 2. 동적 한도 관리
-- ============================================

-- 경기 사이클 지표
CREATE TABLE IF NOT EXISTS economic_cycle (
    cycle_id TEXT PRIMARY KEY,
    reference_date DATE NOT NULL,
    cycle_phase TEXT NOT NULL,  -- EXPANSION, PEAK, CONTRACTION, TROUGH
    gdp_growth REAL,
    unemployment_rate REAL,
    interest_rate REAL,
    inflation_rate REAL,
    credit_spread REAL,
    confidence_index REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 동적 한도 규칙
CREATE TABLE IF NOT EXISTS dynamic_limit_rule (
    rule_id TEXT PRIMARY KEY,
    rule_name TEXT NOT NULL,
    rule_type TEXT NOT NULL,  -- CYCLE_BASED, HHI_BASED, DEFAULT_RATE_BASED
    trigger_condition TEXT NOT NULL,
    trigger_threshold REAL,
    action_type TEXT NOT NULL,  -- INCREASE, DECREASE, SUSPEND
    adjustment_pct REAL,
    target_limit_type TEXT,  -- INDUSTRY, SINGLE_BORROWER, RATING
    target_dimension TEXT,
    priority INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 1,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 동적 한도 조정 이력
CREATE TABLE IF NOT EXISTS dynamic_limit_adjustment (
    adjustment_id TEXT PRIMARY KEY,
    rule_id TEXT NOT NULL,
    limit_id TEXT NOT NULL,
    adjustment_date DATE NOT NULL,
    trigger_value REAL,
    previous_limit REAL,
    adjusted_limit REAL,
    adjustment_pct REAL,
    reason TEXT,
    approved_by TEXT,
    status TEXT DEFAULT 'APPLIED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rule_id) REFERENCES dynamic_limit_rule(rule_id),
    FOREIGN KEY (limit_id) REFERENCES limit_definition(limit_id)
);

-- ============================================
-- 3. 고객 관계 기반 수익성 (RBC)
-- ============================================

-- 고객 종합 수익성
CREATE TABLE IF NOT EXISTS customer_profitability (
    profitability_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    calculation_date DATE NOT NULL,
    -- 여신 수익
    loan_revenue REAL DEFAULT 0,
    loan_cost REAL DEFAULT 0,
    loan_el REAL DEFAULT 0,
    loan_capital_cost REAL DEFAULT 0,
    loan_profit REAL DEFAULT 0,
    -- 수신 수익
    deposit_revenue REAL DEFAULT 0,
    deposit_cost REAL DEFAULT 0,
    deposit_profit REAL DEFAULT 0,
    -- 수수료 수익
    fee_revenue REAL DEFAULT 0,
    fee_cost REAL DEFAULT 0,
    fee_profit REAL DEFAULT 0,
    -- 외환/파생 수익
    fx_revenue REAL DEFAULT 0,
    fx_cost REAL DEFAULT 0,
    fx_profit REAL DEFAULT 0,
    -- 종합
    total_revenue REAL DEFAULT 0,
    total_cost REAL DEFAULT 0,
    total_profit REAL DEFAULT 0,
    economic_capital REAL DEFAULT 0,
    raroc REAL,
    -- 생애가치
    clv_score REAL,
    retention_probability REAL,
    cross_sell_potential REAL,
    churn_risk_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- Cross-sell 기회
CREATE TABLE IF NOT EXISTS cross_sell_opportunity (
    opportunity_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    product_type TEXT NOT NULL,
    probability REAL,
    expected_revenue REAL,
    priority_score REAL,
    status TEXT DEFAULT 'OPEN',
    assigned_rm TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- ============================================
-- 4. 담보 가치 실시간 모니터링
-- ============================================

-- 담보 가치 이력
CREATE TABLE IF NOT EXISTS collateral_valuation_history (
    valuation_id TEXT PRIMARY KEY,
    collateral_id TEXT NOT NULL,
    valuation_date DATE NOT NULL,
    valuation_type TEXT,  -- AUTO, MANUAL, REVALUATION
    valuation_source TEXT,
    previous_value REAL,
    current_value REAL,
    change_pct REAL,
    market_condition TEXT,
    ltv_before REAL,
    ltv_after REAL,
    alert_triggered INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (collateral_id) REFERENCES collateral(collateral_id)
);

-- 부동산 시세 인덱스
CREATE TABLE IF NOT EXISTS real_estate_index (
    index_id TEXT PRIMARY KEY,
    reference_date DATE NOT NULL,
    region_code TEXT NOT NULL,
    property_type TEXT NOT NULL,  -- APT, OFFICE, RETAIL, INDUSTRIAL, LAND
    index_value REAL NOT NULL,
    mom_change REAL,  -- 전월비
    yoy_change REAL,  -- 전년비
    volatility_30d REAL,
    forecast_3m REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 담보 경보
CREATE TABLE IF NOT EXISTS collateral_alert (
    alert_id TEXT PRIMARY KEY,
    collateral_id TEXT NOT NULL,
    facility_id TEXT,
    alert_date DATE NOT NULL,
    alert_type TEXT NOT NULL,  -- LTV_BREACH, VALUE_DROP, VOLATILITY_HIGH, MARGIN_CALL
    severity TEXT,
    current_ltv REAL,
    threshold_ltv REAL,
    value_change_pct REAL,
    required_action TEXT,
    status TEXT DEFAULT 'OPEN',
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (collateral_id) REFERENCES collateral(collateral_id)
);

-- ============================================
-- 5. 포트폴리오 최적화
-- ============================================

-- 최적화 실행 이력
CREATE TABLE IF NOT EXISTS portfolio_optimization_run (
    run_id TEXT PRIMARY KEY,
    run_date TIMESTAMP NOT NULL,
    optimization_type TEXT NOT NULL,  -- RAROC_MAX, RWA_MIN, RISK_PARITY
    objective_value REAL,
    constraints_json TEXT,
    input_portfolio_json TEXT,
    optimal_portfolio_json TEXT,
    improvement_pct REAL,
    status TEXT DEFAULT 'COMPLETED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 최적 배분 결과
CREATE TABLE IF NOT EXISTS optimal_allocation (
    allocation_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    segment_type TEXT NOT NULL,
    segment_code TEXT NOT NULL,
    segment_name TEXT,
    current_exposure REAL,
    optimal_exposure REAL,
    change_amount REAL,
    change_pct REAL,
    current_raroc REAL,
    optimal_raroc REAL,
    recommendation TEXT,
    priority INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES portfolio_optimization_run(run_id)
);

-- ============================================
-- 6. Workout 관리
-- ============================================

-- Workout 케이스
CREATE TABLE IF NOT EXISTS workout_case (
    case_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    facility_id TEXT,
    case_open_date DATE NOT NULL,
    case_status TEXT DEFAULT 'OPEN',  -- OPEN, IN_PROGRESS, RESTRUCTURED, LIQUIDATED, RECOVERED, WRITTEN_OFF
    total_exposure REAL,
    secured_amount REAL,
    unsecured_amount REAL,
    provision_amount REAL,
    assigned_workout_officer TEXT,
    strategy TEXT,  -- NORMALIZATION, RESTRUCTURE, SALE, LEGAL_RECOVERY, WRITE_OFF
    expected_recovery_amount REAL,
    expected_recovery_rate REAL,
    expected_recovery_date DATE,
    actual_recovery_amount REAL,
    actual_recovery_rate REAL,
    closed_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- 회수 시나리오
CREATE TABLE IF NOT EXISTS recovery_scenario (
    scenario_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    scenario_name TEXT NOT NULL,
    scenario_type TEXT NOT NULL,  -- NORMALIZATION, RESTRUCTURE, ASSET_SALE, LEGAL_ACTION
    -- 현금흐름 가정
    recovery_amount REAL,
    recovery_timeline_months INTEGER,
    discount_rate REAL,
    npv REAL,
    irr REAL,
    -- 비용
    legal_cost REAL,
    admin_cost REAL,
    opportunity_cost REAL,
    -- 평가
    probability REAL,
    expected_value REAL,
    is_recommended INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES workout_case(case_id)
);

-- 채무조정 이력
CREATE TABLE IF NOT EXISTS debt_restructuring (
    restructure_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    restructure_date DATE NOT NULL,
    original_principal REAL,
    original_rate REAL,
    original_maturity DATE,
    new_principal REAL,
    new_rate REAL,
    new_maturity DATE,
    haircut_amount REAL,
    grace_period_months INTEGER,
    npv_loss REAL,
    approval_level TEXT,
    status TEXT DEFAULT 'APPROVED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES workout_case(case_id)
);

-- ============================================
-- 7. ESG 리스크 통합
-- ============================================

-- ESG 평가
CREATE TABLE IF NOT EXISTS esg_assessment (
    assessment_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    assessment_date DATE NOT NULL,
    -- Environmental
    e_score REAL,
    carbon_intensity REAL,
    energy_efficiency REAL,
    environmental_incidents INTEGER,
    green_revenue_pct REAL,
    -- Social
    s_score REAL,
    employee_safety_score REAL,
    labor_practices_score REAL,
    community_impact_score REAL,
    -- Governance
    g_score REAL,
    board_independence REAL,
    ownership_transparency REAL,
    ethics_compliance_score REAL,
    -- Composite
    esg_score REAL,
    esg_grade TEXT,  -- A, B, C, D, E
    esg_trend TEXT,  -- IMPROVING, STABLE, DECLINING
    pd_adjustment REAL,  -- ESG 기반 PD 가산
    pricing_adjustment_bp REAL,  -- 금리 조정 (bp)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- 녹색금융 상품
CREATE TABLE IF NOT EXISTS green_finance (
    green_id TEXT PRIMARY KEY,
    facility_id TEXT NOT NULL,
    green_category TEXT NOT NULL,  -- GREEN_BOND, SUSTAINABILITY_LINKED, RENEWABLE_ENERGY, GREEN_BUILDING
    certification_type TEXT,
    certification_date DATE,
    kpi_metrics_json TEXT,
    rwa_discount_pct REAL,
    rate_discount_bp REAL,
    verified_by TEXT,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (facility_id) REFERENCES facility(facility_id)
);

-- ============================================
-- 8. 금리 리스크 헷지 분석 (ALM)
-- ============================================

-- 금리 갭 분석
CREATE TABLE IF NOT EXISTS interest_rate_gap (
    gap_id TEXT PRIMARY KEY,
    base_date DATE NOT NULL,
    bucket TEXT NOT NULL,  -- 1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y, 5Y+
    -- 자산
    fixed_rate_assets REAL,
    floating_rate_assets REAL,
    total_assets REAL,
    asset_duration REAL,
    -- 부채
    fixed_rate_liabilities REAL,
    floating_rate_liabilities REAL,
    total_liabilities REAL,
    liability_duration REAL,
    -- 갭
    repricing_gap REAL,
    duration_gap REAL,
    cumulative_gap REAL,
    -- 민감도
    nim_sensitivity_100bp REAL,  -- NIM 변동 (+100bp 시)
    eve_sensitivity_100bp REAL,  -- EVE 변동 (+100bp 시)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 금리 시나리오
CREATE TABLE IF NOT EXISTS interest_rate_scenario (
    scenario_id TEXT PRIMARY KEY,
    scenario_name TEXT NOT NULL,
    scenario_type TEXT,  -- PARALLEL_UP, PARALLEL_DOWN, STEEPENING, FLATTENING, TWIST
    short_rate_shock REAL,  -- 단기 금리 충격 (bp)
    long_rate_shock REAL,   -- 장기 금리 충격 (bp)
    probability REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 금리 시나리오 분석 결과
CREATE TABLE IF NOT EXISTS alm_scenario_result (
    result_id TEXT PRIMARY KEY,
    base_date DATE NOT NULL,
    scenario_id TEXT NOT NULL,
    current_nim REAL,
    stressed_nim REAL,
    nim_change REAL,
    current_eve REAL,
    stressed_eve REAL,
    eve_change REAL,
    eve_change_pct REAL,
    capital_impact REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scenario_id) REFERENCES interest_rate_scenario(scenario_id)
);

-- 헷지 포지션
CREATE TABLE IF NOT EXISTS hedge_position (
    position_id TEXT PRIMARY KEY,
    position_date DATE NOT NULL,
    instrument_type TEXT NOT NULL,  -- IRS, FRA, CAP, FLOOR, SWAPTION
    notional_amount REAL,
    pay_leg TEXT,  -- FIXED, FLOATING
    receive_leg TEXT,
    fixed_rate REAL,
    floating_index TEXT,
    spread REAL,
    maturity_date DATE,
    mtm_value REAL,
    delta REAL,
    dv01 REAL,
    hedge_effectiveness REAL,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 헷지 제안
CREATE TABLE IF NOT EXISTS hedge_recommendation (
    recommendation_id TEXT PRIMARY KEY,
    recommendation_date DATE NOT NULL,
    gap_bucket TEXT,
    current_gap REAL,
    target_gap REAL,
    recommended_instrument TEXT,
    recommended_notional REAL,
    expected_cost REAL,
    expected_benefit REAL,
    priority INTEGER,
    rationale TEXT,
    status TEXT DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 추가 인덱스
-- ============================================
CREATE INDEX IF NOT EXISTS idx_ews_indicator_value_customer ON ews_indicator_value(customer_id, reference_date);
CREATE INDEX IF NOT EXISTS idx_supply_chain_supplier ON supply_chain_relation(supplier_id);
CREATE INDEX IF NOT EXISTS idx_supply_chain_buyer ON supply_chain_relation(buyer_id);
CREATE INDEX IF NOT EXISTS idx_customer_profitability ON customer_profitability(customer_id, calculation_date);
CREATE INDEX IF NOT EXISTS idx_collateral_valuation ON collateral_valuation_history(collateral_id, valuation_date);
CREATE INDEX IF NOT EXISTS idx_workout_case_customer ON workout_case(customer_id);
CREATE INDEX IF NOT EXISTS idx_esg_assessment_customer ON esg_assessment(customer_id);
CREATE INDEX IF NOT EXISTS idx_interest_rate_gap_date ON interest_rate_gap(base_date);
