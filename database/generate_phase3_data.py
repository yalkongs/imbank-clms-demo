"""
iM뱅크 CLMS Phase 3 시드 데이터 생성
- automation_action: EWS CRITICAL / COVENANT_EOD / DPD_90 트리거 ~200건
"""
import sqlite3
import uuid
import random
from datetime import datetime, timedelta
import math

DB_PATH = "database/imbank_demo.db"

def sigmoid(x):
    return 1 / (1 + math.exp(-x))

def predict_default_prob(ews_score=None, dpd=0, pd=0.05, dscr=1.2):
    """로지스틱 부실전환확률 모델"""
    intercept = -3.5
    beta_ews  = -0.04
    beta_dpd  = 0.05
    beta_pd   = 12.0
    beta_dscr = -0.8

    ews_val  = ews_score if ews_score is not None else 50.0
    logit    = (intercept
                + beta_ews * ews_val
                + beta_dpd * min(dpd, 180)
                + beta_pd  * min(pd, 1.0)
                + beta_dscr * min(dscr, 3.0))
    return round(sigmoid(logit), 4)


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ────────────────────────────────────────────
    # 1. 기존 automation_action 초기화
    # ────────────────────────────────────────────
    cur.execute("DELETE FROM automation_action")

    # ────────────────────────────────────────────
    # 2. 소스 데이터 수집
    # ────────────────────────────────────────────

    # EWS CRITICAL 고객 (composite_score < 40)
    ews_critical = cur.execute("""
        SELECT e.customer_id, e.composite_score,
               c.customer_name
        FROM ews_composite_score e
        JOIN customer c ON e.customer_id = c.customer_id
        WHERE e.score_date = (
            SELECT MAX(score_date) FROM ews_composite_score e2
            WHERE e2.customer_id = e.customer_id
        )
        AND e.composite_score < 40
        ORDER BY e.composite_score ASC
        LIMIT 60
    """).fetchall()

    # COVENANT EOD 고객 (최근 코베넌트 위반) — covenant.result = 'EOD' or breach
    covenant_eod = cur.execute("""
        SELECT f.customer_id, cc.check_id,
               f.facility_id,
               c.customer_name
        FROM covenant_check cc
        JOIN covenant cv ON cc.covenant_id = cv.covenant_id
        JOIN facility f ON cv.facility_id = f.facility_id
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE cc.result IN ('BREACH', 'EOD')
        ORDER BY cc.check_date DESC
        LIMIT 50
    """).fetchall()

    # DPD 90+ 시설 (연체관리에서)
    dpd_90 = cur.execute("""
        SELECT f.facility_id, f.customer_id,
               f.dpd,
               c.customer_name
        FROM facility f
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.dpd >= 90
        ORDER BY f.dpd DESC
        LIMIT 60
    """).fetchall()

    # risk_parameter 조회 (pd, lgd) — application_id 기준
    # dscr은 financial_ratio에서 최신값 조회
    rp_map = {}
    rp_rows = cur.execute("""
        SELECT la.customer_id, rp.ttc_pd, rp.lgd,
               fr.dscr
        FROM risk_parameter rp
        JOIN loan_application la ON rp.application_id = la.application_id
        LEFT JOIN (
            SELECT customer_id, dscr FROM financial_ratio
            WHERE (customer_id, fiscal_year) IN (
                SELECT customer_id, MAX(fiscal_year) FROM financial_ratio GROUP BY customer_id
            )
        ) fr ON la.customer_id = fr.customer_id
    """).fetchall()
    for r in rp_rows:
        rp_map[r["customer_id"]] = {
            "pd": r["ttc_pd"] or 0.05,
            "lgd": r["lgd"] or 0.45,
            "dscr": r["dscr"] or 1.2,
        }

    # EWS 최신 점수 맵
    ews_map = {}
    ews_rows = cur.execute("""
        SELECT customer_id, composite_score
        FROM ews_composite_score
        WHERE score_date = (
            SELECT MAX(score_date) FROM ews_composite_score e2
            WHERE e2.customer_id = ews_composite_score.customer_id
        )
    """).fetchall()
    for r in ews_rows:
        ews_map[r["customer_id"]] = r["composite_score"]

    # ────────────────────────────────────────────
    # 3. automation_action 생성
    # ────────────────────────────────────────────
    now = datetime.now()
    actions = []

    TRIGGER_ACTION_MAP = {
        "EWS_CRITICAL":  ["NOTIFY_RM", "RECLASSIFY", "FREEZE_LIMIT", "ECL_RECALC"],
        "COVENANT_EOD":  ["CREATE_WORKOUT", "NOTIFY_RM", "FREEZE_LIMIT"],
        "DPD_90":        ["CREATE_WORKOUT", "RECLASSIFY", "ECL_RECALC"],
    }

    PRIORITY_MAP = {
        "EWS_CRITICAL": "HIGH",
        "COVENANT_EOD": "CRITICAL",
        "DPD_90":       "CRITICAL",
    }

    STATUS_WEIGHTS = {
        "PENDING":  0.40,
        "EXECUTED": 0.45,
        "SKIPPED":  0.10,
        "FAILED":   0.05,
    }

    def pick_status():
        r = random.random()
        cumul = 0.0
        for s, w in STATUS_WEIGHTS.items():
            cumul += w
            if r < cumul:
                return s
        return "PENDING"

    def result_summary(action_type, status):
        if status == "PENDING":
            return None
        templates = {
            "CREATE_WORKOUT":  "Workout 케이스 자동 생성 완료",
            "NOTIFY_RM":       "RM 담당자 이메일/알림 발송 완료",
            "RECLASSIFY":      "자산건전성 재분류 실행 완료",
            "ECL_RECALC":      "ECL 재산출 완료, 충당금 검토 필요",
            "FREEZE_LIMIT":    "여신 한도 일시 동결 처리 완료",
        }
        return templates.get(action_type, "처리 완료")

    # ─── EWS CRITICAL 트리거 ───
    for row in ews_critical:
        cid = row["customer_id"]
        rp  = rp_map.get(cid, {"pd": 0.07, "lgd": 0.45, "dscr": 1.1})
        ews = row["composite_score"]
        dp  = predict_default_prob(ews_score=ews, dpd=0, pd=rp["pd"], dscr=rp["dscr"])

        # 1~2개 액션 생성
        action_types = random.sample(TRIGGER_ACTION_MAP["EWS_CRITICAL"],
                                     k=random.randint(1, 2))
        for at in action_types:
            created_offset = random.randint(0, 30)
            created_at = now - timedelta(days=created_offset,
                                         hours=random.randint(0, 23))
            status = pick_status()
            executed_at = None
            if status in ("EXECUTED", "FAILED"):
                executed_at = created_at + timedelta(hours=random.randint(1, 48))

            actions.append({
                "action_id":          str(uuid.uuid4()),
                "trigger_type":       "EWS_CRITICAL",
                "trigger_source_id":  None,
                "customer_id":        cid,
                "facility_id":        None,
                "action_type":        at,
                "action_status":      status,
                "priority":           PRIORITY_MAP["EWS_CRITICAL"],
                "default_probability": dp,
                "result_summary":     result_summary(at, status),
                "created_at":         created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "executed_at":        executed_at.strftime("%Y-%m-%d %H:%M:%S") if executed_at else None,
            })

    # ─── COVENANT EOD 트리거 ───
    for row in covenant_eod:
        cid  = row["customer_id"]
        fid  = row["facility_id"]
        rp   = rp_map.get(cid, {"pd": 0.10, "lgd": 0.50, "dscr": 0.9})
        ews  = ews_map.get(cid, 45.0)
        dp   = predict_default_prob(ews_score=ews, dpd=0, pd=rp["pd"], dscr=rp["dscr"])

        action_types = random.sample(TRIGGER_ACTION_MAP["COVENANT_EOD"],
                                     k=random.randint(1, 2))
        for at in action_types:
            created_offset = random.randint(0, 20)
            created_at = now - timedelta(days=created_offset,
                                         hours=random.randint(0, 23))
            status = pick_status()
            executed_at = None
            if status in ("EXECUTED", "FAILED"):
                executed_at = created_at + timedelta(hours=random.randint(1, 24))

            actions.append({
                "action_id":          str(uuid.uuid4()),
                "trigger_type":       "COVENANT_EOD",
                "trigger_source_id":  row["check_id"],
                "customer_id":        cid,
                "facility_id":        fid,
                "action_type":        at,
                "action_status":      status,
                "priority":           PRIORITY_MAP["COVENANT_EOD"],
                "default_probability": dp,
                "result_summary":     result_summary(at, status),
                "created_at":         created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "executed_at":        executed_at.strftime("%Y-%m-%d %H:%M:%S") if executed_at else None,
            })

    # ─── DPD 90+ 트리거 ───
    for row in dpd_90:
        cid  = row["customer_id"]
        fid  = row["facility_id"]
        dpd  = row["dpd"] or 90
        rp   = rp_map.get(cid, {"pd": 0.15, "lgd": 0.55, "dscr": 0.8})
        ews  = ews_map.get(cid, 40.0)
        dp   = predict_default_prob(ews_score=ews, dpd=dpd, pd=rp["pd"], dscr=rp["dscr"])

        action_types = random.sample(TRIGGER_ACTION_MAP["DPD_90"],
                                     k=random.randint(1, 3))
        for at in action_types:
            created_offset = random.randint(0, 15)
            created_at = now - timedelta(days=created_offset,
                                         hours=random.randint(0, 23))
            status = pick_status()
            executed_at = None
            if status in ("EXECUTED", "FAILED"):
                executed_at = created_at + timedelta(hours=random.randint(1, 12))

            actions.append({
                "action_id":          str(uuid.uuid4()),
                "trigger_type":       "DPD_90",
                "trigger_source_id":  fid,
                "customer_id":        cid,
                "facility_id":        fid,
                "action_type":        at,
                "action_status":      status,
                "priority":           PRIORITY_MAP["DPD_90"],
                "default_probability": dp,
                "result_summary":     result_summary(at, status),
                "created_at":         created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "executed_at":        executed_at.strftime("%Y-%m-%d %H:%M:%S") if executed_at else None,
            })

    # ────────────────────────────────────────────
    # 4. INSERT
    # ────────────────────────────────────────────
    cur.executemany("""
        INSERT INTO automation_action (
            action_id, trigger_type, trigger_source_id,
            customer_id, facility_id, action_type,
            action_status, priority, default_probability,
            result_summary, created_at, executed_at
        ) VALUES (
            :action_id, :trigger_type, :trigger_source_id,
            :customer_id, :facility_id, :action_type,
            :action_status, :priority, :default_probability,
            :result_summary, :created_at, :executed_at
        )
    """, actions)

    conn.commit()
    print(f"automation_action: {len(actions)}건 생성")

    # ────────────────────────────────────────────
    # 5. 통계 출력
    # ────────────────────────────────────────────
    stats = cur.execute("""
        SELECT trigger_type, action_status, COUNT(*) as cnt
        FROM automation_action
        GROUP BY trigger_type, action_status
        ORDER BY trigger_type, action_status
    """).fetchall()
    print("\n[트리거 × 상태 분포]")
    for r in stats:
        print(f"  {r[0]:20s} | {r[1]:10s} | {r[2]}건")

    pending = cur.execute("""
        SELECT COUNT(*) FROM automation_action WHERE action_status = 'PENDING'
    """).fetchone()[0]
    print(f"\nPENDING 건수: {pending}건")

    conn.close()
    print("\nPhase 3 데이터 생성 완료.")


if __name__ == "__main__":
    main()
