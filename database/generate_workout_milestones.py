#!/usr/bin/env python3
"""
워크아웃 회수 마일스톤 시드
===========================
케이스 상세에 "지금 어느 단계까지 왔고 다음이 무엇인가"를 보여주기 위한
전략별 회수 절차 타임라인. 종전 케이스 상세는 시나리오 비교(NPV)만 있고
진행 경과가 없어 실무 화면으로서 깊이가 부족했다.
"""
import sqlite3
import random
import uuid
from datetime import timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from base_date import AS_OF_DATE  # noqa: E402

DB_PATH = str(Path(__file__).parent / "imbank_demo.db")

# 전략별 표준 절차 (순서대로)
STRATEGY_STEPS = {
    "LEGAL_RECOVERY": ["기한이익상실 통보", "가압류 신청", "경매 신청", "감정평가", "매각기일", "배당"],
    "RESTRUCTURE":    ["채무조정 신청 접수", "채권단 협의", "조정안 의결", "변경약정 체결", "이행 모니터링"],
    "SALE":           ["매각자문사 선정", "실사(Due Diligence)", "입찰", "매각계약 체결", "채권 양도 완료"],
    "NORMALIZATION":  ["정상화 계획 수립", "신규자금 심사", "지원 실행", "경영 모니터링"],
    "WRITE_OFF":      ["상각 심사", "상각 승인", "부외 관리 전환", "추심 지속"],
}

# 케이스 상태별 진행 정도 (전체 단계 대비 완료 비율)
STATUS_PROGRESS = {
    "OPEN": 0.2, "IN_PROGRESS": 0.5, "RESTRUCTURED": 0.85,
    "RECOVERED": 1.0, "LIQUIDATED": 1.0, "WRITTEN_OFF": 1.0,
}


def main():
    random.seed(20260803)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS workout_milestone (
        milestone_id  TEXT PRIMARY KEY,
        case_id       TEXT NOT NULL,
        seq           INTEGER NOT NULL,
        step_name     TEXT NOT NULL,
        planned_date  TEXT,
        actual_date   TEXT,          -- NULL = 미완료
        status        TEXT NOT NULL, -- DONE / IN_PROGRESS / PLANNED
        notes         TEXT,
        UNIQUE(case_id, seq)
    );
    """)
    cur.execute("DELETE FROM workout_milestone")

    cases = cur.execute(
        "SELECT case_id, strategy, case_status, case_open_date FROM workout_case"
    ).fetchall()

    rows = []
    for case_id, strategy, status, open_date in cases:
        steps = STRATEGY_STEPS.get(strategy, STRATEGY_STEPS["LEGAL_RECOVERY"])
        progress = STATUS_PROGRESS.get(status, 0.4)
        n_done = max(1, round(len(steps) * progress))

        # 케이스 개시일부터 단계 간 30~90일 간격으로 진행됐다고 가정
        try:
            base = AS_OF_DATE - timedelta(days=random.randint(180, 540))
        except Exception:
            base = AS_OF_DATE - timedelta(days=300)

        cursor_date = base
        for i, step in enumerate(steps):
            planned = cursor_date + timedelta(days=random.randint(30, 90))
            if i < n_done:
                actual = planned + timedelta(days=random.randint(-10, 20))
                st = "DONE"
            elif i == n_done:
                actual = None
                st = "IN_PROGRESS"
            else:
                actual = None
                st = "PLANNED"
            rows.append((
                str(uuid.uuid4())[:12], case_id, i + 1, step,
                planned.strftime("%Y-%m-%d"),
                actual.strftime("%Y-%m-%d") if actual else None,
                st, None,
            ))
            cursor_date = planned

    cur.executemany("""
        INSERT INTO workout_milestone
        (milestone_id, case_id, seq, step_name, planned_date, actual_date, status, notes)
        VALUES (?,?,?,?,?,?,?,?)
    """, rows)
    conn.commit()
    print(f"✓ 워크아웃 마일스톤 {len(rows)}건 ({len(cases)}개 케이스)")
    conn.close()


if __name__ == "__main__":
    main()
