#!/usr/bin/env python3
"""
신용공여 원장 시드
==================
ACTIVE 시설에서 난내(대출잔액)·난외(미사용약정 CCF 40%)를 생성하고,
차주의 4%에 은행 취급 지급보증(난외, CCF 100%)을 부여한다.
멱등: 전체 재생성 (원장은 파생 정본 - 원천은 facility).
"""
import random
import sqlite3
import uuid
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from base_date import AS_OF_STR  # noqa: E402

DB = str(Path(__file__).parent / "imbank_demo.db")
random.seed(20260808)

RULE = "은행업감독규정 별표2 근사 (PoC)"

con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("DELETE FROM credit_exposure_ledger")

rows = cur.execute("""
    SELECT facility_id, customer_id, outstanding_amount,
           MAX(current_limit - outstanding_amount, 0)
    FROM facility WHERE status = 'ACTIVE'
""").fetchall()

ins = []
def uid():
    return f"CEL_{uuid.uuid4().hex[:12].upper()}"

for fac, cust, out, undrawn in rows:
    if out and out > 0:
        ins.append((uid(), cust, fac, "ON_LOAN", out, 1.0, 0, out, AS_OF_STR, RULE, fac))
    if undrawn and undrawn > 0:
        ins.append((uid(), cust, fac, "OFF_UNDRAWN", undrawn, 0.4, 0,
                    undrawn * 0.4, AS_OF_STR, RULE, fac))

# 지급보증 (은행 취급 난외) - 차주 4%
borrowers = sorted({r[1] for r in rows})
for cust in borrowers:
    rng = random.Random(cust)
    if rng.random() < 0.04:
        base = sum(r[2] or 0 for r in rows if r[1] == cust)
        g = base * rng.uniform(0.10, 0.40)
        if g > 1e7:
            ins.append((uid(), cust, None, "OFF_GUARANTEE", g, 1.0, 0, g,
                        AS_OF_STR, RULE, "BANK_GUARANTEE"))

cur.executemany("""
    INSERT INTO credit_exposure_ledger
    (exposure_id, customer_id, facility_id, exposure_type, gross_amount, ccf,
     exclusion, net_exposure, as_of_date, rule_ref, source_ref)
    VALUES (?,?,?,?,?,?,?,?,?,?,?)
""", ins)
con.commit()
cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
by = {}
for r in ins:
    by[r[3]] = by.get(r[3], 0) + r[7]
print(f"원장 {len(ins):,}건 - " + " · ".join(f"{k} {v/1e12:.1f}조" for k, v in by.items()))
