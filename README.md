# iM뱅크 기업여신관리시스템 PoC

**Corporate Loan Management System **

기업여신심사시스템의 핵심 기능을 시연하는 PoC 애플리케이션입니다.

![Version](https://img.shields.io/badge/version-1.1.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![React](https://img.shields.io/badge/react-18.2-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 목차

- [개요](#개요)
- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [프로젝트 구조](#프로젝트-구조)
- [설치 및 실행](#설치-및-실행)
- [API 문서](#api-문서)
- [데이터 구조](#데이터-구조)
- [변경 이력](#변경-이력)
- [라이선스](#라이선스)

---

## 개요

iM뱅크 CLMS 데모 시스템은 은행의 기업여신 심사 및 관리 업무를 지원하는 통합 시스템입니다.
실제 운영 시스템의 핵심 기능을 재현하여 개념 검증(PoC) 및 교육 목적으로 활용됩니다.

### 핵심 가치

- **리스크 기반 의사결정**: PD, LGD, EAD 모델을 활용한 과학적 심사
- **자본 효율성 최적화**: RAROC 기반 가격결정 및 자본배분
- **규제 준수**: Basel III/IV 자본 규제 대응
- **통합 모니터링**: 포트폴리오, 한도, 모델 성능의 실시간 관리

---

## 주요 기능

### 1. Dashboard
- 전체 포트폴리오 현황 한눈에 파악
- 자본비율 현황 (BIS, Tier1, CET1, 레버리지)
- EWS(조기경보) 알림
- 핵심 KPI 모니터링 (RAROC, 평균 PD/LGD)
- **지역별 필터링** (수도권/대구경북/부산경남)

### 2. 여신신청 관리
- 신청서 접수 및 진행 상태 추적
- 심사 단계별 진행 현황 (접수 → 서류심사 → 신용분석 → 심사위원회 → 최종승인)
- 신용평가 결과 및 리스크 파라미터
- 금리 산정 및 RAROC
- What-if 시뮬레이션
- 승인/거절 이력 관리
- **지역별 필터링**

### 3. 자본관리
- BIS 비율, CET1 비율 모니터링
- RWA 구성 분석
- 자본 포지션 추이 분석 (최대 3년)
- 세그먼트별 자본 예산 관리
- 신규 익스포저 시뮬레이션
- **지역별 필터링**

### 4. 자본최적화
- RWA 최적화 분석
- 자본배분 최적화
- 동적 가격 제안 (RAROC 기반)
- 포트폴리오 리밸런싱 추천
- 자본 효율성 대시보드
- **지역별 필터링**

### 5. 포트폴리오 분석
- 업종/등급/규모별 집중도 분석
- 업종-등급 전략 매트릭스
- HHI 지수 및 Top 고객/그룹 분석
- 세그먼트별 상세 분석
- **지역별 필터링**

### 6. 포트폴리오 최적화
- 포트폴리오 최적화 시뮬레이션
- 효율적 프론티어 분석
- **지역별 필터링**

### 7. 한도관리
- 규제/내부 한도 설정 및 모니터링
- 다차원 한도 (단일차주, 동일그룹, 업종 등)
- 한도 소진율 추적 및 경보
- 사전 한도 체크

### 8. 스트레스테스트
- 다양한 경제 시나리오 설정
- GDP, 금리, 실업률 충격 분석
- RWA/EL 영향 평가
- 스트레스 상황 자본 영향도 분석

### 9. 모델관리 (MRM)
- 모델 레지스트리 관리 (5개 모델: PD 기업/소호, LGD, EAD, Pricing)
- 성능 모니터링 (GINI, KS, PSI, AR ratio)
- **등급별 PD 백테스트** (Binomial Test 기반, 모델별 필터링)
- **Override 성과 분석** (Type I/II Error, 방향별 정확도)
- **빈티지 분석** (MOB별 연체/부도 추적, 코호트 유형별 필터링)
- **모델 상세 사양 모달** (이론적 배경, 수학 공식, 장단점, 규제 요건)
- Champion-Challenger 비교
- 검증 일정 관리

### 10. 고객관리
- 기업 고객 정보 통합 조회 (400건)
- 업종/규모별 필터링 및 검색
- 고객별 여신 현황 및 이력
- **지역별 필터링**

### 11. 조기경보 (EWS)
- 고급 조기경보 모니터링
- 등급별/업종별 경보 분석
- **지역별 필터링**

---

## 기술 스택

### Backend
- **Python 3.11+**
- **FastAPI**: 고성능 REST API 프레임워크
- **SQLAlchemy**: ORM
- **SQLite**: 경량 데이터베이스 (데모용)

### Frontend
- **React 18.2** + **TypeScript**
- **Vite**: 차세대 빌드 도구
- **Tailwind CSS**: 유틸리티 기반 스타일링
- **Recharts**: 반응형 차트 라이브러리
- **Lucide React**: 아이콘

---

## 프로젝트 구조

```
imbank-clms-demo/
├── backend/
│   ├── app/
│   │   ├── api/               # API 엔드포인트
│   │   │   ├── dashboard.py
│   │   │   ├── applications.py
│   │   │   ├── capital.py
│   │   │   ├── capital_optimizer.py
│   │   │   ├── portfolio.py
│   │   │   ├── portfolio_optimization.py
│   │   │   ├── limits.py
│   │   │   ├── stress_test.py
│   │   │   ├── models.py
│   │   │   ├── customers.py
│   │   │   ├── ews.py
│   │   │   ├── model_inference.py
│   │   │   ├── region_helper.py    # 지역 필터 헬퍼
│   │   │   └── calculations.py     # RAROC 등 핵심 계산
│   │   ├── core/              # 핵심 설정
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   └── main.py            # FastAPI 앱 진입점
│   ├── data/
│   │   └── seed_data.py       # 기초 시드 데이터 생성
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/        # 공통 컴포넌트
│   │   │   ├── index.ts       # Card, StatCard, Badge, Table 등
│   │   │   ├── Layout.tsx
│   │   │   └── RegionFilter.tsx   # 지역 필터 버튼 컴포넌트
│   │   ├── pages/             # 페이지 컴포넌트 (11개)
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Applications.tsx
│   │   │   ├── Capital.tsx
│   │   │   ├── CapitalOptimizer.tsx
│   │   │   ├── Portfolio.tsx
│   │   │   ├── PortfolioOptimization.tsx
│   │   │   ├── Limits.tsx
│   │   │   ├── StressTest.tsx
│   │   │   ├── Models.tsx
│   │   │   ├── CustomerBrowser.tsx
│   │   │   └── EWSAdvanced.tsx
│   │   ├── utils/
│   │   │   ├── api.ts         # API 클라이언트
│   │   │   └── format.ts      # 포맷 유틸리티
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── database/
│   ├── imbank_demo.db              # SQLite 데이터베이스
│   ├── schema.sql                  # 스키마 정의
│   └── generate_extension_data.py  # 확장 데이터 생성
│
├── start.sh                   # 서버 시작 스크립트
├── README.md
└── .gitignore
```

---

## 설치 및 실행

### 사전 요구사항

- Python 3.11 이상
- Node.js 18 이상
- npm 또는 yarn

### 1. 저장소 클론

```bash
git clone https://github.com/your-username/imbank-clms-demo.git
cd imbank-clms-demo
```

### 2. Backend 설정

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r backend/requirements.txt

# 백엔드 실행
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend 설정

```bash
# 새 터미널에서
cd frontend

# 의존성 설치
npm install

# 프론트엔드 실행
npm run dev
```

### 4. 접속

- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **API 문서 (Swagger)**: http://localhost:8000/docs

### 간편 실행

```bash
cd imbank-clms-demo
(cd backend && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &) && \
(cd frontend && npm run dev)
```

### 종료 및 재시작

```bash
# 종료
lsof -ti:8000 | xargs kill 2>/dev/null
lsof -ti:3000 | xargs kill 2>/dev/null
```

---

## API 문서

### 주요 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/dashboard/summary` | 대시보드 요약 |
| GET | `/api/applications` | 여신신청 목록 |
| GET | `/api/applications/{id}` | 여신신청 상세 |
| POST | `/api/applications/{id}/approve` | 승인/거절 처리 |
| GET | `/api/capital/position` | 자본 포지션 |
| GET | `/api/capital/trend` | 자본 추이 |
| GET | `/api/capital-optimizer/rwa-optimization` | RWA 최적화 |
| GET | `/api/capital-optimizer/pricing-suggestion/{id}` | 가격 제안 |
| GET | `/api/portfolio/strategy-matrix` | 전략 매트릭스 |
| GET | `/api/portfolio/concentration` | 집중도 분석 |
| GET | `/api/limits` | 한도 목록 |
| GET | `/api/limits/check` | 한도 체크 |
| GET | `/api/stress-test/scenarios` | 시나리오 목록 |
| POST | `/api/stress-test/run` | 스트레스테스트 실행 |
| GET | `/api/models` | 모델 목록 |
| GET | `/api/models/backtest/summary` | 백테스트 요약 |
| GET | `/api/models/override-performance` | Override 성과 |
| GET | `/api/models/vintage-analysis` | 빈티지 분석 |
| GET | `/api/models/specifications/{id}` | 모델 사양 |
| GET | `/api/customers` | 고객 목록 |
| GET | `/api/ews/summary` | EWS 요약 |
| GET | `/api/portfolio-optimization/...` | 포트폴리오 최적화 |

대부분의 GET 엔드포인트는 `?region=CAPITAL|DAEGU_GB|BUSAN_GN` 파라미터로 지역 필터링을 지원합니다.

전체 API 문서는 서버 실행 후 http://localhost:8000/docs 에서 확인

---

## 데이터 구조

### 주요 테이블 및 데이터량

| 테이블 | 설명 | 레코드 수 |
|--------|------|----------:|
| customer | 기업 고객 | ~400건 |
| loan_application | 여신 신청 | ~1,500건 |
| credit_rating_result | 신용평가 | ~1,500건 |
| risk_parameter | 리스크 파라미터 | ~1,500건 |
| facility | 여신 시설 | ~1,200건 |
| pricing_result | 가격결정 결과 | ~1,200건 |
| collateral | 담보 | ~500건 |
| portfolio_summary | 포트폴리오 집계 | ~200건 |
| override_monitoring | Override 모니터링 | ~50건 |
| override_outcome | Override 성과 | ~50건 |
| vintage_analysis | 빈티지 분석 | ~170건 |
| grade_backtest | 등급 백테스트 | ~36건 |
| model_registry | 모델 레지스트리 | 5건 |
| model_version | 모델 버전 | 15건 |
| model_performance_log | 모델 성능 로그 | ~125건 |
| ews_alert | 조기경보 | ~210건 |
| audit_log | 감사 로그 | ~500건 |

### 데이터 특징

- **고객 규모 분포**: 대기업, 중견, 중소, 소호
- **지역 분포**: 수도권(CAPITAL), 대구경북(DAEGU_GB), 부산경남(BUSAN_GN)
- **업종**: 제조업, 서비스업, 건설업, 부동산, 금융, 에너지, 무역 등
- **신용등급**: 20단계 (AAA ~ D), 투자등급 비율 약 64%
- **기간**: 2021년 1월 ~ 2025년 1월

상세 데이터 보고서: [docs/DATA_REPORT.md](docs/DATA_REPORT.md)

### 데이터 재생성

```bash
cd database
python generate_data.py
```

---

## 주요 모델 이론

### PD 모델 (부도확률)

- **이론**: Merton 구조모형, 축약형 모형, 로지스틱 회귀
- **수식**: `P(Default) = 1 / (1 + exp(-(β₀ + β₁X₁ + ... + βₙXₙ)))`

### LGD 모델 (부도시손실률)

- **이론**: Workout LGD, Market LGD
- **수식**: `LGD = 1 - Σ(Rᵢ/(1+r)^tᵢ) / EAD`

### RAROC 가격결정

- **수식**: `RAROC = (이자수익 - 조달비용 - 운영비 - EL) / Economic Capital`
- **비용률**: 조달비용률 4.3% + 운영비률 0.5% = 총비용률 4.8%
- **Economic Capital**: RWA x 8%
- **Hurdle Rate**: 15%

모델 상세 사양은 시스템 내 모델관리 > 모델 상세 모달에서 확인 가능

---

## 데모 시나리오

### 시나리오 1: 자본효율성 극대화
1. 대시보드에서 현재 자본비율 확인
2. 자본최적화에서 RWA 비효율 익스포저 식별
3. 여신신청 화면에서 RAROC 기반 가격 조정

### 시나리오 2: 모델 검증
1. 모델관리에서 백테스트 결과 확인
2. Override 성과 분석으로 전문가 판단 검증
3. 빈티지 분석으로 코호트별 연체 패턴 분석

### 시나리오 3: 스트레스 대응
1. 스트레스테스트로 경기 침체 시나리오 분석
2. 포트폴리오에서 업종 전략 조정
3. 한도관리에서 고위험 업종 한도 축소

---

## 변경 이력

### v1.1.0 (2026-02)

**지역 필터링 기능 추가**
- 전체 페이지에 지역별(수도권/대구경북/부산경남) 원클릭 필터 버튼 적용
- `RegionFilter` 공통 컴포넌트 도입
- `region_helper.py` 백엔드 헬퍼 모듈로 지역 필터 쿼리 통합

**RAROC 산출식 정합성 개선**
- 정확한 공식 적용: `(이자수익 - 조달비용(4.3%) - 운영비(0.5%) - EL) / EC`
- Dashboard summary/kpis 엔드포인트 산출식 통일
- `pricing_result.expected_raroc` 전건 재계산 (155% → ~14.6%)
- 포트폴리오 RAROC을 raw 테이블에서 직접 계산하여 일관성 확보

**모델관리(MRM) 개선**
- PD Backtest 탭: 모델별 필터 버튼 (기업신용평가/소호신용평가)
- Vintage 분석 탭: 코호트 유형별 필터 버튼 (전체/OVERALL/GRADE/INDUSTRY)
- Override 성과 분석: Type I/II Error 분석, 방향별 정확도
- 모델 활성 카운트 수정 (PRODUCTION 상태 인식)

**데이터 품질 개선**
- `grade_backtest`, `vintage_analysis`, `override_outcome` 테이블 생성 및 데이터 투입
- 여신신청 심사 단계 데이터 정비 (current_stage 할당, status 매핑)
- 한도관리 NULL 나눗셈 오류 수정
- 자본비율 추이 데이터 범위 확대 (최대 3년)
- 스트레스테스트 단위 버그 수정

**UI/UX 개선**
- 모든 지역 필터를 `<select>` 드롭다운에서 원클릭 버튼 그룹으로 변경
- API 에러 시 무한 로딩 방지 (catch 블록에서 빈 데이터 설정)
- TypeScript 빌드 에러 전수 수정

### v1.0.0 (2026-01)
- 초기 PoC 릴리스
- 11개 메뉴 구현 (Dashboard, 여신신청, 자본관리, 자본최적화, 포트폴리오, 포트폴리오최적화, 한도관리, 스트레스테스트, 모델관리, 고객관리, EWS)

---

## 라이선스

이 프로젝트는 데모 및 교육 목적으로 제작되었습니다.

MIT License

---

*iM뱅크 기업여신심사시스템 개념검증(PoC) 데모*
