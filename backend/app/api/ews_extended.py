"""
EWS 확장 채널 API (docs/EWS_8CHANNEL_DESIGN_2026-08-21.md Phase 2·3)
=====================================================================
카드매출·고용·상거래연체 3채널 대시보드 + 채널 선행성 검증 + 가중치 거버넌스.

가중치 변경은 부서장 이상 승인 + 감사기록(critical)으로만 발효되고,
발효 즉시 종합점수가 정본(services/ews_channels.py)으로 재계산된다.
"""
import hashlib
import json
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..core.auth import get_current_user, User
from ..core.audit import record_audit
from ..services.ews_channels import (
    load_weights_meta, publish_weights, recompute_composite, CHANNEL_COLUMNS,
)

router = APIRouter(prefix="/api/ews-advanced", tags=["EWS Extended Channels"])

CHANNEL_LABELS = {
    "card_sales": "카드매출", "employment": "고용", "b2b_delinq": "상거래연체",
    "transaction": "거래행태", "public": "공적정보", "market": "시장신호",
    "news": "뉴스감성", "supply": "공급망", "financial": "재무",
}


@router.get("/card-employment/dashboard")
def get_card_employment_dashboard(db: Session = Depends(get_db)):
    """카드매출·고용 채널 대시보드 (동의 유효 기업만 점수 반영)"""
    card = db.execute(text("""
        SELECT cs.customer_id, c.customer_name, c.industry_name, c.region,
               cs.yoy_change_pct, cs.industry_percentile, cs.active_merchant_days,
               ecs.card_sales_score
        FROM ews_card_sales_monthly cs
        JOIN customer c ON cs.customer_id = c.customer_id
        JOIN ews_channel_consent cc ON cc.customer_id = cs.customer_id
             AND cc.channel = 'CARD_SALES' AND cc.status = 'ACTIVE'
             AND (cc.expiry_date IS NULL OR cc.expiry_date >= date('now'))
        LEFT JOIN ews_composite_score ecs ON ecs.customer_id = cs.customer_id
             AND ecs.score_date = (SELECT MAX(score_date) FROM ews_composite_score)
        WHERE cs.month = (SELECT MAX(month) FROM ews_card_sales_monthly)
        ORDER BY cs.yoy_change_pct ASC LIMIT 15
    """)).fetchall()

    emp = db.execute(text("""
        SELECT em.customer_id, c.customer_name, c.industry_name,
               em.insured_count, em.insured_change_3m, em.premium_arrears_months,
               ecs.employment_score
        FROM ews_employment_monthly em
        JOIN customer c ON em.customer_id = c.customer_id
        JOIN ews_channel_consent cc ON cc.customer_id = em.customer_id
             AND cc.channel = 'EMPLOYMENT' AND cc.status = 'ACTIVE'
             AND (cc.expiry_date IS NULL OR cc.expiry_date >= date('now'))
        LEFT JOIN ews_composite_score ecs ON ecs.customer_id = em.customer_id
             AND ecs.score_date = (SELECT MAX(score_date) FROM ews_composite_score)
        WHERE em.month = (SELECT MAX(month) FROM ews_employment_monthly)
          AND (em.insured_change_3m < 0 OR em.premium_arrears_months > 0)
        ORDER BY em.premium_arrears_months DESC, em.insured_change_3m ASC LIMIT 15
    """)).fetchall()

    # 경보 카운트도 동의 유효 모집단으로 센다 (감사 A3 - 화면 고지와 정합)
    counts = db.execute(text("""
        SELECT
          (SELECT COUNT(*) FROM ews_channel_consent WHERE channel='CARD_SALES' AND status='ACTIVE'
             AND (expiry_date IS NULL OR expiry_date >= date('now'))),
          (SELECT COUNT(*) FROM ews_channel_consent WHERE channel='EMPLOYMENT' AND status='ACTIVE'
             AND (expiry_date IS NULL OR expiry_date >= date('now'))),
          (SELECT COUNT(*) FROM ews_composite_score s
           JOIN ews_channel_consent cc ON cc.customer_id = s.customer_id
             AND cc.channel='CARD_SALES' AND cc.status='ACTIVE'
             AND (cc.expiry_date IS NULL OR cc.expiry_date >= date('now'))
           WHERE s.score_date=(SELECT MAX(score_date) FROM ews_composite_score)
             AND s.card_sales_score < 55),
          (SELECT COUNT(*) FROM ews_composite_score s
           JOIN ews_channel_consent cc ON cc.customer_id = s.customer_id
             AND cc.channel='EMPLOYMENT' AND cc.status='ACTIVE'
             AND (cc.expiry_date IS NULL OR cc.expiry_date >= date('now'))
           WHERE s.score_date=(SELECT MAX(score_date) FROM ews_composite_score)
             AND s.employment_score < 55)
    """)).fetchone()

    return {
        "summary": {"card_consented": counts[0], "emp_consented": counts[1],
                    "card_alerts": counts[2], "emp_alerts": counts[3]},
        "card_decliners": [
            {"customer_id": r[0], "customer_name": r[1], "industry": r[2],
             "region": r[3], "yoy_pct": r[4], "industry_percentile": r[5],
             "active_days": r[6], "score": r[7]}
            for r in card
        ],
        "employment_risks": [
            {"customer_id": r[0], "customer_name": r[1], "industry": r[2],
             "insured_count": r[3], "insured_change_3m": r[4],
             "arrears_months": r[5], "score": r[6]}
            for r in emp
        ],
        "note": "동의(신용정보법 §32) 유효 기업만 점수에 반영 - 만료·철회는 자동 결측 전환",
    }


@router.get("/b2b-delinquency/dashboard")
def get_b2b_dashboard(db: Session = Depends(get_db)):
    """상거래연체 대시보드 - 은행 연체와의 교차가 핵심 (선행 포착 구간)"""
    rows = db.execute(text("""
        SELECT b.customer_id, c.customer_name, c.industry_name,
               b.event_date, b.event_type, b.overdue_days, b.overdue_amount,
               b.counterparty_count, b.resolved_date,
               (SELECT MAX(f.dpd) FROM facility f WHERE f.customer_id = b.customer_id) AS bank_dpd,
               ecs.b2b_delinq_score
        FROM ews_b2b_delinquency b
        JOIN customer c ON b.customer_id = c.customer_id
        LEFT JOIN ews_composite_score ecs ON ecs.customer_id = b.customer_id
             AND ecs.score_date = (SELECT MAX(score_date) FROM ews_composite_score)
        WHERE b.resolved_date IS NULL
        ORDER BY CASE b.event_type WHEN 'COMMERCIAL_DEFAULT' THEN 0 ELSE 1 END,
                 b.overdue_days DESC
        LIMIT 30
    """)).fetchall()

    # 총계는 절단(LIMIT) 전 기준으로 센다 (감사 A7). 선행 판정은 현재 DPD 가
    # 아니라 '최초 은행연체일이 상거래연체 발생일보다 늦거나 없는가'로 판단.
    totals = db.execute(text("""
        SELECT COUNT(*),
               SUM(CASE WHEN fb.first_dt IS NULL OR fb.first_dt > b.event_date
                        THEN 1 ELSE 0 END)
        FROM ews_b2b_delinquency b
        LEFT JOIN (SELECT customer_id, MIN(first_delinquency_date) AS first_dt
                   FROM facility WHERE first_delinquency_date IS NOT NULL
                   GROUP BY customer_id) fb ON fb.customer_id = b.customer_id
        WHERE b.resolved_date IS NULL
    """)).fetchone()
    first_bank = {r[0]: r[1] for r in db.execute(text("""
        SELECT customer_id, MIN(first_delinquency_date) FROM facility
        WHERE first_delinquency_date IS NOT NULL GROUP BY customer_id
    """)).fetchall()}

    items = []
    for r in rows:
        bank_dpd = r[9] or 0
        fb = first_bank.get(r[0])
        is_leading = fb is None or str(fb) > str(r[3])
        items.append({
            "customer_id": r[0], "customer_name": r[1], "industry": r[2],
            "event_date": str(r[3]), "event_type": r[4],
            "overdue_days": r[5], "overdue_amount_eok": round(float(r[6] or 0) / 1e8, 1),
            "counterparties": r[7], "bank_dpd": bank_dpd,
            "leading_signal": is_leading, "score": r[10],
        })
    return {
        "open_events": items,
        "summary": {
            "total_open": totals[0] or 0,
            "leading_signals": totals[1] or 0,
            "listed": len(items),
            "note": "선행 = 상거래연체 발생일이 최초 은행연체일보다 빠르거나 은행연체 없음 - 이 채널이 먼저 본 기업",
        },
    }


@router.get("/channel-validation")
def get_channel_validation(db: Session = Depends(get_db)):
    """채널 선행성 백테스트 지표 - 가중치는 주장이 아니라 백테스트로 정한다.

    정직성 원칙 (2026-08-22 감사 반영):
    - '오경보율'이 아니라 **대조군 경보율** (이벤트 미발생 대조군 중 경보가
      난 기업 비율)로 표기한다 - 12개월 성숙·우측검열을 적용한 설계상
      오경보율과 다른 근사 지표이기 때문.
    - 탐지율에 Wilson 95% 신뢰구간과 표본 충분성 플래그를 병기한다.
    - 합성 백테스트(생성 규칙의 재확인)임을 응답에 명시한다.
    """
    rows = db.execute(text("""
        SELECT scope_value, n_defaults, n_detected, detection_rate_pct,
               avg_lead_months, median_lead_months,
               pct_alert_before_3m, pct_alert_before_6m,
               false_alarm_rate_pct, computed_ym, source
        FROM ews_validation_metrics
        WHERE scope_type = 'CHANNEL'
        ORDER BY median_lead_months DESC, detection_rate_pct DESC
    """)).fetchall()

    # 이벤트 계층 분해 (T2 중대 연체·T3 건전성 강등) - 데이터 충분성 개선 ①
    tier_rows = db.execute(text("""
        SELECT scope_value, n_defaults, n_detected, detection_rate_pct,
               median_lead_months, false_alarm_rate_pct
        FROM ews_validation_metrics WHERE scope_type = 'CHANNEL_TIER'
    """)).fetchall()
    tiers_by_channel: dict = {}
    for r in tier_rows:
        ch, tier = r[0].rsplit(":", 1)
        tiers_by_channel.setdefault(ch, {})[tier] = {
            "n_events": r[1], "n_detected": r[2], "detection_rate": r[3],
            "median_lead_months": r[4], "control_alert_rate": r[5],
        }

    # 채널별 대조군 크기 (월별 점수 패널에서 실측 - 이벤트 기업 제외)
    controls = {r[0]: r[1] for r in db.execute(text("""
        SELECT channel, COUNT(DISTINCT customer_id) FROM ews_channel_score_monthly
        WHERE customer_id NOT IN (SELECT customer_id FROM workout_case
                                  UNION SELECT customer_id FROM facility WHERE dpd >= 90)
        GROUP BY channel
    """)).fetchall()}

    def wilson(k: int, n: int) -> tuple[float, float] | None:
        if not n:
            return None
        z = 1.96
        ph = k / n
        denom = 1 + z * z / n
        center = (ph + z * z / (2 * n)) / denom
        half = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / denom
        return round((center - half) * 100, 1), round((center + half) * 100, 1)

    channels = []
    synthetic = False
    for r in rows:
        if (r[10] or "").startswith("channel_backtest"):
            synthetic = True
        ci = wilson(r[2] or 0, r[1] or 0)
        channels.append({
            "channel": r[0], "label": CHANNEL_LABELS.get(r[0], r[0]),
            "n_events": r[1], "n_detected": r[2], "detection_rate": r[3],
            "detection_ci95": ci,
            "sample_adequate": (r[1] or 0) >= 30,
            "n_controls": controls.get(r[0]),
            "avg_lead_months": r[4], "median_lead_months": r[5],
            "pct_before_3m": r[6], "pct_before_6m": r[7],
            "control_alert_rate": r[8], "computed_ym": r[9],
            "tiers": tiers_by_channel.get(r[0], {}),
        })

    return {
        "methodology": {
            "events": "워크아웃 이관·DPD90 기업 (91사) - 채널 점수가 경보 임계(55) 아래로 최초 하락한 시점과 이벤트 시점의 차 = 리드타임",
            "control_alert": "대조군 400사 중 경보가 난 기업 비율 (설계상 '경보 후 12개월 무이벤트' 오경보율의 근사 - 성숙·검열 미적용)",
            "window": "신규 채널 24개월 · 기존 채널 12개월 (원천 이력 한도)",
            "consent_note": "백테스트는 데이터 보유 전체 기준(동의 게이트 미적용) - 운영 반영 모집단과 다르다",
        },
        "tier_definitions": {
            "T1": "부도·워크아웃 (DPD90 포함) - 91사",
            "T2": "중대 연체 (DPD 60~89) - 13사",
            "T3": "건전성 강등 (요주의 이하, 연체 60일 미만) - 20사",
        },
        "roadmap": [
            "① 데모: 이벤트 3계층 + 표본·CI 표시 (완료) - 합성 한계는 고지 유지",
            "② 파일럿: CB 과거 이력 구입 → 자행 부도와 매칭한 후향적 백테스트 (수천 이벤트)",
            "③ 파일럿: 신규 채널 12~24개월 그림자 운영 (점수 미반영) 후 가중치 편입",
            "④ 운영: 검증 데이터마트(3시점·검열·성숙 코호트) + 연 1회 독립 검증 편입",
        ],
        "synthetic": synthetic,
        "synthetic_notice": ("합성 데모 백테스트 - 생성기가 심은 악화 패턴을 같은 임계로 채점한 "
                             "생성 규칙의 재확인이며, 실데이터 성능 검증이 아니다. "
                             "실데이터 검증 전 가중치 보정의 단독 근거로 쓸 수 없다") if synthetic else None,
        "channels": channels,
    }


def _quality(metrics: dict) -> dict:
    """채널 품질 점수 - 탐지율 × 리드타임 보너스 × (1-대조군 경보율)"""
    q = {}
    for ch, m in metrics.items():
        det = (m["detection_rate"] or 0) / 100
        lead = (m["median_lead_months"] or 0)
        fa = (m["control_alert_rate"] or 0) / 100
        q[ch] = det * (1 + lead / 12) * (1 - fa)
    return q


def _bounded_proposal(current: dict, quality: dict, max_shift: float = 0.05) -> dict:
    """검증 기반 가중치 제안 (2026-08-22 감사 A2 재작성).

    제약 3개를 동시에 만족시킨다:
      ① 채널별 최종 이동폭 ≤ ±max_shift  ② 세그먼트 합계 = 1.000
      ③ 지표 없는 채널(재무 등)·가중치 0 채널은 현행 고정
    방법: 반복 투영 (조정→클램프→합계 보정을 수렴까지) + 최대잔여 반올림.
    """
    proposal = {}
    for seg, w in current.items():
        adjustable = {ch: wt for ch, wt in w.items() if wt > 0 and ch in quality}
        fixed = {ch: wt for ch, wt in w.items() if ch not in adjustable}
        if not adjustable:
            proposal[seg] = dict(w)
            continue
        avg_q = sum(quality[ch] for ch in adjustable) / len(adjustable)
        target = {ch: wt * (1.0 + (quality[ch] - avg_q)) for ch, wt in adjustable.items()}
        cur_mass = sum(adjustable.values())
        vals = dict(target)
        for _ in range(20):
            # 클램프 (±max_shift)
            vals = {ch: min(max(v, adjustable[ch] - max_shift), adjustable[ch] + max_shift)
                    for ch, v in vals.items()}
            gap = cur_mass - sum(vals.values())
            if abs(gap) < 1e-9:
                break
            # 여유가 있는 채널에 잔여를 비례 배분
            room = {ch: (adjustable[ch] + max_shift - v) if gap > 0
                    else (v - (adjustable[ch] - max_shift))
                    for ch, v in vals.items()}
            total_room = sum(room.values())
            if total_room <= 1e-12:
                break
            vals = {ch: v + gap * (room[ch] / total_room) for ch, v in vals.items()}
        # 0.1%p 단위 최대잔여 반올림으로 합계를 정확히 맞춘다
        scaled = {ch: v * 1000 for ch, v in vals.items()}
        floors = {ch: math.floor(v) for ch, v in scaled.items()}
        remain = round(cur_mass * 1000) - sum(floors.values())
        order = sorted(scaled, key=lambda c: scaled[c] - floors[c], reverse=True)
        for ch in order[:max(remain, 0)]:
            floors[ch] += 1
        seg_prop = {ch: floors[ch] / 1000 for ch in floors}
        seg_prop.update({ch: wt for ch, wt in fixed.items()})
        proposal[seg] = seg_prop
    return proposal


def _proposal_bundle(db: Session) -> dict:
    """현행·제안·해시를 한 번에 - 조회와 승인이 같은 근거를 쓴다 (감사 A5)"""
    current, rule_id, source = load_weights_meta(db)
    metrics = {r[0]: {"detection_rate": r[1], "median_lead_months": r[2],
                      "control_alert_rate": r[3]}
               for r in db.execute(text("""
                   SELECT scope_value, detection_rate_pct, median_lead_months,
                          false_alarm_rate_pct
                   FROM ews_validation_metrics WHERE scope_type='CHANNEL'
               """)).fetchall()}
    computed_ym = db.execute(text("""
        SELECT MAX(computed_ym) FROM ews_validation_metrics WHERE scope_type='CHANNEL'
    """)).scalar()
    synthetic = bool(db.execute(text("""
        SELECT 1 FROM ews_validation_metrics
        WHERE scope_type='CHANNEL' AND source LIKE 'channel_backtest%' LIMIT 1
    """)).fetchone())
    quality = _quality(metrics)
    proposal = _bounded_proposal(current, quality)
    payload = json.dumps({"base": rule_id, "ym": computed_ym, "proposal": proposal},
                         ensure_ascii=False, sort_keys=True)
    return {
        "current": current, "proposal": proposal, "quality": quality,
        "base_rule_id": rule_id, "weights_source": source,
        "computed_ym": computed_ym, "synthetic": synthetic,
        "proposal_hash": hashlib.sha256(payload.encode()).hexdigest()[:16],
    }


@router.get("/weight-proposal")
def get_weight_proposal(db: Session = Depends(get_db)):
    """현행 가중치 vs 백테스트 기반 제안 (±5%p 점진 조정, 합계 1 보장)"""
    b = _proposal_bundle(db)
    rule = db.execute(text("""
        SELECT version, valid_from FROM rule_register
        WHERE rule_id LIKE 'RULE_EWS_WEIGHTS%' AND valid_to IS NULL
        ORDER BY valid_from DESC LIMIT 1
    """)).fetchone()
    return {
        "current": b["current"],
        "proposal": b["proposal"],
        "quality": {ch: round(v, 3) for ch, v in b["quality"].items()},
        "current_version": {"version": rule[0], "valid_from": str(rule[1])} if rule else None,
        "base_rule_id": b["base_rule_id"],
        "weights_source": b["weights_source"],
        "proposal_hash": b["proposal_hash"],
        "synthetic": b["synthetic"],
        "governance": "발효는 부서장 이상 승인 + 감사기록 - 승인 즉시 전 고객 종합점수 재계산",
        "bound_note": "채널당 이동폭 ±5%p·세그먼트 합계 100% 보장 · 지표 없는 채널(재무)은 현행 고정",
    }


@router.post("/weight-proposal/approve")
def approve_weight_proposal(
    proposal_hash: str = Query(..., description="조회한 제안의 해시 - 불일치 시 409"),
    reason: str = Query(..., min_length=5),
    synthetic_ack: bool = Query(False, description="합성 백테스트 근거임을 승인자가 확인"),
    version_label: str = Query("백테스트 재조정"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """가중치 제안 발효 - 부서장 이상 + 제안 해시 결박 + 감사 critical.

    승인자는 화면에서 본 제안 그대로만 발효할 수 있다 (감사 A5 - TOCTOU 차단).
    합성 백테스트가 근거인 동안은 synthetic_ack 확인 없이 발효할 수 없다.
    """
    if current_user.approval_level not in ("DEPT_HEAD", "EXECUTIVE", "COMMITTEE"):
        raise HTTPException(403, "EWS 가중치 변경은 부서장 이상만 승인할 수 있습니다")

    b = _proposal_bundle(db)
    if b["proposal_hash"] != proposal_hash:
        raise HTTPException(409, "제안이 조회 시점과 달라졌습니다 - 화면을 새로고침해 다시 검토하세요")
    if b["synthetic"] and not synthetic_ack:
        raise HTTPException(422, "합성 데모 백테스트가 근거입니다 - 확인(synthetic_ack) 없이 발효할 수 없습니다")

    rule_id, version = publish_weights(db, b["proposal"], version_label, current_user.name)
    stats = recompute_composite(db, weights=b["proposal"], applied_rule_id=rule_id)

    record_audit(db, "EWS_WEIGHTS_PUBLISH", "rule_register", rule_id,
                 before={"weights": b["current"], "base_rule_id": b["base_rule_id"]},
                 after={"weights": b["proposal"], "version": version,
                        "reason": reason, "proposal_hash": proposal_hash,
                        "synthetic_ack": b["synthetic"] and synthetic_ack,
                        "approver_name": current_user.name,
                        "approver_level": current_user.approval_level,
                        "recomputed": stats["updated"]},
                 user_id=current_user.user_id, user_dept=current_user.dept,
                 critical=True)
    db.commit()
    return {"rule_id": rule_id, "version": version,
            "approved_by": current_user.name,
            "recomputed_customers": stats["updated"]}


@router.get("/consent/summary")
def get_consent_summary(db: Session = Depends(get_db)):
    """채널 동의 현황 - 만료 임박(D-30)은 데이터 공백 예고"""
    rows = db.execute(text("""
        SELECT channel, status, COUNT(*) FROM ews_channel_consent
        GROUP BY channel, status
    """)).fetchall()
    expiring = db.execute(text("""
        SELECT cc.customer_id, c.customer_name, cc.channel, cc.expiry_date
        FROM ews_channel_consent cc
        JOIN customer c ON cc.customer_id = c.customer_id
        WHERE cc.status = 'ACTIVE'
          AND cc.expiry_date BETWEEN date('now') AND date('now', '+30 days')
        ORDER BY cc.expiry_date LIMIT 20
    """)).fetchall()
    by_channel: dict = {}
    for ch, st, n in rows:
        by_channel.setdefault(ch, {})[st] = n
    return {
        "by_channel": by_channel,
        "expiring_30d": [
            {"customer_id": r[0], "customer_name": r[1],
             "channel": r[2], "expiry_date": str(r[3])}
            for r in expiring
        ],
        "note": "만료·철회 채널은 종합점수에서 자동 결측 전환 (channel_coverage 에 사유 기록)",
    }
