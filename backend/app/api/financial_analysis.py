"""
재무제표 분석 API
=================
3개년 재무비율 자동 산출, DSCR 기반 상환능력 검증, Altman Z-Score, 동업종 벤치마크
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import date
from ..core.database import get_db
from ..core.config import AS_OF_DATE
from ..core.auth import get_current_user, User
from ..core.audit import record_audit
from ..services.calculations import (
    calculate_financial_ratios, calculate_dscr,
    calculate_altman_z, FINANCIAL_BENCHMARKS
)

router = APIRouter(prefix="/api/financial", tags=["Financial Analysis"])

# ============================================================
# 재무비율 판정 기준 레이블
# ============================================================
RATIO_META = {
    'debt_ratio':      {'name': '부채비율',    'unit': '%',  'benchmark': 200.0,  'op': 'LE'},
    'current_ratio':   {'name': '유동비율',    'unit': '%',  'benchmark': 100.0,  'op': 'GE'},
    'ier':             {'name': '이자보상배율', 'unit': '배', 'benchmark': 1.5,    'op': 'GE'},
    'debt_dependency': {'name': '차입금의존도', 'unit': '%',  'benchmark': 50.0,   'op': 'LE'},
    'dscr':            {'name': 'DSCR',        'unit': '배', 'benchmark': 1.25,   'op': 'GE'},
    'op_margin':       {'name': '영업이익률',   'unit': '%',  'benchmark': 0.0,    'op': 'GE'},
    'roa':             {'name': 'ROA',          'unit': '%',  'benchmark': None,   'op': None},
    'roe':             {'name': 'ROE',          'unit': '%',  'benchmark': None,   'op': None},
    'revenue_growth':  {'name': '매출성장률',   'unit': '%',  'benchmark': None,   'op': None},
    'op_growth':       {'name': '영업이익성장률', 'unit': '%', 'benchmark': None,  'op': None},
    'altman_z':        {'name': 'Altman Z\'',  'unit': '',   'benchmark': 1.23,   'op': 'GE'},
}


def _row_to_stmt(row) -> dict:
    """DB 행 → 재무제표 dict 변환"""
    keys = [
        'stmt_id', 'customer_id', 'fiscal_year', 'stmt_type',
        'revenue', 'operating_profit', 'ebitda', 'interest_expense', 'net_profit',
        'total_assets', 'current_assets', 'total_debt', 'current_debt',
        'total_borrowing', 'equity', 'retained_earning', 'working_capital',
        'operating_cf', 'audited', 'source', 'created_at'
    ]
    return dict(zip(keys, row))


@router.get("/ratios/{customer_id}")
def get_financial_ratios(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """
    고객별 재무비율 조회 (3개년)
    재무제표가 없는 경우 customer 테이블의 기본 데이터로 추정값 제공
    """
    # financial_statement 테이블 조회
    stmts = db.execute(text("""
        SELECT stmt_id, customer_id, fiscal_year, stmt_type,
               revenue, operating_profit, ebitda, interest_expense, net_profit,
               total_assets, current_assets, total_debt, current_debt,
               total_borrowing, equity, retained_earning, working_capital,
               operating_cf, audited, source, created_at
        FROM financial_statement
        WHERE customer_id = :cid
        ORDER BY fiscal_year DESC
        LIMIT 3
    """), {"cid": customer_id}).fetchall()

    # 고객 기본정보 (재무제표 없을 때 fallback)
    customer = db.execute(text("""
        SELECT customer_id, customer_name, industry_code, industry_name,
               size_category, asset_size, revenue_size
        FROM customer WHERE customer_id = :cid
    """), {"cid": customer_id}).fetchone()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    results = []

    if stmts:
        stmt_list = [_row_to_stmt(r) for r in stmts]
        for i, stmt in enumerate(stmt_list):
            prev = stmt_list[i + 1] if i + 1 < len(stmt_list) else None
            # 여신 원금상환액: facility 합계에서 추정
            facility_row = db.execute(text("""
                SELECT COALESCE(SUM(outstanding_amount), 0)
                FROM facility
                WHERE customer_id = :cid AND status = 'ACTIVE'
            """), {"cid": customer_id}).scalar() or 0
            annual_principal = facility_row * 0.15  # 평균 6.7년 만기 가정

            ratios = calculate_financial_ratios(stmt, prev, annual_principal)
            results.append({
                'fiscal_year': stmt['fiscal_year'],
                'stmt_type':   stmt['stmt_type'],
                'audited':     bool(stmt.get('audited')),
                'source':      stmt.get('source'),
                'statement':   {
                    'revenue':          stmt.get('revenue'),
                    'operating_profit': stmt.get('operating_profit'),
                    'ebitda':           stmt.get('ebitda'),
                    'interest_expense': stmt.get('interest_expense'),
                    'net_profit':       stmt.get('net_profit'),
                    'total_assets':     stmt.get('total_assets'),
                    'total_debt':       stmt.get('total_debt'),
                    'equity':           stmt.get('equity'),
                },
                'ratios': ratios,
                'altman_z': ratios['altman_z']['value'],
                'risk_signal': ratios['altman_z']['signal'],
            })
    else:
        # fallback: customer 테이블 기본값으로 추정
        asset  = customer[5] or 0
        revenue = customer[6] or 0
        results.append({
            'fiscal_year': AS_OF_DATE.year - 1,
            'stmt_type': 'ESTIMATED',
            'audited': False,
            'source': 'CUSTOMER_MASTER',
            'statement': {'total_assets': asset, 'revenue': revenue},
            'ratios': {},
            'altman_z': None,
            'risk_signal': 'GREY',
            'note': '재무제표 미입력 - customer 기본 데이터 기반 추정'
        })

    # 동업종 평균 (같은 산업, 같은 규모)
    peer_avg = _get_peer_average(customer[2], customer[4], db)

    return {
        'customer_id':   customer[0],
        'customer_name': customer[1],
        'industry_code': customer[2],
        'industry_name': customer[3],
        'size_category': customer[4],
        'years':         results,
        'peer_average':  peer_avg,
        'benchmarks':    RATIO_META,
        'has_statement': len(stmts) > 0,
    }


@router.get("/trend/{customer_id}")
def get_financial_trend(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """재무지표 추세 분석 - 개선/악화 신호 감지"""
    stmts = db.execute(text("""
        SELECT fiscal_year, revenue, operating_profit, ebitda,
               interest_expense, total_assets, total_debt, equity
        FROM financial_statement
        WHERE customer_id = :cid
        ORDER BY fiscal_year ASC
    """), {"cid": customer_id}).fetchall()

    if not stmts:
        raise HTTPException(status_code=404, detail="재무제표 데이터 없음")

    trends = []
    for i, row in enumerate(stmts):
        prev = stmts[i - 1] if i > 0 else None
        year_data = {
            'year': row[0],
            'revenue': row[1],
            'operating_profit': row[2],
            'ebitda': row[3],
            'interest_expense': row[4],
            'total_assets': row[5],
            'total_debt': row[6],
            'equity': row[7],
        }

        # 전기 대비 방향성
        if prev:
            def _dir(cur, pre):
                if cur is None or pre is None or pre == 0:
                    return 'FLAT'
                chg = (cur - pre) / abs(pre) * 100
                if chg > 5:   return 'UP'
                if chg < -5:  return 'DOWN'
                return 'FLAT'

            year_data['directions'] = {
                'revenue':          _dir(row[1], prev[1]),
                'operating_profit': _dir(row[2], prev[2]),
                'ebitda':           _dir(row[3], prev[3]),
                'total_debt':       _dir(row[6], prev[6]),  # 부채 감소가 긍정
                'equity':           _dir(row[7], prev[7]),
            }
            # 종합 신호: 수익성 상승 + 부채 감소 → IMPROVING
            op_up  = year_data['directions']['operating_profit'] == 'UP'
            debt_dn = year_data['directions']['total_debt'] == 'DOWN'
            if op_up and debt_dn:
                year_data['overall_signal'] = 'IMPROVING'
            elif not op_up and year_data['directions']['total_debt'] == 'UP':
                year_data['overall_signal'] = 'DETERIORATING'
            else:
                year_data['overall_signal'] = 'STABLE'

        trends.append(year_data)

    return {'customer_id': customer_id, 'trends': trends}


@router.get("/peer-comparison/{customer_id}")
def get_peer_comparison(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """동업종·동규모 벤치마크 비교"""
    customer = db.execute(text("""
        SELECT customer_id, customer_name, industry_code, size_category
        FROM customer WHERE customer_id = :cid
    """), {"cid": customer_id}).fetchone()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # 최신 재무비율 조회
    ratio_row = db.execute(text("""
        SELECT debt_ratio, current_ratio, ier, debt_dependency, dscr,
               op_margin, roa, roe, altman_z, risk_signal
        FROM financial_ratio
        WHERE customer_id = :cid
        ORDER BY fiscal_year DESC LIMIT 1
    """), {"cid": customer_id}).fetchone()

    # 동업종 평균
    peer_avg = _get_peer_average(customer[2], customer[3], db)

    if not ratio_row:
        return {'customer': {'customer_id': customer[0], 'customer_name': customer[1]},
                'my_ratios': None, 'peer_average': peer_avg,
                'note': '재무비율 데이터 없음'}

    my = {
        'debt_ratio': ratio_row[0], 'current_ratio': ratio_row[1],
        'ier': ratio_row[2], 'debt_dependency': ratio_row[3],
        'dscr': ratio_row[4], 'op_margin': ratio_row[5],
        'roa': ratio_row[6], 'roe': ratio_row[7],
        'altman_z': ratio_row[8], 'risk_signal': ratio_row[9],
    }

    # Percentile 계산 (동업종 내 위치)
    percentiles = {}
    for metric in ['debt_ratio', 'dscr', 'ier', 'op_margin']:
        if my[metric] is None:
            continue
        count_below = db.execute(text(f"""
            SELECT COUNT(*) FROM financial_ratio fr
            JOIN customer c ON fr.customer_id = c.customer_id
            WHERE c.industry_code = :ind
            AND fr.{metric} IS NOT NULL
            AND fr.{metric} <= :val
            AND fr.fiscal_year = (SELECT MAX(fiscal_year) FROM financial_ratio WHERE customer_id = fr.customer_id)
        """), {"ind": customer[2], "val": my[metric]}).scalar() or 0

        total = db.execute(text(f"""
            SELECT COUNT(*) FROM financial_ratio fr
            JOIN customer c ON fr.customer_id = c.customer_id
            WHERE c.industry_code = :ind AND fr.{metric} IS NOT NULL
        """), {"ind": customer[2]}).scalar() or 1

        percentiles[metric] = round(count_below / total * 100, 1)

    return {
        'customer': {'customer_id': customer[0], 'customer_name': customer[1],
                     'industry_code': customer[2], 'size_category': customer[3]},
        'my_ratios': my,
        'peer_average': peer_avg,
        'percentiles': percentiles,
    }


@router.get("/summary/{application_id}")
def get_financial_summary_for_application(
    application_id: str,
    db: Session = Depends(get_db)
):
    """여신 심사 화면 연동용 - 신청건 고객의 재무 요약"""
    app = db.execute(text("""
        SELECT a.customer_id, a.requested_amount, a.requested_tenor,
               cr.pd_value, cr.final_grade
        FROM loan_application a
        LEFT JOIN credit_rating_result cr ON a.application_id = cr.application_id
        WHERE a.application_id = :app_id
        ORDER BY cr.rating_date DESC LIMIT 1
    """), {"app_id": application_id}).fetchone()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    customer_id = app[0]
    requested_amount = app[1] or 0
    tenor_months = app[2] or 36

    # 최신 재무제표
    stmt = db.execute(text("""
        SELECT revenue, operating_profit, ebitda, interest_expense, net_profit,
               total_assets, total_debt, current_assets, current_debt,
               total_borrowing, equity, retained_earning, working_capital, operating_cf
        FROM financial_statement
        WHERE customer_id = :cid
        ORDER BY fiscal_year DESC LIMIT 1
    """), {"cid": customer_id}).fetchone()

    # 기존 여신 원금상환 추정
    existing_debt = db.execute(text("""
        SELECT COALESCE(SUM(outstanding_amount), 0)
        FROM facility WHERE customer_id = :cid AND status = 'ACTIVE'
    """), {"cid": customer_id}).scalar() or 0

    if stmt:
        stmt_dict = {
            'revenue': stmt[0], 'operating_profit': stmt[1], 'ebitda': stmt[2],
            'interest_expense': stmt[3], 'net_profit': stmt[4], 'total_assets': stmt[5],
            'total_debt': stmt[6], 'current_assets': stmt[7], 'current_debt': stmt[8],
            'total_borrowing': stmt[9], 'equity': stmt[10], 'retained_earning': stmt[11],
            'working_capital': stmt[12], 'operating_cf': stmt[13],
        }
        # 신청 건 포함 원금 상환 추정
        new_annual_principal = requested_amount / (tenor_months / 12)
        existing_annual = (existing_debt * 0.15)
        total_annual_principal = existing_annual + new_annual_principal

        ratios = calculate_financial_ratios(
            stmt_dict, annual_principal=total_annual_principal
        )
        altman_z, risk_signal = calculate_altman_z(stmt_dict)

        # DSCR 심사 판정
        dscr_val = ratios['dscr']['value']
        if dscr_val is None:
            dscr_judgment = 'N/A'
        elif dscr_val >= 1.5:
            dscr_judgment = 'STRONG'    # 여유 있음
        elif dscr_val >= 1.25:
            dscr_judgment = 'ADEQUATE'  # 기준 충족
        elif dscr_val >= 1.0:
            dscr_judgment = 'MARGINAL'  # 주의 필요
        else:
            dscr_judgment = 'WEAK'      # 부적격

        return {
            'application_id': application_id,
            'customer_id': customer_id,
            'has_financial_data': True,
            'key_ratios': {
                'dscr': {'value': dscr_val, 'judgment': dscr_judgment,
                         'signal': ratios['dscr']['signal']},
                'debt_ratio': ratios['debt_ratio'],
                'ier':        ratios['ier'],
                'current_ratio': ratios['current_ratio'],
                'altman_z': {'value': altman_z, 'signal': risk_signal},
            },
            'new_dscr_impact': {
                'existing_annual_principal': round(existing_annual, 0),
                'new_annual_principal': round(new_annual_principal, 0),
                'total_annual_principal': round(total_annual_principal, 0),
                'ebitda': stmt_dict.get('ebitda'),
                'interest_expense': stmt_dict.get('interest_expense'),
                'dscr_after_new_loan': dscr_val,
            },
            'all_ratios': ratios,
        }
    else:
        return {
            'application_id': application_id,
            'customer_id': customer_id,
            'has_financial_data': False,
            'note': '재무제표 미입력. 고객 재무 데이터를 등록해 주세요.',
            'key_ratios': {},
        }


@router.post("/statement/{customer_id}")
def upsert_financial_statement(
    customer_id: str,
    fiscal_year: int,
    revenue: Optional[float] = None,
    operating_profit: Optional[float] = None,
    ebitda: Optional[float] = None,
    interest_expense: Optional[float] = None,
    net_profit: Optional[float] = None,
    total_assets: Optional[float] = None,
    current_assets: Optional[float] = None,
    total_debt: Optional[float] = None,
    current_debt: Optional[float] = None,
    total_borrowing: Optional[float] = None,
    equity: Optional[float] = None,
    retained_earning: Optional[float] = None,
    working_capital: Optional[float] = None,
    operating_cf: Optional[float] = None,
    audited: int = 0,
    source: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """재무제표 입력/수정 (Upsert)"""
    stmt_id = f"FS_{customer_id}_{fiscal_year}"

    # EBITDA 자동 추정 (미입력 시)
    _ebitda = ebitda
    if _ebitda is None and operating_profit is not None:
        _ebitda = operating_profit * 1.15  # 감가상각비 추정 (영업이익의 15%)

    # 운전자본 자동 계산
    _working_capital = working_capital
    if _working_capital is None and current_assets is not None and current_debt is not None:
        _working_capital = current_assets - current_debt

    db.execute(text("""
        INSERT INTO financial_statement
        (stmt_id, customer_id, fiscal_year, stmt_type,
         revenue, operating_profit, ebitda, interest_expense, net_profit,
         total_assets, current_assets, total_debt, current_debt,
         total_borrowing, equity, retained_earning, working_capital,
         operating_cf, audited, source)
        VALUES
        (:stmt_id, :cid, :year, 'ANNUAL',
         :revenue, :op_profit, :ebitda, :interest, :net_profit,
         :total_assets, :cur_assets, :total_debt, :cur_debt,
         :total_borrow, :equity, :retained, :working_cap,
         :op_cf, :audited, :source)
        ON CONFLICT(customer_id, fiscal_year, stmt_type)
        DO UPDATE SET
          revenue=excluded.revenue, operating_profit=excluded.operating_profit,
          ebitda=excluded.ebitda, interest_expense=excluded.interest_expense,
          net_profit=excluded.net_profit, total_assets=excluded.total_assets,
          current_assets=excluded.current_assets, total_debt=excluded.total_debt,
          current_debt=excluded.current_debt, total_borrowing=excluded.total_borrowing,
          equity=excluded.equity, retained_earning=excluded.retained_earning,
          working_capital=excluded.working_capital, operating_cf=excluded.operating_cf,
          audited=excluded.audited, source=excluded.source
    """), {
        "stmt_id": stmt_id, "cid": customer_id, "year": fiscal_year,
        "revenue": revenue, "op_profit": operating_profit, "ebitda": _ebitda,
        "interest": interest_expense, "net_profit": net_profit,
        "total_assets": total_assets, "cur_assets": current_assets,
        "total_debt": total_debt, "cur_debt": current_debt,
        "total_borrow": total_borrowing, "equity": equity,
        "retained": retained_earning, "working_cap": _working_capital,
        "op_cf": operating_cf, "audited": audited, "source": source
    })

    # 재무비율 자동 산출 및 캐시
    _save_financial_ratio(customer_id, fiscal_year, db)
    record_audit(db, "FIN_STATEMENT_UPSERT", "financial_statement", stmt_id,
                 after={"customer_id": customer_id, "fiscal_year": fiscal_year,
                        "audited": audited, "source": source},
                 user_id=current_user.name, user_dept=current_user.dept)
    db.commit()

    return {"status": "success", "stmt_id": stmt_id,
            "message": f"{fiscal_year}년 재무제표 저장 완료"}


def _save_financial_ratio(customer_id: str, fiscal_year: int, db: Session):
    """재무비율 자동 산출 및 financial_ratio 테이블 저장"""
    stmt_row = db.execute(text("""
        SELECT revenue, operating_profit, ebitda, interest_expense, net_profit,
               total_assets, current_assets, total_debt, current_debt,
               total_borrowing, equity, retained_earning, working_capital, operating_cf
        FROM financial_statement
        WHERE customer_id = :cid AND fiscal_year = :year
    """), {"cid": customer_id, "year": fiscal_year}).fetchone()

    if not stmt_row:
        return

    prev_row = db.execute(text("""
        SELECT revenue, operating_profit, ebitda, interest_expense, net_profit,
               total_assets, current_assets, total_debt, current_debt,
               total_borrowing, equity, retained_earning, working_capital, operating_cf
        FROM financial_statement
        WHERE customer_id = :cid AND fiscal_year = :year
    """), {"cid": customer_id, "year": fiscal_year - 1}).fetchone()

    def to_dict(row):
        if not row:
            return None
        keys = ['revenue', 'operating_profit', 'ebitda', 'interest_expense', 'net_profit',
                'total_assets', 'current_assets', 'total_debt', 'current_debt',
                'total_borrowing', 'equity', 'retained_earning', 'working_capital', 'operating_cf']
        return dict(zip(keys, row))

    stmt_dict = to_dict(stmt_row)
    prev_dict = to_dict(prev_row)

    existing_debt = db.execute(text("""
        SELECT COALESCE(SUM(outstanding_amount), 0)
        FROM facility WHERE customer_id = :cid AND status = 'ACTIVE'
    """), {"cid": customer_id}).scalar() or 0

    ratios = calculate_financial_ratios(stmt_dict, prev_dict, existing_debt * 0.15)
    altman_z, risk_signal = calculate_altman_z(stmt_dict)

    ratio_id = f"FR_{customer_id}_{fiscal_year}"
    db.execute(text("""
        INSERT INTO financial_ratio
        (ratio_id, customer_id, fiscal_year,
         debt_ratio, current_ratio, ier, debt_dependency, dscr, ocf_ratio,
         op_margin, roa, roe, revenue_growth, op_growth, altman_z, risk_signal)
        VALUES
        (:rid, :cid, :year,
         :debt_ratio, :cur_ratio, :ier, :debt_dep, :dscr, :ocf,
         :op_margin, :roa, :roe, :rev_growth, :op_growth, :altman_z, :signal)
        ON CONFLICT(customer_id, fiscal_year) DO UPDATE SET
          debt_ratio=excluded.debt_ratio, current_ratio=excluded.current_ratio,
          ier=excluded.ier, debt_dependency=excluded.debt_dependency,
          dscr=excluded.dscr, ocf_ratio=excluded.ocf_ratio,
          op_margin=excluded.op_margin, roa=excluded.roa, roe=excluded.roe,
          revenue_growth=excluded.revenue_growth, op_growth=excluded.op_growth,
          altman_z=excluded.altman_z, risk_signal=excluded.risk_signal
    """), {
        "rid": ratio_id, "cid": customer_id, "year": fiscal_year,
        "debt_ratio":  ratios['debt_ratio']['value'],
        "cur_ratio":   ratios['current_ratio']['value'],
        "ier":         ratios['ier']['value'],
        "debt_dep":    ratios['debt_dependency']['value'],
        "dscr":        ratios['dscr']['value'],
        "ocf":         ratios['ocf_ratio']['value'],
        "op_margin":   ratios['op_margin']['value'],
        "roa":         ratios['roa']['value'],
        "roe":         ratios['roe']['value'],
        "rev_growth":  ratios['revenue_growth']['value'],
        "op_growth":   ratios['op_growth']['value'],
        "altman_z":    altman_z,
        "signal":      risk_signal,
    })


def _get_peer_average(industry_code: str, size_category: str, db: Session) -> dict:
    """동업종·동규모 평균 재무비율"""
    if not industry_code:
        return {}

    row = db.execute(text("""
        SELECT
            AVG(fr.debt_ratio)      as avg_debt_ratio,
            AVG(fr.current_ratio)   as avg_current_ratio,
            AVG(fr.ier)             as avg_ier,
            AVG(fr.dscr)            as avg_dscr,
            AVG(fr.op_margin)       as avg_op_margin,
            AVG(fr.roa)             as avg_roa,
            COUNT(DISTINCT fr.customer_id) as peer_count
        FROM financial_ratio fr
        JOIN customer c ON fr.customer_id = c.customer_id
        WHERE c.industry_code = :ind
        AND (:size IS NULL OR c.size_category = :size)
        AND fr.fiscal_year = (SELECT MAX(fiscal_year) FROM financial_ratio WHERE customer_id = fr.customer_id)
    """), {"ind": industry_code, "size": size_category}).fetchone()

    if not row or not row[6]:
        return {}

    return {
        'debt_ratio':    round(row[0], 1) if row[0] else None,
        'current_ratio': round(row[1], 1) if row[1] else None,
        'ier':           round(row[2], 2) if row[2] else None,
        'dscr':          round(row[3], 2) if row[3] else None,
        'op_margin':     round(row[4], 2) if row[4] else None,
        'roa':           round(row[5], 2) if row[5] else None,
        'peer_count':    row[6],
    }
