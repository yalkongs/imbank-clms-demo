# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

iM뱅크 CLMS (Credit Lifecycle Management System) — 기업여신의 심사·실행·모니터링·회수까지 전체 생애주기를 통합 관리하는 PoC 시스템. 42개 사용자 화면 · 43개 API 모듈(라우터) · 97개 업무 테이블 · 자동 테스트 207건.

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

**백엔드** (`backend/`): FastAPI + SQLAlchemy. ORM 모델 정의는 있으나 실제로는 raw SQL을 직접 실행하는 방식을 사용함 (`db.execute(text(...))`). `backend/app/main.py`에서 43개 라우터 등록.

**데이터베이스** (`database/`): SQLite 단일 파일 (`database/imbank_demo.db`, 40MB). 업무 테이블 97개 (schema.sql 49 + migrations/*.sql 확장). WAL 모드 활성화됨.

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

`backend/app/api/` 아래 44개 모듈(라우터 43 + helper 1)이 각각 담당:

- **기본 (8개)**: `dashboard`, `applications`, `capital`, `portfolio`, `limits`, `stress_test`, `models`, `customers`
- **고도화 (9개)**: `capital_optimizer`, `ews_advanced`, `dynamic_limits`, `customer_profitability`, `collateral_monitoring`, `portfolio_optimization`, `workout`, `esg`, `alm`
- **Phase 1** (여신심사 고도화): `financial_analysis`, `group_credit`, `covenant`
- **Phase 2** (부실관리): `asset_classification`, `ecl`, `delinquency`
- **Phase 3** (자동화): `automation`
- **추가**: `model_inference`, `region_helper`
- **규제 대응·건전성 고도화 (2026-08, P1~P8)**: `loss_absorption`(커버리지 조종석), `cet1_path`(output floor), `region_rebalancing`, `accountability`(책무구조도 증거), `facility_lifecycle`(연장·조건변경, 에버그리닝 통제) + `inclusive_finance`·`ecl`·`pf` 확장

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

## 배포 (Render 단일 정본)

`render.yaml` 하나가 정본이다. 단일 uvicorn이 API와 SPA를 함께 서빙한다
(`backend/app/main.py:110-127`). Vercel 구성은 서버리스 읽기 전용 파일시스템이
SQLite 데모와 맞지 않아 제거했으므로 되살리지 말 것.

### 변경은 반드시 배포까지 간다

**커밋만 하고 끝내지 않는다.** Render는 `origin/master`를 바라보므로
push 하지 않으면 사용자가 보는 화면은 그대로다. 작업을 마쳤다고 보고하기 전에
`git push origin master`까지 완료하고, 그 결과를 확인한다.

작업 브랜치를 썼다면 master 로 머지한 뒤 push 한다. 배포 확인 전까지는
"반영했다"고 말하지 않는다.

### 자동화 장치 (`.githooks/`)

클론 후 `./setup-hooks.sh` 를 한 번 실행하면 활성화된다
(`git config core.hooksPath .githooks`).

- **pre-commit** — `frontend/src`·설정 파일이 커밋에 포함되면 자동으로
  `npm run build` 하고 `frontend/dist` 를 함께 스테이징한다. 빌드가 실패하면
  커밋을 중단해 깨진 상태가 배포되지 않게 한다.
- **pre-push** — `index.html` 이 참조하는 번들이 실제로 존재하고 git 에
  추적되는지, 데모 DB가 추적되는지 검증한다. 하나라도 어긋나면 push 를 막는다.

훅을 우회해야 하면 `--no-verify` 를 쓰되, 그 커밋은 배포가 깨질 수 있다.

- **`frontend/dist`는 반드시 커밋한다.** `.gitignore`의 `!frontend/dist/` 예외가
  Python `dist/` 패턴을 상쇄하고 있다. 이 예외를 지우면 신규 번들이 커밋되지 않아
  배포 데모가 백지 화면이 된다.
- 프론트엔드를 수정했으면 `cd frontend && npm run build` 후 **dist 전체를** 커밋한다.
  번들 파일명 해시가 바뀌므로 `index.html`만 커밋하면 asset 404가 난다.
- `database/imbank_demo.db`도 배포 자산이라 `*.db` 예외로 추적한다.
- 색상은 `tailwind.config.js`에서 Tailwind `blue` 스케일을 iM 민트로 리매핑해 처리한다.
  단 이 리매핑은 클래스명에만 적용되므로 Recharts 등에 **인라인 hex를 직접 넘길 때는
  민트 스케일(`#00897B`, `#00BFA5`, `#57D7C2` 등)을 직접 써야 한다.**
