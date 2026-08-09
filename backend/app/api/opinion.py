"""
심사의견서 자동 초안 API
=========================
신청 건의 시스템 보유 데이터(재무·등급·EWS·동일차주·담보·수익성)를 근거로
심사의견서 초안을 자동 생성한다. 문안은 규칙 기반으로 생성되며,
심사역의 검토·수정을 전제로 한 '초안'임을 문서에 명시한다.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..core.config import AS_OF_STR
from ..services.calculations import calculate_raroc, get_pd_from_grade
from .rules import get_rule_params

router = APIRouter(prefix="/api/applications", tags=["Opinion Draft"])

EOK = 1e8

COLLATERAL_KO = {
    "REAL_ESTATE": "부동산", "DEPOSIT": "예금", "SECURITIES": "유가증권",
    "MOVABLE_PROPERTY": "동산", "GUARANTEE": "보증", "RECEIVABLES": "매출채권",
    "IP_RIGHTS": "지식재산권", "NONE": "신용",
}


def _eok(v) -> str:
    v = float(v or 0)
    if abs(v) >= 1e12:
        return f"{v / 1e12:,.2f}조원"
    return f"{v / EOK:,.1f}억원"


def _gather(db: Session, application_id: str) -> dict:
    app = db.execute(text("""
        SELECT la.application_id, la.application_date, la.application_type,
               la.requested_amount, la.requested_tenor, la.requested_rate,
               la.status, la.collateral_type, la.purpose_detail,
               c.customer_id, c.customer_name, c.industry_name, c.size_category,
               c.region, c.establish_date, p.product_name, la.group_id
        FROM loan_application la
        JOIN customer c ON la.customer_id = c.customer_id
        LEFT JOIN product_master p ON la.product_code = p.product_code
        WHERE la.application_id = :aid
    """), {"aid": application_id}).fetchone()
    if not app:
        raise HTTPException(404, "신청 건을 찾을 수 없습니다")

    cid = app[9]

    rating = db.execute(text("""
        SELECT final_grade, pd_value, rating_date FROM credit_rating_result
        WHERE application_id = :aid ORDER BY rating_date DESC LIMIT 1
    """), {"aid": application_id}).fetchone()
    if not rating:
        rating = db.execute(text("""
            SELECT r.final_grade, r.pd_value, r.rating_date
            FROM credit_rating_result r
            JOIN loan_application a ON r.application_id = a.application_id
            WHERE a.customer_id = :cid ORDER BY r.rating_date DESC LIMIT 1
        """), {"cid": cid}).fetchone()

    fin = db.execute(text("""
        SELECT fiscal_year, debt_ratio, current_ratio, ier, dscr, op_margin,
               roa, revenue_growth, altman_z
        FROM financial_ratio WHERE customer_id = :cid
        ORDER BY fiscal_year DESC LIMIT 2
    """), {"cid": cid}).fetchall()

    stmt = db.execute(text("""
        SELECT fiscal_year, revenue, operating_profit, total_assets, equity
        FROM financial_statement WHERE customer_id = :cid
        ORDER BY fiscal_year DESC LIMIT 1
    """), {"cid": cid}).fetchone()

    ews = db.execute(text("""
        SELECT composite_score, risk_level, ews_grade, score_date
        FROM ews_composite_score WHERE customer_id = :cid
        ORDER BY score_date DESC LIMIT 1
    """), {"cid": cid}).fetchone()

    existing = db.execute(text("""
        SELECT COUNT(*), COALESCE(SUM(outstanding_amount), 0)
        FROM facility WHERE customer_id = :cid AND status = 'ACTIVE'
    """), {"cid": cid}).fetchone()

    collateral = db.execute(text("""
        SELECT collateral_type, COALESCE(SUM(recognized_value), 0), COUNT(*)
        FROM collateral WHERE application_id = :aid OR facility_id IN
            (SELECT facility_id FROM facility WHERE customer_id = :cid AND status='ACTIVE')
        GROUP BY collateral_type ORDER BY 2 DESC
    """), {"aid": application_id, "cid": cid}).fetchall()

    group = None
    if app[16]:
        group = db.execute(text("""
            SELECT bg.group_name,
                   (SELECT COALESCE(SUM(net_exposure), 0) FROM credit_exposure_ledger l
                    JOIN borrower_group_member m ON l.customer_id = m.customer_id
                    WHERE m.group_id = bg.group_id),
                   (SELECT total_capital FROM capital_position
                    ORDER BY base_date DESC LIMIT 1)
            FROM borrower_group bg WHERE bg.group_id = :gid
        """), {"gid": app[16]}).fetchone()

    return {"app": app, "rating": rating, "fin": fin, "stmt": stmt, "ews": ews,
            "existing": existing, "collateral": collateral, "group": group}


def _build_draft(d: dict) -> dict:
    app, rating, fin = d["app"], d["rating"], d["fin"]
    amount = float(app[3] or 0)
    tenor = app[4] or 12
    rate = float(app[5] or 0.05)
    grade = rating[0] if rating else None
    pd_val = float(rating[1]) if rating and rating[1] else get_pd_from_grade(grade or "BB")

    positives, cautions, conditions = [], [], []
    sections = []

    # ── 1. 신청 개요 ─────────────────────────────────────────
    coll_total = sum(float(c[1]) for c in d["collateral"]) if d["collateral"] else 0
    sections.append({
        "title": "1. 신청 개요",
        "rows": [
            ["차주", f"{app[10]} ({app[11] or '-'} / {app[12] or '-'} / {app[13] or '-'})"],
            ["신청 내용", f"{app[15] or app[2] or '기업 여신'} {_eok(amount)}, {tenor}개월, "
                        f"신청금리 {rate * 100:.2f}%"],
            ["자금 용도", app[8] or "-"],
            ["기존 여신", f"{d['existing'][0]}건 {_eok(d['existing'][1])} (당행)"],
            ["담보 구분", app[7] or "신용"],
        ],
        "text": [],
    })

    # ── 2. 차주 신용도 ───────────────────────────────────────
    ews = d["ews"]
    lines = []
    if rating:
        lines.append(f"당행 신용평가 결과 {grade} 등급(PD {pd_val * 100:.2f}%, "
                     f"평가일 {rating[2]})이다.")
        gi = ["AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-"]
        if grade in gi:
            positives.append("투자적격 등급")
            lines.append("투자적격 구간으로 신용위험은 양호한 수준으로 판단된다.")
        elif grade and grade.startswith("B") and not grade.startswith("BB"):
            cautions.append(f"투기 등급({grade})")
            lines.append("투기 등급 구간으로 여신 취급 시 보수적 접근이 필요하다.")
    else:
        cautions.append("신용평가 이력 없음")
        lines.append("당행 신용평가 이력이 없어 신규 평가가 선행되어야 한다.")
    if ews:
        lines.append(f"조기경보(EWS) 종합점수 {ews[0]:.1f}점, 위험단계 {ews[1]} "
                     f"({ews[3]} 기준)이다.")
        if ews[1] in ("WARNING", "CRITICAL", "HIGH"):
            cautions.append(f"EWS {ews[1]} 경보")
            conditions.append("EWS 경보 해소 시까지 분기별 모니터링 보고")
        elif ews[1] in ("LOW", "NORMAL"):
            positives.append("EWS 정상 범위")
        else:
            lines.append("EWS 중간 위험 단계로 취급 후 정기 모니터링 대상이다.")
    sections.append({"title": "2. 차주 신용도", "rows": [], "text": lines})

    # ── 3. 재무 분석 ─────────────────────────────────────────
    lines, rows = [], []
    if fin:
        f0 = fin[0]
        rows = [["기준 결산연도", f"{f0[0]}년"], ["부채비율", f"{f0[1]:.1f}%"],
                ["유동비율", f"{f0[2]:.1f}%"], ["이자보상배율", f"{f0[3]:.2f}배"],
                ["영업이익률", f"{f0[5]:.1f}%"], ["매출성장률", f"{f0[7]:.1f}%"]]
        if d["stmt"]:
            lines.append(f"{d['stmt'][0]}년 매출액 {_eok(d['stmt'][1])}, "
                         f"영업이익 {_eok(d['stmt'][2])}, 자기자본 {_eok(d['stmt'][4])}이다.")
        if f0[1] is not None:
            if f0[1] > 300:
                cautions.append(f"부채비율 {f0[1]:.0f}% 과다")
                conditions.append("부채비율 300% 이하 유지 재무약정(코베넌트) 부과")
            elif f0[1] > 200:
                cautions.append(f"부채비율 {f0[1]:.0f}% 다소 높음")
            elif f0[1] <= 150:
                positives.append(f"부채비율 {f0[1]:.0f}% 안정")
        if f0[3] is not None:
            if f0[3] < 1:
                cautions.append(f"이자보상배율 {f0[3]:.2f}배 - 영업이익으로 이자 미충당")
                conditions.append("영업현금흐름 개선 계획 징구")
            elif f0[3] >= 3:
                positives.append(f"이자보상배율 {f0[3]:.1f}배 양호")
        if len(fin) > 1 and fin[1][1] is not None and f0[1] is not None:
            diff = f0[1] - fin[1][1]
            lines.append(f"부채비율은 전기 대비 {abs(diff):.1f}%p "
                         f"{'상승' if diff > 0 else '하락'}했다.")
    else:
        lines.append("재무자료가 없어 최근 결산 재무제표 징구가 선행되어야 한다.")
        cautions.append("재무자료 미비")
        conditions.append("최근 3개년 결산 재무제표 및 부속명세서 징구")
    sections.append({"title": "3. 재무 분석", "rows": rows, "text": lines})

    # ── 4. 동일차주·한도 검토 ────────────────────────────────
    lines = []
    if d["group"]:
        gname, gexp, cap = d["group"][0], float(d["group"][1] or 0), float(d["group"][2] or 0)
        limit25 = cap * 0.25
        after = gexp + amount
        lines.append(f"동일차주그룹 [{gname}] 합산 신용공여는 {_eok(gexp)}이며, "
                     f"본건 포함 시 {_eok(after)}로 은행법 §35 동일차주 한도"
                     f"(자기자본의 25%, {_eok(limit25)})의 "
                     f"{after / limit25 * 100:.1f}% 수준이다.")
        if after > limit25:
            cautions.append("동일차주 법정한도 초과")
            conditions.append("한도 초과분 감액 또는 여신위원회 부의")
        elif after > limit25 * 0.8:
            cautions.append("동일차주 한도 소진율 80% 초과")
        else:
            positives.append("동일차주 한도 여유 충분")
    else:
        lines.append("동일차주그룹에 속하지 않은 단독 차주로, 개별 한도 관리 대상이다.")
    sections.append({"title": "4. 동일차주·한도 검토", "rows": [], "text": lines})

    # ── 5. 담보 및 채권보전 ──────────────────────────────────
    lines, rows = [], []
    if coll_total > 0:
        coverage = coll_total / amount * 100 if amount else 0
        rows = [[COLLATERAL_KO.get(c[0], c[0] or "기타"), _eok(c[1]), f"{c[2]}건"]
                for c in d["collateral"][:5]]
        lines.append(f"인정담보가액 합계는 {_eok(coll_total)}이며, 본건 신청금액의 "
                     f"{coverage:.0f}%를 보전한다.")
        if coverage >= 80:
            positives.append(f"담보 커버리지 {coverage:.0f}%")
        elif coverage < 40:
            cautions.append(f"담보 커버리지 {coverage:.0f}% - 신용 익스포저 비중 큼")
            conditions.append("추가 담보 취득 또는 신용보증기금 보증서 보완 검토")
    else:
        lines.append("본건은 담보 없는 신용여신으로, 차주 신용도와 현금흐름에 "
                     "전적으로 의존한다.")
        cautions.append("무담보 신용여신")
        conditions.append("대표이사 연대보증 또는 보증기관 보증 검토")
    sections.append({"title": "5. 담보 및 채권보전", "rows": rows, "text": lines})

    # ── 6. 수익성 (RAROC) ────────────────────────────────────
    hurdle = float(get_rule_params("RULE_RAROC_HURDLE", {"hurdle_pct": 12})
                   .get("hurdle_pct", 12))
    lgd = 0.35 if coll_total > 0 else 0.45
    raroc = calculate_raroc(amount=amount, rate=rate, ftp_rate=0.03,
                            pd=pd_val, lgd=lgd, tenor_years=max(tenor / 12, 0.5))
    raroc_pct = float(raroc.get("raroc", 0)) * 100   # 소수 → %
    pd_note = "" if rating else " · 등급 미보유로 BB 등급 가정 PD"
    lines = [f"신청 조건 기준 RAROC는 {raroc_pct:.1f}%로 허들레이트 {hurdle:.0f}%"
             f"{'를 충족한다' if raroc_pct >= hurdle else '에 미달한다'} "
             f"(PD {pd_val * 100:.2f}%, LGD {lgd * 100:.0f}% 적용{pd_note})."]
    if raroc_pct >= hurdle:
        positives.append(f"RAROC {raroc_pct:.1f}% (허들 충족)")
    else:
        cautions.append(f"RAROC {raroc_pct:.1f}% (허들 {hurdle:.0f}% 미달)")
        conditions.append("금리 재산정 또는 부수거래(수신·외환) 확보로 수익성 보완")
    sections.append({"title": "6. 수익성 검토", "rows": [], "text": lines})

    # ── 7. 종합의견 ──────────────────────────────────────────
    if len(cautions) == 0:
        verdict, verdict_code = "승인 적정", "APPROVE"
    elif len(cautions) <= 2 and len(positives) >= len(cautions):
        verdict, verdict_code = "조건부 승인 검토", "CONDITIONAL"
    else:
        verdict, verdict_code = "신중 검토 필요", "CAUTION"
    lines = [f"이상을 종합할 때 본건의 시스템 초안 의견은 「{verdict}」 이다."]
    if positives:
        lines.append("긍정 요인: " + " / ".join(positives))
    if cautions:
        lines.append("유의 요인: " + " / ".join(cautions))
    sections.append({"title": "7. 종합의견", "rows": [], "text": lines})

    return {
        "application_id": app[0],
        "customer_name": app[10],
        "as_of": AS_OF_STR,
        "verdict": verdict,
        "verdict_code": verdict_code,
        "sections": sections,
        "recommended_conditions": conditions,
        "disclaimer": ("본 문서는 시스템 보유 데이터를 근거로 자동 생성된 초안으로, "
                       "심사역의 검토·수정 및 결재권자의 판단을 전제로 합니다."),
    }


@router.get("/{application_id}/opinion-draft")
def get_opinion_draft(application_id: str, db: Session = Depends(get_db)):
    """심사의견서 자동 초안 (JSON)"""
    return _build_draft(_gather(db, application_id))


@router.get("/{application_id}/opinion-draft/pdf")
def get_opinion_draft_pdf(application_id: str, db: Session = Depends(get_db)):
    """심사의견서 자동 초안 (PDF 다운로드)"""
    from ..services.report_pdf import build_opinion_pdf
    draft = _build_draft(_gather(db, application_id))
    pdf_bytes = build_opinion_pdf(draft)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition":
                 f'attachment; filename="opinion_{application_id}.pdf"'},
    )
