"""
Phase 1 시드 데이터 생성 스크립트
===================================
재무제표 3개년, 재무비율, 그룹보증, 코베넌트 데이터 생성

실행: python database/generate_phase1_data.py
"""
import sqlite3
import random
import math
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "imbank_demo.db"

random.seed(42)

# ============================================================
# 산업별 재무비율 분포 파라미터 (현실적 기준)
# ============================================================
INDUSTRY_PARAMS = {
    "C10": {"op_margin_mu": 5.5,  "op_margin_sig": 3.0,  "debt_ratio_mu": 120, "debt_sig": 60},  # 식품
    "C20": {"op_margin_mu": 8.0,  "op_margin_sig": 4.0,  "debt_ratio_mu": 100, "debt_sig": 50},  # 화학
    "C26": {"op_margin_mu": 10.0, "op_margin_sig": 5.0,  "debt_ratio_mu": 90,  "debt_sig": 45},  # 전자
    "C29": {"op_margin_mu": 6.0,  "op_margin_sig": 3.5,  "debt_ratio_mu": 130, "debt_sig": 70},  # 기계
    "C30": {"op_margin_mu": 4.0,  "op_margin_sig": 3.0,  "debt_ratio_mu": 150, "debt_sig": 80},  # 자동차
    "F64": {"op_margin_mu": 15.0, "op_margin_sig": 5.0,  "debt_ratio_mu": 300, "debt_sig": 100}, # 금융(레버리지 높음)
    "G46": {"op_margin_mu": 3.0,  "op_margin_sig": 2.0,  "debt_ratio_mu": 180, "debt_sig": 90},  # 도소매
    "F41": {"op_margin_mu": 7.0,  "op_margin_sig": 4.0,  "debt_ratio_mu": 200, "debt_sig": 100}, # 건설
    "H49": {"op_margin_mu": 5.0,  "op_margin_sig": 3.0,  "debt_ratio_mu": 160, "debt_sig": 70},  # 운수
    "I56": {"op_margin_mu": 4.0,  "op_margin_sig": 3.5,  "debt_ratio_mu": 140, "debt_sig": 80},  # 음식점
    "J58": {"op_margin_mu": 12.0, "op_margin_sig": 6.0,  "debt_ratio_mu": 80,  "debt_sig": 40},  # IT/SW
    "K65": {"op_margin_mu": 18.0, "op_margin_sig": 6.0,  "debt_ratio_mu": 250, "debt_sig": 80},  # 보험
    "M70": {"op_margin_mu": 9.0,  "op_margin_sig": 4.0,  "debt_ratio_mu": 100, "debt_sig": 50},  # 전문서비스
    "L68": {"op_margin_mu": 20.0, "op_margin_sig": 8.0,  "debt_ratio_mu": 220, "debt_sig": 90},  # 부동산
    "Q86": {"op_margin_mu": 6.0,  "op_margin_sig": 3.0,  "debt_ratio_mu": 110, "debt_sig": 55},  # 의료
    "E35": {"op_margin_mu": 8.0,  "op_margin_sig": 4.0,  "debt_ratio_mu": 120, "debt_sig": 60},  # 전기
}

DEFAULT_PARAMS = {"op_margin_mu": 6.0, "op_margin_sig": 3.5, "debt_ratio_mu": 140, "debt_sig": 70}

# 규모별 자산·매출 배율
SIZE_SCALE = {
    "LARGE":  {"asset_base": 300_000_000_000, "revenue_base": 200_000_000_000},
    "MEDIUM": {"asset_base": 80_000_000_000,  "revenue_base": 50_000_000_000},
    "SMALL":  {"asset_base": 15_000_000_000,  "revenue_base": 10_000_000_000},
    "SOHO":   {"asset_base": 3_000_000_000,   "revenue_base": 2_000_000_000},
}


def gauss_clamp(mu, sigma, low, high):
    return max(low, min(high, random.gauss(mu, sigma)))


def generate_financial_statements(conn):
    """고객별 3개년 재무제표 생성"""
    print("  재무제표 생성 중...")
    cur = conn.cursor()

    customers = cur.execute("""
        SELECT customer_id, industry_code, size_category, asset_size, revenue_size
        FROM customer
    """).fetchall()

    stmts_inserted = 0
    ratios_inserted = 0

    for cust in customers:
        cid, ind_code, size_cat, asset_size, revenue_size = cust
        params = INDUSTRY_PARAMS.get(ind_code, DEFAULT_PARAMS)
        scale  = SIZE_SCALE.get(size_cat, SIZE_SCALE["SMALL"])

        # 기준 자산/매출 (customer 테이블 vs 규모 배율 중 큰 값)
        base_asset   = max(asset_size or 0, scale["asset_base"]) * random.uniform(0.7, 1.3)
        base_revenue = max(revenue_size or 0, scale["revenue_base"]) * random.uniform(0.7, 1.3)

        prev_stmt = None

        for year_offset, fiscal_year in enumerate([2023, 2024, 2025]):
            # 매출 성장률 (-5% ~ +15%)
            growth = 1 + gauss_clamp(0.05, 0.08, -0.15, 0.25)
            if year_offset == 0:
                revenue = base_revenue
            else:
                revenue = revenue * growth

            # 영업이익
            op_margin_pct = gauss_clamp(
                params["op_margin_mu"], params["op_margin_sig"], -5.0, 30.0
            )
            operating_profit = revenue * (op_margin_pct / 100)
            ebitda = operating_profit * gauss_clamp(1.15, 0.05, 1.0, 1.4)

            # 재무상태표
            asset_growth = 1 + gauss_clamp(0.04, 0.06, -0.10, 0.20)
            if year_offset == 0:
                total_assets = base_asset
            else:
                total_assets = total_assets * asset_growth

            current_assets = total_assets * gauss_clamp(0.40, 0.08, 0.20, 0.65)
            debt_ratio = gauss_clamp(
                params["debt_ratio_mu"], params["debt_sig"], 30.0, 500.0
            )
            equity = total_assets / (1 + debt_ratio / 100)
            total_debt = total_assets - equity
            current_debt = total_debt * gauss_clamp(0.45, 0.10, 0.20, 0.70)
            total_borrowing = total_debt * gauss_clamp(0.55, 0.10, 0.30, 0.80)
            retained_earning = equity * gauss_clamp(0.30, 0.10, -0.10, 0.60)
            working_capital = current_assets - current_debt
            interest_expense = total_borrowing * gauss_clamp(0.045, 0.01, 0.02, 0.08)
            net_profit = operating_profit * gauss_clamp(0.70, 0.10, -0.50, 0.95)
            operating_cf = operating_profit * gauss_clamp(0.85, 0.15, 0.40, 1.30)

            stmt_id = f"FS_{cid}_{fiscal_year}"
            source = random.choice(["KED", "DART", "직접제출"])
            audited = 1 if (size_cat in ("LARGE", "MEDIUM") or random.random() > 0.6) else 0

            cur.execute("""
                INSERT OR IGNORE INTO financial_statement
                (stmt_id, customer_id, fiscal_year, stmt_type,
                 revenue, operating_profit, ebitda, interest_expense, net_profit,
                 total_assets, current_assets, total_debt, current_debt,
                 total_borrowing, equity, retained_earning, working_capital,
                 operating_cf, audited, source)
                VALUES (?,?,?,'ANNUAL',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                stmt_id, cid, fiscal_year,
                round(revenue, 0), round(operating_profit, 0), round(ebitda, 0),
                round(interest_expense, 0), round(net_profit, 0),
                round(total_assets, 0), round(current_assets, 0),
                round(total_debt, 0), round(current_debt, 0),
                round(total_borrowing, 0), round(equity, 0),
                round(retained_earning, 0), round(working_capital, 0),
                round(operating_cf, 0), audited, source
            ))
            stmts_inserted += 1

            # 재무비율 산출
            _debt_ratio   = round(total_debt / equity * 100, 2) if equity > 0 else None
            _current_ratio = round(current_assets / current_debt * 100, 2) if current_debt > 0 else None
            _ier           = round(operating_profit / interest_expense, 2) if interest_expense > 0 else None
            _debt_dep      = round(total_borrowing / total_assets * 100, 2) if total_assets > 0 else None
            annual_principal = total_borrowing * 0.12
            denom = annual_principal + interest_expense
            _dscr = round(ebitda / denom, 4) if denom > 0 else None
            _ocf  = round(operating_cf / total_debt * 100, 2) if total_debt > 0 else None
            _op_margin = round(operating_profit / revenue * 100, 2) if revenue > 0 else None
            _roa = round(net_profit / total_assets * 100, 2) if total_assets > 0 else None
            _roe = round(net_profit / equity * 100, 2) if equity > 0 else None

            # YoY 성장률
            _rev_growth = None
            _op_growth  = None
            if prev_stmt:
                prev_rev = prev_stmt.get("revenue", 0)
                prev_op  = prev_stmt.get("operating_profit", 0)
                if prev_rev and prev_rev != 0:
                    _rev_growth = round((revenue - prev_rev) / abs(prev_rev) * 100, 2)
                if prev_op and prev_op != 0:
                    _op_growth = round((operating_profit - prev_op) / abs(prev_op) * 100, 2)

            # Altman Z'
            x1 = working_capital / total_assets
            x2 = retained_earning / total_assets
            x3 = operating_profit / total_assets
            x4 = equity / total_debt if total_debt > 0 else 0
            x5 = revenue / total_assets
            z = 0.717*x1 + 0.847*x2 + 3.107*x3 + 0.420*x4 + 0.998*x5
            z = round(z, 4)
            signal = "SAFE" if z > 2.9 else "GREY" if z >= 1.23 else "DANGER"

            ratio_id = f"FR_{cid}_{fiscal_year}"
            cur.execute("""
                INSERT OR IGNORE INTO financial_ratio
                (ratio_id, customer_id, fiscal_year,
                 debt_ratio, current_ratio, ier, debt_dependency, dscr, ocf_ratio,
                 op_margin, roa, roe, revenue_growth, op_growth, altman_z, risk_signal)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                ratio_id, cid, fiscal_year,
                _debt_ratio, _current_ratio, _ier, _debt_dep, _dscr, _ocf,
                _op_margin, _roa, _roe, _rev_growth, _op_growth, z, signal
            ))
            ratios_inserted += 1

            prev_stmt = {
                "revenue": revenue,
                "operating_profit": operating_profit,
            }

    conn.commit()
    print(f"    재무제표 {stmts_inserted}건, 재무비율 {ratios_inserted}건 생성 완료")


def generate_group_guarantees(conn):
    """계열사 간 보증 관계 생성"""
    print("  그룹 보증 관계 생성 중...")
    cur = conn.cursor()

    # 그룹별 멤버 조회
    groups = cur.execute("""
        SELECT DISTINCT group_id FROM borrower_group_member
    """).fetchall()

    guarantee_types = ["JOINT", "INDIVIDUAL", "MORTGAGE"]
    inserted = 0

    for (group_id,) in groups:
        members = cur.execute("""
            SELECT customer_id FROM borrower_group_member
            WHERE group_id = ?
        """, (group_id,)).fetchall()
        member_ids = [m[0] for m in members]

        if len(member_ids) < 2:
            continue

        # 그룹 내 랜덤 보증 관계 생성 (멤버 수의 60% 확률)
        n_guarantees = max(1, int(len(member_ids) * 0.6))
        for _ in range(min(n_guarantees, len(member_ids))):
            if len(member_ids) < 2:
                break
            guarantor   = random.choice(member_ids)
            others      = [m for m in member_ids if m != guarantor]
            beneficiary = random.choice(others)

            # 피보증인의 여신 조회
            facility = cur.execute("""
                SELECT outstanding_amount FROM facility
                WHERE customer_id = ? AND status = 'ACTIVE'
                ORDER BY outstanding_amount DESC LIMIT 1
            """, (beneficiary,)).fetchone()
            guarantee_amount = (facility[0] * random.uniform(0.5, 1.0)) if facility else random.uniform(1e8, 5e9)

            gid = f"GG_{group_id}_{guarantor[:6]}_{beneficiary[:6]}"
            eff_date = date(2020, 1, 1) + timedelta(days=random.randint(0, 1500))

            cur.execute("""
                INSERT OR IGNORE INTO group_guarantee
                (guarantee_id, group_id, guarantor_id, beneficiary_id,
                 guarantee_type, guarantee_amount, effective_date, status)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                gid, group_id, guarantor, beneficiary,
                random.choice(guarantee_types),
                round(guarantee_amount, 0),
                str(eff_date), "ACTIVE"
            ))
            inserted += 1

    conn.commit()
    print(f"    그룹 보증 {inserted}건 생성 완료")


def generate_covenants(conn):
    """여신별 코베넌트 생성"""
    print("  코베넌트 생성 중...")
    cur = conn.cursor()

    # 승인된 여신 목록 (APPROVED 신청 → facility)
    facilities = cur.execute("""
        SELECT f.facility_id, f.customer_id, f.outstanding_amount, f.maturity_date,
               c.industry_code, c.size_category
        FROM facility f
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.status = 'ACTIVE'
    """).fetchall()

    covenant_inserted = 0
    check_inserted = 0

    today = date.today()

    # 코베넌트 템플릿 (여신 규모/유형에 따라 부여)
    FINANCIAL_TEMPLATES = [
        {"code": "FC01", "name": "부채비율 유지",   "metric": "debt_ratio",    "op": "LE",
         "threshold_func": lambda ind: 200.0 if ind not in ("F64","K65","L68") else 400.0,
         "frequency": "SEMI"},
        {"code": "FC02", "name": "DSCR 유지",       "metric": "dscr",          "op": "GE",
         "threshold_func": lambda ind: 1.25,
         "frequency": "ANNUAL"},
        {"code": "FC03", "name": "이자보상배율 유지", "metric": "ier",          "op": "GE",
         "threshold_func": lambda ind: 1.5,
         "frequency": "SEMI"},
    ]
    INFO_TEMPLATE = {"code": "IC01", "name": "분기 재무제표 제출", "metric": None,
                     "op": None, "threshold_func": None, "frequency": "QUARTERLY"}

    for fac in facilities:
        fid, cid, outstanding, maturity, ind_code, size_cat = fac

        # 1억 이상 여신에만 코베넌트 부여 (60% 확률)
        if outstanding < 100_000_000 or random.random() > 0.60:
            continue

        # 여신 규모에 따라 코베넌트 수 결정
        if outstanding >= 10_000_000_000:   # 100억 이상
            templates = FINANCIAL_TEMPLATES[:3]
        elif outstanding >= 1_000_000_000:  # 10억 이상
            templates = FINANCIAL_TEMPLATES[:2]
        else:
            templates = FINANCIAL_TEMPLATES[:1]

        templates = templates + [INFO_TEMPLATE]

        for tmpl in templates:
            covenant_id = f"COV_{fid}_{tmpl['code']}"

            threshold = tmpl["threshold_func"](ind_code) if tmpl["threshold_func"] else None

            freq_days = {"MONTHLY": 30, "QUARTERLY": 91, "SEMI": 183, "ANNUAL": 365}
            next_check = today + timedelta(days=random.randint(0, freq_days.get(tmpl["frequency"], 183)))

            cur.execute("""
                INSERT OR IGNORE INTO covenant
                (covenant_id, facility_id, covenant_type, covenant_code, covenant_name,
                 metric, operator, threshold_value, check_frequency, next_check_date, status)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                covenant_id, fid,
                "FINANCIAL" if tmpl["code"].startswith("FC") else
                "BEHAVIORAL" if tmpl["code"].startswith("BC") else "INFORMATION",
                tmpl["code"], tmpl["name"],
                tmpl.get("metric"), tmpl.get("op"), threshold,
                tmpl["frequency"], str(next_check), "ACTIVE"
            ))
            covenant_inserted += 1

            # 과거 점검 이력 2~4회 생성
            n_checks = random.randint(2, 4)
            for i in range(n_checks):
                check_date = today - timedelta(days=(n_checks - i) * freq_days.get(tmpl["frequency"], 183))
                check_id = f"CC_{covenant_id}_{check_date.strftime('%Y%m%d')}"

                # 실측값 생성 (재무비율 테이블에서 가져오거나 랜덤)
                actual_value = None
                if tmpl.get("metric") and threshold:
                    ratio_row = cur.execute(f"""
                        SELECT {tmpl['metric']} FROM financial_ratio
                        WHERE customer_id = ? ORDER BY fiscal_year DESC LIMIT 1
                    """, (cid,)).fetchone()
                    if ratio_row and ratio_row[0]:
                        actual_value = ratio_row[0] * random.uniform(0.8, 1.2)

                # 90% 이행률 기준
                if actual_value and threshold:
                    if tmpl["op"] == "LE":
                        is_pass = actual_value <= threshold
                    else:
                        is_pass = actual_value >= threshold
                    result = "PASS" if is_pass or random.random() > 0.10 else "BREACH"
                else:
                    result = "PASS" if random.random() > 0.10 else "BREACH"

                severity = None
                if result == "BREACH":
                    severity = random.choice(["MINOR", "MAJOR", "MINOR", "MINOR"])  # MINOR 비중 높게

                next_chk = check_date + timedelta(days=freq_days.get(tmpl["frequency"], 183))
                cur.execute("""
                    INSERT OR IGNORE INTO covenant_check
                    (check_id, covenant_id, check_date, actual_value, threshold_value,
                     result, breach_severity, checked_by, next_check_date)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (
                    check_id, covenant_id, str(check_date),
                    round(actual_value, 4) if actual_value else None,
                    threshold, result, severity,
                    random.choice(["김담당", "이심사", "박RM", "SYSTEM"]),
                    str(next_chk)
                ))
                check_inserted += 1

                # BREACH 건은 covenant 상태 업데이트
                if result == "BREACH" and i == n_checks - 1:
                    cur.execute("""
                        UPDATE covenant SET status = 'BREACHED' WHERE covenant_id = ?
                    """, (covenant_id,))

    conn.commit()
    print(f"    코베넌트 {covenant_inserted}건, 점검 이력 {check_inserted}건 생성 완료")


def apply_schema(conn):
    """Phase 1 스키마 적용 (이미 적용된 경우 안전하게 스킵)"""
    print("  스키마 적용 중...")
    cur = conn.cursor()

    schema_path = Path(__file__).parent / "schema_phase1.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        full_sql = f.read()

    # CREATE/DROP 계열과 ALTER를 분리 처리
    # 주석 제거 후 세미콜론 기준 분리
    lines = []
    for line in full_sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        lines.append(line)
    cleaned_sql = "\n".join(lines)

    statements = [s.strip() for s in cleaned_sql.split(";") if s.strip()]
    for stmt in statements:
        if not stmt:
            continue
        try:
            cur.execute(stmt)
            conn.commit()
        except Exception as e:
            err = str(e).lower()
            if ("duplicate column" in err or "already exists" in err
                    or "no such table" in err):
                pass  # 이미 적용됨 또는 인덱스 대상 테이블 없음 (정상)
            else:
                print(f"    [WARN] {str(e)[:100]}")

    conn.commit()
    print("  스키마 적용 완료")


def main():
    print(f"Phase 1 데이터 생성 시작: {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))

    try:
        apply_schema(conn)
        generate_financial_statements(conn)
        generate_group_guarantees(conn)
        generate_covenants(conn)
        print("\nPhase 1 데이터 생성 완료!")

        # 통계 출력
        cur = conn.cursor()
        for tbl in ["financial_statement", "financial_ratio", "group_guarantee", "covenant", "covenant_check"]:
            cnt = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            print(f"  {tbl}: {cnt:,}건")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
