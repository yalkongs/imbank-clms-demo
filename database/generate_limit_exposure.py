#!/usr/bin/env python3
"""
한도 익스포저 재계산
====================
limit_exposure 는 여태 어떤 생성 스크립트에도 없어서, 산업한도 10건만 옛 기준일
(2026-02-07)로 남아 있고 규제한도(동일인·동일그룹) 2건은 아예 비어 있었다.
그 결과 한도관리 화면에서 동일인/동일그룹 사용액이 0억·0.00% 로 표시됐다.

여기서는 임의값을 넣지 않고 실제 여신 잔액에서 계산한다.
  · 산업한도  : 업종별 ACTIVE 여신 잔액 합계
  · 동일인    : 단일 차주 합산 익스포저의 최댓값 (감독규정상 규제 대상은 최대 차주)
  · 동일그룹  : 차주그룹 합산 익스포저의 최댓값

기준일은 base_date.py 의 AS_OF_DATE 를 따른다.
"""

import sqlite3
import uuid
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from base_date import AS_OF_STR  # noqa: E402

DB_PATH = str(Path(__file__).parent / "imbank_demo.db")


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ------------------------------------------------------------------ #
    # 1) 한도 금액 현실화
    # ------------------------------------------------------------------ #
    # 기존 limit_definition 은 총여신 17.9조 규모와 무관하게 산업한도가
    # 2,300~4,900억으로 잡혀 있어 실제 익스포저를 넣으면 소진율이 876% 까지 나왔다.
    #
    #  · 규제한도 : 은행법 제35조 - 동일인 자기자본의 20%, 동일차주(그룹) 25%
    #  · 산업한도 : 업종 집중도 관리용 내부한도. 현 익스포저를 목표 소진율
    #               구간(60~85%)에 놓이도록 설정한다.
    row = cur.execute("""
        SELECT total_capital FROM capital_position ORDER BY base_date DESC LIMIT 1
    """).fetchone()
    equity = float(row[0]) if row and row[0] else 0.0

    if equity > 0:
        cur.execute("UPDATE limit_definition SET limit_amount = ?, base_amount = ? "
                    "WHERE limit_id = 'LIM_REG_SINGLE'",
                    (round(equity * 0.20, 2), round(equity, 2)))
        cur.execute("UPDATE limit_definition SET limit_amount = ?, base_amount = ? "
                    "WHERE limit_id = 'LIM_REG_GROUP'",
                    (round(equity * 0.25, 2), round(equity, 2)))

    # 산업한도 - 업종별 실제 잔액 대비 여유율을 둔다 (업종마다 다르게 해서
    # 화면에 NORMAL/WARNING/ALERT 가 고루 나타나도록)
    headroom = [1.18, 1.25, 1.35, 1.45, 1.55, 1.22, 1.40, 1.30, 1.12, 1.60]
    ind_limits = cur.execute("""
        SELECT limit_id, limit_name FROM limit_definition
        WHERE limit_id LIKE 'LIM_IND_%' ORDER BY limit_id
    """).fetchall()

    industry_exposure_pre = dict(cur.execute("""
        SELECT c.industry_name, SUM(f.outstanding_amount)
        FROM facility f JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.status = 'ACTIVE'
        GROUP BY c.industry_name
    """).fetchall())

    for i, (lid, lname) in enumerate(ind_limits):
        key = (lname or "").replace(" 산업한도", "").strip()
        exp = float(industry_exposure_pre.get(key, 0) or 0)
        if exp > 0:
            cur.execute("UPDATE limit_definition SET limit_amount = ? WHERE limit_id = ?",
                        (round(exp * headroom[i % len(headroom)], 2), lid))
    conn.commit()

    limits = cur.execute("""
        SELECT limit_id, limit_type, limit_name, dimension_code, limit_amount
        FROM limit_definition WHERE status = 'ACTIVE' OR status IS NULL
    """).fetchall()

    # 업종명 → 잔액
    industry_exposure = dict(cur.execute("""
        SELECT c.industry_name, SUM(f.outstanding_amount)
        FROM facility f JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.status = 'ACTIVE'
        GROUP BY c.industry_name
    """).fetchall())

    # 단일 차주 최대 익스포저
    row = cur.execute("""
        SELECT MAX(s) FROM (
            SELECT SUM(outstanding_amount) AS s FROM facility
            WHERE status = 'ACTIVE' GROUP BY customer_id
        )
    """).fetchone()
    single_max = float(row[0] or 0)

    # 차주그룹 최대 합산 익스포저 (그룹 미편입 차주는 단일 차주로 취급)
    try:
        row = cur.execute("""
            SELECT MAX(s) FROM (
                SELECT SUM(f.outstanding_amount) AS s
                FROM facility f
                JOIN borrower_group_member m ON f.customer_id = m.customer_id
                WHERE f.status = 'ACTIVE'
                GROUP BY m.group_id
            )
        """).fetchone()
        group_max = float(row[0] or 0)
    except sqlite3.OperationalError:
        group_max = 0.0
    group_max = max(group_max, single_max)

    cur.execute("DELETE FROM limit_exposure")

    rows = []
    for limit_id, limit_type, limit_name, dim_code, limit_amount in limits:
        limit_amount = float(limit_amount or 0)

        if limit_id == "LIM_REG_SINGLE":
            exposure = single_max
        elif limit_id == "LIM_REG_GROUP":
            exposure = group_max
        else:
            # "반도체 산업한도" → "반도체"
            key = (limit_name or "").replace(" 산업한도", "").strip()
            exposure = float(industry_exposure.get(key, 0) or 0)

        util = (exposure / limit_amount * 100) if limit_amount > 0 else 0.0
        available = max(limit_amount - exposure, 0.0)

        if util >= 90:
            status = "CRITICAL"
        elif util >= 80:
            status = "ALERT"
        elif util >= 70:
            status = "WARNING"
        else:
            status = "NORMAL"

        rows.append((
            f"LEXP_{uuid.uuid4().hex[:10].upper()}",
            limit_id, AS_OF_STR,
            round(exposure, 2), 0.0, round(available, 2),
            round(util, 4), status,
        ))

    cur.executemany("""
        INSERT INTO limit_exposure
        (exposure_id, limit_id, base_date, exposure_amount,
         reserved_amount, available_amount, utilization_rate, status)
        VALUES (?,?,?,?,?,?,?,?)
    """, rows)
    conn.commit()

    print(f"✓ limit_exposure {len(rows)}건 재계산 (기준일 {AS_OF_STR})")
    for r in cur.execute("""
        SELECT d.limit_name, e.exposure_amount, e.utilization_rate, e.status
        FROM limit_exposure e JOIN limit_definition d ON e.limit_id = d.limit_id
        ORDER BY e.utilization_rate DESC
    """):
        print(f"  {r[0]:<20} {r[1]/1e8:>9,.0f}억  {r[2]:>6.2f}%  {r[3]}")

    conn.close()


if __name__ == "__main__":
    main()
