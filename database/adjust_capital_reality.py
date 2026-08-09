#!/usr/bin/env python3
"""
자본·RWA 현실화 (imbank-metrics 실측 대조 반영)
=================================================
종전 시드: 자기자본 14.49조 / RWA 86.2조 - 여신 36.7조 대비 RW 235%라는
비현실적 구조였다. iM뱅크 실제 규모 근사(자기자본 ~5.5조, RWA ~38조,
BIS ~14.5%)로 전 이력을 비례 조정한다.

- capital_position 25개월: 자본 계정 × f_c, RWA 계정 × f_r,
  비율(BIS·CET1·Tier1)은 조정값에서 재계산 (레버리지비율은 유지 -
  분모인 총익스포저는 이 시스템 범위 밖)
- capital_budget: RWA 예산·사용액 × f_r (소진율 보존)
- optimal_allocation 은 익스포저(여신 장부) 스케일이라 조정하지 않는다

멱등: 최신 total_capital 이 이미 7조 미만이면 적용 완료로 보고 종료.
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "imbank_demo.db"

TARGET_CAPITAL = 5.5e12    # 자기자본 5.5조
TARGET_RWA = 38.0e12       # RWA 38조 → BIS 14.47%


def main():
    con = sqlite3.connect(str(DB))
    cur = con.cursor()

    latest = cur.execute(
        "SELECT total_capital, total_rwa FROM capital_position "
        "ORDER BY base_date DESC LIMIT 1"
    ).fetchone()
    if latest[0] < 7e12:
        print(f"이미 적용됨 (자기자본 {latest[0] / 1e12:.2f}조) - 종료")
        return

    f_c = TARGET_CAPITAL / latest[0]
    f_r = TARGET_RWA / latest[1]
    print(f"조정 계수: 자본 ×{f_c:.4f}, RWA ×{f_r:.4f}")

    cur.execute("""
        UPDATE capital_position SET
            cet1_capital     = cet1_capital * :fc,
            at1_capital      = at1_capital * :fc,
            tier2_capital    = tier2_capital * :fc,
            total_capital    = total_capital * :fc,
            credit_rwa       = credit_rwa * :fr,
            market_rwa       = market_rwa * :fr,
            operational_rwa  = operational_rwa * :fr,
            total_rwa        = total_rwa * :fr
    """, {"fc": f_c, "fr": f_r})

    # 비율 재계산 - 저장 비율과 (자본/RWA) 산출이 항상 일치하도록
    cur.execute("""
        UPDATE capital_position SET
            bis_ratio   = total_capital / total_rwa,
            cet1_ratio  = cet1_capital / total_rwa,
            tier1_ratio = (cet1_capital + at1_capital) / total_rwa
    """)

    cur.execute("""
        UPDATE capital_budget SET
            rwa_budget = rwa_budget * :fr,
            rwa_used   = rwa_used * :fr
    """, {"fr": f_r})

    con.commit()

    row = cur.execute("""
        SELECT base_date, total_capital/1e12, total_rwa/1e12,
               bis_ratio*100, cet1_ratio*100, tier1_ratio*100
        FROM capital_position ORDER BY base_date DESC LIMIT 1
    """).fetchone()
    print(f"최신({row[0]}): 자기자본 {row[1]:.2f}조 / RWA {row[2]:.2f}조 / "
          f"BIS {row[3]:.2f}% / CET1 {row[4]:.2f}% / Tier1 {row[5]:.2f}%")
    print(f"동일차주 한도(25%): {row[1] * 0.25:.2f}조 / "
          f"거액공여 판정(10%): {row[1] * 0.10 * 10:.0f}천억")
    bud = cur.execute(
        "SELECT SUM(rwa_budget)/1e12, SUM(rwa_used)/1e12 FROM capital_budget"
    ).fetchone()
    print(f"자본예산: RWA 배정 {bud[0]:.1f}조 / 사용 {bud[1]:.1f}조")
    con.close()


if __name__ == "__main__":
    main()
