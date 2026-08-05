#!/usr/bin/env python3
"""
여신통제 확장 시드 (제3자 리뷰 P0 의 PoC 최소 조각)
====================================================
1. policy_exception        - 정책 예외의 구조화 (규정→사유→완화수단→승인→재검토→성과)
2. ews_action              - EWS 경보별 조치의무 (Playbook 단계·담당·기한·상태)
3. rate_reduction_request  - 기업 금리인하요구권 (은행법 시행령 §18-4, 10영업일 SLA)
4. approval_history 보강    - 여신철 재현을 위해 승인 단계 이력이 없는 기존 승인 건 보완

멱등: 테이블은 IF NOT EXISTS, 시드는 기존 건 수 확인 후 삽입.
"""
import random
import sqlite3
import uuid
from datetime import date, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from base_date import AS_OF_STR  # noqa: E402

DB = str(Path(__file__).parent / "imbank_demo.db")
random.seed(20260807)
AS_OF = date.fromisoformat(AS_OF_STR)


def uid(p):
    return f"{p}_{uuid.uuid4().hex[:10].upper()}"


def biz_days_after(start: date, n: int) -> date:
    d, added = start, 0
    while added < n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            added += 1
    return d


con = sqlite3.connect(DB)
cur = con.cursor()

# ── 테이블 ──────────────────────────────────────────────
cur.executescript("""
CREATE TABLE IF NOT EXISTS policy_exception (
    exception_id   TEXT PRIMARY KEY,
    application_id TEXT REFERENCES loan_application(application_id),
    customer_id    TEXT REFERENCES customer(customer_id),
    rule_ref       TEXT NOT NULL,      -- 예외 대상 규정
    rule_version   TEXT,               -- 적용 규정 버전
    reason         TEXT NOT NULL,      -- 예외 발생 이유
    mitigation     TEXT,               -- 손실완화 수단
    approver_level TEXT,
    approver_name  TEXT,
    approved_at    DATE,
    valid_until    DATE,
    review_date    DATE,
    status         TEXT DEFAULT 'ACTIVE',   -- ACTIVE / EXPIRED / CLOSED
    outcome        TEXT,                    -- 실제 성과 (종결 시)
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ews_action (
    action_id    TEXT PRIMARY KEY,
    alert_id     TEXT REFERENCES ews_alert(alert_id),
    customer_id  TEXT,
    step_no      INTEGER,
    step         TEXT,                 -- Playbook 단계
    owner        TEXT,                 -- 담당 (RM·심사역·사후관리)
    due_date     DATE,
    status       TEXT DEFAULT 'OPEN',  -- OPEN / IN_PROGRESS / DONE
    action_taken TEXT,
    completed_at DATE,
    escalated    INTEGER DEFAULT 0,    -- 기한초과 자동 상향보고 여부
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS rate_reduction_request (
    request_id      TEXT PRIMARY KEY,
    customer_id     TEXT REFERENCES customer(customer_id),
    facility_id     TEXT REFERENCES facility(facility_id),
    request_date    DATE NOT NULL,
    grounds         TEXT,              -- FIN_IMPROVE / GRADE_UP / COLLATERAL_ADD / REVENUE_UP
    grounds_detail  TEXT,
    due_date        DATE,              -- 접수 + 10영업일 (보완기간 제외)
    status          TEXT DEFAULT 'RECEIVED',  -- RECEIVED/REVIEWING/ACCEPTED/PARTIAL/REJECTED
    old_rate        REAL,
    proposed_rate   REAL,              -- 재산정 결과
    decided_rate    REAL,
    decision_reason TEXT,
    decided_at      DATE,
    notified_at     DATE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_polex_app  ON policy_exception(application_id);
CREATE INDEX IF NOT EXISTS idx_ewsact_alert ON ews_action(alert_id);
CREATE INDEX IF NOT EXISTS idx_rrr_status ON rate_reduction_request(status, due_date);
""")

# ── 1. 정책 예외 ───────────────────────────────────────
if cur.execute("SELECT COUNT(*) FROM policy_exception").fetchone()[0] == 0:
    apps = cur.execute("""
        SELECT la.application_id, la.customer_id, la.requested_amount
        FROM loan_application la WHERE la.status IN ('APPROVED','DISBURSED')
        ORDER BY la.requested_amount DESC LIMIT 60
    """).fetchall()
    RULES = [
        ("여신업무지침 §4.2", "담보인정비율(LTV) 상한 70% 초과 취급", "추가 연대보증 및 예금 질권 설정", "부서장"),
        ("여신업무지침 §7.1", "동일업종 내부 집중한도 초과", "6개월 내 타업종 분산 감축 계획", "임원"),
        ("신용정책 §3.4", "BB- 미만 등급 신규취급 제한 예외", "보증기관 80% 보증부 취급", "부서장"),
        ("PF취급기준 §2.2", "사업장 자기자본비율 최소기준(20%) 미달", "책임준공 확약 + 분양률 트리거 조기상환", "여신위원회"),
        ("여신업무지침 §5.3", "무담보 신용한도 상한 초과", "재무 코베넌트(부채비율 250%) 추가", "부서장"),
        ("신용정책 §6.1", "그룹 합산 내부한도 근접 상태 신규취급", "분기별 그룹 익스포저 재점검 조건", "임원"),
    ]
    rows = []
    pick = random.sample(apps, 12)
    for i, (app_id, cust_id, amt) in enumerate(pick):
        rule = RULES[i % len(RULES)]
        approved = AS_OF - timedelta(days=random.randint(30, 420))
        valid = approved + timedelta(days=365)
        review = approved + timedelta(days=180)
        if i < 7:
            status, outcome = "ACTIVE", None
        elif i < 9:
            status, outcome = "EXPIRED", None
        else:
            status = "CLOSED"
            outcome = random.choice([
                "예외기간 중 연체 없음 - 정상 종결",
                "담보 보강 완료로 예외 해소",
                "등급 상향(BB+)으로 예외 요건 소멸",
            ])
        rows.append((uid("PEX"), app_id, cust_id, rule[0], "2026-01 개정판", rule[1], rule[2],
                     rule[3], {"부서장": "박부장", "임원": "이전무", "여신위원회": "여신위원회"}[rule[3]],
                     approved.isoformat(), valid.isoformat(), review.isoformat(), status, outcome))
    cur.executemany("""INSERT INTO policy_exception
        (exception_id, application_id, customer_id, rule_ref, rule_version, reason, mitigation,
         approver_level, approver_name, approved_at, valid_until, review_date, status, outcome)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", rows)
    print(f"정책 예외 {len(rows)}건")

# ── 2. EWS 조치 ────────────────────────────────────────
PLAYBOOK = {
    "DEFAULT": [("사실 확인·오탐 판정", "심사역", 3), ("고객 접촉·소명 청취", "담당 RM", 7),
                ("등급·한도·분류 영향 검토", "심사역", 10)],
    "LIMIT": [("한도소진 원인 확인", "담당 RM", 2), ("신규실행 보류 검토", "심사역", 5),
              ("한도 동결·감액 품의", "사후관리", 10)],
    "FINANCIAL": [("재무자료 징구·검증", "담당 RM", 5), ("코베넌트 추가점검", "심사역", 10),
                  ("Watchlist 편입 검토", "사후관리", 15)],
}
if cur.execute("SELECT COUNT(*) FROM ews_action").fetchone()[0] == 0:
    alerts = cur.execute("""
        SELECT alert_id, customer_id, alert_type, severity, alert_date, status FROM ews_alert
    """).fetchall()
    rows = []
    for alert_id, cust_id, atype, sev, adate, astatus in alerts:
        steps = PLAYBOOK.get("LIMIT" if (atype or "").startswith("LIMIT") else
                             "FINANCIAL" if (atype or "").startswith("FIN") else "DEFAULT")
        base = date.fromisoformat(adate)
        closed = astatus != 'OPEN'
        for no, (step, owner, days) in enumerate(steps, 1):
            due = biz_days_after(base, days)
            if closed:
                status_, taken, done = "DONE", "조치 완료 - 이상 없음 확인", min(due, AS_OF)
                rows.append((uid("EACT"), alert_id, cust_id, no, step, owner, due.isoformat(),
                             status_, taken, done.isoformat(), 0))
            else:
                # 진행 중 경보: 1단계 완료, 2단계 진행, 3단계 대기 (기한 임박/초과 연출)
                if no == 1:
                    rows.append((uid("EACT"), alert_id, cust_id, no, step, owner, due.isoformat(),
                                 "DONE", "거래내역 확인 - 유효 경보로 판정", due.isoformat(), 0))
                elif no == 2:
                    overdue = due < AS_OF
                    rows.append((uid("EACT"), alert_id, cust_id, no, step, owner, due.isoformat(),
                                 "IN_PROGRESS", None, None, 1 if overdue else 0))
                else:
                    rows.append((uid("EACT"), alert_id, cust_id, no, step, owner, due.isoformat(),
                                 "OPEN", None, None, 0))
    cur.executemany("""INSERT INTO ews_action
        (action_id, alert_id, customer_id, step_no, step, owner, due_date, status,
         action_taken, completed_at, escalated) VALUES (?,?,?,?,?,?,?,?,?,?,?)""", rows)
    print(f"EWS 조치 {len(rows)}건 (경보 {len(alerts)}건)")

# ── 3. 금리인하요구권 ──────────────────────────────────
GROUNDS = [
    ("FIN_IMPROVE", "직전 결산 부채비율 32%p 개선"),
    ("GRADE_UP", "신용등급 BB+ → BBB- 상향"),
    ("REVENUE_UP", "연매출 28% 증가 및 흑자 전환"),
    ("COLLATERAL_ADD", "본사 사옥 추가 담보 제공"),
]
if cur.execute("SELECT COUNT(*) FROM rate_reduction_request").fetchone()[0] == 0:
    facs = cur.execute("""
        SELECT f.facility_id, f.customer_id, f.final_rate FROM facility f
        WHERE f.status = 'ACTIVE' AND f.final_rate > 0.055
        ORDER BY RANDOM() LIMIT 16
    """).fetchall()
    rows = []
    for i, (fac_id, cust_id, rate) in enumerate(facs):
        g, gd = GROUNDS[i % 4]
        if i < 2:      # 처리중 - 기한 임박/초과 연출
            req = AS_OF - timedelta(days=12 if i == 0 else 16)
            due = biz_days_after(req, 10)
            rows.append((uid("RRR"), cust_id, fac_id, req.isoformat(), g, gd, due.isoformat(),
                         "REVIEWING", rate, None, None, None, None, None))
        elif i < 4:    # 접수 직후
            req = AS_OF - timedelta(days=2 + i)
            due = biz_days_after(req, 10)
            rows.append((uid("RRR"), cust_id, fac_id, req.isoformat(), g, gd, due.isoformat(),
                         "RECEIVED", rate, None, None, None, None, None))
        else:          # 완료 12건: 수용 6 / 부분 3 / 거절 3
            req = AS_OF - timedelta(days=random.randint(30, 300))
            due = biz_days_after(req, 10)
            decided = biz_days_after(req, random.randint(4, 9))
            if i < 10:
                st, cut = "ACCEPTED", random.uniform(0.003, 0.009)
                reason = "재산정 결과 신용원가 하락 확인 - 전액 수용"
            elif i < 13:
                st, cut = "PARTIAL", random.uniform(0.001, 0.003)
                reason = "등급 상향 반영하되 조달원가 상승분 상쇄 - 부분 수용"
            else:
                st, cut = "REJECTED", 0.0
                reason = "재산정 결과 기존 금리가 이미 신용원가 하회 - 거절"
            new_rate = round(rate - cut, 6)
            rows.append((uid("RRR"), cust_id, fac_id, req.isoformat(), g, gd, due.isoformat(),
                         st, rate, new_rate, new_rate if st != "REJECTED" else rate,
                         reason, decided.isoformat(), biz_days_after(decided, 1).isoformat()))
    cur.executemany("""INSERT INTO rate_reduction_request
        (request_id, customer_id, facility_id, request_date, grounds, grounds_detail, due_date,
         status, old_rate, proposed_rate, decided_rate, decision_reason, decided_at, notified_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", rows)
    print(f"금리인하요구 {len(rows)}건")

# ── 4. approval_history 보강 (여신철 재현용) ────────────
n_hist = cur.execute("SELECT COUNT(*) FROM approval_history").fetchone()[0]
if n_hist < 50:
    apps = cur.execute("""
        SELECT la.application_id, la.requested_amount, la.application_date
        FROM loan_application la
        WHERE la.status IN ('APPROVED','DISBURSED')
          AND NOT EXISTS (SELECT 1 FROM approval_history ah
                          WHERE ah.application_id = la.application_id)
        ORDER BY la.application_date DESC LIMIT 60
    """).fetchall()
    NAMES = {"STAFF": "김심사", "TEAM_LEAD": "김여신", "DEPT_HEAD": "박부장",
             "EXECUTIVE": "이전무", "COMMITTEE": "여신위원회"}
    rows = []
    for app_id, amt, adate in apps:
        eok = (amt or 0) / 1e8
        chain = ["STAFF", "TEAM_LEAD"]
        if eok > 50:
            chain.append("DEPT_HEAD")
        if eok > 300:
            chain.append("EXECUTIVE")
        if eok > 1000:
            chain.append("COMMITTEE")
        base = date.fromisoformat(adate[:10]) if adate else AS_OF - timedelta(days=90)
        for j, lvl in enumerate(chain):
            final = j == len(chain) - 1
            rows.append((uid("APH"), app_id, lvl, f"U{random.randint(100,999)}", NAMES[lvl],
                         "APPROVED", "여신조건 준수 확약" if final else None,
                         "전결 규정에 따른 최종 승인" if final else "검토 의견 첨부 - 상신",
                         biz_days_after(base, j + 1).isoformat()))
    cur.executemany("""INSERT INTO approval_history
        (approval_id, application_id, approval_level, approver_id, approver_name,
         decision, conditions, comments, decided_at) VALUES (?,?,?,?,?,?,?,?,?)""", rows)
    print(f"결재 이력 보강 {len(rows)}건")

con.commit()
cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
print("완료")
