"""
CSV 내보내기 API
================
은행 실무의 공용어는 Excel 이다. 화면으로 보는 것과 "들고 갈 수 있는 것"의 차이가
PoC 의 체감 유용성을 좌우하므로, 주요 목록·보고서를 CSV 로 내려준다.
Excel 한글 호환을 위해 UTF-8 BOM(utf-8-sig)을 붙인다.
"""
import csv
import io
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..core.config import AS_OF_STR

router = APIRouter(prefix="/api/export", tags=["Export"])

# 내보내기 정의 - name: (파일명, 헤더, 쿼리)
EXPORTS = {
    "facilities": (
        "여신목록",
        ["여신ID", "고객명", "업종", "여신유형", "약정액", "잔액", "DPD", "건전성분류"],
        """SELECT f.facility_id, c.customer_name, c.industry_name, f.facility_type,
                  f.approved_amount, f.outstanding_amount,
                  COALESCE(f.dpd, 0), COALESCE(f.classification, 'NORMAL')
           FROM facility f JOIN customer c ON f.customer_id = c.customer_id
           WHERE f.status = 'ACTIVE' ORDER BY f.outstanding_amount DESC""",
    ),
    "classification": (
        "자산건전성분류",
        ["여신ID", "고객명", "기준일", "분류", "DPD", "익스포저", "적립률", "필요충당금", "부족액"],
        """SELECT ac.facility_id, c.customer_name, ac.base_date, ac.classification,
                  ac.dpd, ac.exposure_at_class, ac.provision_rate,
                  ac.required_provision, ac.provision_gap
           FROM asset_classification ac
           JOIN customer c ON ac.customer_id = c.customer_id
           JOIN (SELECT facility_id, MAX(base_date) latest
                 FROM asset_classification GROUP BY facility_id) mx
             ON ac.facility_id = mx.facility_id AND ac.base_date = mx.latest
           ORDER BY ac.exposure_at_class DESC""",
    ),
    "pf-projects": (
        "PF사업장",
        ["사업장ID", "사업장명", "유형", "지역", "시행사", "시공사",
         "익스포저", "자기자본비율", "공정률", "분양률", "상태"],
        """SELECT project_id, project_name, project_type, region, developer_name,
                  constructor_name, exposure, equity_ratio, progress_rate,
                  presale_rate, status
           FROM pf_project WHERE status != 'COMPLETED' ORDER BY exposure DESC""",
    ),
    "delinquency": (
        "연체현황",
        ["연체ID", "여신ID", "고객명", "연체일수", "연체단계", "연체금액", "잔액"],
        """SELECT d.delinquency_id, d.facility_id, c.customer_name, d.dpd,
                  d.delinquency_stage, d.overdue_amount, f.outstanding_amount
           FROM delinquency_record d
           JOIN customer c ON d.customer_id = c.customer_id
           JOIN facility f ON d.facility_id = f.facility_id
           WHERE d.status = 'OPEN' ORDER BY d.dpd DESC""",
    ),
    "inclusive": (
        "포용금융세그먼트",
        ["고객ID", "고객명", "규모", "최신등급", "지역", "여신잔액", "DPD"],
        """SELECT c.customer_id, c.customer_name, c.size_category,
                  g.final_grade, c.region,
                  COALESCE(SUM(f.outstanding_amount), 0), MAX(COALESCE(f.dpd, 0))
           FROM customer c
           LEFT JOIN facility f ON c.customer_id = f.customer_id AND f.status = 'ACTIVE'
           LEFT JOIN (SELECT customer_id, final_grade,
                             ROW_NUMBER() OVER (PARTITION BY customer_id
                                                ORDER BY rating_date DESC) rn
                      FROM credit_rating_result) g
             ON c.customer_id = g.customer_id AND g.rn = 1
           WHERE c.size_category = 'SOHO'
              OR g.final_grade IN ('BBB+','BBB','BBB-','BB+','BB','BB-','B+','B','B-')
           GROUP BY c.customer_id ORDER BY 6 DESC""",
    ),
}


@router.get("/{name}.csv")
def export_csv(name: str, db: Session = Depends(get_db)):
    if name not in EXPORTS:
        raise HTTPException(404, f"지원하지 않는 내보내기: {name}")
    label, headers, query = EXPORTS[name]

    rows = db.execute(text(query)).fetchall()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        w.writerow(["" if v is None else v for v in r])

    filename = f"{label}_{AS_OF_STR}.csv"
    return Response(
        content="﻿" + buf.getvalue(),          # BOM - Excel 한글 인코딩
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )
