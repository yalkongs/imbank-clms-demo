# iM뱅크 CLMS — 여신 심사 고도화 & 부실 관리 고도화
## 구현 계획서 v1.0
> 작성일: 2026-02-20 | 프로젝트: imbank-clms-demo | 기준 버전: v1.2.0

---

## 목차

1. [배경 및 목표](#1-배경-및-목표)
2. [Gap 분석](#2-gap-분석)
3. [구현 대상 기능 정의](#3-구현-대상-기능-정의)
4. [전체 구현 계획 (Phase별)](#4-전체-구현-계획-phase별)
5. [파일별 변경사항 요약](#5-파일별-변경사항-요약)
6. [데이터 생성 계획](#6-데이터-생성-계획)
7. [구현 현황 체크리스트](#7-구현-현황-체크리스트)
8. [잔여 작업 (v2.0 이후)](#8-잔여-작업-v20-이후)

---

## 1. 배경 및 목표

### 프로젝트 목표
iM뱅크 기업여신의 **여신 심사 고도화**와 **부실 관리 체계화**를 목표로 현행 v1.2.0 시스템에 8개 신규 모듈을 추가 구현한다.

### 현재 시스템 규모 (v1.2.0 기준)
- UI 페이지: 19개
- API 엔드포인트: 133개
- DB 테이블: 49개
- 데이터 규모: ~50,000 레코드 / 28MB SQLite

### 추가 목표 규모 (v2.0 완성 후)
- UI 페이지: +5개 (24개)
- API 엔드포인트: +40개 (173개)
- DB 테이블: +11개 (60개)
- 데이터 규모: +~35,000 레코드

---

## 2. Gap 분석

### 2-1. 여신 심사 영역 현황

| 항목 | 현재 상태 | 문제점 | 심각도 |
|------|----------|--------|--------|
| 재무 분석 | `customer.asset_size`, `revenue_size` 2개 필드만 존재 | `applications.py:411` — 자산회전율 1개만 계산. DSCR·이자보상배율 없음 | ★★★ |
| 그룹 심사 | `borrower_group`, `borrower_group_member` 테이블 존재 | **어디서도 조회 안됨.** 계열사 합산 익스포저 관리 불가 | ★★★ |
| 코베넌트 | `approval_history.conditions TEXT` 필드 | 자연어 저장만 가능. 이행 모니터링·위반 트리거 없음 | ★★★ |
| 정기 재심사 | 없음 | `facility.maturity_date`만 있고 재심사 워크플로우 없음 | ★★ |

### 2-2. 부실 관리 영역 현황

| 항목 | 현재 상태 | 문제점 | 심각도 |
|------|----------|--------|--------|
| 자산건전성 분류 | `workout_case.case_status` (OPEN/IN_PROGRESS/...) | 금감원 기준 5단계 분류 없음. `facility`에 연체 필드 없음 | ★★★ |
| ECL 충당금 | `workout_case.provision_amount` 단순 금액 | IFRS 9 Stage 구분 없음. 산출 로직 없음 | ★★★ |
| 연체 관리 | 테이블 자체 없음 | EWS→Workout 연결 없음. DPD 추적 불가 | ★★★ |
| LGD 백테스트 | `model_performance_log` — PD 지표만 | 실측 LGD vs 추정 LGD 비교 없음 | ★★ |

---

## 3. 구현 대상 기능 정의

---

### Module 1: 재무제표 분석 고도화 (Financial Statement Analysis)

**목적**: 3개년 재무 데이터 기반 정량 심사 자동화 및 DSCR 기반 상환능력 검증

#### 핵심 지표 정의

```
안정성 지표
  부채비율     = 총부채 / 자기자본 × 100          (기준: ≤ 200%)
  유동비율     = 유동자산 / 유동부채 × 100         (기준: ≥ 100%)
  이자보상배율 = 영업이익 / 이자비용               (기준: ≥ 1.5배)
  차입금의존도 = 총차입금 / 총자산 × 100           (기준: ≤ 50%)

수익성 지표
  영업이익률   = 영업이익 / 매출액 × 100
  ROA          = 당기순이익 / 총자산 × 100
  ROE          = 당기순이익 / 자기자본 × 100

현금흐름 지표 (핵심)
  DSCR         = EBITDA / (원금상환액 + 이자비용)  (기준: ≥ 1.25)
  영업현금흐름비율 = 영업현금흐름 / 총부채

성장성 지표
  매출 성장률  = (매출_t - 매출_t-1) / |매출_t-1| × 100
  영업이익 성장률 YoY (%)

신용 위험 스코어링
  Altman Z'-Score (비상장 기업용)
  Z' = 0.717×X1 + 0.847×X2 + 3.107×X3 + 0.420×X4 + 0.998×X5
  X1=운전자본/총자산  X2=이익잉여금/총자산
  X3=EBIT/총자산      X4=자기자본/총부채  X5=매출/총자산
  판정: Z' > 2.9: SAFE, 1.23~2.9: GREY, < 1.23: DANGER
```

#### DB 신규 테이블

```sql
-- 재무제표 (3개년)
CREATE TABLE financial_statement (
    stmt_id          TEXT PRIMARY KEY,
    customer_id      TEXT NOT NULL,
    fiscal_year      INTEGER NOT NULL,
    stmt_type        TEXT DEFAULT 'ANNUAL',
    revenue          REAL,  -- 매출액
    operating_profit REAL,  -- 영업이익
    ebitda           REAL,  -- EBITDA
    interest_expense REAL,  -- 이자비용
    net_profit       REAL,  -- 당기순이익
    total_assets     REAL,  -- 총자산
    current_assets   REAL,  -- 유동자산
    total_debt       REAL,  -- 총부채
    current_debt     REAL,  -- 유동부채
    total_borrowing  REAL,  -- 총차입금
    equity           REAL,  -- 자기자본
    retained_earning REAL,  -- 이익잉여금
    working_capital  REAL,  -- 운전자본
    operating_cf     REAL,  -- 영업현금흐름
    audited          INTEGER DEFAULT 0,
    source           TEXT,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(customer_id, fiscal_year, stmt_type)
);

-- 재무비율 캐시 테이블
CREATE TABLE financial_ratio (
    ratio_id        TEXT PRIMARY KEY,
    customer_id     TEXT NOT NULL,
    fiscal_year     INTEGER NOT NULL,
    debt_ratio      REAL,  -- 부채비율
    current_ratio   REAL,  -- 유동비율
    ier             REAL,  -- 이자보상배율
    debt_dependency REAL,  -- 차입금의존도
    dscr            REAL,  -- DSCR
    op_margin       REAL,  -- 영업이익률
    roa             REAL,
    roe             REAL,
    revenue_growth  REAL,  -- 매출성장률 YoY
    op_growth       REAL,  -- 영업이익성장률 YoY
    altman_z        REAL,  -- Altman Z'-Score
    risk_signal     TEXT,  -- SAFE / GREY / DANGER
    calc_date       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(customer_id, fiscal_year)
);
```

#### API 설계

```
POST /api/financial/statement/{customer_id}       재무제표 입력
GET  /api/financial/ratios/{customer_id}          비율 조회 (3개년)
GET  /api/financial/trend/{customer_id}           추세 분석
GET  /api/financial/peer-comparison/{customer_id} 동업종 벤치마크
GET  /api/financial/summary/{application_id}      심사 화면 연동용
```

#### Frontend
- `Applications.tsx` 상세 — "재무분석" 탭 추가
- 3개년 주요 지표 Bar/Line Chart (Recharts)
- DSCR, Altman Z 신호등 (Green/Yellow/Red)
- 동업종 Percentile 위치 표시

---

### Module 2: 그룹여신 통합심사 (Group Credit Management)

**목적**: `borrower_group` 테이블 활성화 — 계열사 합산 익스포저 관리 및 전이 리스크 제어

#### 핵심 기능

```
그룹 구조 시각화
  모회사/자회사/관계사 지분 관계 (ownership_pct 활용)
  계열사별 여신 현황 및 상호보증 관계

그룹 합산 익스포저
  그룹 총 익스포저 = Σ(계열사 outstanding_amount)
  그룹 한도 사용률 = 그룹 총 익스포저 / group_limit
  신규 신청 후 한도 시뮬레이션

연대보증 리스크
  상호보증 비율 = 상호보증 건수 / 전체 여신 건수
  보증 전이: A사 부도 시 B사 추가 부담 시뮬레이션

그룹 한도 규제 체크
  단일 차주그룹 한도 (자기자본의 25%)
  그룹 내 최열위 등급 기준 PD 산출
```

#### DB 수정/추가

```sql
-- borrower_group 컬럼 추가
ALTER TABLE borrower_group ADD COLUMN group_pd REAL;
ALTER TABLE borrower_group ADD COLUMN group_grade TEXT;
ALTER TABLE borrower_group ADD COLUMN group_limit_ratio REAL;

-- 계열사 간 보증 관계 (신규)
CREATE TABLE group_guarantee (
    guarantee_id    TEXT PRIMARY KEY,
    group_id        TEXT NOT NULL,
    guarantor_id    TEXT NOT NULL,
    beneficiary_id  TEXT NOT NULL,
    guarantee_type  TEXT,  -- JOINT / INDIVIDUAL / MORTGAGE
    guarantee_amount REAL,
    effective_date  DATE,
    status          TEXT DEFAULT 'ACTIVE'
);
```

#### API 설계

```
GET  /api/group-credit/group/{group_id}            그룹 전체 현황
GET  /api/group-credit/customer/{customer_id}      고객이 속한 그룹 조회
GET  /api/group-credit/limit-check/{group_id}      그룹 한도 체크
GET  /api/group-credit/concentration               그룹 집중도 TOP 10
GET  /api/group-credit/guarantee-network/{group_id} 보증 관계망
POST /api/group-credit/simulate/{application_id}   신청 후 그룹 한도 시뮬레이션
```

#### Frontend
- `Applications.tsx` — "그룹현황" 탭 (계열사 목록 + 그룹 한도 게이지)

---

### Module 3: 코베넌트 관리 (Covenant Management)

**목적**: 조건부 승인을 구조화하고 이행 여부를 주기적으로 모니터링하여 기한이익상실 트리거 연동

#### 코베넌트 유형 정의

```
재무 코베넌트 (Financial) — 정량 측정, 자동 체크
  FC01: 부채비율 ≤ N%         (반기/연간)
  FC02: DSCR ≥ N배            (연간)
  FC03: 이자보상배율 ≥ N배    (반기)
  FC04: 유동비율 ≥ N%         (반기)
  FC05: 순차입금/EBITDA ≤ N배 (연간)

행동 코베넌트 (Behavioral) — 정성 점검
  BC01: 추가 담보성 채무 제한
  BC02: 자산 처분 제한 (일정금액 이상)
  BC03: 배당 제한
  BC04: 추가 차입 한도 제한

정보 코베넌트 (Information)
  IC01: 분기 재무제표 제출
  IC02: 연간 감사보고서 제출
  IC03: 중요 사건 즉시 통보

위반 심각도 (breach_severity)
  MINOR         → 경고 통보, 30일 치유 기간 부여
  MAJOR         → 기한이익상실 예고, 추가 담보 요구
  EVENT_OF_DEFAULT → 즉시 기한이익상실, EWS CRITICAL 연동
```

#### DB 신규 테이블

```sql
CREATE TABLE covenant (
    covenant_id     TEXT PRIMARY KEY,
    facility_id     TEXT NOT NULL,
    application_id  TEXT,
    covenant_type   TEXT NOT NULL,   -- FINANCIAL / BEHAVIORAL / INFORMATION
    covenant_code   TEXT NOT NULL,   -- FC01, BC01, IC01 ...
    covenant_name   TEXT NOT NULL,
    metric          TEXT,            -- 측정 지표명
    operator        TEXT,            -- LE / GE / EQ
    threshold_value REAL,
    check_frequency TEXT,            -- MONTHLY / QUARTERLY / SEMI / ANNUAL
    next_check_date DATE,
    waiver_count    INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'ACTIVE',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE covenant_check (
    check_id        TEXT PRIMARY KEY,
    covenant_id     TEXT NOT NULL,
    check_date      DATE NOT NULL,
    actual_value    REAL,
    threshold_value REAL,
    result          TEXT,            -- PASS / BREACH / WAIVED
    breach_severity TEXT,            -- MINOR / MAJOR / EVENT_OF_DEFAULT
    action_taken    TEXT,
    checked_by      TEXT,
    next_check_date DATE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### API 설계

```
GET  /api/covenants/facility/{facility_id}  여신별 코베넌트 목록
GET  /api/covenants/due-check               점검 예정 (30일 이내)
POST /api/covenants/check/{covenant_id}     수동 점검 실행
GET  /api/covenants/breach-status           위반 현황 대시보드
GET  /api/covenants/history/{covenant_id}   이행 이력
POST /api/covenants/waiver/{covenant_id}    웨이버(유예) 신청
```

#### Frontend
- `Covenant.tsx` 신규 페이지
- `Applications.tsx` — "약정관리" 탭

---

### Module 4: 자산건전성 분류 (Asset Classification)

**목적**: 금감원 기준 5단계 분류 자동화, 연체일수·PD·EWS 연동으로 실시간 등급 산출

#### 5단계 분류 기준

```
정상 (Normal)            연체 0일,   PD < 3%,   EWS ≥ 75점
요주의 (Precautionary)   연체 1-30일  또는 PD 3-10%   또는 EWS 55-74점
고정 (Substandard)       연체 31-90일 또는 PD 10-20%  또는 EWS 35-54점
회수의문 (Doubtful)      연체 91-180일 또는 PD 20-50%
추정손실 (Loss)          연체 181일+  또는 PD > 50%  또는 회생파산 신청

원칙: 세 기준(DPD/PD/EWS) 중 가장 불리한 것 적용 (Conservatism)

충당금 적립 기준
  정상:    0.5%    (12개월 EL)
  요주의:  2-5%   (Lifetime EL)
  고정:    20%    (개별 평가 시작)
  회수의문: 50%
  추정손실: 100%
```

#### DB 신규 테이블

```sql
CREATE TABLE asset_classification (
    class_id          TEXT PRIMARY KEY,
    facility_id       TEXT NOT NULL,
    customer_id       TEXT NOT NULL,
    base_date         DATE NOT NULL,
    classification    TEXT NOT NULL,  -- NORMAL/PRECAUTIONARY/SUBSTANDARD/DOUBTFUL/LOSS
    prev_class        TEXT,
    dpd               INTEGER DEFAULT 0,
    pd_based_class    TEXT,
    ews_based_class   TEXT,
    final_class_basis TEXT,           -- DPD / PD / EWS
    exposure_at_class REAL,
    provision_rate    REAL,
    required_provision REAL,
    existing_provision REAL,
    provision_gap     REAL,
    classified_by     TEXT DEFAULT 'SYSTEM',
    override_reason   TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- facility 컬럼 추가
ALTER TABLE facility ADD COLUMN dpd INTEGER DEFAULT 0;
ALTER TABLE facility ADD COLUMN max_dpd_12m INTEGER DEFAULT 0;
ALTER TABLE facility ADD COLUMN first_delinquency_date DATE;
ALTER TABLE facility ADD COLUMN classification TEXT DEFAULT 'NORMAL';
```

#### API 설계

```
GET  /api/classification/portfolio           포트폴리오 건전성 현황
GET  /api/classification/facility/{id}       여신별 분류 이력
GET  /api/classification/customer/{id}       고객별 분류 현황
POST /api/classification/run                 월말 일괄 분류 실행
GET  /api/classification/migration-matrix    분류 이동 행렬
GET  /api/classification/provision-gap       충당금 부족액 분석
GET  /api/classification/trend               분류별 추이 (월별)
```

#### Frontend
- `AssetClassification.tsx` 신규 페이지

---

### Module 5: IFRS 9 ECL 충당금 산출 (Expected Credit Loss)

**목적**: 현재 단순 `provision_amount`를 IFRS 9 3단계 ECL 체계로 고도화

#### ECL 모델 정의

```
Stage 1 — 신용위험 유의적 증가 없음
  ECL = PD_12M × LGD × EAD × DF_0.5

Stage 2 — SICR 발생 (신용위험 유의적 증가)
  ECL = Σ_t [PD_marginal_t × LGD × EAD_t × DF_t]  (잔존 전 기간)
  SICR 트리거: PD 2배 이상 상승 | 등급 2 notch 하락 | EWS WATCH 이하 | DPD ≥ 30

Stage 3 — 신용 손상 발생
  ECL = EAD - PV(예상 현금회수액)  (개별 평가)

거시 조정
  ECL_final = ECL_base × macro_adj_factor  (macro_adjustment_factor 테이블 연동)
```

#### DB 신규 테이블

```sql
CREATE TABLE ecl_calculation (
    ecl_id              TEXT PRIMARY KEY,
    facility_id         TEXT NOT NULL,
    customer_id         TEXT NOT NULL,
    calc_date           DATE NOT NULL,
    stage               INTEGER NOT NULL,   -- 1, 2, 3
    sicr_triggered      INTEGER DEFAULT 0,
    sicr_reason         TEXT,
    pd_original         REAL,
    pd_current          REAL,
    lgd                 REAL,
    ead                 REAL,
    remaining_tenor_months INTEGER,
    ecl_base            REAL,
    macro_adj_factor    REAL DEFAULT 1.0,
    ecl_final           REAL,
    prev_ecl            REAL,
    ecl_change          REAL,
    existing_provision  REAL,
    provision_gap       REAL,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### API 설계

```
GET  /api/ecl/portfolio-summary          포트폴리오 ECL 요약 (Stage별)
GET  /api/ecl/facility/{facility_id}     여신별 ECL 산출 결과
GET  /api/ecl/stage-migration            Stage 이동 현황 (월별)
GET  /api/ecl/provision-adequacy         충당금 적정성 분석
POST /api/ecl/calculate/{facility_id}    개별 ECL 재산출
GET  /api/ecl/trend                      ECL 추이 (분기별)
GET  /api/ecl/macro-sensitivity          거시 시나리오별 ECL 민감도
```

#### Frontend
- `Workout.tsx` — "충당금(ECL)" 탭 추가

---

### Module 6: 연체 관리 (Delinquency Management)

**목적**: 연체 발생 → 단계별 추심 → Workout 자동 연결의 전체 프로세스 구현

#### 연체 단계 정의 및 자동 액션

```
DPD 1-30일   (Early)    자동 EWS 경보 생성, RM 접촉 요청
DPD 31-60일  (Mid)      경고장 발송, 채무조정 상담 권유
DPD 61-90일  (Late)     기한이익상실 예고, 법무 검토 시작
DPD 91-180일 (NPL)      Workout 케이스 자동 생성, 자산건전성 → 회수의문
DPD 181일+   (Write-off) 대손상각 검토
```

#### DB 신규 테이블

```sql
CREATE TABLE delinquency_record (
    delinquency_id    TEXT PRIMARY KEY,
    facility_id       TEXT NOT NULL,
    customer_id       TEXT NOT NULL,
    overdue_date      DATE NOT NULL,
    overdue_amount    REAL NOT NULL,
    overdue_type      TEXT,       -- PRINCIPAL / INTEREST / BOTH
    dpd               INTEGER DEFAULT 0,
    resolved_date     DATE,
    resolved_amount   REAL,
    resolution_type   TEXT,       -- PAID / RESTRUCTURED / WORKOUT / WRITEOFF
    status            TEXT DEFAULT 'OPEN',
    delinquency_stage TEXT,       -- EARLY / MID / LATE / NPL / WRITEOFF
    assigned_officer  TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE collection_activity (
    activity_id     TEXT PRIMARY KEY,
    delinquency_id  TEXT NOT NULL,
    facility_id     TEXT NOT NULL,
    activity_date   DATE NOT NULL,
    activity_type   TEXT NOT NULL, -- CALL / LETTER / VISIT / SMS / EMAIL / LEGAL_NOTICE
    contact_result  TEXT,          -- REACHED / NO_ANSWER / PROMISE_TO_PAY / REFUSED
    promised_date   DATE,
    promised_amount REAL,
    notes           TEXT,
    officer         TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### API 설계

```
GET  /api/delinquency/dashboard              연체 현황 대시보드 (DPD 버킷별)
GET  /api/delinquency/active                 현재 연체 목록
GET  /api/delinquency/facility/{id}          여신별 연체 이력
GET  /api/delinquency/roll-rate              Roll Rate 분석 (DPD 버킷 이동률)
GET  /api/delinquency/vintage-delinquency    빈티지별 연체율 곡선
POST /api/delinquency/collection-activity    추심 활동 기록
GET  /api/delinquency/collection-performance 추심 성과 (약속이행률, 회수율)
```

#### Frontend
- `Delinquency.tsx` 신규 페이지

---

### Module 7: EWS → Workflow 자동 연결 (Integration Bridge)

**목적**: 현재 사일로 구조를 연결하는 자동화 트리거 레이어 구현

#### 트리거 설계

```
EWS CRITICAL (종합점수 < 35)
  → 자동: EWS 경보 생성
  → 자동: 담당 RM 알림 Task 생성
  → 선택: Workout 케이스 예비 생성

코베넌트 위반 (EVENT_OF_DEFAULT)
  → 자동: 기한이익상실 예고 알림
  → 자동: 자산건전성 재분류 트리거
  → 선택: 추가 담보 요청 액션

연체 DPD 90일
  → 자동: Workout 케이스 생성
  → 자동: 자산건전성 → 회수의문 재분류
  → 자동: ECL Stage 3 재산출

부실전환 확률 모델
  P(default_90d) = σ(β0 + β1×EWS + β2×DPD + β3×PD + β4×DSCR)
  → 60% 이상 시 선제 채무조정 권고
```

#### DB 신규 테이블

```sql
CREATE TABLE automation_action (
    action_id         TEXT PRIMARY KEY,
    trigger_type      TEXT NOT NULL,
    trigger_source_id TEXT,
    customer_id       TEXT NOT NULL,
    facility_id       TEXT,
    action_type       TEXT NOT NULL,
    action_status     TEXT DEFAULT 'PENDING',
    priority          TEXT DEFAULT 'NORMAL',
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_at       TIMESTAMP
);
```

#### Frontend
- `Dashboard.tsx` — "자동화 액션 현황" 위젯 추가

---

### Module 8: LGD 백테스트 & 회수 실적 분석 (Recovery Analytics)

**목적**: PD 백테스트를 LGD로 확장, 회수 전략 효과성 통계화

#### LGD 백테스트 설계

```
데이터 소스
  추정 LGD: risk_parameter.lgd (심사 시점)
  실측 LGD: 1 - (actual_recovery_amount / total_exposure) (workout_case 활용)

검증 지표
  평균 추정 오차: Σ(LGD_est - LGD_actual) / N
  RMSE: √(Σ(LGD_est - LGD_actual)² / N)
  담보 유형별 분해 (부동산 / 동산 / 신용)
  산업별 분해
  경기 국면별 (호황기 vs 불황기)
```

#### API 설계 (models.py 확장)

```
GET  /api/models/lgd-backtest                LGD 백테스트 전체 결과
GET  /api/models/lgd-backtest/collateral     담보유형별 LGD 실측 vs 추정
GET  /api/models/lgd-backtest/industry       산업별 LGD 정확도
GET  /api/models/recovery-analytics          회수 전략별 성과 통계
GET  /api/models/recovery-timeline           회수 기간 분포
```

#### Frontend
- `Models.tsx` — "LGD 백테스트" 탭 추가

---

## 4. 전체 구현 계획 (Phase별)

### Phase 1 — 여신 심사 고도화 (Module 1~3)

> **목표**: 심사 품질의 정량화와 그룹·약정 리스크 체계화

| 구분 | 작업 | 상세 |
|------|------|------|
| DB | 신규 테이블 5개 | `financial_statement`, `financial_ratio`, `group_guarantee`, `covenant`, `covenant_check` |
| DB | 기존 테이블 ALTER | `borrower_group` (+3 컬럼), `approval_history` (conditions_json 추가) |
| Backend | 신규 API 파일 3개 | `financial_analysis.py`, `group_credit.py`, `covenant.py` |
| Backend | `calculations.py` 확장 | `calculate_financial_ratios()`, `calculate_dscr()`, `calculate_altman_z()`, `check_covenant_compliance()` |
| Backend | `main.py` 수정 | 라우터 3개 추가 |
| Frontend | 신규 페이지 1개 | `Covenant.tsx` |
| Frontend | 기존 페이지 수정 | `Applications.tsx` — 탭 3개 추가 (재무분석, 그룹현황, 약정관리) |
| Frontend | `api.ts` 확장 | `financialApi`, `groupCreditApi`, `covenantApi` 추가 |
| Frontend | `App.tsx` 수정 | Covenant 라우팅 추가 |
| Data | 시드 데이터 생성 | 재무제표 ~3,030건, 코베넌트 ~2,160건 |

### Phase 2 — 부실 관리 핵심 (Module 4~6)

> **목표**: 자산건전성 분류 자동화, IFRS 9 충당금 체계, 연체 프로세스 완성

| 구분 | 작업 | 상세 |
|------|------|------|
| DB | 신규 테이블 4개 | `asset_classification`, `ecl_calculation`, `delinquency_record`, `collection_activity` |
| DB | 기존 테이블 ALTER | `facility` (+4 컬럼: dpd, max_dpd_12m, first_delinquency_date, classification) |
| Backend | 신규 API 파일 3개 | `asset_classification.py`, `ecl.py`, `delinquency.py` |
| Backend | `calculations.py` 확장 | `calculate_ecl_stage1/2/3()`, `determine_sicr()`, `classify_asset()` |
| Backend | 기존 파일 수정 | `workout.py` (연체 DPD 90일 자동 이관 로직) |
| Backend | `main.py` 수정 | 라우터 3개 추가 |
| Frontend | 신규 페이지 2개 | `AssetClassification.tsx`, `Delinquency.tsx` |
| Frontend | 기존 페이지 수정 | `Workout.tsx` — ECL 탭 추가 |
| Frontend | `api.ts` 확장 | `assetClassificationApi`, `eclApi`, `delinquencyApi` 추가 |
| Data | 시드 데이터 생성 | 분류 이력 ~14,400건, ECL ~14,400건, 연체 ~150건 |

### Phase 3 — 연결 및 고도화 (Module 7~8)

> **목표**: EWS-Workout 연결 자동화, LGD 백테스트 추가

| 구분 | 작업 | 상세 |
|------|------|------|
| DB | 신규 테이블 1개 | `automation_action` |
| Backend | 신규 API 파일 1개 | `automation.py` |
| Backend | 기존 파일 수정 | `ews_advanced.py` (CRITICAL 트리거), `models.py` (LGD 백테스트 4개), `workout.py` (자동화 연동) |
| Backend | `main.py` 수정 | 라우터 1개 추가 |
| Frontend | 기존 페이지 수정 | `Dashboard.tsx` (자동화 위젯), `Models.tsx` (LGD 백테스트 탭) |
| Frontend | `api.ts` 확장 | `automationApi` 추가 |

---

## 5. 파일별 변경사항 요약

### 신규 생성 파일

```
database/
  schema_phase1.sql                        Phase 1 신규 테이블 DDL
  schema_phase2.sql                        Phase 2 신규 테이블 DDL
  generate_phase1_data.py                  Phase 1 시드 데이터 생성
  generate_phase2_data.py                  Phase 2 시드 데이터 생성

backend/app/api/
  financial_analysis.py                    재무제표 분석 API   (~350 lines)
  group_credit.py                          그룹여신 통합심사 API (~250 lines)
  covenant.py                              코베넌트 관리 API    (~300 lines)
  asset_classification.py                  자산건전성 분류 API  (~400 lines)
  ecl.py                                   ECL 충당금 산출 API  (~350 lines)
  delinquency.py                           연체 관리 API        (~400 lines)
  automation.py                            자동화 트리거 API    (~200 lines)

frontend/src/pages/
  Covenant.tsx                             코베넌트 관리 페이지 (~400 lines)
  AssetClassification.tsx                  자산건전성 분류 페이지 (~500 lines)
  Delinquency.tsx                          연체 관리 페이지     (~450 lines)
```

### 수정 파일

```
backend/app/services/calculations.py       금융 계산 함수 10개 추가
backend/app/api/models.py                  LGD 백테스트 엔드포인트 5개 추가
backend/app/api/workout.py                 DPD 자동 이관, ECL 연동
backend/app/api/ews_advanced.py            CRITICAL 시 automation_action 트리거
backend/app/main.py                        라우터 7개 추가

frontend/src/pages/Applications.tsx        탭 3개 추가 (재무분석/그룹현황/약정관리)
frontend/src/pages/Dashboard.tsx           자동화 액션 위젯 추가
frontend/src/pages/Models.tsx              LGD 백테스트 탭 추가
frontend/src/pages/Workout.tsx             ECL 탭 추가
frontend/src/utils/api.ts                  API 그룹 7개 추가
frontend/src/App.tsx                       라우팅 3개 추가
```

---

## 6. 데이터 생성 계획

| 테이블 | 건수 | 생성 방식 |
|--------|------|---------|
| `financial_statement` | ~3,030건 | 고객 1,010개 × 3개년 (2023~2025) |
| `financial_ratio` | ~3,030건 | financial_statement 기반 자동 산출 |
| `group_guarantee` | ~300건 | borrower_group_member 기반 생성 |
| `covenant` | ~2,160건 | 여신 1,200개 중 60% × 평균 3개 |
| `covenant_check` | ~4,320건 | covenant 기반 반기 점검 2회분 |
| `asset_classification` | ~14,400건 | 여신 1,200개 × 12개월 |
| `ecl_calculation` | ~14,400건 | 여신 1,200개 × 12개월 |
| `delinquency_record` | ~150건 | 여신의 12% (현실적 NPL 비율) |
| `collection_activity` | ~450건 | 연체 1건당 평균 3회 접촉 |
| `automation_action` | ~200건 | EWS CRITICAL + DPD 90일 트리거 |

---

## 7. 구현 현황 체크리스트

> **상태: Phase 1~3 전 항목 완료 (2026-08-02 검증, 2026-08-15 수치 재확인)**
>
> 검증 방법: `app.openapi()` 기준 경로 집계, 파일 존재 확인, `App.tsx` 라우팅 확인.

### 계획 대비 실적

| 지표 | v1.2.0 | 목표 (v2.0) | 2026-08-02 | **현재 (08-15)** |
|------|--------|------------|-----------|-----------------|
| API 경로 | 133개 | 173개 | 189개 | **243개** |
| 라우터 등록 | — | — | 25개 | **38개** |
| 사용자 화면 | 19개 | 24개 | 21개 | **37개** (README 계수법) |
| 자동 테스트 | — | — | — | **188개 (전건 통과)** |

### Phase 1 — 여신 심사 고도화

- [x] `database/schema_phase1.sql` 작성
- [x] `database/generate_phase1_data.py` 작성 및 실행
- [x] `backend/app/services/calculations.py` 함수 추가
- [x] `backend/app/api/financial_analysis.py` 작성 — `/api/financial` 5개
- [x] `backend/app/api/group_credit.py` 작성 — `/api/group-credit` 6개
- [x] `backend/app/api/covenant.py` 작성 — `/api/covenants` 6개
- [x] `backend/app/main.py` 라우터 등록
- [x] `frontend/src/pages/Applications.tsx` 탭 추가
- [x] `frontend/src/pages/Covenant.tsx` 신규 작성
- [x] `frontend/src/utils/api.ts` API 그룹 추가
- [x] `frontend/src/App.tsx` 라우팅 추가 (`/covenant`)

### Phase 2 — 부실 관리 핵심

- [x] `database/schema_phase2.sql` 작성
- [x] `database/generate_phase2_data.py` 작성 및 실행
- [x] `backend/app/services/calculations.py` ECL 함수 추가
- [x] `backend/app/api/asset_classification.py` 작성 — `/api/classification` 7개
- [x] `backend/app/api/ecl.py` 작성 — `/api/ecl` 7개
- [x] `backend/app/api/delinquency.py` 작성 — `/api/delinquency` 7개
- [x] `backend/app/api/workout.py` 수정 (DPD 자동 이관)
- [x] `backend/app/main.py` 라우터 등록
- [x] `frontend/src/pages/AssetClassification.tsx` 신규 작성
- [x] `frontend/src/pages/Delinquency.tsx` 신규 작성
- [x] `frontend/src/pages/Workout.tsx` ECL 탭 추가
- [x] `frontend/src/utils/api.ts` API 그룹 추가

### Phase 3 — 연결 및 고도화

- [x] `database/schema_phase3.sql` 작성
- [x] `backend/app/api/automation.py` 작성 — `/api/automation` 6개
- [x] `backend/app/api/ews_advanced.py` 트리거 추가
- [x] `backend/app/api/models.py` LGD 백테스트 추가
- [x] `backend/app/main.py` 라우터 등록
- [x] `frontend/src/pages/Dashboard.tsx` 위젯 추가
- [x] `frontend/src/pages/Models.tsx` LGD 탭 추가

---

## 8. 잔여 작업 (v2.0 이후)

계획된 기능 구현은 완료되었고, 남은 항목은 배포·UI 마감 영역이다.

### 완료 (2026-08-02)

- [x] **`frontend/dist` gitignore 충돌 해소** — `.gitignore`의 Python `dist/` 패턴이 프론트 번들까지
      제외해 신규 빌드 산출물을 커밋할 수 없었다. Render는 리포에 포함된 `frontend/dist`를
      FastAPI가 직접 서빙하므로(`render.yaml` + `backend/app/main.py:110-127`) 커밋 시
      asset 404가 발생하는 상태였다. `!frontend/dist/` 예외로 해소.
- [x] **`*.db` negation 순서 정정** — `!database/imbank_demo.db`가 `*.db`보다 앞에 있어
      무효화되던 문제. 데모 DB는 배포 필수 자산이므로 순서 교정.
- [x] **Gradient Mesh 카드 커버리지 확대** — `rounded` / `rounded-2xl` / `rounded-t-xl`
      변형 약 30개가 프로스티드 처리에서 누락되어 불투명 흰 박스로 남던 문제.
- [x] **모달 가독성 회귀 수정** — 모달 패널이 전부 `bg-white rounded-xl shadow-2xl` 조합이라
      카드 규칙에 걸려 반투명 처리되고 있었다. `shadow-xl`/`shadow-2xl` 예외 규칙 추가.

- [x] **mesh 모달 내부 sticky 헤더 회귀** — 모달 패널을 불투명 예외로 돌리면서, 그 내부의
      `bg-white rounded-t-xl` sticky 헤더(`CustomerProfitability.tsx:332`)가 카드 규칙에
      걸려 반투명으로 남았다. 모달 하위 `bg-white` 전체를 불투명 예외로 방어.
- [x] **차트 인라인 hex 브랜드 미적용 13건** — Tailwind `blue` 리매핑은 클래스명에만 적용되어
      Recharts에 직접 넘기는 hex가 구 브랜드 블루로 남아 있었다. 9개 파일을 민트 스케일로 치환.
- [x] **Vercel / Render 이중 배포 구성 정리** — Render를 단일 정본으로 확정하고
      `vercel.json` · `api/index.py`를 제거했다. README에 배포 절차와 체크리스트,
      CLAUDE.md에 함정(dist 커밋 필수)을 문서화.

### 리스크 산식 정합성 감사 (2026-08-02)

`calculations.py` · `credit_models.py` · `stress_test.py` · `ecl.py`를 README의
「핵심 수리 모형」과 대조한 결과. 각 항목은 실제 값으로 재현해 확인했다.

**수정 완료**

- [x] **스트레스 PD/LGD 상한 이중 정의** — `calculate_stress_pd()`는 상한 1.0인데
      `stress_test.py`는 이 함수를 import만 하고 실제로는 `min(pd*f, 0.30)`을 인라인으로
      계산했다(죽은 코드 + 상한 불일치). 같은 입력에 0.70 vs 0.30으로 2.3배 차이.
      → 상한을 `STRESS_PD_CAP`/`STRESS_LGD_CAP` 단일 정의로 통일하고
      `calculate_stress_lgd()`를 신설, `stress_test.py`가 이를 호출하도록 변경.
- [x] **`_signal()` 신호등의 warning 구간 소실** — 여유폭을 곱셈으로만 계산해
      기준값이 0인 `op_margin`에서 pass 경계와 warning 경계가 모두 0으로 붕괴했다.
      영업이익률이 0% 이상이면 전부 pass, 음수만 fail로 3단계가 2단계로 퇴화.
      → 기준값이 0이면 절대 여유폭(`margin_abs`, 5%p)을 쓰도록 수정.
- [x] **`get_grade_from_pd()`의 낙관 편향** — `pd <= grade_pd * 1.5` 로 50% 여유를 둬
      PD 0.017이 BBB(0.0115)로 매겨졌다. `get_pd_from_grade()`로 되돌리면 PD가
      **-32%** 왜곡되고, 이 값이 RWA·EL·가격결정에 그대로 전파된다.
      → 여유폭을 제거해 상한 기준으로 판정(왜곡 -32% → +7~9%, 보수적 방향).
- [x] **DSCR의 만기일시상환 오분류** — `annual_principal or (total_borrowing*0.1)`에서
      원금상환액 0(만기일시상환)이 falsy로 걸려 추정치로 덮어써졌다.
      EBITDA 100·이자 20·차입 1000 기준 DSCR이 5.0 → 0.83으로 뒤집혀 fail 판정.
      → `is None` 검사로 0과 미제공을 구분.
- [x] **README의 RWA 자본요구량 공식 표기 오류** — `K = LGD × [Φ(…) − PD×LGD]`로
      적혀 LGD가 중복 곱해진다(LGD²·PD 항 발생). 표기대로 계산하면 RWA가 +6.5% 어긋난다.
      구현(`lgd*Φ(…) − pd*lgd`)은 Basel 표준과 일치(상대오차 1e-8)하므로 문서만 수정.
- [x] **EWS 종합점수 가중치 설명 오류** — `ews_advanced.py`의 methodology가
      4채널(0.40 재무 + 0.20×3)로 적혀 있었으나 실제 산출은 상장 6채널 / 비상장 5채널이다.
      → 실제 생성 로직(`generate_ews_leading_data.py:534-549`)에 맞게 수정.

### 금융감독규정 반영 (2026-08-02)

「은행업감독규정」·「은행업감독업무시행세칙 별표3」·「기업회계기준서 제1109호」를
근거로 분류·충당금·Stage 판정을 규정 기준에 맞췄다.

- [x] **대손충당금 최저적립률을 감독규정 제29조로 교정** — 정상 0.5%→**0.85%**,
      요주의 2%→**7%** (고정 20% / 회수의문 50% / 추정손실 100%는 기존과 동일).
      기존 값은 규정 최저기준에 미달했다.
- [x] **연체기간 분류 경계를 시행세칙 별표3으로 교정** — 규정은 요주의 1개월 이상
      3개월 미만, 고정 3개월 이상, 추정손실 12개월 이상이다. 기존 구현은
      요주의 1\~30일 · 고정 31\~90일 · 회수의문 91\~180일 · 추정손실 181일 이상으로
      한 단계씩 앞당겨져 있었고 12개월 기준이 6개월로 잡혀 있었다.
      → 30 / 90 / 365일 경계로 상수화(`DPD_PRECAUTIONARY` 등).
- [x] **회수예상가액 기준 분할분류 구현** — 규정상 3개월 이상 연체 건은 담보
      회수예상가액 해당분을 고정, 초과분을 회수의문(12개월 미만)·추정손실(12개월 이상)로
      나눈다. 기존에는 DPD만으로 단일 등급을 매겨 담보를 전혀 반영하지 못했다.
      → `classify_asset()`에 `exposure`·`recoverable_value`를 받아 구간별 충당금을
      산출하고, `asset_classification.py`가 `collateral.recognized_value` 합계를 넘긴다.
- [x] **대손준비금 산출 추가** — IFRS 9 도입 후 회계상 충당금은 ECL로 적립하되
      감독규정 최저적립액에 미달하면 차액을 대손준비금으로 적립해야 한다.
      → `calculate_loan_loss_reserve()` 신설.
- [x] **Stage 3 판정을 기준서 1109호 손상 정의로 교정** — PD 20% 단독 조건을 제거하고
      연체 90일 초과(B5.5.37 채무불이행 추정) 또는 워크아웃 등 객관적 손상 증거로 한정.
      `ecl.py`가 `workout_case`를 조회해 손상 사유를 전달한다. 아울러 Stage 3인데
      `sicr=False`로 나와 SICR 집계에서 누락되던 것도 함께 고쳤다.
- [x] **EWS 임계값을 용도별로 단일 상수화** — 자산건전성 강등선은
      `EWS_THRESHOLD_PRECAUTIONARY`(35, CRITICAL 경계), SICR 트리거는
      `EWS_THRESHOLD_SICR`(55, WATCH 경계). 본 시스템의 EWS 분포가 평균 59점이라
      강등선을 75로 잡으면 차주의 **92%**, 55로 잡아도 **30%**가 요주의가 되어
      과대적립이 된다. CRITICAL 기준이면 6%로, 연체 기준 요주의(7.6%)와 규모가 맞는다.

**교정 효과** (전 여신 1,200건 재분류)

| | 수정 전 | 수정 후 |
|---|---|---|
| 정상 | 6.4% | 73.3% |
| 요주의 | 89.5% | 22.6% |
| 고정 | — | 2.0% (27건) |
| 회수의문 | — | 2.1% (18건) |
| 필요충당금 | 1.32조 | 5,864억 |

고정 27건 + 회수의문 18건 = 45건으로 연체 90일 이상 여신 수와 정확히 일치한다
(담보 있으면 고정, 초과분은 회수의문).

### 시드 데이터 분포 현실화 (2026-08-02)

규정 기준으로 재분류했을 때 요주의가 22.6%까지 나온 원인은 산식이 아니라 **시드 데이터
분포**였다. 감독원 「국내은행 원화대출 연체율 현황」(기업대출 0.84%, 중소기업 1.00%)을
기준으로 맞췄다.

- [x] **EWS 종합점수가 차주 위험과 무관한 난수였다** — `generate_extension_data.py`가
      재무·운영·외부·공급망 점수를 `random.uniform(0, 100)` **균등분포**로 뽑고 있었다.
      그 결과 평균 50점·CRITICAL 6.1%가 되어 EWS만으로 여신의 15%가 요주의로 강등됐다.
      → 차주 신용등급대별 정규분포(PRIME 86 / MID 76 / SUB 58)로 바꾸고, 등급과 무관하게
      징후가 나타나는 차주 2%를 별도로 심었다.
- [x] **"신호 없음"이 정상 점수가 아니었다** — 뉴스 감성이 중립일 때 50점, 시장 신호가
      정상일 때도 40점대라 무소식인 차주까지 WATCH로 끌려 내려갔다. 조기경보 지표는
      신호가 없으면 정상(75점 이상)이어야 한다. → 기준선을 80점으로 재설정.
- [x] **연체 표본을 '분류가 NORMAL 이 아닌 여신'에서 뽑고 있었다** — 그 집합은 대부분
      EWS·PD로 요주의가 된 정상이행 여신이라, 연체율이 12.58%까지 올라갔다.
      → 표본 수를 목표 연체율로 정하고(1개월 이상 1.5% + 단기 2%), 연체일수도 단기 편중
      분포로 뽑는다. 종전에는 1\~365일을 균등에 가깝게 뽑아 장기 연체가 과대했다.
- [x] **시드 스크립트가 분류 기준을 자체 정의하고 있었다** — `generate_phase2_data.py`가
      DPD 경계와 충당금률을 따로 갖고 있어, 규정 반영분이 시드에 반영되지 않았다.
      → `calculations.py`의 상수·함수를 그대로 import 하도록 바꿔 단일 정의로 만들었다.

**분포 교정 결과**

| 지표 | 교정 전 | 교정 후 | 실제 국내은행 |
|---|---|---|---|
| 정상 | 6.4% | **97.8%** | 97~98% |
| 요주의 | 89.5% | **1.4%** | 1~2% |
| NPL(고정이하) | — | **0.76%** | 0.5~0.7% |
| 1개월 이상 연체율 | 12.58% | **1.67%** | 0.84%(기업) / 1.00%(중소) |
| EWS 평균 | 59.2 | **77.5** | — |
| EWS CRITICAL | 6.1% | **0.5%** | — |
| 필요충당금 | 1.32조 | **2,037억** | — |

연체율은 실제(0.84%)보다 다소 높게 두었다. 중소기업 비중이 높은 지방은행 포트폴리오를
가정했고, 부실관리·EWS 화면에 표본이 남아야 하기 때문이다(WARNING 16명·CRITICAL 5명).

**부수 발견 — 시드 스크립트 실행 불가 3건**

- [x] `generate_data.py` · `generate_extension_data.py` · `generate_ews_leading_data.py`의
      `DB_PATH`·`SCHEMA_PATH`가 옛 경로(`/Users/yalkongs/code/Projects/...`)로 하드코딩되어
      있어 실행하면 즉시 죽었다. → 스크립트 기준 상대 경로로 교체.
- [x] `ews_composite_score`가 실행할 때마다 고객당 행이 하나씩 쌓였다(1,010 → 3,030).
      `score_id`를 매번 새 uuid로 만들어 `INSERT OR REPLACE`가 갱신으로 동작하지 않았다.
- [x] Phase 2 재실행 시 분류·ECL이 누적되고 `facility.dpd`가 되돌려지지 않아 연체율이
      실행할수록 올라갔다. → 두 스크립트를 멱등하게 수정.
- [x] `max_dpd = random.randint(dpd, min(dpd + 30, 200))` — DPD가 200을 넘으면
      빈 범위로 예외가 났다(12개월 이상 연체 표본에서 재현).

**부수 발견 — 기존 500 오류 2건**

`POST /api/ecl/calculate/{facility_id}`가 원래부터 동작하지 않았다. 감독규정 반영분을
검증하다 드러났다.

- [x] `risk_parameter`에 없는 `customer_id`로 조인 (`rp` 는 `application_id` 기준)
- [x] `composite_score`를 `ews_alert`에서 조회 (실제로는 `ews_composite_score`에 있음)

### iM뱅크 전략 기능 확장 (2026-08-03)

경영 환경 리서치(시중은행 전환 인가 조건·연체율 1%대·수도권 확장·PF 제도 개편)를
바탕으로 8개 기능을 추가했다. 엔드포인트 190 → 204, 화면 21 → 24.

**Phase A — 전략 직결**
- [x] 포용금융 이행 현황 (`inclusive_finance.py` + `InclusiveFinance.tsx`) —
      중신용(BBB+ 이하)·개인사업자 공급 실적 vs 인가 공언 목표, 세그먼트 건전성 병기.
      실측: 중신용 달성률 55.6%, SOHO 11.1% (미달), SOHO 연체율 1.66%.
- [x] 신규 진출 지역 빈티지 (`vintage_analysis` REGION 코호트 + `/api/delinquency/vintage-by-region`
      + Portfolio 카드) — 수도권 MOB3 3.15% vs 대구경북 1.39%.
- [x] 부동산PF 사업장 관리 (`pf_project`/`pf_progress` + `pf.py` + `PFMonitoring.tsx`) —
      40개 사업장, 공정-분양 괴리 경보 6건, 2027 제도 시뮬레이션(RWA +36%, 충당금 237→1,285억).

**Phase B — 내부통제**
- [x] 전결권 DB화 (`approval_authority` 테이블) + 승인 API 금액-권한 검증
      (담당자가 300억 승인 시도 → 403 차단 실증).
- [x] audit_log 활성화 (`core/audit.py`) — 승인·분류실행·ECL 재산출에 감사 기록.
- [x] 보고·감사 화면 (`governance.py` + `Governance.tsx`) — 업무보고서(인쇄 뷰)·전결 규정·감사 추적.

**Phase C — 자본규제 연계**
- [x] 스트레스완충자본 (`/api/stress-test/stress-capital-buffer` + StressTest 카드) —
      SEVERE 시나리오 BIS 하락폭 기반 SCB, 요구 비율 = 10.5% + SCB.
- [x] ALM 헷지 포지션 등록 POST (조회 전용이던 ALM 에 실행 기능).

**남김 (후순위)**: 상환 스케줄 테이블(DSCR·EAD 실측화) — 계정계 성격이라 별도 판단 필요.

### 유용성 확장 일괄 구현 (2026-08-04)

Tier 1~3 개선안 11건을 일괄 반영했다. 엔드포인트 210 → 217, 화면 25 → 26.

**Tier 1**
- [x] 고객 360 수선 — 여신 미보유 311명이 '0억원 그리드'로 보이던 것을
      잠재고객 안내로 대체 (조인 결함이 아니라 표현 문제였음)
- [x] 스토리 투어 — (주)영남바이오의 생애주기 악화 경로 6단계
      (경보→5채널→코베넌트 위반→강등→연체→워크아웃)를 화면 순회로 안내.
      온보딩 팝업의 '스토리 투어' 버튼으로 진입, 모의 데이터 고지 후 시작
- [x] CSV 내보내기 — 여신·분류·PF·연체·포용금융 5종 (`/api/export/*.csv`,
      UTF-8 BOM), 4개 화면에 다운로드 버튼
- [x] Render 워밍업 — GitHub Actions 10분 간격 /health 핑 (KST 08~22시)

**Tier 2**
- [x] 시나리오 플레이그라운드 — PD/LGD 배수·부동산 충격·금리 bp 슬라이더 →
      BIS·ECL·PF 워치리스트·이자보상배율 일괄 재계산 (`/api/stress-test/custom`)
- [x] EWS 검증 실측 이관 — css/v24 백테스트(부도 3,951건, 탐지율 95.34%,
      리드타임 33개월)와 피처 중요도를 모델관리 화면에 표시
- [x] 역할 전환 + 결재함 — 심사역/부장/임원 페르소나(아바타 메뉴), 결재함에서
      역할별 전결 한도에 따라 승인 가능 건이 달라짐 (심사역 12건 → 임원 37건 실증)
- [x] 전역 검색 Cmd+K — 고객·여신·PF 사업장·화면 이동 통합 팔레트

**Tier 3**
- [x] 한도 예약 연결 — 승인 시 업종 한도 예약 자동 생성 + 한도관리 예약 섹션
      (스키마 컬럼 불일치 reserved_at/expires_at 교정 포함)
- [x] 코드 분할 — 라우트별 React.lazy, 메인 청크 1,124KB → 694KB
- [x] 알림 딥링크 — EWS 경보 클릭 시 해당 고객 조회로 직행 (?q= 지원)

### 통제 커널 · 제3자 리뷰 반영 (2026-08-05)

제3자 리뷰의 P0 지적을 7단계로 나눠 반영했다. 화면 수 증가가 아니라 통제 성립에 집중한 구간.

- [x] **인증·전결권 서버 결정** — 승인자·부서·전결권을 클라이언트 파라미터가 아니라
      인증 사용자에서 서버가 결정. 승인·한도예약·감사기록을 단일 트랜잭션으로 묶음
- [x] **신용공여 원장·법정 3한도** — `credit_exposure_ledger` + 은행법 §35 근사 판정
- [x] **불변 승인 스냅샷** — 승인 시점의 자료·모델·판단을 해시 봉인 (`decision_snapshot`)
- [x] **상태기계·의무관리함·규정 레지스터** — 유효일자 기준 규칙 선택
- [x] **규제 회귀 테스트 + 스모크 CI** — push 시 파라미터 없는 GET 전수 검증
- [x] **성능** — gzip·인덱스·TTL 캐시, GET 지수 백오프 재시도(배포 재시작 시 0 표시 방지)

### 시연 완성도 (2026-08-09 ~ 08-11)

- [x] **AI 심사의견서 초안** (규칙 기반) · **개발 여정 페이지** · **전결권 우회 차단**
- [x] **다크 모드** 추가 — Classic · Gradient Mesh · Dark 3종
- [x] **실측 대조 현실화** — 자기자본·RWA·여신금리(6.04% → 4.70%)를 iM뱅크 공시 기준으로 조정
- [x] **모바일 3계층 지원** — 전용 화면 8개 + 전 화면 자동 모바일화 + 진입 판별
- [x] **첫 방문 필수 코스** — 소개 → 개발 여정 → 모의 데이터 고지 → 대시보드/투어
- [x] **Gate 0 (갭 연구 2026-08-11 반영)** — 승인 ID 충돌·임의 단계전이·client-supplied
      actor·권한 없는 중요 실행·그룹한도 합산 누락 봉합, RAROC 허들 15% 단일화

### 승인조건 구조화 (2026-08-15)

갭 연구 P1 「승인조건 JSON 사용 0건」을 닫았다. `schema_phase1.sql:133`에 선언만
있고 코드 어디서도 참조하지 않던 `approval_history.conditions_json`을 업무흐름에 연결.

- [x] **표준 승인조건 카탈로그 11종** — 선행조건(CP) 5 · 후속조건(CS) 6.
      FC/IC 코드는 `covenant` 테이블 체계와 일치시켜 실행 후 모니터링으로 이어짐
- [x] **결재함 결재 모달** — 승인금액·금리·기간을 심사 결과에서 기본값으로 불러오고
      승인조건을 체크리스트로 선택. 종전에는 `decision`만 보내 금리·기간·조건이
      전혀 기록되지 않았다 (`Applications.tsx` 승인 모달은 이미 연결돼 있었음)
- [x] **조건 위조 차단** — 카탈로그 코드만 허용하고 label·type은 서버가 다시 채운다.
      조건 지정 결재는 `CONDITIONAL` 강제(불일치 시 422)
- [x] **전자 여신철 표시** — 선행/후속 배지와 이행기한 노출

**동반 발견·수정한 결함**

- [x] 결재함 쿼리가 `CONDITIONAL`을 제외해 조건부승인 즉시 목록에서 사라졌다.
      2차 결재자가 그 건을 볼 수 없어 다단계 결재가 성립하지 않았다
- [x] 최종승인이 미지정 승인금액·금리·기간을 NULL로 덮어써, 팀장이 조건부승인에서
      정한 감액·금리가 부서장 최종승인 시점에 유실됐다
- [x] 상세 조회 API가 `approved_amount`/`rate`/`tenor`를 노출하지 않아 승인 결과를
      화면에서 확인할 수 없었다 (P1 「사용 건수 0건」의 관측이 막혀 있던 원인)
- [x] `migrate.py`가 `CLMS_DB_PATH`를 무시해, 앱이 다른 DB를 볼 때도 마이그레이션은
      `database/imbank_demo.db`에 적용됐다 (갭 연구 P1 「경로 분리」 항목)
- [x] **테스트 격리** (`backend/tests/conftest.py`) — 승인 회귀 테스트가 배포 자산인
      데모 DB를 직접 변형시켜, 실행마다 표본이 소진되고 테스트가 실패가 아니라
      **조용히 skip**으로 바뀌고 있었다. 승인 경로 회귀 테스트 8건이 아무것도
      검증하지 않은 채 통과 중이었다. 175 passed/2 skipped → **188 passed/0 skipped**

### 문서·CI·리포 정비 (2026-08-15)

- [x] **프런트엔드 CI 추가** — `ci.yml`이 backend pytest만 돌리고 있어, 프런트 빌드 검증은
      로컬 pre-commit 훅에만 의존했다(`--no-verify`나 훅 미설치 환경은 통과). `frontend` job에
      커밋된 dist 정합성 검증(참조 asset 존재·git 추적·데모 DB 추적)과 `npm ci && npm run build`
      (tsc 포함)를 추가했다
- [x] **`caniuse-lite` 갱신** — `1.0.30001766` → `1.0.30001809`, 빌드 경고 해소
- [x] **리포 위생** — `generate_*_paper.py` 3개를 `tools/`로 이동(산출물 경로는 리포 루트 유지),
      루트의 stale 로그 8개와 0바이트 `imbank_demo.db` 제거. 모두 이미 `.gitignore` 대상이라
      리포에는 영향이 없던 로컬 잔재였다
- [x] **문서 수치 동기화** — README·계획서의 경로 242→243, 테스트 177(175 통과·2 건너뜀)→188(전건 통과)

### 미착수

- [ ] **번들 추가 분할** — 라우트별 `React.lazy` 코드 분할은 적용됨(2026-08-04).
      메인 청크는 현재 **724KB (gzip 213KB)** 이고 `manualChunks`로 벤더를 떼어낼 여지가 남았다.
- [ ] **`Applications.tsx` 승인 모달에 조건 체크리스트 적용** — 결재함 경로에만 넣었다.
      해당 파일이 100KB 규모라 이번 범위에서 제외했고, 서버가 조건 요약을 자유 텍스트로도
      생성하므로 기존 화면 표시는 정상 동작한다.
- [ ] **승인조건 이행 추적** — 현재는 조건을 *부여*하고 조회할 수 있다. 조건별 이행 확인·
      증빙 첨부·미이행 시 실행 차단(선행조건 gate)은 Gate 1 범위로 남겨 두었다.

### 범위 밖 (은행 실운영 로드맵)

`docs/BANK_REQUIRED_CAPABILITIES_RESEARCH_2026-08-11.md`의 **Gate 1~3**(버전형 FSM,
IAM policy adapter, 계정계 booking outbox, AML/KYC 게이트 등)은 실제 은행 파일럿·운영
전환을 전제한 로드맵이다. PoC 범위에서는 착수 대상이 아니라 제안 근거로 다룬다.
같은 문서 §10이 「통제되지 않은 상태에서 화면·차트·시뮬레이션 수를 더 늘리는 것」을
우선순위에서 명시적으로 제외하고 있다.

---

*최종 업데이트: 2026-08-15*
