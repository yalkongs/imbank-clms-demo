#!/usr/bin/env python3
"""
RAROC 허들 단일화 (Gate 0)
===========================
규정 레지스터 RULE_RAROC_HURDLE(15%)이 정본인데 hurdle_rate 테이블이
구 시드값(기본 12%, 규모별 10/12/14%)으로 남아 자본최적화 화면이
다른 허들을 읽던 불일치를 해소한다.

기본(DEFAULT)은 정본 15%에 정렬하고, 규모별 차등(내규 성격)은
±2%p 상대 구조를 유지한 채 재기준한다. 멱등.
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "imbank_demo.db"

RATES = {
    "HUR_DEFAULT": (0.15, 0.18),
    "HUR_LARGE":   (0.13, 0.16),
    "HUR_MEDIUM":  (0.15, 0.18),
    "HUR_SMALL":   (0.17, 0.20),
}


def main():
    con = sqlite3.connect(str(DB))
    cur = con.cursor()
    for rid, (h, t) in RATES.items():
        cur.execute("UPDATE hurdle_rate SET hurdle_raroc = ?, target_raroc = ? "
                    "WHERE rate_id = ?", (h, t, rid))
    con.commit()
    for row in cur.execute("SELECT rate_id, hurdle_raroc, target_raroc FROM hurdle_rate"):
        print(f"  {row[0]}: 허들 {row[1]*100:g}% / 목표 {row[2]*100:g}%")
    con.close()


if __name__ == "__main__":
    main()
