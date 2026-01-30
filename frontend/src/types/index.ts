// 공통 타입 정의

export interface Customer {
  customer_id: string;
  customer_name: string;
  business_no: string;
  industry_code: string;
  industry_name: string;
  company_size: string;
  employee_count: number;
  annual_revenue: number;
  established_date: string;
  relationship_start_date: string;
  relationship_manager: string;
}

export interface LoanApplication {
  application_id: string;
  customer_id: string;
  customer_name: string;
  application_date: string;
  requested_amount: number;
  product_type: string;
  purpose: string;
  term_months: number;
  collateral_type: string;
  collateral_value: number;
  status: string;
  priority: string;
  assigned_rm: string;
  industry_code: string;
  industry_name: string;
  company_size: string;
}

export interface CreditRating {
  rating_id: string;
  application_id: string;
  rating_date: string;
  financial_grade: string;
  non_financial_grade: string;
  final_grade: string;
  pd: number;
  pd_grade: string;
  lgd: number;
  lgd_grade: string;
  ead: number;
  model_version: string;
  analyst_id: string;
}

export interface RiskParameter {
  pd: number;
  lgd: number;
  ead: number;
  rwa: number;
  expected_loss: number;
  economic_capital: number;
}

export interface Pricing {
  base_rate: number;
  ftp_spread: number;
  credit_spread: number;
  strategy_adjustment: number;
  operation_cost: number;
  target_profit: number;
  final_rate: number;
  raroc: number;
}

export interface CapitalPosition {
  total_capital: number;
  tier1_capital: number;
  cet1_capital: number;
  total_rwa: number;
  credit_rwa: number;
  market_rwa: number;
  operational_rwa: number;
  bis_ratio: number;
  tier1_ratio: number;
  cet1_ratio: number;
  leverage_ratio: number;
}

export interface PortfolioStrategy {
  industry_code: string;
  industry_name: string;
  rating_grade: string;
  strategy_code: 'EXPAND' | 'SELECTIVE' | 'MAINTAIN' | 'REDUCE' | 'EXIT';
  target_exposure: number;
  current_exposure: number;
  target_raroc: number;
  max_single_exposure: number;
}

export interface LimitDefinition {
  limit_id: string;
  limit_name: string;
  limit_type: string;
  target_type: string;
  target_id: string;
  limit_amount: number;
  current_usage: number;
  utilization_rate: number;
  warning_threshold: number;
  critical_threshold: number;
  status: 'NORMAL' | 'WARNING' | 'CRITICAL' | 'BREACH';
}

export interface StressScenario {
  scenario_id: string;
  scenario_name: string;
  scenario_type: string;
  severity: string;
  pd_stress_factor: number;
  lgd_stress_factor: number;
  rwa_stress_factor: number;
  description: string;
}

export interface StressResult {
  scenario_id: string;
  scenario_name: string;
  base_rwa: number;
  stressed_rwa: number;
  rwa_increase: number;
  base_el: number;
  stressed_el: number;
  el_increase: number;
  capital_impact: number;
  bis_ratio_impact: number;
}

export interface Model {
  model_id: string;
  model_name: string;
  model_type: string;
  model_purpose: string;
  risk_tier: string;
  development_date: string;
  last_validation_date: string;
  next_validation_date: string;
  status: string;
  owner_dept: string;
}

export interface ModelPerformance {
  date: string;
  gini: number;
  ks: number;
  auroc: number;
  psi: number;
  ar_ratio: number;
  alert: boolean;
  alert_type?: string;
}

export interface DashboardSummary {
  capital: {
    bis_ratio: number;
    tier1_ratio: number;
    cet1_ratio: number;
    leverage_ratio: number;
    total_rwa: number;
  };
  portfolio: {
    total_exposure: number;
    total_customers: number;
    avg_rating: string;
    weighted_pd: number;
    weighted_lgd: number;
    avg_raroc: number;
  };
  applications: {
    pending_count: number;
    pending_amount: number;
    approved_today: number;
    rejected_today: number;
  };
  alerts: {
    capital_warnings: number;
    limit_breaches: number;
    model_alerts: number;
    ews_triggers: number;
  };
}

export interface EWSAlert {
  alert_id: string;
  customer_id: string;
  customer_name: string;
  alert_date: string;
  alert_type: string;
  severity: string;
  trigger_condition: string;
  current_value: number;
  threshold_value: number;
  status: string;
}

// API 응답 타입
export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}
