#!/usr/bin/env python3
"""
EWS 8채널 확장 데모 데이터 생성기 (docs/EWS_8CHANNEL_DESIGN_2026-08-21.md §7)
==============================================================================
1. 신규 3채널 원천 24개월: 카드매출(동의 70%)·고용(동의 60%)·상거래연체(법정집중)
2. 동의 레지스트리 (만료·임박·철회 사례 포함)
3. 부도·워크아웃 이벤트 기업에 채널별로 **서로 다른** 악화 시작점 주입
   (카드 9개월 전 → 고용 5개월 전 → 상거래 4개월 전) - 검증 화면이 채널별
   리드타임 차이를 실측으로 보여주기 위함. 정상 기업 일부에 노이즈 경보 주입
   (오경보율 0% 는 백테스트의 신뢰를 깎는다)
4. 8채널 월별 점수 패널 (이벤트 85사 + 대조군 400사) → ews_channel_score_monthly
5. 종합점수 재계산 (services/ews_channels.py 정본 - 결측 재정규화·동의 게이트)
6. 채널 선행성 백테스트 → ews_validation_metrics (scope_type='CHANNEL')

결정론: 모든 난수는 customer_id 해시 기반 - 재실행해도 같은 결과.
"""
import hashlib
import json
import os
import sqlite3
import sys
import uuid
from pathlib import Path

DB = Path(os.getenv("CLMS_DB_PATH") or Path(__file__).parent / "imbank_demo.db")
BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
from app.services.ews_channels import (   # noqa: E402
    score_card_sales, score_employment, score_b2b, DEFAULT_WEIGHTS,
)


def load_active_weights(con) -> dict:
    """rule_register 정본의 유효 가중치 (감사 A8 - 생성기도 정본을 쓴다)"""
    import json as _json
    row = con.execute("""SELECT params_json FROM rule_register
        WHERE rule_id LIKE 'RULE_EWS_WEIGHTS%' AND valid_to IS NULL
        ORDER BY valid_from DESC LIMIT 1""").fetchone()
    if row and row[0]:
        try:
            return _json.loads(row[0])
        except ValueError:
            pass
    return DEFAULT_WEIGHTS

MONTHS_24 = []          # 2024-08 .. 2026-07
for y in (2024, 2025, 2026):
    for m in range(1, 13):
        ym = f"{y:04d}-{m:02d}"
        if "2024-08" <= ym <= "2026-07":
            MONTHS_24.append(ym)
CUR = MONTHS_24[-1]     # 2026-07
ALERT = 55.0            # WATCH 경계 = 경보 임계

# 스토리 투어 앵커 - 종합점수 밴드(WARNING)를 유지해야 하는 고객
ANCHOR_TARGETS = {"CUST00339": 41.2}   # 투어 ② 정본 - 밴드(WARNING) 유지가 목적
ANCHORS = set(ANCHOR_TARGETS)


def h(cid: str, salt: str) -> float:
    """[0,1) 결정론 해시"""
    return int(hashlib.sha256(f"{cid}:{salt}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    global ACTIVE_WEIGHTS
    ACTIVE_WEIGHTS = load_active_weights(cur)

    customers = cur.execute("""
        SELECT customer_id, size_category, listing_status, industry_name,
               COALESCE(employee_count, 30) AS emp
        FROM customer
    """).fetchall()

    # ── 이벤트 기업: 워크아웃 + DPD90 (이벤트 월은 해시로 최근 6개월 분산) ──
    event_ids = {r[0] for r in cur.execute(
        "SELECT DISTINCT customer_id FROM workout_case")}
    event_ids |= {r[0] for r in cur.execute(
        "SELECT DISTINCT customer_id FROM facility WHERE dpd >= 90")}
    event_month = {cid: MONTHS_24[18 + int(h(cid, "evt") * 6)] for cid in event_ids}

    # 대조군 400사 (오경보율 측정 모집단)
    non_event = [r["customer_id"] for r in customers if r["customer_id"] not in event_ids]
    control = sorted(non_event, key=lambda c: h(c, "ctl"))[:400]
    panel = set(event_ids) | set(control)

    # ── 초기화 (멱등) ────────────────────────────────────────────────
    for t in ("ews_card_sales_monthly", "ews_employment_monthly",
              "ews_b2b_delinquency", "ews_channel_score_monthly",
              "ews_channel_consent"):
        cur.execute(f"DELETE FROM {t}")
    cur.execute("DELETE FROM ews_validation_metrics WHERE scope_type='CHANNEL'")

    # ── 동의 레지스트리 ──────────────────────────────────────────────
    def consent_mix(cid, salt, adopt_rate):
        r = h(cid, salt)
        if r >= adopt_rate:
            return None                       # 미동의
        r2 = h(cid, salt + "mix")
        if r2 < 0.05:
            return ("EXPIRED", "2026-06-30")
        if r2 < 0.07:
            return ("WITHDRAWN", None)
        if r2 < 0.12:
            return ("ACTIVE", "2026-09-10")   # 만료 임박 (D-30 배지 시연)
        return ("ACTIVE", "2027-12-31")

    card_eligible = {r["customer_id"] for r in customers
                     if r["size_category"] == "SOHO" or "유통" in (r["industry_name"] or "")}
    card_ok, emp_ok = set(), set()
    for r in customers:
        cid = r["customer_id"]
        if cid in card_eligible:
            mix = consent_mix(cid, "card", 0.70)
            if mix:
                cur.execute("""INSERT INTO ews_channel_consent
                    (consent_id, customer_id, channel, legal_basis, consent_date, expiry_date, status)
                    VALUES (?,?,?,?,?,?,?)""",
                    (f"CST_{uuid.uuid4().hex[:10].upper()}", cid, "CARD_SALES",
                     "신용정보법 §32 동의", "2025-01-15", mix[1], mix[0]))
                if mix[0] == "ACTIVE":
                    card_ok.add(cid)
        mix = consent_mix(cid, "emp", 0.60)
        if mix:
            cur.execute("""INSERT INTO ews_channel_consent
                (consent_id, customer_id, channel, legal_basis, consent_date, expiry_date, status)
                VALUES (?,?,?,?,?,?,?)""",
                (f"CST_{uuid.uuid4().hex[:10].upper()}", cid, "EMPLOYMENT",
                 "마이데이터·4대보험 동의", "2025-03-02", mix[1], mix[0]))
            if mix[0] == "ACTIVE":
                emp_ok.add(cid)

    # ── 원천 24개월 + 월별 채널점수 ─────────────────────────────────
    # 정합 원칙 (2026-08-22 감사 A6): 저장되는 MoM·YoY·3개월 증감은 전부
    # 실제 금액·인원 시계열에서 계산한다 - 원천에서 점수가 재현돼야 한다.
    def month_idx(ym):
        return MONTHS_24.index(ym)

    card_scores, emp_scores, b2b_scores = {}, {}, {}   # (cid, ym) -> score

    for r in customers:
        cid = r["customer_id"]
        is_event = cid in event_ids
        e_idx = month_idx(event_month[cid]) if is_event else None
        noise = (not is_event) and h(cid, "noise") < 0.05   # 오경보 주입 5%
        noise_idx = 6 + int(h(cid, "nidx") * 12) if noise else None

        # 카드매출: 실제 금액 시계열 → MoM·YoY·연속하락 실계산
        if cid in card_eligible:
            base = 8e7 + h(cid, "cbase") * 5e8
            amts, days_drops, ind_pcts = [], [], []
            for i, ym in enumerate(MONTHS_24):
                mult = 1.0 + (h(cid, "cs" + ym) - 0.5) * 0.08     # ±4% 노이즈
                days_drop = 0.0
                ind_pct = 30 + h(cid, "cpct" + ym) * 60
                if is_event and i >= e_idx - 9:
                    prog = min((i - (e_idx - 9)) / 9.0, 1.0)
                    mult *= (1 - 0.45 * prog)                     # 최대 -45%
                    days_drop = prog * 30
                    ind_pct = max(5, 25 - prog * 20)
                if noise and i == noise_idx:
                    mult *= 0.62                                   # 일시 급감 (오경보)
                    ind_pct = 8.0
                amts.append(base * mult)
                days_drops.append(days_drop)
                ind_pcts.append(ind_pct)
            streak = 0
            for i, ym in enumerate(MONTHS_24):
                mom = (amts[i] / amts[i - 1] - 1) * 100 if i >= 1 else None
                yoy = (amts[i] / amts[i - 12] - 1) * 100 if i >= 12 else None
                streak = streak + 1 if (mom is not None and mom < 0) else 0
                sc = score_card_sales(yoy, streak, days_drops[i], ind_pcts[i])
                card_scores[(cid, ym)] = sc
                cur.execute("""INSERT INTO ews_card_sales_monthly
                    (record_id, customer_id, month, card_sales_amount,
                     active_merchant_days, mom_change_pct, yoy_change_pct, industry_percentile)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (f"CS_{uuid.uuid4().hex[:10].upper()}", cid, ym, round(amts[i]),
                     int(26 * (1 - days_drops[i] / 100)),
                     round(mom, 1) if mom is not None else None,
                     round(yoy, 1) if yoy is not None else None,
                     round(ind_pcts[i], 1)))

        # 고용: 실제 인원 시계열 → 3개월 증감 실계산
        emp0 = max(int(r["emp"]), 5)
        cnts, arrears_list = [], []
        for i, ym in enumerate(MONTHS_24):
            mult = 1.0 + (h(cid, "em" + ym) - 0.5) * 0.04         # ±2% 노이즈
            arrears = 0
            if is_event and i >= e_idx - 5:
                prog = min((i - (e_idx - 5)) / 5.0, 1.0)
                mult *= (1 - 0.26 * prog)                          # 최대 -26%
                if i >= e_idx - 2:
                    arrears = 1
                if i >= e_idx - 1:
                    arrears = 2
            if noise and i == noise_idx:
                mult *= 0.78                                       # 일시 감원 (오경보)
                arrears = 1
            cnts.append(max(int(emp0 * mult), 1))
            arrears_list.append(arrears)
        for i, ym in enumerate(MONTHS_24):
            change_3m = cnts[i] - cnts[i - 3] if i >= 3 else 0
            base_3m = cnts[i - 3] if i >= 3 else cnts[0]
            chg_pct = change_3m / base_3m * 100 if base_3m else 0.0
            sc = score_employment(chg_pct, arrears_list[i])
            emp_scores[(cid, ym)] = sc
            cur.execute("""INSERT INTO ews_employment_monthly
                (record_id, customer_id, month, insured_count, insured_change_3m,
                 premium_arrears_months)
                VALUES (?,?,?,?,?,?)""",
                (f"EM_{uuid.uuid4().hex[:10].upper()}", cid, ym, cnts[i],
                 change_3m, arrears_list[i]))

        # 상거래연체: 미해소 이벤트의 건수·경과일·금액을 월별 누적 (설계 §3)
        open_by_month = {ym: (0, 0, False, 0.0) for ym in MONTHS_24}
        events = []
        if is_event:
            events.append((e_idx - 4, "PAYMENT_DELAY", 35, 1))
            events.append((e_idx - 3, "PAYMENT_DELAY", 60, 1))
            events.append((e_idx - 2, "NOTE_EXTENSION", 65, 1))
            if h(cid, "b2bdef") < 0.30:
                events.append((e_idx - 1, "COMMERCIAL_DEFAULT", 90, 1))
        elif noise:
            events.append((noise_idx, "PAYMENT_DELAY", 65, 2))
        for idx, etype, odays, ncp in events:
            if not 0 <= idx < len(MONTHS_24):
                continue
            ym = MONTHS_24[idx]
            amt = 2e8 + h(cid, "b2bamt" + str(idx)) * 2e9
            resolved = None if etype == "COMMERCIAL_DEFAULT" or idx >= len(MONTHS_24) - 3 \
                else MONTHS_24[idx + 2] + "-15"
            cur.execute("""INSERT INTO ews_b2b_delinquency
                (event_id, customer_id, event_date, counterparty_count,
                 overdue_amount, overdue_days, event_type, resolved_date)
                VALUES (?,?,?,?,?,?,?,?)""",
                (f"B2B_{uuid.uuid4().hex[:10].upper()}", cid, ym + "-10", ncp,
                 round(amt), odays, etype, resolved))
            until = len(MONTHS_24) if resolved is None else min(idx + 2, len(MONTHS_24))
            for j in range(idx, until):
                o, d, df, a = open_by_month[MONTHS_24[j]]
                open_by_month[MONTHS_24[j]] = (o + ncp, max(d, odays),
                                               df or etype == "COMMERCIAL_DEFAULT",
                                               a + amt / 1e8)
        for ym in MONTHS_24:
            o, d, df, a = open_by_month[ym]
            b2b_scores[(cid, ym)] = score_b2b(o, d, df, a)

    # ── 부실 진행 기업의 현재 레거시 채널점수 정합화 ────────────────
    # 워크아웃·DPD90 기업이 거래행태·뉴스·공급망에서 건전 점수를 유지하던
    # 구세대 데이터 모순을 해소한다 (부실 기업은 현재도 부실 신호를 낸다).
    for cid in event_ids:
        cur.execute("""UPDATE ews_composite_score
            SET transaction_score = MIN(transaction_score, ?),
                news_score        = MIN(news_score, ?),
                supply_chain_score = MIN(supply_chain_score, ?)
            WHERE customer_id = ?
              AND score_date = (SELECT MAX(score_date) FROM ews_composite_score)""",
            (22 + h(cid, "tcap") * 18, 30 + h(cid, "ncap") * 20,
             35 + h(cid, "scap") * 20, cid))
        # 중증 부실 코호트(40%): 공적·재무 신호도 악화 (세금체납·자본잠식) → CRITICAL
        if h(cid, "sev") < 0.40:
            cur.execute("""UPDATE ews_composite_score
                SET public_registry_score = MIN(public_registry_score, ?),
                    financial_score       = MIN(financial_score, ?)
                WHERE customer_id = ?
                  AND score_date = (SELECT MAX(score_date) FROM ews_composite_score)""",
                (38 + h(cid, "pcap") * 15, 32 + h(cid, "fcap") * 15, cid))

    # ── 앵커 보정: 투어 기업은 기존 종합점수(41.2 WARNING)를 정확히 유지 ──
    # 신규 채널 점수 x 를 선형 역산: composite = (L + W·x)/(Lw + W) = target
    # (L = 기존 채널 가중합, Lw = 기존 채널 가중치합, W = 신규 채널 가중치합)
    for cid in ANCHORS:
        row = cur.execute("""SELECT s.composite_score, c.size_category, c.listing_status,
                s.transaction_score, s.public_registry_score, s.market_score,
                s.news_score, s.supply_chain_score, s.financial_score
            FROM ews_composite_score s JOIN customer c ON s.customer_id = c.customer_id
            WHERE s.customer_id=? ORDER BY s.score_date DESC LIMIT 1""", (cid,)).fetchone()
        if not row:
            continue
        target = ANCHOR_TARGETS.get(cid, float(row[0]))
        seg = "SOHO" if row[1] == "SOHO" else (
            "LISTED" if (row[2] or "") in ("KOSPI", "KOSDAQ", "LISTED") else "UNLISTED")
        w = ACTIVE_WEIGHTS[seg]
        legacy = {"transaction": row[3], "public": row[4], "market": row[5],
                  "news": row[6], "supply": row[7], "financial": row[8]}
        L = sum(w[ch] * float(v) for ch, v in legacy.items() if v is not None and w.get(ch, 0) > 0)
        Lw = sum(w[ch] for ch, v in legacy.items() if v is not None and w.get(ch, 0) > 0)
        stores = {"card_sales": card_scores, "employment": emp_scores, "b2b_delinq": b2b_scores}
        # 반영 가능한 신규 채널: 데이터 존재 + (동의 채널이면 동의 유효)
        active_new = []
        for ch, store in stores.items():
            if (cid, CUR) not in store:
                continue
            if ch == "card_sales" and cid not in card_ok:
                continue
            if ch == "employment" and cid not in emp_ok:
                continue
            active_new.append(ch)
        W = sum(w[ch] for ch in active_new)
        if W > 0:
            x = max(0.0, min(100.0, (target * (Lw + W) - L) / W))
            for ch in active_new:
                stores[ch][(cid, CUR)] = x

    # ── 당월 채널점수 → ews_composite_score 컬럼 ─────────────────────
    for r in customers:
        cid = r["customer_id"]
        cur.execute("""UPDATE ews_composite_score
            SET card_sales_score = ?, employment_score = ?, b2b_delinq_score = ?
            WHERE customer_id = ?
              AND score_date = (SELECT MAX(score_date) FROM ews_composite_score)""",
            (card_scores.get((cid, CUR)), emp_scores.get((cid, CUR)),
             b2b_scores.get((cid, CUR)), cid))

    # ── 월별 점수 패널 (이벤트 + 대조군) ─────────────────────────────
    def legacy_monthly(cid):
        """기존 채널 월별 점수 - 원천 테이블에서 룰 기반 산출 (12개월)"""
        out = {}
        for row in cur.execute("""SELECT reference_month, limit_utilization,
                payment_delay_days, deposit_outflow_rate, overdraft_count
                FROM ews_transaction_behavior WHERE customer_id=?""", (cid,)):
            s = 100 - max(0.0, (row[1] or 0) - 0.70) * 160 \
                - max(0, (row[2] or 0) - 5) * 3 \
                - max(0.0, (row[3] or 0) - 0.25) * 120 - (row[4] or 0) * 15
            out.setdefault("transaction", {})[row[0]] = max(s, 0)
        for row in cur.execute("""SELECT reference_month, negative_ratio, avg_sentiment
                FROM ews_news_sentiment_monthly WHERE customer_id=?""", (cid,)):
            s = 100 - max(0.0, (row[1] or 0) - 0.60) * 130 - abs(min(row[2] or 0, 0)) * 15
            out.setdefault("news", {})[row[0]] = max(s, 0)
        for row in cur.execute("""SELECT reference_month, implied_pd, stock_price_change
                FROM ews_market_signal WHERE customer_id=?""", (cid,)):
            s = 100 - max(0.0, (row[1] or 0) - 0.38) * 280 - max(0.0, -(row[2] or 0)) * 1.2
            out.setdefault("market", {})[row[0]] = max(s, 0)
        for row in cur.execute("""SELECT reference_month,
                AVG(chain_default_probability),
                SUM(CASE WHEN payment_status != 'NORMAL' THEN 1 ELSE 0 END)
                FROM ews_supply_chain_temporal WHERE customer_id=? GROUP BY reference_month""", (cid,)):
            s = 100 - max(0.0, (row[1] or 0) - 0.20) * 300 - (row[2] or 0) * 6
            out.setdefault("supply", {})[row[0]] = max(s, 0)
        # 공적정보: 이벤트 후 6개월 감쇠 감점
        sev_pen = {"LOW": 12, "MEDIUM": 25, "HIGH": 40, "CRITICAL": 55}
        evs = cur.execute("""SELECT event_date, severity FROM ews_public_registry
            WHERE customer_id=?""", (cid,)).fetchall()
        for ym in MONTHS_24[-12:]:
            s = 100.0
            for ed, sev in evs:
                em = str(ed)[:7]
                if em <= ym:
                    gap = (int(ym[:4]) - int(em[:4])) * 12 + int(ym[5:7]) - int(em[5:7])
                    if gap <= 6:
                        s -= sev_pen.get(sev, 15) * (1 - gap / 8)
            out.setdefault("public", {})[ym] = max(s, 0)
        return out

    rows = []
    for cid in panel:
        for ym in MONTHS_24:
            for ch, store in (("card_sales", card_scores), ("employment", emp_scores),
                              ("b2b_delinq", b2b_scores)):
                if (cid, ym) in store:
                    rows.append((cid, ym, ch, round(store[(cid, ym)], 1)))
        for ch, series in legacy_monthly(cid).items():
            for ym, sc in series.items():
                rows.append((cid, ym, ch, round(sc, 1)))
    cur.executemany("""INSERT OR REPLACE INTO ews_channel_score_monthly
        (customer_id, month, channel, score) VALUES (?,?,?,?)""", rows)

    # ── 채널 선행성 백테스트 → ews_validation_metrics ────────────────
    CHANNELS = ["card_sales", "employment", "b2b_delinq",
                "transaction", "public", "market", "news", "supply"]
    panel_scores = {}
    for cid, ym, ch, sc in cur.execute(
            "SELECT customer_id, month, channel, score FROM ews_channel_score_monthly"):
        panel_scores.setdefault((cid, ch), []).append((ym, sc))

    for ch in CHANNELS:
        leads, detected, n_events_covered = [], 0, 0
        for cid in event_ids:
            series = sorted(panel_scores.get((cid, ch), []))
            if not series:
                continue
            n_events_covered += 1
            e_ym = event_month[cid]
            alert_ym = next((ym for ym, sc in series if ym < e_ym and sc < ALERT), None)
            if alert_ym:
                detected += 1
                lead = (int(e_ym[:4]) - int(alert_ym[:4])) * 12 \
                    + int(e_ym[5:7]) - int(alert_ym[5:7])
                leads.append(lead)
        false_alarms, ctl_covered = 0, 0
        for cid in control:
            series = panel_scores.get((cid, ch), [])
            if not series:
                continue
            ctl_covered += 1
            if any(sc < ALERT for _, sc in series):
                false_alarms += 1
        if n_events_covered == 0:
            continue
        leads.sort()
        med = leads[len(leads) // 2] if leads else None
        avg = sum(leads) / len(leads) if leads else None
        cur.execute("""INSERT INTO ews_validation_metrics
            (scope_type, scope_value, n_defaults, n_detected, detection_rate_pct,
             avg_lead_months, median_lead_months, pct_alert_before_3m,
             pct_alert_before_6m, pct_alert_before_12m, alert_threshold_score,
             computed_ym, source, false_alarm_rate_pct)
            VALUES ('CHANNEL',?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ch, n_events_covered, detected,
             round(detected / n_events_covered * 100, 1),
             round(avg, 1) if avg else None, med,
             round(sum(1 for x in leads if x >= 3) / n_events_covered * 100, 1),
             round(sum(1 for x in leads if x >= 6) / n_events_covered * 100, 1),
             round(sum(1 for x in leads if x >= 12) / n_events_covered * 100, 1),
             ALERT, CUR, "channel_backtest_v1",
             round(false_alarms / ctl_covered * 100, 1) if ctl_covered else None))

    con.commit()

    # ── 종합점수 재계산 (백엔드 정본 - 동의 게이트·결측 재정규화) ────
    from app.core import database as _dbmod
    from app.services.ews_channels import recompute_composite
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    eng = create_engine(f"sqlite:///{DB}")
    S = sessionmaker(bind=eng)()
    stats = recompute_composite(S)
    S.commit()

    # 앵커 밴드 확인
    for cid in ANCHORS:
        row = S.execute(__import__("sqlalchemy").text(
            """SELECT composite_score, ews_grade FROM ews_composite_score
               WHERE customer_id=:c ORDER BY score_date DESC LIMIT 1"""), {"c": cid}).fetchone()
        print(f"  앵커 {cid}: composite={row[0]} grade={row[1]}")
    S.close()

    print(f"완료: 이벤트 {len(event_ids)}사 · 대조군 {len(control)}사 · "
          f"카드동의 {len(card_ok)} · 고용동의 {len(emp_ok)} · 재계산 {stats}")


if __name__ == "__main__":
    main()
