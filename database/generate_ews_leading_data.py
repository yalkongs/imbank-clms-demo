#!/usr/bin/env python3
"""
EWS 선행지표 강화 데이터 생성 스크립트
======================================
6개 신규 테이블 + ews_composite_score 컬럼 추가 + 데이터 적재

테이블:
1. ews_transaction_behavior  (~12,120건)
2. ews_public_registry       (~900건)
3. ews_market_signal         (~3,636건)
4. ews_news_sentiment        (~5,050건)
5. ews_news_sentiment_monthly (~12,120건)
6. ews_supply_chain_temporal  (~11,976건)
"""

import sqlite3
import random
import math
from datetime import datetime, timedelta

DB_PATH = '/Users/yalkongs/code/Projects/imbank-clms-demo/database/imbank_demo.db'
SCHEMA_PATH = '/Users/yalkongs/code/Projects/imbank-clms-demo/database/schema_ews_leading.sql'

# 12개월 시계열 (2025-03 ~ 2026-02)
MONTHS = [f"2025-{m:02d}" for m in range(3, 13)] + ["2026-01", "2026-02"]

# 신용등급별 위험 프로파일
RISK_PROFILES = {
    'AAA': 0.05, 'AA+': 0.08, 'AA': 0.10, 'AA-': 0.13,
    'A+': 0.18, 'A': 0.22, 'A-': 0.28,
    'BBB+': 0.35, 'BBB': 0.42, 'BBB-': 0.50,
    'BB+': 0.60, 'BB': 0.70, 'B+': 0.82,
}

# EWS 등급 경계
def ews_grade(score):
    if score >= 75: return 'NORMAL'
    if score >= 55: return 'WATCH'
    if score >= 35: return 'WARNING'
    return 'CRITICAL'

# 추세 판정
def score_trend(current, previous):
    if previous is None: return 'STABLE'
    diff = current - previous
    if diff > 3: return 'IMPROVING'
    if diff < -3: return 'DETERIORATING'
    return 'STABLE'

HEADLINES_NEGATIVE = [
    "실적 부진으로 영업이익 감소", "대규모 소송에 휘말려", "환율 변동에 따른 손실 확대",
    "주요 거래처 부도 여파", "내부 회계 감사 지적사항 발생", "규제 위반으로 과태료 부과",
    "핵심 인력 이탈 가속화", "원자재 가격 급등 부담", "시장 점유율 하락세 지속",
    "부채비율 급증에 신용등급 하향", "공장 가동률 대폭 하락", "매출채권 회수 지연 심화",
]
HEADLINES_NEUTRAL = [
    "분기 실적 시장 기대 부합", "신규 사업 진출 검토 중", "인사 개편 단행",
    "업계 평균 수준 성장세 유지", "설비 투자 계획 발표", "해외시장 동향 점검",
]
HEADLINES_POSITIVE = [
    "수주 잔고 사상 최대 경신", "신용등급 상향 조정", "영업이익률 전년비 대폭 개선",
    "ESG 우수 기업 선정", "신기술 특허 취득", "대규모 수출 계약 체결",
    "배당금 인상 발표", "전략적 M&A 성공", "원가절감으로 수익성 개선",
]

NEWS_CATEGORIES = ['FINANCIAL', 'LEGAL', 'OPERATIONAL', 'MANAGEMENT', 'INDUSTRY']
NEWS_SOURCES = ['매일경제', '한국경제', '이데일리', '연합뉴스', '서울경제', '머니투데이', '파이낸셜뉴스']

PUBLIC_EVENT_TYPES = ['TAX_DELINQUENT', 'SOCIAL_INSURANCE', 'SEIZURE', 'AUDIT_OPINION', 'MGMT_CHANGE']
PUBLIC_EVENT_DESC = {
    'TAX_DELINQUENT': '세금 체납 발생',
    'SOCIAL_INSURANCE': '사회보험료 미납',
    'SEIZURE': '자산 가압류 결정',
    'AUDIT_OPINION': '감사의견 비적정',
    'MGMT_CHANGE': '대표이사 변경',
}

PAYMENT_STATUSES = ['NORMAL', 'DELAYED', 'DELINQUENT']


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def execute_schema(conn):
    """스키마 SQL 실행"""
    with open(SCHEMA_PATH, 'r') as f:
        sql = f.read()
    conn.executescript(sql)
    conn.commit()
    print("  스키마 6개 테이블 생성 완료")


def add_composite_columns(conn):
    """ews_composite_score에 새 컬럼 추가 (이미 존재하면 무시)"""
    new_cols = [
        ("transaction_score", "REAL"),
        ("public_registry_score", "REAL"),
        ("market_score", "REAL"),
        ("news_score", "REAL"),
        ("ews_grade", "TEXT"),
        ("score_trend", "TEXT"),
        ("previous_composite", "REAL"),
    ]
    cursor = conn.cursor()
    for col_name, col_type in new_cols:
        try:
            cursor.execute(f"ALTER TABLE ews_composite_score ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.commit()
    print("  ews_composite_score 컬럼 추가 완료")


def load_customers(conn):
    """고객 목록 + 신용등급 로딩"""
    cursor = conn.cursor()
    rows = cursor.execute("""
        SELECT c.customer_id, c.customer_name, c.listing_status, c.industry_code,
               c.industry_name, c.size_category,
               COALESCE(cr.final_grade, 'BBB') as grade
        FROM customer c
        LEFT JOIN (
            SELECT customer_id, final_grade,
                   ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY rating_date DESC) as rn
            FROM credit_rating_result
        ) cr ON c.customer_id = cr.customer_id AND cr.rn = 1
    """).fetchall()
    customers = []
    for r in rows:
        customers.append({
            'id': r[0], 'name': r[1], 'listed': r[2] == 'LISTED',
            'industry_code': r[3], 'industry_name': r[4],
            'size': r[5], 'grade': r[6],
            'risk': RISK_PROFILES.get(r[6], 0.42),
        })
    return customers


def load_supply_chain(conn):
    """기존 공급망 관계 로딩"""
    rows = conn.execute("""
        SELECT supplier_id, buyer_id, dependency_score, share_of_revenue
        FROM supply_chain_relation WHERE status = 'ACTIVE'
    """).fetchall()
    relations = []
    for r in rows:
        relations.append({
            'supplier': r[0], 'buyer': r[1],
            'dependency': r[2] or 0.1, 'share': r[3] or 0.05,
        })
    return relations


# ============================================
# 1. 거래행태
# ============================================
def generate_transaction_behavior(conn, customers):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ews_transaction_behavior")
    count = 0
    batch = []

    for ci, cust in enumerate(customers):
        risk = cust['risk']
        base_balance = random.uniform(5, 200) * (1 - risk * 0.5)
        base_util = 0.3 + risk * 0.5 + random.uniform(-0.1, 0.1)
        base_util = max(0.1, min(0.95, base_util))
        has_salary = 1 if random.random() > risk * 0.8 else 0

        for mi, month in enumerate(MONTHS):
            seq = ci * len(MONTHS) + mi + 1
            row_id = f"EWSTX_{seq:06d}"
            # 위험 기업은 시간이 갈수록 악화 경향
            drift = mi * 0.005 * risk
            balance = max(0.1, base_balance * (1 - drift + random.uniform(-0.05, 0.05)))
            utilization = max(0.05, min(0.99, base_util + drift + random.uniform(-0.03, 0.03)))
            delay = max(0, int(risk * 30 * random.random() + drift * 10))
            salary = has_salary if random.random() > 0.05 else (1 - has_salary)
            outflow = max(0, min(0.8, risk * 0.3 + drift + random.uniform(-0.05, 0.05)))
            txn_count = max(1, int(random.gauss(50 * (1 - risk * 0.3), 10)))
            overdraft = max(0, int(random.expovariate(1 / (risk * 3 + 0.1)) - 1)) if risk > 0.3 else 0

            batch.append((row_id, cust['id'], month,
                          round(balance, 2), round(utilization, 4), delay,
                          salary, round(outflow, 4), txn_count, overdraft))
            count += 1

            if len(batch) >= 1000:
                cursor.executemany("""
                    INSERT OR REPLACE INTO ews_transaction_behavior
                    (id, customer_id, reference_month, avg_balance, limit_utilization,
                     payment_delay_days, salary_transfer, deposit_outflow_rate,
                     transaction_count, overdraft_count)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                """, batch)
                batch = []

    if batch:
        cursor.executemany("""
            INSERT OR REPLACE INTO ews_transaction_behavior
            (id, customer_id, reference_month, avg_balance, limit_utilization,
             payment_delay_days, salary_transfer, deposit_outflow_rate,
             transaction_count, overdraft_count)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, batch)
    conn.commit()
    print(f"  거래행태: {count}건")
    return count


# ============================================
# 2. 공적정보
# ============================================
def generate_public_registry(conn, customers):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ews_public_registry")
    count = 0
    batch = []

    for ci, cust in enumerate(customers):
        risk = cust['risk']
        # 이벤트 발생 확률: 위험 기업일수록 높음
        n_events = 0
        for _ in range(3):  # 최대 3건
            if random.random() < risk * 0.6:
                n_events += 1
        if n_events == 0:
            continue

        for ei in range(n_events):
            seq = count + 1
            row_id = f"EWSPR_{seq:06d}"
            etype = random.choice(PUBLIC_EVENT_TYPES)
            severity = random.choices(
                ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'],
                weights=[0.2, 0.3, 0.3, 0.2] if risk > 0.5 else [0.4, 0.3, 0.2, 0.1]
            )[0]
            # 최근 12개월 중 랜덤 날짜
            day_offset = random.randint(0, 365)
            event_date = (datetime(2025, 3, 1) + timedelta(days=day_offset)).strftime('%Y-%m-%d')
            desc = PUBLIC_EVENT_DESC.get(etype, '공적정보 이벤트')
            amount = round(random.uniform(0.5, 50), 2) if etype in ('TAX_DELINQUENT', 'SOCIAL_INSURANCE', 'SEIZURE') else None
            resolved = 1 if random.random() > risk else 0
            resolved_date = (datetime.strptime(event_date, '%Y-%m-%d') + timedelta(days=random.randint(7, 90))).strftime('%Y-%m-%d') if resolved else None

            batch.append((row_id, cust['id'], event_date, etype, severity, desc, amount, resolved, resolved_date))
            count += 1

    if batch:
        cursor.executemany("""
            INSERT OR REPLACE INTO ews_public_registry
            (id, customer_id, event_date, event_type, severity, description, amount, resolved, resolved_date)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, batch)
    conn.commit()
    print(f"  공적정보: {count}건")
    return count


# ============================================
# 3. 시장신호 (상장기업만)
# ============================================
def generate_market_signals(conn, customers):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ews_market_signal")
    listed = [c for c in customers if c['listed']]
    count = 0
    batch = []

    for ci, cust in enumerate(listed):
        risk = cust['risk']
        base_dd = max(0.5, 5.0 - risk * 8 + random.uniform(-1, 1))
        base_cds = 50 + risk * 400 + random.uniform(-20, 20)

        for mi, month in enumerate(MONTHS):
            seq = ci * len(MONTHS) + mi + 1
            row_id = f"EWSMK_{seq:06d}"
            drift = mi * 0.01 * risk
            stock_chg = round(random.gauss(-risk * 2 - drift * 5, 5), 2)
            cds = round(max(10, base_cds + drift * 50 + random.gauss(0, 15)), 1)
            bond_spread = round(max(5, cds * 0.7 + random.gauss(0, 10)), 1)
            dd = round(max(0.1, base_dd - drift * 3 + random.gauss(0, 0.5)), 2)
            implied_pd = round(max(0.001, min(0.5, 1 / (1 + math.exp(dd - 2)))), 4)
            mcap = round(random.uniform(500, 50000) * (1 - risk * 0.3), 1)
            vol = round(max(5, 15 + risk * 30 + random.gauss(0, 5)), 2)

            batch.append((row_id, cust['id'], month, stock_chg, cds, bond_spread, dd, implied_pd, mcap, vol))
            count += 1

    if batch:
        cursor.executemany("""
            INSERT OR REPLACE INTO ews_market_signal
            (id, customer_id, reference_month, stock_price_change, cds_spread,
             bond_spread, distance_to_default, implied_pd, market_cap, volatility_30d)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, batch)
    conn.commit()
    print(f"  시장신호: {count}건 (상장 {len(listed)}사)")
    return count


# ============================================
# 4. 뉴스감성 (개별기사 + 월별집계)
# ============================================
def generate_news_sentiment(conn, customers):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ews_news_sentiment")
    cursor.execute("DELETE FROM ews_news_sentiment_monthly")
    article_count = 0
    monthly_count = 0
    article_batch = []
    monthly_batch = []

    for ci, cust in enumerate(customers):
        risk = cust['risk']
        # 기사 수: 상장/대형일수록 많음
        articles_per_month = 1 if cust['size'] in ('SMALL', 'SOHO') else (3 if not cust['listed'] else 5)

        for mi, month in enumerate(MONTHS):
            month_articles = []
            for ai in range(random.randint(max(0, articles_per_month - 1), articles_per_month + 1)):
                seq = article_count + 1
                row_id = f"EWSNW_{seq:06d}"
                # 위험 기업: 부정 기사 비율 높음
                neg_prob = min(0.8, risk * 1.2)
                pos_prob = max(0.05, 0.4 - risk * 0.5)
                if random.random() < neg_prob:
                    headline = random.choice(HEADLINES_NEGATIVE)
                    sentiment = round(random.uniform(-0.9, -0.2), 2)
                elif random.random() < pos_prob / (1 - neg_prob + 0.01):
                    headline = random.choice(HEADLINES_POSITIVE)
                    sentiment = round(random.uniform(0.2, 0.9), 2)
                else:
                    headline = random.choice(HEADLINES_NEUTRAL)
                    sentiment = round(random.uniform(-0.2, 0.2), 2)

                headline = f"{cust['name']}, {headline}"
                # 날짜: 해당 월 내 랜덤
                y, m = int(month[:4]), int(month[5:7])
                day = random.randint(1, 28)
                pub_date = f"{y}-{m:02d}-{day:02d}"
                cat = random.choice(NEWS_CATEGORIES)
                relevance = round(random.uniform(0.5, 1.0), 2)

                article_batch.append((row_id, cust['id'], pub_date, headline,
                                      random.choice(NEWS_SOURCES), sentiment, cat, relevance))
                month_articles.append(sentiment)
                article_count += 1

                if len(article_batch) >= 1000:
                    cursor.executemany("""
                        INSERT OR REPLACE INTO ews_news_sentiment
                        (id, customer_id, publish_date, headline, source, sentiment_score, category, relevance_score)
                        VALUES (?,?,?,?,?,?,?,?)
                    """, article_batch)
                    article_batch = []

            # 월별 집계
            seq_m = monthly_count + 1
            row_id_m = f"EWSNM_{seq_m:06d}"
            if month_articles:
                avg_sent = round(sum(month_articles) / len(month_articles), 3)
                neg_ratio = round(sum(1 for s in month_articles if s < -0.2) / len(month_articles), 3)
                pos_ratio = round(sum(1 for s in month_articles if s > 0.2) / len(month_articles), 3)
            else:
                avg_sent, neg_ratio, pos_ratio = 0, 0, 0
            dom_cat = random.choice(NEWS_CATEGORIES)
            monthly_batch.append((row_id_m, cust['id'], month, len(month_articles),
                                  avg_sent, neg_ratio, pos_ratio, dom_cat))
            monthly_count += 1

            if len(monthly_batch) >= 1000:
                cursor.executemany("""
                    INSERT OR REPLACE INTO ews_news_sentiment_monthly
                    (id, customer_id, reference_month, article_count, avg_sentiment,
                     negative_ratio, positive_ratio, dominant_category)
                    VALUES (?,?,?,?,?,?,?,?)
                """, monthly_batch)
                monthly_batch = []

    # Flush remaining
    if article_batch:
        cursor.executemany("""
            INSERT OR REPLACE INTO ews_news_sentiment
            (id, customer_id, publish_date, headline, source, sentiment_score, category, relevance_score)
            VALUES (?,?,?,?,?,?,?,?)
        """, article_batch)
    if monthly_batch:
        cursor.executemany("""
            INSERT OR REPLACE INTO ews_news_sentiment_monthly
            (id, customer_id, reference_month, article_count, avg_sentiment,
             negative_ratio, positive_ratio, dominant_category)
            VALUES (?,?,?,?,?,?,?,?)
        """, monthly_batch)

    conn.commit()
    print(f"  뉴스기사: {article_count}건, 월별집계: {monthly_count}건")
    return article_count, monthly_count


# ============================================
# 5. 공급망 시계열
# ============================================
def generate_supply_chain_temporal(conn, customers, relations):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ews_supply_chain_temporal")
    cust_map = {c['id']: c for c in customers}
    count = 0
    batch = []

    for ri, rel in enumerate(relations):
        supplier = cust_map.get(rel['supplier'])
        buyer = cust_map.get(rel['buyer'])
        if not supplier or not buyer:
            continue

        # 양방향: supplier에 대해 buyer는 partner, buyer에 대해 supplier는 partner
        pairs = [
            (rel['supplier'], rel['buyer'], buyer),
            (rel['buyer'], rel['supplier'], supplier),
        ]
        for cust_id, partner_id, partner in pairs:
            base_amount = random.uniform(1, 50) * (1 + rel['dependency'])
            for mi, month in enumerate(MONTHS):
                seq = count + 1
                row_id = f"EWSSC_{seq:06d}"
                partner_risk = partner['risk']
                drift = mi * 0.005 * partner_risk
                amount = round(max(0.1, base_amount * (1 + random.gauss(0, 0.1) - drift)), 2)
                chg_rate = round(random.gauss(-partner_risk * 2 - drift * 5, 3), 2)
                status = random.choices(
                    PAYMENT_STATUSES,
                    weights=[0.8 - partner_risk * 0.5, 0.15 + partner_risk * 0.3, 0.05 + partner_risk * 0.2]
                )[0]
                chain_pd = round(max(0.001, partner_risk * rel['dependency'] * (1 + drift)), 4)

                batch.append((row_id, cust_id, partner_id, month, amount, chg_rate,
                              status, partner['grade'], chain_pd, round(rel['dependency'], 4)))
                count += 1

                if len(batch) >= 1000:
                    cursor.executemany("""
                        INSERT OR REPLACE INTO ews_supply_chain_temporal
                        (id, customer_id, partner_id, reference_month, transaction_amount,
                         transaction_change_rate, payment_status, partner_credit_grade,
                         chain_default_probability, dependency_ratio)
                        VALUES (?,?,?,?,?,?,?,?,?,?)
                    """, batch)
                    batch = []

    if batch:
        cursor.executemany("""
            INSERT OR REPLACE INTO ews_supply_chain_temporal
            (id, customer_id, partner_id, reference_month, transaction_amount,
             transaction_change_rate, payment_status, partner_credit_grade,
             chain_default_probability, dependency_ratio)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, batch)
    conn.commit()
    print(f"  공급망시계열: {count}건")
    return count


# ============================================
# 6. 종합점수 업데이트
# ============================================
def compute_channel_scores(conn, customers):
    """각 채널별 점수 계산 → ews_composite_score 업데이트"""
    cursor = conn.cursor()
    cust_map = {c['id']: c for c in customers}
    updated = 0

    for cust in customers:
        cid = cust['id']
        risk = cust['risk']
        is_listed = cust['listed']

        # 1) 거래행태 점수 (0~100, 높을수록 양호)
        txn_row = cursor.execute("""
            SELECT AVG(limit_utilization), AVG(payment_delay_days), AVG(deposit_outflow_rate), AVG(overdraft_count)
            FROM ews_transaction_behavior WHERE customer_id = ? AND reference_month >= '2025-12'
        """, (cid,)).fetchone()
        if txn_row and txn_row[0] is not None:
            util, delay, outflow, od = txn_row
            txn_score = max(0, min(100, 100 - util * 40 - delay * 0.5 - outflow * 30 - od * 5))
        else:
            txn_score = 60 - risk * 30

        # 2) 공적정보 점수 (0~100)
        pub_row = cursor.execute("""
            SELECT COUNT(*), SUM(CASE WHEN severity IN ('HIGH','CRITICAL') THEN 1 ELSE 0 END)
            FROM ews_public_registry WHERE customer_id = ? AND resolved = 0
        """, (cid,)).fetchone()
        pub_total = pub_row[0] or 0
        pub_severe = pub_row[1] or 0
        pub_score = max(0, 100 - pub_total * 15 - pub_severe * 20)

        # 3) 시장점수 (상장만, 0~100)
        if is_listed:
            mkt_row = cursor.execute("""
                SELECT AVG(distance_to_default), AVG(cds_spread), AVG(implied_pd)
                FROM ews_market_signal WHERE customer_id = ? AND reference_month >= '2025-12'
            """, (cid,)).fetchone()
            if mkt_row and mkt_row[0] is not None:
                dd, cds, ipd = mkt_row
                mkt_score = max(0, min(100, dd * 15 + max(0, 50 - cds * 0.1) - ipd * 100))
            else:
                mkt_score = 60 - risk * 30
        else:
            mkt_score = None

        # 4) 뉴스점수 (0~100)
        news_row = cursor.execute("""
            SELECT AVG(avg_sentiment), AVG(negative_ratio)
            FROM ews_news_sentiment_monthly WHERE customer_id = ? AND reference_month >= '2025-12'
        """, (cid,)).fetchone()
        if news_row and news_row[0] is not None:
            avg_sent, neg_ratio = news_row
            news_score = max(0, min(100, 50 + avg_sent * 50 - neg_ratio * 30))
        else:
            news_score = 55 - risk * 25

        # 5) 기존 재무점수 유지
        existing = cursor.execute("""
            SELECT financial_score, composite_score FROM ews_composite_score WHERE customer_id = ?
        """, (cid,)).fetchone()
        financial_score = existing[0] if existing else (70 - risk * 60)
        previous_composite = existing[1] if existing else None

        # 종합점수 산출
        if is_listed and mkt_score is not None:
            # 상장: 거래행태0.25 + 공적정보0.15 + 시장0.15 + 뉴스0.15 + 공급망(=기존supply_chain_score)0.15 + 재무0.15
            sc_score_row = cursor.execute("""
                SELECT supply_chain_score FROM ews_composite_score WHERE customer_id = ?
            """, (cid,)).fetchone()
            sc_score = sc_score_row[0] if sc_score_row and sc_score_row[0] else (60 - risk * 30)
            composite = (txn_score * 0.25 + pub_score * 0.15 + mkt_score * 0.15 +
                         news_score * 0.15 + sc_score * 0.15 + financial_score * 0.15)
        else:
            # 비상장: 거래행태0.30 + 공적정보0.20 + 뉴스0.20 + 공급망0.15 + 재무0.15
            sc_score_row = cursor.execute("""
                SELECT supply_chain_score FROM ews_composite_score WHERE customer_id = ?
            """, (cid,)).fetchone()
            sc_score = sc_score_row[0] if sc_score_row and sc_score_row[0] else (60 - risk * 30)
            composite = (txn_score * 0.30 + pub_score * 0.20 + news_score * 0.20 +
                         sc_score * 0.15 + financial_score * 0.15)

        composite = round(max(0, min(100, composite)), 1)
        grade = ews_grade(composite)
        trend = score_trend(composite, previous_composite)

        # risk_level 재계산
        risk_level = 'LOW' if composite >= 70 else ('MEDIUM' if composite >= 50 else ('HIGH' if composite >= 30 else 'CRITICAL'))

        if existing:
            cursor.execute("""
                UPDATE ews_composite_score SET
                    transaction_score = ?, public_registry_score = ?, market_score = ?,
                    news_score = ?, composite_score = ?, risk_level = ?,
                    ews_grade = ?, score_trend = ?, previous_composite = ?
                WHERE customer_id = ?
            """, (round(txn_score, 1), round(pub_score, 1),
                  round(mkt_score, 1) if mkt_score is not None else None,
                  round(news_score, 1), composite, risk_level,
                  grade, trend, previous_composite, cid))
        else:
            # INSERT new row
            sid = f"EWSC_{updated+1:06d}"
            cursor.execute("""
                INSERT INTO ews_composite_score
                (score_id, customer_id, score_date, financial_score, operational_score,
                 external_score, supply_chain_score, composite_score, risk_level,
                 predicted_default_prob, recommendation,
                 transaction_score, public_registry_score, market_score, news_score,
                 ews_grade, score_trend, previous_composite)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (sid, cid, '2026-02-01', round(financial_score, 1), round(50 - risk * 30, 1),
                  round(news_score, 1), round(sc_score, 1), composite, risk_level,
                  round(risk * 0.1, 4), '정기모니터링',
                  round(txn_score, 1), round(pub_score, 1),
                  round(mkt_score, 1) if mkt_score is not None else None,
                  round(news_score, 1), grade, trend, None))
        updated += 1

    conn.commit()
    print(f"  종합점수 업데이트: {updated}건")
    return updated


def main():
    random.seed(42)
    print("=" * 50)
    print("EWS 선행지표 데이터 생성 시작")
    print("=" * 50)

    conn = get_connection()

    print("\n[1/7] 스키마 생성...")
    execute_schema(conn)

    print("[2/7] ews_composite_score 컬럼 추가...")
    add_composite_columns(conn)

    print("[3/7] 고객/공급망 데이터 로딩...")
    customers = load_customers(conn)
    relations = load_supply_chain(conn)
    print(f"  고객 {len(customers)}명, 상장 {sum(1 for c in customers if c['listed'])}사, 공급망관계 {len(relations)}건")

    print("[4/7] 거래행태 데이터...")
    n1 = generate_transaction_behavior(conn, customers)

    print("[5/7] 공적정보 데이터...")
    n2 = generate_public_registry(conn, customers)

    print("[6/7] 시장신호 + 뉴스감성...")
    n3 = generate_market_signals(conn, customers)
    n4a, n4b = generate_news_sentiment(conn, customers)

    print("[7/7] 공급망 시계열 + 종합점수...")
    n5 = generate_supply_chain_temporal(conn, customers, relations)
    n6 = compute_channel_scores(conn, customers)

    total = n1 + n2 + n3 + n4a + n4b + n5
    print(f"\n총 {total}건 데이터 생성 완료")
    print("=" * 50)

    conn.close()


if __name__ == '__main__':
    main()
