import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * 콜드스타트·배포 재시작 순단 내성
 * ----------------------------------
 * Render 재시작 직후에는 일부 API 가 일시적으로 실패(네트워크 오류·5xx)한다.
 * 화면들이 실패를 조용히 0 으로 그리지 않도록, 전송 계층에서 GET 요청을
 * 지수 백오프(1s → 2.5s → 5s)로 최대 3회 재시도한다.
 * 전역 axios 와 api 인스턴스 모두에 적용 (일부 화면은 전역 axios 를 직접 쓴다).
 */
const RETRYABLE_STATUS = new Set([502, 503, 504]);
const BACKOFF_MS = [1000, 2500, 5000];

function attachRetry(instance: { interceptors: any; request: (cfg: any) => Promise<any> }) {
  instance.interceptors.response.use(undefined, async (error: any) => {
    const cfg = error?.config || {};
    const isGet = (cfg.method || 'get').toLowerCase() === 'get';
    const retryable =
      !error?.response || RETRYABLE_STATUS.has(error.response.status) || error?.code === 'ECONNABORTED';
    cfg.__retryCount = cfg.__retryCount || 0;
    if (!isGet || !retryable || cfg.__retryCount >= BACKOFF_MS.length) throw error;
    const delay = BACKOFF_MS[cfg.__retryCount];
    cfg.__retryCount += 1;
    await new Promise(r => setTimeout(r, delay));
    return instance.request(cfg);
  });
}
attachRetry(axios);
attachRetry(api);

// 요청 인터셉터
api.interceptors.request.use(
  (config) => {
    // 토큰 등 인증 정보 추가 가능
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

// Dashboard API
export const dashboardApi = {
  getSummary: (region?: string) => api.get('/dashboard/summary', { params: region ? { region } : undefined }),
  getEWSAlerts: (region?: string) => api.get('/dashboard/ews-alerts', { params: region ? { region } : undefined }),
  getKPIs: (region?: string) => api.get('/dashboard/kpis', { params: region ? { region } : undefined }),
  getCapitalTrend: () => api.get('/dashboard/capital-trend'),
  getPortfolioDistribution: (region?: string) => api.get('/dashboard/portfolio-distribution', { params: region ? { region } : undefined }),
};

// Applications API
export const applicationsApi = {
  getAll: (params?: { status?: string; stage?: string; priority?: string; region?: string; limit?: number }) =>
    api.get('/applications', { params }),
  getPending: () => api.get('/applications/pending'),
  getSummary: (region?: string) => api.get('/applications/summary', { params: region ? { region } : undefined }),
  getById: (id: string) => api.get(`/applications/${id}`),
  simulate: (id: string, params?: { amount?: number; rate?: number; tenor?: number }) =>
    api.get(`/applications/${id}/simulate`, { params }),
  updateStage: (id: string, stage: string, comments?: string) =>
    api.post(`/applications/${id}/stage`, null, { params: { new_stage: stage, comments } }),
  approve: (
    id: string,
    decision: string,
    data?: {
      approval_level?: string;
      approver_name?: string;
      conditions?: string;
      comments?: string;
      approved_amount?: number;
      approved_rate?: number;
      approved_tenor?: number;
    }
  ) => api.post(`/applications/${id}/approve`, null, {
    params: { decision, ...data }
  }),
};

// Capital API
export const capitalApi = {
  getPosition: () => api.get('/capital/position'),
  getTrend: (months?: number) => api.get('/capital/trend', { params: { months } }),
  getBudget: () => api.get('/capital/budget'),
  simulate: (data: any) => api.get('/capital/simulate', { params: { new_exposure: data.amount, pd: data.pd, lgd: data.lgd } }),
  getEfficiency: (region?: string) => api.get('/capital/efficiency', { params: region ? { region } : undefined }),
};

// Portfolio API
export const portfolioApi = {
  getStrategyMatrix: (region?: string) => api.get('/portfolio/strategy-matrix', { params: region ? { region } : undefined }),
  getConcentration: (region?: string) => api.get('/portfolio/concentration', { params: region ? { region } : undefined }),
  getIndustryDetail: (code: string, region?: string) => api.get(`/portfolio/industry/${code}`, { params: region ? { region } : undefined }),
  getIndustryRegionAnalysis: () => api.get('/portfolio/industry-region-analysis'),
};

// Limits API
export const limitsApi = {
  getAll: () => api.get('/limits'),
  check: (params: { customer_id: string; amount: number; industry_code?: string }) =>
    api.get('/limits/check', { params }),
  getIndustry: () => api.get('/limits/industry'),
  getCustomers: () => api.get('/limits/customers'),
};

// Stress Test API
export const stressTestApi = {
  getScenarios: () => api.get('/stress-test/scenarios'),
  getResults: (scenarioId: string) => api.get(`/stress-test/results/${scenarioId}`),
  run: (scenarioId: string, data: any) => api.post(`/stress-test/run`, null, { params: { scenario_id: scenarioId, ...data } }),
};

// Models API
export const modelsApi = {
  getAll: () => api.get('/models'),
  getById: (id: string) => api.get(`/models/${id}`),
  getPerformance: (id: string, months?: number) => api.get(`/models/${id}/performance`, { params: { months } }),
  getStatus: () => api.get('/models/summary/status'),
  getOverrides: () => api.get('/models/overrides'),
  getChampionChallenger: () => api.get('/models/champion-challenger'),
  // Backtest APIs
  getBacktestSummary: () => api.get('/models/backtest/summary'),
  getModelBacktest: (modelId: string) => api.get(`/models/backtest/${modelId}`),
  // Override Performance APIs
  getOverridePerformance: () => api.get('/models/override-performance'),
  // Vintage Analysis APIs
  getVintageAnalysis: (cohortType?: string) => api.get('/models/vintage-analysis', { params: cohortType ? { cohort_type: cohortType } : undefined }),
  getVintageDetail: (vintageMonth: string) => api.get(`/models/vintage-analysis/${vintageMonth}`),
  // Model Specifications
  getModelSpecifications: (modelId: string) => api.get(`/models/specifications/${modelId}`),
};

// Customers API
export const customersApi = {
  getAll: (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    industry_code?: string;
    size_category?: string;
    region?: string;
    sort_by?: string;
    sort_order?: string;
  }) => api.get('/customers', { params }),
  getById: (id: string) => api.get(`/customers/${id}`),
  getSummary: (region?: string) => api.get('/customers/summary', { params: region ? { region } : undefined }),
  getIndustries: () => api.get('/customers/industries'),
};

// Capital Optimizer API (자본활용성 최적화)
export const capitalOptimizerApi = {
  // RWA 최적화 분석
  getRwaOptimization: (region?: string) => api.get('/capital-optimizer/rwa-optimization', { params: region ? { region } : undefined }),
  // 자본배분 최적화
  getAllocationOptimization: (region?: string) => api.get('/capital-optimizer/allocation-optimizer', { params: region ? { region } : undefined }),
  // 동적 가격제안
  getPricingSuggestion: (applicationId: string, targetRaroc?: number) =>
    api.get(`/capital-optimizer/pricing-suggestion/${applicationId}`, {
      params: targetRaroc ? { target_raroc: targetRaroc } : undefined
    }),
  // 포트폴리오 리밸런싱 제안
  getRebalancingSuggestions: (region?: string) => api.get('/capital-optimizer/rebalancing-suggestions', { params: region ? { region } : undefined }),
  // 효율성 대시보드
  getEfficiencyDashboard: (region?: string) => api.get('/capital-optimizer/efficiency-dashboard', { params: region ? { region } : undefined }),
};

// EWS Advanced API (조기경보 고도화)
export const ewsAdvancedApi = {
  getFeatureDescription: (featureId: string) => api.get(`/ews-advanced/feature-description/${featureId}`),
  getIndicators: () => api.get('/ews-advanced/indicators'),
  getIndicatorValues: (customerId: string, months?: number) =>
    api.get(`/ews-advanced/indicator-values/${customerId}`, { params: months ? { months } : undefined }),
  getSupplyChain: (customerId: string) => api.get(`/ews-advanced/supply-chain/${customerId}`),
  getExternalSignals: (params?: { signal_type?: string; region?: string }) =>
    api.get('/ews-advanced/external-signals', { params }),
  getCompositeScores: (params?: { min_score?: number; limit?: number; region?: string }) =>
    api.get('/ews-advanced/composite-scores', { params }),
  getDashboard: (region?: string) => api.get('/ews-advanced/dashboard', { params: region ? { region } : undefined }),
  // 거래행태
  getTransactionDashboard: (region?: string) => api.get('/ews-advanced/transaction-behavior/dashboard', { params: region ? { region } : undefined }),
  getTransactionCustomer: (customerId: string) => api.get(`/ews-advanced/transaction-behavior/${customerId}`),
  getTransactionAnomalies: (region?: string) => api.get('/ews-advanced/transaction-behavior/anomalies', { params: region ? { region } : undefined }),
  // 공적정보
  getPublicRegistryDashboard: (region?: string) => api.get('/ews-advanced/public-registry/dashboard', { params: region ? { region } : undefined }),
  getPublicRegistryCustomers: (region?: string) => api.get('/ews-advanced/public-registry/customers', { params: region ? { region } : undefined }),
  getPublicRegistryCustomer: (customerId: string) => api.get(`/ews-advanced/public-registry/${customerId}`),
  getPublicRegistryTimeline: (region?: string) => api.get('/ews-advanced/public-registry/timeline', { params: region ? { region } : undefined }),
  // 시장신호
  getMarketDashboard: (region?: string) => api.get('/ews-advanced/market-signals/dashboard', { params: region ? { region } : undefined }),
  getMarketCustomer: (customerId: string) => api.get(`/ews-advanced/market-signals/${customerId}`),
  getMarketAlerts: (region?: string) => api.get('/ews-advanced/market-signals/alerts', { params: region ? { region } : undefined }),
  // 뉴스감성
  getNewsDashboard: (region?: string) => api.get('/ews-advanced/news-sentiment/dashboard', { params: region ? { region } : undefined }),
  getNewsCustomer: (customerId: string) => api.get(`/ews-advanced/news-sentiment/${customerId}`),
  getNewsFeed: (params?: { region?: string; sentiment?: string }) => api.get('/ews-advanced/news-sentiment/feed', { params }),
  // 공급망
  getSupplyChainDashboard: (region?: string) => api.get('/ews-advanced/supply-chain/dashboard', { params: region ? { region } : undefined }),
  getSupplyChainCustomers: (region?: string) => api.get('/ews-advanced/supply-chain/customers', { params: region ? { region } : undefined }),
  getSupplyChainTemporal: (customerId: string) => api.get(`/ews-advanced/supply-chain/${customerId}/temporal`),
  // 통합
  getIntegratedDashboard: (region?: string) => api.get('/ews-advanced/integrated-dashboard', { params: region ? { region } : undefined }),
};

// Dynamic Limits API (동적 한도관리)
export const dynamicLimitsApi = {
  getFeatureDescription: (featureId: string) => api.get(`/dynamic-limits/feature-description/${featureId}`),
  getEconomicCycle: () => api.get('/dynamic-limits/economic-cycle'),
  getRules: (ruleType?: string) =>
    api.get('/dynamic-limits/rules', { params: ruleType ? { rule_type: ruleType } : undefined }),
  getAdjustments: (params?: { industry_code?: string; months?: number }) =>
    api.get('/dynamic-limits/adjustments', { params }),
  getCurrentStatus: () => api.get('/dynamic-limits/current-status'),
  simulate: (params: { gdp_growth_shock?: number; interest_rate_shock?: number }) =>
    api.get('/dynamic-limits/simulate-shock', { params }),
};

// Customer Profitability API (고객 수익성 분석)
export const customerProfitabilityApi = {
  getFeatureDescription: (featureId: string) => api.get(`/customer-profitability/feature-description/${featureId}`),
  getRankings: (params?: { sort_by?: string; limit?: number; region?: string }) =>
    api.get('/customer-profitability/rankings', { params }),
  getCustomer: (customerId: string) => api.get(`/customer-profitability/customer/${customerId}`),
  getCrossSellOpportunities: (params?: { status?: string; min_probability?: number; region?: string }) =>
    api.get('/customer-profitability/cross-sell-opportunities', { params }),
  getChurnRisk: (params?: { min_risk?: number; region?: string }) =>
    api.get('/customer-profitability/churn-risk', { params }),
  getDashboard: (region?: string) => api.get('/customer-profitability/dashboard', { params: region ? { region } : undefined }),
};

// Collateral Monitoring API (담보 모니터링)
export const collateralMonitoringApi = {
  getFeatureDescription: (featureId: string) => api.get(`/collateral-monitoring/feature-description/${featureId}`),
  getRealEstateIndex: (region?: string) =>
    api.get('/collateral-monitoring/real-estate-index', { params: region ? { region } : undefined }),
  getValuationHistory: (collateralId: string, months?: number) =>
    api.get(`/collateral-monitoring/valuation-history/${collateralId}`, { params: months ? { months } : undefined }),
  getAlerts: (params?: { alert_type?: string; status?: string; region?: string }) =>
    api.get('/collateral-monitoring/alerts', { params }),
  getLtvAnalysis: (region?: string) => api.get('/collateral-monitoring/ltv-analysis', { params: region ? { region } : undefined }),
  getDashboard: (region?: string) => api.get('/collateral-monitoring/dashboard', { params: region ? { region } : undefined }),
  getCustomers: (params?: {
    search?: string; collateral_type?: string; region?: string;
    sort_by?: string; sort_order?: string; page?: number; page_size?: number;
  }) => api.get('/collateral-monitoring/customers', { params }),
  getCustomerDetail: (customerId: string) => api.get(`/collateral-monitoring/customer/${customerId}`),
};

// Portfolio Optimization API (포트폴리오 최적화)
export const portfolioOptimizationApi = {
  getFeatureDescription: (featureId: string) => api.get(`/portfolio-optimization/feature-description/${featureId}`),
  getOptimizationRuns: () => api.get('/portfolio-optimization/optimization-runs'),
  getOptimizationResult: (runId: string) => api.get(`/portfolio-optimization/optimization-result/${runId}`),
  getLatestRecommendations: (region?: string) => api.get('/portfolio-optimization/latest-recommendations', { params: region ? { region } : undefined }),
  getCurrentVsOptimal: (region?: string) => api.get('/portfolio-optimization/current-vs-optimal', { params: region ? { region } : undefined }),
  getConstraints: () => api.get('/portfolio-optimization/constraints'),
  getDashboard: () => api.get('/portfolio-optimization/dashboard'),
};

// Workout API (Workout 관리)
export const workoutApi = {
  getFeatureDescription: (featureId: string) => api.get(`/workout/feature-description/${featureId}`),
  getCases: (params?: { status?: string; priority?: string; region?: string }) =>
    api.get('/workout/cases', { params }),
  getCase: (caseId: string) => api.get(`/workout/case/${caseId}`),
  getScenarios: (caseId: string) => api.get(`/workout/scenarios/${caseId}`),
  getRestructuringHistory: (customerId?: string) =>
    api.get('/workout/restructuring-history', { params: customerId ? { customer_id: customerId } : undefined }),
  getDashboard: (region?: string) => api.get('/workout/dashboard', { params: region ? { region } : undefined }),
};

// ESG API (ESG 리스크 관리)
export const esgApi = {
  getFeatureDescription: (featureId: string) => api.get(`/esg/feature-description/${featureId}`),
  getAssessments: (params?: { min_score?: number; limit?: number; region?: string }) =>
    api.get('/esg/assessments', { params }),
  getAssessment: (customerId: string) => api.get(`/esg/assessment/${customerId}`),
  getGreenFinance: (productType?: string) =>
    api.get('/esg/green-finance', { params: productType ? { product_type: productType } : undefined }),
  getGradeDistribution: (region?: string) => api.get('/esg/grade-distribution', { params: region ? { region } : undefined }),
  getDashboard: (region?: string) => api.get('/esg/dashboard', { params: region ? { region } : undefined }),
};

// ALM API (금리 리스크 관리)
export const almApi = {
  getFeatureDescription: (featureId: string) => api.get(`/alm/feature-description/${featureId}`),
  getGapAnalysis: () => api.get('/alm/gap-analysis'),
  getScenarios: () => api.get('/alm/scenarios'),
  getScenarioResults: (scenarioId?: string) =>
    api.get('/alm/scenario-results', { params: scenarioId ? { scenario_id: scenarioId } : undefined }),
  getHedgePositions: (params?: { instrument_type?: string; status?: string }) =>
    api.get('/alm/hedge-positions', { params }),
  getHedgeRecommendations: (status?: string) =>
    api.get('/alm/hedge-recommendations', { params: status ? { status } : undefined }),
  getDashboard: () => api.get('/alm/dashboard'),
};

// ============================================================
// Phase 1: 여신 심사 고도화 API
// ============================================================

// Financial Analysis API (재무제표 분석)
export const financialApi = {
  getRatios: (customerId: string) =>
    api.get(`/financial/ratios/${customerId}`),
  getTrend: (customerId: string) =>
    api.get(`/financial/trend/${customerId}`),
  getPeerComparison: (customerId: string) =>
    api.get(`/financial/peer-comparison/${customerId}`),
  getSummaryForApplication: (applicationId: string) =>
    api.get(`/financial/summary/${applicationId}`),
  upsertStatement: (customerId: string, params: {
    fiscal_year: number;
    revenue?: number;
    operating_profit?: number;
    ebitda?: number;
    interest_expense?: number;
    net_profit?: number;
    total_assets?: number;
    current_assets?: number;
    total_debt?: number;
    current_debt?: number;
    total_borrowing?: number;
    equity?: number;
    retained_earning?: number;
    working_capital?: number;
    operating_cf?: number;
    audited?: number;
    source?: string;
  }) => api.post(`/financial/statement/${customerId}`, null, { params }),
};

// Group Credit API (그룹여신 통합심사)
export const groupCreditApi = {
  getGroup: (groupId: string) =>
    api.get(`/group-credit/group/${groupId}`),
  getCustomerGroup: (customerId: string) =>
    api.get(`/group-credit/customer/${customerId}`),
  checkGroupLimit: (groupId: string, newAmount?: number) =>
    api.get(`/group-credit/limit-check/${groupId}`, { params: newAmount ? { new_amount: newAmount } : undefined }),
  getConcentration: (region?: string) =>
    api.get('/group-credit/concentration', { params: region ? { region } : undefined }),
  getGuaranteeNetwork: (groupId: string) =>
    api.get(`/group-credit/guarantee-network/${groupId}`),
  simulateGroupLimit: (applicationId: string) =>
    api.post(`/group-credit/simulate/${applicationId}`),
};

// Covenant API (코베넌트 관리)
export const covenantApi = {
  getByFacility: (facilityId: string) =>
    api.get(`/covenants/facility/${facilityId}`),
  getDueCheck: (daysAhead?: number, region?: string) =>
    api.get('/covenants/due-check', { params: { days_ahead: daysAhead, region } }),
  runCheck: (covenantId: string, params?: { actual_value?: number; checked_by?: string; notes?: string }) =>
    api.post(`/covenants/check/${covenantId}`, null, { params }),
  getBreachStatus: (region?: string) =>
    api.get('/covenants/breach-status', { params: region ? { region } : undefined }),
  getHistory: (covenantId: string) =>
    api.get(`/covenants/history/${covenantId}`),
  applyWaiver: (covenantId: string, params: { reason: string; approved_by: string; waiver_period_days?: number }) =>
    api.post(`/covenants/waiver/${covenantId}`, null, { params }),
};

// ============================================================
// Phase 2: 부실 관리 핵심
// ============================================================

export const assetClassificationApi = {
  getPortfolio: (baseDate?: string) =>
    api.get('/classification/portfolio', { params: baseDate ? { base_date: baseDate } : undefined }),
  getFacilityHistory: (facilityId: string, limit?: number) =>
    api.get(`/classification/facility/${facilityId}`, { params: limit ? { limit } : undefined }),
  getCustomer: (customerId: string) =>
    api.get(`/classification/customer/${customerId}`),
  runClassification: (baseDate?: string) =>
    api.post('/classification/run', null, { params: baseDate ? { base_date: baseDate } : undefined }),
  getMigrationMatrix: (fromDate?: string, toDate?: string) =>
    api.get('/classification/migration-matrix', { params: { from_date: fromDate, to_date: toDate } }),
  getProvisionGap: () =>
    api.get('/classification/provision-gap'),
  getTrend: (months?: number) =>
    api.get('/classification/trend', { params: months ? { months } : undefined }),
};

export const eclApi = {
  getPortfolioSummary: (calcDate?: string) =>
    api.get('/ecl/portfolio-summary', { params: calcDate ? { calc_date: calcDate } : undefined }),
  getFacility: (facilityId: string, limit?: number) =>
    api.get(`/ecl/facility/${facilityId}`, { params: limit ? { limit } : undefined }),
  getStageMigration: () =>
    api.get('/ecl/stage-migration'),
  getProvisionAdequacy: () =>
    api.get('/ecl/provision-adequacy'),
  calculate: (facilityId: string, calcDate?: string) =>
    api.post(`/ecl/calculate/${facilityId}`, null, { params: calcDate ? { calc_date: calcDate } : undefined }),
  getTrend: (quarters?: number) =>
    api.get('/ecl/trend', { params: quarters ? { quarters } : undefined }),
  getMacroSensitivity: (facilityId?: string) =>
    api.get('/ecl/macro-sensitivity', { params: facilityId ? { facility_id: facilityId } : undefined }),
};

export const delinquencyApi = {
  getDashboard: () =>
    api.get('/delinquency/dashboard'),
  getActive: (stage?: string, limit?: number, offset?: number) =>
    api.get('/delinquency/active', { params: { stage, limit, offset } }),
  getFacility: (facilityId: string) =>
    api.get(`/delinquency/facility/${facilityId}`),
  getRollRate: (months?: number) =>
    api.get('/delinquency/roll-rate', { params: months ? { months } : undefined }),
  getVintage: () =>
    api.get('/delinquency/vintage-delinquency'),
  recordActivity: (params: {
    delinquency_id: string;
    facility_id: string;
    activity_type: string;
    contact_result?: string;
    promised_date?: string;
    promised_amount?: number;
    notes?: string;
    officer?: string;
  }) => api.post('/delinquency/collection-activity', null, { params }),
  getCollectionPerformance: (months?: number) =>
    api.get('/delinquency/collection-performance', { params: months ? { months } : undefined }),
};

export const workoutEclApi = {
  getEclSummary: () =>
    api.get('/workout/ecl-summary'),
  autoTransferNpl: (dpdThreshold?: number) =>
    api.post('/workout/auto-transfer-npl', null, { params: dpdThreshold ? { dpd_threshold: dpdThreshold } : undefined }),
};

// ============================================================
// Phase 3: 자동화 브릿지 / LGD 백테스트
// ============================================================

export const automationApi = {
  getDashboard: () =>
    api.get('/automation/dashboard'),
  getPending: (priority?: string, triggerType?: string, limit?: number) =>
    api.get('/automation/pending', { params: { priority, trigger_type: triggerType, limit } }),
  executeAction: (actionId: string) =>
    api.post(`/automation/execute/${actionId}`),
  scan: () =>
    api.post('/automation/trigger/scan'),
  getDefaultProbability: (customerId: string) =>
    api.get(`/automation/default-probability/${customerId}`),
  getStatistics: (days?: number) =>
    api.get('/automation/statistics', { params: days ? { days } : undefined }),
};

export const lgdBacktestApi = {
  getOverall: () =>
    api.get('/models/lgd-backtest'),
  getByCollateral: () =>
    api.get('/models/lgd-backtest/collateral'),
  getByIndustry: () =>
    api.get('/models/lgd-backtest/industry'),
  getRecoveryAnalytics: () =>
    api.get('/models/recovery-analytics'),
  getRecoveryTimeline: () =>
    api.get('/models/recovery-timeline'),
};

export default api;

/**
 * 네트워크 활동 신호 - 상단 진행 표시줄용
 * 전역 axios·api 인스턴스의 진행 중 요청 수를 구독할 수 있게 한다.
 */
type NetListener = (pending: number) => void;
const netListeners = new Set<NetListener>();
let pendingCount = 0;

export function onNetActivity(fn: NetListener): () => void {
  netListeners.add(fn);
  fn(pendingCount);
  return () => netListeners.delete(fn);
}

function bump(delta: number) {
  pendingCount = Math.max(0, pendingCount + delta);
  netListeners.forEach(fn => fn(pendingCount));
}

function attachActivity(instance: { interceptors: any }) {
  instance.interceptors.request.use((cfg: any) => { bump(1); return cfg; });
  instance.interceptors.response.use(
    (res: any) => { bump(-1); return res; },
    (err: any) => { bump(-1); throw err; }
  );
}
attachActivity(axios);
attachActivity(api);
