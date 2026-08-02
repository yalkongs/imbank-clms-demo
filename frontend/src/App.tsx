import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components';
import CapitalHub from './pages/CapitalHub';
import PortfolioHub from './pages/PortfolioHub';
import LimitsHub from './pages/LimitsHub';
import {
  Dashboard,
  Applications,
  Capital,
  CapitalOptimizer,
  Portfolio,
  Limits,
  StressTest,
  Models,
  Customers,
  EWSAdvanced,
  DynamicLimits,
  CustomerProfitability,
  CollateralMonitoring,
  PortfolioOptimization,
  Workout,
  ESG,
  ALM,
  CustomerBrowser,
  Covenant,
  AssetClassification,
  Delinquency
} from './pages';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="applications" element={<Applications />} />
        <Route path="capital" element={<CapitalHub />} />
        {/* 구 경로 유지 — 통합된 탭으로 보낸다 */}
        <Route path="capital-optimizer" element={<Navigate to="/capital?tab=optimizer" replace />} />
        <Route path="portfolio" element={<PortfolioHub />} />
        <Route path="limits" element={<LimitsHub />} />
        <Route path="stress-test" element={<StressTest />} />
        <Route path="models" element={<Models />} />
        <Route path="customers" element={<Customers />} />
        {/* 신규 기능 라우트 */}
        <Route path="ews-advanced" element={<EWSAdvanced />} />
        <Route path="dynamic-limits" element={<Navigate to="/limits?tab=dynamic" replace />} />
        <Route path="customer-profitability" element={<CustomerProfitability />} />
        <Route path="collateral-monitoring" element={<CollateralMonitoring />} />
        <Route path="portfolio-optimization" element={<Navigate to="/portfolio?tab=optimizer" replace />} />
        <Route path="workout" element={<Workout />} />
        <Route path="esg" element={<ESG />} />
        <Route path="alm" element={<ALM />} />
        <Route path="customer-browser" element={<CustomerBrowser />} />
        {/* Phase 1: 여신 심사 고도화 */}
        <Route path="covenant" element={<Covenant />} />
        {/* Phase 2: 부실 관리 핵심 */}
        <Route path="asset-classification" element={<AssetClassification />} />
        <Route path="delinquency" element={<Delinquency />} />
      </Route>
    </Routes>
  );
}

export default App;
