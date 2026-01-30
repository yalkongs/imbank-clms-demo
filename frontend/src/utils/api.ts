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
  getEfficiency: () => api.get('/capital/efficiency'),
};

// Portfolio API
export const portfolioApi = {
  getStrategyMatrix: () => api.get('/portfolio/strategy-matrix'),
  getConcentration: () => api.get('/portfolio/concentration'),
  getIndustryDetail: (code: string) => api.get(`/portfolio/industry/${code}`),
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
  getRwaOptimization: () => api.get('/capital-optimizer/rwa-optimization'),
  // 자본배분 최적화
  getAllocationOptimization: () => api.get('/capital-optimizer/allocation-optimizer'),
  // 동적 가격제안
  getPricingSuggestion: (applicationId: string, targetRaroc?: number) =>
    api.get(`/capital-optimizer/pricing-suggestion/${applicationId}`, {
      params: targetRaroc ? { target_raroc: targetRaroc } : undefined
    }),
  // 포트폴리오 리밸런싱 제안
  getRebalancingSuggestions: () => api.get('/capital-optimizer/rebalancing-suggestions'),
  // 효율성 대시보드
  getEfficiencyDashboard: () => api.get('/capital-optimizer/efficiency-dashboard'),
};

export default api;
