from datetime import date
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "iM뱅크 CLMS Demo"
    DEBUG: bool = True
    DATABASE_URL: str = f"sqlite:///{Path(__file__).parent.parent.parent.parent}/database/imbank_demo.db"

    # 시스템 기준일 (as-of date)
    # 데모 데이터의 모든 시점 기준. 실행 시각(date.today())을 쓰면 날이 갈수록
    # 연체일수·잔존만기·기준월이 어긋나므로 고정 기준일을 단일 소스로 둔다.
    # 시드 데이터도 이 값을 기준으로 생성된다 (database/base_date.py 참조).
    AS_OF_DATE: date = date(2026, 7, 31)

    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173", "http://localhost:5174", "http://localhost:5175"]

    class Config:
        env_file = ".env"


settings = Settings()

# 자주 쓰는 파생 값
AS_OF_DATE = settings.AS_OF_DATE
AS_OF_MONTH = AS_OF_DATE.strftime("%Y-%m")          # 'YYYY-MM' — EWS 기준월
AS_OF_STR = AS_OF_DATE.strftime("%Y-%m-%d")


def as_of_months(n: int = 12) -> list:
    """기준월부터 거슬러 n개월치 'YYYY-MM' 목록 (오름차순)."""
    y, m = AS_OF_DATE.year, AS_OF_DATE.month
    out = []
    for i in range(n - 1, -1, -1):
        mm = m - i
        yy = y
        while mm <= 0:
            mm += 12
            yy -= 1
        out.append(f"{yy}-{mm:02d}")
    return out
