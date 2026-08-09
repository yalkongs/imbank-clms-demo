-- Roll Rate 전이 이력 - 연체 단계의 월별 스냅샷
-- delinquency_record 는 '건' 단위(현재 상태)라 전이 관측이 불가능했다.
-- 다른 화면 집계(대시보드 OPEN 필터, vintage LEFT JOIN, 여신별 이력)를
-- 오염시키지 않도록 별도 테이블로 분리한다.

CREATE TABLE IF NOT EXISTS delinquency_stage_history (
    history_id    TEXT PRIMARY KEY,
    facility_id   TEXT NOT NULL REFERENCES facility(facility_id),
    episode_id    TEXT NOT NULL,          -- 연체 에피소드 단위 (같은 여신의 재연체 구분)
    seq           INTEGER NOT NULL,       -- 에피소드 내 월 순번 (0부터)
    snapshot_date DATE NOT NULL,
    stage         TEXT NOT NULL           -- EARLY/MID/LATE/NPL/WRITEOFF/CURED
);

CREATE INDEX IF NOT EXISTS idx_dsh_episode
    ON delinquency_stage_history (episode_id, seq);
CREATE INDEX IF NOT EXISTS idx_dsh_facility
    ON delinquency_stage_history (facility_id);
