# EWS 8채널 확장 설계 — 카드매출·고용·상거래연체 + 채널 선행성 검증

- 작성일: 2026-08-21 (설계 승인 대기)
- 배경: 현행 EWS는 5개 대체채널(거래행태·공적정보·시장신호·뉴스감성·공급망) + 재무로 구성된다. 본 설계는 3개 채널을 추가해 8채널 체계로 확장하고, "채널을 늘리는 것"이 아니라 **"채널의 선행성을 증명하는 것"** 을 선진화의 핵심으로 삼는다.
- 선정 근거: 신규 3종은 모두 개인사업자·중소기업 세그먼트(iM뱅크 기업여신의 87%, P4 모듈)에 직결되고, 국내 제도(신용정보법 동의·마이데이터·상거래 신용정보 집중) 위에서 실제 확보 가능한 데이터다.

## 1. 신규 채널 정의

| 채널 | 코드 | 원천(실제) | 잡는 신호 | 선행성 목표 |
|---|---|---|---|---|
| 카드매출 | `CARD_SALES` | 카드사·VAN 가맹점 매출 (동의) | 월매출 YoY·연속 하락, 영업일수 급감 | 6~12개월 |
| 고용 | `EMPLOYMENT` | 4대보험 피보험자·납부 (동의) | 피보험자 수 감소(감원), 보험료 체납 | 3~6개월 |
| 상거래연체 | `B2B_DELINQ` | 기업 간 상거래 신용정보 (KED·NICE) | 납품대금 결제 지연 이벤트 (은행 연체보다 선행) | 3~9개월 |

적용 대상: 카드매출은 SOHO·소매업종 중심(가맹점 보유 기업), 고용·상거래연체는 전 기업. **대상이 아니거나 동의가 없는 기업은 채널 결측으로 처리**하고 가중치를 재정규화한다(§4) — 있는 척하지 않는다(외부감사 #10 provenance 원칙).

## 2. 데이터 모델 (migration 011)

기존 패턴(채널별 원천 테이블 + `ews_composite_score` 채널 점수 컬럼)을 그대로 따른다.

```sql
-- 원천 3종
CREATE TABLE ews_card_sales_monthly (
    record_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, month TEXT NOT NULL, -- YYYY-MM
    card_sales_amount REAL, active_merchant_days INTEGER,
    mom_change_pct REAL, yoy_change_pct REAL,
    industry_percentile REAL,          -- 동업종 대비 상대 위치 (상권 효과 분리)
    UNIQUE(customer_id, month)
);
CREATE TABLE ews_employment_monthly (
    record_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, month TEXT NOT NULL,
    insured_count INTEGER, insured_change_3m INTEGER,
    premium_arrears_months INTEGER DEFAULT 0,   -- 4대보험 체납 개월수
    UNIQUE(customer_id, month)
);
CREATE TABLE ews_b2b_delinquency (
    event_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, event_date DATE NOT NULL,
    counterparty_count INTEGER, overdue_amount REAL, overdue_days INTEGER,
    event_type TEXT,        -- PAYMENT_DELAY | NOTE_EXTENSION | COMMERCIAL_DEFAULT
    resolved_date DATE
);

-- 채널 점수 (기존 컬럼 패턴 연장)
ALTER TABLE ews_composite_score ADD COLUMN card_sales_score REAL;
ALTER TABLE ews_composite_score ADD COLUMN employment_score REAL;
ALTER TABLE ews_composite_score ADD COLUMN b2b_delinq_score REAL;
ALTER TABLE ews_composite_score ADD COLUMN channel_coverage TEXT;  -- JSON: 채널별 가용 여부

-- 동의 관리 (신용정보법 §32·§33 - 규제 완결 요건)
CREATE TABLE ews_channel_consent (
    consent_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, channel TEXT NOT NULL,
    legal_basis TEXT,                  -- 신용정보법 동의 | 마이데이터 | CB 집중
    consent_date DATE, expiry_date DATE,
    status TEXT DEFAULT 'ACTIVE',      -- ACTIVE | EXPIRED | WITHDRAWN
    UNIQUE(customer_id, channel)
);
```

검증 지표는 **기존 `ews_validation_metrics`를 스키마 변경 없이 재사용**한다: `scope_type='CHANNEL'`, `scope_value='CARD_SALES'` 행으로 채널별 지표를 적재한다 (기존 scope 체계가 이미 이 확장을 허용).

## 3. 채널 점수화 규칙 (0~100, 낮을수록 위험 - 기존 체계 동일)

결정론적 룰 기반(기존 채널과 동일 철학 - 재현 가능·설명 가능):

- **카드매출**: 100 기점 감점 — YoY –15% 초과 하락 시 구간별 감점(–15%p→–20점, –30%p→–40점), 3개월 연속 MoM 하락 –15점, 영업일수 20% 급감 –15점, 동업종 하위 10% –10점. 동업종 percentile 로 상권·계절 효과를 분리한다.
- **고용**: 피보험자 3개월 –10% → –25점, –20% → –45점. 보험료 체납 1개월 –20점, 2개월+ –40점. (감원과 체납의 결합은 유동성 위기의 강신호 → 두 조건 동시면 추가 –10점)
- **상거래연체**: 미해소 이벤트 건수·금액·경과일 가중 감점. COMMERCIAL_DEFAULT(상거래 부도) 1건이면 즉시 35점 하한 관통 허용(CRITICAL 직행) — 은행 연체 없이도 실질 부도 상태인 기업을 잡는 채널이므로.

## 4. 가중치 개편 — 규정 레지스터 정본화

가중치를 생성기 하드코딩에서 **`rule_register`(규정 레지스터, 효력일 관리 기구현) 정본**으로 옮긴다. 세그먼트 3종:

| 채널 | 상장 | 비상장 일반 | 비상장 SOHO |
|---|---|---|---|
| 거래행태 | 0.20 | 0.20 | 0.20 |
| 카드매출 | — | 0.05 | **0.20** |
| 상거래연체 | 0.10 | **0.15** | 0.10 |
| 고용 | 0.05 | **0.10** | 0.05 |
| 공적정보 | 0.10 | 0.15 | 0.10 |
| 시장신호 | 0.15 | — | — |
| 뉴스감성 | 0.10 | 0.10 | 0.05 |
| 공급망 | 0.15 | 0.10 | 0.05 |
| 재무 | 0.15 | 0.15 | 0.25* |

\* SOHO 는 재무제표 신뢰도가 낮아 실측 행동 데이터(카드매출)에 비중을 옮기되, 재무 결측이 잦으므로 결측 재정규화가 흡수한다.

**결측 재정규화**: 가용 채널의 가중치 합으로 나눠 정규화하고, `channel_coverage`에 채널별 가용/결측/동의만료를 기록해 화면에 커버리지 배지로 표시한다. 동의 만료(`ews_channel_consent.expiry_date` 경과) 채널은 **자동 결측 전환** — 만료 데이터로 점수를 내지 않는 것이 규제 완결이다.

**가중치 변경 거버넌스**: 검증 화면(§5)의 가중치 재제안을 부서장 이상이 승인해야 rule_register 새 버전으로 발효(감사기록 critical). 모형 가중치가 담당자 수정으로 조용히 바뀌는 것을 막는다.

## 5. 채널 선행성 검증 (이 설계의 핵심)

**방법론** — 사후 이벤트 기준 백테스트:
1. 이벤트 정의: 부도여신 발생·워크아웃 이관·DPD 90 도달 (기존 데이터에서 식별 가능)
2. 각 이벤트 기업에 대해, 채널별 점수가 경보 임계(55, WATCH 경계) 아래로 최초 하락한 시점과 이벤트 시점의 차 = **채널 리드타임**
3. 채널별 산출 지표: 탐지율(이벤트 전 경보 발화 비율), 리드타임 중앙값/평균, 3·6·12개월 전 경보율, **오경보율**(경보 후 12개월 무이벤트 비율 — 탐지율만 보면 항상 경보하는 채널이 이기므로 반드시 쌍으로)
4. 적재: `ews_validation_metrics` (scope_type='CHANNEL')
5. **가중치 재제안**: 정규화 점수 = 탐지율 × f(리드타임) × (1−오경보율) 비례 배분 → 현행 가중치와 나란히 표시, diff와 근거 제시. 적용은 §4 거버넌스 경유.

**API**: `GET /api/ews-advanced/channel-validation` (채널별 지표 + 리드타임 분포), `GET .../weight-proposal`, `POST .../weight-proposal/approve` (부서장+, 감사 critical).

**화면**: EWS 탭 추가 ① `채널 검증` — 채널×지표 매트릭스, 리드타임 분포 차트, 가중치 현행 vs 제안 비교 + 승인 버튼. "이 은행의 EWS 가중치는 주장이 아니라 백테스트로 정해진다"가 시연 메시지.

## 6. 화면 구성 (탭 6→8)

| 탭 | 내용 |
|---|---|
| `매출·고용` (신규 1탭 통합) | 카드매출 급감 기업 목록·추이 차트, 고용 감소·체납 기업, SOHO 필터 기본 |
| `상거래연체` (신규) | 미해소 이벤트 타임라인, 은행 연체와의 교차 (상거래연체 有·은행연체 無 = 선행 포착 구간 강조) |
| `채널 검증` (신규) | §5. 가중치 거버넌스 포함 |

통합 대시보드는 8채널 레이더/바 + 커버리지 배지(동의 만료 D-30 경고)로 확장. 고객 상세에는 채널별 점수·데이터 출처·동의 상태를 함께 표시한다.

**시연 스토리 연결**: P4 채무조정 후보(예: 부실우려 SOHO)의 카드매출이 연체 발생 8개월 전부터 하락하는 궤적을 심어, "재무제표·연체보다 카드매출이 먼저 알았다 → 새출발기금 연계(P4)까지"로 이어지는 흐름을 만든다. 스토리 투어 ②(5채널 조기경보) 문구를 8채널로 갱신.

## 7. 데모 데이터 생성 (`database/generate_ews_extended_channels.py`)

- 기간: 24개월 월별 (검증 백테스트가 성립하려면 이벤트 이전 이력이 필요)
- 카드매출: SOHO 556사 + 소매·요식 업종, 동의율 70% 가정. 고용: 전 기업 동의율 60%. 상거래연체: CB 집중 데이터라 동의 불요(법정 집중) — 전 기업.
- **선행 패턴 주입**: 기존 부도·워크아웃·DPD90 기업(약 20~40사)에 이벤트 시점 역산으로 채널별 악화 곡선을 심는다 — 카드매출은 8~10개월 전부터, 고용은 5개월 전부터, 상거래연체는 4개월 전부터. 이렇게 해야 검증 화면이 채널별로 **서로 다른 리드타임**을 실측으로 보여준다 (모두 같은 시점에 악화하면 검증 화면이 무의미).
- 정상 기업 일부에도 노이즈 경보를 심어 오경보율이 0이 아니게 한다 (완벽한 채널은 백테스트의 신뢰를 깎는다).
- 동의 데이터: 만료 임박·만료·철회 사례 포함 (커버리지 배지 시연용).

## 8. 구현 단계·규모

| 단계 | 내용 | 규모 |
|---|---|---|
| Phase 1 | migration 011 + 데이터 생성기 + 채널 점수화·composite 개편(결측 재정규화·rule_register 가중치) | M |
| Phase 2 | API 3종 + 화면 2탭(매출·고용, 상거래연체) + 통합 대시보드 8채널 | M |
| Phase 3 | 채널 검증 백테스트 + 검증 탭 + 가중치 제안·승인 거버넌스 + 동의 관리 | M |

합계 L (커밋 3개 단위 권장). 통제 완결 원칙 유지: 가중치 승인·동의 상태 변경은 권한 + 감사기록.

## 9. 비목표

- 실데이터 연동(카드사 API·건보공단·CB 실계약) — PoC 는 합성 데이터로 구조와 검증 방법론을 증명한다.
- ML 기반 채널 융합(GNN·시계열 딥러닝) — 룰 기반 점수화의 설명가능성이 감독 대응(모형 검증)에 유리하며, ML 은 채널 검증 체계가 자리잡은 뒤의 후속 과제.
- 개인 CB(대표자 개인신용) 연동 — 개인신용정보 별도 동의 체계가 필요해 범위 밖.
