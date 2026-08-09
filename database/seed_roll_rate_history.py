#!/usr/bin/env python3
"""
Roll Rate 전이 이력 시드
========================
delinquency_stage_history 에 연체 단계의 월별 스냅샷을 생성한다.

1) 현재 OPEN 연체 27건: overdue_date 부터 30일 간격으로 AS_OF 까지,
   각 시점의 DPD 로 단계를 판정 - 실제 레코드의 dpd/stage 와 완전히 일치한다.
2) 과거 정상화 에피소드 ~90건: 연체 이력이 없는 ACTIVE 여신에 합성 생성.
   단계가 깊어질수록 정상화(CURED) 확률이 낮아지는 은행 실무 전이 확률을 쓴다.

멱등: 실행 시 기존 데이터를 전량 삭제 후 재생성 (random.seed 고정).
"""
import random
import sqlite3
import uuid
from datetime import date, timedelta
from pathlib import Path

DB = Path(__file__).parent / "imbank_demo.db"
AS_OF = date(2026, 7, 31)          # backend/app/core/config.py 와 동일 기준일

random.seed(42)


def stage_of(dpd: int) -> str:
    """backend/app/services/calculations.py determine_delinquency_stage 와 동일"""
    if dpd <= 0:
        return 'CURRENT'
    if dpd <= 30:
        return 'EARLY'
    if dpd <= 60:
        return 'MID'
    if dpd <= 90:
        return 'LATE'
    if dpd <= 180:
        return 'NPL'
    return 'WRITEOFF'


# 다음 달 행선지 확률: (정상화, 유지, 악화) - 단계가 깊을수록 정상화 급감
TRANSITION_P = {
    'EARLY': (0.55, 0.25, 0.20),
    'MID':   (0.30, 0.35, 0.35),
    'LATE':  (0.15, 0.35, 0.50),
    'NPL':   (0.05, 0.60, 0.35),
}
WORSE = {'EARLY': 'MID', 'MID': 'LATE', 'LATE': 'NPL', 'NPL': 'WRITEOFF'}


def main():
    con = sqlite3.connect(str(DB))
    con.execute("PRAGMA foreign_keys=ON")
    cur = con.cursor()

    cur.execute("DELETE FROM delinquency_stage_history")

    rows = []

    def add(fid: str, ep: str, seq: int, d: date, stage: str):
        rows.append((str(uuid.uuid4()), fid, ep, seq, d.isoformat(), stage))

    # ── 1) 현재 OPEN 연체의 실측 이력 ─────────────────────────────
    open_recs = cur.execute(
        "SELECT facility_id, overdue_date FROM delinquency_record WHERE status='OPEN'"
    ).fetchall()
    for fid, od in open_recs:
        start = date.fromisoformat(str(od))
        ep = f"EP-{fid}-OPEN"
        seq = 0
        d = start + timedelta(days=1)   # 연체 발생 직후 첫 스냅샷 (DPD 1)
        while d <= AS_OF:
            add(fid, ep, seq, d, stage_of((d - start).days))
            seq += 1
            d += timedelta(days=30)

    # ── 2) 과거 정상화 에피소드 (합성) ───────────────────────────
    used = {fid for fid, _ in open_recs}
    candidates = [r[0] for r in cur.execute(
        """SELECT facility_id FROM facility
           WHERE status='ACTIVE' AND facility_id NOT IN (
               SELECT facility_id FROM delinquency_record)
           ORDER BY facility_id"""
    ).fetchall() if r[0] not in used]
    random.shuffle(candidates)

    n_episodes = 90
    for i, fid in enumerate(candidates[:n_episodes]):
        # 에피소드 시작: 3~17개월 전
        start = AS_OF - timedelta(days=random.randint(90, 520))
        ep = f"EP-{fid}-{start.isoformat()}"
        stage, seq, d = 'EARLY', 0, start
        while True:
            add(fid, ep, seq, d, stage)
            seq += 1
            d += timedelta(days=30)
            if d >= AS_OF - timedelta(days=30):
                break                      # 미종결 상태로 관측 중단 (과거 이력만)
            cure, stay, worse = TRANSITION_P[stage]
            r = random.random()
            if r < cure:
                add(fid, ep, seq, d, 'CURED')
                break
            if r < cure + stay:
                continue                   # 단계 유지
            if stage == 'NPL':
                add(fid, ep, seq, d, 'WRITEOFF')
                break                      # 상각은 종결 상태
            stage = WORSE[stage]

    cur.executemany(
        """INSERT INTO delinquency_stage_history
           (history_id, facility_id, episode_id, seq, snapshot_date, stage)
           VALUES (?, ?, ?, ?, ?, ?)""",
        rows,
    )
    con.commit()

    # 검증 출력: 전이 행렬 미리보기
    print(f"스냅샷 {len(rows)}건 생성 "
          f"(OPEN 이력 {len(open_recs)}건 + 합성 에피소드 {min(n_episodes, len(candidates))}건)")
    for fs, ts, cnt in cur.execute(
        """SELECT h1.stage, h2.stage, COUNT(*)
           FROM delinquency_stage_history h1
           JOIN delinquency_stage_history h2
             ON h2.episode_id = h1.episode_id AND h2.seq = h1.seq + 1
           GROUP BY h1.stage, h2.stage ORDER BY h1.stage, h2.stage"""
    ).fetchall():
        print(f"  {fs:8s} → {ts:8s} {cnt}")
    con.close()


if __name__ == "__main__":
    main()
