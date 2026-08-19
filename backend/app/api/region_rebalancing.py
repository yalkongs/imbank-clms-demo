"""
지역 편중 리스크 · 리밸런싱 관제 API (P3)
==========================================
iM뱅크만이 가진 긴장 구조를 다룬다: 시중은행 전환 인가 부대조건(본점 대구
유지)·지역재투자 최우수 등급이 요구하는 **지역 공급 의무**와, 대구·경북
집중(공시 기준 여신 66~72%)이 만드는 **편중 리스크**를 한 화면에서 관리한다.

전략 방향(공시·보도): 대구경북 중소기업 중심 → 전국 우량기업·수도권 제조업
리밸런싱. PRM 기반 기업여신 +11.6% (2025.1Q).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db

router = APIRouter(prefix="/api/region-rebalancing", tags=["Region Rebalancing"])

REGION_LABEL = {
    "DAEGU_GB": "대구·경북",
    "CAPITAL":  "수도권",
    "BUSAN_GN": "부산·경남",
}

# 공시·보도 벤치마크 (지주/은행·보도 기준 병기용)
BENCHMARK = {
    "disclosed_daegu_share": "66~72%",   # 대구경북 여신 비중 (보도 기준별 상이)
    "reinvestment_grade": "최우수 (2024·2025 연속)",   # 금융위 지역재투자 평가
    "license_condition": "본점 대구 유지 (시중은행 전환 인가 부대조건)",
    "strategy": "전국 우량기업·수도권 제조업 리밸런싱 (PRM 여신 +11.6%)",
    # 관리 밴드 (내부 정책 가정치 - 화면에 '가정' 표기)
    "reinvestment_floor": 45.0,   # 지역 공급 의무 하한 (가정)
    "concentration_cap": 60.0,    # 편중 리스크 상한 (가정)
}

NPL_CLASSES = "('SUBSTANDARD','DOUBTFUL','ESTIMATED_LOSS')"


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    """지역별 잔액·건전성 + 신규취급 추이 + 양면 게이지 데이터"""
    rows = db.execute(text(f"""
        SELECT c.region,
               COUNT(DISTINCT c.customer_id)                  AS customers,
               SUM(f.outstanding_amount)                      AS exposure,
               SUM(CASE WHEN f.dpd > 0 THEN f.outstanding_amount ELSE 0 END) AS overdue_exp,
               SUM(CASE WHEN f.classification IN {NPL_CLASSES}
                        THEN f.outstanding_amount ELSE 0 END) AS npl_exp
        FROM customer c
        JOIN facility f ON c.customer_id = f.customer_id
        WHERE f.status IN ('ACTIVE', 'FROZEN')
        GROUP BY c.region
    """)).fetchall()

    total_exp = sum(float(r[2] or 0) for r in rows) or 1.0
    regions = []
    hhi = 0.0
    for r in rows:
        exp = float(r[2] or 0)
        share = exp / total_exp * 100
        hhi += share ** 2
        regions.append({
            "region": r[0],
            "label": REGION_LABEL.get(r[0], r[0]),
            "customers": r[1],
            "exposure_eok": round(exp / 1e8, 0),
            "share": round(share, 1),
            "delinquency_rate": round(float(r[3] or 0) / exp * 100, 2) if exp else 0,
            "npl_ratio": round(float(r[4] or 0) / exp * 100, 2) if exp else 0,
        })
    regions.sort(key=lambda x: -x["exposure_eok"])

    # 신규취급 지역 구성 추이 (계약일 기준 12개월) - 리밸런싱 진척의 실측
    trend_rows = db.execute(text("""
        SELECT substr(f.contract_date, 1, 7) AS ym, c.region,
               SUM(f.approved_amount) AS amt
        FROM facility f
        JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.contract_date >= date((SELECT MAX(contract_date) FROM facility), '-12 months')
        GROUP BY ym, c.region ORDER BY ym
    """)).fetchall()
    trend_map: dict = {}
    for ym, region, amt in trend_rows:
        trend_map.setdefault(ym, {})[region] = float(amt or 0)
    new_biz_trend = []
    for ym in sorted(trend_map.keys()):
        vals = trend_map[ym]
        tot = sum(vals.values()) or 1.0
        new_biz_trend.append({
            "month": ym,
            "daegu_share": round(vals.get("DAEGU_GB", 0) / tot * 100, 1),
            "capital_share": round(vals.get("CAPITAL", 0) / tot * 100, 1),
            "busan_share": round(vals.get("BUSAN_GN", 0) / tot * 100, 1),
            "total_eok": round(tot / 1e8, 0),
        })

    daegu = next((r for r in regions if r["region"] == "DAEGU_GB"), None)
    daegu_share = daegu["share"] if daegu else 0

    return {
        "benchmark": BENCHMARK,
        "regions": regions,
        "region_hhi": round(hhi, 0),
        "daegu_share": daegu_share,
        "gauge": {
            # 같은 지표(대구경북 비중)가 두 제약 사이에 있어야 한다:
            # 지역재투자 하한(의무) <= 비중 <= 편중 상한(건전성)
            "value": daegu_share,
            "reinvestment_floor": BENCHMARK["reinvestment_floor"],
            "concentration_cap": BENCHMARK["concentration_cap"],
            "in_band": BENCHMARK["reinvestment_floor"] <= daegu_share <= BENCHMARK["concentration_cap"],
        },
        "new_business_trend": new_biz_trend,
    }


@router.get("/industry-matrix")
def get_industry_matrix(db: Session = Depends(get_db)):
    """산업×지역 교차 매트릭스 - 익스포저와 연체율로 리밸런싱 방향을 짚는다"""
    rows = db.execute(text("""
        SELECT c.industry_name, c.region,
               SUM(f.outstanding_amount) AS exposure,
               SUM(CASE WHEN f.dpd > 0 THEN f.outstanding_amount ELSE 0 END) AS overdue
        FROM customer c
        JOIN facility f ON c.customer_id = f.customer_id
        WHERE f.status IN ('ACTIVE', 'FROZEN')
        GROUP BY c.industry_name, c.region
    """)).fetchall()

    by_industry: dict = {}
    for ind, region, exp, ov in rows:
        cell = by_industry.setdefault(ind, {})
        e = float(exp or 0)
        cell[region] = {
            "exposure_eok": round(e / 1e8, 0),
            "delinquency_rate": round(float(ov or 0) / e * 100, 2) if e else 0,
        }

    matrix = []
    for ind, cells in by_industry.items():
        total = sum(v["exposure_eok"] for v in cells.values())
        matrix.append({
            "industry": ind,
            "total_eok": total,
            "cells": {r: cells.get(r, {"exposure_eok": 0, "delinquency_rate": 0})
                      for r in REGION_LABEL},
        })
    matrix.sort(key=lambda x: -x["total_eok"])

    return {"regions": REGION_LABEL, "matrix": matrix}
