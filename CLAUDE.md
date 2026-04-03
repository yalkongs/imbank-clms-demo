# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

iM뱅크 CLMS (Credit Lifecycle Management System) — 기업여신의 심사·실행·모니터링·회수까지 전체 생애주기를 통합 관리하는 PoC 시스템. 19개 화면 · 27개 API 모듈 · 49개 DB 테이블.

## 개발 서버 실행

```bash
# 통합 시작 (백엔드 + 프론트엔드)
./start.sh

# 백엔드만 (포트 8000)
cd backend && python run.py

# 프론트엔드만 (포트 3000)
cd frontend && npm run dev
```

- 프론트엔드: http://localhost:3000
- API 문서 (Swagger): http://localhost:8000/docs

## 빌드

```bash
# 프론트엔드 빌드
cd frontend && npm run build

# Python 의존성 설치
cd backend && pip install -r requirements.txt
```

## 아키텍처

```
React 18 (Vite, port 3000)  →  /api/* proxy  →  FastAPI (uvicorn, port 8000)  →  SQLite
```

**프론트엔드** (`frontend/`): TypeScript + React 18 + Vite. Tailwind CSS, Recharts, Axios. `vite.config.ts`에 `/api` → `localhost:8000` 프록시 설정.

**백엔드** (`backend/`): FastAPI + SQLAlchemy. ORM 모델 정의는 있으나 실제로는 raw SQL을 직접 실행하는 방식을 사용함 (`db.execute(text(...))`). `backend/app/main.py`에서 27개 라우터 등록.

**데이터베이스** (`database/`): SQLite 단일 파일 (`database/imbank_demo.db`, 40MB). 49개 테이블. WAL 모드 활성화됨.

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `backend/app/main.py` | FastAPI 앱, 라우터 등록, CORS 설정 |
| `backend/app/core/database.py` | SQLAlchemy 엔진 및 세션 팩토리 |
| `backend/app/services/calculations.py` | RAROC, PD, LGD, RWA 핵심 계산 로직 |
| `backend/app/services/credit_models.py` | 신용 모델 (16단계 등급 체계) |
| `frontend/src/App.tsx` | React Router 라우팅 정의 |
| `frontend/src/components/Layout.tsx` | 사이드 네비게이션 및 전체 레이아웃 |
| `database/schema.sql` | 메인 49개 테이블 스키마 |

## API 모듈 구조

`backend/app/api/` 아래 27개 모듈이 각각 라우터 담당:

- **기본 (8개)**: `dashboard`, `applications`, `capital`, `portfolio`, `limits`, `stress_test`, `models`, `customers`
- **고도화 (9개)**: `capital_optimizer`, `ews_advanced`, `dynamic_limits`, `customer_profitability`, `collateral_monitoring`, `portfolio_optimization`, `workout`, `esg`, `alm`
- **Phase 1** (여신심사 고도화): `financial_analysis`, `group_credit`, `covenant`
- **Phase 2** (부실관리): `asset_classification`, `ecl`, `delinquency`
- **Phase 3** (자동화): `automation`
- **추가**: `model_inference`, `region_helper`

## 페이지-API 대응

| 페이지 (`frontend/src/pages/`) | API prefix |
|------|------|
| `Applications.tsx` (101KB, 대규모) | `/api/applications` |
| `Models.tsx` | `/api/models` |
| `EWSAdvanced.tsx` + `ews/` 하위 6개 | `/api/ews-advanced` |
| `AssetClassification.tsx` | `/api/asset-classification` |
| `Covenant.tsx` | `/api/covenant` |

## 데이터베이스

DB 경로는 `backend/app/core/config.py`에 절대 경로로 설정됨. 데이터 재생성이 필요하면:

```bash
cd database
python generate_data.py          # 마스터 데이터 (고객 1000+, 여신 5000+)
python generate_phase1_data.py   # Phase 1 여신심사 데이터
python generate_phase2_data.py   # Phase 2 부실관리 데이터
python generate_phase3_data.py   # Phase 3 자동화 데이터
python generate_ews_leading_data.py  # EWS 선행지표 데이터
python generate_extension_data.py    # 확장 데이터
```

## 주의사항

- 백엔드는 SQLAlchemy ORM 모델(`backend/app/models/`)을 선언하지만 실제 쿼리는 `text()`로 raw SQL을 실행함. API 추가 시 이 패턴 유지.
- `Applications.tsx`와 `ews_advanced.py`는 각각 100KB 내외의 대형 파일이므로 편집 시 주의.
- DB WAL 파일(`imbank_demo.db-shm`, `imbank_demo.db-wal`)은 git 추적 불필요.
