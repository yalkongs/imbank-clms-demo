-- EWS 감사 후속 (2026-08-22 codex 감사 A4): 종합점수의 적용 규칙 provenance
-- 가중치 발효로 점수가 재계산될 때 어떤 규칙 버전으로 언제 계산됐는지를
-- 점수 행에 봉인한다. (PoC 타협: 행을 새 스냅샷으로 적재하는 대신 제자리
-- 갱신하되 근거를 기록 - 감사로그와 함께 계산 재현이 가능해진다)
ALTER TABLE ews_composite_score ADD COLUMN applied_rule_id TEXT;
ALTER TABLE ews_composite_score ADD COLUMN computed_at TIMESTAMP;
