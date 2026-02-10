-- ============================================
-- EWS 선행지표 강화 스키마
-- ============================================
-- 5개 선행 채널: 거래행태, 공적정보, 시장신호, 뉴스감성, 공급망 시계열

-- 1. 거래행태 (자행 거래 데이터 기반)
CREATE TABLE IF NOT EXISTS ews_transaction_behavior (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    reference_month TEXT NOT NULL,        -- YYYY-MM
    avg_balance REAL,                     -- 평잔 (억원)
    limit_utilization REAL,               -- 한도소진율 (0~1)
    payment_delay_days INTEGER DEFAULT 0, -- 결제지연일수
    salary_transfer INTEGER DEFAULT 1,    -- 급여이체 여부 (0/1)
    deposit_outflow_rate REAL,            -- 예금유출률 (0~1)
    transaction_count INTEGER,            -- 월간 거래건수
    overdraft_count INTEGER DEFAULT 0,    -- 당좌대월 발생횟수
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- 2. 공적정보 이벤트
CREATE TABLE IF NOT EXISTS ews_public_registry (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    event_date DATE NOT NULL,
    event_type TEXT NOT NULL,  -- TAX_DELINQUENT, SOCIAL_INSURANCE, SEIZURE, AUDIT_OPINION, MGMT_CHANGE
    severity TEXT NOT NULL,    -- LOW, MEDIUM, HIGH, CRITICAL
    description TEXT,
    amount REAL,               -- 관련 금액 (해당 시)
    resolved INTEGER DEFAULT 0,
    resolved_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- 3. 시장신호 (상장기업만)
CREATE TABLE IF NOT EXISTS ews_market_signal (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    reference_month TEXT NOT NULL,         -- YYYY-MM
    stock_price_change REAL,               -- 주가 변동률 (전월대비)
    cds_spread REAL,                       -- CDS 스프레드 (bp)
    bond_spread REAL,                      -- 채권 스프레드 (bp)
    distance_to_default REAL,              -- 부도거리 (DD)
    implied_pd REAL,                       -- 내재 PD
    market_cap REAL,                       -- 시가총액 (억원)
    volatility_30d REAL,                   -- 30일 변동성
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- 4. 뉴스 개별 기사
CREATE TABLE IF NOT EXISTS ews_news_sentiment (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    publish_date DATE NOT NULL,
    headline TEXT NOT NULL,
    source TEXT,
    sentiment_score REAL,          -- -1.0 ~ +1.0
    category TEXT,                 -- FINANCIAL, LEGAL, OPERATIONAL, MANAGEMENT, INDUSTRY
    relevance_score REAL,          -- 0~1
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- 5. 뉴스 월별 집계
CREATE TABLE IF NOT EXISTS ews_news_sentiment_monthly (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    reference_month TEXT NOT NULL,  -- YYYY-MM
    article_count INTEGER DEFAULT 0,
    avg_sentiment REAL,            -- -1.0 ~ +1.0
    negative_ratio REAL,           -- 부정 기사 비율
    positive_ratio REAL,           -- 긍정 기사 비율
    dominant_category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- 6. 공급망 시계열
CREATE TABLE IF NOT EXISTS ews_supply_chain_temporal (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    partner_id TEXT NOT NULL,
    reference_month TEXT NOT NULL,         -- YYYY-MM
    transaction_amount REAL,               -- 거래금액 (억원)
    transaction_change_rate REAL,          -- 거래변동률 (전월대비)
    payment_status TEXT,                   -- NORMAL, DELAYED, DELINQUENT
    partner_credit_grade TEXT,             -- 거래처 신용등급
    chain_default_probability REAL,        -- 연쇄부도확률
    dependency_ratio REAL,                 -- 거래비중
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
    FOREIGN KEY (partner_id) REFERENCES customer(customer_id)
);

-- ews_composite_score 컬럼 추가
-- SQLite는 ALTER TABLE ADD COLUMN만 지원
-- 이미 있으면 무시됨 (스크립트에서 try/except 처리)

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_ews_txn_cust_month ON ews_transaction_behavior(customer_id, reference_month);
CREATE INDEX IF NOT EXISTS idx_ews_pub_cust ON ews_public_registry(customer_id);
CREATE INDEX IF NOT EXISTS idx_ews_pub_date ON ews_public_registry(event_date);
CREATE INDEX IF NOT EXISTS idx_ews_mkt_cust_month ON ews_market_signal(customer_id, reference_month);
CREATE INDEX IF NOT EXISTS idx_ews_news_cust ON ews_news_sentiment(customer_id);
CREATE INDEX IF NOT EXISTS idx_ews_news_date ON ews_news_sentiment(publish_date);
CREATE INDEX IF NOT EXISTS idx_ews_news_monthly ON ews_news_sentiment_monthly(customer_id, reference_month);
CREATE INDEX IF NOT EXISTS idx_ews_sc_temporal ON ews_supply_chain_temporal(customer_id, reference_month);
