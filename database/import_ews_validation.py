#!/usr/bin/env python3
"""
EWS 모델 검증 실측 지표 이관
============================
~/dev/css/v24 프로젝트는 60,000개 기업·부도 3,951건의 라벨 데이터로 EWS 모델을
백테스트했다. 그 산출물(리드타임 지표·피처 중요도)을 이관해, 근거 없는 수치였던
모델 화면을 실측 기반으로 만든다. 원본 12GB DB 는 옮기지 않는다 — 요약 지표만.

원본이 없는 환경(예: Render)에서 실행하면 기존 데이터를 보존하고 건너뛴다.
"""
import csv
import sqlite3
from pathlib import Path

DB_PATH = str(Path(__file__).parent / "imbank_demo.db")
SRC_DB = Path.home() / "dev" / "css" / "v24" / "ews_corporate_v24.db"
SRC_FI = Path.home() / "dev" / "css" / "ml" / "results" / "feature_importance.csv"

SCHEMA = """
CREATE TABLE IF NOT EXISTS ews_validation_metrics (
    metric_id       INTEGER PRIMARY KEY,
    scope_type      TEXT,     -- OVERALL / FOLD
    scope_value     TEXT,
    n_defaults      INTEGER,
    n_detected      INTEGER,
    detection_rate_pct REAL,
    avg_lead_months REAL,
    median_lead_months REAL,
    pct_alert_before_3m REAL,
    pct_alert_before_6m REAL,
    pct_alert_before_12m REAL,
    alert_threshold_score REAL,
    computed_ym     TEXT,
    source          TEXT DEFAULT 'ews_corporate_v24'
);
CREATE TABLE IF NOT EXISTS ews_feature_importance (
    rank            INTEGER PRIMARY KEY,
    feature_name    TEXT NOT NULL,
    importance      REAL NOT NULL,
    source          TEXT DEFAULT 'ews_corporate_v24'
);
"""


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(SCHEMA)

    if not SRC_DB.exists():
        n = cur.execute("SELECT COUNT(*) FROM ews_validation_metrics").fetchone()[0]
        print(f"원본 없음 — 기존 이관 데이터 {n}건 유지")
        conn.close()
        return

    src = sqlite3.connect(str(SRC_DB))
    rows = src.execute("""
        SELECT metric_id, scope_type, scope_value, n_defaults, n_detected,
               detection_rate_pct, avg_lead_months, median_lead_months,
               pct_alert_before_3m, pct_alert_before_6m, pct_alert_before_12m,
               alert_threshold_score, computed_ym
        FROM ews_leadtime_metrics
    """).fetchall()
    src.close()

    cur.execute("DELETE FROM ews_validation_metrics")
    cur.executemany("""
        INSERT INTO ews_validation_metrics
        (metric_id, scope_type, scope_value, n_defaults, n_detected,
         detection_rate_pct, avg_lead_months, median_lead_months,
         pct_alert_before_3m, pct_alert_before_6m, pct_alert_before_12m,
         alert_threshold_score, computed_ym)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)

    fi_count = 0
    if SRC_FI.exists():
        cur.execute("DELETE FROM ews_feature_importance")
        with open(SRC_FI, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames or []
            name_col = next((c for c in cols if "feature" in c.lower() or "name" in c.lower()), cols[0])
            imp_col = next((c for c in cols if "importance" in c.lower() or "gain" in c.lower()), cols[-1])
            items = sorted(
                ((row[name_col], float(row[imp_col] or 0)) for row in reader),
                key=lambda x: -x[1],
            )[:15]
        cur.executemany(
            "INSERT INTO ews_feature_importance (rank, feature_name, importance) VALUES (?,?,?)",
            [(i + 1, n, v) for i, (n, v) in enumerate(items)],
        )
        fi_count = len(items)

    conn.commit()
    print(f"✓ 검증 지표 {len(rows)}건 + 피처 중요도 {fi_count}건 이관")
    ov = cur.execute("""
        SELECT n_defaults, detection_rate_pct, avg_lead_months
        FROM ews_validation_metrics WHERE scope_type = 'OVERALL'
    """).fetchone()
    if ov:
        print(f"  전체: 부도 {ov[0]:,}건 · 탐지율 {ov[1]}% · 평균 리드타임 {ov[2]}개월")
    conn.close()


if __name__ == "__main__":
    main()
