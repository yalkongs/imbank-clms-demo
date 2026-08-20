-- C2 (2026-08-21 외부감사 #9): 상환방식 구조화
-- DSCR 원금상환액이 '잔액의 15%/년' 일률 가정이었다. 만기일시 여신은
-- 만기 전 원금상환이 0인데 연 15%로, 단기 분할상환은 과소로 계산됐다.
-- 시설 유형에서 상환방식을 도출해 저장한다 (백필 규칙은 유형 관행 근사):
--   AMORTIZING: 시설자금·TERM (분할상환 관행)
--   BULLET    : PF·무역·운전·한도성·보증 (만기일시 / 회전성)
ALTER TABLE facility ADD COLUMN repayment_type TEXT;

UPDATE facility
SET repayment_type = CASE
    WHEN facility_type IN ('FACILITY', 'TERM', '기업시설자금대출') THEN 'AMORTIZING'
    ELSE 'BULLET'
END
WHERE repayment_type IS NULL;
