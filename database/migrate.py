#!/usr/bin/env python3
"""
DB 마이그레이션 러너
====================
database/migrations/*.sql 을 파일명 순서로 적용하고 schema_migrations 에 기록한다.
- 멱등: 이미 적용된 파일은 건너뛴다 (DDL 도 IF NOT EXISTS 원칙)
- 앱 기동 시(lifespan)에도 호출되어 새 배포 환경에서 스키마가 자동 보장된다
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "imbank_demo.db"
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def run_migrations(db_path: str | Path = DB) -> list[str]:
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename   TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    applied = {r[0] for r in cur.execute("SELECT filename FROM schema_migrations")}
    done = []
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if f.name in applied:
            continue
        cur.executescript(f.read_text())
        cur.execute("INSERT INTO schema_migrations (filename) VALUES (?)", (f.name,))
        con.commit()
        done.append(f.name)
    con.close()
    return done


if __name__ == "__main__":
    for name in run_migrations():
        print(f"  ✓ {name}")
    print("마이그레이션 완료")
