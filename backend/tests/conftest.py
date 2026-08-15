"""테스트 DB 격리.

승인·결재 회귀 테스트는 실제로 신청을 승인하므로 DB 를 변형시킨다. 종전에는
그 대상이 배포 자산인 `database/imbank_demo.db` 자체였고, 결과가 두 가지였다.

1. 테스트를 돌릴 때마다 데모 DB 가 변경돼 커밋에 섞여 들어갔다.
2. `_find_pending_app` 이 찾는 '심사중 + 결재이력 없음' 표본이 실행마다 소진돼,
   테스트가 실패가 아니라 **조용히 skip** 으로 바뀌었다. 실제로 승인 경로
   회귀 테스트 8건이 아무것도 검증하지 않는 상태로 통과하고 있었다.

그래서 세션 시작 시 데모 DB 를 임시 사본으로 복사하고 `CLMS_DB_PATH`
(`app/core/database.py` 가 이미 지원하는 오버라이드)로 앱을 그쪽에 붙인다.
앱 import 보다 먼저 실행돼야 하므로 모듈 최상단에서 처리하고, 이 파일은
앱 모듈을 import 하지 않는다.
"""
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SOURCE_DB = _REPO_ROOT / "database" / "imbank_demo.db"

# 사본은 .db 본체만 복사한다 - -wal/-shm 사이드카를 함께 옮기면 사본이 깨진다.
_TEST_DB = Path(tempfile.mkdtemp(prefix="clms-test-")) / "imbank_demo.db"
shutil.copy(_SOURCE_DB, _TEST_DB)
os.environ["CLMS_DB_PATH"] = str(_TEST_DB)


# 결재 회귀 테스트가 소비할 '심사중' 표본을 사본에만 보충한다.
# 시드에는 팀장 전결(50억) 안에 드는 미결재 심사중 건이 1건뿐이라, 보충하지
# 않으면 승인 경로 테스트가 표본 부족으로 다시 skip 된다.
_PENDING_FIXTURES = 8
_FIXTURE_AMOUNT = 30e8          # 팀장 전결 한도(50억) 이내
_FIXTURE_PREFIX = "TEST_PEND_"


def _seed_pending_applications() -> None:
    con = sqlite3.connect(_TEST_DB)
    con.execute("PRAGMA foreign_keys=ON")
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info(loan_application)")]
        # 종속 데이터(고객·재무제표·신용등급)가 갖춰진 실제 심사중 건을 원본으로
        # 삼아 복제한다. 스냅샷 봉인은 customer_id 기준으로 읽으므로 신청 행만
        # 복제해도 승인 경로 전체가 성립한다.
        src = con.execute(
            f"SELECT {', '.join(cols)} FROM loan_application "
            "WHERE status = 'REVIEWING' AND current_stage NOT IN ('RECEIVED') "
            "ORDER BY requested_amount LIMIT 1"
        ).fetchone()
        if src is None:
            return
        row = dict(zip(cols, src))
        placeholders = ", ".join(f":{c}" for c in cols)
        for i in range(_PENDING_FIXTURES):
            new = dict(row)
            new["application_id"] = f"{_FIXTURE_PREFIX}{i:02d}"
            new["status"] = "REVIEWING"
            new["current_stage"] = "CREDIT_REVIEW"
            new["requested_amount"] = _FIXTURE_AMOUNT
            for c in ("approved_amount", "approved_rate", "approved_tenor"):
                if c in new:
                    new[c] = None
            con.execute(
                f"INSERT OR REPLACE INTO loan_application ({', '.join(cols)}) "
                f"VALUES ({placeholders})", new)
        con.commit()
    finally:
        con.close()


_seed_pending_applications()
