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
  Customers
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
      </Route>
    </Routes>
  );
}

export default App;
