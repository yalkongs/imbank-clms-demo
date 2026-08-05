#!/usr/bin/env python3
"""
FK 정합화 (제3자 리뷰 지적 ③)
==============================
PRAGMA foreign_key_check 전수 결과 두 덩어리를 정리한다.

1. loan_application → product_master (2,534건)
   확장 시드가 기존 신청 관례(CORP_*)를 따랐으나 product_master 는 LOAN_* 체계.
   CORP_* 코드를 product_master 에 등록해 해소한다 (기존 신청도 CORP_* 를 쓰므로
   마스터 등록이 데이터 수정보다 안전).

2. group_guarantee → borrower_group (238건)
   시드가 48개 그룹 ID 를 참조하지만 실제 그룹은 10개뿐.
   미존재 그룹 참조 보증은 삭제한다 (임의 그룹에 재배정하면 그룹여신
   화면의 보증 네트워크가 왜곡됨).

정리 후 재검사해 0건을 확인한다. 멱등.
"""
import sqlite3
from pathlib import Path

DB = str(Path(__file__).parent / "imbank_demo.db")

CORP_PRODUCTS = [
    ("CORP_WORK", "기업운전자금대출(구코드)", "LOAN"),
    ("CORP_TERM", "기업일반자금대출(구코드)", "LOAN"),
    ("CORP_FACILITY", "기업시설자금대출(구코드)", "LOAN"),
    ("CORP_TRADE", "무역금융(구코드)", "LOAN"),
    ("CORP_PF", "PF대출(구코드)", "LOAN"),
    ("CORP_BOND", "회사채인수(구코드)", "LOAN"),
]

con = sqlite3.connect(DB)
cur = con.cursor()

cols = [r[1] for r in cur.execute("PRAGMA table_info(product_master)")]
for code, name, cat in CORP_PRODUCTS:
    exists = cur.execute("SELECT 1 FROM product_master WHERE product_code = ?", (code,)).fetchone()
    if not exists:
        cur.execute("INSERT INTO product_master (product_code, product_name) VALUES (?, ?)",
                    (code, name))
        print(f"  + product_master {code}")

deleted = cur.execute("""
    DELETE FROM group_guarantee
    WHERE group_id NOT IN (SELECT group_id FROM borrower_group)
""").rowcount
print(f"  - group_guarantee 고아 {deleted}건 삭제")

con.commit()
cur.execute("PRAGMA foreign_keys=ON")
remain = cur.execute("PRAGMA foreign_key_check").fetchall()
print(f"잔여 위반: {len(remain)}건")
assert len(remain) == 0, remain[:5]
cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
print("FK 정합 완료")
