#!/usr/bin/env python3
"""
고객 수익성(RBC) 정본 연동 재생성 (2026-08-22)
================================================
종전 생성 로직은 여신이자수익을 난수(잔액×3~6%)로 만들어 여신 화면의 실제
계약 금리와 불일치했고, 여신 0 고객 161사에 여신수익이 존재했으며, EC 가
난수라 RAROC 이 최대 20,893%까지 튀어 랭킹 화면이 왜곡됐다 (검증 보고).

정본 연동 원칙:
  여신수익   = Σ(잔액 × 실제 final_rate)          ← facility 정본
  여신조달   = Σ(잔액 × 테너별 FTP) + 운영 0.5%    ← ftp_rate 정본
  여신 EL    = Σ(risk_parameter.expected_loss)     ← 리스크 정본
  경제적자본 = Σ(risk_parameter.rwa) × 10.5%       ← 자본 정본 (RWA×10.5%)
  자본비용   = EC × 자본원가 10% (가정 명시)
  RAROC     = 경제적이익 ÷ EC                      ← capital_optimizer 와 동일 구조
  수신·수수료·FX = 관계 규모(여신·자산·매출) 연동 결정론 해시
  여신 0 고객 = 여신 항목 전부 0, 수신·수수료 관계만

결정론: customer_id 해시 기반 - 재실행해도 같은 결과.
"""
import hashlib
import os
import sqlite3
import uuid
from pathlib import Path

DB = Path(os.getenv("CLMS_DB_PATH") or Path(__file__).parent / "imbank_demo.db")

OPEX_RATE = 0.005          # 여신 운영비 (region_helper·정본과 동일)
CAPITAL_CHARGE = 0.10      # 자본원가 가정 (EC 에 대한 요구수익률)
DEPOSIT_PAY_RATE = 0.021   # 예금 지급금리 (실측 수신금리 2.1% 참조)
DEPOSIT_FTP = 0.030        # 수신의 내부 이전가치 (FTP 조달 대체)
AS_OF = "2026-07-31"

# FX 활동성 업종 (수출입·무역 성격)
FX_INDUSTRIES = ("무역", "자동차부품", "반도체", "화학", "기계장비")


def h(cid: str, salt: str) -> float:
    return int(hashlib.sha256(f"{cid}:{salt}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # FTP 곡선 (최신 effective_date)
    ftp_rows = cur.execute("""
        SELECT tenor_months, final_ftp_rate FROM ftp_rate
        WHERE effective_date = (SELECT MAX(effective_date) FROM ftp_rate)
        ORDER BY tenor_months
    """).fetchall()
    ftp_curve = ftp_rows or [(12, 0.0272), (36, 0.0300), (60, 0.0319)]

    def ftp_for(months: float) -> float:
        best = min(ftp_curve, key=lambda r: abs(r[0] - months))
        return float(best[1])

    # 고객별 여신 정본 집계 (금리·FTP·EL·RWA 전부 실제값)
    fac_rows = cur.execute("""
        SELECT f.customer_id, f.outstanding_amount, f.final_rate,
               COALESCE((julianday(f.maturity_date) - julianday(f.contract_date)) / 30.4, 36) AS tenor_m,
               COALESCE(rp.expected_loss, f.outstanding_amount * 0.0025) AS el,
               COALESCE(rp.rwa, f.outstanding_amount * 0.6) AS rwa
        FROM facility f
        LEFT JOIN risk_parameter rp ON f.application_id = rp.application_id
        WHERE f.status = 'ACTIVE'
    """).fetchall()
    loan_agg: dict = {}
    for cid, out, rate, tenor_m, el, rwa in fac_rows:
        out = float(out or 0)
        a = loan_agg.setdefault(cid, {"rev": 0.0, "ftp": 0.0, "el": 0.0, "rwa": 0.0, "bal": 0.0})
        a["bal"] += out
        a["rev"] += out * float(rate or 0.047)
        a["ftp"] += out * ftp_for(float(tenor_m or 36))
        a["el"]  += float(el or 0)
        a["rwa"] += float(rwa or 0)

    customers = cur.execute("""
        SELECT customer_id, size_category, industry_name,
               COALESCE(asset_size, 0), COALESCE(revenue_size, 0)
        FROM customer
    """).fetchall()

    cur.execute("DELETE FROM customer_profitability")
    rows = []
    for cid, size, industry, assets, revenue_size in customers:
        a = loan_agg.get(cid)

        if a:
            loan_revenue = a["rev"]
            loan_cost = a["ftp"] + a["bal"] * OPEX_RATE
            loan_el = a["el"]
            ec_credit = a["rwa"] * 0.105
            loan_capital_cost = ec_credit * CAPITAL_CHARGE
            loan_profit = loan_revenue - loan_cost - loan_el - loan_capital_cost
            bal = a["bal"]
        else:
            loan_revenue = loan_cost = loan_el = loan_capital_cost = loan_profit = 0.0
            ec_credit = 0.0
            bal = 0.0

        # 수신: 관계 규모 연동 - 여신 고객은 여신의 15~55%, 무여신 고객은
        # 자산 규모의 1~4% 수준 요구불·정기성 예치 가정 (결정론 해시)
        deposit_bal = bal * (0.15 + h(cid, "dep") * 0.40) if bal > 0 \
            else float(assets) * (0.01 + h(cid, "dep") * 0.03)
        deposit_revenue = deposit_bal * DEPOSIT_FTP          # 내부 이전가치
        deposit_cost = deposit_bal * DEPOSIT_PAY_RATE + deposit_bal * 0.002  # 지급이자+운영
        deposit_profit = deposit_revenue - deposit_cost

        # 수수료: 여신·수신 관계 규모의 0.10~0.30% (약정·송금·CMS 등)
        rel = bal + deposit_bal
        fee_revenue = rel * (0.0010 + h(cid, "fee") * 0.0020)
        fee_cost = fee_revenue * 0.25
        fee_profit = fee_revenue - fee_cost

        # 외환: 수출입 성격 업종의 60%만 활동 - 매출 규모의 0.03~0.10%
        fx_active = any(k in (industry or "") for k in FX_INDUSTRIES) and h(cid, "fxon") < 0.6
        fx_revenue = float(revenue_size) * (0.0003 + h(cid, "fx") * 0.0007) if fx_active else 0.0
        fx_cost = fx_revenue * 0.35
        fx_profit = fx_revenue - fx_cost

        total_revenue = loan_revenue + deposit_revenue + fee_revenue + fx_revenue
        total_cost = loan_cost + deposit_cost + fee_cost + fx_cost + loan_el + loan_capital_cost
        total_profit = total_revenue - total_cost

        # EC: 신용 RWA×10.5% + 비여신 활동의 운영리스크성 최소자본
        # (수익의 15% - 바젤 운영리스크 지표 근사). 무여신 고객 RAROC 폭주 방지.
        ec_oprisk = (deposit_revenue + fee_revenue + fx_revenue) * 0.15
        # 관계 규모(여신+수신)의 0.5% 를 최소 자본으로 - 무여신 수수료·수신
        # 고객의 RAROC 폭주 완화 (수수료 비즈니스 RAROC 이 높은 것 자체는
        # 실무 부합이나, 랭킹 왜곡을 막기 위한 운영·평판리스크성 하한)
        economic_capital = max(ec_credit + ec_oprisk, rel * 0.005, 1e6)
        raroc = total_profit / economic_capital * 100

        clv = round(30 + h(cid, "clv") * 65, 1)
        retention = round(0.60 + h(cid, "ret") * 0.38, 2)
        churn = round(max(0.0, min(1.0, 1 - retention + (h(cid, "chn") - 0.5) * 0.2)), 2)

        rows.append((
            f"CP_{uuid.uuid4().hex[:12].upper()}", cid, AS_OF,
            round(loan_revenue), round(loan_cost), round(loan_el),
            round(loan_capital_cost), round(loan_profit),
            round(deposit_revenue), round(deposit_cost), round(deposit_profit),
            round(fee_revenue), round(fee_cost), round(fee_profit),
            round(fx_revenue), round(fx_cost), round(fx_profit),
            round(total_revenue), round(total_cost), round(total_profit),
            round(economic_capital), round(raroc, 2),
            clv, retention, round(0.1 + h(cid, "xs") * 0.7, 2), churn,
        ))

    cur.executemany("""
        INSERT INTO customer_profitability
        (profitability_id, customer_id, calculation_date,
         loan_revenue, loan_cost, loan_el, loan_capital_cost, loan_profit,
         deposit_revenue, deposit_cost, deposit_profit,
         fee_revenue, fee_cost, fee_profit,
         fx_revenue, fx_cost, fx_profit,
         total_revenue, total_cost, total_profit,
         economic_capital, raroc, clv_score, retention_probability,
         cross_sell_potential, churn_risk_score)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    con.commit()

    # 검증 출력
    chk = cur.execute("""
        SELECT ROUND(AVG(raroc),1),
               (SELECT COUNT(*) FROM customer_profitability WHERE raroc > 100),
               (SELECT COUNT(*) FROM customer_profitability cp
                WHERE cp.loan_revenue > 0 AND cp.customer_id NOT IN
                  (SELECT customer_id FROM facility WHERE status='ACTIVE'))
        FROM customer_profitability
    """).fetchone()
    print(f"재생성 {len(rows)}건 · RAROC 평균 {chk[0]}% · RAROC>100% {chk[1]}건 · 무여신+여신수익 {chk[2]}건")


if __name__ == "__main__":
    main()
