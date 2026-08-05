#!/usr/bin/env python3
"""
성능 인덱스 추가
================
차주 확대(699→1,999개사, 시설 3,734건) 후 저사양 배포 인스턴스에서
"고객별/시설별 최신 1건" 패턴(ROW_NUMBER · MAX 조인)이 풀스캔으로 돌며
응답이 수 초로 늘었다. 해당 패턴이 타는 복합 인덱스를 보강한다.
멱등(IF NOT EXISTS). 마지막에 ANALYZE 로 플래너 통계 갱신.
"""
import sqlite3
from pathlib import Path

DB = str(Path(__file__).parent / "imbank_demo.db")

INDEXES = [
    # 고객별 최신 1건 (ROW_NUMBER PARTITION BY customer_id ORDER BY date DESC)
    ("idx_rating_cust_date", "credit_rating_result(customer_id, rating_date DESC)"),
    ("idx_ews_comp_cust_date", "ews_composite_score(customer_id, score_date DESC)"),
    ("idx_prof_cust_date", "customer_profitability(customer_id, calculation_date DESC)"),
    ("idx_finratio_cust_year", "financial_ratio(customer_id, fiscal_year DESC)"),
    ("idx_finstmt_cust_year", "financial_statement(customer_id, fiscal_year DESC)"),
    # 시설별 최신 1건 (MAX(base_date)/MAX(calc_date) 조인)
    ("idx_class_fac_date", "asset_classification(facility_id, base_date DESC)"),
    ("idx_class_date", "asset_classification(base_date)"),
    ("idx_ecl_fac_date", "ecl_calculation(facility_id, calc_date DESC)"),
    ("idx_ecl_cust", "ecl_calculation(customer_id)"),
    # 조인 축
    ("idx_fac_cust_status", "facility(customer_id, status)"),
    ("idx_riskparam_app", "risk_parameter(application_id)"),
    ("idx_collateral_fac", "collateral(facility_id)"),
    ("idx_covcheck_cov_date", "covenant_check(covenant_id, check_date DESC)"),
    ("idx_delinq_fac", "delinquency_record(facility_id)"),
]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    for name, spec in INDEXES:
        cur.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {spec}")
        print(f"  ✓ {name}")
    cur.execute("ANALYZE")
    con.commit()
    cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    print("ANALYZE 완료")


if __name__ == "__main__":
    main()
