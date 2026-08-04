"""
전역 검색 API - 커맨드 팔레트(Cmd+K)용
======================================
고객 1,010명·여신 1,200건·PF 사업장 40곳을 페이지별 필터 없이 한 입력으로 찾는다.
결과에 이동 경로(route)를 함께 내려 프론트가 바로 네비게이션할 수 있게 한다.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.get("")
def global_search(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    like = f"%{q}%"
    results = []

    # 고객
    for r in db.execute(text("""
        SELECT customer_id, customer_name, industry_name FROM customer
        WHERE customer_name LIKE :q OR customer_id LIKE :q
        ORDER BY customer_name LIMIT 6
    """), {"q": like}):
        results.append({
            "type": "customer", "type_label": "고객",
            "id": r[0], "title": r[1], "subtitle": f"{r[0]} · {r[2]}",
            "route": f"/customer-browser?q={r[1]}",
        })

    # 여신
    for r in db.execute(text("""
        SELECT f.facility_id, c.customer_name, f.facility_type, f.outstanding_amount
        FROM facility f JOIN customer c ON f.customer_id = c.customer_id
        WHERE f.facility_id LIKE :q AND f.status = 'ACTIVE'
        LIMIT 4
    """), {"q": like}):
        results.append({
            "type": "facility", "type_label": "여신",
            "id": r[0], "title": r[0],
            "subtitle": f"{r[1]} · {r[2]} · {r[3]/1e8:,.0f}억",
            "route": f"/customer-browser?q={r[1]}",
        })

    # PF 사업장
    for r in db.execute(text("""
        SELECT project_id, project_name, region FROM pf_project
        WHERE project_name LIKE :q OR developer_name LIKE :q OR constructor_name LIKE :q
        LIMIT 4
    """), {"q": like}):
        results.append({
            "type": "pf", "type_label": "PF 사업장",
            "id": r[0], "title": r[1], "subtitle": r[0],
            "route": f"/pf-monitoring?project={r[0]}",
        })

    return {"query": q, "results": results[:12]}
