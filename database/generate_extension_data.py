#!/usr/bin/env python3
"""
iM뱅크 CLMS - 확장 기능 데이터 생성 스크립트
============================================
8개 신규 기능을 위한 테스트 데이터 생성

1. EWS 고도화
2. 동적 한도 관리
3. 고객 관계 기반 수익성 (RBC)
4. 담보 가치 실시간 모니터링
5. 포트폴리오 최적화
6. Workout 관리
7. ESG 리스크 통합
8. 금리 리스크 헷지 분석 (ALM)
"""

import sqlite3
import random
from datetime import datetime, timedelta
import uuid
import json
import math

DB_PATH = '/Users/yalkongs/code/Projects/imbank-clms-demo/database/imbank_demo.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def generate_uuid():
    return str(uuid.uuid4())[:8].upper()

def random_date(start_year=2023, end_year=2024):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    random_days = random.randint(0, delta.days)
    return (start + timedelta(days=random_days)).strftime('%Y-%m-%d')

def execute_schema_extension(conn):
    """스키마 확장 SQL 실행"""
    with open('/Users/yalkongs/code/Projects/imbank-clms-demo/database/schema_extension.sql', 'r') as f:
        sql = f.read()
    cursor = conn.cursor()
    cursor.executescript(sql)
    conn.commit()
    print("✓ 스키마 확장 완료")

# ============================================
# 1. EWS 고도화 데이터
# ============================================

def generate_ews_indicators(conn):
    """EWS 선행지표 정의"""
    cursor = conn.cursor()

    indicators = [
        ('EWS_IND_001', '매출채권회전일', 'FINANCIAL', 'LEAD', 'AR_DAYS = 매출채권 / 일평균매출', 60, 90, 1.2, '매출채권 회수 기간 - 증가 시 유동성 위험'),
        ('EWS_IND_002', '재고자산회전율', 'FINANCIAL', 'LEAD', 'INV_TURN = 매출원가 / 평균재고', 4, 2, 1.0, '재고 효율성 - 하락 시 판매 부진'),
        ('EWS_IND_003', '현금흐름커버리지', 'FINANCIAL', 'COINCIDENT', 'CFO / 단기차입금', 1.5, 0.8, 1.5, '영업현금흐름의 단기채무 상환 능력'),
        ('EWS_IND_004', '이자보상배율', 'FINANCIAL', 'COINCIDENT', 'EBIT / 이자비용', 3, 1.5, 1.3, '영업이익의 이자 지급 능력'),
        ('EWS_IND_005', '순운전자본비율', 'FINANCIAL', 'LEAD', '(유동자산-유동부채) / 총자산', 0.1, -0.05, 1.0, '단기 유동성 상태'),
        ('EWS_IND_006', '부채비율변화', 'FINANCIAL', 'LEAD', '(당기부채비율-전기부채비율) / 전기부채비율', 0.15, 0.30, 1.1, '레버리지 급증 징후'),
        ('EWS_IND_007', '거래처부도영향도', 'SUPPLY_CHAIN', 'LEAD', 'Σ(거래비중 × 거래처PD)', 0.02, 0.05, 1.4, '공급망 연쇄부도 위험'),
        ('EWS_IND_008', '외부신용등급변화', 'EXTERNAL', 'COINCIDENT', '외부 신용평가사 등급 변동', -1, -2, 1.5, '외부 신용평가 하향 조정'),
        ('EWS_IND_009', '뉴스심리지수', 'EXTERNAL', 'LEAD', 'NLP 기반 뉴스 감성 분석', -0.3, -0.6, 0.8, '부정적 언론 보도 증가'),
        ('EWS_IND_010', '연체발생여부', 'OPERATIONAL', 'LAG', '30일 이상 연체 발생', 0, 1, 2.0, '실제 연체 발생 (후행지표)'),
    ]

    for ind in indicators:
        cursor.execute("""
            INSERT OR REPLACE INTO ews_indicator
            (indicator_id, indicator_name, indicator_type, category, calculation_method,
             threshold_warning, threshold_critical, weight, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ind)

    conn.commit()
    print(f"✓ EWS 선행지표: {len(indicators)}건 생성")
    return [ind[0] for ind in indicators]

def generate_ews_indicator_values(conn, indicator_ids):
    """EWS 지표 값 생성"""
    cursor = conn.cursor()
    cursor.execute("SELECT customer_id FROM customer LIMIT 200")
    customers = [row[0] for row in cursor.fetchall()]

    count = 0
    for customer_id in customers:
        for indicator_id in indicator_ids:
            # 최근 6개월 데이터 생성
            for month_offset in range(6):
                date = (datetime.now() - timedelta(days=30*month_offset)).strftime('%Y-%m-%d')

                # 지표별 값 범위 설정
                if 'IND_001' in indicator_id:  # 매출채권회전일
                    value = random.uniform(30, 120)
                    threshold = 60
                elif 'IND_002' in indicator_id:  # 재고자산회전율
                    value = random.uniform(1, 10)
                    threshold = 4
                elif 'IND_003' in indicator_id:  # 현금흐름커버리지
                    value = random.uniform(0.3, 3.0)
                    threshold = 1.5
                elif 'IND_004' in indicator_id:  # 이자보상배율
                    value = random.uniform(0.5, 8.0)
                    threshold = 3
                elif 'IND_007' in indicator_id:  # 거래처부도영향도
                    value = random.uniform(0.001, 0.08)
                    threshold = 0.02
                elif 'IND_009' in indicator_id:  # 뉴스심리지수
                    value = random.uniform(-0.8, 0.5)
                    threshold = -0.3
                else:
                    value = random.uniform(0, 1)
                    threshold = 0.5

                prev_value = value * random.uniform(0.85, 1.15)
                change_rate = (value - prev_value) / prev_value if prev_value != 0 else 0

                # 신호 레벨 결정
                if 'IND_002' in indicator_id or 'IND_003' in indicator_id or 'IND_004' in indicator_id:
                    # 높을수록 좋은 지표
                    signal = 'CRITICAL' if value < threshold * 0.5 else 'WARNING' if value < threshold else 'NORMAL'
                else:
                    # 낮을수록 좋은 지표
                    signal = 'CRITICAL' if value > threshold * 1.5 else 'WARNING' if value > threshold else 'NORMAL'

                trend = 'UP' if change_rate > 0.05 else 'DOWN' if change_rate < -0.05 else 'STABLE'

                cursor.execute("""
                    INSERT INTO ews_indicator_value
                    (value_id, customer_id, indicator_id, reference_date, value,
                     previous_value, change_rate, trend, signal_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (f"EIV_{generate_uuid()}", customer_id, indicator_id, date,
                      round(value, 4), round(prev_value, 4), round(change_rate, 4), trend, signal))
                count += 1

    conn.commit()
    print(f"✓ EWS 지표 값: {count}건 생성")

def generate_supply_chain_relations(conn):
    """공급망 관계 데이터 생성"""
    cursor = conn.cursor()
    cursor.execute("SELECT customer_id FROM customer")
    customers = [row[0] for row in cursor.fetchall()]

    relations = []
    for _ in range(500):
        supplier = random.choice(customers)
        buyer = random.choice(customers)
        if supplier != buyer:
            relations.append((
                f"SCR_{generate_uuid()}",
                supplier,
                buyer,
                random.choice(['SUPPLIER', 'BUYER']),
                round(random.uniform(0.1, 0.9), 2),
                random.randint(100000000, 50000000000),
                round(random.uniform(0.01, 0.3), 2),
                '2023-01-01',
                'ACTIVE'
            ))

    cursor.executemany("""
        INSERT OR IGNORE INTO supply_chain_relation
        (relation_id, supplier_id, buyer_id, relation_type, dependency_score,
         transaction_volume, share_of_revenue, effective_from, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, relations)

    conn.commit()
    print(f"✓ 공급망 관계: {len(relations)}건 생성")

def generate_external_signals(conn):
    """외부 신호 데이터 생성"""
    cursor = conn.cursor()
    cursor.execute("SELECT customer_id, customer_name FROM customer")
    customers = cursor.fetchall()

    signal_types = [
        ('NEWS', '부정적 뉴스 보도', ['재무상태 악화 우려', '소송 제기', '경영진 교체', '주가 급락', '회계 의혹']),
        ('LAWSUIT', '소송 관련', ['손해배상 소송', '특허 분쟁', '노동 분쟁', '공정거래법 위반']),
        ('TAX_DELINQUENT', '세금 체납', ['법인세 체납', '부가세 체납', '원천세 체납']),
        ('PARTNER_DEFAULT', '거래처 부도', ['주요 매출처 부도', '협력업체 워크아웃']),
        ('RATING_DOWNGRADE', '신용등급 하향', ['외부 신용등급 1노치 하향', '외부 신용등급 2노치 하향'])
    ]

    signals = []
    for _ in range(300):
        customer = random.choice(customers)
        signal_type = random.choice(signal_types)
        severity = random.choices(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'], weights=[30, 40, 20, 10])[0]

        signals.append((
            f"EXT_{generate_uuid()}",
            customer[0],
            random_date(2023, 2024),
            signal_type[0],
            random.choice(['뉴스', '공시', '신용정보', '관계사']),
            severity,
            f"{customer[1]} {random.choice(signal_type[2])}",
            signal_type[1],
            round(random.uniform(0.1, 1.0), 2),
            random.randint(0, 1),
            1 if severity in ['HIGH', 'CRITICAL'] else 0
        ))

    cursor.executemany("""
        INSERT INTO ews_external_signal
        (signal_id, customer_id, signal_date, signal_type, signal_source, severity,
         title, description, impact_score, verified, action_required)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, signals)

    conn.commit()
    print(f"✓ 외부 신호: {len(signals)}건 생성")

def generate_composite_scores(conn):
    """종합 EWS 점수 생성"""
    cursor = conn.cursor()
    cursor.execute("SELECT customer_id FROM customer")
    customers = [row[0] for row in cursor.fetchall()]

    scores = []
    for customer_id in customers:
        financial = round(random.uniform(0, 100), 1)
        operational = round(random.uniform(0, 100), 1)
        external = round(random.uniform(0, 100), 1)
        supply_chain = round(random.uniform(0, 100), 1)
        composite = round(financial * 0.4 + operational * 0.2 + external * 0.2 + supply_chain * 0.2, 1)

        risk_level = 'LOW' if composite >= 70 else 'MEDIUM' if composite >= 50 else 'HIGH' if composite >= 30 else 'CRITICAL'

        recommendations = {
            'LOW': '정기 모니터링 유지',
            'MEDIUM': '모니터링 주기 단축 권고',
            'HIGH': '워치리스트 편입 검토',
            'CRITICAL': '긴급 현장 실사 및 여신 회수 검토'
        }

        scores.append((
            f"ECS_{generate_uuid()}",
            customer_id,
            datetime.now().strftime('%Y-%m-%d'),
            financial,
            operational,
            external,
            supply_chain,
            composite,
            risk_level,
            round(random.uniform(0.001, 0.15), 4),
            recommendations[risk_level]
        ))

    cursor.executemany("""
        INSERT OR REPLACE INTO ews_composite_score
        (score_id, customer_id, score_date, financial_score, operational_score,
         external_score, supply_chain_score, composite_score, risk_level,
         predicted_default_prob, recommendation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, scores)

    conn.commit()
    print(f"✓ 종합 EWS 점수: {len(scores)}건 생성")

# ============================================
# 2. 동적 한도 관리 데이터
# ============================================

def generate_economic_cycle(conn):
    """경기 사이클 지표 생성"""
    cursor = conn.cursor()

    cycles = []
    phases = ['EXPANSION', 'PEAK', 'CONTRACTION', 'TROUGH']

    for month_offset in range(24):
        date = (datetime.now() - timedelta(days=30*month_offset)).strftime('%Y-%m-%d')
        phase_idx = (month_offset // 6) % 4
        phase = phases[phase_idx]

        gdp = 2.5 + random.uniform(-1, 1) + (1 if phase == 'EXPANSION' else -1 if phase == 'CONTRACTION' else 0)
        unemployment = 3.5 + random.uniform(-0.5, 0.5) + (-0.5 if phase == 'EXPANSION' else 0.5 if phase == 'CONTRACTION' else 0)
        interest = 3.5 + random.uniform(-0.3, 0.3) + (0.5 if phase == 'PEAK' else -0.5 if phase == 'TROUGH' else 0)

        cycles.append((
            f"EC_{generate_uuid()}",
            date,
            phase,
            round(gdp, 2),
            round(unemployment, 2),
            round(interest, 2),
            round(2.5 + random.uniform(-0.5, 0.5), 2),
            round(100 + random.uniform(-30, 30), 1),
            round(95 + random.uniform(-15, 15), 1)
        ))

    cursor.executemany("""
        INSERT INTO economic_cycle
        (cycle_id, reference_date, cycle_phase, gdp_growth, unemployment_rate,
         interest_rate, inflation_rate, credit_spread, confidence_index)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, cycles)

    conn.commit()
    print(f"✓ 경기 사이클: {len(cycles)}건 생성")

def generate_dynamic_limit_rules(conn):
    """동적 한도 규칙 생성"""
    cursor = conn.cursor()

    rules = [
        ('DLR_001', '경기 침체기 고위험 업종 한도 축소', 'CYCLE_BASED', 'cycle_phase == CONTRACTION', None, 'DECREASE', -15, 'INDUSTRY', 'HIGH_RISK', 1, 1, '경기 침체 시 고위험 업종 한도 15% 자동 축소'),
        ('DLR_002', '경기 확장기 성장 업종 한도 확대', 'CYCLE_BASED', 'cycle_phase == EXPANSION', None, 'INCREASE', 10, 'INDUSTRY', 'GROWTH', 2, 1, '경기 확장기 성장 업종 한도 10% 자동 확대'),
        ('DLR_003', '업종 HHI 경보 시 한도 동결', 'HHI_BASED', 'industry_hhi > threshold', 0.25, 'SUSPEND', 0, 'INDUSTRY', None, 1, 1, '업종 집중도 25% 초과 시 신규 한도 동결'),
        ('DLR_004', '업종 부도율 급등 시 한도 축소', 'DEFAULT_RATE_BASED', 'industry_default_rate > threshold', 0.03, 'DECREASE', -20, 'INDUSTRY', None, 1, 1, '업종 부도율 3% 초과 시 한도 20% 축소'),
        ('DLR_005', '금리 급등기 변동금리 한도 제한', 'CYCLE_BASED', 'interest_rate_change > 1%', 1.0, 'DECREASE', -10, 'SINGLE_BORROWER', 'FLOATING_RATE', 2, 1, '금리 급등 시 변동금리 여신 한도 제한'),
        ('DLR_006', '특정 등급 부도율 초과 시 축소', 'DEFAULT_RATE_BASED', 'rating_default_rate > threshold', 0.05, 'DECREASE', -25, 'RATING', 'BB_BELOW', 1, 1, 'BB 이하 등급 부도율 5% 초과 시 한도 25% 축소'),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO dynamic_limit_rule
        (rule_id, rule_name, rule_type, trigger_condition, trigger_threshold,
         action_type, adjustment_pct, target_limit_type, target_dimension, priority, is_active, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rules)

    conn.commit()
    print(f"✓ 동적 한도 규칙: {len(rules)}건 생성")

def generate_dynamic_limit_adjustments(conn):
    """동적 한도 조정 이력 생성"""
    cursor = conn.cursor()

    # 기존 한도 ID 조회
    cursor.execute("SELECT limit_id, limit_amount FROM limit_definition LIMIT 10")
    limits = cursor.fetchall()

    adjustments = []
    for limit_id, limit_amount in limits:
        for _ in range(random.randint(1, 3)):
            adj_pct = random.choice([-20, -15, -10, 10, 15])
            prev_limit = limit_amount * random.uniform(0.9, 1.1)
            new_limit = prev_limit * (1 + adj_pct / 100)

            adjustments.append((
                f"DLA_{generate_uuid()}",
                random.choice(['DLR_001', 'DLR_002', 'DLR_003', 'DLR_004']),
                limit_id,
                random_date(2023, 2024),
                round(random.uniform(0.2, 0.35), 3),
                round(prev_limit, 0),
                round(new_limit, 0),
                adj_pct,
                '경기 사이클 변화에 따른 자동 조정',
                '시스템',
                'APPLIED'
            ))

    cursor.executemany("""
        INSERT INTO dynamic_limit_adjustment
        (adjustment_id, rule_id, limit_id, adjustment_date, trigger_value,
         previous_limit, adjusted_limit, adjustment_pct, reason, approved_by, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, adjustments)

    conn.commit()
    print(f"✓ 동적 한도 조정 이력: {len(adjustments)}건 생성")

# ============================================
# 3. 고객 관계 기반 수익성 (RBC)
# ============================================

def generate_customer_profitability(conn):
    """고객 종합 수익성 데이터 생성"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.customer_id, c.size_category,
               COALESCE(SUM(f.outstanding_amount), 0) as total_loan
        FROM customer c
        LEFT JOIN facility f ON c.customer_id = f.customer_id AND f.status = 'ACTIVE'
        GROUP BY c.customer_id
    """)
    customers = cursor.fetchall()

    profitability_data = []
    for customer_id, size_category, total_loan in customers:
        # 규모에 따른 기본값 설정
        multiplier = {'LARGE': 5, 'MEDIUM': 2, 'SMALL': 1, 'SOHO': 0.5}.get(size_category, 1)

        # 여신 수익/비용
        loan_revenue = total_loan * random.uniform(0.03, 0.06) if total_loan > 0 else random.uniform(10000000, 100000000) * multiplier
        loan_cost = loan_revenue * random.uniform(0.3, 0.5)
        loan_el = total_loan * random.uniform(0.005, 0.02) if total_loan > 0 else 0
        loan_capital_cost = total_loan * random.uniform(0.01, 0.02) if total_loan > 0 else 0
        loan_profit = loan_revenue - loan_cost - loan_el - loan_capital_cost

        # 수신 수익/비용
        deposit_revenue = random.uniform(5000000, 50000000) * multiplier
        deposit_cost = deposit_revenue * random.uniform(0.4, 0.6)
        deposit_profit = deposit_revenue - deposit_cost

        # 수수료 수익
        fee_revenue = random.uniform(1000000, 20000000) * multiplier
        fee_cost = fee_revenue * random.uniform(0.1, 0.3)
        fee_profit = fee_revenue - fee_cost

        # 외환/파생 수익
        fx_revenue = random.uniform(500000, 10000000) * multiplier if random.random() > 0.5 else 0
        fx_cost = fx_revenue * random.uniform(0.2, 0.4)
        fx_profit = fx_revenue - fx_cost

        # 종합
        total_revenue = loan_revenue + deposit_revenue + fee_revenue + fx_revenue
        total_cost = loan_cost + deposit_cost + fee_cost + fx_cost + loan_el + loan_capital_cost
        total_profit = total_revenue - total_cost

        economic_capital = max(total_loan * random.uniform(0.06, 0.12), 1000000)
        raroc = (total_profit / economic_capital * 100) if economic_capital > 0 else 0

        # 생애가치 지표
        clv_score = round(random.uniform(30, 100), 1)
        retention_prob = round(random.uniform(0.6, 0.98), 2)
        cross_sell = round(random.uniform(0.1, 0.8), 2)
        churn_risk = round(1 - retention_prob + random.uniform(-0.1, 0.1), 2)

        profitability_data.append((
            f"CP_{generate_uuid()}",
            customer_id,
            datetime.now().strftime('%Y-%m-%d'),
            round(loan_revenue, 0),
            round(loan_cost, 0),
            round(loan_el, 0),
            round(loan_capital_cost, 0),
            round(loan_profit, 0),
            round(deposit_revenue, 0),
            round(deposit_cost, 0),
            round(deposit_profit, 0),
            round(fee_revenue, 0),
            round(fee_cost, 0),
            round(fee_profit, 0),
            round(fx_revenue, 0),
            round(fx_cost, 0),
            round(fx_profit, 0),
            round(total_revenue, 0),
            round(total_cost, 0),
            round(total_profit, 0),
            round(economic_capital, 0),
            round(raroc, 2),
            clv_score,
            retention_prob,
            cross_sell,
            max(0, min(1, churn_risk))
        ))

    cursor.executemany("""
        INSERT OR REPLACE INTO customer_profitability
        (profitability_id, customer_id, calculation_date,
         loan_revenue, loan_cost, loan_el, loan_capital_cost, loan_profit,
         deposit_revenue, deposit_cost, deposit_profit,
         fee_revenue, fee_cost, fee_profit,
         fx_revenue, fx_cost, fx_profit,
         total_revenue, total_cost, total_profit,
         economic_capital, raroc, clv_score, retention_probability, cross_sell_potential, churn_risk_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, profitability_data)

    conn.commit()
    print(f"✓ 고객 수익성: {len(profitability_data)}건 생성")

def generate_cross_sell_opportunities(conn):
    """Cross-sell 기회 생성"""
    cursor = conn.cursor()
    cursor.execute("SELECT customer_id FROM customer")
    customers = [row[0] for row in cursor.fetchall()]

    products = ['수신상품', '외환거래', '파생상품', '무역금융', 'PF', '채권인수', '현금관리', '퇴직연금']

    opportunities = []
    for customer_id in random.sample(customers, min(200, len(customers))):
        for product in random.sample(products, random.randint(1, 3)):
            probability = round(random.uniform(0.2, 0.9), 2)
            expected_revenue = random.randint(1000000, 100000000)
            priority = round(probability * expected_revenue / 10000000, 1)

            opportunities.append((
                f"CSO_{generate_uuid()}",
                customer_id,
                product,
                probability,
                expected_revenue,
                priority,
                'OPEN',
                f"RM{random.randint(100, 999)}"
            ))

    cursor.executemany("""
        INSERT INTO cross_sell_opportunity
        (opportunity_id, customer_id, product_type, probability, expected_revenue, priority_score, status, assigned_rm)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, opportunities)

    conn.commit()
    print(f"✓ Cross-sell 기회: {len(opportunities)}건 생성")

# ============================================
# 4. 담보 가치 실시간 모니터링
# ============================================

def generate_real_estate_index(conn):
    """부동산 시세 인덱스 생성"""
    cursor = conn.cursor()

    regions = ['SEOUL', 'BUSAN', 'DAEGU', 'INCHEON', 'GWANGJU', 'DAEJEON', 'GYEONGGI', 'GANGWON']
    property_types = ['APT', 'OFFICE', 'RETAIL', 'INDUSTRIAL', 'LAND']

    indices = []
    for region in regions:
        for prop_type in property_types:
            base_index = 100
            for month_offset in range(12):
                date = (datetime.now() - timedelta(days=30*month_offset)).strftime('%Y-%m-%d')

                # 지역/유형별 변동성 차이
                volatility = 0.02 if region == 'SEOUL' else 0.03 if region == 'GYEONGGI' else 0.04
                mom_change = random.uniform(-volatility, volatility)

                index_value = base_index * (1 + mom_change)
                base_index = index_value

                indices.append((
                    f"REI_{generate_uuid()}",
                    date,
                    region,
                    prop_type,
                    round(index_value, 2),
                    round(mom_change * 100, 2),
                    round((index_value - 100) / 100 * 100, 2),
                    round(volatility * 100, 2),
                    round(index_value * (1 + random.uniform(-0.05, 0.05)), 2)
                ))

    cursor.executemany("""
        INSERT INTO real_estate_index
        (index_id, reference_date, region_code, property_type, index_value,
         mom_change, yoy_change, volatility_30d, forecast_3m)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, indices)

    conn.commit()
    print(f"✓ 부동산 시세 인덱스: {len(indices)}건 생성")

def generate_collateral_valuations(conn):
    """담보 가치 이력 생성"""
    cursor = conn.cursor()
    cursor.execute("SELECT collateral_id, current_value FROM collateral")
    collaterals = cursor.fetchall()

    valuations = []
    alerts = []

    for collateral_id, current_value in collaterals:
        if current_value is None or current_value <= 0:
            continue

        base_value = current_value
        for month_offset in range(6):
            date = (datetime.now() - timedelta(days=30*month_offset)).strftime('%Y-%m-%d')

            change_pct = random.uniform(-0.1, 0.05)
            new_value = base_value * (1 + change_pct)

            ltv_before = random.uniform(0.4, 0.8)
            ltv_after = ltv_before * (1 + change_pct * 0.5)

            alert_triggered = 1 if change_pct < -0.05 or ltv_after > 0.8 else 0

            valuations.append((
                f"CVH_{generate_uuid()}",
                collateral_id,
                date,
                random.choice(['AUTO', 'MANUAL']),
                random.choice(['시세연동', '감정평가', '공시지가']),
                round(base_value, 0),
                round(new_value, 0),
                round(change_pct * 100, 2),
                random.choice(['상승', '보합', '하락']),
                round(ltv_before, 3),
                round(ltv_after, 3),
                alert_triggered
            ))

            if alert_triggered:
                alert_type = 'LTV_BREACH' if ltv_after > 0.8 else 'VALUE_DROP'
                alerts.append((
                    f"CAL_{generate_uuid()}",
                    collateral_id,
                    None,
                    date,
                    alert_type,
                    'HIGH' if ltv_after > 0.9 else 'MEDIUM',
                    round(ltv_after, 3),
                    0.8 if alert_type == 'LTV_BREACH' else None,
                    round(change_pct * 100, 2),
                    '추가담보 징구 검토' if ltv_after > 0.8 else '모니터링 강화',
                    random.choice(['OPEN', 'IN_PROGRESS', 'RESOLVED'])
                ))

            base_value = new_value

    cursor.executemany("""
        INSERT INTO collateral_valuation_history
        (valuation_id, collateral_id, valuation_date, valuation_type, valuation_source,
         previous_value, current_value, change_pct, market_condition, ltv_before, ltv_after, alert_triggered)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, valuations)

    cursor.executemany("""
        INSERT INTO collateral_alert
        (alert_id, collateral_id, facility_id, alert_date, alert_type, severity,
         current_ltv, threshold_ltv, value_change_pct, required_action, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, alerts)

    conn.commit()
    print(f"✓ 담보 가치 이력: {len(valuations)}건, 경보: {len(alerts)}건 생성")

# ============================================
# 5. 포트폴리오 최적화
# ============================================

def generate_portfolio_optimization(conn):
    """포트폴리오 최적화 결과 생성"""
    cursor = conn.cursor()

    # 최적화 실행
    runs = []
    allocations = []

    industries = [
        ('MFG001', '반도체'), ('MFG003', '2차전지'), ('MFG009', '의약품'),
        ('SVC001', 'IT서비스'), ('SVC003', '플랫폼'), ('CON001', '종합건설'),
        ('REA001', '부동산개발'), ('FIN001', '캐피탈')
    ]

    for i in range(5):
        run_id = f"OPT_{generate_uuid()}"
        run_date = (datetime.now() - timedelta(days=30*i)).strftime('%Y-%m-%d %H:%M:%S')

        current_portfolio = {}
        optimal_portfolio = {}

        for code, name in industries:
            current_exp = random.uniform(100, 500) * 1e9
            optimal_exp = current_exp * random.uniform(0.8, 1.2)
            current_raroc = random.uniform(10, 25)
            optimal_raroc = current_raroc * random.uniform(1.0, 1.15)

            current_portfolio[code] = current_exp
            optimal_portfolio[code] = optimal_exp

            change_amount = optimal_exp - current_exp
            recommendation = '확대' if change_amount > 0 else '축소' if change_amount < 0 else '유지'

            allocations.append((
                f"OA_{generate_uuid()}",
                run_id,
                'INDUSTRY',
                code,
                name,
                round(current_exp, 0),
                round(optimal_exp, 0),
                round(change_amount, 0),
                round(change_amount / current_exp * 100, 2),
                round(current_raroc, 2),
                round(optimal_raroc, 2),
                recommendation,
                random.randint(1, 5)
            ))

        total_improvement = random.uniform(5, 15)

        runs.append((
            run_id,
            run_date,
            random.choice(['RAROC_MAX', 'RWA_MIN', 'RISK_PARITY']),
            round(random.uniform(15, 20), 2),
            json.dumps({'bis_min': 0.11, 'hhi_max': 0.25, 'single_max': 0.1}),
            json.dumps(current_portfolio),
            json.dumps(optimal_portfolio),
            round(total_improvement, 2),
            'COMPLETED'
        ))

    cursor.executemany("""
        INSERT INTO portfolio_optimization_run
        (run_id, run_date, optimization_type, objective_value, constraints_json,
         input_portfolio_json, optimal_portfolio_json, improvement_pct, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, runs)

    cursor.executemany("""
        INSERT INTO optimal_allocation
        (allocation_id, run_id, segment_type, segment_code, segment_name,
         current_exposure, optimal_exposure, change_amount, change_pct,
         current_raroc, optimal_raroc, recommendation, priority)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, allocations)

    conn.commit()
    print(f"✓ 포트폴리오 최적화: {len(runs)}건 실행, {len(allocations)}건 배분")

# ============================================
# 6. Workout 관리
# ============================================

def generate_workout_data(conn):
    """Workout 케이스 및 시나리오 생성"""
    cursor = conn.cursor()

    # 일부 고객을 Workout 대상으로 선정
    cursor.execute("""
        SELECT c.customer_id, c.customer_name, SUM(f.outstanding_amount) as exposure
        FROM customer c
        JOIN facility f ON c.customer_id = f.customer_id
        GROUP BY c.customer_id
        HAVING exposure > 10000000000
        ORDER BY RANDOM()
        LIMIT 30
    """)
    workout_candidates = cursor.fetchall()

    cases = []
    scenarios = []
    restructurings = []

    statuses = ['OPEN', 'IN_PROGRESS', 'RESTRUCTURED', 'LIQUIDATED', 'RECOVERED', 'WRITTEN_OFF']
    strategies = ['NORMALIZATION', 'RESTRUCTURE', 'SALE', 'LEGAL_RECOVERY', 'WRITE_OFF']

    for customer_id, customer_name, exposure in workout_candidates:
        case_id = f"WO_{generate_uuid()}"
        status = random.choices(statuses, weights=[20, 30, 25, 10, 10, 5])[0]
        strategy = random.choice(strategies)

        secured = exposure * random.uniform(0.3, 0.7)
        unsecured = exposure - secured
        provision = exposure * random.uniform(0.2, 0.6)

        expected_recovery_rate = random.uniform(0.3, 0.8)
        actual_recovery_rate = expected_recovery_rate * random.uniform(0.8, 1.2) if status in ['RECOVERED', 'LIQUIDATED'] else None

        cases.append((
            case_id,
            customer_id,
            None,
            random_date(2022, 2024),
            status,
            round(exposure, 0),
            round(secured, 0),
            round(unsecured, 0),
            round(provision, 0),
            f"WO_OFFICER_{random.randint(1, 10)}",
            strategy,
            round(exposure * expected_recovery_rate, 0),
            round(expected_recovery_rate, 3),
            (datetime.now() + timedelta(days=random.randint(90, 365))).strftime('%Y-%m-%d'),
            round(exposure * actual_recovery_rate, 0) if actual_recovery_rate else None,
            round(actual_recovery_rate, 3) if actual_recovery_rate else None,
            random_date(2023, 2024) if status in ['RECOVERED', 'LIQUIDATED', 'WRITTEN_OFF'] else None
        ))

        # 회수 시나리오 생성
        scenario_types = [
            ('NORMALIZATION', '정상화', 0.85, 24),
            ('RESTRUCTURE', '채무조정', 0.65, 36),
            ('ASSET_SALE', '자산매각', 0.50, 12),
            ('LEGAL_ACTION', '법적회수', 0.35, 48)
        ]

        for sc_type, sc_name, base_recovery, timeline in scenario_types:
            recovery_rate = base_recovery * random.uniform(0.8, 1.2)
            recovery_amount = exposure * recovery_rate

            discount_rate = 0.08
            npv = recovery_amount / ((1 + discount_rate) ** (timeline / 12))

            legal_cost = exposure * 0.02 if sc_type == 'LEGAL_ACTION' else exposure * 0.005
            admin_cost = exposure * 0.01

            scenarios.append((
                f"RS_{generate_uuid()}",
                case_id,
                f"{sc_name} 시나리오",
                sc_type,
                round(recovery_amount, 0),
                timeline,
                discount_rate,
                round(npv, 0),
                round(random.uniform(0.05, 0.25), 3),
                round(legal_cost, 0),
                round(admin_cost, 0),
                round(exposure * 0.01, 0),
                round(random.uniform(0.1, 0.4), 2),
                round(npv * random.uniform(0.1, 0.4), 0),
                1 if sc_type == strategy else 0
            ))

        # 채무조정 이력 (일부 케이스)
        if status == 'RESTRUCTURED':
            original_rate = random.uniform(0.04, 0.08)
            new_rate = original_rate * random.uniform(0.5, 0.8)
            haircut = exposure * random.uniform(0, 0.3)

            restructurings.append((
                f"DR_{generate_uuid()}",
                case_id,
                random_date(2023, 2024),
                round(exposure, 0),
                round(original_rate, 4),
                (datetime.now() + timedelta(days=random.randint(30, 365))).strftime('%Y-%m-%d'),
                round(exposure - haircut, 0),
                round(new_rate, 4),
                (datetime.now() + timedelta(days=random.randint(365, 1825))).strftime('%Y-%m-%d'),
                round(haircut, 0),
                random.randint(0, 12),
                round(haircut + (exposure * (original_rate - new_rate) * 3), 0),
                random.choice(['BRANCH', 'CREDIT_DEPT', 'EXECUTIVE']),
                'APPROVED'
            ))

    cursor.executemany("""
        INSERT INTO workout_case
        (case_id, customer_id, facility_id, case_open_date, case_status, total_exposure,
         secured_amount, unsecured_amount, provision_amount, assigned_workout_officer,
         strategy, expected_recovery_amount, expected_recovery_rate, expected_recovery_date,
         actual_recovery_amount, actual_recovery_rate, closed_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, cases)

    cursor.executemany("""
        INSERT INTO recovery_scenario
        (scenario_id, case_id, scenario_name, scenario_type, recovery_amount,
         recovery_timeline_months, discount_rate, npv, irr, legal_cost, admin_cost,
         opportunity_cost, probability, expected_value, is_recommended)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, scenarios)

    cursor.executemany("""
        INSERT INTO debt_restructuring
        (restructure_id, case_id, restructure_date, original_principal, original_rate,
         original_maturity, new_principal, new_rate, new_maturity, haircut_amount,
         grace_period_months, npv_loss, approval_level, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, restructurings)

    conn.commit()
    print(f"✓ Workout 케이스: {len(cases)}건, 시나리오: {len(scenarios)}건, 조정: {len(restructurings)}건 생성")

# ============================================
# 7. ESG 리스크 통합
# ============================================

def generate_esg_data(conn):
    """ESG 평가 데이터 생성"""
    cursor = conn.cursor()
    cursor.execute("SELECT customer_id, industry_code FROM customer")
    customers = cursor.fetchall()

    # 업종별 ESG 기본 점수 (제조업은 E 낮음, 서비스업은 높음 등)
    industry_esg_bias = {
        'MFG': {'e': -10, 's': 0, 'g': 5},
        'SVC': {'e': 10, 's': 5, 'g': 5},
        'CON': {'e': -15, 's': -5, 'g': 0},
        'REA': {'e': -5, 's': 0, 'g': -5},
        'FIN': {'e': 5, 's': 0, 'g': 10},
        'ENE': {'e': 15, 's': 0, 'g': 0}
    }

    esg_grades = ['A', 'B', 'C', 'D', 'E']

    assessments = []
    green_finances = []

    for customer_id, industry_code in customers:
        industry_prefix = industry_code[:3] if industry_code else 'SVC'
        bias = industry_esg_bias.get(industry_prefix, {'e': 0, 's': 0, 'g': 0})

        # Environmental
        e_score = min(100, max(0, 50 + bias['e'] + random.uniform(-20, 20)))
        carbon_intensity = random.uniform(10, 500) if industry_prefix in ['MFG', 'CON', 'ENE'] else random.uniform(1, 50)

        # Social
        s_score = min(100, max(0, 60 + bias['s'] + random.uniform(-15, 15)))

        # Governance
        g_score = min(100, max(0, 65 + bias['g'] + random.uniform(-10, 10)))

        # Composite
        esg_score = round(e_score * 0.35 + s_score * 0.30 + g_score * 0.35, 1)

        if esg_score >= 80:
            esg_grade = 'A'
            pd_adj = -0.002
            pricing_adj = -10
        elif esg_score >= 65:
            esg_grade = 'B'
            pd_adj = -0.001
            pricing_adj = -5
        elif esg_score >= 50:
            esg_grade = 'C'
            pd_adj = 0
            pricing_adj = 0
        elif esg_score >= 35:
            esg_grade = 'D'
            pd_adj = 0.002
            pricing_adj = 10
        else:
            esg_grade = 'E'
            pd_adj = 0.005
            pricing_adj = 25

        assessments.append((
            f"ESG_{generate_uuid()}",
            customer_id,
            datetime.now().strftime('%Y-%m-%d'),
            round(e_score, 1),
            round(carbon_intensity, 1),
            round(random.uniform(0.3, 0.9), 2),
            random.randint(0, 5),
            round(random.uniform(0, 0.3), 2) if industry_prefix == 'ENE' else round(random.uniform(0, 0.1), 2),
            round(s_score, 1),
            round(random.uniform(60, 100), 1),
            round(random.uniform(50, 100), 1),
            round(random.uniform(40, 90), 1),
            round(g_score, 1),
            round(random.uniform(0.3, 0.8), 2),
            round(random.uniform(0.5, 1.0), 2),
            round(random.uniform(60, 100), 1),
            esg_score,
            esg_grade,
            random.choice(['IMPROVING', 'STABLE', 'DECLINING']),
            pd_adj,
            pricing_adj
        ))

    cursor.executemany("""
        INSERT OR REPLACE INTO esg_assessment
        (assessment_id, customer_id, assessment_date,
         e_score, carbon_intensity, energy_efficiency, environmental_incidents, green_revenue_pct,
         s_score, employee_safety_score, labor_practices_score, community_impact_score,
         g_score, board_independence, ownership_transparency, ethics_compliance_score,
         esg_score, esg_grade, esg_trend, pd_adjustment, pricing_adjustment_bp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, assessments)

    # 녹색금융 상품 (일부 시설)
    cursor.execute("SELECT facility_id FROM facility WHERE status = 'ACTIVE' ORDER BY RANDOM() LIMIT 50")
    facilities = [row[0] for row in cursor.fetchall()]

    green_categories = ['GREEN_BOND', 'SUSTAINABILITY_LINKED', 'RENEWABLE_ENERGY', 'GREEN_BUILDING']

    for facility_id in facilities:
        green_finances.append((
            f"GF_{generate_uuid()}",
            facility_id,
            random.choice(green_categories),
            random.choice(['KLIMAT_BOND', 'GRI', 'CDP', 'ISO14001']),
            random_date(2023, 2024),
            json.dumps({'carbon_reduction': f"{random.randint(10, 50)}%", 'energy_efficiency': f"{random.randint(15, 40)}%"}),
            round(random.uniform(0, 15), 1),
            round(random.uniform(5, 25), 0),
            random.choice(['Internal', 'External Auditor', 'Third Party']),
            'ACTIVE'
        ))

    cursor.executemany("""
        INSERT INTO green_finance
        (green_id, facility_id, green_category, certification_type, certification_date,
         kpi_metrics_json, rwa_discount_pct, rate_discount_bp, verified_by, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, green_finances)

    conn.commit()
    print(f"✓ ESG 평가: {len(assessments)}건, 녹색금융: {len(green_finances)}건 생성")

# ============================================
# 8. 금리 리스크 헷지 분석 (ALM)
# ============================================

def generate_alm_data(conn):
    """ALM 데이터 생성"""
    cursor = conn.cursor()

    # 금리 갭 분석
    buckets = ['1M', '3M', '6M', '1Y', '2Y', '3Y', '5Y', '5Y+']
    gaps = []

    total_assets = 50000 * 1e9  # 50조
    total_liabilities = 45000 * 1e9  # 45조

    cumulative_gap = 0
    for i, bucket in enumerate(buckets):
        bucket_pct = [0.15, 0.15, 0.15, 0.20, 0.15, 0.10, 0.05, 0.05][i]

        fixed_assets = total_assets * bucket_pct * random.uniform(0.3, 0.5)
        floating_assets = total_assets * bucket_pct * random.uniform(0.5, 0.7)
        bucket_assets = fixed_assets + floating_assets

        fixed_liab = total_liabilities * bucket_pct * random.uniform(0.4, 0.6)
        floating_liab = total_liabilities * bucket_pct * random.uniform(0.4, 0.6)
        bucket_liab = fixed_liab + floating_liab

        repricing_gap = floating_assets - floating_liab
        cumulative_gap += repricing_gap

        asset_duration = [0.08, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0][i]
        liab_duration = asset_duration * random.uniform(0.85, 1.15)
        duration_gap = asset_duration - liab_duration

        nim_sens = repricing_gap * 0.0001 / 1e9  # 100bp당 NIM 변동 (십억원)
        eve_sens = -duration_gap * bucket_assets * 0.01 / 1e9

        gaps.append((
            f"IRG_{generate_uuid()}",
            datetime.now().strftime('%Y-%m-%d'),
            bucket,
            round(fixed_assets, 0),
            round(floating_assets, 0),
            round(bucket_assets, 0),
            round(asset_duration, 2),
            round(fixed_liab, 0),
            round(floating_liab, 0),
            round(bucket_liab, 0),
            round(liab_duration, 2),
            round(repricing_gap, 0),
            round(duration_gap, 2),
            round(cumulative_gap, 0),
            round(nim_sens, 2),
            round(eve_sens, 2)
        ))

    cursor.executemany("""
        INSERT INTO interest_rate_gap
        (gap_id, base_date, bucket, fixed_rate_assets, floating_rate_assets, total_assets,
         asset_duration, fixed_rate_liabilities, floating_rate_liabilities, total_liabilities,
         liability_duration, repricing_gap, duration_gap, cumulative_gap, nim_sensitivity_100bp, eve_sensitivity_100bp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, gaps)

    # 금리 시나리오
    scenarios = [
        ('IRS_001', '평행 상승 100bp', 'PARALLEL_UP', 100, 100, 0.25),
        ('IRS_002', '평행 하락 100bp', 'PARALLEL_DOWN', -100, -100, 0.20),
        ('IRS_003', '평행 상승 200bp', 'PARALLEL_UP', 200, 200, 0.15),
        ('IRS_004', '평행 하락 200bp', 'PARALLEL_DOWN', -200, -200, 0.10),
        ('IRS_005', '스티프닝 (단기↓장기↑)', 'STEEPENING', -50, 100, 0.15),
        ('IRS_006', '플래트닝 (단기↑장기↓)', 'FLATTENING', 100, -50, 0.10),
        ('IRS_007', '트위스트 (역전)', 'TWIST', 150, -100, 0.05)
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO interest_rate_scenario
        (scenario_id, scenario_name, scenario_type, short_rate_shock, long_rate_shock, probability)
        VALUES (?, ?, ?, ?, ?, ?)
    """, scenarios)

    # 시나리오 분석 결과
    results = []
    current_nim = 1.85  # 1.85%
    current_eve = 4500 * 1e9  # 4.5조

    for scenario in scenarios:
        scenario_id = scenario[0]
        short_shock = scenario[3]
        long_shock = scenario[4]

        avg_shock = (short_shock + long_shock) / 2
        nim_change = avg_shock * 0.002  # 100bp당 약 20bp NIM 변동
        stressed_nim = current_nim + nim_change / 100

        eve_change = -avg_shock * 0.003 * current_eve / 100  # 100bp당 약 0.3% EVE 변동
        stressed_eve = current_eve + eve_change

        results.append((
            f"ASR_{generate_uuid()}",
            datetime.now().strftime('%Y-%m-%d'),
            scenario_id,
            current_nim,
            round(stressed_nim, 4),
            round(nim_change / 100, 4),
            round(current_eve, 0),
            round(stressed_eve, 0),
            round(eve_change, 0),
            round(eve_change / current_eve * 100, 2),
            round(eve_change * 0.1, 0)  # 자본 영향
        ))

    cursor.executemany("""
        INSERT INTO alm_scenario_result
        (result_id, base_date, scenario_id, current_nim, stressed_nim, nim_change,
         current_eve, stressed_eve, eve_change, eve_change_pct, capital_impact)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, results)

    # 헷지 포지션
    hedges = []
    instruments = [
        ('IRS', 'FIXED', 'FLOATING', 3.5),
        ('IRS', 'FLOATING', 'FIXED', 3.8),
        ('FRA', 'FIXED', 'FLOATING', 3.6),
        ('CAP', None, 'FLOATING', 4.0),
        ('FLOOR', 'FLOATING', None, 3.0)
    ]

    for _ in range(10):
        inst = random.choice(instruments)
        notional = random.uniform(100, 1000) * 1e9

        hedges.append((
            f"HP_{generate_uuid()}",
            datetime.now().strftime('%Y-%m-%d'),
            inst[0],
            round(notional, 0),
            inst[1],
            inst[2],
            inst[3] + random.uniform(-0.5, 0.5),
            'CD91' if inst[2] == 'FLOATING' else None,
            random.uniform(-0.1, 0.1),
            (datetime.now() + timedelta(days=random.randint(365, 1825))).strftime('%Y-%m-%d'),
            round(random.uniform(-50, 50) * 1e9, 0),
            round(random.uniform(-0.5, 0.5), 4),
            round(notional * 0.0001, 0),
            round(random.uniform(0.85, 0.99), 2),
            'ACTIVE'
        ))

    cursor.executemany("""
        INSERT INTO hedge_position
        (position_id, position_date, instrument_type, notional_amount, pay_leg, receive_leg,
         fixed_rate, floating_index, spread, maturity_date, mtm_value, delta, dv01, hedge_effectiveness, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, hedges)

    # 헷지 제안
    recommendations = []
    for bucket in buckets[:4]:  # 단기 버킷에 대해 제안
        current_gap = random.uniform(-500, 500) * 1e9
        if abs(current_gap) > 200 * 1e9:
            recommendations.append((
                f"HR_{generate_uuid()}",
                datetime.now().strftime('%Y-%m-%d'),
                bucket,
                round(current_gap, 0),
                0,
                'IRS' if current_gap > 0 else 'FRA',
                round(abs(current_gap) * 0.5, 0),
                round(abs(current_gap) * 0.001, 0),
                round(abs(current_gap) * 0.005, 0),
                random.randint(1, 3),
                f"{'플로팅 자산 > 플로팅 부채' if current_gap > 0 else '플로팅 부채 > 플로팅 자산'}로 금리 상승 시 {'이익' if current_gap > 0 else '손실'} 발생 가능",
                'PENDING'
            ))

    cursor.executemany("""
        INSERT INTO hedge_recommendation
        (recommendation_id, recommendation_date, gap_bucket, current_gap, target_gap,
         recommended_instrument, recommended_notional, expected_cost, expected_benefit,
         priority, rationale, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, recommendations)

    conn.commit()
    print(f"✓ ALM 갭: {len(gaps)}건, 시나리오: {len(scenarios)}건, 헷지: {len(hedges)}건, 제안: {len(recommendations)}건 생성")

# ============================================
# 메인 실행
# ============================================

def main():
    print("="*60)
    print("iM뱅크 CLMS 확장 기능 데이터 생성")
    print("="*60)

    conn = get_connection()

    try:
        # 1. 스키마 확장
        print("\n[1/9] 스키마 확장...")
        execute_schema_extension(conn)

        # 2. EWS 고도화
        print("\n[2/9] EWS 고도화 데이터 생성...")
        indicator_ids = generate_ews_indicators(conn)
        generate_ews_indicator_values(conn, indicator_ids)
        generate_supply_chain_relations(conn)
        generate_external_signals(conn)
        generate_composite_scores(conn)

        # 3. 동적 한도 관리
        print("\n[3/9] 동적 한도 관리 데이터 생성...")
        generate_economic_cycle(conn)
        generate_dynamic_limit_rules(conn)
        generate_dynamic_limit_adjustments(conn)

        # 4. 고객 수익성 (RBC)
        print("\n[4/9] 고객 수익성 데이터 생성...")
        generate_customer_profitability(conn)
        generate_cross_sell_opportunities(conn)

        # 5. 담보 모니터링
        print("\n[5/9] 담보 모니터링 데이터 생성...")
        generate_real_estate_index(conn)
        generate_collateral_valuations(conn)

        # 6. 포트폴리오 최적화
        print("\n[6/9] 포트폴리오 최적화 데이터 생성...")
        generate_portfolio_optimization(conn)

        # 7. Workout 관리
        print("\n[7/9] Workout 관리 데이터 생성...")
        generate_workout_data(conn)

        # 8. ESG
        print("\n[8/9] ESG 데이터 생성...")
        generate_esg_data(conn)

        # 9. ALM
        print("\n[9/9] ALM 데이터 생성...")
        generate_alm_data(conn)

        print("\n" + "="*60)
        print("✓ 모든 확장 데이터 생성 완료!")
        print("="*60)

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
