"""
Phase 2 시드 데이터 생성 스크립트
===================================
자산건전성 분류 / IFRS9 ECL / 연체 관리 초기 데이터 생성

생성 대상:
  - asset_classification : 여신 × 12개월 ≈ 14,400건
  - ecl_calculation      : 여신 × 12개월 ≈ 14,400건
  - delinquency_record   : 여신의 약 12% ≈ 150건
  - collection_activity  : 연체 1건당 평균 3회 ≈ 450건
  - facility 컬럼 갱신   : dpd, max_dpd_12m, classification
"""

import sqlite3
import uuid
import random
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from base_date import AS_OF_DATE, month_starts  # noqa: E402

DB_PATH   = os.path.join(os.path.dirname(__file__), "imbank_demo.db")
SQL_FILE  = os.path.join(os.path.dirname(__file__), "schema_phase2.sql")

# ------------------------------------------------------------------ #
# Phase 2 스키마 적용
# ------------------------------------------------------------------ #

def apply_schema(conn: sqlite3.Connection):
    """schema_phase2.sql 적용 (중복 무시)"""
    with open(SQL_FILE, "r", encoding="utf-8") as f:
        full_sql = f.read()

    lines = []
    for line in full_sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)

    cur = conn.cursor()
    for stmt in [s.strip() for s in cleaned.split(";") if s.strip()]:
        try:
            cur.execute(stmt)
            conn.commit()
        except Exception as e:
            err = str(e).lower()
            if ("duplicate column" in err or "already exists" in err
                    or "no such table" in err):
                pass
            else:
                print(f"  [WARN] {str(e)[:120]}")


# ------------------------------------------------------------------ #
# 헬퍼
# ------------------------------------------------------------------ #

def uid():
    return str(uuid.uuid4())

def fmt(d: date) -> str:
    return d.strftime("%Y-%m-%d")

# 분류 기준·충당금률·연체단계는 런타임과 반드시 같아야 한다.
# 여기서 따로 정의하면 시드와 월말 재분류 결과가 어긋나므로 backend 모듈을 그대로 쓴다.
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from app.services.calculations import (          # noqa: E402
    GRADE_PD_MAP as GRADE_PD,
    PROVISION_RATES,
    _CLASS_ORDER as CLASS_ORDER,
    classify_asset_by_dpd as classify_by_dpd,
    classify_asset_by_pd as classify_by_pd,
    classify_asset_by_ews as classify_by_ews,
    determine_delinquency_stage as delinquency_stage,
    DPD_PRECAUTIONARY, DPD_SUBSTANDARD, DPD_LOSS,
)


def worst_class(*classes) -> str:
    ranks = [CLASS_ORDER.index(c) if c in CLASS_ORDER else 0 for c in classes]
    return CLASS_ORDER[max(ranks)]


# ------------------------------------------------------------------ #
# 연체 발생 모수 - 금융감독원 「국내은행 원화대출 연체율 현황」 기준
# ------------------------------------------------------------------ #
# 기업대출 연체율(1개월 이상) 0.84%, 중소기업 1.00%, 대기업 0.27%.
# 본 데모는 중소기업 비중이 높은 지방은행 포트폴리오를 가정해 1.5% 수준으로 잡는다
# (실제보다 다소 보수적 - 부실관리 화면에 표본이 남아야 하므로).
#
# 종전에는 여신의 12%를 연체로 만들고 연체일수를 1~90일 균등분포로 뽑아
# 1개월 이상 연체율이 11.3%까지 올라갔다. 실제의 13배다.
DELINQUENCY_RATE_1M = 0.015    # 1개월 이상 연체 비중
DELINQUENCY_RATE_SHORT = 0.02  # 1개월 미만 단기 연체 비중 (건전성상 정상)

# 연체 구간 분포 - 연체는 단기에 몰리고 장기로 갈수록 급감한다(롤레이트 체감).
# (하한일, 상한일, 가중치)
DPD_BUCKETS = [
    (DPD_PRECAUTIONARY, DPD_SUBSTANDARD - 1, 0.55),   # 30~89일   요주의
    (DPD_SUBSTANDARD,   180,                 0.28),   # 90~180일  고정이하
    (181,               DPD_LOSS - 1,        0.12),   # 181~364일 고정이하
    (DPD_LOSS,          DPD_LOSS + 200,      0.05),   # 365일 이상 추정손실
]


def sample_dpd() -> int:
    """실제 연체 분포에 가깝게 DPD를 뽑는다 (1개월 이상 구간)."""
    buckets = [(lo, hi) for lo, hi, _ in DPD_BUCKETS]
    weights = [w for _, _, w in DPD_BUCKETS]
    lo, hi = random.choices(buckets, weights=weights, k=1)[0]
    return random.randint(lo, hi)


# ------------------------------------------------------------------ #
# 자산건전성 분류 + ECL 생성
# ------------------------------------------------------------------ #

def generate_classification_and_ecl(conn: sqlite3.Connection):
    cur = conn.cursor()

    # 대상 여신 조회
    facilities = cur.execute("""
        SELECT f.facility_id, f.customer_id,
               f.outstanding_amount, f.contract_date, f.maturity_date,
               rp.ttc_pd, rp.lgd,
               ews.composite_score
        FROM facility f
        LEFT JOIN loan_application la ON f.application_id = la.application_id
        LEFT JOIN (
            SELECT application_id, ttc_pd, lgd
            FROM risk_parameter
        ) rp ON la.application_id = rp.application_id
        LEFT JOIN (
            SELECT customer_id, composite_score
            FROM ews_composite_score
            WHERE (customer_id, score_date) IN (
                SELECT customer_id, MAX(score_date) FROM ews_composite_score
                GROUP BY customer_id
            )
        ) ews ON f.customer_id = ews.customer_id
        WHERE f.status = 'ACTIVE'
        LIMIT 1200
    """).fetchall()

    print(f"  대상 여신: {len(facilities)}건")

    # 12개월치 기준일 생성 (2024-01 ~ 2024-12)
    # 기준월부터 거슬러 12개월 (각 월 1일). 종전에는 2024-01 고정이라
    # 화면 기준일과 분류 이력 시점이 2년 넘게 어긋나 있었다.
    base_dates = month_starts(12)

    class_rows = []
    ecl_rows   = []

    for fac in facilities:
        fid       = fac[0]
        cid       = fac[1]
        ead       = float(fac[2] or 1_000_000_000)
        pd_base   = float(fac[5]) if fac[5] else 0.02
        lgd       = float(fac[6]) if fac[6] else 0.45
        ews_base  = float(fac[7]) if fac[7] else random.uniform(50, 90)

        # 여신별 기본 DPD - 감독원 연체율 통계에 맞춘 발생률과 구간 분포
        roll = random.random()
        if roll < DELINQUENCY_RATE_1M:
            is_delinquent = True                      # 1개월 이상 연체
            base_dpd = sample_dpd()
        elif roll < DELINQUENCY_RATE_1M + DELINQUENCY_RATE_SHORT:
            is_delinquent = False                     # 단기 연체 (건전성상 정상)
            base_dpd = random.randint(1, DPD_PRECAUTIONARY - 1)
        else:
            is_delinquent = False
            base_dpd = 0

        prev_class = None
        prev_ecl   = None

        for i, bd in enumerate(base_dates):
            # DPD 월별 변화 (단순 랜덤 워크)
            dpd = max(0, base_dpd + random.randint(-5, 8) * (1 if is_delinquent else 0))

            # EWS 점수 (기본값에서 월별 변동)
            ews_score = ews_base + random.gauss(0, 8) if not is_delinquent else ews_base - random.gauss(15, 10)
            ews_score = max(10, min(100, ews_score))

            # PD: 시간에 따라 소폭 변동
            pd_curr = max(0.0001, min(0.99, pd_base * random.uniform(0.8, 1.4)))

            # 분류
            dpd_cls = classify_by_dpd(dpd)
            pd_cls  = classify_by_pd(pd_curr)
            ews_cls = classify_by_ews(ews_score)
            cls     = worst_class(dpd_cls, pd_cls, ews_cls)

            # 분류 근거
            ranks   = {"DPD": CLASS_ORDER.index(dpd_cls),
                       "PD":  CLASS_ORDER.index(pd_cls),
                       "EWS": CLASS_ORDER.index(ews_cls)}
            basis   = max(ranks, key=ranks.get)

            # 충당금
            prov_rate = PROVISION_RATES[cls]
            req_prov  = round(ead * prov_rate, 2)
            ex_prov   = round(req_prov * random.uniform(0.7, 1.0), 2)
            prov_gap  = round(req_prov - ex_prov, 2)

            class_rows.append((
                uid(), fid, cid, fmt(bd), cls, prev_class,
                dpd, pd_cls, ews_cls, basis,
                ead, prov_rate, req_prov, ex_prov, prov_gap,
                "SYSTEM",
            ))

            # ECL: SICR 판별
            sicr = False
            sicr_reasons = []
            if prev_ecl is not None:
                if pd_curr >= pd_base * 2:
                    sicr = True; sicr_reasons.append("PD_DOUBLED")
            if ews_score < 55:
                sicr = True; sicr_reasons.append("EWS_WATCH")
            if dpd >= 30:
                sicr = True; sicr_reasons.append("DPD_30")

            if dpd >= 90 or pd_curr >= 0.20:
                stage = 3
            elif sicr:
                stage = 2
            else:
                stage = 1

            # 잔존기간 (간단 추정)
            remaining_months = max(1, 36 - i * 3)

            # ECL 산출
            macro = random.uniform(0.95, 1.15)
            if stage == 1:
                ecl_base = pd_curr * lgd * ead * 0.97
            elif stage == 2:
                # 단순 lifetime ECL
                r_monthly = 0.005
                pd_monthly = 1 - (1 - min(pd_curr, 0.99)) ** (1/12)
                ecl_base = 0.0
                surv = 1.0
                for t in range(1, remaining_months + 1):
                    ecl_base += pd_monthly * surv * lgd * ead / (1 + r_monthly) ** t
                    surv *= (1 - pd_monthly)
            else:
                expected_recovery = ead * (1 - lgd)
                r_monthly = 0.005
                recovery_months = 24
                pv_recovery = sum(
                    (expected_recovery / recovery_months) / (1 + r_monthly) ** t
                    for t in range(1, recovery_months + 1)
                )
                ecl_base = max(ead - pv_recovery, 0)

            ecl_final = round(ecl_base * macro, 2)
            ecl_change = round(ecl_final - (prev_ecl or 0), 2)

            ecl_rows.append((
                uid(), fid, cid, fmt(bd), stage,
                1 if sicr else 0, ",".join(sicr_reasons),
                round(pd_base, 6), round(pd_curr, 6), lgd, ead, remaining_months,
                round(ecl_base, 2), round(macro, 4), ecl_final,
                prev_ecl, ecl_change,
                ex_prov, round(ecl_final - ex_prov, 2),
            ))

            prev_class = cls
            prev_ecl   = ecl_final

    # 배치 INSERT
    print(f"  자산건전성 분류 {len(class_rows)}건 저장 중...")
    cur.executemany("""
        INSERT OR IGNORE INTO asset_classification
            (class_id, facility_id, customer_id, base_date,
             classification, prev_class,
             dpd, pd_based_class, ews_based_class, final_class_basis,
             exposure_at_class, provision_rate,
             required_provision, existing_provision, provision_gap,
             classified_by)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, class_rows)
    conn.commit()

    print(f"  ECL 산출 {len(ecl_rows)}건 저장 중...")
    cur.executemany("""
        INSERT OR IGNORE INTO ecl_calculation
            (ecl_id, facility_id, customer_id, calc_date,
             stage, sicr_triggered, sicr_reason,
             pd_original, pd_current, lgd, ead, remaining_tenor_months,
             ecl_base, macro_adj_factor, ecl_final,
             prev_ecl, ecl_change,
             existing_provision, provision_gap)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, ecl_rows)
    conn.commit()

    return len(class_rows), len(ecl_rows)


# ------------------------------------------------------------------ #
# 연체 레코드 + 추심 활동 생성
# ------------------------------------------------------------------ #

def generate_delinquency(conn: sqlite3.Connection):
    cur = conn.cursor()

    # 연체 대상 여신 - 표본 수를 목표 연체율로 정한다.
    # 종전에는 '분류가 NORMAL 이 아닌' 여신 200건을 그대로 연체로 만들었다.
    # 그 집합에는 EWS·PD 때문에 요주의가 된 정상이행 여신이 대부분이라
    # 1개월 이상 연체율이 12%를 넘었다(실제 기업대출 0.84%).
    total_active = cur.execute(
        "SELECT COUNT(*) FROM facility WHERE status = 'ACTIVE'"
    ).fetchone()[0]
    target_n = max(1, round(total_active * (DELINQUENCY_RATE_1M + DELINQUENCY_RATE_SHORT)))

    facilities = cur.execute("""
        SELECT f.facility_id, f.customer_id, f.outstanding_amount, f.facility_type
        FROM facility f
        WHERE f.status = 'ACTIVE'
        ORDER BY RANDOM()
        LIMIT :n
    """, {"n": target_n}).fetchall()

    print(f"  연체 대상 여신: {len(facilities)}건")

    OFFICERS = ["김여신", "이심사", "박관리", "최회수", "정담당"]
    ACT_TYPES = ["CALL", "SMS", "EMAIL", "LETTER", "VISIT", "LEGAL_NOTICE"]
    RESULTS   = ["REACHED", "NO_ANSWER", "PROMISE_TO_PAY", "REFUSED", "LEFT_MESSAGE"]

    delinquency_rows  = []
    activity_rows     = []
    facility_updates  = []

    today = AS_OF_DATE   # 실행일이 아니라 시스템 기준일을 쓴다

    # 연체는 단기에 몰리고 장기로 갈수록 급감한다. 표본 중 1개월 미만 비중은
    # DELINQUENCY_RATE_SHORT / (SHORT + 1M) 로 잡고, 나머지를 sample_dpd() 로 뽑는다.
    short_share = DELINQUENCY_RATE_SHORT / (DELINQUENCY_RATE_SHORT + DELINQUENCY_RATE_1M)

    def pick_dpd():
        if random.random() < short_share:
            return random.randint(1, DPD_PRECAUTIONARY - 1)   # 건전성상 정상
        return sample_dpd()

    for fac in facilities:
        fid       = fac[0]
        cid       = fac[1]
        exposure  = float(fac[2] or 0)

        # 연체 1건 생성
        dpd         = pick_dpd()
        overdue_date = today - timedelta(days=dpd)
        overdue_pct  = random.uniform(0.05, 0.20)
        overdue_amt  = round(exposure * overdue_pct, 2)
        stage        = delinquency_stage(dpd)

        # 해결 여부 (30% 확률)
        resolved = random.random() < 0.30
        resolved_date   = None
        resolved_amount = None
        resolution_type = None
        status          = "OPEN"

        if resolved:
            resolved_date   = fmt(overdue_date + timedelta(days=random.randint(5, 30)))
            resolved_amount = round(overdue_amt * random.uniform(0.6, 1.0), 2)
            resolution_type = random.choice(["PAID", "RESTRUCTURED", "WORKOUT"])
            status          = "RESOLVED"
            dpd             = 0

        did = uid()
        delinquency_rows.append((
            did, fid, cid,
            fmt(overdue_date), overdue_amt,
            random.choice(["PRINCIPAL", "INTEREST", "BOTH"]),
            dpd, resolved_date, resolved_amount, resolution_type,
            status, stage if not resolved else None,
            random.choice(OFFICERS),
        ))

        # 추심 활동 2~5건
        num_acts = random.randint(2, 5)
        for j in range(num_acts):
            act_date = overdue_date + timedelta(days=j * random.randint(3, 10))
            if act_date > today:
                break
            atype  = random.choice(ACT_TYPES)
            result = random.choice(RESULTS)
            promised_date   = None
            promised_amount = None
            if result == "PROMISE_TO_PAY":
                promised_date   = fmt(act_date + timedelta(days=random.randint(3, 14)))
                promised_amount = round(overdue_amt * random.uniform(0.3, 1.0), 2)

            activity_rows.append((
                uid(), did, fid,
                fmt(act_date), atype, result,
                promised_date, promised_amount,
                None, random.choice(OFFICERS),
            ))

        # facility 업데이트
        # 상한을 200으로 묶으면 dpd 가 200을 넘는 순간 빈 범위가 되어 터진다.
        max_dpd = random.randint(dpd, dpd + 30)
        facility_updates.append((dpd, max_dpd, fmt(overdue_date), fid))

    print(f"  연체 레코드 {len(delinquency_rows)}건 저장 중...")
    cur.executemany("""
        INSERT OR IGNORE INTO delinquency_record
            (delinquency_id, facility_id, customer_id,
             overdue_date, overdue_amount, overdue_type,
             dpd, resolved_date, resolved_amount, resolution_type,
             status, delinquency_stage, assigned_officer)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, delinquency_rows)
    conn.commit()

    print(f"  추심 활동 {len(activity_rows)}건 저장 중...")
    cur.executemany("""
        INSERT OR IGNORE INTO collection_activity
            (activity_id, delinquency_id, facility_id,
             activity_date, activity_type, contact_result,
             promised_date, promised_amount,
             notes, officer)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, activity_rows)
    conn.commit()

    print(f"  facility DPD 갱신 {len(facility_updates)}건...")
    cur.executemany("""
        UPDATE facility
        SET dpd = ?, max_dpd_12m = ?, first_delinquency_date = ?
        WHERE facility_id = ?
    """, facility_updates)
    conn.commit()

    return len(delinquency_rows), len(activity_rows)


# ------------------------------------------------------------------ #
# facility classification 동기화
# ------------------------------------------------------------------ #

def sync_facility_classification(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("""
        UPDATE facility SET classification = (
            SELECT ac.classification
            FROM asset_classification ac
            JOIN (
                SELECT facility_id, MAX(base_date) AS latest
                FROM asset_classification GROUP BY facility_id
            ) mx ON ac.facility_id = mx.facility_id AND ac.base_date = mx.latest
            WHERE ac.facility_id = facility.facility_id
        )
        WHERE EXISTS (
            SELECT 1 FROM asset_classification
            WHERE facility_id = facility.facility_id
        )
    """)
    conn.commit()
    print(f"  facility.classification 동기화 완료")


# ------------------------------------------------------------------ #
# 메인
# ------------------------------------------------------------------ #

def main():
    print("=" * 60)
    print("Phase 2 시드 데이터 생성")
    print("=" * 60)
    print(f"DB: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)

    print("\n[1] 스키마 적용 중...")
    apply_schema(conn)
    print("  완료")

    # 재실행 가능하도록 기존 생성분을 비운다. 종전에는 지우지 않아 두 번 돌리면
    # 같은 여신·같은 기준일의 분류/ECL 행이 그대로 쌓였다.
    print("  기존 Phase 2 데이터 삭제...")
    cur = conn.cursor()
    for t in ("collection_activity", "delinquency_record",
              "ecl_calculation", "asset_classification"):
        try:
            cur.execute(f"DELETE FROM {t}")
        except Exception as e:
            print(f"    [WARN] {t}: {str(e)[:80]}")
    # facility 의 연체 컬럼도 되돌린다. 이번 실행에서 연체로 뽑히지 않은 여신에
    # 지난 실행의 DPD 가 남아 있으면 연체율이 실행할수록 누적된다.
    try:
        cur.execute("""
            UPDATE facility
               SET dpd = 0, max_dpd_12m = 0,
                   first_delinquency_date = NULL, classification = 'NORMAL'
        """)
    except Exception as e:
        print(f"    [WARN] facility 연체 컬럼 초기화: {str(e)[:80]}")
    conn.commit()

    print("\n[2] 자산건전성 분류 + ECL 생성 중...")
    n_class, n_ecl = generate_classification_and_ecl(conn)
    print(f"  완료: 분류 {n_class}건, ECL {n_ecl}건")

    print("\n[3] 연체 레코드 + 추심 활동 생성 중...")
    n_delinq, n_act = generate_delinquency(conn)
    print(f"  완료: 연체 {n_delinq}건, 추심 {n_act}건")

    print("\n[4] facility 분류 동기화...")
    sync_facility_classification(conn)

    conn.close()
    print("\n" + "=" * 60)
    print("Phase 2 데이터 생성 완료!")
    print(f"  자산건전성 분류 : {n_class:,}건")
    print(f"  ECL 산출        : {n_ecl:,}건")
    print(f"  연체 레코드      : {n_delinq:,}건")
    print(f"  추심 활동        : {n_act:,}건")
    print("=" * 60)


if __name__ == "__main__":
    main()
