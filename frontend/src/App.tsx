import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Layout } from './components';
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
  CustomerBrowser
} from './pages';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="applications" element={<Applications />} />
        <Route path="capital" element={<Capital />} />
        <Route path="capital-optimizer" element={<CapitalOptimizer />} />
        <Route path="portfolio" element={<Portfolio />} />
        <Route path="limits" element={<Limits />} />
        <Route path="stress-test" element={<StressTest />} />
        <Route path="models" element={<Models />} />
        <Route path="customers" element={<Customers />} />
        {/* 신규 기능 라우트 */}
        <Route path="ews-advanced" element={<EWSAdvanced />} />
        <Route path="dynamic-limits" element={<DynamicLimits />} />
        <Route path="customer-profitability" element={<CustomerProfitability />} />
        <Route path="collateral-monitoring" element={<CollateralMonitoring />} />
        <Route path="portfolio-optimization" element={<PortfolioOptimization />} />
        <Route path="workout" element={<Workout />} />
        <Route path="esg" element={<ESG />} />
        <Route path="alm" element={<ALM />} />
        <Route path="customer-browser" element={<CustomerBrowser />} />
      </Route>
    </Routes>
  );
}

export default App;
