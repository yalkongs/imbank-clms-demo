-- 인증·전결의 서버측 정본: 사용자 계정
-- 승인자·부서·전결권은 클라이언트 파라미터가 아니라 인증 사용자에서 결정한다
CREATE TABLE IF NOT EXISTS user_account (
    user_id        TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    dept           TEXT,
    approval_level TEXT NOT NULL,     -- STAFF / TEAM_LEAD / DEPT_HEAD / EXECUTIVE / COMMITTEE
    pin_hash       TEXT NOT NULL,     -- sha256(user_id:pin)
    active         INTEGER DEFAULT 1,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 데모 계정 (PoC: PIN 은 화면에 힌트로 공개된다)
INSERT OR IGNORE INTO user_account (user_id, name, dept, approval_level, pin_hash) VALUES
  ('kim.simsa',  '김심사', '여신심사부',  'STAFF',
   'ae5ff1072dfc96716ab4b7a4641dde487cc26a407795ffe0864cc91020e95ebd'),
  ('kim.yeosin', '김여신', '여신심사부',  'TEAM_LEAD',
   'd3c4d5ae8473266fa22f7cd59bc1c7b308653d263bf64568e08f4652f07eea32'),
  ('park.bujang','박부장', '여신심사부',  'DEPT_HEAD',
   '50295f8c10ca3506bd75e01f4287824fc5ba77c27a064c2ebffbe3809f3165c4'),
  ('lee.jeonmu', '이전무', '여신그룹',    'EXECUTIVE',
   '470157334a11050add65750885bb5e7dbcca6e731a05ec9332d495f018c0ee9c');
