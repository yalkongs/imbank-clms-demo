"""
iM뱅크 CLMS 데모 시스템 - FastAPI 메인 애플리케이션
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from .core.database import engine, Base
from .api import dashboard, applications, capital, portfolio, limits, stress_test, models, model_inference, customers, capital_optimizer
from .api import ews_advanced, dynamic_limits, customer_profitability, collateral_monitoring, portfolio_optimization, workout, esg, alm


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # Startup
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
    pass


app = FastAPI(
    title="iM뱅크 CLMS 데모 시스템",
    description="""
    기업여신심사시스템 (Corporate Loan Management System) 데모

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


@app.get("/health")
def health_check():
    """헬스체크 엔드포인트"""
    return {"status": "healthy"}


# 프론트엔드 빌드 파일 서빙
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend", "dist")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA 라우팅 - 모든 비-API 경로를 index.html로"""
        file_path = os.path.join(FRONTEND_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
