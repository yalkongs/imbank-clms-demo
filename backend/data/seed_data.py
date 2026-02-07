"""
iM뱅크 CLMS 데모용 가상 데이터 생성 스크립트
"""
import sqlite3
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import json

# 데이터베이스 경로
DB_PATH = Path(__file__).parent.parent.parent / "database" / "imbank_demo.db"
SCHEMA_PATH = Path(__file__).parent.parent.parent / "database" / "schema.sql"

# 등급별 PD 매핑
GRADE_PD_MAP = {
    'AAA': 0.0002, 'AA+': 0.0004, 'AA': 0.0006, 'AA-': 0.0010,
    'A+': 0.0015, 'A': 0.0025, 'A-': 0.0045,
    'BBB+': 0.0070, 'BBB': 0.0115, 'BBB-': 0.0185,
    'BB+': 0.0300, 'BB': 0.0480, 'BB-': 0.0750,
    'B+': 0.1200, 'B': 0.2000, 'B-': 0.3000
}

# 산업 마스터 데이터
INDUSTRIES = [
    ('IND001', '반도체', '제조업', '전자부품', 'LOW', 'POSITIVE'),
    ('IND002', 'IT서비스', '서비스업', 'IT', 'LOW', 'POSITIVE'),
    ('IND003', '자동차부품', '제조업', '자동차', 'MEDIUM', 'STABLE'),
    ('IND004', '기계장비', '제조업', '기계', 'MEDIUM', 'STABLE'),
    ('IND005', '화학', '제조업', '화학', 'MEDIUM', 'STABLE'),
    ('IND006', '바이오헬스', '제조업', '바이오', 'MEDIUM', 'POSITIVE'),
    ('IND007', '유통', '서비스업', '유통', 'MEDIUM', 'STABLE'),
    ('IND008', '건설', '건설업', '건설', 'HIGH', 'NEGATIVE'),
    ('IND009', '부동산PF', '금융업', '부동산', 'HIGH', 'NEGATIVE'),
    ('IND010', '무역', '서비스업', '무역', 'MEDIUM', 'STABLE'),
]

# 산업별 전략
INDUSTRY_STRATEGY = {
    'IND001': 'EXPAND', 'IND002': 'EXPAND', 'IND003': 'SELECTIVE',
    'IND004': 'MAINTAIN', 'IND005': 'MAINTAIN', 'IND006': 'EXPAND',
    'IND007': 'MAINTAIN', 'IND008': 'REDUCE', 'IND009': 'EXIT',
    'IND010': 'MAINTAIN'
}

# 상품 마스터
PRODUCTS = [
    ('LOAN_WORKING', '기업운전자금대출', 'WORKING', 'STANDARD'),
    ('LOAN_FACILITY', '기업시설자금대출', 'FACILITY', 'STANDARD'),
    ('LOAN_LIMIT', '기업한도대출', 'LIMIT', 'STANDARD'),
    ('LOAN_TRADE', '무역금융', 'TRADE', 'STANDARD'),
    ('LOAN_PF', 'PF대출', 'PF', 'HIGH'),
    ('GUARANTEE', '지급보증', 'GUARANTEE', 'STANDARD'),
]

# 고객명 생성용
COMPANY_PREFIXES = [
    '삼성', '현대', '코리아', '한국', '동양', '대한', '서울', '글로벌', '유니온', '테크',
    '스마트', '퓨처', '넥스트', '하이', '메가', '대구', '경북', '포항', '구미', '영남',
    '신라', '팔공', '금호', '성서', '비슬', '아이엠', '디지털', '그린', '블루', '에이스',
    '제일', '우진', '태영', '성진', '동아', '남성', '신흥', '창조', '혁신', '미래'
]
COMPANY_SUFFIXES = [
    '전자', '테크', '시스템', '솔루션', '개발', '산업', '건설', '무역', '유통', '물류',
    '바이오', '파트너스', '홀딩스', '인베스트', 'E&C', '섬유', '금속', '정밀', '엔지니어링',
    '에너지', '플랜트', '소재', '케미칼', '메디컬', '로보틱스', '오토', '모빌리티', '푸드', '커머스'
]

# 지역별 주소 및 region 코드
REGION_ADDRESSES = {
    'CAPITAL': [
        '서울시 강남구', '서울시 서초구', '서울시 영등포구', '서울시 중구', '서울시 종로구',
        '서울시 마포구', '서울시 송파구', '서울시 강서구',
        '경기도 성남시', '경기도 수원시', '경기도 용인시', '경기도 화성시', '경기도 안양시',
        '인천시 남동구', '인천시 연수구'
    ],
    'DAEGU_GB': [
        '대구시 수성구', '대구시 달서구', '대구시 북구', '대구시 동구', '대구시 서구',
        '대구시 중구', '대구시 남구', '대구시 달성군',
        '경북 포항시', '경북 구미시', '경북 경주시', '경북 김천시',
        '경북 안동시', '경북 영천시', '경북 경산시', '경북 상주시', '경북 칠곡군'
    ],
    'BUSAN_GN': [
        '부산시 해운대구', '부산시 남구', '부산시 사하구', '부산시 동래구', '부산시 부산진구',
        '경남 창원시', '경남 김해시', '경남 양산시', '경남 거제시',
        '울산시 남구', '울산시 울주군'
    ],
}

def get_region_and_address():
    """지역 코드와 주소를 랜덤으로 반환 (iM뱅크 거점: 대구경북 70%)"""
    region = random.choices(
        ['CAPITAL', 'DAEGU_GB', 'BUSAN_GN'],
        weights=[20, 70, 10]
    )[0]
    address = random.choice(REGION_ADDRESSES[region])
    return region, address

# 지역별 등급 가중치 (수도권 > 대구경북 > 부산경남 건전성 순)
REGION_GRADE_WEIGHTS = {
    # 수도권: 우량 등급 비중 높음
    'CAPITAL': {
        'LARGE':  [0.15, 0.20, 0.25, 0.18, 0.10, 0.07, 0.03, 0.01, 0.01],
        'MEDIUM': [0.05, 0.10, 0.15, 0.20, 0.20, 0.15, 0.10, 0.03, 0.02],
        'SMALL':  [0.02, 0.05, 0.10, 0.15, 0.20, 0.20, 0.15, 0.08, 0.05],
        'SOHO':   [0.01, 0.02, 0.05, 0.10, 0.18, 0.25, 0.20, 0.12, 0.07],
    },
    # 대구경북: 중간 수준
    'DAEGU_GB': {
        'LARGE':  [0.08, 0.12, 0.18, 0.20, 0.17, 0.12, 0.08, 0.03, 0.02],
        'MEDIUM': [0.02, 0.05, 0.10, 0.15, 0.22, 0.20, 0.15, 0.07, 0.04],
        'SMALL':  [0.01, 0.02, 0.05, 0.10, 0.15, 0.22, 0.22, 0.14, 0.09],
        'SOHO':   [0.00, 0.01, 0.03, 0.07, 0.12, 0.20, 0.25, 0.18, 0.14],
    },
    # 부산경남: 상대적 저건전성
    'BUSAN_GN': {
        'LARGE':  [0.05, 0.08, 0.12, 0.18, 0.20, 0.17, 0.12, 0.05, 0.03],
        'MEDIUM': [0.01, 0.03, 0.06, 0.10, 0.18, 0.25, 0.20, 0.10, 0.07],
        'SMALL':  [0.00, 0.01, 0.03, 0.06, 0.12, 0.20, 0.25, 0.20, 0.13],
        'SOHO':   [0.00, 0.00, 0.02, 0.04, 0.08, 0.15, 0.25, 0.25, 0.21],
    },
}

# 지역별 LGD 범위 (수도권 담보 가치 높고 회수율 양호)
REGION_LGD = {
    'CAPITAL':  {'secured': (0.18, 0.32), 'unsecured': (0.38, 0.50)},
    'DAEGU_GB': {'secured': (0.25, 0.40), 'unsecured': (0.45, 0.58)},
    'BUSAN_GN': {'secured': (0.30, 0.48), 'unsecured': (0.50, 0.65)},
}

def generate_uuid():
    return str(uuid.uuid4())[:8].upper()

def generate_biz_reg_no():
    return f"{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(10000,99999)}"

def generate_company_name():
    prefix = random.choice(COMPANY_PREFIXES)
    suffix = random.choice(COMPANY_SUFFIXES)
    return f"(주){prefix}{suffix}"

def create_database():
    """데이터베이스 및 테이블 생성"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with open(SCHEMA_PATH, 'r') as f:
        schema = f.read()
    cursor.executescript(schema)

    conn.commit()
    return conn

def seed_master_data(conn):
    """마스터 데이터 생성"""
    cursor = conn.cursor()

    # 산업 마스터
    cursor.executemany(
        "INSERT OR REPLACE INTO industry_master VALUES (?, ?, ?, ?, ?, ?)",
        INDUSTRIES
    )

    # 상품 마스터
    cursor.executemany(
        "INSERT OR REPLACE INTO product_master VALUES (?, ?, ?, ?, 1)",
        PRODUCTS
    )

    conn.commit()
    print("마스터 데이터 생성 완료")

def seed_customers(conn, count=100):
    """고객 데이터 생성"""
    cursor = conn.cursor()
    customers = []

    size_distribution = [
        ('LARGE', int(count * 0.10)),
        ('MEDIUM', int(count * 0.25)),
        ('SMALL', int(count * 0.50)),
        ('SOHO', count - int(count * 0.10) - int(count * 0.25) - int(count * 0.50)),
    ]

    customer_id = 1
    for size, cnt in size_distribution:
        for _ in range(cnt):
            industry = random.choice(INDUSTRIES)

            if size == 'LARGE':
                asset = random.uniform(5000, 50000)  # 5천억 ~ 5조
                revenue = random.uniform(3000, 30000)
                employees = random.randint(1000, 10000)
            elif size == 'MEDIUM':
                asset = random.uniform(1000, 5000)  # 1천억 ~ 5천억
                revenue = random.uniform(500, 3000)
                employees = random.randint(300, 1000)
            elif size == 'SMALL':
                asset = random.uniform(100, 1000)  # 100억 ~ 1천억
                revenue = random.uniform(50, 500)
                employees = random.randint(50, 300)
            else:  # SOHO
                asset = random.uniform(10, 100)  # 10억 ~ 100억
                revenue = random.uniform(5, 50)
                employees = random.randint(5, 50)

            cust_id = f"CUST{customer_id:05d}"
            establish_year = random.randint(1980, 2020)
            region, address = get_region_and_address()

            customers.append((
                cust_id,
                generate_company_name(),
                None,  # eng name
                generate_biz_reg_no(),
                None,  # corp reg no
                f"{establish_year}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                industry[0],
                industry[1],
                size,
                asset * 100000000,  # 억 -> 원
                revenue * 100000000,
                employees,
                'LISTED' if random.random() < 0.2 else 'UNLISTED',
                address,
                region,
                f"RM{random.randint(1,20):03d}",
                f"BR{random.randint(1,50):03d}",
            ))
            customer_id += 1

    cursor.executemany("""
        INSERT OR REPLACE INTO customer
        (customer_id, customer_name, customer_name_eng, biz_reg_no, corp_reg_no,
         establish_date, industry_code, industry_name, size_category, asset_size,
         revenue_size, employee_count, listing_status, address, region, rm_id, branch_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, customers)

    conn.commit()
    print(f"고객 데이터 {len(customers)}건 생성 완료")
    return customers

def seed_borrower_groups(conn, customers):
    """차주그룹 데이터 생성"""
    cursor = conn.cursor()

    # 대기업 위주로 10개 그룹 생성
    large_customers = [c for c in customers if c[8] == 'LARGE']

    groups = []
    group_members = []

    for i, cust in enumerate(large_customers[:10]):
        group_id = f"GRP{i+1:05d}"
        groups.append((
            group_id,
            f"{cust[1]} 그룹",
            'CONGLOMERATE',
            cust[0],
            0,
            5000 * 100000000  # 5000억 한도
        ))

        # 그룹 멤버 추가 (모회사)
        group_members.append((group_id, cust[0], 'PARENT', 100.0))

        # 자회사 2~3개 추가
        subsidiaries = random.sample([c for c in customers if c[8] in ['MEDIUM', 'SMALL']], random.randint(2, 3))
        for sub in subsidiaries:
            group_members.append((group_id, sub[0], 'SUBSIDIARY', random.uniform(30, 100)))

    cursor.executemany("""
        INSERT OR REPLACE INTO borrower_group
        (group_id, group_name, group_type, parent_company_id, total_exposure, group_limit)
        VALUES (?, ?, ?, ?, ?, ?)
    """, groups)

    cursor.executemany("""
        INSERT OR REPLACE INTO borrower_group_member
        (group_id, customer_id, relationship_type, ownership_pct)
        VALUES (?, ?, ?, ?)
    """, group_members)

    conn.commit()
    print(f"차주그룹 {len(groups)}개, 멤버 {len(group_members)}건 생성 완료")

def seed_facilities_and_applications(conn, customers):
    """여신약정 및 신청 데이터 생성"""
    cursor = conn.cursor()

    facilities = []
    applications = []
    ratings = []
    risk_params = []
    pricing_results = []

    grades = list(GRADE_PD_MAP.keys())

    # 기존 포트폴리오 (약정 완료): 1200건
    for i in range(1200):
        cust = random.choice(customers)
        product = random.choice(PRODUCTS)
        region = cust[14]  # customer region

        # 규모별 금액 범위
        if cust[8] == 'LARGE':
            amount = random.uniform(100, 1000) * 100000000  # 100억~1000억
        elif cust[8] == 'MEDIUM':
            amount = random.uniform(50, 300) * 100000000
        elif cust[8] == 'SMALL':
            amount = random.uniform(10, 100) * 100000000
        else:
            amount = random.uniform(1, 20) * 100000000

        # 등급 배정 (규모 + 지역별 가중치)
        size_key = cust[8] if cust[8] in ('LARGE', 'MEDIUM', 'SMALL', 'SOHO') else 'SMALL'
        grade_weights = REGION_GRADE_WEIGHTS.get(region, REGION_GRADE_WEIGHTS['DAEGU_GB']).get(size_key, REGION_GRADE_WEIGHTS['DAEGU_GB']['SMALL'])

        grade_weights = list(grade_weights) + [0] * (len(grades) - len(grade_weights))
        grade = random.choices(grades, weights=grade_weights[:len(grades)])[0]
        pd = GRADE_PD_MAP[grade]

        facility_id = f"FAC{i+1:06d}"
        app_id = f"APP{i+1:06d}"

        contract_date = datetime.now() - timedelta(days=random.randint(30, 720))
        maturity_date = contract_date + timedelta(days=random.randint(365, 1825))

        tenor_months = (maturity_date - contract_date).days // 30
        outstanding = amount * random.uniform(0.3, 1.0)

        # 담보 정보 + 지역별 LGD 차등
        collateral_type = random.choice(['REAL_ESTATE', 'DEPOSIT', 'SECURITIES', 'NONE'])
        lgd_range = REGION_LGD.get(region, REGION_LGD['DAEGU_GB'])
        if collateral_type != 'NONE':
            collateral_value = amount * random.uniform(1.0, 1.5)
            lgd = random.uniform(*lgd_range['secured'])
        else:
            collateral_value = 0
            lgd = random.uniform(*lgd_range['unsecured'])

        # 금리 계산
        base_rate = 0.035  # 3.5%
        credit_spread = pd * lgd * 1.5
        strategy_adj = random.uniform(-0.005, 0.01)
        final_rate = base_rate + credit_spread + strategy_adj + 0.015

        # RWA 계산 (간소화)
        rwa = outstanding * (0.5 + pd * 10) * (lgd / 0.45)
        el = pd * lgd * outstanding

        # RAROC 계산
        revenue = outstanding * final_rate
        cost = outstanding * (base_rate + 0.005)
        ec = rwa * 0.08
        raroc = (revenue - cost - el) / ec if ec > 0 else 0

        facilities.append((
            facility_id, app_id, cust[0], product[1], product[0], 'KRW',
            amount, amount, outstanding, amount - outstanding,
            'FLOATING', 'CD91', final_rate - base_rate, final_rate,
            contract_date.strftime('%Y-%m-%d'), maturity_date.strftime('%Y-%m-%d'), 'ACTIVE'
        ))

        applications.append((
            app_id, contract_date.strftime('%Y-%m-%d'), 'NEW', cust[0], None,
            product[0], amount, tenor_months, None, 'WORKING_CAPITAL', None,
            collateral_type, collateral_value, None, 'APPROVED', 'COMPLETED',
            'NORMAL', f"RM{random.randint(1,20):03d}", f"BR{random.randint(1,50):03d}"
        ))

        ratings.append((
            f"RAT{i+1:06d}", cust[0], app_id, contract_date.strftime('%Y-%m-%d'),
            'CORP_RATING_V3', '3.0', random.uniform(300, 800), grade,
            grades.index(grade), pd, None, None, None,
            contract_date.strftime('%Y-%m-%d'), None
        ))

        risk_params.append((
            f"RSK{i+1:06d}", app_id, contract_date.strftime('%Y-%m-%d'),
            pd, pd * 1.1, lgd, outstanding, 1.0, tenor_months / 12,
            rwa, el, el * 2.5, rwa * 0.08
        ))

        pricing_results.append((
            f"PRC{i+1:06d}", app_id, contract_date.strftime('%Y-%m-%d'), 1,
            base_rate, 0.005, credit_spread, 0.003, 0.002, 0.01,
            strategy_adj, 0, -0.002 if collateral_type != 'NONE' else 0, 0,
            final_rate, final_rate, final_rate, revenue, raroc, revenue / rwa if rwa > 0 else 0,
            0.12, 'ABOVE_HURDLE' if raroc > 0.12 else 'BELOW_HURDLE'
        ))

    # 신규 심사 건 (10건) - 시연용 케이스
    demo_cases = [
        ('삼성반도체파트너', 'IND001', 'LARGE', 200*100000000, 'A+', 'EXPAND'),
        ('현대차부품', 'IND003', 'MEDIUM', 100*100000000, 'A', 'SELECTIVE'),
        ('코리아건설', 'IND008', 'MEDIUM', 80*100000000, 'BBB+', 'REDUCE'),
        ('강남PF개발', 'IND009', 'MEDIUM', 300*100000000, 'BBB-', 'EXIT'),
        ('바이오텍', 'IND006', 'SMALL', 50*100000000, 'BB+', 'EXPAND'),
        ('글로벌무역', 'IND010', 'SMALL', 30*100000000, 'BBB', 'MAINTAIN'),
        ('IT솔루션', 'IND002', 'SMALL', 25*100000000, 'A-', 'EXPAND'),
        ('제조테크', 'IND004', 'SMALL', 60*100000000, 'BBB-', 'MAINTAIN'),
        ('유통마트', 'IND007', 'SMALL', 40*100000000, 'BB', 'MAINTAIN'),
        ('스타트업AI', 'IND002', 'SOHO', 15*100000000, 'B+', 'SELECTIVE'),
    ]

    # 산업코드 -> 산업명 매핑
    industry_name_map = {ind[0]: ind[1] for ind in INDUSTRIES}

    for i, (name, ind_code, size, amount, grade, strategy) in enumerate(demo_cases):
        app_id = f"APP2025{i+1:04d}"
        cust_id = f"DEMO{i+1:04d}"

        pd = GRADE_PD_MAP[grade]
        lgd = random.uniform(0.30, 0.45)
        region, address = get_region_and_address()

        # 고객 추가
        cursor.execute("""
            INSERT OR REPLACE INTO customer
            (customer_id, customer_name, biz_reg_no, industry_code, industry_name,
             size_category, asset_size, revenue_size, employee_count, address, region, rm_id, branch_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cust_id, f"(주){name}", generate_biz_reg_no(), ind_code,
              industry_name_map.get(ind_code, name),
              size, amount * 3, amount * 2, random.randint(50, 500), address, region, 'RM001', 'BR001'))

        applications.append((
            app_id, datetime.now().strftime('%Y-%m-%d'), 'NEW', cust_id, None,
            'LOAN_WORKING', amount, 36, None, 'WORKING_CAPITAL', None,
            'REAL_ESTATE', amount * 1.2, None, 'REVIEWING', 'RATING',
            'HIGH', 'RM001', 'BR001'
        ))

        ratings.append((
            f"RAT2025{i+1:04d}", cust_id, app_id, datetime.now().strftime('%Y-%m-%d'),
            'CORP_RATING_V3', '3.0', random.uniform(400, 700), grade,
            list(GRADE_PD_MAP.keys()).index(grade), pd, None, None, None,
            datetime.now().strftime('%Y-%m-%d'), None
        ))

    cursor.executemany("""
        INSERT OR REPLACE INTO facility
        (facility_id, application_id, customer_id, facility_type, product_code, currency_code,
         approved_amount, current_limit, outstanding_amount, available_amount,
         rate_type, base_rate_code, spread, final_rate, contract_date, maturity_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, facilities)

    cursor.executemany("""
        INSERT OR REPLACE INTO loan_application
        (application_id, application_date, application_type, customer_id, group_id,
         product_code, requested_amount, requested_tenor, requested_rate, purpose_code, purpose_detail,
         collateral_type, collateral_value, guarantee_type, status, current_stage,
         priority, assigned_to, branch_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, applications)

    cursor.executemany("""
        INSERT OR REPLACE INTO credit_rating_result
        (rating_id, customer_id, application_id, rating_date, model_id, model_version,
         raw_score, final_grade, grade_notch, pd_value, override_grade, override_reason,
         override_by, effective_from, effective_to)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ratings)

    cursor.executemany("""
        INSERT OR REPLACE INTO risk_parameter
        (param_id, application_id, calc_date, ttc_pd, pit_pd, lgd, ead, ccf,
         maturity_years, rwa, expected_loss, unexpected_loss, economic_capital)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, risk_params)

    cursor.executemany("""
        INSERT OR REPLACE INTO pricing_result
        (pricing_id, application_id, pricing_date, pricing_version, base_rate, ftp_spread,
         credit_spread, capital_spread, opex_spread, target_margin, strategy_adj,
         contribution_adj, collateral_adj, competitive_adj, system_rate, proposed_rate,
         final_rate, expected_revenue, expected_raroc, expected_rorwa, hurdle_rate, raroc_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, pricing_results)

    conn.commit()
    print(f"여신약정 {len(facilities)}건, 신청 {len(applications)}건 생성 완료")


def seed_collateral(conn):
    """담보 데이터 생성"""
    cursor = conn.cursor()

    # 담보가 있는 여신 조회
    cursor.execute("""
        SELECT la.application_id, f.facility_id, f.outstanding_amount, f.approved_amount,
               la.collateral_type, la.collateral_value
        FROM loan_application la
        JOIN facility f ON la.application_id = f.application_id
        WHERE la.collateral_type IS NOT NULL AND la.collateral_type != 'NONE'
          AND la.collateral_value > 0
    """)
    facilities_with_collateral = cursor.fetchall()

    collaterals = []
    subtypes = {
        'REAL_ESTATE': ['아파트', '오피스', '상가', '토지', '공장'],
        'DEPOSIT': ['정기예금', '적금', 'CD'],
        'SECURITIES': ['상장주식', '채권', '펀드'],
    }

    for i, (app_id, fac_id, outstanding, approved, col_type, col_value) in enumerate(facilities_with_collateral):
        subtype = random.choice(subtypes.get(col_type, ['기타']))
        current_value = col_value * random.uniform(0.85, 1.1)
        ltv = outstanding / current_value if current_value > 0 else 0

        collaterals.append((
            f"COL{i+1:06d}",
            app_id,
            fac_id,
            col_type,
            subtype,
            col_value,
            round(current_value, 0),
            round(ltv, 4),
            (datetime.now() - timedelta(days=random.randint(0, 90))).strftime('%Y-%m-%d'),
            1
        ))

    cursor.executemany("""
        INSERT OR REPLACE INTO collateral
        (collateral_id, application_id, facility_id, collateral_type, collateral_subtype,
         original_value, current_value, ltv, valuation_date, priority_rank)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, collaterals)

    conn.commit()
    print(f"담보 {len(collaterals)}건 생성 완료")


def seed_capital_data(conn):
    """자본 현황 데이터 생성"""
    cursor = conn.cursor()

    # iM뱅크 2024년말 공시 기준 자본 포지션
    # BIS 16.63%, Tier1 14.62%, CET1 14.32% (금융감독원 공시)
    # 총자산 ~82조원 기준 RWA 48조원 역산
    CET1 = 6_874_000_000_000    # 6조 8,740억원 (CET1비율 14.32% × RWA 48조)
    AT1  =   144_000_000_000    # 1,440억원
    T2   =   964_000_000_000    # 9,640억원
    TOTAL_CAP = CET1 + AT1 + T2 # 7조 9,820억원
    CR_RWA = 43_200_000_000_000 # 43.2조원 (신용위험, 총RWA의 90%)
    MR_RWA =  1_200_000_000_000 # 1.2조원 (시장위험)
    OR_RWA =  3_600_000_000_000 # 3.6조원 (운영위험)
    TOTAL_RWA = CR_RWA + MR_RWA + OR_RWA  # 48조원

    capital_data = [
        ('CAP001', datetime.now().strftime('%Y-%m-%d'),
         CET1, AT1, T2, TOTAL_CAP,
         CR_RWA, MR_RWA, OR_RWA, TOTAL_RWA,
         round(TOTAL_CAP / TOTAL_RWA, 4),              # BIS비율 16.63%
         round(CET1 / TOTAL_RWA, 4),                   # CET1비율 14.32%
         round((CET1 + AT1) / TOTAL_RWA, 4),           # Tier1비율 14.62%
         0.0700)                                        # 레버리지비율 7.0%
    ]

    # 월별 자본 추이 (과거 26개월, 2023-12부터)
    for i in range(1, 27):
        date = datetime.now() - timedelta(days=30*i)
        variation = random.uniform(0.97, 1.03)
        cet1_v = CET1 * variation
        total_cap_v = cet1_v + AT1 + T2
        cr_rwa_v = CR_RWA * variation
        total_rwa_v = cr_rwa_v + MR_RWA + OR_RWA
        capital_data.append((
            f"CAP{i+1:03d}", date.strftime('%Y-%m-%d'),
            cet1_v, AT1, T2, total_cap_v,
            cr_rwa_v, MR_RWA, OR_RWA, total_rwa_v,
            round(total_cap_v / total_rwa_v, 4),
            round(cet1_v / total_rwa_v, 4),
            round((cet1_v + AT1) / total_rwa_v, 4),
            0.0700 * variation
        ))

    cursor.executemany("""
        INSERT OR REPLACE INTO capital_position
        (position_id, base_date, cet1_capital, at1_capital, tier2_capital, total_capital,
         credit_rwa, market_rwa, operational_rwa, total_rwa,
         bis_ratio, cet1_ratio, tier1_ratio, leverage_ratio)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, capital_data)

    conn.commit()
    print("자본 현황 데이터 생성 완료")

def seed_capital_budget(conn):
    """자본예산 데이터 생성"""
    cursor = conn.cursor()

    budgets = []

    # 산업별 예산 (총 RWA 48조 기준, 산업당 2조~6조 배분)
    for ind_code, ind_name, _, _, _, _ in INDUSTRIES:
        budget_amt = random.uniform(20000, 60000) * 100000000  # 2조~6조
        used_pct = random.uniform(0.5, 0.95)

        budgets.append((
            f"BUD_IND_{ind_code}", '2025', None, 'INDUSTRY', ind_code, ind_name,
            budget_amt, budget_amt * 0.01, budget_amt * 0.05,
            budget_amt * used_pct, budget_amt * 0.01 * used_pct, budget_amt * 0.05 * used_pct * random.uniform(0.8, 1.2),
            0.12, 0.015, 'ACTIVE'
        ))

    # 등급별 예산 (등급군당 5조~15조 배분)
    for grade in ['AAA_AA', 'A', 'BBB', 'BB', 'B_Below']:
        budget_amt = random.uniform(50000, 150000) * 100000000  # 5조~15조
        used_pct = random.uniform(0.5, 0.9)

        budgets.append((
            f"BUD_GRADE_{grade}", '2025', None, 'RATING', grade, f"{grade} 등급군",
            budget_amt, budget_amt * 0.01, budget_amt * 0.05,
            budget_amt * used_pct, budget_amt * 0.01 * used_pct, budget_amt * 0.05 * used_pct,
            0.12, 0.015, 'ACTIVE'
        ))

    cursor.executemany("""
        INSERT OR REPLACE INTO capital_budget
        (budget_id, budget_year, budget_quarter, segment_type, segment_code, segment_name,
         rwa_budget, el_budget, revenue_target, rwa_used, el_used, revenue_actual,
         raroc_target, rorwa_target, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, budgets)

    conn.commit()
    print(f"자본예산 {len(budgets)}건 생성 완료")

def seed_portfolio_strategy(conn):
    """포트폴리오 전략 매트릭스 생성"""
    cursor = conn.cursor()

    strategies = []
    rating_buckets = ['AAA_AA', 'A', 'BBB', 'BB_Below']

    strategy_matrix = {
        'IND001': ['EXPAND', 'EXPAND', 'SELECTIVE', 'MAINTAIN'],  # 반도체
        'IND002': ['EXPAND', 'EXPAND', 'SELECTIVE', 'MAINTAIN'],  # IT서비스
        'IND003': ['EXPAND', 'SELECTIVE', 'MAINTAIN', 'REDUCE'],  # 자동차
        'IND004': ['SELECTIVE', 'MAINTAIN', 'MAINTAIN', 'REDUCE'],  # 기계
        'IND005': ['SELECTIVE', 'MAINTAIN', 'MAINTAIN', 'REDUCE'],  # 화학
        'IND006': ['EXPAND', 'EXPAND', 'SELECTIVE', 'MAINTAIN'],  # 바이오
        'IND007': ['MAINTAIN', 'MAINTAIN', 'REDUCE', 'EXIT'],  # 유통
        'IND008': ['MAINTAIN', 'REDUCE', 'REDUCE', 'EXIT'],  # 건설
        'IND009': ['REDUCE', 'REDUCE', 'EXIT', 'EXIT'],  # 부동산PF
        'IND010': ['SELECTIVE', 'MAINTAIN', 'MAINTAIN', 'REDUCE'],  # 무역
    }

    pricing_adj = {'EXPAND': -20, 'SELECTIVE': 0, 'MAINTAIN': 10, 'REDUCE': 30, 'EXIT': 100}

    for ind_code, ind_name, _, _, _, _ in INDUSTRIES:
        for i, rating in enumerate(rating_buckets):
            strat = strategy_matrix.get(ind_code, ['MAINTAIN', 'MAINTAIN', 'REDUCE', 'EXIT'])[i]
            strategies.append((
                ind_code, ind_name, rating, strat, pricing_adj[strat],
                datetime.now().strftime('%Y-%m-%d')
            ))

    cursor.executemany("""
        INSERT OR REPLACE INTO industry_rating_strategy
        (industry_code, industry_name, rating_bucket, strategy_code, pricing_adj_bp, effective_from)
        VALUES (?, ?, ?, ?, ?, ?)
    """, strategies)

    conn.commit()
    print(f"포트폴리오 전략 {len(strategies)}건 생성 완료")

def seed_limits(conn):
    """한도 데이터 생성"""
    cursor = conn.cursor()

    limits = []
    exposures = []

    # 규제 한도
    limits.append(('LIM_REG_SINGLE', '동일인 한도', 'REGULATORY', 'SINGLE', None,
                   625000000000, 'AMOUNT', 2500000000000, 80, 90, 95,  # 자기자본 25%
                   datetime.now().strftime('%Y-%m-%d'), None, 'ACTIVE'))

    limits.append(('LIM_REG_GROUP', '동일그룹 한도', 'REGULATORY', 'GROUP', None,
                   625000000000, 'AMOUNT', 2500000000000, 80, 90, 95,
                   datetime.now().strftime('%Y-%m-%d'), None, 'ACTIVE'))

    # 내부 한도 - 산업별
    for ind_code, ind_name, _, _, _, _ in INDUSTRIES:
        limit_amt = random.uniform(2000, 5000) * 100000000  # 2000억~5000억
        used_amt = limit_amt * random.uniform(0.4, 0.95)

        limits.append((
            f'LIM_IND_{ind_code}', f'{ind_name} 산업한도', 'INTERNAL', 'INDUSTRY', ind_code,
            limit_amt, 'AMOUNT', None, 80, 90, 95,
            datetime.now().strftime('%Y-%m-%d'), None, 'ACTIVE'
        ))

        util_rate = used_amt / limit_amt * 100
        status = 'NORMAL' if util_rate < 80 else ('WARNING' if util_rate < 90 else ('ALERT' if util_rate < 95 else 'CRITICAL'))

        exposures.append((
            f'EXP_IND_{ind_code}', f'LIM_IND_{ind_code}', datetime.now().strftime('%Y-%m-%d'),
            used_amt, 0, limit_amt - used_amt, util_rate, status
        ))

    cursor.executemany("""
        INSERT OR REPLACE INTO limit_definition
        (limit_id, limit_name, limit_type, dimension_type, dimension_code,
         limit_amount, limit_unit, base_amount, warning_level, alert_level, critical_level,
         effective_from, effective_to, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, limits)

    cursor.executemany("""
        INSERT OR REPLACE INTO limit_exposure
        (exposure_id, limit_id, base_date, exposure_amount, reserved_amount,
         available_amount, utilization_rate, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, exposures)

    conn.commit()
    print(f"한도 {len(limits)}건, 사용현황 {len(exposures)}건 생성 완료")

def seed_stress_scenarios(conn):
    """스트레스 시나리오 데이터 생성"""
    cursor = conn.cursor()

    scenarios = [
        ('SCN_BASE', 'Baseline', 'INTERNAL', 'BASELINE', 2.5, 3.5, 0, 3, 5, 0, '기본 시나리오'),
        ('SCN_MILD', 'Mild Stress', 'INTERNAL', 'MILD', 0.5, 4.5, 50, -5, -10, 5, '경미한 스트레스'),
        ('SCN_MOD', 'Moderate Stress', 'INTERNAL', 'MODERATE', -1.0, 6.0, 100, -15, -25, 10, '보통 스트레스'),
        ('SCN_SEV', 'Severe Stress', 'REGULATORY', 'SEVERE', -3.0, 8.0, 150, -30, -40, 15, '심각한 스트레스'),
        ('SCN_EXT', 'Extreme Stress', 'REGULATORY', 'EXTREME', -5.0, 10.0, 200, -40, -50, 20, '극단적 스트레스'),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO stress_scenario
        (scenario_id, scenario_name, scenario_type, severity_level,
         gdp_growth_shock, unemployment_shock, interest_rate_shock,
         housing_price_shock, stock_price_shock, fx_rate_shock, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, scenarios)

    # 스트레스 테스트 결과 생성
    results = []
    for scn_id, _, _, severity, gdp, unemp, rate, housing, stock, fx, _ in scenarios:
        # 스트레스 강도에 따른 PD/LGD 조정
        stress_factor = {'BASELINE': 1.0, 'MILD': 1.3, 'MODERATE': 1.8, 'SEVERE': 2.5, 'EXTREME': 3.5}
        factor = stress_factor.get(severity, 1.0)

        base_pd = 0.02
        base_lgd = 0.40
        base_ead = 5000000000000  # 5조

        stressed_pd = min(base_pd * factor, 0.30)
        stressed_lgd = min(base_lgd * (1 + (factor - 1) * 0.3), 0.70)
        el = stressed_pd * stressed_lgd * base_ead
        ul = el * 2.5

        # RWA 증가
        base_rwa = 16500000000000
        stressed_rwa = base_rwa * (1 + (factor - 1) * 0.2)

        # 자본비율 변화
        total_capital = 2500000000000
        stressed_bis = total_capital / stressed_rwa
        stressed_cet1 = 1850000000000 / stressed_rwa

        capital_shortfall = max(0, (0.08 * stressed_rwa) - total_capital)

        results.append((
            f'STR_{scn_id}', scn_id, datetime.now().strftime('%Y-%m-%d'), 12,
            base_ead, stressed_pd, stressed_lgd, el, ul, stressed_rwa,
            stressed_bis, stressed_cet1, capital_shortfall, None
        ))

    cursor.executemany("""
        INSERT OR REPLACE INTO stress_test_result
        (result_id, scenario_id, test_date, horizon_months,
         portfolio_ead, stressed_pd, stressed_lgd, expected_loss, unexpected_loss,
         stressed_rwa, stressed_bis_ratio, stressed_cet1_ratio, capital_shortfall, segment_detail_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, results)

    conn.commit()
    print(f"스트레스 시나리오 {len(scenarios)}건, 테스트 결과 {len(results)}건 생성 완료")

def seed_macro_indicators(conn):
    """거시경제 지표 데이터 생성"""
    cursor = conn.cursor()

    indicators = [
        ('GDP_GROWTH', 'GDP 성장률', 'ECONOMIC', '한국은행', 'QUARTERLY', '%'),
        ('UNEMPLOYMENT', '실업률', 'ECONOMIC', '통계청', 'MONTHLY', '%'),
        ('BASE_RATE', '기준금리', 'INTEREST', '한국은행', 'ADHOC', '%'),
        ('CORP_SPREAD', '회사채스프레드(AA)', 'MARKET', '금융투자협회', 'DAILY', 'bp'),
        ('HPI', '주택가격지수', 'PROPERTY', 'KB국민은행', 'MONTHLY', 'INDEX'),
        ('KOSPI', 'KOSPI', 'MARKET', 'KRX', 'DAILY', 'INDEX'),
        ('USD_KRW', '원/달러 환율', 'FX', '한국은행', 'DAILY', 'KRW'),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO macro_indicator
        (indicator_id, indicator_name, indicator_type, source, frequency, unit)
        VALUES (?, ?, ?, ?, ?, ?)
    """, indicators)

    # 지표 값 (36개월치)
    values = []
    base_values = {
        'GDP_GROWTH': 2.0, 'UNEMPLOYMENT': 3.5, 'BASE_RATE': 3.0,
        'CORP_SPREAD': 70, 'HPI': 100, 'KOSPI': 2600, 'USD_KRW': 1350
    }

    for i in range(36):
        date = datetime.now() - timedelta(days=30*i)
        for ind_id, _, _, _, _, _ in indicators:
            base = base_values[ind_id]
            variation = random.uniform(0.95, 1.05)
            value = base * variation
            prev_value = base * random.uniform(0.95, 1.05)

            values.append((
                f'VAL_{ind_id}_{i:03d}', ind_id, date.strftime('%Y-%m-%d'),
                value, prev_value, (value - prev_value) / prev_value * 100
            ))

    cursor.executemany("""
        INSERT OR REPLACE INTO macro_indicator_value
        (value_id, indicator_id, reference_date, value, previous_value, change_rate)
        VALUES (?, ?, ?, ?, ?, ?)
    """, values)

    conn.commit()
    print(f"거시지표 {len(indicators)}건, 지표값 {len(values)}건 생성 완료")

def seed_models(conn):
    """모델 데이터 생성"""
    cursor = conn.cursor()

    models = [
        ('MDL_CORP_RATING', '기업신용평가모형', 'RATING', 'PD', 'TIER1', '2023-01-01', '2024-06-01', '2025-06-01', 'PRODUCTION', '리스크관리부'),
        ('MDL_RETAIL_RATING', '소호신용평가모형', 'RATING', 'PD', 'TIER1', '2023-03-01', '2024-09-01', '2025-09-01', 'PRODUCTION', '리스크관리부'),
        ('MDL_LGD', 'LGD 모형', 'LGD', 'LGD', 'TIER2', '2022-06-01', '2024-06-01', '2025-06-01', 'PRODUCTION', '리스크관리부'),
        ('MDL_EAD', 'EAD/CCF 모형', 'EAD', 'EAD', 'TIER2', '2022-06-01', '2024-06-01', '2025-06-01', 'PRODUCTION', '리스크관리부'),
        ('MDL_PRICING', '가격결정모형', 'PRICING', 'PRICING', 'TIER2', '2024-01-01', '2024-12-01', '2025-12-01', 'PRODUCTION', '기업금융부'),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO model_registry
        (model_id, model_name, model_type, model_purpose, risk_tier,
         development_date, last_validation_date, next_validation_date, status, owner_dept)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, models)

    # 모델 버전
    versions = []
    for mdl_id, _, _, _, _, _, _, _, _, _ in models:
        for v in range(1, 4):
            versions.append((
                f'{mdl_id}_V{v}', mdl_id, f'{v}.0', 'PRODUCTION' if v == 3 else 'RETIRED',
                f'202{v+1}-01-01', f'202{v+2}-01-01' if v < 3 else None,
                json.dumps({'gini': 0.45 + v*0.02, 'ks': 0.35 + v*0.02, 'psi': 0.05}),
                'ACTIVE' if v == 3 else 'RETIRED'
            ))

    cursor.executemany("""
        INSERT OR REPLACE INTO model_version
        (version_id, model_id, version_no, deployment_env, effective_from, effective_to,
         performance_metrics, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, versions)

    # 성능 로그 (12개월)
    perf_logs = []
    for mdl_id, _, _, _, _, _, _, _, _, _ in models:
        for i in range(12):
            date = datetime.now() - timedelta(days=30*i)
            gini = random.uniform(0.42, 0.52)
            ks = random.uniform(0.32, 0.42)
            psi = random.uniform(0.03, 0.15)

            alert = 1 if psi > 0.10 or gini < 0.40 else 0
            alert_type = 'PSI_WARNING' if psi > 0.10 else ('GINI_WARNING' if gini < 0.40 else None)

            perf_logs.append((
                f'PERF_{mdl_id}_{i:03d}', mdl_id, f'{mdl_id}_V3',
                date.strftime('%Y-%m-%d'), None, None,
                gini, ks, gini + 0.05, psi, psi * 0.8,
                random.uniform(0.01, 0.03), random.uniform(0.01, 0.035),
                random.uniform(0.8, 1.2), alert, alert_type
            ))

    cursor.executemany("""
        INSERT OR REPLACE INTO model_performance_log
        (log_id, model_id, version_id, monitoring_date, segment_type, segment_code,
         gini_coefficient, ks_statistic, auroc, psi, csi,
         predicted_dr, actual_dr, ar_ratio, alert_triggered, alert_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, perf_logs)

    conn.commit()
    print(f"모델 {len(models)}건, 버전 {len(versions)}건, 성능로그 {len(perf_logs)}건 생성 완료")

def seed_ftp_and_spreads(conn):
    """FTP 및 스프레드 데이터 생성"""
    cursor = conn.cursor()

    # FTP 금리
    ftp_rates = []
    tenors = [3, 6, 12, 24, 36, 60]
    for tenor in tenors:
        base = 0.030 + tenor * 0.0005  # 기간 프리미엄
        ftp_rates.append((
            f'FTP_{tenor}M', datetime.now().strftime('%Y-%m-%d'), 'KRW', tenor,
            base, 0.002, 0.001, base + 0.003
        ))

    cursor.executemany("""
        INSERT OR REPLACE INTO ftp_rate
        (ftp_id, effective_date, currency_code, tenor_months,
         base_ftp_rate, liquidity_premium, term_premium, final_ftp_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ftp_rates)

    # 신용스프레드
    spreads = []
    grades = list(GRADE_PD_MAP.keys())
    secured_types = ['SECURED', 'UNSECURED']

    for grade in grades:
        pd = GRADE_PD_MAP[grade]
        for sec_type in secured_types:
            lgd = 0.35 if sec_type == 'SECURED' else 0.50
            el_spread = pd * lgd * 100  # %로 환산
            ul_spread = el_spread * 0.5
            base_spread = el_spread + ul_spread

            spreads.append((
                f'SPR_{grade}_{sec_type}', datetime.now().strftime('%Y-%m-%d'),
                grade, sec_type, 'ALL', base_spread, el_spread, ul_spread
            ))

    cursor.executemany("""
        INSERT OR REPLACE INTO credit_spread
        (spread_id, effective_date, rating_grade, secured_type, tenor_bucket,
         base_spread, el_spread, ul_spread)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, spreads)

    # Hurdle Rate
    hurdle_rates = [
        ('HUR_DEFAULT', datetime.now().strftime('%Y-%m-%d'), None, None, 0.12, 0.15, 'WACC'),
        ('HUR_LARGE', datetime.now().strftime('%Y-%m-%d'), 'SIZE', 'LARGE', 0.10, 0.13, 'WACC'),
        ('HUR_MEDIUM', datetime.now().strftime('%Y-%m-%d'), 'SIZE', 'MEDIUM', 0.12, 0.15, 'WACC'),
        ('HUR_SMALL', datetime.now().strftime('%Y-%m-%d'), 'SIZE', 'SMALL', 0.14, 0.17, 'WACC'),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO hurdle_rate
        (rate_id, effective_date, segment_type, segment_code, hurdle_raroc, target_raroc, calc_method)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, hurdle_rates)

    conn.commit()
    print(f"FTP {len(ftp_rates)}건, 스프레드 {len(spreads)}건, Hurdle Rate {len(hurdle_rates)}건 생성 완료")

def seed_portfolio_summary(conn):
    """포트폴리오 요약 데이터 생성 - 실제 DB 데이터에서 집계"""
    cursor = conn.cursor()
    base_date = datetime.now().strftime('%Y-%m-%d')

    # 기존 데이터 삭제
    cursor.execute("DELETE FROM portfolio_summary")

    # 산업별 요약 - 실제 데이터에서 집계
    cursor.execute("""
        INSERT INTO portfolio_summary
        (summary_id, base_date, segment_type, segment_code, segment_name,
         exposure_count, total_exposure, total_rwa, total_el,
         avg_pd, avg_lgd, weighted_rate, total_revenue, raroc)
        SELECT
            'SUM_IND_' || c.industry_code,
            ?,
            'INDUSTRY',
            c.industry_code,
            c.industry_name,
            COUNT(DISTINCT c.customer_id),
            COALESCE(SUM(f.outstanding_amount), 0),
            COALESCE(SUM(rp.rwa), 0),
            COALESCE(SUM(rp.expected_loss), 0),
            AVG(COALESCE(rp.pit_pd, rp.ttc_pd)),
            AVG(rp.lgd),
            AVG(f.final_rate),
            COALESCE(SUM(f.outstanding_amount * f.final_rate), 0),
            CASE
                WHEN SUM(rp.rwa) * 0.08 > 0
                THEN (SUM(f.outstanding_amount * f.final_rate) - SUM(f.outstanding_amount) * 0.048 - SUM(rp.expected_loss)) / (SUM(rp.rwa) * 0.08)
                ELSE 0
            END
        FROM customer c
        JOIN facility f ON c.customer_id = f.customer_id AND f.status = 'ACTIVE'
        LEFT JOIN loan_application la ON f.application_id = la.application_id
        LEFT JOIN risk_parameter rp ON la.application_id = rp.application_id
        WHERE c.industry_code IS NOT NULL
        GROUP BY c.industry_code, c.industry_name
    """, (base_date,))

    ind_count = cursor.rowcount

    # 등급별 요약 - 실제 데이터에서 집계
    grade_buckets = {
        'AAA_AA': ('AAA~AA 등급', ['AAA', 'AA+', 'AA', 'AA-']),
        'A': ('A 등급', ['A+', 'A', 'A-']),
        'BBB': ('BBB 등급', ['BBB+', 'BBB', 'BBB-']),
        'BB': ('BB 등급', ['BB+', 'BB', 'BB-']),
        'B_Below': ('B 이하', ['B+', 'B', 'B-', 'CCC+', 'CCC', 'CCC-', 'CC', 'C', 'D']),
    }

    rating_count = 0
    for bucket_code, (bucket_name, grades) in grade_buckets.items():
        placeholders = ','.join(['?'] * len(grades))
        cursor.execute(f"""
            INSERT INTO portfolio_summary
            (summary_id, base_date, segment_type, segment_code, segment_name,
             exposure_count, total_exposure, total_rwa, total_el,
             avg_pd, avg_lgd, weighted_rate, total_revenue, raroc)
            SELECT
                'SUM_GRADE_{bucket_code}',
                ?,
                'RATING',
                '{bucket_code}',
                '{bucket_name}',
                COUNT(DISTINCT c.customer_id),
                COALESCE(SUM(f.outstanding_amount), 0),
                COALESCE(SUM(rp.rwa), 0),
                COALESCE(SUM(rp.expected_loss), 0),
                AVG(COALESCE(rp.pit_pd, rp.ttc_pd)),
                AVG(rp.lgd),
                AVG(f.final_rate),
                COALESCE(SUM(f.outstanding_amount * f.final_rate), 0),
                CASE
                    WHEN SUM(rp.rwa) * 0.08 > 0
                    THEN (SUM(f.outstanding_amount * f.final_rate) - SUM(f.outstanding_amount) * 0.048 - SUM(rp.expected_loss)) / (SUM(rp.rwa) * 0.08)
                    ELSE 0
                END
            FROM customer c
            JOIN facility f ON c.customer_id = f.customer_id AND f.status = 'ACTIVE'
            LEFT JOIN loan_application la ON f.application_id = la.application_id
            LEFT JOIN risk_parameter rp ON la.application_id = rp.application_id
            LEFT JOIN credit_rating_result cr ON c.customer_id = cr.customer_id
                AND cr.rating_date = (SELECT MAX(rating_date) FROM credit_rating_result WHERE customer_id = c.customer_id)
            WHERE cr.final_grade IN ({placeholders})
        """, (base_date, *grades))
        rating_count += 1

    conn.commit()
    print(f"포트폴리오 요약 {ind_count + rating_count}건 생성 완료 (실제 데이터 기반)")

def seed_ews_alerts(conn):
    """EWS 경보 데이터 생성"""
    cursor = conn.cursor()

    # 일부 고객에 대해 경보 생성
    cursor.execute("SELECT customer_id, customer_name FROM customer LIMIT 20")
    customers = cursor.fetchall()

    alerts = []
    alert_types = [
        ('FINANCIAL', 'REVENUE_DECLINE', '매출 20% 이상 감소'),
        ('FINANCIAL', 'PROFIT_LOSS', '영업이익 적자 전환'),
        ('FINANCIAL', 'DEBT_INCREASE', '부채비율 급증'),
        ('BEHAVIOR', 'OVERDUE', '연체 발생'),
        ('BEHAVIOR', 'LIMIT_USAGE', '한도 사용률 90% 초과'),
        ('EXTERNAL', 'RATING_DOWN', '외부등급 하락'),
        ('EXTERNAL', 'NEGATIVE_NEWS', '부정적 뉴스 탐지'),
    ]

    for i, (cust_id, cust_name) in enumerate(customers[:10]):
        alert_type, subtype, desc = random.choice(alert_types)
        severity = random.choice(['HIGH', 'MEDIUM', 'LOW'])
        status = random.choice(['OPEN', 'OPEN', 'REVIEWING', 'RESOLVED'])

        alerts.append((
            f'EWS{i+1:05d}', cust_id, None,
            (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d'),
            alert_type, subtype, severity,
            random.uniform(0.1, 0.5), 0.2, f"{cust_name}: {desc}",
            status, None if status != 'RESOLVED' else '조치 완료',
            datetime.now().strftime('%Y-%m-%d %H:%M:%S') if status == 'RESOLVED' else None
        ))

    cursor.executemany("""
        INSERT OR REPLACE INTO ews_alert
        (alert_id, customer_id, facility_id, alert_date, alert_type, alert_subtype,
         severity, indicator_value, threshold_value, description, status,
         action_taken, resolved_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, alerts)

    conn.commit()
    print(f"EWS 경보 {len(alerts)}건 생성 완료")

def main():
    """메인 실행 함수"""
    print("=" * 50)
    print("iM뱅크 CLMS 데모 데이터 생성 시작")
    print("=" * 50)

    # DB 디렉토리 생성
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 기존 DB 삭제
    if DB_PATH.exists():
        DB_PATH.unlink()
        print("기존 데이터베이스 삭제")

    # DB 생성 및 연결
    conn = create_database()
    print("데이터베이스 생성 완료")

    try:
        # 마스터 데이터
        seed_master_data(conn)

        # 고객 및 그룹
        customers = seed_customers(conn, 1000)
        seed_borrower_groups(conn, customers)

        # 여신 데이터
        seed_facilities_and_applications(conn, customers)

        # 담보 데이터
        seed_collateral(conn)

        # 전략계층 데이터
        seed_capital_data(conn)
        seed_capital_budget(conn)
        seed_portfolio_strategy(conn)
        seed_limits(conn)
        seed_stress_scenarios(conn)

        # 전술계층 데이터
        seed_macro_indicators(conn)
        seed_ftp_and_spreads(conn)

        # 기반계층 데이터
        seed_models(conn)
        seed_portfolio_summary(conn)
        seed_ews_alerts(conn)

        print("=" * 50)
        print("데이터 생성 완료!")
        print(f"데이터베이스: {DB_PATH}")
        print("=" * 50)

    finally:
        conn.close()

if __name__ == "__main__":
    main()
