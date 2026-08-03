#!/usr/bin/env python3
"""
스토리 투어 기업 시드
=====================
투어는 한 기업의 생애주기 악화 경로를 따라간다:
EWS 경보 → 코베넌트 위반 → 건전성 강등 → 연체 → 워크아웃.

(주)영남바이오(CUST00339)는 이미 연체 1건·워크아웃 2건을 갖고 있어
앞 단계(EWS 경보·코베넌트 위반)만 보강해 이야기를 완성한다. 멱등.
"""
import sqlite3
import uuid
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from base_date import AS_OF_STR, days_before  # noqa: E402

DB_PATH = str(Path(__file__).parent / "imbank_demo.db")
STORY_CUSTOMER = "CUST00339"


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    name = cur.execute("SELECT customer_name FROM customer WHERE customer_id=?",
                       (STORY_CUSTOMER,)).fetchone()
    if not name:
        print(f"스토리 고객 {STORY_CUSTOMER} 없음 — 건너뜀")
        return
    name = name[0]

    # 1) EWS 종합점수를 WARNING 구간으로 (경보의 근거)
    cur.execute("""
        UPDATE ews_composite_score
        SET composite_score = 41.2, risk_level = 'HIGH', ews_grade = 'WARNING',
            score_trend = 'DETERIORATING'
        WHERE customer_id = ?
    """, (STORY_CUSTOMER,))

    # 2) EWS 경보 (거래행태 채널, HIGH) — 알림 메뉴·대시보드에 노출된다
    cur.execute("DELETE FROM ews_alert WHERE alert_id = 'EWS_STORY01'")
    cur.execute("""
        INSERT INTO ews_alert
        (alert_id, customer_id, alert_date, alert_type, alert_subtype, severity,
         indicator_value, threshold_value, description, status)
        VALUES ('EWS_STORY01', ?, ?, 'BEHAVIOR', 'LIMIT_UTILIZATION', 'HIGH',
                0.94, 0.85, '한도소진율 94% — 유동성 압박 신호', 'OPEN')
    """, (STORY_CUSTOMER, days_before(210).strftime("%Y-%m-%d")))

    # 3) 코베넌트 위반 — 이 고객 여신의 코베넌트에 BREACH 점검 기록
    fac = cur.execute("""
        SELECT facility_id FROM facility WHERE customer_id = ? LIMIT 1
    """, (STORY_CUSTOMER,)).fetchone()
    if fac:
        cov = cur.execute("""
            SELECT covenant_id FROM covenant WHERE facility_id = ? LIMIT 1
        """, (fac[0],)).fetchone()
        if not cov:
            cov_id = f"COV_STORY01"
            cur.execute("DELETE FROM covenant WHERE covenant_id = ?", (cov_id,))
            cur.execute("""
                INSERT INTO covenant
                (covenant_id, facility_id, covenant_type, covenant_code, covenant_name,
                 metric, operator, threshold_value, check_frequency, status)
                VALUES (?, ?, 'FINANCIAL', 'FC01', '부채비율 200% 이하 유지',
                        'debt_ratio', 'LE', 200.0, 'SEMI', 'ACTIVE')
            """, (cov_id, fac[0]))
            cov = (cov_id,)
        cur.execute("DELETE FROM covenant_check WHERE check_id = 'CHK_STORY01'")
        cur.execute("""
            INSERT INTO covenant_check
            (check_id, covenant_id, check_date, actual_value, threshold_value,
             result, breach_severity, action_taken)
            VALUES ('CHK_STORY01', ?, ?, 247.3, 200.0, 'BREACH', 'MAJOR',
                    '추가 담보 요구 및 30일 치유 기간 부여')
        """, (cov[0], days_before(150).strftime("%Y-%m-%d")))

    conn.commit()
    print(f"✓ 스토리 기업 보강: {name} ({STORY_CUSTOMER})")
    print(f"  EWS 41.2(WARNING) · 경보 1건 · 코베넌트 위반 1건 · 기존 연체/워크아웃 유지")
    conn.close()


if __name__ == "__main__":
    main()
