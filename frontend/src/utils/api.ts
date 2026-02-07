import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

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
  getSummary: () => api.get('/dashboard/summary'),
  getEWSAlerts: () => api.get('/dashboard/ews-alerts'),
  getKPIs: () => api.get('/dashboard/kpis'),
};

// Applications API
export const applicationsApi = {
  getAll: (params?: { status?: string; stage?: string; priority?: string; limit?: number }) =>
    api.get('/applications', { params }),
  getPending: () => api.get('/applications/pending'),
  getSummary: () => api.get('/applications/summary'),
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
    sort_by?: string;
    sort_order?: string;
  }) => api.get('/customers', { params }),
  getById: (id: string) => api.get(`/customers/${id}`),
  getSummary: () => api.get('/customers/summary'),
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
  getExternalSignals: (signalType?: string) =>
    api.get('/ews-advanced/external-signals', { params: signalType ? { signal_type: signalType } : undefined }),
  getCompositeScores: (params?: { min_score?: number; limit?: number }) =>
    api.get('/ews-advanced/composite-scores', { params }),
  getDashboard: () => api.get('/ews-advanced/dashboard'),
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
  getRankings: (params?: { sort_by?: string; limit?: number }) =>
    api.get('/customer-profitability/rankings', { params }),
  getCustomer: (customerId: string) => api.get(`/customer-profitability/customer/${customerId}`),
  getCrossSellOpportunities: (params?: { status?: string; min_probability?: number }) =>
    api.get('/customer-profitability/cross-sell-opportunities', { params }),
  getChurnRisk: (minRisk?: number) =>
    api.get('/customer-profitability/churn-risk', { params: minRisk ? { min_risk: minRisk } : undefined }),
  getDashboard: () => api.get('/customer-profitability/dashboard'),
};

// Collateral Monitoring API (담보 모니터링)
export const collateralMonitoringApi = {
  getFeatureDescription: (featureId: string) => api.get(`/collateral-monitoring/feature-description/${featureId}`),
  getRealEstateIndex: (region?: string) =>
    api.get('/collateral-monitoring/real-estate-index', { params: region ? { region } : undefined }),
  getValuationHistory: (collateralId: string, months?: number) =>
    api.get(`/collateral-monitoring/valuation-history/${collateralId}`, { params: months ? { months } : undefined }),
  getAlerts: (params?: { alert_type?: string; status?: string }) =>
    api.get('/collateral-monitoring/alerts', { params }),
  getLtvAnalysis: () => api.get('/collateral-monitoring/ltv-analysis'),
  getDashboard: () => api.get('/collateral-monitoring/dashboard'),
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
  getCases: (params?: { status?: string; priority?: string }) =>
    api.get('/workout/cases', { params }),
  getCase: (caseId: string) => api.get(`/workout/case/${caseId}`),
  getScenarios: (caseId: string) => api.get(`/workout/scenarios/${caseId}`),
  getRestructuringHistory: (customerId?: string) =>
    api.get('/workout/restructuring-history', { params: customerId ? { customer_id: customerId } : undefined }),
  getDashboard: () => api.get('/workout/dashboard'),
};

// ESG API (ESG 리스크 관리)
export const esgApi = {
  getFeatureDescription: (featureId: string) => api.get(`/esg/feature-description/${featureId}`),
  getAssessments: (params?: { min_score?: number; limit?: number }) =>
    api.get('/esg/assessments', { params }),
  getAssessment: (customerId: string) => api.get(`/esg/assessment/${customerId}`),
  getGreenFinance: (productType?: string) =>
    api.get('/esg/green-finance', { params: productType ? { product_type: productType } : undefined }),
  getGradeDistribution: () => api.get('/esg/grade-distribution'),
  getDashboard: () => api.get('/esg/dashboard'),
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

export default api;
