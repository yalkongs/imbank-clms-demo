# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

iM뱅크 CLMS (Credit Lifecycle Management System) — 기업여신의 심사·실행·모니터링·회수까지 전체 생애주기를 통합 관리하는 PoC 시스템. 42개 사용자 화면 · 44개 API 모듈(라우터) · 103개 업무 테이블 · 자동 테스트 223건.

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

**백엔드** (`backend/`): FastAPI + SQLAlchemy. ORM 모델 정의는 있으나 실제로는 raw SQL을 직접 실행하는 방식을 사용함 (`db.execute(text(...))`). `backend/app/main.py`에서 44개 라우터 등록.

**데이터베이스** (`database/`): SQLite 단일 파일 (`database/imbank_demo.db`, 40MB). 업무 테이블 103개 (schema.sql 49 + migrations/*.sql 확장). WAL 모드 활성화됨.

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `backend/app/main.py` | FastAPI 앱, 라우터 등록, CORS 설정 |
| `backend/app/core/database.py` | SQLAlchemy 엔진 및 세션 팩토리 |
| `backend/app/services/calculations.py` | RAROC, PD, LGD, RWA 핵심 계산 로직 |
| `backend/app/services/credit_models.py` | 신용 모델 (16단계 등급 체계) |
| `backend/app/services/ews_channels.py` | EWS 8채널 점수화·가중 결합 정본 (생성기·API 공유) |
| `backend/app/core/audit.py` | 감사기록 헬퍼 - 상태 변경 API 필수 (critical=승인류) |
| `frontend/src/App.tsx` | React Router 라우팅 정의 |
| `frontend/src/components/Layout.tsx` | 사이드 네비게이션 및 전체 레이아웃 |
| `database/schema.sql` | 메인 49개 테이블 스키마 |

## API 모듈 구조

`backend/app/api/` 아래 45개 모듈(라우터 44 + helper 1)이 각각 담당:

- **기본 (8개)**: `dashboard`, `applications`, `capital`, `portfolio`, `limits`, `stress_test`, `models`, `customers`
- **고도화 (9개)**: `capital_optimizer`, `ews_advanced`, `dynamic_limits`, `customer_profitability`, `collateral_monitoring`, `portfolio_optimization`, `workout`, `esg`, `alm`
- **Phase 1** (여신심사 고도화): `financial_analysis`, `group_credit`, `covenant`
- **Phase 2** (부실관리): `asset_classification`, `ecl`, `delinquency`
- **Phase 3** (자동화): `automation`
- **추가**: `model_inference`, `region_helper`
- **규제 대응·건전성 고도화 (2026-08, P1~P8)**: `loss_absorption`(커버리지 조종석), `cet1_path`(output floor), `region_rebalancing`, `accountability`(책무구조도 증거), `facility_lifecycle`(연장·조건변경, 에버그리닝 통제) + `inclusive_finance`·`ecl`·`pf` 확장
- **EWS 8채널 확장 (2026-08)**: `ews_extended` — 카드매출·고용·상거래연체 대시보드, 채널 선행성 백테스트(3계층), 가중치 거버넌스(해시 결박·synthetic_ack)

## 페이지-API 대응

| 페이지 (`frontend/src/pages/`) | API prefix |
|------|------|
| `Applications.tsx` (101KB, 대규모) | `/api/applications` |
| `Models.tsx` | `/api/models` |
| `EWSAdvanced.tsx` (2단 탭 IA) + `ews/` 하위 10개 | `/api/ews-advanced` |
| `LossAbsorption.tsx`·`CET1Path.tsx`·`RegionRebalancing.tsx`·`Accountability.tsx`·`FacilityLifecycle.tsx` | `/api/loss-absorption`·`/api/cet1-path`·`/api/region-rebalancing`·`/api/accountability`·`/api/lifecycle` |
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
python migrate.py                    # migrations/*.sql 멱등 적용 (앱 기동 시 자동 실행되기도 함)
../venv/bin/python generate_ews_extended_channels.py  # EWS 8채널 데이터 (멱등, 백엔드 정본 import)
```

## 테스트

```bash
cd backend && ../venv/bin/python -m pytest tests -q   # 223건, 약 3초
```

- venv 는 **저장소 루트** `venv/` (backend 안 아님). 시스템 python 은 의존성 없음.
- `tests/conftest.py` 가 데모 DB 를 임시 사본으로 격리(`CLMS_DB_PATH`)하고
  `CLMS_DB_POOL=null` 로 커넥션 풀을 끈다 (테스트 세션 미반납 대비).
- **쓰기 동작을 수동 검증할 때도 배포 DB 에 직접 하지 말 것** — `CLMS_DB_PATH` 로
  사본을 가리켜 실행한다. 데모 DB 는 커밋되는 배포 자산이다 (의도적 시연 시드 제외).

## 정본·통제 원칙 (2026-08 외부감사 2회 정비 이후)

- **산식 단일 정본**: IRB·분류·ECL 은 `services/calculations.py`, EWS 점수·가중
  결합은 `services/ews_channels.py`. 모듈별 상수·공식 복제 금지 — 과거 감사에서
  동일 거래 조달원가가 모듈 간 110bp 어긋난 원인이었다.
- **규정값은 rule_register 정본**: 가중치·한도·임계는 하드코딩 대신 규정 레지스터
  버전으로 관리하고, 변경은 승인 API(부서장+ · 감사 critical · 해시 결박)로만 발효.
- **통제 완결 출고**: 신규 쓰기 기능은 상태기계 + 전결권 검증 + `record_audit`
  (승인류는 critical=True — 감사 실패 시 롤백)를 갖춰서만 추가한다.
- **표기 정직성**: 수치에는 공시/가정/합성 라벨을 구분해 붙인다. 특정 시기 언론
  보도·컨퍼런스콜 발언의 직접 인용은 화면·투어에 넣지 않는다 (사용자 지시).
  합성 백테스트는 '생성 규칙의 재확인'임을 상시 고지한다.
- **투어 앵커**: 스토리 투어(10단계)의 (주)영남바이오는 종합점수 41.2 WARNING 을
  전제한다 — EWS 데이터 재생성 시 `generate_ews_extended_channels.py` 의
  `ANCHOR_TARGETS` 가 이를 보존하는지 확인할 것.
- **외부 감사 루프**: `codex exec --sandbox read-only` 로 감사 → 발견을 코드·SQL 로
  재검증 → 타당 건 정비 → `docs/EXTERNAL_AUDIT_*.md` 에 기록. agy CLI 는 비대화
  모드 권한 문제로 이 환경에서 실행 불가 (2026-08-21 문서 참조).

## 연구·설계 문서 (docs/)

- `IMPROVEMENT_RESEARCH_2026-08-19.md` — 규제·건전성 개선 P1~P8 (전량 구현 완료)
- `EWS_8CHANNEL_DESIGN_2026-08-21.md` — EWS 8채널 설계 (구현 완료)
- `EXTERNAL_AUDIT_VERIFICATION_2026-08-21.md` / `EXTERNAL_AUDIT_EWS_2026-08-22.md`
  — codex 감사 검증·조치 기록. 후속 과제(ECL EIR 엔진, 오경보율 성숙 코호트,
  점수 스냅샷 이력화, 실데이터 리트로 백테스트·그림자 운영)는 여기서 추적.

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
