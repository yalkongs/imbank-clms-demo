#!/usr/bin/env python3
"""
기존 승인 건 스냅샷 백필
========================
스냅샷 체계 도입 이전에 승인된 건들에 as-of 재구성 스냅샷을 생성한다.
backfilled=true 로 표시되어 '승인 순간 봉인'과 구분된다. 멱등.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from base_date import AS_OF_STR  # noqa: E402

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

DB = Path(__file__).parent / "imbank_demo.db"
engine = create_engine(f"sqlite:///{DB}")
Session = sessionmaker(bind=engine)

from app.services.snapshot import build_and_seal_snapshot  # noqa: E402

db = Session()
rows = db.execute(text("""
    SELECT ah.application_id,
           MAX(ah.approval_level) AS lvl,
           MAX(ah.approver_name) AS nm,
           MAX(ah.decided_at) AS at
    FROM approval_history ah
    JOIN loan_application la ON la.application_id = ah.application_id
    WHERE la.status IN ('APPROVED', 'DISBURSED', 'CONDITIONAL')
      AND NOT EXISTS (SELECT 1 FROM decision_snapshot ds
                      WHERE ds.application_id = ah.application_id)
    GROUP BY ah.application_id
""")).fetchall()
n = 0
for aid, lvl, nm, at in rows:
    amt = db.execute(text(
        "SELECT requested_amount FROM loan_application WHERE application_id = :a"
    ), {"a": aid}).fetchone()[0]
    build_and_seal_snapshot(db, aid, decision="APPROVE", approved_amount=amt,
                            approver_name=nm or "이력", approval_level=lvl or "TEAM_LEAD",
                            as_of=(at or AS_OF_STR)[:10], backfilled=True)
    n += 1
db.commit()
con = sqlite3.connect(str(DB))
con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
print(f"백필 {n}건")
