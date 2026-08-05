#!/usr/bin/env python3
"""
여신 보유 고객 대폭 확대
========================
여신 보유 699개사 → 약 2,000개사. 다양성 확보가 목적:
  · 업종 : industry_master 40개 업종 고르게 (기존 쏠림 완화)
  · 지역 : 수도권 45% / 대구경북 35% / 부산경남 20% (수도권 진출 서사)
  · 규모 : 대 3% / 중견 14% / 중소 48% / 개인사업자 35%
  · 한도 : 규모별 로그균등 - SOHO 1~15억 ~ 대기업 300~2,000억
  · 담보 : 부동산·예금·증권·보증·매출채권·동산·IP 혼합 (시설의 70%)

구성: 기존 잠재고객 150개사 전환 + 신규 고객 1,150개사 생성.
차주별 연계 시드를 빠짐없이 생성해 어느 화면에서도 공란이 없게 한다:
  등급(PD)·재무비율·재무제표·수익성(RAROC)·EWS종합·거래행태 12개월·
  뉴스감성 12개월·상장사 시장신호 12개월·자산건전성 분류·ECL·담보(+평가이력)·여신신청

건전성 분포는 기존 캘리브레이션(정상 ~97.6%, NPL ~0.4%, 연체율 30일+ ~0.7%)을
유지한다. 거래행태 월별 추세는 이후 enhance_behavior_history.py 가 일괄 부여.
실행 순서: 본 스크립트 → enhance_behavior_history.py → generate_limit_exposure.py
"""
import random
import sqlite3
import uuid
from datetime import date, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from base_date import AS_OF_STR  # noqa: E402  (2026-07-31)
ECL_CALC_DATE = AS_OF_STR[:8] + "01"   # ECL 은 매월 1일 스냅샷 케이던스를 따른다

DB = str(Path(__file__).parent / "imbank_demo.db")
random.seed(20260805)

N_NEW_CUSTOMERS = 1150
N_CONVERT_PROSPECTS = 150

REGIONS = [("CAPITAL", 0.45), ("DAEGU_GB", 0.35), ("BUSAN_GN", 0.20)]
REGION_ADDR = {
    "CAPITAL": ["서울시 강남구", "서울시 중구", "경기도 성남시", "경기도 화성시", "인천시 연수구"],
    "DAEGU_GB": ["대구시 동구", "대구시 달서구", "경북 구미시", "경북 포항시", "경북 경산시"],
    "BUSAN_GN": ["부산시 해운대구", "부산시 강서구", "경남 창원시", "경남 김해시", "울산시 남구"],
}
SIZES = [("LARGE", 0.03), ("MEDIUM", 0.14), ("SMALL", 0.48), ("SOHO", 0.35)]
# 규모별 시설당 승인액 범위 (원)
AMOUNT_RANGE = {
    "LARGE": (300e8, 2000e8), "MEDIUM": (50e8, 400e8),
    "SMALL": (10e8, 90e8), "SOHO": (1e8, 15e8),
}
GRADE_BUCKETS = [  # (등급 후보, 가중치) - 중신용(BBB+ 이하) 비중 확대
    (["A+", "A", "A-"], 0.15),
    (["BBB+", "BBB", "BBB-"], 0.45),
    (["BB+", "BB", "BB-"], 0.30),
    (["B+", "B", "B-"], 0.08),
    (["CCC"], 0.02),
]
GRADE_PD = {
    "A+": 0.0008, "A": 0.0012, "A-": 0.0018,
    "BBB+": 0.0028, "BBB": 0.0042, "BBB-": 0.0065,
    "BB+": 0.0098, "BB": 0.0150, "BB-": 0.0225,
    "B+": 0.0340, "B": 0.0510, "B-": 0.0765, "CCC": 0.1150,
}
COLLATERAL_MIX = [
    ("REAL_ESTATE", 0.35, 0.70), ("DEPOSIT", 0.15, 1.00), ("SECURITIES", 0.15, 0.60),
    ("GUARANTEE", 0.12, 0.90), ("RECEIVABLES", 0.10, 0.50),
    ("MOVABLE_PROPERTY", 0.08, 0.40), ("IP_RIGHTS", 0.05, 0.30),
]
PREFIXES = ['한국', '대한', '동아', '태평양', '신성', '우진', '한빛', '글로벌', '아신', '코리아',
            '제일', '삼진', '현진', '광명', '에스제이', '포스', '한울', '롯데', '두성', '금호',
            '효성', '동부', '대원', '쌍용', '진흥', '동양', '태영', '영풍', '세아', '동국',
            '미래', '청담', '가온', '누리', '해성', '경일', '서린', '남도', '북극성', '중원']
SUFFIXES = ['테크', '시스템', '솔루션', '엔지니어링', '산업', '물산', '상사', '인터내셔널', '홀딩스', '정공',
            '전자', '화학', '건설', '개발', '에너지', '바이오', '메디컬', '파마', '로지스', '커머스',
            '푸드', '스틸', '모빌리티', '반도체', '디스플레이', '섬유', '기계', '정보통신', '유통', '자원']
MONTHS = ["2025-08", "2025-09", "2025-10", "2025-11", "2025-12", "2026-01",
          "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07"]


def wchoice(pairs):
    return random.choices([p[0] for p in pairs], weights=[p[1] for p in pairs])[0]


def uid(prefix=""):
    return f"{prefix}{uuid.uuid4().hex[:10].upper()}"


def d(base: str, delta_days: int) -> str:
    y, m, dd = map(int, base.split("-"))
    return (date(y, m, dd) + timedelta(days=delta_days)).isoformat()


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    industries = cur.execute(
        "SELECT industry_code, industry_name, risk_grade FROM industry_master").fetchall()
    used_names = {r[0] for r in cur.execute("SELECT customer_name FROM customer")}
    used_biz = {r[0] for r in cur.execute("SELECT biz_reg_no FROM customer")}
    next_fac = int(cur.execute(
        "SELECT MAX(CAST(substr(facility_id, 4) AS INTEGER)) FROM facility WHERE facility_id LIKE 'FAC0%'"
    ).fetchone()[0] or 1200) + 1

    # ── 대상 차주 목록 구성 ──────────────────────────────
    prospects = [r[0] for r in cur.execute("""
        SELECT c.customer_id FROM customer c
        WHERE NOT EXISTS (SELECT 1 FROM facility f
                          WHERE f.customer_id = c.customer_id AND f.status = 'ACTIVE')
          AND c.customer_id LIKE 'CUST%'
        ORDER BY c.customer_id LIMIT ?
    """, (N_CONVERT_PROSPECTS,)).fetchall()]

    borrowers = []          # (cust_id, size, region, industry, listing, is_new)
    for cid in prospects:
        size, region, ind_code, ind_name, listing = cur.execute("""
            SELECT size_category, region, industry_code, industry_name, listing_status
            FROM customer WHERE customer_id = ?""", (cid,)).fetchone()
        borrowers.append((cid, size or "SMALL", region or "DAEGU_GB",
                          (ind_code, ind_name), listing or "PRIVATE", False))

    new_customers = []
    start_no = 1001
    for i in range(N_NEW_CUSTOMERS):
        cid = f"CUST{start_no + i:05d}"
        size = wchoice(SIZES)
        region = wchoice(REGIONS)
        ind = random.choice(industries)
        # 회사명 유일화
        for _ in range(50):
            name = f"(주){random.choice(PREFIXES)}{random.choice(SUFFIXES)}"
            if name not in used_names:
                break
        else:
            name = f"(주){random.choice(PREFIXES)}{random.choice(SUFFIXES)}{random.randint(2, 9)}"
        used_names.add(name)
        while True:
            biz = f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(10000, 99999)}"
            if biz not in used_biz:
                used_biz.add(biz)
                break
        listing = ("KOSPI" if size == "LARGE" and random.random() < 0.6 else
                   "KOSDAQ" if size in ("LARGE", "MEDIUM") and random.random() < 0.35 else
                   "PRIVATE")
        asset = {"LARGE": random.uniform(3000e8, 3e12), "MEDIUM": random.uniform(500e8, 3000e8),
                 "SMALL": random.uniform(50e8, 500e8), "SOHO": random.uniform(5e8, 60e8)}[size]
        revenue = asset * random.uniform(0.4, 1.1)
        new_customers.append((
            cid, name, None, biz, f"110111-{random.randint(1000000, 9999999)}",
            d("2000-01-01", random.randint(0, 8500)), ind[0], ind[1], size,
            round(asset, 0), round(revenue, 0), random.randint(5, 3000), listing,
            f"{random.choice(REGION_ADDR[region])}", region,
            f"RM{random.randint(1, 150):03d}", f"BR{random.randint(1, 50):03d}",
        ))
        borrowers.append((cid, size, region, (ind[0], ind[1]), listing, True))

    cur.executemany("""
        INSERT INTO customer (customer_id, customer_name, customer_name_eng, biz_reg_no,
                              corp_reg_no, establish_date, industry_code, industry_name,
                              size_category, asset_size, revenue_size, employee_count,
                              listing_status, address, region, rm_id, branch_code)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, new_customers)
    print(f"신규 고객 {len(new_customers)}개사 + 잠재고객 전환 {len(prospects)}개사")

    # ── 차주별 연계 시드 ────────────────────────────────
    apps, facs, cols, colvals, ratings, profs, ewss = [], [], [], [], [], [], []
    txns, newsm, mkts, fins, stmts, clss, ecls = [], [], [], [], [], [], []
    tot_exposure = 0.0

    for cid, size, region, ind, listing, is_new in borrowers:
        # 건전성 시나리오
        r = random.random()
        if r < 0.004:       health = "NPL"
        elif r < 0.016:     health = "PRECAUTIONARY"
        elif r < 0.030:     health = "EARLY"       # 경증 연체 (1~29일)
        else:               health = "CLEAN"

        bucket = wchoice(GRADE_BUCKETS)
        grade = random.choice(bucket)
        if health == "NPL":
            grade = random.choice(["B-", "CCC"])
        elif health == "PRECAUTIONARY":
            grade = random.choice(["BB-", "B+", "B"])
        pd_v = GRADE_PD[grade]

        n_fac = random.choices([1, 2, 3, 4], weights=[0.45, 0.30, 0.17, 0.08])[0]
        lo, hi = AMOUNT_RANGE[size]
        cust_exposure = 0.0
        first_fac_id = None
        for j in range(n_fac):
            approved = lo * (hi / lo) ** random.random()          # 로그균등
            outstanding = approved * random.uniform(0.55, 0.95)
            cust_exposure += outstanding
            fac_id = f"FAC{next_fac:06d}"
            next_fac += 1
            if first_fac_id is None:
                first_fac_id = fac_id
            app_id = f"APP_{uid()}"
            contract = d("2024-01-01", random.randint(0, 930))     # ~2026-07
            maturity = d(contract, random.randint(365, 1825))
            spread = {"A": 2.2, "B": 3.2, "C": 4.2}.get(grade[0], 3.2) + random.uniform(-0.3, 1.0)
            final_rate = round((3.4 + spread) / 100, 6)

            dpd = 0
            fac_cls = "NORMAL"
            if j == 0:  # 대표 시설에 건전성 시나리오 반영
                if health == "NPL":
                    dpd = random.randint(95, 320)
                    fac_cls = "SUBSTANDARD" if dpd < 180 else "DOUBTFUL"
                elif health == "PRECAUTIONARY":
                    dpd = random.randint(32, 75)
                    fac_cls = "PRECAUTIONARY"
                elif health == "EARLY":
                    dpd = random.randint(3, 25)

            product = random.choice(["CORP_WORK", "CORP_TERM", "CORP_FACILITY", "CORP_TRADE"])
            apps.append((app_id, d(contract, -random.randint(10, 45)), "NEW", cid, None,
                         product, approved * random.uniform(1.0, 1.2), 36, (3.4 + spread),
                         "WORKING_CAPITAL", None, None, None, None, "DISBURSED", "COMPLETED",
                         "NORMAL", None, f"BR{random.randint(1, 50):03d}"))
            facs.append((fac_id, app_id, cid, product.replace("CORP_", ""), product, "KRW",
                         approved, approved, outstanding, approved - outstanding,
                         random.choice(["FIXED", "FLOATING"]), random.choice(["CD91", "COFIX"]),
                         round(spread / 100, 6), final_rate, contract, maturity, "ACTIVE",
                         dpd, dpd, d(AS_OF_STR, -dpd) if dpd else None, fac_cls))

            # 담보 (70%)
            if random.random() < 0.70:
                ctype, _w, recog = COLLATERAL_MIX[random.choices(
                    range(len(COLLATERAL_MIX)), weights=[c[1] for c in COLLATERAL_MIX])[0]]
                value = outstanding * random.uniform(0.4, 1.3)
                col_id = f"COL_{uid()}"
                cols.append((col_id, app_id, fac_id, ctype, None, value, value,
                             round(outstanding / value * 100, 1), d(AS_OF_STR, -random.randint(10, 200)),
                             1, value, value, recog, value * recog, 0, value * recog - outstanding,
                             None, d(AS_OF_STR, -random.randint(10, 200)), None, None))
                prev = value * random.uniform(0.95, 1.08)
                colvals.append((f"CVH_{uid()}", col_id, "2026-01-15", "REGULAR", "MODEL",
                                prev, value, round((value - prev) / prev * 100, 2), "STABLE",
                                round(outstanding / prev * 100, 1), round(outstanding / value * 100, 1),
                                0))

            # 분류·ECL (시설 단위)
            cls_rate = {"NORMAL": 0.0085, "PRECAUTIONARY": 0.07,
                        "SUBSTANDARD": 0.20, "DOUBTFUL": 0.50}[fac_cls]
            req = outstanding * cls_rate
            clss.append((f"AC_{uid()}", fac_id, cid, AS_OF_STR, fac_cls, "NORMAL", dpd,
                         "NORMAL", "NORMAL", "DPD" if dpd >= 30 else "PD",
                         outstanding, cls_rate, req, req * random.uniform(0.85, 1.0),
                         req * random.uniform(0.0, 0.15), "BATCH", None))
            lgd = random.uniform(0.30, 0.50)
            stage = 3 if fac_cls in ("SUBSTANDARD", "DOUBTFUL") else \
                    2 if fac_cls == "PRECAUTIONARY" else 1
            ecl = lgd * outstanding * random.uniform(0.6, 0.9) if stage == 3 else \
                  pd_v * lgd * outstanding * (2.2 if stage == 2 else 1.0)
            ecls.append((f"ECL_{uid()}", fac_id, cid, ECL_CALC_DATE, stage,
                         1 if stage >= 2 else 0, "DPD_30" if stage >= 2 else None,
                         pd_v, pd_v, lgd, outstanding, random.randint(6, 48),
                         ecl, 1.0, ecl, ecl * random.uniform(0.8, 1.0),
                         ecl * random.uniform(0.0, 0.2), req, ecl - req))

        tot_exposure += cust_exposure

        # 전환 잠재고객은 고객 단위 시드(등급·EWS·재무·수익성·월별)가 이미 존재한다
        if not is_new:
            continue

        # 등급
        ratings.append((f"RAT_{uid()}", cid, first_fac_id and None, d("2025-03-01", random.randint(0, 480)),
                        "CORP_RATING_V3", "3.1", random.uniform(40, 95), grade, 0, pd_v,
                        None, None, None, None, None))

        # EWS 종합
        if health == "NPL":
            score = random.uniform(22, 42)
        elif health == "PRECAUTIONARY":
            score = random.uniform(40, 60)
        elif health == "EARLY":
            score = random.uniform(55, 72)
        else:
            score = random.uniform(62, 95)
        risk = "LOW" if score >= 72 else "MEDIUM" if score >= 55 else "HIGH" if score >= 33 else "CRITICAL"
        ews_grade = {"LOW": "NORMAL", "MEDIUM": "WATCH", "HIGH": "WARNING", "CRITICAL": "CRITICAL"}[risk]
        ewss.append((f"EWS_{uid()}", cid, AS_OF_STR, score * random.uniform(0.9, 1.1),
                     score * random.uniform(0.9, 1.1), score * random.uniform(0.85, 1.1),
                     score * random.uniform(0.9, 1.1), round(score, 1), risk, pd_v,
                     None, score * random.uniform(0.9, 1.1), score * random.uniform(0.9, 1.1),
                     None, score * random.uniform(0.9, 1.1), ews_grade, "STABLE",
                     round(score + random.uniform(-4, 4), 1)))

        # 거래행태 12개월 (기본 수준 + 소노이즈 - 추세는 enhance 스크립트가 부여)
        base_util = random.uniform(0.72, 0.93) if health in ("NPL", "PRECAUTIONARY") else \
                    random.uniform(0.20, 0.60)
        for m in MONTHS:
            txns.append((cid, m, cust_exposure * random.uniform(0.02, 0.15),
                         min(0.97, max(0.03, base_util + random.gauss(0, 0.02))),
                         random.randint(5, 20) if health != "CLEAN" else random.randint(0, 4),
                         random.random() < 0.7,
                         random.uniform(0.05, 0.5) if health != "CLEAN" else random.uniform(0.0, 0.2),
                         random.randint(20, 400),
                         random.randint(1, 6) if health in ("NPL", "PRECAUTIONARY") else 0))

        # 뉴스 감성 12개월
        senti = random.uniform(-0.35, -0.05) if health in ("NPL", "PRECAUTIONARY") else \
                random.uniform(-0.05, 0.25)
        for m in MONTHS:
            s = max(-0.95, min(0.95, senti + random.gauss(0, 0.08)))
            neg = max(0.0, min(1.0, 0.5 - s * 0.8 + random.gauss(0, 0.05)))
            newsm.append((cid, m, random.randint(0, 14), round(s, 3), round(neg, 3),
                          round(max(0.0, 1 - neg - random.uniform(0.1, 0.4)), 3),
                          random.choice(["INDUSTRY", "OPERATIONAL", "FINANCE", "LEGAL", "MANAGEMENT"])))

        # 상장사 시장신호 12개월
        if listing in ("KOSPI", "KOSDAQ"):
            dd0 = random.uniform(1.2, 2.4) if health in ("NPL", "PRECAUTIONARY") else random.uniform(2.4, 5.5)
            cds0 = random.uniform(180, 380) if dd0 < 2.4 else random.uniform(60, 180)
            for k, m in enumerate(MONTHS):
                dd_m = max(0.3, dd0 + random.gauss(0, 0.15) - (0.04 * k if health != "CLEAN" else 0))
                mkts.append((cid, m, random.uniform(-15, 12), cds0 * random.uniform(0.9, 1.1),
                             cds0 * random.uniform(0.7, 0.95), round(dd_m, 2),
                             min(0.5, pd_v * random.uniform(1.5, 40)),
                             random.uniform(500e8, 5e12), random.uniform(0.15, 0.6)))

        # 재무비율 + 재무제표 (2025 회계연도)
        debt = random.uniform(180, 420) if health in ("NPL", "PRECAUTIONARY") else random.uniform(30, 220)
        icr = random.uniform(0.2, 1.4) if health in ("NPL", "PRECAUTIONARY") else random.uniform(1.2, 12)
        fins.append((f"FR_{uid()}", cid, 2025, round(debt, 1), random.uniform(70, 250),
                     round(icr, 2), random.uniform(10, 60), round(icr * random.uniform(0.7, 1.1), 2),
                     random.uniform(-5, 25), random.uniform(-8, 18), random.uniform(-3, 12),
                     random.uniform(0.5, 9), random.uniform(-20, 30), random.uniform(-25, 35),
                     round(random.uniform(0.8, 4.5) if health == "CLEAN" else random.uniform(0.4, 2.0), 2),
                     "HIGH" if health in ("NPL", "PRECAUTIONARY") else "NORMAL", AS_OF_STR))
        asset_w = dict(zip(["LARGE", "MEDIUM", "SMALL", "SOHO"], [1.0, 1.0, 1.0, 1.0]))
        arow = cur.execute("SELECT asset_size, revenue_size FROM customer WHERE customer_id=?",
                           (cid,)).fetchone()
        a_sz = (arow[0] or 100e8) * asset_w[size]
        rev = arow[1] or a_sz * 0.7
        equity = a_sz / (1 + debt / 100)
        stmts.append((f"FS_{uid()}", cid, 2025, "AUDITED", rev, rev * random.uniform(0.02, 0.12),
                      rev * random.uniform(0.05, 0.16), rev * random.uniform(0.01, 0.04),
                      rev * random.uniform(0.005, 0.08), a_sz, a_sz * random.uniform(0.3, 0.6),
                      a_sz - equity, (a_sz - equity) * random.uniform(0.3, 0.6),
                      (a_sz - equity) * random.uniform(0.5, 0.9), equity,
                      equity * random.uniform(0.2, 0.7), a_sz * random.uniform(0.05, 0.2),
                      rev * random.uniform(0.03, 0.13), 1, "DART"))

        # 수익성
        econ_cap = cust_exposure * 0.08
        revenue_loan = cust_exposure * (0.034 + random.uniform(0.008, 0.03))
        el = pd_v * 0.4 * cust_exposure
        profit = revenue_loan * random.uniform(0.30, 0.45) - el
        raroc = max(-8.0, min(28.0, profit / econ_cap * 100 if econ_cap else 8.0))
        profs.append((f"PR_{uid()}", cid, AS_OF_STR, revenue_loan, revenue_loan * 0.55, el,
                      econ_cap * 0.1, profit, cust_exposure * 0.01, cust_exposure * 0.006,
                      cust_exposure * 0.004, cust_exposure * 0.003, cust_exposure * 0.001,
                      cust_exposure * 0.002, 0, 0, 0, revenue_loan * 1.05, revenue_loan * 0.6,
                      profit, econ_cap, round(raroc, 2), random.uniform(30, 90),
                      random.uniform(0.5, 0.95), random.uniform(0.1, 0.8), random.uniform(0.05, 0.6)))

    # ── 일괄 INSERT ─────────────────────────────────────
    cur.executemany("""INSERT INTO loan_application
        (application_id, application_date, application_type, customer_id, group_id, product_code,
         requested_amount, requested_tenor, requested_rate, purpose_code, purpose_detail,
         collateral_type, collateral_value, guarantee_type, status, current_stage, priority,
         assigned_to, branch_code) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", apps)
    cur.executemany("""INSERT INTO facility
        (facility_id, application_id, customer_id, facility_type, product_code, currency_code,
         approved_amount, current_limit, outstanding_amount, available_amount, rate_type,
         base_rate_code, spread, final_rate, contract_date, maturity_date, status,
         dpd, max_dpd_12m, first_delinquency_date, classification)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", facs)
    cur.executemany("""INSERT INTO collateral
        (collateral_id, application_id, facility_id, collateral_type, collateral_subtype,
         original_value, current_value, ltv, valuation_date, priority_rank, appraisal_value,
         market_value, recognition_ratio, recognized_value, prior_lien_amount, collateral_margin,
         appraiser, last_appraisal_date, location_address, description)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", cols)
    cur.executemany("""INSERT INTO collateral_valuation_history
        (valuation_id, collateral_id, valuation_date, valuation_type, valuation_source,
         previous_value, current_value, change_pct, market_condition, ltv_before, ltv_after,
         alert_triggered) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", colvals)
    cur.executemany("""INSERT INTO credit_rating_result
        (rating_id, customer_id, application_id, rating_date, model_id, model_version,
         raw_score, final_grade, grade_notch, pd_value, override_grade, override_reason,
         override_by, effective_from, effective_to) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", ratings)
    cur.executemany("""INSERT INTO ews_composite_score
        (score_id, customer_id, score_date, financial_score, operational_score, external_score,
         supply_chain_score, composite_score, risk_level, predicted_default_prob, recommendation,
         transaction_score, public_registry_score, market_score, news_score, ews_grade,
         score_trend, previous_composite) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", ewss)
    cur.executemany("""INSERT INTO ews_transaction_behavior
        (customer_id, reference_month, avg_balance, limit_utilization, payment_delay_days,
         salary_transfer, deposit_outflow_rate, transaction_count, overdraft_count)
        VALUES (?,?,?,?,?,?,?,?,?)""", txns)
    cur.executemany("""INSERT INTO ews_news_sentiment_monthly
        (customer_id, reference_month, article_count, avg_sentiment, negative_ratio,
         positive_ratio, dominant_category) VALUES (?,?,?,?,?,?,?)""", newsm)
    cur.executemany("""INSERT INTO ews_market_signal
        (customer_id, reference_month, stock_price_change, cds_spread, bond_spread,
         distance_to_default, implied_pd, market_cap, volatility_30d)
        VALUES (?,?,?,?,?,?,?,?,?)""", mkts)
    cur.executemany("""INSERT INTO financial_ratio
        (ratio_id, customer_id, fiscal_year, debt_ratio, current_ratio, ier, debt_dependency,
         dscr, ocf_ratio, op_margin, roa, roe, revenue_growth, op_growth, altman_z,
         risk_signal, calc_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", fins)
    cur.executemany("""INSERT INTO financial_statement
        (stmt_id, customer_id, fiscal_year, stmt_type, revenue, operating_profit, ebitda,
         interest_expense, net_profit, total_assets, current_assets, total_debt, current_debt,
         total_borrowing, equity, retained_earning, working_capital, operating_cf, audited, source)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", stmts)
    cur.executemany("""INSERT INTO customer_profitability
        (profitability_id, customer_id, calculation_date, loan_revenue, loan_cost, loan_el,
         loan_capital_cost, loan_profit, deposit_revenue, deposit_cost, deposit_profit,
         fee_revenue, fee_cost, fee_profit, fx_revenue, fx_cost, fx_profit, total_revenue,
         total_cost, total_profit, economic_capital, raroc, clv_score, retention_probability,
         cross_sell_potential, churn_risk_score) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", profs)
    cur.executemany("""INSERT INTO asset_classification
        (class_id, facility_id, customer_id, base_date, classification, prev_class, dpd,
         pd_based_class, ews_based_class, final_class_basis, exposure_at_class, provision_rate,
         required_provision, existing_provision, provision_gap, classified_by, override_reason)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", clss)
    cur.executemany("""INSERT INTO ecl_calculation
        (ecl_id, facility_id, customer_id, calc_date, stage, sicr_triggered, sicr_reason,
         pd_original, pd_current, lgd, ead, remaining_tenor_months, ecl_base, macro_adj_factor,
         ecl_final, prev_ecl, ecl_change, existing_provision, provision_gap)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", ecls)

    con.commit()
    cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    # ── 결과 요약 ──
    n_borrowers = cur.execute("""
        SELECT COUNT(DISTINCT customer_id) FROM facility WHERE status='ACTIVE'""").fetchone()[0]
    tot = cur.execute("""
        SELECT SUM(outstanding_amount) FROM facility WHERE status='ACTIVE'""").fetchone()[0]
    npl = cur.execute("""
        SELECT SUM(CASE WHEN classification IN ('SUBSTANDARD','DOUBTFUL','LOSS')
                   THEN outstanding_amount END) * 100.0 / SUM(outstanding_amount)
        FROM facility WHERE status='ACTIVE'""").fetchone()[0]
    dq = cur.execute("""
        SELECT SUM(CASE WHEN dpd >= 30 THEN outstanding_amount END) * 100.0 / SUM(outstanding_amount)
        FROM facility WHERE status='ACTIVE'""").fetchone()[0]
    print(f"여신 보유 차주: {n_borrowers:,}개사 · 총여신 {tot/1e12:.1f}조 · "
          f"NPL {npl:.2f}% · 연체율(30+) {dq:.3f}%")
    print(f"신설 시설 {len(facs):,}건 · 담보 {len(cols):,}건")


if __name__ == "__main__":
    main()
