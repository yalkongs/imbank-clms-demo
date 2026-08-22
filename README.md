# iM뱅크 CLMS — 종합 기업여신 관리시스템

**Credit Lifecycle Management System**

기업여신의 심사·포트폴리오·모니터링·회수를 통합적으로 분석·시연하는 PoC 시스템입니다.
Basel II/III IRB 신용리스크 계량화 체계를 기반으로, **42개 사용자 화면 · 265개 API 경로 · 103개 업무 테이블 ·
자동 테스트 220개(전건 통과)**로 구성되며, iM뱅크 공시 규모를 참고한 모의 포트폴리오
(고객 2,160개사 · 총여신 36.7조 · 자기자본 5.5조 · BIS 14.5%)를 탑재합니다.

**▶ 라이브: https://imbank-clms.onrender.com**  (예비: https://imbank-clms-demo.onrender.com)

- 무료 인스턴스라 첫 접속 시 수십 초 걸릴 수 있습니다. 휴대폰 접속 시 모바일 전용 화면이 자동 표시됩니다.
- 두 주소는 같은 코드가 배포된 독립 인스턴스입니다 (master 푸시 시 양쪽 모두 자동 배포).

**은행 파일럿 준비도와 추가 요구기능:** [2026-08-11 은행 요구기능 갭 연구 및 실행 권고](docs/BANK_REQUIRED_CAPABILITIES_RESEARCH_2026-08-11.md)

> 현재 공개 배포는 분석·의사결정 PoC입니다. 실제 여신 승인·실행 권한이 있는 은행 운영시스템으로 사용하지 않습니다.

![Version](https://img.shields.io/badge/version-1.9-blue)
![Python](https://img.shields.io/badge/python-3.13-green)
![React](https://img.shields.io/badge/react-18.2-blue)
![Tests](https://img.shields.io/badge/tests-220_passed-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

**체험 계정** (헤더 우측 로그인 → 계정 선택, PIN 힌트 표시):

| 계정 | PIN | 직급 | 전결권 |
|------|-----|------|--------|
| kim.simsa | 1111 | 심사역 (담당자) | 5억 |
| kim.yeosin | 1234 | 팀장 | 50억 |
| park.bujang | 2222 | 부서장 | 200억 |
| lee.jeonmu | 3333 | 임원 | 1,000억 |

---

## 목차

- [개요](#개요)
- [주요 기능](#주요-기능)
- [핵심 수리 모형](#핵심-수리-모형)
- [시스템 아키텍처](#시스템-아키텍처)
- [프로젝트 구조](#프로젝트-구조)
- [설치 및 실행](#설치-및-실행)
- [배포](#배포)
- [API 엔드포인트](#api-엔드포인트)
- [데이터 모델](#데이터-모델)
- [은행 요구기능 연구](docs/BANK_REQUIRED_CAPABILITIES_RESEARCH_2026-08-11.md)
- [시스템 상수 및 가정치](#시스템-상수-및-가정치)
- [변경 이력](#변경-이력)
- [라이선스](#라이선스)

---

## 개요

### 핵심 가치

| 영역 | 내용 |
|------|------|
| **리스크 기반 의사결정** | PD·LGD·EAD 모델 기반 심사 시뮬레이션, RAROC 가격결정, 규칙 기반 심사의견서 초안 |
| **자본 효율성 최적화** | IRB RWA 산출, 포트폴리오 최적화, 리밸런싱 추천 |
| **규제 분석** | Basel III 자본비율, 은행법 §35 법정 3한도 조회·시뮬레이션, 스트레스 테스트, 모델 검증(MRM) |
| **내부통제** | 서버 결정 전결권·동일인 중복결재 차단, 승인 시점 심사자료 봉인(SHA-256), 핵심 승인 감사추적, 규정 레지스터 *(다단계 Maker-Checker는 후속 과제)* |
| **선제적 리스크 관리** | 5채널 선행지표 EWS(조치 상태기계 포함), 동적한도, ESG 연동 |
| **통합 모니터링** | 42개 사용자 화면, 포트폴리오 맵(what-if 드래그·타임슬라이더), 의무관리함, 지역별 필터 |

### 시스템 범위

```
전략계층: 대시보드 · 자본관리 · 포트폴리오 전략 · 스트레스 테스트 · 자본 최적화
전술계층: 한도관리 · 동적한도 · 여신심사 · 결재함 · 가격결정(What-if)
운영계층: 고객관리 · 시설/실행현황 · 담보관리 · 연체관리 · 부실채권(Workout) · 금리인하요구권
통제계층: 전자 여신철 · 의무관리함 · 업무보고서(PDF) · 감사추적 · 규정 레지스터
분석계층: 조기경보(EWS) · 포트폴리오 맵 · 모델관리(MRM) · 고객수익성 · ESG · ALM · PF 사업장
```

---

## 주요 기능

### 1. 전략 대시보드 (Dashboard)
- 자본비율 현황 (BIS, CET1, Tier1, 레버리지)
- 포트폴리오 KPI: RAROC, 평균 PD/LGD, 대표등급
- EWS 경보 요약, 자본비율 추이 차트, 포트폴리오 분포
- **지역별 필터링** (수도권/대구경북/부산경남)

### 2. 여신심사 (Applications)
- 신청서 접수 → 서류심사 → 신용분석 → 심사위원회 → 최종승인 단계 현황·수동 변경 *(정식 FSM은 후속 과제)*
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
- 기업 고객 통합 조회 (2,160건)
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

### 18~28. 2026년 추가 화면 (v2.0)

| 화면 | 핵심 |
|------|------|
| **포트폴리오 맵** ★ | 1,999개사 2축 산점도. 포인트 드래그 what-if(EL·분류·충당금 실시간 재계산), 12개월 타임슬라이더 재생, 누적 담기(BIS 파급), CSV |
| **결재함** | 로그인 사용자 전결권 기준 결재 가능 건 구분·우선 정렬, 승인/반려 |
| **전자 여신철** | 건별 심사·승인 기록. 🔒 승인 당시 심사자료 확정·보존(SHA-256 무결성 검증값) |
| **의무관리함** | 정책예외 재검토·EWS 조치·코베넌트 점검·금리인하 SLA·승인조건 이행을 단일 목록으로 |
| **금리인하요구권** | 접수→보완(SLA 정지)→심사→결정→통지 상태기계, 영업일 기준 10영업일 SLA |
| **연체 관리** | DPD 버킷, Roll Rate 전이행렬(월별 스냅샷 실측), 추심활동, 워크아웃 자동이관 |
| **자산건전성 분류** | 5단계 분류·충당금 갭, 분류 이동행렬, 감독분류×IFRS9×EWS 3체계 대사 |
| **코베넌트 관리** | 재무약정 점검 일정·위반·치유기간 관리 |
| **PF 사업장** | 공정률-분양률 괴리 경보, 자기자본비율 구간 제도 시뮬레이션 |
| **포용금융 이행** | 중신용·개인사업자 공급 실적 vs 목표, 세그먼트 건전성 병기 |
| **보고·감사** | 업무보고서(PDF 다운로드), 전결규정, 감사추적, 정책예외, 규정 레지스터(효력일 관리) |

여기에 **규칙 기반 심사의견서 초안**(여신신청 상세에서 데이터 기반 7개 섹션 문안 자동 생성 + PDF),
**스토리 투어**(한 기업의 생애주기 악화 경로에서 손실흡수력·CET1까지 10단계 안내), **개발 여정**(소개 팝업에서 진입)이 더해집니다.

---

## 핵심 수리 모형

### RWA 산출 — Basel IRB 공식

```
자산상관계수:
  R = 0.12 × (1-e^(-50·PD))/(1-e^(-50)) + 0.24 × [1 - (1-e^(-50·PD))/(1-e^(-50))]

만기조정:
  b = (0.11852 - 0.05478 × ln(max(PD, 0.0001)))²

자본요구량:
  K = LGD × Φ(Φ⁻¹(PD)/√(1-R) + √(R/(1-R))×Φ⁻¹(0.999)) - PD×LGD
  K_adj = K × (1+(M-2.5)×b) / (1-1.5×b)

위험가중자산:
  RWA = K_adj × 12.5 × EAD
```

### RAROC (Risk-Adjusted Return on Capital)

```
개별 건: RAROC = (A×r - A×FTP - A×0.005 - PD×LGD×A) / (RWA × 10.5%)
포트폴리오: RAROC = (Σ(Oi×ri) - ΣOi×0.035 - ΣELi) / (ΣRWA×0.105)

비용률: 조달(FTP 테너별) + 운영(0.5%) — 포트폴리오 총비용률 3.5% (2026-08 금리 현실화)
경제적자본: EC = RWA × 10.5% (BIS 8% + 보전완충 2.5%)
허들레이트: 기본 15% (규정 레지스터 정본, hurdle_rate 테이블·코드 상수 정렬 완료 - 규모별 13~17% 차등)
```

### 가격결정 (Pricing)

```
r_final = r_base(2.7%) + FTP spread(0.5%) + Credit spread + Opex(0.2%) + Margin(1.0%)
        + Strategy adj + Collateral adj

Credit spread = EL spread + UL spread
  EL spread = PD × LGD
  UL spread = EL spread × 0.5 × 적용 Hurdle rate
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

### 자산건전성 분류 및 대손충당금 — 감독규정 기준

```
연체기간 분류 (은행업감독업무시행세칙 별표3)
  정상       연체 30일 미만
  요주의     연체 30일 이상 90일 미만          (1개월 이상 3개월 미만)
  고정       연체 90일 이상 중 회수예상가액 해당분
  회수의문   회수예상가액 초과분 중 연체 90~364일
  추정손실   회수예상가액 초과분 중 연체 365일 이상  (12개월 이상)

  → 3개월 이상 연체 건은 담보 인정가액을 기준으로 분할분류한다.
    PD·EWS 기준과 함께 가장 불리한 등급을 적용(보수주의).

대손충당금 최저적립률 (은행업감독규정 제29조, 기업여신)
  정상 0.85% / 요주의 7% / 고정 20% / 회수의문 50% / 추정손실 100%

  회계상 충당금은 IFRS 9 ECL로 적립하고, 그 금액이 위 최저적립액에
  미달하면 차액을 대손준비금으로 적립한다.
```

### IFRS 9 Stage 판정 (기업회계기준서 제1109호)

```
Stage 1  신용위험의 유의적 증가 없음                → 12개월 ECL
Stage 2  SICR 발생                                  → 전기간 ECL
         트리거: PD 2배 상승 | 등급 2 notch 하락
                 | EWS < 55 | 연체 30일 이상(5.5.11 추정)
Stage 3  신용손상 발생 (부록A)                      → 개별 평가
         요건: 연체 90일 초과(B5.5.37 채무불이행 추정)
               또는 워크아웃 등 객관적 손상 증거

  PD 수치 단독(예: PD ≥ 20%)은 기준서상 손상 요건이 아니므로
  Stage 3 판정에 쓰지 않는다.
```

상세 수식은 [기술 보고서](CLMS_Technical_Report.md) 참조.

---

## 시스템 아키텍처

```
┌──────────────────────────────────────────────────────────────┐
│                     Frontend (React 18 + TypeScript)          │
│  37 User Views · RegionFilter · Recharts · Tailwind · Vite    │
├──────────────────────────────────────────────────────────────┤
│                     Backend (FastAPI + SQLAlchemy)             │
│  38 API Routers · 242 Paths · calculations.py (수리엔진)      │
├──────────────────────────────────────────────────────────────┤
│                     Database (SQLite)                          │
│  95 Business Tables · 2,160 Customers · 3 Regions             │
└──────────────────────────────────────────────────────────────┘
```

---

## 프로젝트 구조

```
imbank-clms-demo/
├── backend/
│   ├── app/
│   │   ├── api/                    # API 모듈 44개 (라우터 43 + helper 1, 아래는 대표 파일)
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
│   │   ├── pages/                  # 사용자 화면 42개 · 페이지 컴포넌트 46개
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
│   ├── schema.sql                  # 핵심 스키마 (적용 DB는 마이그레이션·확장 포함 95개)
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

## 배포

**배포 정본은 Render 하나다** (`render.yaml`). 과거에 Vercel 구성이 함께 있었으나
서버리스 환경의 읽기 전용 파일시스템이 SQLite 구조와 맞지 않아 제거했다.

### 구조

```
단일 uvicorn 프로세스
  ├─ /api/*   FastAPI 라우터 38개 (242 path / 243 operation)
  └─ /*       사전 빌드된 SPA (frontend/dist) 를 StaticFiles + FileResponse 로 서빙
```

프론트엔드를 별도 호스팅하지 않고 백엔드가 함께 서빙한다
(`backend/app/main.py:110-127`). 따라서 **`frontend/dist`는 리포에 커밋되어야 한다.**
`.gitignore`의 Python `dist/` 패턴에 걸리지 않도록 `!frontend/dist/` 예외가 있으니
지우지 말 것. PoC DB(`database/imbank_demo.db`)도 같은 이유로 `*.db` 예외로 추적한다.

### 배포 전 체크리스트

```bash
# 1. 프론트엔드 빌드 — 번들 해시가 바뀌므로 반드시 dist 전체를 커밋한다
cd frontend && npm run build

# 2. index.html이 참조하는 asset이 실제로 존재하는지 확인
cd .. && grep -o '/assets/[^"]*' frontend/dist/index.html | \
  while read f; do [ -f "frontend/dist$f" ] && echo "OK $f" || echo "MISSING $f"; done

# 3. 로컬에서 Render와 동일한 방식으로 기동해 확인
cd backend && uvicorn app.main:app --port 8177
#   /health, /api/dashboard/summary, SPA 딥링크(/covenant) 모두 200 이어야 한다

git add frontend/dist && git commit
```

2단계에서 `MISSING`이 나오면 배포 화면이 백지가 된다. 신규 빌드 산출물을
커밋하지 않고 `index.html`만 갱신했을 때 발생하는 전형적인 실수다.

### 설정 요약

| 항목 | 값 |
|------|-----|
| 런타임 | Python 3.13.4 |
| 리전 | Singapore (무료 플랜 중 한국 최근접) |
| 빌드 | `pip install -r requirements.txt` |
| 기동 | `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| 헬스체크 | `/health` |

---

## API 엔드포인트

총 **265개 경로** (OpenAPI 기준 · 아래는 대표 모듈 발췌). 대부분 `?region=CAPITAL|DAEGU_GB|BUSAN_GN` 파라미터 지원.

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

### 테이블 분류 (업무 테이블 103개)

| 계층 | 주요 테이블 |
|------|------------|
| **고객·그룹·담보** | customer, borrower_group, borrower_group_member, collateral, group_guarantee |
| **신청·승인·실행** | loan_application, approval_history, decision_snapshot, facility, limit_reservation |
| **등급·가격·자본** | risk_parameter, credit_rating_result, pricing_result, hurdle_rate, capital_position |
| **한도·신용공여** | limit_definition, limit_exposure, credit_exposure_ledger, portfolio_strategy |
| **EWS·사후관리** | ews_alert, ews_action, covenant, delinquency_record, notification_log, workout_case |
| **회계·모델·통제** | ecl_calculation, asset_classification, model_registry, rule_register, audit_log |
| **확장분석** | stress_scenario, customer_profitability, esg_assessment, alm_scenario_result, pf_project |

### 데이터 규모

| 구분 | 건수 |
|------|-----:|
| 고객 | 2,160 |
| 여신신청 | 3,794 |
| 여신 (facility) | 3,734 |
| 신용공여 원장 | 7,541 |
| 승인 이력 | 157 |
| 감사로그 | 23 |

현재 운영 준비도, 통제 공백, 추가 기능의 시스템 경계와 인수기준은
[은행 요구기능 갭 연구](docs/BANK_REQUIRED_CAPABILITIES_RESEARCH_2026-08-11.md)를 참조하십시오.

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
| 조달비용률 (FUNDING_RATE) | 3.0% | FTP 현실화 반영 (실측 수신금리 2.10% 참조) |
| 운영비율 (OPEX_RATE) | 0.5% | |
| 총비용률 (COST_RATE) | 3.5% | 포트폴리오 대시보드 적용 |
| 경제적 자본비율 | 10.5% | BIS 8% + 보전완충 2.5% |
| 허들레이트 | 10·12·14·15% 혼재 | 현재 정합성 결함. 운영 사용 전 유효일자 기준 단일 정책으로 통합 필요 |

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

### v1.9.1 (2026-08-22) — EWS 8채널 확장 + 채널 선행성 검증

`docs/EWS_8CHANNEL_DESIGN_2026-08-21.md` 전량 구현 (migration 011).

- **신규 3채널**: 카드매출(동의 484사)·고용(동의 1,190사)·상거래연체(CB 법정집중).
  이벤트 기업에 채널별 상이한 악화 시작점을 주입해 리드타임 차이를 시연
  (합성 백테스트 - 생성 규칙의 재확인이며 실데이터 성능 검증이 아님을 화면에 상시 고지)
- **채널 선행성 백테스트**: 워크아웃·DPD90 91사 vs 대조군 400사 - 채널별 탐지율·
  리드타임·대조군 경보율 + Wilson 95% CI·표본충분성 표시. '채널 검증' 탭 신설
- **가중치 거버넌스**: 가중치를 rule_register 정본으로 이관(세그먼트 3종, SOHO 신설),
  백테스트 기반 제안(±5%p 점진)은 부서장 이상 승인 + 감사기록으로만 발효,
  발효 즉시 전 고객 종합점수 재계산 (services/ews_channels.py 단일 정본)
- **동의 관리**: 신용정보법 §32 동의 레지스트리 - 만료·철회 채널 자동 결측 전환,
  가중치 재정규화, channel_coverage 로 사유 기록. 만료 임박 D-30 표시
- EWS 탭 7→10 (매출·고용 / 상거래연체 / 채널 검증), 투어 ② 8채널로 갱신
- 회귀 테스트 3건 추가, 220개 전건 통과

### v1.9 (2026-08-19) — 규제 대응·건전성 고도화 P1~P8 (화면 표시 버전 v1.9 로 상향)

`docs/IMPROVEMENT_RESEARCH_2026-08-19.md` 연구의 권장 실행 순서(QW → P1~P8)를 전량 반영.
핵심 프레임: iM금융 2026.2Q 컨퍼런스콜에서 경영진이 공언한 두 목표(CRO: NPL커버리지
연말 100% 회복 / CFO: CET1 12.3%)를 그대로 화면으로 만들었다.

- **QW** 상태 변경 API 전반 감사기록 일원화 (covenant 웨이버·automation 실행·NPL 이관·
  추심활동·재무제표·EWS 트리거) — 웨이버는 critical(실패 시 롤백)
- **P1 손실흡수력 관리** (`/loss-absorption`) — 커버리지 경로 시뮬레이터(적립·상각·매각
  3레버), 연말 100% 필요 적립액 역산, 감독 §29 vs ECL 이중구조 실측 블록
- **P2 CET1 경로** (`/cet1-path`) — output floor 65→72.5% 경과규정 반영 연도별 경로,
  생산적 금융 위험가중치 시나리오, RAROC 리밸런싱 연동
- **P3 지역 리밸런싱** (`/region-rebalancing`) — 재투자 의무 하한 ↔ 편중 상한 양면 게이지,
  신규취급 지역 구성 추이, 산업×지역 히트맵
- **P4 개인사업자 심화** (포용금융 확장) — SOHO 히트맵·DPD 버킷, 새출발기금 요건 매칭,
  채무조정 연계 등록(팀장 이상 + 감사 + 중복 409)
- **P5 책무구조도 증거체인** (`/accountability`) — 책무 8건 ↔ 통제활동 매핑, 증거를
  audit_log 실측 집계(EVIDENCED/GAP/IDLE), 임원별 관리의무 점검 리포트
- **P6 거래 생애주기** (`/lifecycle`, migration 007) — 기한연장·조건변경 재승인,
  에버그리닝 플래그 시 부서장 이상 전결 상향 + 사후 관제
- **P7 ECL 전망모형 점검** (migration 008) — FLI 시나리오 민감도, 관리자 오버레이
  (부서장 이상·재검토 기한 강제), 독립 검증 제출용 점검 리포트 초안
- **P8 PF 충당금 차등화** — 사업성평가 4등급 자동 판정 → 차등 충당금(2/7/30/75% 가정)
  시뮬, 일률 적립 대비 증감
- 스토리 투어 7단계 → 10단계 확장 (연장 통제 → 손실흡수력 → CET1 경로로 마무리)
- 테스트 207개 전건 통과 (세션 풀 고갈 교정 포함)

### v2.0.1 (2026-08-15) — 승인조건 구조화

- 표준 승인조건 카탈로그 11종(선행 CP 5 · 후속 CS 6). 결재함 결재 모달에서
  승인금액·금리·기간을 확정하고 승인조건을 체크리스트로 부여한다.
  조건명은 서버가 카탈로그로 다시 채워 위조를 막고, 조건 지정 결재는 조건부승인으로 강제한다
- 전자 여신철에 선행/후속 배지와 이행기한 표시
- 결재함이 조건부승인 건을 제외해 2차 결재자가 그 건을 볼 수 없던 결함 수정
- 최종승인이 앞 단계에서 정한 승인금액·금리·기간을 NULL로 덮어쓰던 결함 수정
- 테스트가 배포용 데모 DB를 변형시켜 표본 소진 시 **조용히 skip**으로 바뀌던 구조를
  DB 사본 격리로 교정 — 승인 경로 회귀 테스트 8건이 실제로 실행되기 시작했다.
  177개(175 통과·2 건너뜀) → **188개 전건 통과**

### v2.0.0 (2026-08)

**내부통제·업무 완결성 (제3자 감사형 리뷰 2건 반영)**
- HMAC 토큰 인증 + 역할 4계정, 쓰기 API 인증 강제 (익명 쓰기 401)
- 전결권 서버 결정 · 동일인 중복결재 차단(409) · 전결권 우회 차단
  (승인금액은 (0, 신청금액] 검증, 전결 판정은 신청금액 기준) · 승인조건 영속화
- 승인 시점 심사자료 봉인: canonical JSON + SHA-256, 과거 승인건 소급 등재 66건
- 신용공여 원장(credit_exposure_ledger, CCF 적용) + 은행법 §35 법정 3한도 조회·경보 PoC
  *(승인·실행 거래 반영형 상시통제는 후속 과제)*
- EWS 조치 상태기계(순서 가드·기한초과 자동 상향보고) · 금리인하요구권 SLA 상태기계
- 규정 레지스터 15건(효력일·버전·파라미터 등록·조회), 통합 의무관리함(5원천 95건)
- DB 마이그레이션 체계(schema_migrations) + 규제 시나리오 회귀 테스트, 총 172개(171 통과·1 건너뜀) + CI

**화면·UX**
- 포트폴리오 맵 신설(what-if 드래그·타임슬라이더·누적 파급·CSV), 스토리 투어 7단계
- 규칙 기반 심사의견서 자동 초안(JSON+PDF), 개발 여정 팝업
- 로딩 UX 표준화(스켈레톤·오류·빈 데이터 3상태 분리), Roll Rate 전이 이력 실측화
- 업무보고서 11개 섹션 + 서버 PDF(fpdf2·Pretendard), 조 단위 금액 표기

**데이터 현실화 (iM뱅크 공시·실측 대조)**
- 고객 699 → 2,160개사(업종 40종·담보 7종), 총여신 36.7조 (실측 기업여신 37.0조 대비 -0.8%)
- 자기자본 5.5조 · RWA 38조 · BIS 14.47% (종전 2.6배 과대를 실제 규모로 조정)
- 연체율 0.94% (실측 1.0% 정합)
- 여신금리 현실화: 잔액가중 6.04% → 4.70% (실측 4.36% 대비 기업 프리미엄 반영),
  FTP·프라이싱·조달원가 동반 조정으로 포트폴리오 RAROC 16.6% 유지

**성능**
- 응답 gzip(-87%) · 인덱스 14개 · TTL 캐시로 주요 화면 7.7초 → 0.3초

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

이 프로젝트는 PoC 및 교육 목적으로 제작되었습니다.

MIT License

---

*iM뱅크 CLMS — 기업여신생애주기관리시스템 PoC*
