"""
EWS 8채널 점수화·종합점수 정본 (docs/EWS_8CHANNEL_DESIGN_2026-08-21.md)
========================================================================
채널 점수화 룰과 종합점수(가중·결측 재정규화) 계산의 단일 소스.
데이터 생성기(database/generate_ews_extended_channels.py)와 가중치 승인
API 가 모두 이 모듈을 쓴다 - 산식이 두 곳에 복제되지 않게 한다.

원칙:
- 가중치는 rule_register(RULE_EWS_WEIGHTS) 정본에서 읽는다. 변경은
  가중치 승인 API(부서장 이상 + 감사기록)로만 새 버전이 발효된다.
- 채널 결측·동의 만료는 가중치 재정규화로 처리하고 channel_coverage 에
  사유를 남긴다 - 없는 데이터로 점수를 만들지 않는다 (감사 #10 원칙).
"""
import json
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

# 채널 키 ↔ ews_composite_score 컬럼 매핑
CHANNEL_COLUMNS = {
    "transaction": "transaction_score",
    "card_sales":  "card_sales_score",
    "b2b_delinq":  "b2b_delinq_score",
    "employment":  "employment_score",
    "public":      "public_registry_score",
    "market":      "market_score",
    "news":        "news_score",
    "supply":      "supply_chain_score",
    "financial":   "financial_score",
}

# 동의가 필요한 채널 (상거래연체는 CB 법정 집중이라 동의 불요)
CONSENT_CHANNELS = {"card_sales": "CARD_SALES", "employment": "EMPLOYMENT"}

# rule_register 미존재 시 폴백 (migration 011 시드와 동일)
DEFAULT_WEIGHTS = {
    "LISTED":   {"transaction": 0.20, "card_sales": 0.0,  "b2b_delinq": 0.10,
                 "employment": 0.05, "public": 0.10, "market": 0.15,
                 "news": 0.10, "supply": 0.15, "financial": 0.15},
    "UNLISTED": {"transaction": 0.20, "card_sales": 0.05, "b2b_delinq": 0.15,
                 "employment": 0.10, "public": 0.15, "market": 0.0,
                 "news": 0.10, "supply": 0.10, "financial": 0.15},
    "SOHO":     {"transaction": 0.20, "card_sales": 0.20, "b2b_delinq": 0.10,
                 "employment": 0.05, "public": 0.10, "market": 0.0,
                 "news": 0.05, "supply": 0.05, "financial": 0.25},
}

LISTED_STATUSES = ("KOSPI", "KOSDAQ", "LISTED")


def segment_of(size_category: str, listing_status: str) -> str:
    if size_category == "SOHO":
        return "SOHO"
    if (listing_status or "") in LISTED_STATUSES:
        return "LISTED"
    return "UNLISTED"


def _validate_weights(w: dict) -> bool:
    """구조·합계·범위 검증 - 세그먼트 3종, 값 0~1, 세그먼트 합 1±0.02"""
    try:
        for seg in ("LISTED", "UNLISTED", "SOHO"):
            m = w[seg]
            vals = [float(v) for v in m.values()]
            if any(v < 0 or v > 1 for v in vals):
                return False
            if abs(sum(vals) - 1.0) > 0.02:
                return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def load_weights_meta(db: Session) -> tuple[dict, str, str]:
    """(가중치, rule_id, source). 정본이 깨졌으면 폴백하되 소리 내서 알린다
    (2026-08-22 감사 A8: 조용한 fail-open 금지)."""
    row = db.execute(text("""
        SELECT rule_id, params_json FROM rule_register
        WHERE rule_id LIKE 'RULE_EWS_WEIGHTS%' AND valid_to IS NULL
        ORDER BY valid_from DESC LIMIT 1
    """)).fetchone()
    if row and row[1]:
        try:
            w = json.loads(row[1])
            if _validate_weights(w):
                return w, row[0], "RULE_REGISTER"
            print(f"[ews_channels] 경고: {row[0]} 가중치 검증 실패 - 폴백 사용")
        except ValueError:
            print(f"[ews_channels] 경고: {row[0]} params_json 파싱 실패 - 폴백 사용")
    else:
        print("[ews_channels] 경고: 유효한 RULE_EWS_WEIGHTS 없음 - 폴백 사용")
    return DEFAULT_WEIGHTS, "FALLBACK_DEFAULT", "FALLBACK"


def load_weights(db: Session) -> dict:
    return load_weights_meta(db)[0]


# ── 신규 채널 점수화 룰 (0~100, 낮을수록 위험) ─────────────────────────

def score_card_sales(yoy: float, mom_streak_down: int,
                     active_days_drop_pct: float, industry_pct: float) -> float:
    """카드매출: YoY 급감·연속 하락·영업일수 급감·동업종 열위 감점"""
    s = 100.0
    if yoy is not None:
        if yoy <= -30:
            s -= 40
        elif yoy <= -15:
            s -= 20
    if mom_streak_down >= 3:
        s -= 15
    if active_days_drop_pct is not None and active_days_drop_pct >= 20:
        s -= 15
    if industry_pct is not None and industry_pct <= 10:
        s -= 10
    return max(s, 0.0)


def score_employment(insured_change_3m_pct: float, arrears_months: int) -> float:
    """고용: 피보험자 감소(감원) + 보험료 체납. 동시 발생은 강신호"""
    s = 100.0
    cut = False
    if insured_change_3m_pct is not None:
        if insured_change_3m_pct <= -20:
            s -= 45
            cut = True
        elif insured_change_3m_pct <= -10:
            s -= 25
            cut = True
    if arrears_months >= 2:
        s -= 40
    elif arrears_months >= 1:
        s -= 20
    if cut and arrears_months >= 1:
        s -= 10
    return max(s, 0.0)


def score_b2b(open_events: int, max_overdue_days: int, has_default: bool,
              open_amount_eok: float = 0.0) -> float:
    """상거래연체: 미해소 이벤트 건수·경과일·금액 가중 (설계 §3).
    상거래 부도는 CRITICAL 직행"""
    if has_default:
        return 15.0
    s = 100.0
    s -= min(open_events * 15, 45)
    if max_overdue_days >= 60:
        s -= 25
    elif max_overdue_days >= 30:
        s -= 15
    if open_amount_eok >= 50:
        s -= 10
    elif open_amount_eok >= 20:
        s -= 5
    return max(s, 0.0)


# ── 종합점수 재계산 ────────────────────────────────────────────────────

def grade_of(score: float) -> tuple[str, str]:
    """(ews_grade, risk_level) - README 정본 경계 75/55/35"""
    if score >= 75:
        return "NORMAL", "LOW"
    if score >= 55:
        return "WATCH", "MEDIUM"
    if score >= 35:
        return "WARNING", "HIGH"
    return "CRITICAL", "CRITICAL"


def _consent_state(db: Session) -> dict:
    """customer→channel→상태. 동의 필요 채널만 조회한다."""
    out: dict = {}
    for r in db.execute(text("""
        SELECT customer_id, channel, status, expiry_date
        FROM ews_channel_consent
    """)).fetchall():
        cid, ch, status, expiry = r
        if status == "WITHDRAWN":
            state = "WITHDRAWN"
        elif status == "EXPIRED" or (expiry and str(expiry) < db.execute(
                text("SELECT date('now')")).scalar()):
            state = "CONSENT_EXPIRED"
        else:
            state = "OK"
        out.setdefault(cid, {})[ch] = state
    return out


def recompute_composite(db: Session, weights: dict | None = None,
                        applied_rule_id: str | None = None) -> dict:
    """최신 score_date 의 전 고객 종합점수를 8채널·결측 재정규화로 재계산.

    채널 점수 자체는 갱신하지 않는다 (원천 반영은 생성기·배치의 몫) -
    이 함수는 '가중 결합' 정본이다. 가중치 변경 승인 시에도 호출된다.
    """
    if weights is None:
        weights, rid, _src = load_weights_meta(db)
        applied_rule_id = applied_rule_id or rid
    consent = _consent_state(db)
    today = db.execute(text("SELECT date('now')")).scalar()
    from datetime import datetime as _dt
    computed_at = _dt.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = db.execute(text("""
        SELECT s.score_id, s.customer_id, c.size_category, c.listing_status,
               s.transaction_score, s.card_sales_score, s.b2b_delinq_score,
               s.employment_score, s.public_registry_score, s.market_score,
               s.news_score, s.supply_chain_score, s.financial_score,
               s.composite_score
        FROM ews_composite_score s
        JOIN customer c ON s.customer_id = c.customer_id
        WHERE s.score_date = (SELECT MAX(score_date) FROM ews_composite_score)
    """)).fetchall()

    updated = 0
    for r in rows:
        score_id, cid = r[0], r[1]
        seg = segment_of(r[2], r[3])
        w = weights.get(seg, weights.get("UNLISTED", {}))
        chan_scores = {
            "transaction": r[4], "card_sales": r[5], "b2b_delinq": r[6],
            "employment": r[7], "public": r[8], "market": r[9],
            "news": r[10], "supply": r[11], "financial": r[12],
        }
        coverage = {}
        num = 0.0
        den = 0.0
        for ch, sc in chan_scores.items():
            wt = float(w.get(ch, 0) or 0)
            if wt <= 0:
                continue
            # 동의 필요 채널: 동의 없음/만료면 데이터가 있어도 결측 처리
            consent_key = CONSENT_CHANNELS.get(ch)
            if consent_key:
                state = consent.get(cid, {}).get(consent_key)
                if state is None:
                    coverage[ch] = "NO_CONSENT"
                    continue
                if state != "OK":
                    coverage[ch] = state
                    continue
            if sc is None:
                coverage[ch] = "MISSING"
                continue
            coverage[ch] = "OK"
            num += wt * float(sc)
            den += wt
        if den <= 0:
            continue
        composite = round(num / den, 1)
        grade, risk = grade_of(composite)
        db.execute(text("""
            UPDATE ews_composite_score
            SET composite_score = :cs, ews_grade = :g, risk_level = :rl,
                channel_coverage = :cov,
                applied_rule_id = :rid, computed_at = :cat
            WHERE score_id = :sid
        """), {"cs": composite, "g": grade, "rl": risk,
               "cov": json.dumps(coverage, ensure_ascii=False),
               "rid": applied_rule_id, "cat": computed_at, "sid": score_id})
        updated += 1

    return {"updated": updated, "as_of": today}


def publish_weights(db: Session, new_weights: dict, version_label: str,
                    approved_by: str) -> tuple[str, str]:
    """가중치 새 버전 발효 - 기존 행 valid_to 마감 + 새 행 삽입.
    버전은 서버가 단조 증가로 채번한다 (감사 A5 - 중복 버전 차단).
    호출부(API)가 권한·감사기록을 책임진다. 반환: (rule_id, version)"""
    if not _validate_weights(new_weights):
        raise ValueError("가중치 검증 실패 - 세그먼트 합계·범위 위반")
    n = db.execute(text(
        "SELECT COUNT(*) FROM rule_register WHERE rule_id LIKE 'RULE_EWS_WEIGHTS%'"
    )).scalar() or 0
    version = f"v3.{n} ({version_label})"
    db.execute(text("""
        UPDATE rule_register SET valid_to = date('now')
        WHERE rule_id LIKE 'RULE_EWS_WEIGHTS%' AND valid_to IS NULL
    """))
    new_id = f"RULE_EWS_WEIGHTS_{uuid.uuid4().hex[:6].upper()}"
    db.execute(text("""
        INSERT INTO rule_register
            (rule_id, domain, name, basis, version, valid_from, params_json, applied_in)
        VALUES (:rid, 'EWS', 'EWS 채널 가중치 (세그먼트별)',
                :basis, :ver, date('now'), :params,
                'services/ews_channels.py recompute_composite')
    """), {"rid": new_id,
           "basis": f"채널 선행성 백테스트 기반 재조정 - 승인 {approved_by}",
           "ver": version,
           "params": json.dumps(new_weights, ensure_ascii=False)})
    return new_id, version
