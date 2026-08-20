-- A3 (2026-08-21 외부감사 #4): SICR 최초 인식 기준점의 불변 스냅샷
-- IFRS9 5.5.9는 보고일 부도위험을 '최초 인식일' 부도위험과 비교하도록
-- 요구한다. 종전에는 최초 PD를 현재 PD×0.7 로 사후 생성해(상승배율이
-- 항상 1.43배) PD 기반 SICR 트리거(2배)가 구조적으로 작동하지 않았다.
-- 이 테이블이 시설별 최초 인식 시점의 PD·등급 정본이다. source 로
-- 출처(백필/최초계산)를 구분해 추정 기준점임을 숨기지 않는다.
CREATE TABLE IF NOT EXISTS facility_origination_risk (
    facility_id   TEXT PRIMARY KEY,
    orig_date     DATE,
    orig_grade    TEXT,
    orig_pd       REAL,
    model_version TEXT,
    source        TEXT NOT NULL DEFAULT 'ORIGINATION',
    -- ORIGINATION        : 승인·실행 시점 기록 (정식)
    -- BACKFILL_RISK_PARAM: 승인 시점 risk_parameter TTC PD 백필
    -- BACKFILL_FIRST_ECL : 최초 ECL 계산의 pd_original 백필
    -- FIRST_CALC_CURRENT : 이력 전무 - 최초 계산 시점 현재 PD 를 기준점으로 고정
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 백필 1순위: 승인 시점 risk_parameter 의 TTC PD (신청 연계)
INSERT OR IGNORE INTO facility_origination_risk
    (facility_id, orig_date, orig_pd, source)
SELECT f.facility_id, f.contract_date, MAX(rp.ttc_pd), 'BACKFILL_RISK_PARAM'
FROM facility f
JOIN risk_parameter rp ON f.application_id = rp.application_id
WHERE rp.ttc_pd IS NOT NULL
GROUP BY f.facility_id;

-- 백필 2순위: 최초 ECL 계산 이력의 pd_original
INSERT OR IGNORE INTO facility_origination_risk
    (facility_id, orig_date, orig_pd, source)
SELECT e.facility_id, MIN(e.calc_date),
       (SELECT e2.pd_original FROM ecl_calculation e2
        WHERE e2.facility_id = e.facility_id
        ORDER BY e2.calc_date ASC LIMIT 1),
       'BACKFILL_FIRST_ECL'
FROM ecl_calculation e
GROUP BY e.facility_id;

-- 등급 백필: 해당 고객의 최초 신용평가 등급 (계약 시점 근사)
UPDATE facility_origination_risk
SET orig_grade = (
    SELECT crr.final_grade
    FROM facility f
    JOIN credit_rating_result crr ON f.customer_id = crr.customer_id
    WHERE f.facility_id = facility_origination_risk.facility_id
    ORDER BY crr.rating_date ASC LIMIT 1
)
WHERE orig_grade IS NULL;
