"""
iM뱅크 CLMS - FastAPI 메인 애플리케이션
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from .core.database import engine, Base
from .core.config import AS_OF_DATE, AS_OF_MONTH, AS_OF_STR
from .api import dashboard, applications, capital, portfolio, limits, stress_test, models, model_inference, customers, capital_optimizer
from .api import ews_advanced, dynamic_limits, customer_profitability, collateral_monitoring, portfolio_optimization, workout, esg, alm
# Phase 1: 여신 심사 고도화
from .api import financial_analysis, group_credit, covenant
# Phase 2: 부실 관리 핵심
from .api import asset_classification, ecl, delinquency
# Phase 3: 자동화 브릿지
from .api import automation
# iM뱅크 전략 기능: 포용금융·PF 사업장
from .api import inclusive_finance, pf, governance, export, search
# 포트폴리오 맵 (기업 다차원 산점도 + what-if)
from .api import portfolio_map
# 여신통제 확장: 여신철·EWS 조치의무·금리인하요구권
from .api import credit_case, ews_actions, rate_reduction, obligations, rules
from .api import opinion
# 규제 대응·건전성 고도화 (2026-08 개선 연구 P1~P8)
from .api import loss_absorption, cet1_path, region_rebalancing
# 인증 (서버측 전결·승인자 결정)
from .api import auth as auth_api
from .core.auth import verify_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # Startup - 마이그레이션 먼저 (새 배포 환경 스키마 보장)
    try:
        import sys as _sys
        from pathlib import Path as _P
        _sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "database"))
        from migrate import run_migrations
        applied = run_migrations()
        if applied:
            print(f"[migrate] 적용: {applied}")
    except Exception as e:
        print(f"[migrate] 경고: {e}")
    Base.metadata.create_all(bind=engine)
    # EWS 기한초과 상향보고 실행 (스케줄러 근사 - 기동 시 1회, 멱등)
    try:
        from .core.database import SessionLocal as _SL
        from .api.ews_actions import run_escalation as _rune
        _db = _SL()
        _res = _rune(db=_db)
        if _res.get("escalated"):
            print(f"[escalation] 상향보고 {_res['escalated']}건 실행")
        _db.close()
    except Exception as e:
        print(f"[escalation] 경고: {e}")
    yield
    # Shutdown
    pass


app = FastAPI(
    title="iM뱅크 CLMS",
    description="""
    종합 기업여신 관리시스템 (Corporate Loan Management System)

    ## 주요 기능
    - **경영진 대시보드**: 자본비율, 포트폴리오 현황, EWS 알림
    - **여신신청 관리**: 신청 목록, 상세 심사, What-if 시뮬레이션
    - **자본관리**: 자본비율 모니터링, RWA 예산, 효율성 분석
    - **포트폴리오 전략**: 전략 매트릭스, 집중도 관리
    - **한도관리**: 한도 사용현황, 한도 체크
    - **스트레스 테스트**: 시나리오 분석, 충격 시뮬레이션
    - **모델관리/MRM**: 모델 성능 모니터링, Override 관리
    - **EWS 고도화**: 선행지표, 공급망 분석, 복합지표
    - **동적 한도관리**: 경기사이클 연동, 자동 한도 조정
    - **고객 수익성**: RBC, CLV, 교차판매
    - **담보 모니터링**: 실시간 담보가치, LTV 관리
    - **포트폴리오 최적화**: 효율적 프론티어, 리밸런싱
    - **Workout 관리**: 부실채권, 회수 시나리오
    - **ESG 리스크**: ESG 평가, 녹색금융
    - **ALM**: 금리갭 분석, 헷지 전략
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정 (프론트엔드 연동용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서는 모든 origin 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 응답 압축 - 포트폴리오 맵(736KB)·이력(498KB) 같은 대형 JSON 이
# 저속 회선·무료 인스턴스에서 로딩 시간을 지배한다. gzip 으로 ~1/8 로 줄인다.
app.add_middleware(GZipMiddleware, minimum_size=2048)


# 쓰기 인증 - 공개 배포에서 익명 쓰기를 차단한다 (제3자 리뷰 P0-1).
# GET 은 공개, POST/PUT/DELETE /api/* 는 데모 계정 로그인 필수.
from fastapi import Request as _Req
from fastapi.responses import JSONResponse as _JR

@app.middleware("http")
async def _write_auth_guard(request: _Req, call_next):
    if (request.method in ("POST", "PUT", "DELETE", "PATCH")
            and request.url.path.startswith("/api/")
            and request.url.path != "/api/auth/login"):
        authz = request.headers.get("Authorization", "")
        if not (authz.startswith("Bearer ") and verify_token(authz[7:])):
            return _JR(status_code=401, content={
                "detail": "쓰기 작업은 로그인이 필요합니다 - 우측 상단 사용자 메뉴에서 데모 계정으로 로그인하세요"})
    return await call_next(request)


# 읽기 전용 모드 토글 - READ_ONLY=true 로 기동하면 /api/* 쓰기 요청을 차단한다.
# 공개 데모는 승인·시뮬레이션 체험이 핵심 가치라 기본은 쓰기 허용이며,
# 필요 시(악용 징후 등) 환경변수 하나로 잠글 수 있게 한다.
if os.getenv("READ_ONLY", "").lower() in ("1", "true", "yes"):
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.middleware("http")
    async def _read_only_guard(request: Request, call_next):
        if request.method not in ("GET", "HEAD", "OPTIONS") and request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=403,
                content={"detail": "읽기 전용 모드입니다 - 쓰기 작업이 비활성화되어 있습니다."},
            )
        return await call_next(request)

# API 라우터 등록
app.include_router(dashboard.router)
app.include_router(applications.router)
app.include_router(capital.router)
app.include_router(portfolio.router)
app.include_router(limits.router)
app.include_router(stress_test.router)
app.include_router(models.router)
app.include_router(model_inference.router)
app.include_router(customers.router)
app.include_router(capital_optimizer.router)

# 신규 기능 API 라우터
app.include_router(ews_advanced.router)
app.include_router(dynamic_limits.router)
app.include_router(customer_profitability.router)
app.include_router(collateral_monitoring.router)
app.include_router(portfolio_optimization.router)
app.include_router(workout.router)
app.include_router(esg.router)
app.include_router(alm.router)

# Phase 1: 여신 심사 고도화
app.include_router(financial_analysis.router)
app.include_router(group_credit.router)
app.include_router(covenant.router)

# Phase 2: 부실 관리 핵심
app.include_router(asset_classification.router)
app.include_router(ecl.router)
app.include_router(delinquency.router)

# Phase 3: 자동화 브릿지
app.include_router(automation.router)

# iM뱅크 전략 기능
app.include_router(inclusive_finance.router)
app.include_router(pf.router)
app.include_router(governance.router)
app.include_router(export.router)
app.include_router(search.router)
app.include_router(portfolio_map.router)
app.include_router(credit_case.router)
app.include_router(ews_actions.router)
app.include_router(rate_reduction.router)
app.include_router(auth_api.router)
app.include_router(obligations.router)
app.include_router(rules.router)
app.include_router(opinion.router)

# 규제 대응·건전성 고도화 (2026-08 개선 연구)
app.include_router(loss_absorption.router)
app.include_router(cet1_path.router)
app.include_router(region_rebalancing.router)


@app.get("/health")
def health_check():
    """헬스체크 엔드포인트"""
    return {"status": "healthy"}


@app.get("/api/system/as-of")
def get_as_of_date():
    """시스템 기준일 - 화면 상단 '기준' 배지와 각종 시점 표시에 쓴다.
    프론트에 날짜를 하드코딩하지 않도록 단일 소스에서 내려준다."""
    return {
        "as_of_date":  AS_OF_STR,
        "as_of_month": AS_OF_MONTH,
        "label_ko":    f"{AS_OF_DATE.year}년 {AS_OF_DATE.month}월 {AS_OF_DATE.day}일 기준",
    }


# 프론트엔드 빌드 파일 서빙
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend", "dist")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="static")

    # 경로 탐색(directory traversal) 방지를 위해 실제 경로가 FRONTEND_DIR 내부인지 검증
    _FRONTEND_ROOT = os.path.realpath(FRONTEND_DIR)

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA 라우팅 - 모든 비-API 경로를 index.html로"""
        index_file = os.path.join(FRONTEND_DIR, "index.html")
        requested = os.path.realpath(os.path.join(FRONTEND_DIR, full_path))
        # FRONTEND_DIR 밖으로 벗어나는 요청(../, %2e%2e 등)은 SPA index로 폴백
        if requested == _FRONTEND_ROOT or requested.startswith(_FRONTEND_ROOT + os.sep):
            if os.path.isfile(requested):
                return FileResponse(requested)
        return FileResponse(index_file)
