import React from 'react';
import { Suspense } from 'react';
import { PageLoader } from './components';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components';
const CapitalHub = React.lazy(() => import('./pages/CapitalHub'));
const PortfolioHub = React.lazy(() => import('./pages/PortfolioHub'));
const LimitsHub = React.lazy(() => import('./pages/LimitsHub'));
const InclusiveFinance = React.lazy(() => import('./pages/InclusiveFinance'));
const PFMonitoring = React.lazy(() => import('./pages/PFMonitoring'));
const PortfolioMap = React.lazy(() => import('./pages/PortfolioMap'));
const CreditCaseFile = React.lazy(() => import('./pages/CreditCaseFile'));
const RateReduction = React.lazy(() => import('./pages/RateReduction'));
const Governance = React.lazy(() => import('./pages/Governance'));
const ApprovalInbox = React.lazy(() => import('./pages/ApprovalInbox'));
import Dashboard from './pages/Dashboard';
const Applications = React.lazy(() => import('./pages/Applications'));
const Capital = React.lazy(() => import('./pages/Capital'));
const CapitalOptimizer = React.lazy(() => import('./pages/CapitalOptimizer'));
const Portfolio = React.lazy(() => import('./pages/Portfolio'));
const Limits = React.lazy(() => import('./pages/Limits'));
const StressTest = React.lazy(() => import('./pages/StressTest'));
const Models = React.lazy(() => import('./pages/Models'));
const Customers = React.lazy(() => import('./pages/Customers'));
const EWSAdvanced = React.lazy(() => import('./pages/EWSAdvanced'));
const DynamicLimits = React.lazy(() => import('./pages/DynamicLimits'));
const CustomerProfitability = React.lazy(() => import('./pages/CustomerProfitability'));
const CollateralMonitoring = React.lazy(() => import('./pages/CollateralMonitoring'));
const PortfolioOptimization = React.lazy(() => import('./pages/PortfolioOptimization'));
const Workout = React.lazy(() => import('./pages/Workout'));
const ESG = React.lazy(() => import('./pages/ESG'));
const ALM = React.lazy(() => import('./pages/ALM'));
const CustomerBrowser = React.lazy(() => import('./pages/CustomerBrowser'));
const Covenant = React.lazy(() => import('./pages/Covenant'));
const AssetClassification = React.lazy(() => import('./pages/AssetClassification'));
const Delinquency = React.lazy(() => import('./pages/Delinquency'));

function App() {
  return (
    <Suspense fallback={<PageLoader label="화면을 여는 중" />}>
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="applications" element={<Applications />} />
        <Route path="capital" element={<CapitalHub />} />
        {/* 구 경로 유지 - 통합된 탭으로 보낸다 */}
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
        <Route path="inclusive-finance" element={<InclusiveFinance />} />
        <Route path="pf-monitoring" element={<PFMonitoring />} />
        <Route path="portfolio-map" element={<PortfolioMap />} />
        <Route path="governance" element={<Governance />} />
        <Route path="approval-inbox" element={<ApprovalInbox />} />
        <Route path="credit-case/:applicationId" element={<CreditCaseFile />} />
        <Route path="rate-reduction" element={<RateReduction />} />
        {/* Phase 2: 부실 관리 핵심 */}
        <Route path="asset-classification" element={<AssetClassification />} />
        <Route path="delinquency" element={<Delinquency />} />
      </Route>
    </Routes>
    </Suspense>
  );
}

export default App;
