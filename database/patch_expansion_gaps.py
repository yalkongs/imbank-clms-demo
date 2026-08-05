#!/usr/bin/env python3
"""
차주 확대 후속 정합 패치
========================
expand_borrowers.py 실행 후 남는 두 가지 정합 공백을 메운다.

1. 전환 잠재고객의 customer_profitability - 잠재고객 시절 행은 여신이 없어
   경제적자본이 0에 가깝고 RAROC 이 수만 % 로 발산한다 (포트폴리오 맵 Y축 폭발).
   실제 여신 잔액 기준으로 재계산해 덮어쓴다.
2. 신규 여신신청의 risk_parameter - 대시보드 RAROC/EL/PD 집계가
   risk_parameter 조인 기반이라, 없으면 신규 여신이 집계에서 빠진다.

멱등: 두 패치 모두 "필요한 행만" 갱신/삽입한다.
"""
import random
import sqlite3
import uuid
from pathlib import Path

DB = str(Path(__file__).parent / "imbank_demo.db")
random.seed(20260806)

con = sqlite3.connect(DB)
cur = con.cursor()

# ── 1. 발산한 수익성 행 재계산 (여신 보유인데 경제자본이 잔액의 2% 미만) ──
rows = cur.execute("""
    SELECT p.customer_id, p.profitability_id,
           (SELECT SUM(outstanding_amount) FROM facility f
             WHERE f.customer_id = p.customer_id AND f.status = 'ACTIVE') AS exposure,
           (SELECT AVG(final_rate) FROM facility f
             WHERE f.customer_id = p.customer_id AND f.status = 'ACTIVE') AS avg_rate,
           (SELECT pd_value FROM credit_rating_result r
             WHERE r.customer_id = p.customer_id ORDER BY rating_date DESC LIMIT 1) AS pd
    FROM customer_profitability p
    WHERE exposure > 0 AND p.economic_capital < exposure * 0.02
""").fetchall()
fixed = 0
for cid, pid, exposure, rate, pd_v in rows:
    pd_v = pd_v or 0.01
    rate = rate or 0.055
    econ = exposure * 0.08
    rev = exposure * (rate + random.uniform(0.005, 0.02))
    el = pd_v * 0.4 * exposure
    profit = rev * random.uniform(0.30, 0.45) - el
    raroc = max(-8.0, min(28.0, profit / econ * 100))
    cur.execute("""
        UPDATE customer_profitability SET
            loan_revenue = ?, loan_cost = ?, loan_el = ?, loan_capital_cost = ?,
            loan_profit = ?, total_revenue = ?, total_cost = ?, total_profit = ?,
            economic_capital = ?, raroc = ?
        WHERE profitability_id = ?
    """, (rev, rev * 0.55, el, econ * 0.1, profit, rev * 1.05, rev * 0.6,
          profit, econ, round(raroc, 2), pid))
    fixed += 1
print(f"수익성 재계산: {fixed}개사")

# ── 2. risk_parameter 백필 (ACTIVE 여신인데 파라미터 없는 신청) ──
RW = {"A": 0.55, "B": 0.85, "C": 1.15}   # 등급 대역별 위험가중치 근사
rows = cur.execute("""
    SELECT f.application_id, f.customer_id, f.outstanding_amount, f.maturity_date, f.contract_date
    FROM facility f
    WHERE f.status = 'ACTIVE'
      AND NOT EXISTS (SELECT 1 FROM risk_parameter rp
                      WHERE rp.application_id = f.application_id)
""").fetchall()
ins = []
for app_id, cid, ead, mat, contract in rows:
    g = cur.execute("""
        SELECT final_grade, pd_value FROM credit_rating_result
        WHERE customer_id = ? ORDER BY rating_date DESC LIMIT 1""", (cid,)).fetchone()
    grade, pd_v = (g if g else ("BBB", 0.0042))
    pd_v = pd_v or 0.0042
    lgd = random.uniform(0.30, 0.50)
    years = max(0.5, (int(mat[:4]) - int(contract[:4])) + (int(mat[5:7]) - int(contract[5:7])) / 12)
    rw = RW.get((grade or "B")[0], 1.0) * random.uniform(0.9, 1.1)
    rwa = ead * rw
    el = pd_v * lgd * ead
    ins.append((f"RSK_{uuid.uuid4().hex[:10].upper()}", app_id, contract, pd_v,
                pd_v * 1.1, lgd, ead, 1.0, round(years, 2), rwa, el, el * 2.5, rwa * 0.08))
cur.executemany("""
    INSERT INTO risk_parameter (param_id, application_id, calc_date, ttc_pd, pit_pd,
                                lgd, ead, ccf, maturity_years, rwa, expected_loss,
                                unexpected_loss, economic_capital)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
""", ins)
print(f"risk_parameter 백필: {len(ins)}건")

con.commit()
cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")

# ── 3. 신규 여신 재가격 - 스프레드가 낮아 포트폴리오 RAROC 이 조달원가에 잠식됨 ──
#     (신규 = FAC001201 이후. 등급 대역별 스프레드를 정본 산식과 동일하게 상향)
reprice = cur.execute("""
    SELECT f.facility_id, f.customer_id,
           (SELECT final_grade FROM credit_rating_result r
             WHERE r.customer_id = f.customer_id ORDER BY rating_date DESC LIMIT 1)
    FROM facility f
    WHERE f.status = 'ACTIVE'
      AND CAST(substr(f.facility_id, 4) AS INTEGER) > 1200
      AND f.final_rate < 0.058
""").fetchall()
for fac_id, cid, grade in reprice:
    base = {"A": 2.2, "B": 3.2, "C": 4.2}.get((grade or "B")[0], 3.2)
    spread = base + random.uniform(-0.3, 1.0)
    cur.execute("UPDATE facility SET spread = ?, final_rate = ? WHERE facility_id = ?",
                (round(spread / 100, 6), round((3.4 + spread) / 100, 6), fac_id))
print(f"재가격: {len(reprice)}건")

# ── 4. 재가격 반영 수익성 재계산 (신규·전환 차주 전체) ──
rows = cur.execute("""
    SELECT p.customer_id, p.profitability_id,
           (SELECT SUM(outstanding_amount) FROM facility f
             WHERE f.customer_id = p.customer_id AND f.status = 'ACTIVE') AS exposure,
           (SELECT SUM(outstanding_amount * final_rate) /
                   NULLIF(SUM(outstanding_amount), 0) FROM facility f
             WHERE f.customer_id = p.customer_id AND f.status = 'ACTIVE') AS wavg_rate,
           (SELECT pd_value FROM credit_rating_result r
             WHERE r.customer_id = p.customer_id ORDER BY rating_date DESC LIMIT 1) AS pd
    FROM customer_profitability p
    WHERE exposure > 0
      AND EXISTS (SELECT 1 FROM facility f
                  WHERE f.customer_id = p.customer_id AND f.status = 'ACTIVE'
                    AND CAST(substr(f.facility_id, 4) AS INTEGER) > 1200)
""").fetchall()
for cid, pid, exposure, rate, pd_v in rows:
    pd_v = pd_v or 0.01
    rate = rate or 0.065
    econ = exposure * 0.08
    rev = exposure * rate
    el = pd_v * 0.4 * exposure
    profit = rev - exposure * 0.048 - el          # 조달·운영원가 4.8% (대시보드 산식과 정렬)
    raroc = max(-8.0, min(28.0, profit / econ * 100))
    cur.execute("""
        UPDATE customer_profitability SET
            loan_revenue = ?, loan_cost = ?, loan_el = ?, loan_profit = ?,
            total_revenue = ?, total_cost = ?, total_profit = ?,
            economic_capital = ?, raroc = ?
        WHERE profitability_id = ?
    """, (rev, exposure * 0.048, el, profit, rev * 1.03, exposure * 0.048 * 1.05,
          profit, econ, round(raroc, 2), pid))
print(f"수익성 재계산(재가격 반영): {len(rows)}개사")

con.commit()
cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
