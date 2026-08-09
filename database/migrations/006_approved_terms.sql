-- 승인조건 영속화 - 승인금액·금리·기간을 신청 원장에 기록한다.
-- 종전에는 승인 API 응답에만 존재하고 어디에도 저장되지 않아
-- '1원 감액승인' 조작이 사실상 전액 승인이 되는 구멍이 있었다.

ALTER TABLE loan_application ADD COLUMN approved_amount REAL;
ALTER TABLE loan_application ADD COLUMN approved_rate REAL;
ALTER TABLE loan_application ADD COLUMN approved_tenor INTEGER;
