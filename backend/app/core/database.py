from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import os

# CLMS_DB_PATH 환경변수로 오버라이드 가능 (테스트 DB 격리용)
DATABASE_PATH = Path(
    os.getenv("CLMS_DB_PATH")
    or Path(__file__).parent.parent.parent.parent / "database" / "imbank_demo.db"
)
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# 테스트는 CLMS_DB_POOL=null 로 풀 없이 연결한다 - 테스트가 여는 세션이
# 늘어나면 QueuePool(5+10) 이 고갈돼 뒤쪽 테스트가 TimeoutError 로 죽는다.
_pool_kwargs = {}
if os.getenv("CLMS_DB_POOL") == "null":
    from sqlalchemy.pool import NullPool
    _pool_kwargs["poolclass"] = NullPool

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    **_pool_kwargs,
)


@event.listens_for(engine, "connect")
def _enable_foreign_keys(dbapi_conn, _record):
    """SQLite 는 연결마다 FK 검사를 켜야 한다 - 고아 참조 데이터 유입 방지
    (제3자 리뷰 지적: 미활성 상태에서 group_guarantee 고아 238건이 허용됐음)"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
