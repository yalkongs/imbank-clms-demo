#!/usr/bin/env python3
"""
iM뱅크 CLMS 데모 시스템 - 데이터 대폭 보강 스크립트
=================================================
작성일: 2024-01-30
목적: 테스트 데이터의 현실성 및 다양성 확보

생성 데이터:
- 고객: 300명 추가 (총 약 410명)
- 여신신청: 1000건 추가 (총 약 1510건)
- 신용평가: 연동 생성
- 리스크파라미터: 연동 생성
- 담보: 500건 추가
- EWS Alert: 200건 추가
- Vintage Analysis: 확장
- Override Monitoring: 100건 추가
- 거래이력: 새로 생성
- 감사로그: 500건 추가
"""

import sqlite3
import random
from datetime import datetime, timedelta
import uuid
import math

# 데이터베이스 연결
DB_PATH = '/Users/yalkongs/code/Projects/imbank-clms-demo/database/imbank_demo.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

# 업종 마스터 데이터
INDUSTRIES = [
    ('MFG001', '반도체', '제조업', '전자부품', 'A', 'POSITIVE'),
    ('MFG002', '디스플레이', '제조업', '전자부품', 'B', 'NEUTRAL'),
    ('MFG003', '2차전지', '제조업', '전자부품', 'A', 'POSITIVE'),
    ('MFG004', '자동차부품', '제조업', '운송장비', 'B', 'NEUTRAL'),
    ('MFG005', '조선', '제조업', '운송장비', 'C', 'NEGATIVE'),
    ('MFG006', '철강', '제조업', '1차금속', 'C', 'NEUTRAL'),
    ('MFG007', '석유화학', '제조업', '화학', 'B', 'NEUTRAL'),
    ('MFG008', '정밀화학', '제조업', '화학', 'B', 'POSITIVE'),
    ('MFG009', '의약품', '제조업', '바이오', 'A', 'POSITIVE'),
    ('MFG010', '의료기기', '제조업', '바이오', 'A', 'POSITIVE'),
    ('MFG011', '기계설비', '제조업', '기계', 'B', 'NEUTRAL'),
    ('MFG012', '섬유의복', '제조업', '섬유', 'C', 'NEGATIVE'),
    ('MFG013', '식품가공', '제조업', '식품', 'B', 'NEUTRAL'),
    ('MFG014', '음료', '제조업', '식품', 'B', 'NEUTRAL'),
    ('SVC001', 'IT서비스', '서비스업', 'IT', 'A', 'POSITIVE'),
    ('SVC002', '소프트웨어', '서비스업', 'IT', 'A', 'POSITIVE'),
    ('SVC003', '플랫폼', '서비스업', 'IT', 'A', 'POSITIVE'),
    ('SVC004', '게임', '서비스업', 'IT', 'B', 'NEUTRAL'),
    ('SVC005', '콘텐츠', '서비스업', '미디어', 'B', 'POSITIVE'),
    ('SVC006', '광고', '서비스업', '미디어', 'B', 'NEUTRAL'),
    ('SVC007', '의료서비스', '서비스업', '헬스케어', 'A', 'POSITIVE'),
    ('SVC008', '교육', '서비스업', '교육', 'B', 'NEUTRAL'),
    ('SVC009', '물류', '서비스업', '유통', 'B', 'POSITIVE'),
    ('SVC010', '도소매', '서비스업', '유통', 'B', 'NEUTRAL'),
    ('SVC011', '호텔관광', '서비스업', '관광', 'C', 'NEUTRAL'),
    ('SVC012', '외식', '서비스업', '요식', 'C', 'NEUTRAL'),
    ('CON001', '종합건설', '건설업', '건설', 'C', 'NEGATIVE'),
    ('CON002', '전문건설', '건설업', '건설', 'C', 'NEGATIVE'),
    ('CON003', '건자재', '건설업', '건설', 'C', 'NEUTRAL'),
    ('REA001', '부동산개발', '부동산', 'PF', 'D', 'NEGATIVE'),
    ('REA002', '부동산임대', '부동산', '임대', 'C', 'NEUTRAL'),
    ('REA003', '부동산관리', '부동산', '관리', 'B', 'NEUTRAL'),
    ('FIN001', '캐피탈', '금융', '여신전문', 'B', 'NEUTRAL'),
    ('FIN002', '증권', '금융', '투자', 'B', 'NEUTRAL'),
    ('FIN003', '자산운용', '금융', '투자', 'B', 'NEUTRAL'),
    ('ENE001', '태양광', '에너지', '신재생', 'B', 'POSITIVE'),
    ('ENE002', '풍력', '에너지', '신재생', 'B', 'POSITIVE'),
    ('ENE003', '발전', '에너지', '전력', 'B', 'NEUTRAL'),
    ('TRD001', '수출입', '무역', '무역', 'B', 'NEUTRAL'),
    ('TRD002', '중개무역', '무역', '무역', 'C', 'NEUTRAL'),
]

# 기업명 생성용 데이터
COMPANY_PREFIXES = ['한국', '대한', '동아', '태평양', '신한', '우리', '하나', '글로벌', '아시아', '코리아',
                    '제일', '삼성', '현대', '엘지', '에스케이', '포스코', '한화', '롯데', '두산', '금호',
                    '효성', '동부', '대우', '쌍용', '진흥', '동양', '태영', '영풍', '세아', '동국']
COMPANY_SUFFIXES = ['테크', '시스템', '솔루션', '엔지니어링', '산업', '물산', '상사', '인터내셔널', '홀딩스', '그룹',
                    '전자', '화학', '건설', '개발', '에너지', '바이오', '메디컬', '파마', '로지스틱스', '커머스']

# 지역 데이터
REGIONS = ['서울시', '부산시', '대구시', '인천시', '광주시', '대전시', '울산시', '세종시',
           '경기도', '강원도', '충북', '충남', '전북', '전남', '경북', '경남', '제주']

# 신용등급 및 PD 매핑
GRADES = ['AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-', 'BBB+', 'BBB', 'BBB-', 'BB+', 'BB', 'BB-', 'B+', 'B', 'B-', 'CCC', 'CC', 'C', 'D']
GRADE_PD = {
    'AAA': 0.0001, 'AA+': 0.0002, 'AA': 0.0003, 'AA-': 0.0005,
    'A+': 0.0008, 'A': 0.0012, 'A-': 0.0018,
    'BBB+': 0.0028, 'BBB': 0.0042, 'BBB-': 0.0065,
    'BB+': 0.0098, 'BB': 0.0150, 'BB-': 0.0225,
    'B+': 0.0340, 'B': 0.0510, 'B-': 0.0765,
    'CCC': 0.1150, 'CC': 0.1725, 'C': 0.2500, 'D': 1.0
}

# 상품코드
PRODUCTS = ['CORP_WORK', 'CORP_TERM', 'CORP_FACILITY', 'CORP_TRADE', 'CORP_PF', 'CORP_BOND']

# 상태 및 단계
STATUSES = ['RECEIVED', 'SCREENING', 'REVIEWING', 'APPROVED', 'REJECTED', 'WITHDRAWN', 'DISBURSED']
STAGES = ['RECEPTION', 'SCREENING', 'CREDIT_REVIEW', 'PRICING', 'APPROVAL', 'DOCUMENTATION', 'DISBURSEMENT', 'COMPLETED']

def generate_uuid():
    return str(uuid.uuid4())[:8].upper()

def random_date(start_year=2020, end_year=2024):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    random_days = random.randint(0, delta.days)
    return (start + timedelta(days=random_days)).strftime('%Y-%m-%d')

def random_datetime(start_year=2020, end_year=2024):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    random_days = random.randint(0, delta.days)
    random_seconds = random.randint(0, 86400)
    return (start + timedelta(days=random_days, seconds=random_seconds)).strftime('%Y-%m-%d %H:%M:%S')

def generate_biz_reg_no():
    """사업자등록번호 생성"""
    return f"{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(10000,99999)}"

def generate_corp_reg_no():
    """법인등록번호 생성"""
    return f"110111-{random.randint(1000000,9999999)}"

def update_industry_master(conn):
    """업종 마스터 업데이트"""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM industry_master")

    for ind in INDUSTRIES:
        cursor.execute("""
            INSERT INTO industry_master (industry_code, industry_name, industry_large, industry_medium, risk_grade, outlook)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ind)

    conn.commit()
    print(f"✓ 업종 마스터: {len(INDUSTRIES)}건 생성")

def generate_customers(conn, count=300):
    """고객 데이터 생성"""
    cursor = conn.cursor()

    # 기존 최대 ID 확인
    cursor.execute("SELECT COUNT(*) FROM customer")
    existing_count = cursor.fetchone()[0]

    size_categories = ['LARGE', 'MEDIUM', 'SMALL', 'SOHO']
    size_weights = [0.05, 0.15, 0.40, 0.40]  # 대기업 5%, 중견 15%, 중소 40%, 소호 40%

    listing_statuses = ['KOSPI', 'KOSDAQ', 'KONEX', 'PRIVATE']

    customers = []
    for i in range(count):
        cust_id = f"CUST_NEW_{i+1:04d}"

        # 기업규모 결정
        size = random.choices(size_categories, weights=size_weights)[0]

        # 규모별 자산/매출 범위
        if size == 'LARGE':
            asset = random.randint(100000, 800000)
            revenue = random.randint(80000, 600000)
            employees = random.randint(1000, 20000)
            listing = random.choice(['KOSPI', 'KOSDAQ'])
        elif size == 'MEDIUM':
            asset = random.randint(20000, 100000)
            revenue = random.randint(15000, 80000)
            employees = random.randint(300, 2000)
            listing = random.choice(['KOSPI', 'KOSDAQ', 'KONEX', 'PRIVATE'])
        elif size == 'SMALL':
            asset = random.randint(5000, 30000)
            revenue = random.randint(3000, 25000)
            employees = random.randint(50, 500)
            listing = random.choice(['KOSDAQ', 'KONEX', 'PRIVATE', 'PRIVATE', 'PRIVATE'])
        else:  # SOHO
            asset = random.randint(500, 8000)
            revenue = random.randint(300, 5000)
            employees = random.randint(5, 100)
            listing = 'PRIVATE'

        # 업종 선택
        industry = random.choice(INDUSTRIES)

        # 회사명 생성
        prefix = random.choice(COMPANY_PREFIXES)
        suffix = random.choice(COMPANY_SUFFIXES)
        name = f"{prefix}{suffix}"
        name_eng = f"{prefix.upper()} {suffix.upper()}"

        # 지역 선택
        region = random.choice(REGIONS)

        customer = (
            cust_id,
            name,
            name_eng,
            generate_biz_reg_no(),
            generate_corp_reg_no(),
            random_date(1960, 2020),  # 설립일
            industry[0],  # industry_code
            industry[1],  # industry_name
            size,
            asset,
            revenue,
            employees,
            listing,
            f"{region} {random.choice(['중구', '강남구', '서구', '남구', '북구'])}",
            f"RM{random.randint(1, 150):03d}",
            f"BR{random.randint(1, 50):03d}",
        )
        customers.append(customer)

    cursor.executemany("""
        INSERT INTO customer (customer_id, customer_name, customer_name_eng, biz_reg_no, corp_reg_no,
                              establish_date, industry_code, industry_name, size_category, asset_size,
                              revenue_size, employee_count, listing_status, address, rm_id, branch_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, customers)

    conn.commit()
    print(f"✓ 고객: {count}건 추가 (총 {existing_count + count}건)")
    return [c[0] for c in customers]

def generate_loan_applications(conn, count=1000):
    """여신신청 데이터 생성"""
    cursor = conn.cursor()

    # 모든 고객 ID 조회
    cursor.execute("SELECT customer_id, size_category FROM customer")
    customers = cursor.fetchall()

    # 기존 신청건 수 확인
    cursor.execute("SELECT COUNT(*) FROM loan_application")
    existing_count = cursor.fetchone()[0]

    applications = []
    for i in range(count):
        app_id = f"APP_{datetime.now().strftime('%Y%m')}{i+1:05d}"

        # 고객 선택
        customer = random.choice(customers)
        cust_id = customer[0]
        size = customer[1]

        # 규모별 신청금액 범위
        if size == 'LARGE':
            amount = random.randint(50000, 500000)
        elif size == 'MEDIUM':
            amount = random.randint(10000, 100000)
        elif size == 'SMALL':
            amount = random.randint(1000, 30000)
        else:  # SOHO
            amount = random.randint(100, 5000)

        # 상태/단계 결정 (현실적인 분포)
        status_weights = [0.05, 0.08, 0.12, 0.45, 0.10, 0.05, 0.15]  # RECEIVED~DISBURSED
        status = random.choices(STATUSES, weights=status_weights)[0]

        if status in ['RECEIVED', 'SCREENING']:
            stage = random.choice(['RECEPTION', 'SCREENING'])
        elif status == 'REVIEWING':
            stage = random.choice(['CREDIT_REVIEW', 'PRICING'])
        elif status == 'APPROVED':
            stage = random.choice(['APPROVAL', 'DOCUMENTATION'])
        elif status == 'DISBURSED':
            stage = 'COMPLETED'
        else:
            stage = random.choice(STAGES[:4])

        app = (
            app_id,
            random_date(2023, 2024),
            random.choice(['NEW', 'RENEWAL', 'INCREASE', 'CHANGE']),
            cust_id,
            None,  # group_id
            random.choice(PRODUCTS),
            amount,
            random.choice([12, 24, 36, 48, 60, 84, 120]),  # tenor
            round(random.uniform(3.5, 8.5), 2),  # rate
            random.choice(['WORKING_CAPITAL', 'FACILITY_INVEST', 'TRADE_FINANCE', 'M&A', 'REFINANCING']),
            '운전자금 목적',
            random.choice(['REAL_ESTATE', 'DEPOSIT', 'SECURITIES', 'RECEIVABLE', 'UNSECURED']),
            amount * random.uniform(0.5, 1.5) if random.random() > 0.3 else None,
            random.choice(['NONE', 'PARTIAL', 'FULL', 'CREDIT_GUARANTEE']),
            status,
            stage,
            random.choice(['NORMAL', 'URGENT', 'EXPRESS']),
            f"RM{random.randint(1, 150):03d}",
            f"BR{random.randint(1, 50):03d}",
        )
        applications.append(app)

    cursor.executemany("""
        INSERT INTO loan_application (application_id, application_date, application_type, customer_id,
                                      group_id, product_code, requested_amount, requested_tenor,
                                      requested_rate, purpose_code, purpose_detail, collateral_type,
                                      collateral_value, guarantee_type, status, current_stage,
                                      priority, assigned_to, branch_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, applications)

    conn.commit()
    print(f"✓ 여신신청: {count}건 추가 (총 {existing_count + count}건)")
    return [a[0] for a in applications]

def generate_credit_ratings(conn, app_ids):
    """신용평가 결과 생성"""
    cursor = conn.cursor()

    ratings = []
    for app_id in app_ids:
        # 고객 정보 조회
        cursor.execute("""
            SELECT la.customer_id, c.size_category, c.industry_code
            FROM loan_application la
            JOIN customer c ON la.customer_id = c.customer_id
            WHERE la.application_id = ?
        """, (app_id,))
        result = cursor.fetchone()
        if not result:
            continue

        cust_id, size, industry = result

        # 규모별 등급 분포 (대기업이 좋은 등급 받을 확률 높음)
        if size == 'LARGE':
            grade_idx = random.choices(range(len(GRADES)),
                                       weights=[5,8,10,12,15,15,12,8,5,3,2,2,1,1,0.5,0.3,0.1,0.05,0.03,0.02])[0]
        elif size == 'MEDIUM':
            grade_idx = random.choices(range(len(GRADES)),
                                       weights=[2,4,6,8,10,12,14,12,10,8,5,3,2,1.5,1,0.8,0.4,0.2,0.08,0.02])[0]
        elif size == 'SMALL':
            grade_idx = random.choices(range(len(GRADES)),
                                       weights=[0.5,1,2,4,6,8,10,12,14,12,10,8,5,3,2,1,0.8,0.5,0.15,0.05])[0]
        else:
            grade_idx = random.choices(range(len(GRADES)),
                                       weights=[0.2,0.5,1,2,4,6,8,10,12,14,12,10,8,5,3,2,1,0.8,0.4,0.1])[0]

        grade = GRADES[grade_idx]
        pd_value = GRADE_PD[grade] * random.uniform(0.8, 1.2)  # 약간의 변동

        # Override 여부 (10% 확률)
        override_grade = None
        override_reason = None
        if random.random() < 0.10:
            # 1~2 notch 조정
            notch = random.choice([-2, -1, 1, 2])
            new_idx = max(0, min(len(GRADES)-1, grade_idx + notch))
            override_grade = GRADES[new_idx]
            override_reason = random.choice(['FINANCIAL_STRENGTH', 'MANAGEMENT_QUALITY', 'INDUSTRY_OUTLOOK', 'SPECIAL_FACTOR'])

        rating = (
            f"RTG_{generate_uuid()}",
            cust_id,
            app_id,
            random_date(2023, 2024),
            f"MDL_CORP_RATING",
            "v2.1",
            random.uniform(300, 900),  # raw_score
            grade,
            grade_idx + 1,
            pd_value,
            override_grade,
            override_reason,
            f"RM{random.randint(1, 150):03d}" if override_grade else None,
            random_date(2023, 2024),
            None,
        )
        ratings.append(rating)

    cursor.executemany("""
        INSERT INTO credit_rating_result (rating_id, customer_id, application_id, rating_date,
                                          model_id, model_version, raw_score, final_grade,
                                          grade_notch, pd_value, override_grade, override_reason,
                                          override_by, effective_from, effective_to)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ratings)

    conn.commit()
    print(f"✓ 신용평가: {len(ratings)}건 생성")

def generate_risk_parameters(conn, app_ids):
    """리스크 파라미터 생성"""
    cursor = conn.cursor()

    params = []
    for app_id in app_ids:
        # 신청정보 및 신용등급 조회
        cursor.execute("""
            SELECT la.requested_amount, la.requested_tenor, la.collateral_type,
                   cr.pd_value, cr.final_grade
            FROM loan_application la
            LEFT JOIN credit_rating_result cr ON la.application_id = cr.application_id
            WHERE la.application_id = ?
        """, (app_id,))
        result = cursor.fetchone()
        if not result:
            continue

        amount, tenor, collateral_type, pd_value, grade = result

        if pd_value is None:
            pd_value = random.uniform(0.001, 0.10)

        # LGD 결정 (담보유형별)
        lgd_by_collateral = {
            'REAL_ESTATE': random.uniform(0.15, 0.30),
            'DEPOSIT': random.uniform(0.05, 0.15),
            'SECURITIES': random.uniform(0.20, 0.35),
            'RECEIVABLE': random.uniform(0.35, 0.50),
            'UNSECURED': random.uniform(0.45, 0.65),
        }
        lgd = lgd_by_collateral.get(collateral_type, random.uniform(0.40, 0.55))

        # EAD (CCF 적용)
        ccf = random.uniform(0.75, 1.0)
        ead = amount * ccf

        # 만기
        maturity = (tenor or 36) / 12

        # RWA 계산 (Basel IRB 간략화)
        try:
            r = 0.12 * (1 - math.exp(-50 * pd_value)) / (1 - math.exp(-50)) + \
                0.24 * (1 - (1 - math.exp(-50 * pd_value)) / (1 - math.exp(-50)))
            b = (0.11852 - 0.05478 * math.log(pd_value)) ** 2

            from scipy.stats import norm
            k = lgd * (norm.cdf(norm.ppf(pd_value) / math.sqrt(1-r) +
                               math.sqrt(r/(1-r)) * norm.ppf(0.999)) - pd_value)
            k = k * (1 + (maturity - 2.5) * b) / (1 - 1.5 * b)
            rwa = k * 12.5 * ead
        except:
            rwa = ead * random.uniform(0.5, 1.5)

        # EL, UL, EC
        el = pd_value * lgd * ead
        ul = rwa * 0.08  # 대략적인 UL
        ec = ul * random.uniform(1.0, 1.2)

        param = (
            f"RISK_{generate_uuid()}",
            app_id,
            random_date(2023, 2024),
            pd_value,
            pd_value * random.uniform(0.8, 1.5),  # PIT PD
            lgd,
            ead,
            ccf,
            maturity,
            rwa,
            el,
            ul,
            ec,
        )
        params.append(param)

    cursor.executemany("""
        INSERT INTO risk_parameter (param_id, application_id, calc_date, ttc_pd, pit_pd,
                                    lgd, ead, ccf, maturity_years, rwa, expected_loss,
                                    unexpected_loss, economic_capital)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, params)

    conn.commit()
    print(f"✓ 리스크 파라미터: {len(params)}건 생성")

def generate_facilities(conn, app_ids):
    """여신 시설(Facility) 생성"""
    cursor = conn.cursor()

    facilities = []
    for app_id in app_ids:
        # 승인된 건만 Facility 생성
        cursor.execute("""
            SELECT la.customer_id, la.requested_amount, la.requested_tenor,
                   la.requested_rate, la.product_code, la.status
            FROM loan_application la
            WHERE la.application_id = ? AND la.status IN ('APPROVED', 'DISBURSED')
        """, (app_id,))
        result = cursor.fetchone()
        if not result:
            continue

        cust_id, amount, tenor, rate, product, status = result

        # 승인금액 (요청금액의 80~100%)
        approved = amount * random.uniform(0.8, 1.0)

        # 실행금액
        if status == 'DISBURSED':
            outstanding = approved * random.uniform(0.5, 1.0)
        else:
            outstanding = 0

        facility = (
            f"FAC_{generate_uuid()}",
            app_id,
            cust_id,
            product.replace('CORP_', ''),
            product,
            'KRW',
            approved,
            approved,
            outstanding,
            approved - outstanding,
            random.choice(['FIXED', 'FLOATING']),
            random.choice(['CD91', 'COFIX', 'PRIME']),
            rate - 3.0 if rate else random.uniform(0.5, 2.0),
            rate,
            random_date(2023, 2024),
            random_date(2024, 2027),
            'ACTIVE' if status == 'DISBURSED' else 'APPROVED',
        )
        facilities.append(facility)

    cursor.executemany("""
        INSERT INTO facility (facility_id, application_id, customer_id, facility_type,
                              product_code, currency_code, approved_amount, current_limit,
                              outstanding_amount, available_amount, rate_type, base_rate_code,
                              spread, final_rate, contract_date, maturity_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, facilities)

    conn.commit()
    print(f"✓ Facility: {len(facilities)}건 생성")

def generate_collaterals(conn, count=500):
    """담보 데이터 생성"""
    cursor = conn.cursor()

    # 담보 있는 신청건 조회
    cursor.execute("""
        SELECT application_id, collateral_type, collateral_value
        FROM loan_application
        WHERE collateral_type IS NOT NULL AND collateral_type != 'UNSECURED'
        AND collateral_value > 0
    """)
    apps = cursor.fetchall()

    collaterals = []
    for app in random.sample(apps, min(count, len(apps))):
        app_id, col_type, col_value = app

        subtype_map = {
            'REAL_ESTATE': ['LAND', 'BUILDING', 'APARTMENT', 'FACTORY', 'WAREHOUSE'],
            'DEPOSIT': ['TERM_DEPOSIT', 'SAVINGS', 'CD'],
            'SECURITIES': ['STOCK', 'BOND', 'FUND'],
            'RECEIVABLE': ['TRADE_RECEIVABLE', 'LOAN_RECEIVABLE'],
        }

        subtype = random.choice(subtype_map.get(col_type, ['OTHER']))

        original_value = col_value * random.uniform(1.0, 1.3)
        current_value = col_value
        ltv = col_value / original_value * 100 if original_value > 0 else 0

        collateral = (
            f"COL_{generate_uuid()}",
            app_id,
            None,  # facility_id
            col_type,
            subtype,
            original_value,
            current_value,
            ltv,
            random_date(2023, 2024),
            random.randint(1, 3),
        )
        collaterals.append(collateral)

    cursor.executemany("""
        INSERT INTO collateral (collateral_id, application_id, facility_id, collateral_type,
                                collateral_subtype, original_value, current_value, ltv,
                                valuation_date, priority_rank)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, collaterals)

    conn.commit()
    print(f"✓ 담보: {len(collaterals)}건 생성")

def generate_ews_alerts(conn, count=200):
    """조기경보 Alert 생성"""
    cursor = conn.cursor()

    # 활성 고객 조회
    cursor.execute("SELECT customer_id FROM customer")
    customers = [c[0] for c in cursor.fetchall()]

    alert_types = [
        ('FINANCIAL', ['REVENUE_DECLINE', 'MARGIN_DECLINE', 'LIQUIDITY_SHORTAGE', 'LEVERAGE_INCREASE']),
        ('BEHAVIORAL', ['PAYMENT_DELAY', 'LIMIT_OVERUSE', 'PATTERN_CHANGE', 'BALANCE_DECLINE']),
        ('EXTERNAL', ['RATING_DOWNGRADE', 'LEGAL_ISSUE', 'NEWS_NEGATIVE', 'MARKET_SIGNAL']),
        ('CREDIT', ['GRADE_DETERIORATION', 'WATCH_LIST', 'NPL_WARNING', 'COVENANT_BREACH']),
    ]

    severities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
    severity_weights = [0.35, 0.35, 0.20, 0.10]

    alerts = []
    for _ in range(count):
        cust_id = random.choice(customers)
        alert_category = random.choice(alert_types)
        alert_type = alert_category[0]
        alert_subtype = random.choice(alert_category[1])
        severity = random.choices(severities, weights=severity_weights)[0]

        indicator_value = random.uniform(0, 100)
        threshold_value = indicator_value * random.uniform(0.7, 0.95)

        # 상태 (오래된 것은 해결됨)
        alert_date = random_date(2023, 2024)
        if alert_date < '2024-06-01':
            status = random.choice(['RESOLVED', 'RESOLVED', 'RESOLVED', 'OPEN'])
        else:
            status = random.choice(['OPEN', 'OPEN', 'MONITORING', 'RESOLVED'])

        alert = (
            f"EWS_{generate_uuid()}",
            cust_id,
            None,  # facility_id
            alert_date,
            alert_type,
            alert_subtype,
            severity,
            indicator_value,
            threshold_value,
            f"{alert_subtype} 경보 발생",
            status,
            '조치 완료' if status == 'RESOLVED' else None,
            random_datetime(2023, 2024) if status == 'RESOLVED' else None,
        )
        alerts.append(alert)

    cursor.executemany("""
        INSERT INTO ews_alert (alert_id, customer_id, facility_id, alert_date, alert_type,
                               alert_subtype, severity, indicator_value, threshold_value,
                               description, status, action_taken, resolved_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, alerts)

    conn.commit()
    print(f"✓ EWS Alert: {len(alerts)}건 생성")

def generate_override_monitoring(conn, count=100):
    """Override 모니터링 데이터 생성"""
    cursor = conn.cursor()

    # Override 있는 신용평가 조회
    cursor.execute("""
        SELECT cr.application_id, cr.final_grade, cr.override_grade, cr.override_reason, cr.override_by
        FROM credit_rating_result cr
        WHERE cr.override_grade IS NOT NULL
    """)
    overrides = cursor.fetchall()

    if not overrides:
        print("✓ Override 데이터 없음 - 건너뜀")
        return

    monitoring = []
    outcomes = []

    for ov in random.sample(overrides, min(count, len(overrides))):
        app_id, system_grade, override_grade, reason, overrider = ov

        # notch 변화 계산
        sys_idx = GRADES.index(system_grade) if system_grade in GRADES else 10
        ov_idx = GRADES.index(override_grade) if override_grade in GRADES else 10
        notch_change = sys_idx - ov_idx
        direction = 'UPGRADE' if notch_change > 0 else 'DOWNGRADE'

        override_date = random_date(2023, 2024)

        mon = (
            f"OV_{generate_uuid()}",
            app_id,
            'GRADE',
            override_date,
            system_grade,
            override_grade,
            direction,
            abs(notch_change),
            reason,
            f"{reason} 사유로 등급 조정",
            overrider,
            f"MGR{random.randint(1, 50):03d}",
            random_date(2024, 2024) if random.random() > 0.3 else None,
            random.choice(['PERFORMING', 'DELINQUENT', 'DEFAULT', 'NPL', None]),
        )
        monitoring.append(mon)

        # Override outcome 생성
        if mon[-1]:  # outcome이 있으면
            # 정확도 판정
            if direction == 'UPGRADE':
                correct = 0 if mon[-1] in ['DEFAULT', 'NPL'] else 1  # 상향 후 부도면 잘못
            else:
                correct = 0 if mon[-1] == 'PERFORMING' else 1  # 하향 후 정상이면 잘못

            cursor.execute("SELECT customer_id FROM loan_application WHERE application_id = ?", (app_id,))
            cust = cursor.fetchone()
            cust_id = cust[0] if cust else 'UNKNOWN'

            outcome = (
                f"OUT_{generate_uuid()}",
                mon[0],  # override_id
                app_id,
                cust_id,
                override_date,
                system_grade,
                override_grade,
                direction,
                abs(notch_change),
                reason,
                overrider,
                random_date(2024, 2024),
                mon[-1],
                correct,
                random.randint(30, 365) if mon[-1] in ['DEFAULT', 'NPL'] else None,
            )
            outcomes.append(outcome)

    cursor.executemany("""
        INSERT INTO override_monitoring (override_id, application_id, override_type, override_date,
                                         system_value, override_value, override_direction, notch_change,
                                         override_reason_code, override_reason_text, override_by,
                                         approved_by, outcome_date, outcome_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, monitoring)

    # 기존 override_outcome 삭제 후 재생성
    cursor.execute("DELETE FROM override_outcome")

    cursor.executemany("""
        INSERT INTO override_outcome (outcome_id, override_id, application_id, customer_id,
                                      override_date, system_grade, override_grade, override_direction,
                                      notch_change, override_reason, overrider_id, observation_date,
                                      actual_outcome, outcome_correct, days_to_default)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, outcomes)

    conn.commit()
    print(f"✓ Override Monitoring: {len(monitoring)}건, Outcome: {len(outcomes)}건 생성")

def generate_vintage_analysis(conn):
    """Vintage 분석 데이터 확장"""
    cursor = conn.cursor()

    # 기존 데이터 삭제
    cursor.execute("DELETE FROM vintage_analysis")

    vintages = []

    # 2021년 1월부터 2024년 6월까지 월별 OVERALL 데이터
    start_date = datetime(2021, 1, 1)
    for i in range(42):  # 3.5년
        vintage_month = (start_date + timedelta(days=i*30)).strftime('%Y-%m')

        # 기본 건수/금액 (계절성 반영)
        month_num = int(vintage_month.split('-')[1])
        seasonal_factor = 1.0 + 0.2 * math.sin((month_num - 3) * math.pi / 6)  # 3월 피크

        base_count = int(random.uniform(100, 200) * seasonal_factor)
        base_amount = base_count * random.uniform(300, 500)

        # MOB별 연체율/부도율 (시간 경과에 따라 증가)
        mob_3_del_rate = random.uniform(0.015, 0.035)
        mob_6_del_rate = mob_3_del_rate * random.uniform(1.3, 1.8)
        mob_12_del_rate = mob_6_del_rate * random.uniform(1.2, 1.5)
        mob_12_dr = mob_12_del_rate * random.uniform(0.3, 0.5)
        mob_24_dr = mob_12_dr * random.uniform(1.5, 2.0)
        cum_loss = mob_24_dr * random.uniform(0.4, 0.6)

        vintage = (
            f"VIN_{vintage_month.replace('-', '')}_OVERALL",
            vintage_month,
            'OVERALL',
            'ALL',
            base_count,
            base_amount,
            int(base_count * mob_3_del_rate),
            mob_3_del_rate,
            int(base_count * mob_6_del_rate),
            mob_6_del_rate,
            int(base_count * mob_12_del_rate),
            mob_12_del_rate,
            int(base_count * mob_12_dr),
            mob_12_dr,
            int(base_count * mob_24_dr),
            mob_24_dr,
            cum_loss,
        )
        vintages.append(vintage)

    # 등급별 Vintage (최근 12개월)
    for grade in ['A+', 'A', 'BBB+', 'BBB', 'BB+', 'BB', 'B+', 'B']:
        for i in range(12):
            vintage_month = (datetime(2024, 1, 1) - timedelta(days=i*30)).strftime('%Y-%m')

            # 등급별 기본 연체율 차등
            grade_factor = {
                'A+': 0.3, 'A': 0.5, 'BBB+': 0.8, 'BBB': 1.0,
                'BB+': 1.5, 'BB': 2.0, 'B+': 3.0, 'B': 4.0
            }[grade]

            base_count = random.randint(20, 50)
            base_amount = base_count * random.uniform(200, 400)

            mob_3_del_rate = random.uniform(0.01, 0.03) * grade_factor
            mob_6_del_rate = mob_3_del_rate * random.uniform(1.3, 1.8)
            mob_12_del_rate = mob_6_del_rate * random.uniform(1.2, 1.5)
            mob_12_dr = mob_12_del_rate * random.uniform(0.3, 0.5)
            mob_24_dr = mob_12_dr * random.uniform(1.5, 2.0)
            cum_loss = mob_24_dr * random.uniform(0.4, 0.6)

            vintage = (
                f"VIN_{vintage_month.replace('-', '')}_GRADE_{grade.replace('+', 'P').replace('-', 'M')}",
                vintage_month,
                'GRADE',
                grade,
                base_count,
                base_amount,
                int(base_count * mob_3_del_rate),
                mob_3_del_rate,
                int(base_count * mob_6_del_rate),
                mob_6_del_rate,
                int(base_count * mob_12_del_rate),
                mob_12_del_rate,
                int(base_count * mob_12_dr),
                mob_12_dr,
                int(base_count * mob_24_dr),
                mob_24_dr,
                cum_loss,
            )
            vintages.append(vintage)

    # 업종별 Vintage (최근 6개월)
    for ind_code in ['MFG001', 'MFG003', 'MFG004', 'SVC001', 'SVC010', 'CON001', 'REA001']:
        for i in range(6):
            vintage_month = (datetime(2024, 1, 1) - timedelta(days=i*30)).strftime('%Y-%m')

            # 업종별 리스크 차등
            industry_factor = {
                'MFG001': 0.5, 'MFG003': 0.6, 'MFG004': 1.0, 'SVC001': 0.4,
                'SVC010': 1.2, 'CON001': 2.0, 'REA001': 3.0
            }[ind_code]

            base_count = random.randint(15, 40)
            base_amount = base_count * random.uniform(300, 600)

            mob_3_del_rate = random.uniform(0.015, 0.035) * industry_factor
            mob_6_del_rate = mob_3_del_rate * random.uniform(1.3, 1.8)
            mob_12_del_rate = mob_6_del_rate * random.uniform(1.2, 1.5)
            mob_12_dr = mob_12_del_rate * random.uniform(0.3, 0.5)
            mob_24_dr = mob_12_dr * random.uniform(1.5, 2.0)
            cum_loss = mob_24_dr * random.uniform(0.4, 0.6)

            vintage = (
                f"VIN_{vintage_month.replace('-', '')}_IND_{ind_code}",
                vintage_month,
                'INDUSTRY',
                ind_code,
                base_count,
                base_amount,
                int(base_count * mob_3_del_rate),
                mob_3_del_rate,
                int(base_count * mob_6_del_rate),
                mob_6_del_rate,
                int(base_count * mob_12_del_rate),
                mob_12_del_rate,
                int(base_count * mob_12_dr),
                mob_12_dr,
                int(base_count * mob_24_dr),
                mob_24_dr,
                cum_loss,
            )
            vintages.append(vintage)

    cursor.executemany("""
        INSERT INTO vintage_analysis (vintage_id, vintage_month, cohort_type, cohort_value,
                                      origination_count, origination_amount, mob_3_delinquent,
                                      mob_3_delinquent_rate, mob_6_delinquent, mob_6_delinquent_rate,
                                      mob_12_delinquent, mob_12_delinquent_rate, mob_12_default,
                                      mob_12_default_rate, mob_24_default, mob_24_default_rate,
                                      cumulative_loss_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, vintages)

    conn.commit()
    print(f"✓ Vintage Analysis: {len(vintages)}건 생성")

def generate_audit_logs(conn, count=500):
    """감사 로그 생성"""
    cursor = conn.cursor()

    action_types = [
        'LOGIN', 'LOGOUT', 'VIEW', 'CREATE', 'UPDATE', 'DELETE',
        'APPROVE', 'REJECT', 'SUBMIT', 'EXPORT', 'IMPORT'
    ]

    target_entities = [
        'APPLICATION', 'CUSTOMER', 'RATING', 'FACILITY', 'COLLATERAL',
        'LIMIT', 'MODEL', 'REPORT', 'USER', 'SETTING'
    ]

    users = [f"USER{i:03d}" for i in range(1, 101)]
    depts = ['여신심사부', '리스크관리부', '영업부', '준법감시부', '경영지원부', 'IT부']

    logs = []
    for _ in range(count):
        action = random.choice(action_types)
        target = random.choice(target_entities)

        log = (
            f"LOG_{generate_uuid()}",
            random_datetime(2023, 2024),
            random.choice(users),
            random.choice(depts),
            action,
            target,
            f"{target[:3]}_{generate_uuid()}",
            '{"field": "old_value"}' if action == 'UPDATE' else None,
            '{"field": "new_value"}' if action == 'UPDATE' else None,
            f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}",
        )
        logs.append(log)

    cursor.executemany("""
        INSERT INTO audit_log (log_id, log_timestamp, user_id, user_dept, action_type,
                               target_entity, target_id, before_value, after_value, ip_address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, logs)

    conn.commit()
    print(f"✓ 감사 로그: {len(logs)}건 생성")

def generate_pricing_results(conn, app_ids):
    """가격결정 결과 생성"""
    cursor = conn.cursor()

    pricings = []
    for app_id in app_ids:
        # 신청정보 및 리스크 파라미터 조회
        cursor.execute("""
            SELECT la.requested_amount, la.requested_rate, la.status,
                   rp.ttc_pd, rp.lgd, rp.ead, rp.rwa
            FROM loan_application la
            LEFT JOIN risk_parameter rp ON la.application_id = rp.application_id
            WHERE la.application_id = ?
        """, (app_id,))
        result = cursor.fetchone()
        if not result:
            continue

        amount, req_rate, status, pd, lgd, ead, rwa = result

        if not pd or status in ['RECEIVED', 'SCREENING']:
            continue

        # 가격 구성요소 계산
        base_rate = random.uniform(3.5, 4.5)
        ftp_spread = random.uniform(1.0, 2.0)
        credit_spread = pd * lgd * 100 if pd and lgd else random.uniform(0.5, 2.0)
        capital_spread = (rwa * 0.08 * 0.10) / ead * 100 if rwa and ead else random.uniform(0.3, 1.0)
        opex_spread = random.uniform(0.2, 0.5)
        target_margin = random.uniform(0.3, 0.8)

        system_rate = base_rate + ftp_spread + credit_spread + capital_spread + opex_spread + target_margin
        proposed_rate = req_rate if req_rate else system_rate
        final_rate = proposed_rate * random.uniform(0.95, 1.05)

        # RAROC 계산
        revenue = ead * final_rate / 100 if ead else amount * final_rate / 100
        el = pd * lgd * ead if pd and lgd and ead else 0
        ec = rwa * 0.08 if rwa else amount * 0.08
        raroc = (revenue - el) / ec * 100 if ec > 0 else 0

        hurdle = random.uniform(12, 15)
        raroc_status = 'PASS' if raroc >= hurdle else 'FAIL'

        pricing = (
            f"PRC_{generate_uuid()}",
            app_id,
            random_date(2023, 2024),
            1,
            base_rate,
            ftp_spread,
            credit_spread,
            capital_spread,
            opex_spread,
            target_margin,
            random.uniform(-0.2, 0.2),  # strategy_adj
            random.uniform(-0.1, 0.1),  # contribution_adj
            random.uniform(-0.3, 0) if status == 'APPROVED' else 0,  # collateral_adj
            random.uniform(-0.2, 0.1),  # competitive_adj
            system_rate,
            proposed_rate,
            final_rate,
            revenue,
            raroc,
            raroc / (rwa if rwa else 1) * 100,  # RORWA
            hurdle,
            raroc_status,
        )
        pricings.append(pricing)

    cursor.executemany("""
        INSERT INTO pricing_result (pricing_id, application_id, pricing_date, pricing_version,
                                    base_rate, ftp_spread, credit_spread, capital_spread,
                                    opex_spread, target_margin, strategy_adj, contribution_adj,
                                    collateral_adj, competitive_adj, system_rate, proposed_rate,
                                    final_rate, expected_revenue, expected_raroc, expected_rorwa,
                                    hurdle_rate, raroc_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, pricings)

    conn.commit()
    print(f"✓ 가격결정: {len(pricings)}건 생성")

def generate_grade_backtest(conn):
    """등급별 백테스트 데이터 확장"""
    cursor = conn.cursor()

    # 기존 데이터 삭제
    cursor.execute("DELETE FROM grade_backtest")

    backtests = []
    models = ['MDL_CORP_RATING', 'MDL_SME_PD', 'MDL_SOHO_SCORE']
    years = [2021, 2022, 2023, 2024]

    for model in models:
        for year in years:
            for i, grade in enumerate(GRADES[:15]):  # AAA ~ B-
                pd_value = GRADE_PD[grade]
                obs_count = random.randint(50, 500)

                # 실제 부도율 (예측 PD 근처에서 변동)
                actual_dr = pd_value * random.uniform(0.5, 2.0)
                default_count = int(obs_count * actual_dr)
                actual_dr = default_count / obs_count if obs_count > 0 else 0

                # Binomial test p-value (간략화)
                if abs(actual_dr - pd_value) / pd_value < 0.3:
                    p_value = random.uniform(0.1, 0.5)
                    result = 'PASS'
                elif abs(actual_dr - pd_value) / pd_value < 0.5:
                    p_value = random.uniform(0.02, 0.08)
                    result = 'WARNING'
                else:
                    p_value = random.uniform(0.001, 0.02)
                    result = 'FAIL'

                backtest = (
                    f"BT_{model}_{year}_{grade.replace('+', 'P').replace('-', 'M')}",
                    model,
                    year,
                    grade,
                    i + 1,
                    pd_value,
                    obs_count,
                    default_count,
                    actual_dr,
                    p_value,
                    result,
                )
                backtests.append(backtest)

    cursor.executemany("""
        INSERT INTO grade_backtest (backtest_id, model_id, observation_year, grade, grade_notch,
                                    predicted_pd, observation_count, default_count, actual_dr,
                                    binomial_test_pvalue, test_result)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, backtests)

    conn.commit()
    print(f"✓ Grade Backtest: {len(backtests)}건 생성")

def generate_portfolio_summary(conn):
    """포트폴리오 요약 데이터 생성"""
    cursor = conn.cursor()

    # 기존 데이터 삭제
    cursor.execute("DELETE FROM portfolio_summary")

    summaries = []
    base_date = '2024-01-31'

    # 등급별 요약
    for i, grade in enumerate(GRADES[:12]):
        exposure = random.randint(50000, 500000)
        avg_pd = GRADE_PD[grade]
        avg_lgd = random.uniform(0.35, 0.50)
        rwa = exposure * avg_pd * avg_lgd * 12.5 * random.uniform(0.8, 1.2)
        el = exposure * avg_pd * avg_lgd

        summary = (
            f"PS_{base_date}_RATING_{grade.replace('+', 'P').replace('-', 'M')}",
            base_date,
            'RATING',
            grade,
            grade,
            random.randint(50, 300),
            exposure,
            rwa,
            el,
            avg_pd,
            avg_lgd,
            random.uniform(4.5, 7.5),
            exposure * random.uniform(0.04, 0.07),
            random.uniform(10, 20),
        )
        summaries.append(summary)

    # 업종별 요약
    for ind in INDUSTRIES[:15]:
        exposure = random.randint(30000, 300000)
        avg_pd = random.uniform(0.005, 0.05)
        avg_lgd = random.uniform(0.30, 0.55)
        rwa = exposure * avg_pd * avg_lgd * 12.5 * random.uniform(0.8, 1.2)
        el = exposure * avg_pd * avg_lgd

        summary = (
            f"PS_{base_date}_INDUSTRY_{ind[0]}",
            base_date,
            'INDUSTRY',
            ind[0],
            ind[1],
            random.randint(20, 150),
            exposure,
            rwa,
            el,
            avg_pd,
            avg_lgd,
            random.uniform(4.5, 7.5),
            exposure * random.uniform(0.04, 0.07),
            random.uniform(8, 22),
        )
        summaries.append(summary)

    # 규모별 요약
    for size in ['LARGE', 'MEDIUM', 'SMALL', 'SOHO']:
        size_factor = {'LARGE': 5, 'MEDIUM': 2, 'SMALL': 1, 'SOHO': 0.5}[size]
        exposure = int(random.randint(100000, 500000) * size_factor)
        avg_pd = random.uniform(0.003, 0.03) * (0.5 if size == 'LARGE' else 1.5 if size == 'SOHO' else 1)
        avg_lgd = random.uniform(0.30, 0.50)
        rwa = exposure * avg_pd * avg_lgd * 12.5 * random.uniform(0.8, 1.2)
        el = exposure * avg_pd * avg_lgd

        summary = (
            f"PS_{base_date}_SIZE_{size}",
            base_date,
            'SIZE',
            size,
            size,
            random.randint(30, 200),
            exposure,
            rwa,
            el,
            avg_pd,
            avg_lgd,
            random.uniform(4.5, 7.5),
            exposure * random.uniform(0.04, 0.07),
            random.uniform(10, 18),
        )
        summaries.append(summary)

    cursor.executemany("""
        INSERT INTO portfolio_summary (summary_id, base_date, segment_type, segment_code,
                                       segment_name, exposure_count, total_exposure, total_rwa,
                                       total_el, avg_pd, avg_lgd, weighted_rate, total_revenue, raroc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, summaries)

    conn.commit()
    print(f"✓ Portfolio Summary: {len(summaries)}건 생성")

def generate_capital_positions(conn):
    """자본 포지션 데이터 확장"""
    cursor = conn.cursor()

    # 기존 데이터 삭제
    cursor.execute("DELETE FROM capital_position")

    positions = []

    # 2022년 1월부터 2024년 1월까지 월말 데이터
    start_date = datetime(2022, 1, 31)
    for i in range(25):
        base_date = start_date + timedelta(days=i*30)
        base_date_str = base_date.strftime('%Y-%m-%d')

        # 자본 구성
        cet1 = random.uniform(35000, 42000)
        at1 = random.uniform(3000, 5000)
        tier2 = random.uniform(8000, 12000)
        total_capital = cet1 + at1 + tier2

        # RWA
        credit_rwa = random.uniform(280000, 350000)
        market_rwa = random.uniform(15000, 25000)
        op_rwa = random.uniform(20000, 30000)
        total_rwa = credit_rwa + market_rwa + op_rwa

        # 비율 계산
        bis_ratio = total_capital / total_rwa * 100
        cet1_ratio = cet1 / total_rwa * 100
        tier1_ratio = (cet1 + at1) / total_rwa * 100
        leverage_ratio = (cet1 + at1) / (total_rwa * 3) * 100  # 간략화

        position = (
            f"CAP_{base_date_str.replace('-', '')}",
            base_date_str,
            cet1,
            at1,
            tier2,
            total_capital,
            credit_rwa,
            market_rwa,
            op_rwa,
            total_rwa,
            bis_ratio,
            cet1_ratio,
            tier1_ratio,
            leverage_ratio,
        )
        positions.append(position)

    cursor.executemany("""
        INSERT INTO capital_position (position_id, base_date, cet1_capital, at1_capital,
                                      tier2_capital, total_capital, credit_rwa, market_rwa,
                                      operational_rwa, total_rwa, bis_ratio, cet1_ratio,
                                      tier1_ratio, leverage_ratio)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, positions)

    conn.commit()
    print(f"✓ Capital Position: {len(positions)}건 생성")

def generate_model_performance(conn):
    """모델 성능 로그 확장"""
    cursor = conn.cursor()

    # 기존 데이터 삭제
    cursor.execute("DELETE FROM model_performance_log")

    performances = []
    models = ['MDL_CORP_RATING', 'MDL_SME_PD', 'MDL_SOHO_SCORE', 'MDL_CORP_LGD', 'MDL_CORP_EWS']

    for model in models:
        # 2022년 1월부터 2024년 1월까지
        for i in range(25):
            mon_date = (datetime(2022, 1, 1) + timedelta(days=i*30)).strftime('%Y-%m-%d')

            # 기본 성능 지표 (시간에 따라 약간 변동)
            base_gini = random.uniform(0.55, 0.70)
            gini = base_gini + random.uniform(-0.05, 0.05)
            ks = gini * random.uniform(0.7, 0.85)
            auroc = (gini + 1) / 2
            psi = random.uniform(0.02, 0.15)
            ar_ratio = random.uniform(0.85, 1.15)

            # Alert 여부
            alert = 1 if psi > 0.10 or gini < 0.45 or ar_ratio < 0.80 or ar_ratio > 1.20 else 0
            alert_type = None
            if alert:
                if psi > 0.10:
                    alert_type = 'PSI_BREACH'
                elif gini < 0.45:
                    alert_type = 'GINI_DECLINE'
                else:
                    alert_type = 'AR_DEVIATION'

            perf = (
                f"PERF_{model}_{mon_date.replace('-', '')}",
                model,
                None,
                mon_date,
                None,
                None,
                gini,
                ks,
                auroc,
                psi,
                random.uniform(0.01, 0.05),  # CSI
                random.uniform(0.01, 0.05),  # predicted_dr
                random.uniform(0.008, 0.06),  # actual_dr
                ar_ratio,
                alert,
                alert_type,
            )
            performances.append(perf)

    cursor.executemany("""
        INSERT INTO model_performance_log (log_id, model_id, version_id, monitoring_date,
                                           segment_type, segment_code, gini_coefficient,
                                           ks_statistic, auroc, psi, csi, predicted_dr,
                                           actual_dr, ar_ratio, alert_triggered, alert_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, performances)

    conn.commit()
    print(f"✓ Model Performance: {len(performances)}건 생성")

def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("iM뱅크 CLMS 데모 시스템 - 데이터 대폭 보강")
    print("=" * 60)
    print()

    conn = get_connection()

    try:
        # 1. 업종 마스터 업데이트
        update_industry_master(conn)

        # 2. 고객 추가
        new_customers = generate_customers(conn, 300)

        # 3. 여신신청 추가
        new_applications = generate_loan_applications(conn, 1000)

        # 4. 신용평가 생성
        generate_credit_ratings(conn, new_applications)

        # 5. 리스크 파라미터 생성
        generate_risk_parameters(conn, new_applications)

        # 6. Facility 생성
        generate_facilities(conn, new_applications)

        # 7. 담보 생성
        generate_collaterals(conn, 500)

        # 8. EWS Alert 생성
        generate_ews_alerts(conn, 200)

        # 9. Override 모니터링 생성
        generate_override_monitoring(conn, 100)

        # 10. Vintage 분석 확장
        generate_vintage_analysis(conn)

        # 11. 감사 로그 생성
        generate_audit_logs(conn, 500)

        # 12. 가격결정 결과 생성
        generate_pricing_results(conn, new_applications)

        # 13. 백테스트 데이터 확장
        generate_grade_backtest(conn)

        # 14. 포트폴리오 요약 생성
        generate_portfolio_summary(conn)

        # 15. 자본 포지션 확장
        generate_capital_positions(conn)

        # 16. 모델 성능 로그 확장
        generate_model_performance(conn)

        print()
        print("=" * 60)
        print("데이터 보강 완료!")
        print("=" * 60)

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
