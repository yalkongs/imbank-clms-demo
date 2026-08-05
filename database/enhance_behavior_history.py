#!/usr/bin/env python3
"""
거래행태 월별 이력에 리스크 연동 추세 부여
==========================================
기존 시드는 한도소진율이 추세 없는 노이즈(순변화 2.2%p < 진폭 5.6%p)라
포트폴리오 맵 타임 슬라이더에서 포인트가 제자리 왕복만 했다.

원칙:
  · 최신월(현재) 값은 앵커로 보존 - 현재 시점 화면들과 정합 유지
  · 과거 11개월을 "현재로 수렴하는 경로"로 재작성
      - 고정이하(NPL)      : 15~30%p 낮은 곳에서 상승 (한도 잠식 경로)
      - 요주의/EWS<55      : 8~18%p 상승
      - 건전               : ±4%p 완만한 랜덤워크
  · (주)영남바이오(CUST00339)는 스토리 투어("한도소진율 94% 치솟음")에 맞춰
    최신값을 94%로 올리고 45%→94% 가속 상승 경로를 만든다
  · 기업별 고정 시드 - 재실행해도 같은 결과 (결정적)
"""
import hashlib
import random
import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "imbank_demo.db"
STORY_ID = "CUST00339"
STORY_END = 0.94          # 투어 서사: 한도소진율 94%

con = sqlite3.connect(DB)
cur = con.cursor()

months = [r[0] for r in cur.execute(
    "SELECT DISTINCT reference_month FROM ews_transaction_behavior ORDER BY 1"
).fetchall()]
n = len(months)
assert n >= 6, "월별 데이터 부족"

# 고객별 리스크 신호: 최악 분류 · 최신 EWS 종합점수
risk = {}
for cid, cls in cur.execute("""
    SELECT customer_id,
           MAX(CASE classification WHEN 'LOSS' THEN 5 WHEN 'DOUBTFUL' THEN 4
               WHEN 'SUBSTANDARD' THEN 3 WHEN 'PRECAUTIONARY' THEN 2 ELSE 1 END)
    FROM facility WHERE status = 'ACTIVE' GROUP BY customer_id
"""):
    risk[cid] = {"cls": cls, "ews": None}
for cid, ews in cur.execute("""
    SELECT customer_id, composite_score FROM (
        SELECT customer_id, composite_score,
               ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY score_date DESC) rn
        FROM ews_composite_score) WHERE rn = 1
"""):
    if cid in risk:
        risk[cid]["ews"] = ews

rows = cur.execute("""
    SELECT customer_id, reference_month, limit_utilization
    FROM ews_transaction_behavior ORDER BY customer_id, reference_month
""").fetchall()
by_cust: dict = {}
for cid, m, v in rows:
    by_cust.setdefault(cid, {})[m] = v

updated = 0
for cid, series in by_cust.items():
    if len(series) < n:
        continue
    rng = random.Random(int(hashlib.md5(cid.encode()).hexdigest()[:8], 16))
    end = series[months[-1]] or 0.4

    if cid == STORY_ID:
        end = STORY_END
        start = 0.45
        # 가속 상승(볼록) - 후반에 급등하는 서사
        path = [start + (end - start) * ((i / (n - 1)) ** 1.8) for i in range(n)]
        noise = 0.008
    else:
        r = risk.get(cid, {"cls": 1, "ews": None})
        ews = r["ews"]
        if r["cls"] >= 3:                                  # NPL
            rise = rng.uniform(0.15, 0.30)
        elif r["cls"] == 2 or (ews is not None and ews < 55):
            rise = rng.uniform(0.08, 0.18)
        elif ews is not None and ews < 70:                 # EWS 주의(MEDIUM) 구간
            rise = rng.uniform(0.05, 0.12)
        else:                                              # 건전: 완만한 드리프트
            rise = rng.uniform(-0.06, 0.06)
        start = end - rise
        path = [start + (end - start) * (i / (n - 1)) for i in range(n)]
        noise = 0.012

    # AR(1) 성격의 잔차 - 인접월이 자연스럽게 이어지게
    eps = 0.0
    for i, m in enumerate(months):
        eps = eps * 0.5 + rng.gauss(0, noise)
        v = path[i] + (0.0 if i == n - 1 and cid != STORY_ID else eps)
        if i == n - 1 and cid != STORY_ID:
            v = end                                        # 앵커 보존
        v = max(0.03, min(0.98, v))
        cur.execute("""
            UPDATE ews_transaction_behavior SET limit_utilization = ?
            WHERE customer_id = ? AND reference_month = ?
        """, (round(v, 4), cid, m))
    updated += 1

con.commit()
cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
print(f"재작성 {updated}개사 x {n}개월")

# 검증: 추세 대 노이즈 비율
import statistics
rows = cur.execute("""
    SELECT customer_id, reference_month, limit_utilization
    FROM ews_transaction_behavior ORDER BY customer_id, reference_month
""").fetchall()
s: dict = {}
for cid, m, v in rows:
    s.setdefault(cid, []).append(v)
trends = [arr[-1] - arr[0] for arr in s.values() if len(arr) >= n]
print(f"순변화 |Δ| 중앙값: {statistics.median(abs(t) for t in trends)*100:.1f}%p "
      f"(5%p 이상 {sum(1 for t in trends if abs(t) > 0.05)}개)")
story = [round(v * 100, 1) for v in s[STORY_ID]]
print("영남바이오:", story)
