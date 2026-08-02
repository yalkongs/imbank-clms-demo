"""
시드 데이터 생성용 공통 기준일
==============================
백엔드(`backend/app/core/config.py`)의 AS_OF_DATE 와 반드시 같은 값이어야 한다.
시드가 만든 시점과 API 가 조회하는 기준월이 어긋나면 화면이 빈 값으로 나온다.

기준일을 바꿀 때는 이 파일과 config.py 두 곳을 함께 고치고 시드를 재생성한다.
"""

from datetime import date, timedelta

AS_OF_DATE = date(2026, 7, 31)
AS_OF_MONTH = AS_OF_DATE.strftime("%Y-%m")
AS_OF_STR = AS_OF_DATE.strftime("%Y-%m-%d")


def months_back(n: int = 12) -> list:
    """기준월부터 거슬러 n개월치 'YYYY-MM' 목록 (오름차순)."""
    y, m = AS_OF_DATE.year, AS_OF_DATE.month
    out = []
    for i in range(n - 1, -1, -1):
        mm, yy = m - i, y
        while mm <= 0:
            mm += 12
            yy -= 1
        out.append(f"{yy}-{mm:02d}")
    return out


def month_starts(n: int = 12) -> list:
    """기준월부터 거슬러 n개월치 각 월 1일 date 목록 (오름차순)."""
    return [date(int(s[:4]), int(s[5:]), 1) for s in months_back(n)]


def month_ends(n: int = 12) -> list:
    """기준월부터 거슬러 n개월치 각 월 말일 date 목록 (오름차순).

    자본비율처럼 월말 스냅샷으로 쌓이는 지표에 쓴다. 30일씩 더하는 방식은
    달마다 날짜가 밀려 '2026-02-07' 같은 어정쩡한 기준일이 나온다.
    """
    out = []
    for s in months_back(n):
        y, m = int(s[:4]), int(s[5:])
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        out.append(date(ny, nm, 1) - timedelta(days=1))
    return out


def days_before(days: int) -> date:
    """기준일에서 days 일 전."""
    return AS_OF_DATE - timedelta(days=days)
