#!/usr/bin/env python3
"""
여신금리 현실화 (imbank-metrics 실측 대조 2단계)
==================================================
종전 시드: 잔액가중 평균 여신금리 6.04% - 실측(원화대출 4.36%, 기업 중심
포트폴리오 적정선 4.6~4.8%) 대비 1.3%p 이상 높았다.

방법: 비례 축소 (final_rate·spread × k). 평행이동과 달리 등급·담보 간
상대 스프레드 구조가 그대로 보존되고, 내재 기준금리(final - spread)도
같은 비율로 내려가 CD91 3.43% → 2.67% 수준의 현실적 기준금리가 된다.

- facility.final_rate, facility.spread × k  (k = 4.70% / 현재 가중평균)
- ftp_rate 4개 금리 컬럼 × k  (조달원가도 같은 금리 사이클 반영)
- loan_application.requested_rate: 퍼센트 스케일 오염(5.37 등) 소수로
  정규화 후 × k  (2,534건이 %단위로 저장돼 있던 데이터 결함 동시 수정)

멱등: 가중평균이 이미 5.2% 미만이면 적용 완료로 보고 종료.
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "imbank_demo.db"

TARGET_WEIGHTED = 0.0470   # 잔액가중 평균 4.70%


def main():
    con = sqlite3.connect(str(DB))
    cur = con.cursor()

    cur_avg = cur.execute("""
        SELECT SUM(outstanding_amount * final_rate) / SUM(outstanding_amount)
        FROM facility WHERE status='ACTIVE'
    """).fetchone()[0]
    if cur_avg < 0.052:
        print(f"이미 적용됨 (가중평균 {cur_avg * 100:.2f}%) - 종료")
        return

    k = TARGET_WEIGHTED / cur_avg
    print(f"조정 계수 k = {k:.4f} (가중평균 {cur_avg * 100:.3f}% → {TARGET_WEIGHTED * 100:.2f}%)")

    cur.execute("UPDATE facility SET final_rate = final_rate * :k, spread = spread * :k",
                {"k": k})
    cur.execute("""
        UPDATE ftp_rate SET
            base_ftp_rate = base_ftp_rate * :k,
            liquidity_premium = liquidity_premium * :k,
            term_premium = term_premium * :k,
            final_ftp_rate = final_ftp_rate * :k
    """, {"k": k})

    # 신청금리: %단위 오염 정규화(> 0.5 는 소수가 아님) 후 동일 계수 적용
    cur.execute("UPDATE loan_application SET requested_rate = requested_rate / 100.0 "
                "WHERE requested_rate > 0.5")
    cur.execute("UPDATE loan_application SET requested_rate = requested_rate * :k "
                "WHERE requested_rate IS NOT NULL", {"k": k})

    # 저장된 가격산출 결과의 금리 성분도 동일 계수로 - 화면에 신·구 금리가 섞이지 않게
    cur.execute("""
        UPDATE pricing_result SET
            base_rate = base_rate * :k, ftp_spread = ftp_spread * :k,
            credit_spread = credit_spread * :k, capital_spread = capital_spread * :k,
            opex_spread = opex_spread * :k, target_margin = target_margin * :k,
            system_rate = system_rate * :k, proposed_rate = proposed_rate * :k,
            final_rate = final_rate * :k
    """, {"k": k})

    # 포트폴리오 요약 스냅샷(INDUSTRY 세그먼트)은 실측 재집계 - 대시보드 산식
    # (비용 3.5%, RWA×10.5%)과 동일한 기준으로 맞춰 화면 간 수치 불일치를 없앤다
    cur.execute("""
        UPDATE portfolio_summary SET
            (total_exposure, total_rwa, total_el, weighted_rate, total_revenue, raroc) = (
                SELECT SUM(f.outstanding_amount),
                       COALESCE(SUM(rp.rwa), 0),
                       COALESCE(SUM(rp.expected_loss), 0),
                       SUM(f.outstanding_amount * f.final_rate) / SUM(f.outstanding_amount),
                       SUM(f.outstanding_amount * f.final_rate),
                       CASE WHEN SUM(rp.rwa) * 0.105 > 0
                           THEN (SUM(f.outstanding_amount * f.final_rate)
                                 - SUM(f.outstanding_amount) * 0.035
                                 - SUM(rp.expected_loss)) / (SUM(rp.rwa) * 0.105)
                           ELSE 0 END
                FROM customer c
                JOIN facility f ON c.customer_id = f.customer_id AND f.status = 'ACTIVE'
                LEFT JOIN risk_parameter rp ON f.application_id = rp.application_id
                WHERE c.industry_name = portfolio_summary.segment_name
            )
        WHERE segment_type = 'INDUSTRY'
    """)
    # RATING 세그먼트는 금리 성분만 스케일 (등급 구간 정의가 별도 시드 기준)
    cur.execute("""
        UPDATE portfolio_summary SET
            weighted_rate = weighted_rate * :k,
            total_revenue = total_revenue * :k,
            raroc = CASE WHEN total_rwa * 0.105 > 0
                THEN (total_exposure * weighted_rate * :k - total_exposure * 0.035 - total_el)
                     / (total_rwa * 0.105) ELSE 0 END
        WHERE segment_type != 'INDUSTRY'
    """, {"k": k})

    con.commit()

    chk = cur.execute("""
        SELECT SUM(outstanding_amount * final_rate) / SUM(outstanding_amount) * 100,
               MIN(final_rate) * 100, MAX(final_rate) * 100,
               AVG(final_rate - spread) * 100
        FROM facility WHERE status='ACTIVE'
    """).fetchone()
    print(f"여신금리: 가중평균 {chk[0]:.3f}% / 범위 {chk[1]:.2f}~{chk[2]:.2f}% / "
          f"내재 기준금리 평균 {chk[3]:.2f}%")
    ftp = cur.execute(
        "SELECT MIN(final_ftp_rate)*100, MAX(final_ftp_rate)*100 FROM ftp_rate"
    ).fetchone()
    print(f"FTP: {ftp[0]:.2f}~{ftp[1]:.2f}%")
    req = cur.execute(
        "SELECT AVG(requested_rate)*100, COUNT(*) FROM loan_application "
        "WHERE requested_rate IS NOT NULL"
    ).fetchone()
    print(f"신청금리 평균 {req[0]:.2f}% ({req[1]}건, 단위 정규화 포함)")
    con.close()


if __name__ == "__main__":
    main()
