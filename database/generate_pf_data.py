#!/usr/bin/env python3
"""
부동산PF 사업장 시드 데이터
===========================
2027 시행 예정인 PF 제도 개편(사업장 자기자본비율에 위험가중치·충당금·한도 연동)에
대비한 사업장 단위 관리 데이터. 기존 시스템에는 PF 가 업종코드 1건으로만 존재했다.

생성:
  - pf_project  : 사업장 ~40곳 (브릿지/본PF, 시행·시공사, 공정률, 분양률, 자기자본비율)
  - pf_progress : 사업장별 최근 12개월 공정·분양 추이
"""
import sqlite3
import random
import uuid
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from base_date import AS_OF_STR, months_back  # noqa: E402

DB_PATH = str(Path(__file__).parent / "imbank_demo.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS pf_project (
    project_id      TEXT PRIMARY KEY,
    project_name    TEXT NOT NULL,
    project_type    TEXT NOT NULL,      -- BRIDGE / MAIN
    property_type   TEXT NOT NULL,      -- APT / OFFICETEL / LOGISTICS / COMMERCIAL / KNOWLEDGE
    region          TEXT NOT NULL,      -- CAPITAL / DAEGU_GB / BUSAN_GN
    developer_name  TEXT,               -- 시행사
    constructor_name TEXT,              -- 시공사
    exposure        REAL NOT NULL,      -- 익스포저 (원)
    equity_ratio    REAL NOT NULL,      -- 사업장 자기자본비율 (%)
    progress_rate   REAL,               -- 공정률 (%)
    presale_rate    REAL,               -- 분양률 (%)
    ltv             REAL,
    maturity_date   TEXT,
    status          TEXT DEFAULT 'ACTIVE',   -- ACTIVE / COMPLETED / WATCHLIST
    base_date       TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS pf_progress (
    progress_id     TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL,
    reference_month TEXT NOT NULL,
    progress_rate   REAL,
    presale_rate    REAL,
    UNIQUE(project_id, reference_month)
);
"""

DEVELOPERS = ["대성디앤씨", "혁신개발", "미래도시개발", "한빛시티", "그랜드디벨롭",
              "청담피에프브이", "동성산업개발", "수성개발", "리버사이드PFV", "국제자산개발"]
CONSTRUCTORS = ["현대건설", "GS건설", "포스코이앤씨", "대우건설", "롯데건설",
                "화성산업", "서한", "태왕이앤씨", "HL디앤아이한라", "코오롱글로벌"]
PROPERTY_TYPES = ["APT", "OFFICETEL", "LOGISTICS", "COMMERCIAL", "KNOWLEDGE"]
PROPERTY_LABEL = {"APT": "아파트", "OFFICETEL": "오피스텔", "LOGISTICS": "물류센터",
                  "COMMERCIAL": "상업시설", "KNOWLEDGE": "지식산업센터"}
DISTRICT = {
    "CAPITAL":  ["하남 미사", "평택 고덕", "인천 검단", "고양 창릉", "용인 처인", "안산 단원"],
    "DAEGU_GB": ["대구 수성", "대구 달서", "구미 산동", "경산 중산", "포항 북구"],
    "BUSAN_GN": ["부산 강서", "창원 성산", "김해 장유", "양산 물금"],
}


def main():
    random.seed(20260731)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(SCHEMA)
    cur.execute("DELETE FROM pf_progress")
    cur.execute("DELETE FROM pf_project")

    months = months_back(12)
    projects, progress_rows = [], []

    n_projects = 40
    for i in range(n_projects):
        region = random.choices(["CAPITAL", "DAEGU_GB", "BUSAN_GN"], weights=[0.35, 0.45, 0.20])[0]
        ptype = random.choices(["BRIDGE", "MAIN"], weights=[0.3, 0.7])[0]
        prop = random.choice(PROPERTY_TYPES)
        district = random.choice(DISTRICT[region])
        name = f"{district} {PROPERTY_LABEL[prop]} PF"

        # 자기자본비율 — 2027 제도의 관리 축. 20% 이상은 소수, 대부분 5~15% 구간.
        equity_ratio = round(random.choices(
            [random.uniform(2, 5), random.uniform(5, 10),
             random.uniform(10, 15), random.uniform(15, 20), random.uniform(20, 28)],
            weights=[0.15, 0.35, 0.28, 0.14, 0.08])[0], 1)

        exposure = random.uniform(150, 1200) * 1e8   # 150억 ~ 1,200억

        if ptype == "BRIDGE":
            progress, presale = 0.0, 0.0
            maturity = f"202{random.choice([6, 7])}-{random.randint(1, 12):02d}-01"
        else:
            progress = round(random.uniform(15, 95), 1)
            # 분양률은 공정률과 대체로 동행하지만 일부 사업장은 크게 뒤처진다(위험)
            lag = random.choices([random.uniform(-5, 10), random.uniform(25, 55)],
                                 weights=[0.75, 0.25])[0]
            presale = round(max(0.0, min(100.0, progress - lag)), 1)
            maturity = f"202{random.choice([7, 8])}-{random.randint(1, 12):02d}-01"

        gap = progress - presale
        status = "WATCHLIST" if (ptype == "MAIN" and gap >= 30) or equity_ratio < 5 else "ACTIVE"

        pid = f"PF{i+1:03d}"
        projects.append((
            pid, name, ptype, prop, region,
            random.choice(DEVELOPERS), random.choice(CONSTRUCTORS),
            round(exposure, 2), equity_ratio, progress, presale,
            round(random.uniform(55, 85), 1), maturity, status, AS_OF_STR,
        ))

        # 12개월 추이 — 현재값에서 거꾸로 완만하게 감소
        p_cur, s_cur = progress, presale
        series = []
        for m in reversed(months):
            series.append((str(uuid.uuid4())[:12], pid, m, round(max(0, p_cur), 1),
                           round(max(0, s_cur), 1)))
            p_cur -= random.uniform(3, 9)
            s_cur -= random.uniform(1, 7)
        progress_rows.extend(reversed(series))

    cur.executemany("""
        INSERT INTO pf_project
        (project_id, project_name, project_type, property_type, region,
         developer_name, constructor_name, exposure, equity_ratio,
         progress_rate, presale_rate, ltv, maturity_date, status, base_date)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, projects)
    cur.executemany("""
        INSERT INTO pf_progress (progress_id, project_id, reference_month,
                                 progress_rate, presale_rate)
        VALUES (?,?,?,?,?)
    """, progress_rows)
    conn.commit()

    n_watch = sum(1 for p in projects if p[13] == "WATCHLIST")
    total = sum(p[7] for p in projects)
    print(f"✓ PF 사업장 {len(projects)}곳 (워치리스트 {n_watch}) · 추이 {len(progress_rows)}건")
    print(f"  총 익스포저 {total/1e12:.2f}조")
    conn.close()


if __name__ == "__main__":
    main()
