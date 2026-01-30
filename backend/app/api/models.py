"""
모델관리/MRM API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..core.database import get_db

router = APIRouter(prefix="/api/models", tags=["Models"])


@router.get("")
def get_models(db: Session = Depends(get_db)):
    """모델 레지스트리"""
    results = db.execute(text("""
        SELECT model_id, model_name, model_type, model_purpose, risk_tier,
               development_date, last_validation_date, next_validation_date,
               status, owner_dept
        FROM model_registry
        ORDER BY model_type, model_name
    """)).fetchall()

    return [
        {
            "model_id": r[0],
            "model_name": r[1],
            "model_type": r[2],
            "model_purpose": r[3],
            "risk_tier": r[4],
            "development_date": r[5],
            "last_validation_date": r[6],
            "next_validation_date": r[7],
            "status": r[8],
            "owner_dept": r[9]
        }
        for r in results
    ]


@router.get("/summary/status")
def get_models_status(db: Session = Depends(get_db)):
    """모델 현황 요약"""

    # 상태별 카운트
    by_status = db.execute(text("""
        SELECT status, COUNT(*) FROM model_registry GROUP BY status
    """)).fetchall()

    # 검증 예정
    upcoming_validation = db.execute(text("""
        SELECT model_id, model_name, next_validation_date
        FROM model_registry
        WHERE next_validation_date IS NOT NULL
        ORDER BY next_validation_date
        LIMIT 5
    """)).fetchall()

    # 최근 경보
    recent_alerts = db.execute(text("""
        SELECT mpl.model_id, mr.model_name, mpl.monitoring_date, mpl.alert_type,
               mpl.gini_coefficient, mpl.psi
        FROM model_performance_log mpl
        JOIN model_registry mr ON mpl.model_id = mr.model_id
        WHERE mpl.alert_triggered = 1
        ORDER BY mpl.monitoring_date DESC
        LIMIT 10
    """)).fetchall()

    return {
        "status_summary": {r[0]: r[1] for r in by_status},
        "upcoming_validations": [
            {"model_id": v[0], "model_name": v[1], "date": v[2]}
            for v in upcoming_validation
        ],
        "recent_alerts": [
            {
                "model_id": a[0],
                "model_name": a[1],
                "date": a[2],
                "alert_type": a[3],
                "gini": a[4],
                "psi": a[5]
            }
            for a in recent_alerts
        ]
    }


@router.get("/overrides")
def get_override_summary(db: Session = Depends(get_db)):
    """Override 현황"""
    results = db.execute(text("""
        SELECT override_direction, COUNT(*) as count,
               AVG(ABS(notch_change)) as avg_notch
        FROM override_monitoring
        GROUP BY override_direction
    """)).fetchall()

    # 최근 override
    recent = db.execute(text("""
        SELECT om.override_id, om.application_id, om.override_date,
               om.system_value, om.override_value, om.override_direction,
               om.notch_change, om.override_reason_text, om.outcome_status
        FROM override_monitoring om
        ORDER BY om.override_date DESC
        LIMIT 20
    """)).fetchall()

    # Override 비율
    total_ratings = db.execute(text("""
        SELECT COUNT(*) FROM credit_rating_result
    """)).fetchone()

    override_count = db.execute(text("""
        SELECT COUNT(*) FROM override_monitoring
    """)).fetchone()

    override_rate = (override_count[0] / total_ratings[0] * 100) if total_ratings[0] else 0

    return {
        "summary": [
            {"direction": r[0], "count": r[1], "avg_notch": r[2]}
            for r in results
        ],
        "recent_overrides": [
            {
                "override_id": r[0],
                "application_id": r[1],
                "date": r[2],
                "system_value": r[3],
                "override_value": r[4],
                "direction": r[5],
                "notch_change": r[6],
                "reason": r[7],
                "outcome": r[8]
            }
            for r in recent
        ],
        "override_rate": override_rate,
        "total_overrides": override_count[0] if override_count else 0,
        "thresholds": {
            "max_override_rate": 15,
            "max_upward_rate": 50
        }
    }


@router.get("/champion-challenger")
def get_champion_challenger(db: Session = Depends(get_db)):
    """Champion-Challenger 비교"""

    # 각 모델의 현재 버전 성능
    models = db.execute(text("""
        SELECT mr.model_id, mr.model_name,
               mv.version_no, mv.deployment_env,
               mpl.gini_coefficient, mpl.ks_statistic, mpl.psi, mpl.ar_ratio
        FROM model_registry mr
        JOIN model_version mv ON mr.model_id = mv.model_id
        LEFT JOIN model_performance_log mpl ON mv.version_id = mpl.version_id
        WHERE mv.status = 'ACTIVE'
        ORDER BY mr.model_id, mpl.monitoring_date DESC
    """)).fetchall()

    # 그룹화
    grouped = {}
    for m in models:
        if m[0] not in grouped:
            grouped[m[0]] = {
                "model_id": m[0],
                "model_name": m[1],
                "versions": []
            }
        grouped[m[0]]["versions"].append({
            "version": m[2],
            "env": m[3],
            "gini": m[4],
            "ks": m[5],
            "psi": m[6],
            "ar_ratio": m[7]
        })

    return list(grouped.values())


@router.get("/backtest/summary")
def get_backtest_summary(db: Session = Depends(get_db)):
    """등급별 PD Backtest 요약"""

    # 연도별/등급별 백테스트 결과
    results = db.execute(text("""
        SELECT gb.model_id, mr.model_name, gb.observation_year, gb.grade,
               gb.predicted_pd, gb.observation_count, gb.default_count,
               gb.actual_dr, gb.binomial_test_pvalue, gb.test_result
        FROM grade_backtest gb
        JOIN model_registry mr ON gb.model_id = mr.model_id
        ORDER BY gb.model_id, gb.observation_year DESC, gb.grade
    """)).fetchall()

    # 테스트 결과 요약
    summary = db.execute(text("""
        SELECT test_result, COUNT(*) as cnt
        FROM grade_backtest
        GROUP BY test_result
    """)).fetchall()

    # 최근 경보 (FAIL 또는 WARNING)
    alerts = db.execute(text("""
        SELECT gb.model_id, mr.model_name, gb.observation_year, gb.grade,
               gb.predicted_pd, gb.actual_dr, gb.test_result
        FROM grade_backtest gb
        JOIN model_registry mr ON gb.model_id = mr.model_id
        WHERE gb.test_result IN ('FAIL', 'WARNING')
        ORDER BY gb.observation_year DESC, gb.grade
    """)).fetchall()

    return {
        "backtest_results": [
            {
                "model_id": r[0],
                "model_name": r[1],
                "year": r[2],
                "grade": r[3],
                "predicted_pd": r[4],
                "observation_count": r[5],
                "default_count": r[6],
                "actual_dr": r[7],
                "p_value": r[8],
                "result": r[9]
            }
            for r in results
        ],
        "summary": {r[0]: r[1] for r in summary},
        "alerts": [
            {
                "model_id": a[0],
                "model_name": a[1],
                "year": a[2],
                "grade": a[3],
                "predicted_pd": a[4],
                "actual_dr": a[5],
                "result": a[6]
            }
            for a in alerts
        ],
        "methodology": {
            "test_type": "Binomial Test",
            "confidence_level": 0.95,
            "warning_threshold": 0.05,
            "fail_threshold": 0.01,
            "description": "예측 PD와 실제 부도율(DR) 간 통계적 유의성을 검정. p-value < 0.01이면 FAIL, < 0.05이면 WARNING."
        }
    }


@router.get("/override-performance")
def get_override_performance(db: Session = Depends(get_db)):
    """Override 성과 분석"""

    # Override 결과 분석
    results = db.execute(text("""
        SELECT oo.override_direction, oo.actual_outcome, oo.outcome_correct,
               COUNT(*) as cnt
        FROM override_outcome oo
        GROUP BY oo.override_direction, oo.actual_outcome, oo.outcome_correct
    """)).fetchall()

    # 방향별 정확도
    accuracy = db.execute(text("""
        SELECT override_direction,
               COUNT(*) as total,
               SUM(CASE WHEN outcome_correct = 1 THEN 1 ELSE 0 END) as correct,
               CAST(SUM(CASE WHEN outcome_correct = 1 THEN 1 ELSE 0 END) AS REAL) / COUNT(*) as accuracy
        FROM override_outcome
        WHERE actual_outcome IS NOT NULL
        GROUP BY override_direction
    """)).fetchall()

    # 상세 내역
    details = db.execute(text("""
        SELECT oo.outcome_id, oo.override_id, om.application_id, om.override_date,
               oo.system_grade, oo.override_grade, oo.override_direction,
               oo.actual_outcome, oo.outcome_correct,
               om.override_reason_text
        FROM override_outcome oo
        JOIN override_monitoring om ON oo.override_id = om.override_id
        ORDER BY om.override_date DESC
    """)).fetchall()

    # Type I / Type II 오류 분석
    type1_errors = db.execute(text("""
        SELECT COUNT(*) FROM override_outcome
        WHERE override_direction = 'UPGRADE'
        AND actual_outcome IN ('DEFAULT', 'NPL')
    """)).fetchone()

    type2_errors = db.execute(text("""
        SELECT COUNT(*) FROM override_outcome
        WHERE override_direction = 'DOWNGRADE'
        AND actual_outcome = 'PERFORMING'
    """)).fetchone()

    return {
        "outcome_distribution": [
            {
                "direction": r[0],
                "outcome": r[1],
                "correct": r[2] == 1 if r[2] is not None else None,
                "count": r[3]
            }
            for r in results
        ],
        "accuracy_by_direction": [
            {
                "direction": a[0],
                "total": a[1],
                "correct": a[2],
                "accuracy_rate": round(a[3] * 100, 1) if a[3] else 0
            }
            for a in accuracy
        ],
        "error_analysis": {
            "type1_errors": type1_errors[0] if type1_errors else 0,
            "type1_description": "등급 상향 후 부도/NPL 발생 (Overconfidence)",
            "type2_errors": type2_errors[0] if type2_errors else 0,
            "type2_description": "등급 하향 후 정상 (Overcautious)",
        },
        "details": [
            {
                "outcome_id": d[0],
                "override_id": d[1],
                "application_id": d[2],
                "date": d[3],
                "system_grade": d[4],
                "override_grade": d[5],
                "direction": d[6],
                "outcome": d[7],
                "correct": d[8] == 1 if d[8] is not None else None,
                "reason": d[9]
            }
            for d in details
        ],
        "thresholds": {
            "acceptable_type1_rate": 5.0,
            "acceptable_type2_rate": 20.0,
            "min_accuracy": 70.0
        }
    }


@router.get("/vintage-analysis")
def get_vintage_analysis(cohort_type: str = None, db: Session = Depends(get_db)):
    """Vintage 분석"""

    query = """
        SELECT vintage_id, vintage_month, cohort_type, cohort_value,
               origination_count, origination_amount,
               mob_3_delinquent_rate, mob_6_delinquent_rate,
               mob_12_delinquent_rate, mob_12_default_rate,
               mob_24_default_rate, cumulative_loss_rate
        FROM vintage_analysis
    """

    params = {}
    if cohort_type:
        query += " WHERE cohort_type = :ctype"
        params["ctype"] = cohort_type

    query += " ORDER BY vintage_month DESC, cohort_type, cohort_value"

    results = db.execute(text(query), params).fetchall()

    # 코호트 유형별 요약
    summary = db.execute(text("""
        SELECT cohort_type,
               AVG(mob_3_delinquent_rate) as avg_mob3,
               AVG(mob_6_delinquent_rate) as avg_mob6,
               AVG(mob_12_default_rate) as avg_mob12_dr,
               AVG(cumulative_loss_rate) as avg_loss
        FROM vintage_analysis
        GROUP BY cohort_type
    """)).fetchall()

    # 트렌드 분석 (월별)
    trend = db.execute(text("""
        SELECT vintage_month,
               AVG(mob_3_delinquent_rate) as avg_mob3,
               AVG(mob_6_delinquent_rate) as avg_mob6,
               AVG(mob_12_default_rate) as avg_dr
        FROM vintage_analysis
        WHERE cohort_type = 'OVERALL'
        GROUP BY vintage_month
        ORDER BY vintage_month
    """)).fetchall()

    return {
        "vintages": [
            {
                "vintage_id": r[0],
                "month": r[1],
                "cohort_type": r[2],
                "cohort_value": r[3],
                "count": r[4],
                "amount": r[5],
                "mob_3_del_rate": r[6],
                "mob_6_del_rate": r[7],
                "mob_12_del_rate": r[8],
                "mob_12_dr": r[9],
                "mob_24_dr": r[10],
                "loss_rate": r[11]
            }
            for r in results
        ],
        "summary_by_type": [
            {
                "cohort_type": s[0],
                "avg_mob3_delinquency": round(s[1] * 100, 2) if s[1] else None,
                "avg_mob6_delinquency": round(s[2] * 100, 2) if s[2] else None,
                "avg_mob12_default": round(s[3] * 100, 2) if s[3] else None,
                "avg_cumulative_loss": round(s[4] * 100, 2) if s[4] else None
            }
            for s in summary
        ],
        "monthly_trend": [
            {
                "month": t[0],
                "mob3": round(t[1] * 100, 2) if t[1] else None,
                "mob6": round(t[2] * 100, 2) if t[2] else None,
                "mob12_dr": round(t[3] * 100, 2) if t[3] else None
            }
            for t in trend
        ],
        "analysis_info": {
            "mob_periods": ["MOB 3", "MOB 6", "MOB 12", "MOB 24"],
            "cohort_types": ["OVERALL", "GRADE", "INDUSTRY"],
            "description": "빈티지 분석은 동일 시점에 취급된 여신의 시간 경과에 따른 연체/부도 패턴을 추적합니다."
        }
    }


@router.get("/backtest/{model_id}")
def get_model_backtest(model_id: str, db: Session = Depends(get_db)):
    """특정 모델의 상세 백테스트 결과"""

    results = db.execute(text("""
        SELECT observation_year, grade, predicted_pd, observation_count,
               default_count, actual_dr, binomial_test_pvalue, test_result
        FROM grade_backtest
        WHERE model_id = :mid
        ORDER BY observation_year, grade
    """), {"mid": model_id}).fetchall()

    # 연도별 그룹화
    by_year = {}
    for r in results:
        year = r[0]
        if year not in by_year:
            by_year[year] = []
        by_year[year].append({
            "grade": r[1],
            "predicted_pd": r[2],
            "count": r[3],
            "defaults": r[4],
            "actual_dr": r[5],
            "p_value": r[6],
            "result": r[7]
        })

    # 연도별 요약 통계
    yearly_summary = db.execute(text("""
        SELECT observation_year,
               SUM(observation_count) as total_obs,
               SUM(default_count) as total_def,
               AVG(predicted_pd) as avg_predicted,
               CAST(SUM(default_count) AS REAL) / SUM(observation_count) as overall_dr,
               SUM(CASE WHEN test_result = 'PASS' THEN 1 ELSE 0 END) as pass_count,
               SUM(CASE WHEN test_result = 'WARNING' THEN 1 ELSE 0 END) as warn_count,
               SUM(CASE WHEN test_result = 'FAIL' THEN 1 ELSE 0 END) as fail_count
        FROM grade_backtest
        WHERE model_id = :mid
        GROUP BY observation_year
        ORDER BY observation_year
    """), {"mid": model_id}).fetchall()

    return {
        "model_id": model_id,
        "by_year": by_year,
        "yearly_summary": [
            {
                "year": s[0],
                "total_observations": s[1],
                "total_defaults": s[2],
                "avg_predicted_pd": s[3],
                "overall_dr": s[4],
                "pass_count": s[5],
                "warning_count": s[6],
                "fail_count": s[7]
            }
            for s in yearly_summary
        ]
    }


@router.get("/vintage-analysis/{vintage_month}")
def get_vintage_detail(vintage_month: str, db: Session = Depends(get_db)):
    """특정 월 빈티지 상세"""

    results = db.execute(text("""
        SELECT cohort_type, cohort_value, origination_count, origination_amount,
               mob_3_delinquent_rate, mob_6_delinquent_rate,
               mob_12_delinquent_rate, mob_12_default_rate,
               mob_24_default_rate, cumulative_loss_rate
        FROM vintage_analysis
        WHERE vintage_month = :month
        ORDER BY cohort_type, cohort_value
    """), {"month": vintage_month}).fetchall()

    return {
        "vintage_month": vintage_month,
        "cohorts": [
            {
                "type": r[0],
                "value": r[1],
                "count": r[2],
                "amount": r[3],
                "metrics": {
                    "mob_3": r[4],
                    "mob_6": r[5],
                    "mob_12_del": r[6],
                    "mob_12_dr": r[7],
                    "mob_24_dr": r[8],
                    "loss_rate": r[9]
                }
            }
            for r in results
        ]
    }


@router.get("/specifications/{model_id}")
def get_model_specifications(model_id: str, db: Session = Depends(get_db)):
    """모델 상세 사양 및 이론적 배경"""

    # 모델 기본 정보
    model = db.execute(text("""
        SELECT model_id, model_name, model_type, model_purpose, risk_tier,
               development_date, status, owner_dept
        FROM model_registry
        WHERE model_id = :mid
    """), {"mid": model_id}).fetchone()

    if not model:
        return {"error": "Model not found"}

    # model_purpose (PD, LGD, EAD, PRICING, EWS) 기준으로 사양 조회
    model_purpose = model[3]

    # 모델 타입별 상세 사양
    specifications = get_model_type_specifications(model_purpose)

    return {
        "model": {
            "model_id": model[0],
            "model_name": model[1],
            "model_type": model[2],
            "model_purpose": model[3],
            "risk_tier": model[4],
            "development_date": model[5],
            "status": model[6],
            "owner_dept": model[7]
        },
        "specifications": specifications
    }


@router.get("/{model_id}")
def get_model_detail(model_id: str, db: Session = Depends(get_db)):
    """모델 상세 정보"""

    # 기본 정보
    model = db.execute(text("""
        SELECT * FROM model_registry WHERE model_id = :mid
    """), {"mid": model_id}).fetchone()

    # 버전 정보
    versions = db.execute(text("""
        SELECT version_id, version_no, deployment_env, effective_from,
               effective_to, performance_metrics, status
        FROM model_version
        WHERE model_id = :mid
        ORDER BY effective_from DESC
    """), {"mid": model_id}).fetchall()

    # 최근 성능 로그
    performance = db.execute(text("""
        SELECT monitoring_date, gini_coefficient, ks_statistic, auroc,
               psi, csi, predicted_dr, actual_dr, ar_ratio,
               alert_triggered, alert_type
        FROM model_performance_log
        WHERE model_id = :mid
        ORDER BY monitoring_date DESC
        LIMIT 12
    """), {"mid": model_id}).fetchall()

    return {
        "model": {
            "model_id": model[0] if model else None,
            "model_name": model[1] if model else None,
            "model_type": model[2] if model else None,
            "model_purpose": model[3] if model else None,
            "risk_tier": model[4] if model else None,
            "development_date": model[5] if model else None,
            "last_validation_date": model[6] if model else None,
            "next_validation_date": model[7] if model else None,
            "status": model[8] if model else None,
            "owner_dept": model[9] if model else None
        } if model else None,
        "versions": [
            {
                "version_id": v[0],
                "version_no": v[1],
                "deployment_env": v[2],
                "effective_from": v[3],
                "effective_to": v[4],
                "performance_metrics": v[5],
                "status": v[6]
            }
            for v in versions
        ],
        "performance_history": [
            {
                "date": p[0],
                "gini": p[1],
                "ks": p[2],
                "auroc": p[3],
                "psi": p[4],
                "csi": p[5],
                "predicted_dr": p[6],
                "actual_dr": p[7],
                "ar_ratio": p[8],
                "alert": p[9] == 1,
                "alert_type": p[10]
            }
            for p in reversed(performance)
        ]
    }


@router.get("/{model_id}/performance")
def get_model_performance(model_id: str, months: int = 12, db: Session = Depends(get_db)):
    """모델 성능 추이"""
    results = db.execute(text(f"""
        SELECT monitoring_date, gini_coefficient, ks_statistic, auroc,
               psi, ar_ratio, alert_triggered
        FROM model_performance_log
        WHERE model_id = :mid
        ORDER BY monitoring_date DESC
        LIMIT {months}
    """), {"mid": model_id}).fetchall()

    return {
        "model_id": model_id,
        "performance": [
            {
                "date": r[0],
                "gini": r[1],
                "ks": r[2],
                "auroc": r[3],
                "psi": r[4],
                "ar_ratio": r[5],
                "alert": r[6] == 1
            }
            for r in reversed(results)
        ],
        "thresholds": {
            "gini": {"warning": 0.40, "critical": 0.35},
            "psi": {"warning": 0.10, "critical": 0.25},
            "ar_ratio": {"warning_low": 0.80, "warning_high": 1.20, "critical_low": 0.70, "critical_high": 1.30}
        }
    }


def get_model_type_specifications(model_type: str) -> dict:
    """모델 타입별 상세 사양 반환"""

    specs = {
        "PD": {
            "full_name": "Probability of Default Model",
            "korean_name": "부도확률 모델",
            "description": "차주의 향후 1년 내 부도 가능성을 확률로 추정하는 모델",
            "theoretical_background": """
## 이론적 배경

### Merton 구조모형 (Structural Model)
- 기업가치가 부채 이하로 하락할 때 부도 발생
- 옵션이론 기반: 주주지분 = Call Option on Firm Value
- V(t) < D(t) 일 때 부도 (V: 기업가치, D: 부채)

### 축약형 모형 (Reduced-Form Model)
- 부도를 외생적 점프 과정으로 모델링
- Hazard Rate (위험률) 기반 접근
- λ(t) = 순간적 부도 확률

### 통계적 접근
- Logistic Regression: P(D=1|X) = 1/(1 + exp(-βX))
- 판별분석 (Discriminant Analysis)
- 기계학습: Random Forest, XGBoost, Neural Network
            """,
            "formulas": {
                "logistic_regression": {
                    "name": "로지스틱 회귀",
                    "formula": "P(Default) = 1 / (1 + exp(-(β₀ + β₁X₁ + β₂X₂ + ... + βₙXₙ)))",
                    "description": "선형 결합의 결과를 0~1 사이 확률로 변환"
                },
                "merton_dd": {
                    "name": "Merton Distance to Default",
                    "formula": "DD = (ln(V/D) + (μ - σ²/2)T) / (σ√T)",
                    "description": "기업가치와 부채 간 거리를 표준화한 지표"
                },
                "hazard_rate": {
                    "name": "위험률 (Hazard Rate)",
                    "formula": "λ(t) = lim(Δt→0) P(t < T ≤ t+Δt | T > t) / Δt",
                    "description": "특정 시점까지 생존 시 순간적 부도 확률"
                },
                "pit_pd": {
                    "name": "Point-in-Time PD",
                    "formula": "PD_PIT = PD_TTC × Scalar(Macro)",
                    "description": "현재 경기 상황을 반영한 PD"
                },
                "ttc_pd": {
                    "name": "Through-the-Cycle PD",
                    "formula": "PD_TTC = Long-term Average DR by Grade",
                    "description": "경기 사이클을 평균화한 PD"
                }
            },
            "key_variables": [
                {"name": "재무비율", "examples": "부채비율, 이자보상배율, 유동비율, ROA"},
                {"name": "현금흐름", "examples": "영업현금흐름/총부채, FCF/이자비용"},
                {"name": "규모/업력", "examples": "총자산(log), 설립연수"},
                {"name": "정성요소", "examples": "경영진 평가, 업종 전망, 기술력"},
                {"name": "행동정보", "examples": "연체이력, 거래기간, 결제패턴"}
            ],
            "advantages": [
                "객관적이고 일관된 신용평가 가능",
                "대량 심사 효율화",
                "규제자본 계산의 핵심 입력값",
                "리스크 기반 가격결정(RBP) 가능"
            ],
            "disadvantages": [
                "과거 데이터에 의존 (후향적)",
                "급격한 환경변화 반영 지연",
                "저빈도 사건(Low Default Portfolio) 추정 어려움",
                "모델 리스크 존재"
            ],
            "limitations": [
                "경기 사이클 미반영 시 경기순응성 증가",
                "신규 업종/상품에 적용 한계",
                "정성적 요소의 계량화 어려움",
                "데이터 품질에 민감"
            ],
            "regulatory_requirements": {
                "basel": "IRB Approach: PD, LGD, EAD, M 추정 필요",
                "validation": "연 1회 이상 백테스트 및 검증 수행",
                "documentation": "모델 개발문서, 검증문서, 운영문서 구비"
            }
        },
        "LGD": {
            "full_name": "Loss Given Default Model",
            "korean_name": "부도시손실률 모델",
            "description": "부도 발생 시 예상 손실 비율을 추정하는 모델",
            "theoretical_background": """
## 이론적 배경

### Workout LGD
- 실제 부도 사례의 회수 데이터 기반
- LGD = 1 - Recovery Rate
- 회수기간의 시간가치(할인) 반영

### Market LGD
- 부도채권 시장가격 기반
- LGD = 1 - (부도 직후 채권가격 / 액면가)

### Implied LGD
- 정상 채권과 무위험 채권의 스프레드에서 역산
- Credit Spread = PD × LGD (단순화)
            """,
            "formulas": {
                "workout_lgd": {
                    "name": "Workout LGD",
                    "formula": "LGD = 1 - Σ(Rᵢ/(1+r)^tᵢ) / EAD",
                    "description": "회수금액의 현재가치를 EAD로 나눈 값의 보수"
                },
                "downturn_lgd": {
                    "name": "Downturn LGD",
                    "formula": "LGD_downturn = LGD_avg × Stress Factor",
                    "description": "경기 침체기의 손실률 (규제 요건)"
                },
                "collateral_haircut": {
                    "name": "담보 Haircut",
                    "formula": "Effective Collateral = Collateral Value × (1 - Haircut)",
                    "description": "담보가치 변동 및 처분비용 반영"
                }
            },
            "key_variables": [
                {"name": "담보유형", "examples": "부동산, 예적금, 유가증권, 매출채권"},
                {"name": "담보비율", "examples": "LTV (Loan-to-Value)"},
                {"name": "선순위/후순위", "examples": "근저당 순위, 채권 순위"},
                {"name": "부도유형", "examples": "도산, 연체, 채무조정"},
                {"name": "산업/경기", "examples": "업종별 회수율, 경기 국면"}
            ],
            "advantages": [
                "손실 예측의 정교화",
                "담보 가치 반영",
                "익스포저별 차별화된 리스크 측정"
            ],
            "disadvantages": [
                "부도 데이터 부족 (Low Default)",
                "회수기간 장기로 데이터 축적 오래 걸림",
                "Downturn LGD 추정의 어려움"
            ],
            "limitations": [
                "담보가치 평가의 주관성",
                "회수 비용 추정의 불확실성",
                "경기 침체기 데이터 부족"
            ],
            "regulatory_requirements": {
                "basel": "A-IRB에서 자체 추정 허용, F-IRB는 감독당국 제시값 사용",
                "downturn": "Downturn LGD 적용 의무",
                "floor": "규제 LGD Floor 존재"
            }
        },
        "EAD": {
            "full_name": "Exposure at Default Model",
            "korean_name": "부도시익스포저 모델",
            "description": "부도 시점의 예상 익스포저(노출금액)를 추정하는 모델",
            "theoretical_background": """
## 이론적 배경

### On-Balance Sheet EAD
- 현재 대출잔액이 기본
- 미상환 원금 + 미수이자

### Off-Balance Sheet EAD
- 미사용 한도의 부도 시 전환율 (CCF) 적용
- EAD = 사용액 + CCF × 미사용액

### LEQ (Loan Equivalent Factor)
- 미사용 한도 중 부도 전 추가 인출 비율
- 신용 악화 시 한도 소진 경향 반영
            """,
            "formulas": {
                "ead_formula": {
                    "name": "EAD 계산",
                    "formula": "EAD = Drawn + CCF × (Limit - Drawn)",
                    "description": "사용액 + 신용전환율 × 미사용액"
                },
                "ccf": {
                    "name": "신용전환율 (CCF)",
                    "formula": "CCF = (EAD - Drawn₀) / (Limit - Drawn₀)",
                    "description": "미사용 한도 중 부도 시점까지 인출된 비율"
                }
            },
            "key_variables": [
                {"name": "상품유형", "examples": "한도대출, 당좌대출, 보증"},
                {"name": "한도사용률", "examples": "현재 사용액/한도"},
                {"name": "거래기간", "examples": "한도 설정 후 경과기간"},
                {"name": "신용등급", "examples": "등급 하락 시 인출 증가 경향"}
            ],
            "advantages": [
                "한도성 상품의 리스크 정량화",
                "미사용 약정의 자본 반영"
            ],
            "disadvantages": [
                "CCF 추정 데이터 부족",
                "상품별 행태 차이 큼"
            ],
            "limitations": [
                "급격한 한도 인출 예측 한계",
                "Facility 간 상관관계 미반영"
            ],
            "regulatory_requirements": {
                "basel": "상품유형별 CCF 적용",
                "floor": "감독당국 제시 CCF Floor"
            }
        },
        "PRICING": {
            "full_name": "Risk-Based Pricing Model",
            "korean_name": "리스크 기반 가격결정 모델",
            "description": "차주의 신용리스크를 반영한 적정 금리를 산출하는 모델",
            "theoretical_background": """
## 이론적 배경

### RAROC 기반 가격결정
- Risk-Adjusted Return on Capital
- 리스크 조정 수익률이 허들레이트 이상이 되는 금리 산출

### EL Pricing
- Expected Loss를 금리에 반영
- Spread = PD × LGD (간략화)

### Economic Capital Approach
- 예상외손실(UL)에 대한 자본비용 반영
- 자본비용 = EC × 목표수익률
            """,
            "formulas": {
                "raroc": {
                    "name": "RAROC",
                    "formula": "RAROC = (수익 - 비용 - EL) / Economic Capital",
                    "description": "리스크 조정 자기자본이익률"
                },
                "spread": {
                    "name": "최소 스프레드",
                    "formula": "Spread = (FTP + OpEx + EL + Capital Cost) - Base Rate",
                    "description": "리스크와 비용을 커버하는 최소 마진"
                },
                "el": {
                    "name": "Expected Loss",
                    "formula": "EL = PD × LGD × EAD",
                    "description": "예상손실"
                }
            },
            "key_variables": [
                {"name": "PD/LGD/EAD", "examples": "리스크 파라미터"},
                {"name": "FTP", "examples": "자금조달비용 (Funds Transfer Price)"},
                {"name": "운영비용", "examples": "심사비용, 관리비용"},
                {"name": "자본비용", "examples": "EC × 목표 ROE"}
            ],
            "advantages": [
                "리스크-수익 균형",
                "수익성 기반 여신 의사결정",
                "포트폴리오 최적화 기반"
            ],
            "disadvantages": [
                "경쟁 금리와 괴리 가능",
                "영업 현장 활용 복잡",
                "입력 파라미터 민감도 높음"
            ],
            "limitations": [
                "관계 가치 미반영",
                "교차판매 효과 정량화 어려움"
            ],
            "regulatory_requirements": {
                "guideline": "리스크 기반 가격정책 권고",
                "disclosure": "금리 산정 근거 고객 설명 의무"
            }
        },
        "EWS": {
            "full_name": "Early Warning System",
            "korean_name": "조기경보시스템",
            "description": "여신 부실화를 사전에 감지하여 선제적 관리를 지원하는 시스템",
            "theoretical_background": """
## 이론적 배경

### 신호 이론 (Signal Theory)
- 부실 기업은 특정 패턴의 징후를 보임
- 재무악화, 결제지연, 시장정보 변화 등

### 판별 분석 (Discriminant Analysis)
- 정상/부실 그룹의 분류 기준 도출
- Z-score (Altman), ZETA 모형 등

### 생존 분석 (Survival Analysis)
- 시간 경과에 따른 부실 확률 추정
- Cox Proportional Hazards Model
            """,
            "formulas": {
                "z_score": {
                    "name": "Altman Z-Score",
                    "formula": "Z = 1.2X₁ + 1.4X₂ + 3.3X₃ + 0.6X₄ + 1.0X₅",
                    "description": "유동성, 수익성, 레버리지 등 복합 지표"
                },
                "hazard": {
                    "name": "Cox Hazard",
                    "formula": "h(t|X) = h₀(t) × exp(βX)",
                    "description": "공변량 기반 위험률 추정"
                },
                "signal_strength": {
                    "name": "신호 강도",
                    "formula": "Signal = Σ(wᵢ × Triggerᵢ)",
                    "description": "가중합 기반 종합 경보 수준"
                }
            },
            "key_variables": [
                {"name": "재무징후", "examples": "매출감소, 영업손실, 유동성 악화"},
                {"name": "행동징후", "examples": "연체, 한도소진, 결제패턴 변화"},
                {"name": "시장징후", "examples": "주가하락, 신용등급 하락, CDS 상승"},
                {"name": "비재무징후", "examples": "대표자 변경, 소송, 언론보도"}
            ],
            "advantages": [
                "선제적 리스크 관리 가능",
                "손실 최소화",
                "워크아웃 성공률 제고"
            ],
            "disadvantages": [
                "False Positive 관리 부담",
                "적시성과 정확성의 트레이드오프",
                "정보 수집 비용"
            ],
            "limitations": [
                "급격한 부실화 감지 한계",
                "외부 충격 예측 불가",
                "분식회계 탐지 어려움"
            ],
            "regulatory_requirements": {
                "guideline": "여신 건전성 사후관리 체계 구축 의무",
                "reporting": "부실징후 기업 보고"
            }
        }
    }

    return specs.get(model_type, {
        "full_name": model_type,
        "korean_name": model_type,
        "description": "상세 사양 정보 없음",
        "theoretical_background": "",
        "formulas": {},
        "key_variables": [],
        "advantages": [],
        "disadvantages": [],
        "limitations": [],
        "regulatory_requirements": {}
    })

