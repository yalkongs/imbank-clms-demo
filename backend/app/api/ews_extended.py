"""
EWS 확장 채널 API (docs/EWS_8CHANNEL_DESIGN_2026-08-21.md Phase 2·3)
=====================================================================
카드매출·고용·상거래연체 3채널 대시보드 + 채널 선행성 검증 + 가중치 거버넌스.

가중치 변경은 부서장 이상 승인 + 감사기록(critical)으로만 발효되고,
발효 즉시 종합점수가 정본(services/ews_channels.py)으로 재계산된다.
"""
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..core.auth import get_current_user, User
from ..core.audit import record_audit
from ..services.ews_channels import (
    load_weights, publish_weights, recompute_composite, CHANNEL_COLUMNS,
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
        LEFT JOIN ews_composite_score ecs ON ecs.customer_id = em.customer_id
             AND ecs.score_date = (SELECT MAX(score_date) FROM ews_composite_score)
        WHERE em.month = (SELECT MAX(month) FROM ews_employment_monthly)
          AND (em.insured_change_3m < 0 OR em.premium_arrears_months > 0)
        ORDER BY em.premium_arrears_months DESC, em.insured_change_3m ASC LIMIT 15
    """)).fetchall()

    counts = db.execute(text("""
        SELECT
          (SELECT COUNT(*) FROM ews_channel_consent WHERE channel='CARD_SALES' AND status='ACTIVE'),
          (SELECT COUNT(*) FROM ews_channel_consent WHERE channel='EMPLOYMENT' AND status='ACTIVE'),
          (SELECT COUNT(*) FROM ews_composite_score
           WHERE score_date=(SELECT MAX(score_date) FROM ews_composite_score)
             AND card_sales_score < 55),
          (SELECT COUNT(*) FROM ews_composite_score
           WHERE score_date=(SELECT MAX(score_date) FROM ews_composite_score)
             AND employment_score < 55)
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

    items = []
    leading = 0
    for r in rows:
        bank_dpd = r[9] or 0
        is_leading = bank_dpd == 0
        if is_leading:
            leading += 1
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
            "total_open": len(items),
            "leading_signals": leading,
            "note": "은행 DPD 0 인데 상거래연체가 있는 구간 = 이 채널이 은행 연체보다 먼저 본 기업",
        },
    }


@router.get("/channel-validation")
def get_channel_validation(db: Session = Depends(get_db)):
    """채널 선행성 백테스트 지표 - 가중치는 주장이 아니라 백테스트로 정한다"""
    rows = db.execute(text("""
        SELECT scope_value, n_defaults, n_detected, detection_rate_pct,
               avg_lead_months, median_lead_months,
               pct_alert_before_3m, pct_alert_before_6m,
               false_alarm_rate_pct, computed_ym
        FROM ews_validation_metrics
        WHERE scope_type = 'CHANNEL'
        ORDER BY median_lead_months DESC, detection_rate_pct DESC
    """)).fetchall()
    return {
        "methodology": {
            "events": "워크아웃 이관·DPD90 기업 (91사) - 채널 점수가 경보 임계(55) 아래로 최초 하락한 시점과 이벤트 시점의 차 = 리드타임",
            "false_alarm": "대조군 400사 중 경보 발화 후 이벤트 미발생 비율 - 탐지율과 반드시 쌍으로 본다",
            "window": "신규 채널 24개월 · 기존 채널 12개월 (원천 이력 한도)",
        },
        "channels": [
            {"channel": r[0], "label": CHANNEL_LABELS.get(r[0], r[0]),
             "n_events": r[1], "n_detected": r[2], "detection_rate": r[3],
             "avg_lead_months": r[4], "median_lead_months": r[5],
             "pct_before_3m": r[6], "pct_before_6m": r[7],
             "false_alarm_rate": r[8], "computed_ym": r[9]}
            for r in rows
        ],
    }


def _quality(metrics: dict) -> dict:
    """채널 품질 점수 - 탐지율 × 리드타임 보너스 × (1-오경보율)"""
    q = {}
    for ch, m in metrics.items():
        det = (m["detection_rate"] or 0) / 100
        lead = (m["median_lead_months"] or 0)
        fa = (m["false_alarm_rate"] or 0) / 100
        q[ch] = det * (1 + lead / 12) * (1 - fa)
    return q


def _bounded_proposal(current: dict, quality: dict, max_shift: float = 0.05) -> dict:
    """검증 기반 가중치 제안 - 채널당 이동폭 ±max_shift 로 제한 후 재정규화.
    급격한 가중치 교체는 모형 안정성을 해치므로 점진 조정만 제안한다."""
    proposal = {}
    for seg, w in current.items():
        active = {ch: wt for ch, wt in w.items() if wt > 0}
        qs = {ch: quality.get(ch, 0.5) for ch in active}
        avg_q = sum(qs.values()) / len(qs) if qs else 1.0
        raw = {}
        for ch, wt in active.items():
            factor = 1.0 + (qs[ch] - avg_q)          # 품질 상대치만큼 가감
            raw[ch] = min(max(wt * factor, wt - max_shift), wt + max_shift)
        total = sum(raw.values())
        seg_prop = {ch: round(v / total, 3) for ch, v in raw.items()}
        # 미활성 채널은 0 유지
        for ch in w:
            seg_prop.setdefault(ch, 0.0)
        proposal[seg] = seg_prop
    return proposal


@router.get("/weight-proposal")
def get_weight_proposal(db: Session = Depends(get_db)):
    """현행 가중치 vs 백테스트 기반 제안 (±5%p 점진 조정)"""
    current = load_weights(db)
    metrics = {r[0]: {"detection_rate": r[1], "median_lead_months": r[2],
                      "false_alarm_rate": r[3]}
               for r in db.execute(text("""
                   SELECT scope_value, detection_rate_pct, median_lead_months,
                          false_alarm_rate_pct
                   FROM ews_validation_metrics WHERE scope_type='CHANNEL'
               """)).fetchall()}
    quality = _quality(metrics)
    proposal = _bounded_proposal(current, quality)
    rule = db.execute(text("""
        SELECT version, valid_from FROM rule_register
        WHERE rule_id LIKE 'RULE_EWS_WEIGHTS%' AND valid_to IS NULL
        ORDER BY valid_from DESC LIMIT 1
    """)).fetchone()
    return {
        "current": current,
        "proposal": proposal,
        "quality": {ch: round(v, 3) for ch, v in quality.items()},
        "current_version": {"version": rule[0], "valid_from": str(rule[1])} if rule else None,
        "governance": "발효는 부서장 이상 승인 + 감사기록 - 승인 즉시 전 고객 종합점수 재계산",
        "bound_note": "채널당 이동폭 ±5%p 제한 (모형 안정성)",
    }


@router.post("/weight-proposal/approve")
def approve_weight_proposal(
    version_label: str = Query("v3.1 (백테스트 재조정)"),
    reason: str = Query(..., min_length=5),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """가중치 제안 발효 - 부서장 이상 + 감사 critical + 즉시 재계산"""
    if current_user.approval_level not in ("DEPT_HEAD", "EXECUTIVE", "COMMITTEE"):
        raise HTTPException(403, "EWS 가중치 변경은 부서장 이상만 승인할 수 있습니다")

    prop = get_weight_proposal(db)
    before = prop["current"]
    new_weights = prop["proposal"]

    rule_id = publish_weights(db, new_weights, version_label, current_user.name)
    stats = recompute_composite(db, weights=new_weights)

    record_audit(db, "EWS_WEIGHTS_PUBLISH", "rule_register", rule_id,
                 before={"weights": before},
                 after={"weights": new_weights, "version": version_label,
                        "reason": reason, "recomputed": stats["updated"]},
                 user_id=current_user.name, user_dept=current_user.dept,
                 critical=True)
    db.commit()
    return {"rule_id": rule_id, "version": version_label,
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
