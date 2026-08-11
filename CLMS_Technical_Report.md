# iM뱅크 CLMS(여신생애주기관리시스템) 기술 보고서

**iM Bank Credit Lifecycle Management System — Technical Specification & Mathematical Framework**

**Version 1.1.0 | 2026년 2월**

> **문서 상태:** 이 문서는 2026년 2월 당시의 수리모형·설계 기준을 보존한 역사 문서입니다. 화면·API·테이블·데이터 건수는 현재값이 아닙니다. 현재 인벤토리는 [README](README.md), 은행 파일럿 준비도와 추가 기능은 [2026-08-11 은행 요구기능 갭 연구](docs/BANK_REQUIRED_CAPABILITIES_RESEARCH_2026-08-11.md)를 기준으로 보십시오.

---

## 목차

1. [서론](#1-서론)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [데이터 모델](#3-데이터-모델)
4. [핵심 수리 모형](#4-핵심-수리-모형)
5. [메뉴별 기능 및 산출식](#5-메뉴별-기능-및-산출식)
6. [시스템 상수 및 가정치](#6-시스템-상수-및-가정치)
7. [데이터 생성 방법론](#7-데이터-생성-방법론)
8. [모형 한계 및 향후 과제](#8-모형-한계-및-향후-과제)
9. [부록: API 엔드포인트 목록](#9-부록-api-엔드포인트-목록)

---

## 1. 서론

### 1.1 시스템 개요

iM뱅크 CLMS(Credit Lifecycle Management System)는 여신(대출)의 전체 생애주기를 통합 관리하는 시스템으로, 신용리스크 측정·한도관리·가격결정·포트폴리오 최적화·조기경보 등 은행 여신업무의 핵심 기능을 포괄한다. 본 시스템은 Basel II/III 내부등급법(IRB) 기반의 리스크 계량화 체계를 채택하며, 19개 화면, 133개 이상의 API 엔드포인트, 49개 데이터 테이블로 구성된다.

### 1.2 시스템의 범위

| 영역 | 기능 |
|------|------|
| **전략계층** | 대시보드, 자본관리, 포트폴리오 전략, 스트레스 테스트, 자본 최적화 |
| **전술계층** | 한도관리, 동적한도, 여신심사, 가격결정(What-if) |
| **운영계층** | 고객관리, 여신실행, 담보관리, 부실채권(Workout) |
| **분석계층** | 조기경보(EWS), 모델관리(MRM), 고객수익성, 포트폴리오 최적화, ESG, ALM |

### 1.3 이론적 기반

본 시스템의 신용리스크 모형은 다음의 학술적·규제적 프레임워크에 기초한다:

- **Basel II/III IRB Approach** (BCBS, 2006; 2017): 자본요구량 산출 공식
- **Vasicek (1991/2002) Single-Factor Model**: 자산상관계수 및 자본요구량 도출
- **Merton (1974) Structural Model**: 기업가치 기반 부도확률 이론
- **KMV Model (Crosbie & Bohn, 2003)**: Distance-to-Default 개념
- **RiskMetrics (J.P. Morgan, 1996)**: 시장리스크 측정 방법론
- **Altman Z-Score (1968)**: 재무비율 기반 부실예측

---

## 2. 시스템 아키텍처

### 2.1 기술 스택

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend Layer                         │
│  React 18 + TypeScript + Tailwind CSS + Recharts         │
│  19 Pages, RegionFilter Component, Centralized API       │
├─────────────────────────────────────────────────────────┤
│                    Backend Layer                          │
│  FastAPI (Python 3.x) + SQLAlchemy                       │
│  18 API Routers, 133+ Endpoints                          │
│  Services: calculations.py (수리 모형 엔진)               │
├─────────────────────────────────────────────────────────┤
│                    Data Layer                             │
│  SQLite (imbank_demo.db)                                 │
│  49 Tables, ~1,010 Customers, 3 Regions                  │
│  Pre-aggregated: portfolio_summary                       │
└─────────────────────────────────────────────────────────┘
```

### 2.2 프론트엔드 라우팅 구조

| 경로 | 컴포넌트 | 화면명 |
|------|----------|--------|
| `/` | Dashboard | 전략 대시보드 |
| `/applications` | Applications | 여신심사 |
| `/capital` | Capital | 자본관리 |
| `/capital-optimizer` | CapitalOptimizer | 자본 효율성 최적화 |
| `/portfolio` | Portfolio | 포트폴리오 전략 |
| `/limits` | Limits | 한도관리 |
| `/stress-test` | StressTest | 스트레스 테스트 |
| `/models` | Models | 모델관리(MRM) |
| `/customers` | Customers | 고객관리 |
| `/customer-browser` | CustomerBrowser | 고객 검색 |
| `/ews-advanced` | EWSAdvanced | 조기경보(EWS) — 6개 탭 |
| `/dynamic-limits` | DynamicLimits | 동적 한도관리 |
| `/customer-profitability` | CustomerProfitability | 고객 수익성 |
| `/collateral-monitoring` | CollateralMonitoring | 담보 모니터링 |
| `/portfolio-optimization` | PortfolioOptimization | 포트폴리오 최적화 |
| `/workout` | Workout | 부실채권 관리 |
| `/esg` | ESG | ESG 리스크 |
| `/alm` | ALM | 금리리스크(ALM) |

### 2.3 백엔드 API 구조

| API 모듈 | 엔드포인트 수 | 담당 기능 |
|----------|-------------|----------|
| `dashboard.py` | 5 | 전략 대시보드 |
| `applications.py` | 7 | 여신심사 |
| `capital.py` | 6 | 자본관리 |
| `capital_optimizer.py` | 5 | 자본 효율성 |
| `portfolio.py` | 6 | 포트폴리오 전략 |
| `limits.py` | 7 | 한도관리 |
| `stress_test.py` | 4 | 스트레스 테스트 |
| `models.py` | 12 | 모델관리(MRM) |
| `customers.py` | 4 | 고객관리 |
| `ews_advanced.py` | 24 | 조기경보(EWS) |
| `dynamic_limits.py` | 7 | 동적한도 |
| `customer_profitability.py` | 6 | 고객수익성 |
| `collateral_monitoring.py` | 6 | 담보관리 |
| `portfolio_optimization.py` | 7 | 포트폴리오 최적화 |
| `workout.py` | 6 | Workout |
| `esg.py` | 6 | ESG 리스크 |
| `alm.py` | 7 | ALM |
| `model_inference.py` | 8 | 모델 추론 |
| **합계** | **133** | |

---

## 3. 데이터 모델

### 3.1 테이블 분류 체계

#### 마스터 계층 (5개)

| 테이블 | 컬럼 수 | 설명 |
|--------|---------|------|
| `customer` | 18 | 고객 마스터 (region 포함) |
| `borrower_group` | 7 | 차주그룹 |
| `borrower_group_member` | 5 | 그룹 멤버십 |
| `industry_master` | 6 | 산업분류 |
| `product_master` | 5 | 상품분류 |

#### 운영 계층 (7개)

| 테이블 | 컬럼 수 | 설명 |
|--------|---------|------|
| `loan_application` | 20 | 여신신청 |
| `credit_rating_result` | 16 | 신용등급 결과 |
| `risk_parameter` | 13 | 리스크 파라미터 (PD, LGD, EAD, RWA, EL) |
| `collateral` | 11 | 담보 정보 |
| `facility` | 17 | 여신(실행) 현황 |
| `approval_history` | 10 | 승인이력 |
| `ews_alert` | 12 | EWS 경보 |

#### 전술 계층 (6개)

| 테이블 | 컬럼 수 | 설명 |
|--------|---------|------|
| `ftp_rate` | 8 | FTP 금리 커브 |
| `credit_spread` | 8 | 등급별 신용스프레드 |
| `pricing_result` | 23 | 가격결정 결과 |
| `macro_indicator` | 6 | 거시경제지표 정의 |
| `macro_indicator_value` | 7 | 거시경제지표 시계열 |
| `macro_adjustment_factor` | 8 | PIT 조정 계수 |

#### 전략 계층 (9개)

| 테이블 | 컬럼 수 | 설명 |
|--------|---------|------|
| `capital_position` | 13 | 자본 포지션 (BIS비율 등) |
| `capital_budget` | 14 | 자본 예산 배분 |
| `portfolio_strategy` | 13 | 포트폴리오 전략 |
| `industry_rating_strategy` | 7 | 산업-등급 전략 매트릭스 |
| `limit_definition` | 14 | 한도 정의 |
| `limit_exposure` | 9 | 한도 사용현황 |
| `limit_reservation` | 8 | 한도 예약 |
| `stress_scenario` | 13 | 스트레스 시나리오 |
| `stress_test_result` | 13 | 스트레스 테스트 결과 |

#### 기반 계층 (8개)

| 테이블 | 컬럼 수 | 설명 |
|--------|---------|------|
| `model_registry` | 10 | 모델 등록부 |
| `model_version` | 8 | 모델 버전 |
| `model_performance_log` | 15 | 모델 성능 모니터링 |
| `override_monitoring` | 13 | 재조정(Override) 모니터링 |
| `override_outcome` | ~10 | 재조정 성과 |
| `decision_snapshot` | 9 | 의사결정 스냅샷 |
| `audit_log` | 10 | 감사 로그 |
| `portfolio_summary` | 12 | 포트폴리오 사전집계 |

#### 확장 계층 (14개+)

EWS 선행지표(6개), 동적한도(3개), 고객수익성(2개), 담보(3개), 포트폴리오 최적화(2개), ESG, ALM, Workout 등

### 3.2 핵심 관계도

```
customer (1)──(N) facility (1)──(1) loan_application
    │                  │                    │
    │                  └──(1) risk_parameter─┘
    │
    ├──(N) credit_rating_result
    ├──(N) ews_alert
    ├──(N) ews_composite_score
    ├──(N) ews_transaction_behavior
    ├──(N) ews_public_registry
    ├──(N) ews_market_signal (상장기업만)
    └──(N) customer_profitability
```

---

## 4. 핵심 수리 모형

### 4.1 RWA 산출 — Basel IRB 공식

Basel II/III 내부등급법(Foundation IRB)에 의한 자본요구량(K) 및 위험가중자산(RWA) 산출식이다.

#### 자산상관계수 (Asset Correlation, R)

$$R = 0.12 \times \frac{1 - e^{-50 \cdot PD}}{1 - e^{-50}} + 0.24 \times \left(1 - \frac{1 - e^{-50 \cdot PD}}{1 - e^{-50}}\right)$$

- PD가 높을수록 R이 감소 (0.12에 수렴), PD가 낮을수록 R 증가 (0.24에 수렴)
- 범위: 0.12 ≤ R ≤ 0.24

#### 만기조정 계수 (Maturity Adjustment, b)

$$b = \left(0.11852 - 0.05478 \times \ln(\max(PD, 0.0001))\right)^2$$

#### 자본요구량 (Capital Requirement, K)

$$K = LGD \times \left[\Phi\left(\frac{\Phi^{-1}(PD)}{\sqrt{1-R}} + \sqrt{\frac{R}{1-R}} \times \Phi^{-1}(0.999)\right) - PD \times LGD\right]$$

$$K_{adj} = K \times \frac{1 + (M - 2.5) \times b}{1 - 1.5 \times b}$$

여기서:
- $\Phi$ : 표준정규분포 누적분포함수 (CDF)
- $\Phi^{-1}$ : 표준정규분포 역함수 (quantile function)
- $M$ : 잔존만기 (기본값: 2.5년)
- 0.999 : 99.9% 신뢰수준 (1년 부도확률)

#### 위험가중자산 (RWA)

$$RWA = K_{adj} \times 12.5 \times EAD$$

- 12.5 = 1 / 0.08 (최소자본비율 8%의 역수)

> **구현**: `backend/app/services/calculations.py:27-89`

### 4.2 예상손실 (Expected Loss, EL)

$$EL = PD \times LGD \times EAD$$

- PD: 부도확률 (연간, TTC 또는 PIT)
- LGD: 부도시손실률 (0 ~ 1)
- EAD: 부도시익스포저 (원)

> **구현**: `backend/app/services/calculations.py:92-94`

### 4.3 경제적 자본 (Economic Capital, EC)

$$EC = RWA \times 10.5\%$$

- BIS 최소 자본비율 8% + 자본보전완충자본 2.5% = 10.5%
- 이는 규제자본(Regulatory Capital)의 하한으로, 은행의 내부자본적정성평가(ICAAP) 기준

> **구현**: `backend/app/services/calculations.py:97-99`

### 4.4 RAROC (Risk-Adjusted Return on Capital)

#### 기본 공식

$$RAROC = \frac{\text{이자수익} - \text{조달비용} - \text{운영비} - EL}{EC}$$

#### 개별 건별 (What-if 분석)

$$RAROC = \frac{A \times r_{final} - A \times r_{FTP} - A \times r_{opex} - PD \times LGD \times A}{RWA(PD, LGD, A, M) \times 0.105}$$

여기서:
- $A$ : 대출금액 (원)
- $r_{final}$ : 최종 적용금리 (연율)
- $r_{FTP}$ : 내부자금이전가격 (Funds Transfer Pricing, 테너별)
- $r_{opex}$ : 운영비율 (0.5%)
- $M$ : 대출만기 (년)

#### 포트폴리오 수준 (대시보드)

$$RAROC_{portfolio} = \frac{\sum_i (O_i \times r_i) - \sum_i O_i \times 0.048 - \sum_i EL_i}{\sum_i RWA_i \times 0.105}$$

여기서:
- $O_i$ : i번째 여신의 잔액 (outstanding_amount)
- $r_i$ : i번째 여신의 최종금리 (final_rate)
- 0.048 : 총비용률 (조달 4.3% + 운영 0.5%)
- $EL_i$ : i번째 여신의 예상손실
- $RWA_i$ : i번째 여신의 위험가중자산

> **구현**: `backend/app/services/calculations.py:102-153`, `backend/app/api/dashboard.py:53-62`

### 4.5 가격결정 (Pricing) 모형

#### 금리 구성요소

$$r_{final} = r_{base} + s_{FTP} + s_{credit} + s_{opex} + s_{margin} + adj_{strategy} + adj_{collateral}$$

#### 신용스프레드 분해

$$s_{credit} = s_{EL} + s_{UL}$$

$$s_{EL} = PD \times LGD$$

$$s_{UL} = s_{EL} \times 0.5 \times r_{hurdle}$$

여기서:
- $r_{base}$ : 기준금리 (기본값 3.5%)
- $s_{FTP}$ : FTP 스프레드 (0.5%)
- $s_{opex}$ : 운영비 스프레드 (0.2%)
- $s_{margin}$ : 목표마진 (1.0%)
- $r_{hurdle}$ : 허들레이트 (12%)

#### 전략별 가감 조정

| 전략코드 | 가감 (bp) | 설명 |
|----------|----------|------|
| EXPAND | -20 | 확대 전략: 금리 인하 |
| SELECTIVE | 0 | 선별적 |
| MAINTAIN | +10 | 유지 |
| REDUCE | +30 | 축소 |
| EXIT | +100 | 퇴출: 금리 인상 |

#### 담보 가감

$$adj_{collateral} = \begin{cases} -30bp & \text{if 담보 있음} \\ 0 & \text{if 무담보} \end{cases}$$

> **구현**: `backend/app/services/calculations.py:156-205`

### 4.6 자본비율 체계

#### BIS 자기자본비율

$$BIS\ Ratio = \frac{CET1 + AT1 + T2}{RWA_{credit} + RWA_{market} + RWA_{operational}}$$

#### CET1 비율

$$CET1\ Ratio = \frac{CET1\ Capital}{Total\ RWA}$$

#### Tier1 비율

$$Tier1\ Ratio = \frac{CET1 + AT1}{Total\ RWA}$$

#### 레버리지 비율

$$Leverage\ Ratio = \frac{Tier1\ Capital}{Total\ Exposure}$$

> **구현**: `backend/app/services/calculations.py:224-256`

---

## 5. 메뉴별 기능 및 산출식

### 5.1 전략 대시보드 (Dashboard)

**화면 구성**: 자본현황 StatCard, 포트폴리오 KPI, EWS 경보 요약, 자본비율 추이 차트, 포트폴리오 분포 차트

**핵심 지표 산출**:

| 지표 | 산출식 | 데이터 소스 |
|------|--------|------------|
| BIS 비율 | capital_position.bis_ratio × 100 | capital_position 테이블 |
| 총 익스포저 | SUM(facility.approved_amount) | facility 테이블 |
| 평균금리 | AVG(facility.final_rate) × 100 | facility 테이블 |
| 가중PD | AVG(risk_parameter.ttc_pd) | risk_parameter 테이블 |
| 가중LGD | AVG(risk_parameter.lgd) | risk_parameter 테이블 |
| 포트폴리오 RAROC | 4.4절 포트폴리오 공식 | facility + risk_parameter |
| 대표등급 | MODE(credit_rating_result.final_grade) | credit_rating_result |

**지역 필터**: 모든 지표에 customer.region 기반 필터 적용 (자본현황 제외 — 은행 전체)

> **구현**: `backend/app/api/dashboard.py:20-143`

### 5.2 여신심사 (Applications)

**기능**: 여신신청 목록 조회, 심사 시뮬레이션, 단계별 진행, 승인/반려

**심사 시뮬레이션 산출**:
- 등급별 PD 매핑 → RWA 계산 → EC 계산 → RAROC 계산
- 한도 점검: limit_definition 대비 현재 사용량 + 신청금액

**등급-PD 매핑표**:

| 등급 | PD | 등급 | PD | 등급 | PD |
|------|-----|------|-----|------|-----|
| AAA | 0.02% | A+ | 0.15% | BBB- | 1.85% |
| AA+ | 0.04% | A | 0.25% | BB+ | 3.00% |
| AA | 0.06% | A- | 0.45% | BB | 4.80% |
| AA- | 0.10% | BBB+ | 0.70% | BB- | 7.50% |
| | | BBB | 1.15% | B+ | 12.00% |
| | | | | B / B- | 20% / 30% |

> **구현**: `backend/app/api/applications.py`, `backend/app/services/calculations.py:9-15`

### 5.3 자본관리 (Capital)

**화면 구성**: 자본 포지션 현황, BIS/CET1/Tier1/레버리지 비율 추이, 자본예산 배분, 자본 시뮬레이션

**자본 시뮬레이션**: 자본요소 변동 시 비율 변화를 즉시 계산
- 산출: 4.6절 자본비율 공식 적용

**자본 효율성** (Capital Optimizer):

$$RWA\ Density = \frac{RWA}{Exposure} \times 100\%$$

$$RORWA = \frac{Net\ Income}{RWA}$$

> **구현**: `backend/app/api/capital.py`, `backend/app/api/capital_optimizer.py`

### 5.4 포트폴리오 전략 (Portfolio)

**화면 구성**: 산업-등급 전략 매트릭스, 산업별 포트폴리오 지표, 집중도 분석

#### 전략 매트릭스

산업별 전략(EXPAND/SELECTIVE/MAINTAIN/REDUCE/EXIT) × 등급별 구간에 따라 전략적 포지셔닝 결정

#### 집중도 분석 — HHI (Herfindahl-Hirschman Index)

$$HHI = \sum_{i=1}^{N} \left(\frac{Exposure_i}{Total\ Exposure}\right)^2$$

- HHI < 0.10 : 분산 양호
- 0.10 ≤ HHI < 0.18 : 보통
- HHI ≥ 0.18 : 집중도 높음

#### 산업별 포트폴리오 지표

| 지표 | 산출식 |
|------|--------|
| 익스포저 | SUM(facility.outstanding_amount) |
| RWA | SUM(risk_parameter.rwa) |
| EL | SUM(risk_parameter.expected_loss) |
| 평균 PD | AVG(COALESCE(pit_pd, ttc_pd)) |
| 평균 LGD | AVG(risk_parameter.lgd) |
| RAROC | 4.4절 포트폴리오 공식 |

> **구현**: `backend/app/api/portfolio.py`, `backend/app/api/region_helper.py`

### 5.5 한도관리 (Limits)

**기능**: 한도 정의/현황, 산업별·고객별 한도 점검

**한도소진율**:

$$Utilization = \frac{Current\ Exposure}{Limit\ Amount} \times 100\%$$

**상태 분류**:
- NORMAL: < 80%
- WARNING: 80% ~ 100%
- BREACH: > 100%

### 5.6 동적 한도관리 (Dynamic Limits)

**기능**: 경기순환 연동 한도 자동 조정

**한도 조정 공식**:

$$Adjusted\ Limit = Base\ Limit \times (1 + Cycle\ Adjustment)$$

**경기순환 조정**:
| 경기국면 | 조정 범위 |
|----------|-----------|
| 확장기 | +10% ~ +15% |
| 정상기 | 0% |
| 수축기 | -15% ~ -25% |

> **구현**: `backend/app/api/dynamic_limits.py`

### 5.7 스트레스 테스트 (Stress Test)

**시나리오별 충격 계수**:

| 강도 | PD 배수 | LGD 배수 | RWA 배수 |
|------|---------|----------|----------|
| BASELINE | 1.0 | 1.0 | 1.0 |
| MILD | 1.3 | 1.1 | 1.1 |
| MODERATE | 1.8 | 1.3 | 1.25 |
| SEVERE | 2.5 | 1.5 | 1.4 |
| EXTREME | 3.5 | 1.8 | 1.6 |

**스트레스 PD 산출**:

$$PD_{stressed} = \min(PD_{base} \times F_{PD} \times S_{industry},\ 0.30)$$

여기서:
- $F_{PD}$ : 시나리오별 PD 충격 배수
- $S_{industry}$ : 산업별 민감도 계수

**산업별 민감도 계수**:

| 산업 | 민감도 | 산업 | 민감도 |
|------|--------|------|--------|
| 금융 | 0.8 | 부동산 | 1.1 |
| IT | 0.8 | 숙박/관광 | 1.5 |
| 제조 | 1.0 | 항공 | 1.8 |
| 건설 | 1.0 | 의료 | 0.9 |
| 도소매 | 1.0 | 기타 | 1.0 |

**자본비율 영향**:

$$BIS_{stressed} = \frac{Total\ Capital}{RWA_{stressed}}$$

$$\Delta BIS = BIS_{stressed} - BIS_{base}$$

> **구현**: `backend/app/api/stress_test.py`

### 5.8 모델관리 — MRM (Model Risk Management)

**5개 등록 모델**:

| 모델 ID | 명칭 | 유형 |
|---------|------|------|
| MDL_CORP_RATING | 기업 신용평가 | PD |
| MDL_RETAIL_RATING | 소호 신용평가 | PD |
| MDL_LGD | 부도시손실률 | LGD |
| MDL_EAD | 부도시익스포저 | EAD |
| MDL_PRICING | 가격결정 | Pricing |

#### 5.8.1 모델 성능 지표

| 지표 | 설명 | 경보 기준 |
|------|------|----------|
| **Gini 계수** | 판별력 | Warning < 0.40, Critical < 0.35 |
| **KS 통계량** | Kolmogorov-Smirnov | 높을수록 양호 |
| **AUROC** | ROC 곡선 하 면적 | > 0.70 |
| **PSI** | 모집단 안정성 지수 | Warning > 0.10, Critical > 0.25 |
| **AR Ratio** | 실적/예측 비율 | Warning: <0.80 or >1.20 |

#### 5.8.2 PD 백테스트

**이항검정 (Binomial Test)**:

$$p\text{-value} = P(X \geq k\ |\ n, PD_{predicted})$$

$$X \sim Binomial(n, PD_{predicted})$$

- 신뢰수준: 95%
- Warning: p-value < 0.05
- Fail: p-value < 0.01

#### 5.8.3 Override 모니터링

| 임계치 | 기준 |
|--------|------|
| 최대 재조정률 | 15% |
| 최대 상향 비율 | 50% |
| Type I 오류 (상향→부도) | 5% |
| Type II 오류 (하향→정상) | 20% |
| 최소 정확도 | 70% |

#### 5.8.4 빈티지 분석

- MOB(Months on Book): 3, 6, 12, 24개월
- 코호트 유형: OVERALL, GRADE, INDUSTRY, SIZE
- 지표: 연체율, 부도율, 누적손실률

> **구현**: `backend/app/api/models.py`

### 5.9 조기경보 시스템 — EWS (Early Warning System)

본 시스템의 EWS는 6개 탭으로 구성된 다채널 선행지표 기반 조기경보 체계이다.

#### 5.9.1 5채널 선행지표 체계

| 채널 | 데이터 소스 | 선행성 | 이론적 근거 |
|------|-----------|--------|------------|
| **거래행태** | 자행 입출금·결제 | 3-6개월 | 유동성 악화 선행 신호 |
| **공적정보** | 세금체납·가압류·감사의견 | 1-3개월 | 법적·재무적 위기 신호 |
| **시장신호** | 주가·CDS·DD (상장기업) | 즉시-1개월 | Merton 구조모형 |
| **뉴스감성** | 뉴스 NLP 감성분석 | 1-3개월 | 시장심리 반영 |
| **공급망** | 거래처 리스크 전이 | 3-6개월 | 연쇄부도 이론 |
| **재무비율** | 재무제표 기반 (기존) | 후행 | 전통적 신용분석 |

#### 5.9.2 채널별 점수 산출

**거래행태 점수 (0-100)**:

$$S_{txn} = 100 - (U_{limit} \times 40 + D_{payment} \times 0.5 + R_{outflow} \times 30 + N_{overdraft} \times 5)$$

여기서:
- $U_{limit}$ : 한도소진율 (0~1)
- $D_{payment}$ : 결제지연일수
- $R_{outflow}$ : 예금유출률 (0~1)
- $N_{overdraft}$ : 당좌부도 횟수

**공적정보 점수 (0-100)**:

$$S_{pub} = 100 - (N_{unresolved} \times 15 + N_{severe} \times 20)$$

**시장신호 점수 (0-100, 상장기업만)**:

$$S_{mkt} = DD \times 15 + \max(0, 50 - S_{CDS} \times 0.1) - PD_{implied} \times 100$$

여기서:
- $DD$ : Distance-to-Default
- $S_{CDS}$ : CDS 스프레드 (bp)
- $PD_{implied}$ : 시장내재 부도확률

**뉴스감성 점수 (0-100)**:

$$S_{news} = 50 + \bar{s}_{sentiment} \times 50 - R_{negative} \times 30$$

#### 5.9.3 종합점수 산출 (Composite Score)

**상장기업**:

$$S_{composite} = 0.25 \times S_{txn} + 0.15 \times S_{pub} + 0.15 \times S_{mkt} + 0.15 \times S_{news} + 0.15 \times S_{supply} + 0.15 \times S_{fin}$$

**비상장기업**:

$$S_{composite} = 0.30 \times S_{txn} + 0.20 \times S_{pub} + 0.20 \times S_{news} + 0.15 \times S_{supply} + 0.15 \times S_{fin}$$

#### 5.9.4 EWS 등급 분류

| 등급 | 점수 범위 | 관리 조치 |
|------|----------|----------|
| **NORMAL** | ≥ 75 | 정기 모니터링 |
| **WATCH** | 55 ≤ S < 75 | 관찰 대상 등록, 모니터링 강화 |
| **WARNING** | 35 ≤ S < 55 | 여신관리 담당 지정, 한도 동결 |
| **CRITICAL** | < 35 | 여신회수 검토, Workout 이관 |

#### 5.9.5 추세 판정

$$\Delta S = S_{current} - S_{previous}$$

| 판정 | 조건 |
|------|------|
| IMPROVING | $\Delta S > +5$ |
| STABLE | $-5 \leq \Delta S \leq +5$ |
| DETERIORATING | $\Delta S < -5$ |

> **구현**: `backend/app/api/ews_advanced.py` (24개 엔드포인트), `database/generate_ews_leading_data.py`

### 5.10 고객 수익성 (Customer Profitability)

#### RBC (Relationship-Based Costing) 체계

**총이익**:

$$\Pi_{total} = \Pi_{loan} + \Pi_{deposit} + \Pi_{fee} + \Pi_{FX}$$

**여신이익**:

$$\Pi_{loan} = A \times r_{final} - A \times r_{funding} - EL - EC \times r_{hurdle}$$

**고객 RAROC**:

$$RAROC_{customer} = \frac{\Pi_{total}}{EC_{total}} \times 100$$

#### 고객생애가치 (CLV)

$$CLV = \sum_{t=1}^{T} \frac{\Pi_t \times p_{retention}^t}{(1 + r_{discount})^t}$$

여기서:
- $\Pi_t$ : t기 예상 이익
- $p_{retention}$ : 유지 확률
- $r_{discount}$ : 할인율 (자기자본비용)

**CLV 등급**:
| 점수 | 분류 | 전략 |
|------|------|------|
| 80-100 | VIP 전략고객 | 프리미엄 관리 |
| 60-79 | 성장잠재고객 | 확대 전략 |
| 40-59 | 유지 고객 | 효율적 관리 |
| 0-39 | 재평가 대상 | 구조조정 검토 |

> **구현**: `backend/app/api/customer_profitability.py`

### 5.11 담보 모니터링 (Collateral Monitoring)

**LTV (Loan-to-Value) 산출**:

$$LTV = \frac{Outstanding\ Amount}{Collateral\ Value} \times 100\%$$

**경보 기준**: LTV > 80%

**담보가치 변동 추적**: 부동산 시세지수(real_estate_index) 연동, 감정가 대비 시가 변동률 모니터링

> **구현**: `backend/app/api/collateral_monitoring.py`

### 5.12 포트폴리오 최적화 (Portfolio Optimization)

#### 목적함수 — RAROC 극대화

$$\max_{\mathbf{w}} \sum_{i=1}^{N} w_i \times RAROC_i$$

#### 제약조건

1. **완전투자**: $\sum_{i=1}^{N} w_i = 1$
2. **자본적정성**: $BIS\ Ratio \geq 11\%$
3. **집중도 제한**: $HHI \leq 0.25$
4. **단일차주 제한**: $\max(w_i) \leq 10\%$
5. **비음조건**: $w_i \geq 0$

#### 최적화 유형

| 유형 | 목적 |
|------|------|
| RAROC_MAX | RAROC 극대화 |
| RWA_MIN | RWA 최소화 (최소수익 제약) |
| RISK_PARITY | 리스크 균등 배분 |

#### 포트폴리오 리스크 (Unexpected Loss)

$$\sigma_p^2 = \sum_i \sum_j w_i w_j \rho_{ij} UL_i UL_j$$

#### 신용 Sharpe 비율

$$SR_{credit} = \frac{RAROC_{portfolio} - r_{hurdle}}{\sigma_{UL}}$$

> **구현**: `backend/app/api/portfolio_optimization.py`

### 5.13 부실채권 관리 (Workout)

**회수 시나리오 분석**:
- 예상회수율: 30% ~ 80%
- 시나리오별 NPV 산출
- 구조조정 유형: 금리감면, 만기연장, 원금감면, 출자전환

> **구현**: `backend/app/api/workout.py`

### 5.14 ESG 리스크 (ESG)

#### ESG 종합점수

$$S_{ESG} = 0.35 \times S_E + 0.30 \times S_S + 0.35 \times S_G$$

#### 신용리스크 가감

| ESG 등급 | 점수 범위 | PD 가감 | 금리 가감 |
|----------|----------|---------|----------|
| A | ≥ 80 | -0.2%p | -10bp |
| B | 65-79 | -0.1%p | -5bp |
| C | 50-64 | 0 | 0 |
| D | 35-49 | +0.2%p | +10bp |
| E | < 35 | +0.5%p | +25bp |

$$PD_{adjusted} = PD_{base} \times (1 + adj_{ESG})$$

#### 녹색금융 인센티브

| 상품 유형 | RWA 할인 | 금리 할인 |
|----------|----------|----------|
| 녹색채권 | 10-15% | 5-15bp |
| 지속가능연계대출 | 5-10% | 5-25bp |
| 신재생에너지 | 10-20% | 10-20bp |

> **구현**: `backend/app/api/esg.py`

### 5.15 금리리스크 관리 — ALM (Asset-Liability Management)

#### 금리갭 분석

$$Gap = A_{floating} - L_{floating}$$

- 양(+)의 갭: 금리 상승 시 NIM 증가
- 음(-)의 갭: 금리 상승 시 NIM 감소

#### NIM 민감도

$$\Delta NIM = \frac{Gap \times \Delta r}{A_{total}}$$

#### 듀레이션 갭

$$D_{gap} = D_A - \frac{L}{A} \times D_L$$

#### EVE 민감도

$$\Delta EVE = -D_{gap} \times A \times \Delta r$$

#### 금리 시나리오

| 시나리오 | 단기 충격 | 장기 충격 |
|----------|----------|----------|
| 평행 상승 | +100/+200bp | +100/+200bp |
| 평행 하락 | -100/-200bp | -100/-200bp |
| 스티프닝 | -50bp | +100bp |
| 플래트닝 | +100bp | -50bp |
| 역전 | +150bp | -100bp |

**만기 버킷**: 1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y, 5Y+

**헤지 효과성**:

$$H_{eff} = \frac{\Delta V_{hedged}}{\Delta V_{unhedged}}$$

- 목표: ≥ 80%

> **구현**: `backend/app/api/alm.py`

---

## 6. 시스템 상수 및 가정치

### 6.1 비용률 상수

| 상수 | 값 | 설명 | 적용 위치 |
|------|-----|------|----------|
| FUNDING_RATE | 4.3% | 조달비용률 | region_helper.py |
| OPEX_RATE | 0.5% | 운영비율 | region_helper.py, calculations.py |
| COST_RATE | 4.8% | 총비용률 (FUNDING + OPEX) | dashboard.py, region_helper.py |
| EC_RATIO | 10.5% | 경제적 자본 비율 (BIS 8% + 보전완충 2.5%) | 전 모듈 |
| HURDLE_RATE | 12% | 자기자본비용 | dashboard.py, calculations.py |

### 6.2 FTP 금리 커브 (KRW)

| 테너 | 최종 FTP 금리 |
|------|-------------|
| 3개월 | 3.20% |
| 12개월 | 3.50% |
| 24개월 | 3.70% |
| 36개월 | 3.85% |
| 60개월 | 4.10% |

- 원화 스왑금리 기반, 유동성 프리미엄 및 기간 프리미엄 포함
- 2026년 2월 기준 한국 시장금리 수준을 반영

### 6.3 Basel IRB 파라미터

| 파라미터 | 값 | 근거 |
|----------|-----|------|
| 자산상관계수 범위 | 0.12 ~ 0.24 | Basel II IRB 공식 |
| 신뢰수준 | 99.9% | Basel II 기준 |
| 기본 만기 | 2.5년 | Basel II 기본 가정 |
| RWA 승수 | 12.5 | 1/0.08 |
| 최소 PD | 0.0001 (0.01%) | 로그 계산 안정성 |

### 6.4 스트레스 테스트 가정

| 파라미터 | 가정 |
|----------|------|
| 최대 스트레스 PD | 30% (상한) |
| 최대 스트레스 LGD | 70% (상한) |
| PD 상한 클리핑 | min(stressed_pd, 0.30) |
| 자본 불변 가정 | 스트레스 중 자본 변동 없음 |

### 6.5 대시보드 RAROC 실측값 (2026-02 기준)

| 지역 | RAROC |
|------|-------|
| 전체 | 11.09% |
| 수도권 (CAPITAL) | 14.13% |
| 대구경북 (DAEGU_GB) | 10.96% |
| 부산경남 (BUSAN_GN) | 8.34% |

---

## 7. 데이터 생성 방법론

### 7.1 기초 데이터 (seed_data.py)

- **고객 수**: 1,010명 (기업 + 소호)
- **지역 분포**: 수도권(CAPITAL), 대구경북(DAEGU_GB), 부산경남(BUSAN_GN)
- **산업 분류**: 10개 산업 (금융, IT, 제조, 건설, 도소매, 의료, 부동산, 숙박, 항공, 기타)
- **규모 분류**: LARGE, MEDIUM, SMALL, SOHO
- **상장기업 비율**: ~30%

### 7.2 확장 데이터 (generate_extension_data.py)

| 모듈 | 데이터 건수 | 주요 가정 |
|------|-----------|----------|
| EWS 지표 | ~12,000 | 200고객 × 6개월 × 10지표 |
| 공급망 관계 | 500 | 의존도 0.1~0.9 |
| 외부신호 | 300 | 5가지 유형 |
| 동적한도 | ~200 | 24개월 경기순환 |
| 고객수익성 | 1,010 | 전 고객 대상 |
| 담보 | ~480 인덱스, ~6,000 이력 | 8지역 × 5유형 × 12개월 |
| Workout | 30건 | 고액 여신 대상 |
| ESG | 1,010 + 50 | 전 고객 + 녹색금융 |
| ALM | ~180 | 8만기버킷 × 7시나리오 |

### 7.3 EWS 선행지표 데이터 (generate_ews_leading_data.py)

| 테이블 | 건수 | 기간 |
|--------|------|------|
| ews_transaction_behavior | ~12,120 | 12개월 (2025-03~2026-02) |
| ews_public_registry | ~900 | 이벤트 기반 |
| ews_market_signal | ~3,636 | 상장 303사 × 12개월 |
| ews_news_sentiment | ~5,050 | 기사 단위 |
| ews_news_sentiment_monthly | ~12,120 | 월별 집계 |
| ews_supply_chain_temporal | ~11,976 | 거래처별 시계열 |
| **합계** | **~45,800** | |

- 신용등급 기반 위험 프로파일로 일관된 상관관계 생성
- 결정적 ID 포맷 사용 (UUID 충돌 방지)

### 7.4 규모별 승수

| 규모 | 승수 | 적용 |
|------|------|------|
| LARGE | 5.0x | 익스포저, 수익 규모 |
| MEDIUM | 2.0x | |
| SMALL | 1.0x | 기준 |
| SOHO | 0.5x | |

---

## 8. 모형 한계 및 향후 과제

### 8.1 모형 한계

1. **단일요인 모형(Single-Factor Model)**: 자산상관 구조가 단일 체계요인(systematic factor)에만 의존하여, 산업간·지역간 상이한 상관 구조를 완전히 포착하지 못함.

2. **상관계수의 정적 가정**: 자산상관계수 R이 PD만의 함수로 정의되어, 경기순환이나 위기 시의 상관관계 급등(correlation smile) 현상을 반영하지 못함.

3. **LGD의 경기순환 비의존**: 현재 LGD는 고정값으로 처리되나, 실제로는 경기 하강기에 LGD가 상승하는 경향(downturn LGD)이 있음.

4. **FTP 커브의 정적 가정**: FTP 금리가 고정되어 있어, 시장금리 변동에 따른 동적 조정이 반영되지 않음.

5. **EWS 가중치의 전문가 판단 의존**: 5채널 가중치가 통계적 최적화가 아닌 전문가 판단에 의해 설정되어, 데이터 기반 재보정이 필요할 수 있음.

6. **포트폴리오 최적화의 선형 가정**: 실제 신용 포트폴리오의 비선형 리스크 특성(꼬리 리스크, 극단 손실)이 충분히 반영되지 않음.

### 8.2 향후 과제

1. **다요인 모형(Multi-Factor Model)** 도입으로 산업별·지역별 상관 구조 세분화
2. **기계학습 기반 EWS**: 채널 가중치의 데이터 기반 자동 보정 (LASSO, Random Forest 등)
3. **동적 FTP**: 실시간 시장금리 연동 FTP 커브 자동 업데이트
4. **Downturn LGD 모형**: PIT LGD 추정을 위한 경기순환 조정 모형
5. **CVA/DVA 통합**: 거래상대방 신용리스크 가치조정 반영
6. **IFRS 9 통합**: 기대신용손실(ECL) 산출과 3-Stage 분류 체계 연동

---

## 9. 부록: API 엔드포인트 목록

### A. Dashboard (5)
- `GET /api/dashboard/summary` — 대시보드 요약
- `GET /api/dashboard/ews-alerts` — EWS 경보 목록
- `GET /api/dashboard/kpis` — KPI 현황
- `GET /api/dashboard/capital-trend` — 자본비율 추이
- `GET /api/dashboard/portfolio-distribution` — 포트폴리오 분포

### B. Applications (7)
- `GET /api/applications/` — 여신신청 목록
- `GET /api/applications/pending` — 대기 심사
- `GET /api/applications/summary` — 심사 요약
- `GET /api/applications/{id}` — 신청 상세
- `POST /api/applications/simulate` — 심사 시뮬레이션
- `PUT /api/applications/{id}/stage` — 단계 변경
- `POST /api/applications/{id}/approve` — 승인/반려

### C. Capital (6)
- `GET /api/capital/position` — 자본 포지션
- `GET /api/capital/trend` — 비율 추이
- `GET /api/capital/budget` — 자본 예산
- `POST /api/capital/simulate` — 자본 시뮬레이션
- `GET /api/capital/efficiency` — 자본 효율성

### D. Capital Optimizer (5)
- `GET /api/capital-optimizer/rwa-optimization` — RWA 최적화
- `GET /api/capital-optimizer/allocation-optimization` — 배분 최적화
- `GET /api/capital-optimizer/pricing-suggestion` — 가격 제안
- `GET /api/capital-optimizer/rebalancing-suggestions` — 리밸런싱
- `GET /api/capital-optimizer/efficiency-dashboard` — 효율성 대시보드

### E. Portfolio (6)
- `GET /api/portfolio/strategy-matrix` — 전략 매트릭스
- `GET /api/portfolio/concentration` — 집중도 분석
- `GET /api/portfolio/industry/{code}` — 산업별 상세
- `GET /api/portfolio/industry-region-analysis` — 산업-지역 분석

### F. Stress Test (4)
- `GET /api/stress-test/scenarios` — 시나리오 목록
- `GET /api/stress-test/results` — 테스트 결과
- `POST /api/stress-test/run` — 테스트 실행

### G. EWS Advanced (24)
- `GET /api/ews-advanced/feature-description/{id}`
- `GET /api/ews-advanced/indicators`
- `GET /api/ews-advanced/indicator-values/{customer_id}`
- `GET /api/ews-advanced/supply-chain/customers`
- `GET /api/ews-advanced/supply-chain/dashboard`
- `GET /api/ews-advanced/supply-chain/{customer_id}/temporal`
- `GET /api/ews-advanced/supply-chain/{customer_id}`
- `GET /api/ews-advanced/external-signals`
- `GET /api/ews-advanced/composite-scores`
- `GET /api/ews-advanced/dashboard`
- `GET /api/ews-advanced/transaction-behavior/dashboard`
- `GET /api/ews-advanced/transaction-behavior/anomalies`
- `GET /api/ews-advanced/transaction-behavior/{customer_id}`
- `GET /api/ews-advanced/public-registry/customers`
- `GET /api/ews-advanced/public-registry/dashboard`
- `GET /api/ews-advanced/public-registry/timeline`
- `GET /api/ews-advanced/public-registry/{customer_id}`
- `GET /api/ews-advanced/market-signals/dashboard`
- `GET /api/ews-advanced/market-signals/alerts`
- `GET /api/ews-advanced/market-signals/{customer_id}`
- `GET /api/ews-advanced/news-sentiment/dashboard`
- `GET /api/ews-advanced/news-sentiment/feed`
- `GET /api/ews-advanced/news-sentiment/{customer_id}`
- `GET /api/ews-advanced/integrated-dashboard`

### H. Models/MRM (12)
- `GET /api/models/` — 모델 목록
- `GET /api/models/{id}` — 모델 상세
- `GET /api/models/performance` — 성능 로그
- `GET /api/models/status` — 모델 상태
- `GET /api/models/overrides` — Override 목록
- `GET /api/models/champion-challenger` — 챔피언-챌린저
- `GET /api/models/backtest-summary` — 백테스트 요약
- `GET /api/models/model-backtest` — 모델별 백테스트
- `GET /api/models/override-performance` — Override 성과
- `GET /api/models/vintage-analysis` — 빈티지 분석
- `GET /api/models/vintage-detail` — 빈티지 상세
- `GET /api/models/specifications` — 모델 사양

### I~R. 기타 모듈
- **Limits** (7), **Dynamic Limits** (7), **Customers** (4)
- **Customer Profitability** (6), **Collateral Monitoring** (6)
- **Portfolio Optimization** (7), **Workout** (6)
- **ESG** (6), **ALM** (7), **Model Inference** (8)

---

**끝.**

*본 보고서는 iM뱅크 CLMS Demo v1.1.0 소스코드에서 직접 추출한 산출식과 파라미터를 기반으로 작성되었으며, 시스템 코드의 정확한 구현을 반영한다. 모든 수식과 상수는 `backend/app/services/calculations.py`, `backend/app/api/` 디렉토리 내 각 모듈 소스에서 검증 가능하다.*
