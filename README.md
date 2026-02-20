# iM뱅크 CLMS — 여신생애주기관리시스템

**Credit Lifecycle Management System**

기업여신의 심사·실행·모니터링·회수까지 전체 생애주기를 통합 관리하는 PoC 시스템입니다.
Basel II/III IRB 방식의 신용리스크 계량화 체계를 기반으로, 19개 화면·133개 API·49개 DB 테이블로 구성됩니다.

![Version](https://img.shields.io/badge/version-1.2.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![React](https://img.shields.io/badge/react-18.2-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 목차

- [개요](#개요)
- [주요 기능 (19개 화면)](#주요-기능-19개-화면)
- [핵심 수리 모형](#핵심-수리-모형)
- [시스템 아키텍처](#시스템-아키텍처)
- [프로젝트 구조](#프로젝트-구조)
- [설치 및 실행](#설치-및-실행)
- [API 엔드포인트](#api-엔드포인트)
- [데이터 모델](#데이터-모델)
- [시스템 상수 및 가정치](#시스템-상수-및-가정치)
- [변경 이력](#변경-이력)
- [라이선스](#라이선스)

---

## 개요

### 핵심 가치

| 영역 | 내용 |
|------|------|
| **리스크 기반 의사결정** | PD·LGD·EAD 모델 기반 과학적 심사, RAROC 가격결정 |
| **자본 효율성 최적화** | IRB RWA 산출, 포트폴리오 최적화, 리밸런싱 추천 |
| **규제 준수** | Basel III 자본비율, 스트레스 테스트, 모델 검증(MRM) |
| **선제적 리스크 관리** | 5채널 선행지표 EWS, 동적한도, ESG 연동 |
| **통합 모니터링** | 19개 대시보드, 지역별 필터, 고객 수익성 분석 |

### 시스템 범위

```
전략계층: 대시보드 · 자본관리 · 포트폴리오 전략 · 스트레스 테스트 · 자본 최적화
전술계층: 한도관리 · 동적한도 · 여신심사 · 가격결정(What-if)
운영계층: 고객관리 · 여신실행 · 담보관리 · 부실채권(Workout)
분석계층: 조기경보(EWS) · 모델관리(MRM) · 고객수익성 · 포트폴리오 최적화 · ESG · ALM
```

---

## 주요 기능 (19개 화면)

### 1. 전략 대시보드 (Dashboard)
- 자본비율 현황 (BIS, CET1, Tier1, 레버리지)
- 포트폴리오 KPI: RAROC, 평균 PD/LGD, 대표등급
- EWS 경보 요약, 자본비율 추이 차트, 포트폴리오 분포
- **지역별 필터링** (수도권/대구경북/부산경남)

### 2. 여신심사 (Applications)
- 신청서 접수 → 서류심사 → 신용분석 → 심사위원회 → 최종승인 단계 관리
- What-if 시뮬레이션: 금리·만기 변경에 따른 RAROC 즉시 산출
- FTP 테너별 조달금리 자동 적용, 등급-PD 매핑(16단계)

### 3. 자본관리 (Capital)
- BIS/CET1/Tier1/레버리지 비율 추이 분석 (최대 3년)
- RWA 구성 분석, 자본 포지션, 세그먼트별 자본예산
- 신규 익스포저 시뮬레이션

### 4. 자본 효율성 최적화 (Capital Optimizer)
- RWA 밀도(Density) 분석: 산업별 RWA/Exposure 비율
- 자본배분 최적화, 동적 가격 제안(RAROC 기반)
- 포트폴리오 리밸런싱 추천, 효율성 대시보드

### 5. 포트폴리오 전략 (Portfolio)
- 산업-등급 전략 매트릭스 (EXPAND/SELECTIVE/MAINTAIN/REDUCE/EXIT)
- 집중도 분석: HHI 지수, Top 10 고객, Top 5 차주그룹
- 산업별 RAROC·PD·LGD·RWA 상세 분석

### 6. 포트폴리오 최적화 (Portfolio Optimization)
- 3가지 최적화: RAROC 극대화, RWA 최소화, Risk Parity
- 효율적 프론티어, 현재 vs 최적 배분 비교
- 제약조건: BIS ≥ 11%, HHI ≤ 25%, 단일차주 ≤ 10%

### 7. 한도관리 (Limits)
- 다차원 한도: 단일차주, 동일그룹, 업종, 등급
- 한도 소진율 추적, 사전 한도체크, 경보 (WARNING/BREACH)

### 8. 동적 한도관리 (Dynamic Limits)
- 경기순환 연동 자동 한도 조정
- 확장기 +15%, 수축기 -25% 범위 내 동적 운영

### 9. 스트레스 테스트 (Stress Test)
- 5단계 시나리오: BASELINE → MILD → MODERATE → SEVERE → EXTREME
- GDP·금리·실업률 충격 → PD/LGD/RWA 영향도 산출
- 산업별 민감도 계수 적용, 자본비율 영향 분석

### 10. 모델관리 — MRM (Models)
- 5개 모델 레지스트리: PD 기업/소호, LGD, EAD, Pricing
- 성능 모니터링: Gini, KS, AUROC, PSI, AR Ratio
- **PD 백테스트**: 이항검정 기반 (p-value < 0.05 Warning, < 0.01 Fail)
- **Override 성과**: Type I/II Error, 방향별 정확도 (임계치: 최대 15%, Type I ≤ 5%)
- **빈티지 분석**: MOB 3/6/12/24개월, 코호트별 연체·부도 추적
- Champion-Challenger 비교, 모델 상세 사양 모달(수학 공식 포함)

### 11. 고객관리 (Customers / Customer Browser)
- 기업 고객 통합 조회 (~1,010건)
- 업종·규모·등급별 필터링, 고객별 여신 현황

### 12. 조기경보 — EWS (EWS Advanced) ★
6개 탭으로 구성된 다채널 선행지표 기반 조기경보 체계:

| 탭 | 내용 | 선행성 |
|----|------|--------|
| **통합 대시보드** | 5채널 종합점수, 등급 분포, Watchlist | — |
| **거래행태** | 한도소진율, 결제지연, 예금유출, 당좌부도 | 3-6개월 |
| **공적정보** | 세금체납, 가압류, 감사의견, 경영진변동 | 1-3개월 |
| **시장신호** | 주가, CDS, Distance-to-Default (상장기업) | 즉시-1개월 |
| **뉴스감성** | NLP 감성분석, 부정감성 기업 | 1-3개월 |
| **공급망** | 거래처 리스크 전이, 연쇄부도 확률 | 3-6개월 |

- **EWS 등급**: NORMAL(≥75) / WATCH(≥55) / WARNING(≥35) / CRITICAL(<35)
- **가중치**: 상장 — 거래 25% + 공적 15% + 시장 15% + 뉴스 15% + 공급망 15% + 재무 15%
- **가중치**: 비상장 — 거래 30% + 공적 20% + 뉴스 20% + 공급망 15% + 재무 15%
- EWS 등급 산정 방법론 모달 (논문 수준 설명, 참고문헌 포함)

### 13. 고객 수익성 (Customer Profitability)
- RBC(Relationship-Based Costing) 체계: 여신·예금·수수료·FX 이익 통합
- 고객 RAROC, 고객생애가치(CLV), Cross-sell 기회, 이탈 리스크

### 14. 담보 모니터링 (Collateral Monitoring)
- LTV(Loan-to-Value) 실시간 추적 (경보 기준: 80%)
- 부동산 시세지수 연동 감정가 변동 모니터링

### 15. 부실채권 관리 (Workout)
- 회수 시나리오 분석 (금리감면, 만기연장, 원금감면, 출자전환)
- 예상회수율 30~80%, 시나리오별 NPV 산출

### 16. ESG 리스크 (ESG)
- ESG 종합점수: E(35%) + S(30%) + G(35%)
- 등급별 PD·금리 가감 (A등급: PD -0.2%p, -10bp)
- 녹색금융 상품 관리 (RWA 할인, 금리 우대)

### 17. 금리리스크 관리 — ALM
- 금리갭 분석 (8개 만기 버킷: 1M ~ 5Y+)
- NIM 민감도, 듀레이션 갭, EVE 변동
- 5가지 금리 시나리오 (평행이동, 스티프닝, 플래트닝, 역전)
- 헤지 효과성 평가 (목표 ≥ 80%)

---

## 핵심 수리 모형

### RWA 산출 — Basel IRB 공식

```
자산상관계수:
  R = 0.12 × (1-e^(-50·PD))/(1-e^(-50)) + 0.24 × [1 - (1-e^(-50·PD))/(1-e^(-50))]

만기조정:
  b = (0.11852 - 0.05478 × ln(max(PD, 0.0001)))²

자본요구량:
  K = LGD × [Φ(Φ⁻¹(PD)/√(1-R) + √(R/(1-R))×Φ⁻¹(0.999)) - PD×LGD]
  K_adj = K × (1+(M-2.5)×b) / (1-1.5×b)

위험가중자산:
  RWA = K_adj × 12.5 × EAD
```

### RAROC (Risk-Adjusted Return on Capital)

```
개별 건: RAROC = (A×r - A×FTP - A×0.005 - PD×LGD×A) / (RWA × 10.5%)
포트폴리오: RAROC = (Σ(Oi×ri) - ΣOi×0.048 - ΣELi) / (ΣRWA×0.105)

비용률: 조달(FTP 테너별) + 운영(0.5%) — 포트폴리오 총비용률 4.8%
경제적자본: EC = RWA × 10.5% (BIS 8% + 보전완충 2.5%)
허들레이트: 12%
```

### 가격결정 (Pricing)

```
r_final = r_base(3.5%) + FTP spread(0.5%) + Credit spread + Opex(0.2%) + Margin(1.0%)
        + Strategy adj + Collateral adj

Credit spread = EL spread + UL spread
  EL spread = PD × LGD
  UL spread = EL spread × 0.5 × Hurdle rate(12%)
```

### 스트레스 테스트

```
PD_stressed = min(PD_base × F_pd × S_industry, 0.30)
LGD_stressed = min(LGD_base × F_lgd, 0.70)
BIS_stressed = Total Capital / RWA_stressed

F_pd: BASELINE=1.0, MILD=1.3, MODERATE=1.8, SEVERE=2.5, EXTREME=3.5
```

### EWS 종합점수

```
상장:   S = 0.25×Txn + 0.15×Pub + 0.15×Mkt + 0.15×News + 0.15×Supply + 0.15×Fin
비상장: S = 0.30×Txn + 0.20×Pub + 0.20×News + 0.15×Supply + 0.15×Fin

등급: NORMAL(≥75) / WATCH(≥55) / WARNING(≥35) / CRITICAL(<35)
```

상세 수식은 [기술 보고서](CLMS_Technical_Report.md) 참조.

---

## 시스템 아키텍처

```
┌──────────────────────────────────────────────────────────────┐
│                     Frontend (React 18 + TypeScript)          │
│  19 Pages · RegionFilter · Recharts · Tailwind CSS · Vite    │
├──────────────────────────────────────────────────────────────┤
│                     Backend (FastAPI + SQLAlchemy)             │
│  18 API Routers · 133 Endpoints · calculations.py (수리엔진)  │
├──────────────────────────────────────────────────────────────┤
│                     Database (SQLite)                          │
│  49 Tables · ~1,010 Customers · 3 Regions · ~45,800 EWS rows │
└──────────────────────────────────────────────────────────────┘
```

---

## 프로젝트 구조

```
imbank-clms-demo/
├── backend/
│   ├── app/
│   │   ├── api/                    # API 엔드포인트 (18개 모듈)
│   │   │   ├── dashboard.py        # 전략 대시보드
│   │   │   ├── applications.py     # 여신심사
│   │   │   ├── capital.py          # 자본관리
│   │   │   ├── capital_optimizer.py # 자본 효율성
│   │   │   ├── portfolio.py        # 포트폴리오 전략
│   │   │   ├── portfolio_optimization.py
│   │   │   ├── limits.py           # 한도관리
│   │   │   ├── dynamic_limits.py   # 동적한도
│   │   │   ├── stress_test.py      # 스트레스 테스트
│   │   │   ├── models.py           # 모델관리 (MRM)
│   │   │   ├── model_inference.py  # 모델 추론
│   │   │   ├── customers.py        # 고객관리
│   │   │   ├── ews_advanced.py     # 조기경보 (24 endpoints)
│   │   │   ├── customer_profitability.py
│   │   │   ├── collateral_monitoring.py
│   │   │   ├── workout.py          # 부실채권
│   │   │   ├── esg.py              # ESG 리스크
│   │   │   ├── alm.py              # 금리리스크
│   │   │   └── region_helper.py    # 지역 필터 헬퍼
│   │   ├── services/
│   │   │   └── calculations.py     # 핵심 수리 모형 엔진
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   └── main.py
│   ├── data/
│   │   └── seed_data.py            # 기초 시드 데이터
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── index.ts            # Card, StatCard, Badge, Table, Modal
│   │   │   ├── Layout.tsx
│   │   │   └── RegionFilter.tsx
│   │   ├── pages/                  # 19개 페이지
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Applications.tsx
│   │   │   ├── Capital.tsx
│   │   │   ├── CapitalOptimizer.tsx
│   │   │   ├── Portfolio.tsx
│   │   │   ├── PortfolioOptimization.tsx
│   │   │   ├── Limits.tsx
│   │   │   ├── DynamicLimits.tsx
│   │   │   ├── StressTest.tsx
│   │   │   ├── Models.tsx
│   │   │   ├── Customers.tsx
│   │   │   ├── CustomerBrowser.tsx
│   │   │   ├── EWSAdvanced.tsx     # 6탭 컨트롤러
│   │   │   ├── CustomerProfitability.tsx
│   │   │   ├── CollateralMonitoring.tsx
│   │   │   ├── Workout.tsx
│   │   │   ├── ESG.tsx
│   │   │   ├── ALM.tsx
│   │   │   └── ews/                # EWS 서브 컴포넌트
│   │   │       ├── EWSIntegratedDashboard.tsx
│   │   │       ├── EWSTransactionBehavior.tsx
│   │   │       ├── EWSPublicRegistry.tsx
│   │   │       ├── EWSMarketSignals.tsx
│   │   │       ├── EWSNewsSentiment.tsx
│   │   │       └── EWSSupplyChain.tsx
│   │   ├── utils/
│   │   │   ├── api.ts              # API 클라이언트 (15개 그룹)
│   │   │   └── format.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── database/
│   ├── imbank_demo.db              # SQLite 데이터베이스
│   ├── schema.sql                  # 스키마 정의 (49 tables)
│   ├── schema_ews_leading.sql      # EWS 선행지표 스키마
│   ├── generate_extension_data.py  # 확장 데이터 생성
│   └── generate_ews_leading_data.py # EWS 선행지표 데이터 생성
│
├── CLMS_Technical_Report.md        # 기술 보고서 (전체 산출식)
├── start.sh
├── README.md
└── .gitignore
```

---

## 설치 및 실행

### 사전 요구사항

- Python 3.11+
- Node.js 18+
- npm

### 1. 저장소 클론

```bash
git clone https://github.com/your-username/imbank-clms-demo.git
cd imbank-clms-demo
```

### 2. Backend

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r backend/requirements.txt

cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. 접속

| 서비스 | URL |
|--------|-----|
| 프론트엔드 | http://localhost:3000 |
| 백엔드 API | http://localhost:8000 |
| Swagger 문서 | http://localhost:8000/docs |

### 간편 실행

```bash
cd imbank-clms-demo
(cd backend && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &) && \
(cd frontend && npm run dev)
```

### 종료

```bash
lsof -ti:8000 | xargs kill 2>/dev/null
lsof -ti:3000 | xargs kill 2>/dev/null
```

---

## API 엔드포인트

총 **133개** 엔드포인트. 대부분 `?region=CAPITAL|DAEGU_GB|BUSAN_GN` 파라미터 지원.

### Dashboard (5)
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/dashboard/summary` | 대시보드 요약 (RAROC, 자본, 포트폴리오) |
| GET | `/api/dashboard/ews-alerts` | EWS 경보 목록 |
| GET | `/api/dashboard/kpis` | KPI 현황 |
| GET | `/api/dashboard/capital-trend` | 자본비율 추이 |
| GET | `/api/dashboard/portfolio-distribution` | 산업·등급·규모 분포 |

### Applications (7)
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/applications/` | 여신신청 목록 |
| GET | `/api/applications/pending` | 대기 심사 |
| GET | `/api/applications/summary` | 심사 요약 통계 |
| GET | `/api/applications/{id}` | 신청 상세 |
| POST | `/api/applications/simulate` | What-if 시뮬레이션 |
| PUT | `/api/applications/{id}/stage` | 단계 변경 |
| POST | `/api/applications/{id}/approve` | 승인/반려 |

### Capital (6) · Capital Optimizer (5)
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/capital/position` | 자본 포지션 |
| GET | `/api/capital/trend` | 비율 추이 |
| GET | `/api/capital/budget` | 자본 예산 |
| POST | `/api/capital/simulate` | 자본 시뮬레이션 |
| GET | `/api/capital-optimizer/rwa-optimization` | RWA 최적화 |
| GET | `/api/capital-optimizer/efficiency-dashboard` | 효율성 대시보드 |

### Portfolio (6) · Portfolio Optimization (7)
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/portfolio/strategy-matrix` | 전략 매트릭스 |
| GET | `/api/portfolio/concentration` | 집중도 (HHI) |
| GET | `/api/portfolio-optimization/dashboard` | 최적화 대시보드 |
| GET | `/api/portfolio-optimization/current-vs-optimal` | 현재 vs 최적 |

### Stress Test (4)
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/stress-test/scenarios` | 시나리오 목록 (5단계) |
| GET | `/api/stress-test/results` | 테스트 결과 |
| POST | `/api/stress-test/run` | 테스트 실행 |

### Models / MRM (12)
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/models/` | 모델 목록 (5개) |
| GET | `/api/models/performance` | 성능 로그 (Gini, KS, PSI) |
| GET | `/api/models/backtest-summary` | PD 백테스트 요약 |
| GET | `/api/models/model-backtest` | 모델별 백테스트 |
| GET | `/api/models/override-performance` | Override 성과 |
| GET | `/api/models/vintage-analysis` | 빈티지 분석 |
| GET | `/api/models/specifications` | 모델 사양 |

### EWS Advanced (24)
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/ews-advanced/integrated-dashboard` | 통합 대시보드 |
| GET | `/api/ews-advanced/composite-scores` | 종합점수 목록 |
| GET | `/api/ews-advanced/transaction-behavior/dashboard` | 거래행태 요약 |
| GET | `/api/ews-advanced/transaction-behavior/anomalies` | 이상징후 |
| GET | `/api/ews-advanced/transaction-behavior/{id}` | 고객별 시계열 |
| GET | `/api/ews-advanced/public-registry/customers` | 공적정보 기업목록 |
| GET | `/api/ews-advanced/public-registry/dashboard` | 공적정보 요약 |
| GET | `/api/ews-advanced/public-registry/{id}` | 고객별 이벤트 |
| GET | `/api/ews-advanced/market-signals/dashboard` | 시장신호 요약 |
| GET | `/api/ews-advanced/market-signals/alerts` | 시장 경보 |
| GET | `/api/ews-advanced/news-sentiment/dashboard` | 뉴스감성 요약 |
| GET | `/api/ews-advanced/news-sentiment/feed` | 뉴스 피드 |
| GET | `/api/ews-advanced/supply-chain/customers` | 공급망 기업목록 |
| GET | `/api/ews-advanced/supply-chain/dashboard` | 공급망 요약 |
| GET | `/api/ews-advanced/supply-chain/{id}/temporal` | 공급망 시계열 |

### 기타 모듈
| 모듈 | 엔드포인트 수 | 주요 기능 |
|------|-------------|----------|
| Dynamic Limits | 7 | 경기순환 연동 한도 |
| Customer Profitability | 6 | RBC, CLV, Cross-sell |
| Collateral Monitoring | 6 | LTV, 담보가치 추적 |
| Workout | 6 | 회수 시나리오 |
| ESG | 6 | ESG 점수, 녹색금융 |
| ALM | 7 | 금리갭, 듀레이션 |
| Model Inference | 8 | 모델 추론 |
| Customers | 4 | 고객 조회 |
| Limits | 7 | 한도 관리 |

전체 API 문서: http://localhost:8000/docs

---

## 데이터 모델

### 테이블 분류 (49개)

| 계층 | 테이블 수 | 주요 테이블 |
|------|----------|------------|
| **마스터** | 5 | customer(18col), borrower_group, industry_master |
| **운영** | 7 | facility(17col), loan_application(20col), risk_parameter(13col), credit_rating_result |
| **전술** | 6 | ftp_rate, pricing_result(23col), credit_spread, macro_indicator |
| **전략** | 9 | capital_position(13col), stress_scenario, limit_definition, portfolio_strategy |
| **기반** | 8 | model_registry, model_performance_log(15col), portfolio_summary, audit_log |
| **EWS 확장** | 6 | ews_transaction_behavior, ews_public_registry, ews_market_signal, ews_news_sentiment, ews_supply_chain_temporal, ews_composite_score |
| **기타 확장** | 8 | dynamic_limit_rule, customer_profitability(27col), collateral_valuation_history, optimal_allocation |

### 데이터 규모

| 구분 | 건수 |
|------|-----:|
| 고객 | ~1,010 |
| 여신 (facility) | ~1,200 |
| 리스크 파라미터 | ~1,500 |
| EWS 거래행태 시계열 | ~12,120 |
| EWS 시장신호 | ~3,636 |
| EWS 뉴스감성 | ~17,170 |
| EWS 공급망 시계열 | ~11,976 |
| EWS 공적정보 이벤트 | ~900 |
| 모델 성능 로그 | ~125 |
| **합계** | **~50,000+** |

### 데이터 재생성

```bash
# 기초 데이터
cd backend && python3 -c "from data.seed_data import seed_all; seed_all()"

# 확장 데이터 (동적한도, 수익성, 담보, Workout, ESG, ALM)
cd database && python3 generate_extension_data.py

# EWS 선행지표 데이터
cd database && python3 generate_ews_leading_data.py
```

---

## 시스템 상수 및 가정치

### 비용률

| 상수 | 값 | 설명 |
|------|-----|------|
| 조달비용률 (FUNDING_RATE) | 4.3% | 기본 FTP + 가산 |
| 운영비율 (OPEX_RATE) | 0.5% | |
| 총비용률 (COST_RATE) | 4.8% | 포트폴리오 대시보드 적용 |
| 경제적 자본비율 | 10.5% | BIS 8% + 보전완충 2.5% |
| 허들레이트 | 12% | 자기자본비용 |

### FTP 금리 커브 (KRW, 2026-02)

| 테너 | FTP 금리 |
|------|---------|
| 3개월 | 3.20% |
| 12개월 | 3.50% |
| 24개월 | 3.70% |
| 36개월 | 3.85% |
| 60개월 | 4.10% |

### 포트폴리오 RAROC (2026-02 기준)

| 지역 | RAROC |
|------|-------|
| 전체 | 11.09% |
| 수도권 | 14.13% |
| 대구경북 | 10.96% |
| 부산경남 | 8.34% |

### 스트레스 충격 계수

| 강도 | PD 배수 | LGD 배수 | RWA 배수 |
|------|---------|----------|----------|
| BASELINE | 1.0× | 1.0× | 1.0× |
| MILD | 1.3× | 1.1× | 1.1× |
| MODERATE | 1.8× | 1.3× | 1.25× |
| SEVERE | 2.5× | 1.5× | 1.4× |
| EXTREME | 3.5× | 1.8× | 1.6× |

### 등급-PD 매핑

| 등급 | PD | 등급 | PD | 등급 | PD |
|------|-----|------|-----|------|-----|
| AAA | 0.02% | A+ | 0.15% | BBB- | 1.85% |
| AA+ | 0.04% | A | 0.25% | BB+ | 3.00% |
| AA | 0.06% | A- | 0.45% | BB | 4.80% |
| AA- | 0.10% | BBB+ | 0.70% | BB- | 7.50% |
| | | BBB | 1.15% | B+/B/B- | 12/20/30% |

전체 수리 모형 및 상세 산출식: **[CLMS_Technical_Report.md](CLMS_Technical_Report.md)**

---

## 변경 이력

### v1.2.0 (2026-02)

**EWS 선행지표 체계 구축**
- 5채널 선행지표 기반 조기경보 전면 재구성 (6개 탭)
- 신규 테이블 6개 + 데이터 ~45,800건 (거래행태, 공적정보, 시장신호, 뉴스감성, 공급망)
- 상장/비상장 차등 가중치 종합점수, EWS 등급(NORMAL/WATCH/WARNING/CRITICAL)
- 거래행태 이상징후 탐지, 공적정보 이벤트 타임라인
- 시장신호 DD/CDS 모니터링 (상장기업), 뉴스감성 피드
- 공급망 리스크 전이 시계열, 기업 검색 UI (리스트 선택형)
- EWS 등급 산정 방법론 모달 (논문 수준, 학술 참고문헌 포함)
- 24개 신규 API 엔드포인트

**RAROC 현실화**
- 경제적자본 비율: 8% → 10.5% (BIS 8% + 보전완충 2.5%) — 전 모듈 통일
- FTP 커브 현실화: 3M=3.20%, 12M=3.50%, 36M=3.85%, 60M=4.10%
- 허들레이트: 15% → 12% (한국 은행 자기자본비용 수준)
- What-if RAROC 민감도 적정 범위로 조정

**기술 보고서**
- `CLMS_Technical_Report.md` 작성 (전체 산출식, 가정치, 시스템 구조 문서화)

### v1.1.0 (2026-02)

**지역 필터링 기능 추가**
- 전체 페이지에 지역별(수도권/대구경북/부산경남) 원클릭 필터 버튼 적용
- `RegionFilter` 공통 컴포넌트, `region_helper.py` 헬퍼 모듈

**RAROC 산출식 정합성 개선**
- Dashboard summary/kpis 산출식 통일 (raw 테이블 직접 계산)

**모델관리(MRM) 개선**
- PD Backtest: 모델별 필터 (기업/소호)
- Vintage 분석: 코호트 유형별 필터
- Override 성과: Type I/II Error 분석
- 모델 상세 사양 모달 (수학 공식, 이론적 배경)

**데이터 품질**
- `grade_backtest`, `vintage_analysis`, `override_outcome` 테이블 신규
- 여신신청 심사 단계 정비, 한도관리 NULL 오류 수정
- API 에러 시 무한 로딩 방지

### v1.0.0 (2026-01)
- 초기 PoC 릴리스
- 11개 메뉴 구현

---

## 라이선스

이 프로젝트는 데모 및 교육 목적으로 제작되었습니다.

MIT License

---

*iM뱅크 CLMS — 기업여신생애주기관리시스템 PoC*
