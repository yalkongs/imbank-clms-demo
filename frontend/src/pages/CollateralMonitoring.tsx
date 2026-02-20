import React, { useEffect, useState, useCallback } from 'react';
import {
  Home,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Building,
  BarChart3,
  MapPin,
  Search,
  Users,
  Shield,
  ChevronLeft,
  ChevronRight,
  X,
  Eye
} from 'lucide-react';
import { Card, StatCard, TrendChart, GroupedBarChart, DonutChart, COLORS, FeatureModal, HelpButton, RegionFilter } from '../components';
import { collateralMonitoringApi } from '../utils/api';
import { formatAmount, formatPercent } from '../utils/format';

const COLLATERAL_TYPE_LABELS: Record<string, string> = {
  REAL_ESTATE: '부동산',
  DEPOSIT: '예금',
  SECURITIES: '유가증권',
  MOVABLE_PROPERTY: '동산',
  GUARANTEE: '보증',
  RECEIVABLES: '매출채권',
  IP_RIGHTS: '지식재산권',
};

const REGION_LABELS: Record<string, string> = {
  CAPITAL: '수도권',
  DAEGU_GB: '대구경북',
  BUSAN_GN: '부산경남',
};

const SIZE_LABELS: Record<string, string> = {
  LARGE: '대기업',
  MEDIUM: '중견기업',
  SMALL: '중소기업',
  SOHO: 'SOHO',
};

export default function CollateralMonitoring() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'customers'>('dashboard');
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>(null);
  const [realEstateIndex, setRealEstateIndex] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [ltvAnalysis, setLtvAnalysis] = useState<any>(null);
  const [region, setRegion] = useState<string>('');
  const [chartRegion, setChartRegion] = useState<string>('');
  const [modalOpen, setModalOpen] = useState(false);
  const [featureInfo, setFeatureInfo] = useState<any>(null);

  // Customer tab state
  const [custLoading, setCustLoading] = useState(false);
  const [custData, setCustData] = useState<any>(null);
  const [custSearch, setCustSearch] = useState('');
  const [custTypeFilter, setCustTypeFilter] = useState('');
  const [custSortBy, setCustSortBy] = useState('total_value');
  const [custPage, setCustPage] = useState(1);
  const [selectedCustomer, setSelectedCustomer] = useState<any>(null);
  const [custDetailLoading, setCustDetailLoading] = useState(false);
  const [custDetail, setCustDetail] = useState<any>(null);
  const [expandedCollateral, setExpandedCollateral] = useState<string | null>(null);
  const [valuationHistory, setValuationHistory] = useState<any>(null);

  useEffect(() => {
    if (activeTab === 'dashboard') {
      loadDashboardData();
    }
  }, [region, activeTab]);

  useEffect(() => {
    if (activeTab === 'customers') {
      loadCustomerData();
    }
  }, [region, custTypeFilter, custSortBy, custPage, activeTab]);

  const loadDashboardData = async () => {
    setLoading(true);
    const r = region || undefined;
    try {
      const [dashRes, indexRes, alertRes, ltvRes] = await Promise.all([
        collateralMonitoringApi.getDashboard(r),
        collateralMonitoringApi.getRealEstateIndex(r),
        collateralMonitoringApi.getAlerts({ status: 'OPEN', region: r }),
        collateralMonitoringApi.getLtvAnalysis(r)
      ]);
      setDashboard(dashRes.data);
      setRealEstateIndex(indexRes.data.indices || indexRes.data.index_data || []);
      setAlerts(alertRes.data.alerts || []);
      setLtvAnalysis(ltvRes.data);
    } catch (error) {
      console.error('Collateral monitoring data load error:', error);
      setDashboard(null);
      setRealEstateIndex([]);
      setAlerts([]);
      setLtvAnalysis(null);
    } finally {
      setLoading(false);
    }
  };

  const loadCustomerData = async () => {
    setCustLoading(true);
    try {
      const res = await collateralMonitoringApi.getCustomers({
        search: custSearch || undefined,
        collateral_type: custTypeFilter || undefined,
        region: region || undefined,
        sort_by: custSortBy,
        sort_order: 'desc',
        page: custPage,
        page_size: 15,
      });
      setCustData(res.data);
    } catch (error) {
      console.error('Customer collateral data load error:', error);
      setCustData(null);
    } finally {
      setCustLoading(false);
    }
  };

  const handleCustSearch = () => {
    setCustPage(1);
    loadCustomerData();
  };

  const openCustomerDetail = async (customerId: string) => {
    setSelectedCustomer(customerId);
    setCustDetailLoading(true);
    setExpandedCollateral(null);
    setValuationHistory(null);
    try {
      const res = await collateralMonitoringApi.getCustomerDetail(customerId);
      setCustDetail(res.data);
    } catch (error) {
      console.error('Customer detail load error:', error);
      setCustDetail(null);
    } finally {
      setCustDetailLoading(false);
    }
  };

  const toggleValuationHistory = async (collateralId: string) => {
    if (expandedCollateral === collateralId) {
      setExpandedCollateral(null);
      setValuationHistory(null);
      return;
    }
    setExpandedCollateral(collateralId);
    try {
      const res = await collateralMonitoringApi.getValuationHistory(collateralId);
      setValuationHistory(res.data);
    } catch {
      setValuationHistory(null);
    }
  };

  const openFeatureModal = async (featureId: string) => {
    try {
      const res = await collateralMonitoringApi.getFeatureDescription(featureId);
      setFeatureInfo(res.data);
      setModalOpen(true);
    } catch (error) {
      console.error('Feature description load error:', error);
    }
  };

  // LTV distribution for chart
  const ltvDistribution = ltvAnalysis?.ltv_distribution?.map((d: any) => {
    const bucket = d.ltv_bucket || d.range;
    return {
      name: bucket,
      value: d.count,
      color: bucket === '0-50%' ? COLORS.success :
             bucket?.includes('50') || bucket?.includes('60') ? COLORS.primary :
             bucket?.includes('70') ? COLORS.warning : COLORS.danger
    };
  }).filter((d: any) => d.value > 0) || [];

  // Prepare chart data
  const indexRegions = [...new Set(realEstateIndex.map((d: any) => d.region_code || d.region))];
  const indexChartData = realEstateIndex
    .filter((d: any) => !chartRegion || (d.region_code || d.region) === chartRegion)
    .reduce((acc: any[], curr: any) => {
      const dateKey = (curr.reference_date || curr.index_month)?.substring(0, 7);
      const regionKey = curr.region_code || curr.region;
      const existing = acc.find(a => a.date === dateKey);
      if (existing) {
        existing[regionKey] = curr.index_value;
      } else {
        acc.push({ date: dateKey, [regionKey]: curr.index_value });
      }
      return acc;
    }, [])
    .sort((a, b) => (a.date || '').localeCompare(b.date || ''))
    .slice(-12);

  const renderDashboard = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center h-96">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        {/* Summary Stats */}
        <div className="grid grid-cols-5 gap-4">
          <StatCard
            title="총 담보가치"
            value={formatAmount(dashboard?.summary?.total_value || 0, 'trillion')}
            icon={<Building size={24} />}
            color="blue"
          />
          <StatCard
            title="평균 LTV"
            value={formatPercent((dashboard?.summary?.avg_ltv || 0) * 100)}
            icon={<BarChart3 size={24} />}
            color={(dashboard?.summary?.avg_ltv || 0) > 0.7 ? 'red' : (dashboard?.summary?.avg_ltv || 0) > 0.6 ? 'yellow' : 'green'}
          />
          <StatCard
            title="고 LTV 건수"
            value={dashboard?.summary?.high_ltv_count || 0}
            subtitle="LTV 80% 초과"
            icon={<AlertTriangle size={24} />}
            color="red"
          />
          <StatCard
            title="총 담보 수"
            value={dashboard?.summary?.total_collaterals || 0}
            icon={<Home size={24} />}
            color="blue"
          />
          <StatCard
            title="미해결 알림"
            value={Object.values(dashboard?.open_alerts_by_severity || {}).reduce((a: number, b: any) => a + (b || 0), 0)}
            icon={<AlertTriangle size={24} />}
            color="yellow"
          />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-3 gap-6">
          <Card
            title="LTV 분포"
            headerAction={<HelpButton onClick={() => openFeatureModal('ltv_management')} size="sm" />}
          >
            <DonutChart
              data={ltvDistribution}
              height={240}
              innerRadius={50}
              outerRadius={80}
            />
          </Card>

          <Card
            title="부동산 가격지수 추이"
            headerAction={
              <div className="flex items-center space-x-2">
                <HelpButton onClick={() => openFeatureModal('real_estate_index')} size="sm" />
                <select
                  value={chartRegion}
                  onChange={(e) => setChartRegion(e.target.value)}
                  className="text-sm border rounded px-2 py-1"
                >
                  <option value="">전체</option>
                  {indexRegions.map(r => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </div>
            }
            className="col-span-2"
          >
            <TrendChart
              data={indexChartData}
              lines={
                chartRegion
                  ? [{ key: chartRegion, name: chartRegion, color: COLORS.primary }]
                  : indexRegions.slice(0, 5).map((r, i) => ({
                      key: r,
                      name: r,
                      color: [COLORS.primary, COLORS.success, COLORS.warning, COLORS.danger, COLORS.secondary][i]
                    }))
              }
              xAxisKey="date"
              height={240}
              showLegend
            />
          </Card>
        </div>

        {/* LTV Analysis */}
        <Card title="LTV 분석 현황">
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="p-4 bg-green-50 rounded-lg border border-green-200">
              <p className="text-sm text-green-700">안전 (0-50%)</p>
              <p className="text-2xl font-bold text-green-600">{ltvAnalysis?.ltv_distribution?.find((d: any) => (d.ltv_bucket || d.range) === '0-50%')?.count || 0}건</p>
              <p className="text-xs text-green-600">{formatAmount(ltvAnalysis?.ltv_distribution?.find((d: any) => (d.ltv_bucket || d.range) === '0-50%')?.total_collateral_value || 0, 'billion')}</p>
            </div>
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm text-blue-700">양호 (50-60%)</p>
              <p className="text-2xl font-bold text-blue-600">{ltvAnalysis?.ltv_distribution?.find((d: any) => (d.ltv_bucket || d.range) === '50-60%')?.count || 0}건</p>
              <p className="text-xs text-blue-600">{formatAmount(ltvAnalysis?.ltv_distribution?.find((d: any) => (d.ltv_bucket || d.range) === '50-60%')?.total_collateral_value || 0, 'billion')}</p>
            </div>
            <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
              <p className="text-sm text-yellow-700">주의 (60-80%)</p>
              <p className="text-2xl font-bold text-yellow-600">{
                (ltvAnalysis?.ltv_distribution?.find((d: any) => (d.ltv_bucket || d.range) === '60-70%')?.count || 0) +
                (ltvAnalysis?.ltv_distribution?.find((d: any) => (d.ltv_bucket || d.range) === '70-80%')?.count || 0)
              }건</p>
              <p className="text-xs text-yellow-600">{formatAmount(
                (ltvAnalysis?.ltv_distribution?.find((d: any) => (d.ltv_bucket || d.range) === '60-70%')?.total_collateral_value || 0) +
                (ltvAnalysis?.ltv_distribution?.find((d: any) => (d.ltv_bucket || d.range) === '70-80%')?.total_collateral_value || 0), 'billion')}</p>
            </div>
            <div className="p-4 bg-red-50 rounded-lg border border-red-200">
              <p className="text-sm text-red-700">위험 (80%+)</p>
              <p className="text-2xl font-bold text-red-600">{ltvAnalysis?.ltv_distribution?.find((d: any) => (d.ltv_bucket || d.range) === '80%+')?.count || 0}건</p>
              <p className="text-xs text-red-600">{formatAmount(ltvAnalysis?.ltv_distribution?.find((d: any) => (d.ltv_bucket || d.range) === '80%+')?.total_collateral_value || 0, 'billion')}</p>
            </div>
          </div>

          {(ltvAnalysis?.high_ltv_collaterals?.length > 0 || ltvAnalysis?.high_ltv_cases?.length > 0) && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">고 LTV 건 상세 (상위 10건)</h4>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-gray-50">
                      <th className="px-3 py-2 text-left">담보ID</th>
                      <th className="px-3 py-2 text-left">담보유형</th>
                      <th className="px-3 py-2 text-right">담보가치</th>
                      <th className="px-3 py-2 text-right">여신잔액</th>
                      <th className="px-3 py-2 text-center">LTV</th>
                      <th className="px-3 py-2 text-left">고객명</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(ltvAnalysis.high_ltv_collaterals || ltvAnalysis.high_ltv_cases || []).slice(0, 10).map((item: any) => (
                      <tr key={item.collateral_id} className="border-b hover:bg-gray-50">
                        <td className="px-3 py-2 font-mono text-xs">{item.collateral_id}</td>
                        <td className="px-3 py-2">{COLLATERAL_TYPE_LABELS[item.collateral_type] || item.collateral_type}</td>
                        <td className="px-3 py-2 text-right">{formatAmount(item.current_value, 'billion')}</td>
                        <td className="px-3 py-2 text-right">{formatAmount(item.outstanding_amount || item.loan_balance, 'billion')}</td>
                        <td className="px-3 py-2 text-center">
                          <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                            (item.ltv || 0) >= 0.9 ? 'bg-red-100 text-red-700' :
                            (item.ltv || 0) >= 0.8 ? 'bg-yellow-100 text-yellow-700' :
                            'bg-blue-100 text-blue-700'
                          }`}>
                            {formatPercent((item.ltv || 0) * 100)}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-gray-600">{item.customer_name || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </Card>

        {/* Active Alerts */}
        <Card title="활성 알림">
          <div className="grid grid-cols-2 gap-4">
            {alerts.slice(0, 8).map((alert: any) => (
              <div
                key={alert.alert_id}
                className={`p-4 rounded-lg border ${
                  alert.alert_type === 'LTV_BREACH' ? 'border-red-200 bg-red-50' :
                  alert.alert_type === 'VALUE_DROP' ? 'border-yellow-200 bg-yellow-50' :
                  'border-blue-200 bg-blue-50'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    alert.alert_type === 'LTV_BREACH' ? 'bg-red-100 text-red-700' :
                    alert.alert_type === 'VALUE_DROP' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-blue-100 text-blue-700'
                  }`}>
                    {alert.alert_type}
                  </span>
                  <span className={`text-xs ${
                    alert.severity === 'CRITICAL' ? 'text-red-600' :
                    alert.severity === 'HIGH' ? 'text-orange-600' : 'text-yellow-600'
                  }`}>
                    {alert.severity}
                  </span>
                </div>
                <p className="text-sm font-medium text-gray-900 mb-1">{alert.customer_name || alert.collateral_type}</p>
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>{alert.alert_date}</span>
                  <span>LTV: {formatPercent((alert.current_ltv || 0) * 100)}</span>
                </div>
                {alert.required_action && (
                  <p className="mt-2 text-xs text-gray-600 bg-white p-2 rounded">
                    권장조치: {alert.required_action}
                  </p>
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>
    );
  };

  const renderCustomerTab = () => {
    const summary = custData?.summary;
    const typeDistribution = custData?.type_distribution || [];

    return (
      <div className="space-y-6">
        {/* Summary StatCards */}
        <div className="grid grid-cols-4 gap-4">
          <StatCard
            title="담보보유 고객수"
            value={summary?.customer_count?.toLocaleString() || '0'}
            icon={<Users size={24} />}
            color="blue"
          />
          <StatCard
            title="총 담보가치"
            value={formatAmount(summary?.total_value || 0, 'trillion')}
            icon={<Building size={24} />}
            color="green"
          />
          <StatCard
            title="총 인정가액"
            value={formatAmount(summary?.total_recognized || 0, 'trillion')}
            icon={<Shield size={24} />}
            color="blue"
          />
          <StatCard
            title="평균 LTV"
            value={formatPercent((summary?.avg_ltv || 0) * 100)}
            icon={<BarChart3 size={24} />}
            color={(summary?.avg_ltv || 0) > 0.7 ? 'red' : (summary?.avg_ltv || 0) > 0.6 ? 'yellow' : 'green'}
          />
        </div>

        {/* Filters */}
        <Card>
          <div className="flex items-center gap-3">
            {/* Type filter buttons */}
            <div className="flex items-center gap-1">
              <button
                onClick={() => { setCustTypeFilter(''); setCustPage(1); }}
                className={`px-3 py-1.5 text-xs rounded-full font-medium transition-colors ${
                  !custTypeFilter ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                전체
              </button>
              {typeDistribution.map((t: any) => (
                <button
                  key={t.type}
                  onClick={() => { setCustTypeFilter(t.type === custTypeFilter ? '' : t.type); setCustPage(1); }}
                  className={`px-3 py-1.5 text-xs rounded-full font-medium transition-colors ${
                    custTypeFilter === t.type ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {COLLATERAL_TYPE_LABELS[t.type] || t.type} ({t.count})
                </button>
              ))}
            </div>
            <div className="flex-1" />
            {/* Search */}
            <div className="flex items-center gap-2">
              <div className="relative">
                <input
                  type="text"
                  value={custSearch}
                  onChange={(e) => setCustSearch(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleCustSearch()}
                  placeholder="고객명/ID 검색..."
                  className="pl-8 pr-3 py-1.5 text-sm border rounded-lg w-48 focus:ring-2 focus:ring-blue-300 focus:border-blue-400 outline-none"
                />
                <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
              </div>
              <button onClick={handleCustSearch} className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
                검색
              </button>
            </div>
          </div>
        </Card>

        {/* Customer Table */}
        <Card title={`고객별 담보 현황 (${custData?.total_count || 0}건)`}>
          {custLoading ? (
            <div className="flex items-center justify-center h-40">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-gray-50">
                      <th className="px-3 py-2 text-left">고객명</th>
                      <th className="px-3 py-2 text-left">업종</th>
                      <th className="px-3 py-2 text-center">규모</th>
                      <th className="px-3 py-2 text-center">지역</th>
                      <th className="px-3 py-2 text-center cursor-pointer hover:text-blue-600"
                          onClick={() => { setCustSortBy('count'); setCustPage(1); }}>
                        담보건수 {custSortBy === 'count' && '▼'}
                      </th>
                      <th className="px-3 py-2 text-right cursor-pointer hover:text-blue-600"
                          onClick={() => { setCustSortBy('total_value'); setCustPage(1); }}>
                        담보가치 {custSortBy === 'total_value' && '▼'}
                      </th>
                      <th className="px-3 py-2 text-right cursor-pointer hover:text-blue-600"
                          onClick={() => { setCustSortBy('recognized_value'); setCustPage(1); }}>
                        인정가액 {custSortBy === 'recognized_value' && '▼'}
                      </th>
                      <th className="px-3 py-2 text-center cursor-pointer hover:text-blue-600"
                          onClick={() => { setCustSortBy('avg_ltv'); setCustPage(1); }}>
                        평균LTV {custSortBy === 'avg_ltv' && '▼'}
                      </th>
                      <th className="px-3 py-2 text-right cursor-pointer hover:text-blue-600"
                          onClick={() => { setCustSortBy('margin'); setCustPage(1); }}>
                        담보여력 {custSortBy === 'margin' && '▼'}
                      </th>
                      <th className="px-3 py-2 text-center">상세</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(custData?.customers || []).map((c: any) => (
                      <tr key={c.customer_id} className="border-b hover:bg-blue-50 cursor-pointer" onClick={() => openCustomerDetail(c.customer_id)}>
                        <td className="px-3 py-2 font-medium text-gray-900">{c.customer_name}</td>
                        <td className="px-3 py-2 text-gray-600 text-xs">{c.industry_name || '-'}</td>
                        <td className="px-3 py-2 text-center">
                          <span className="px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-700">
                            {SIZE_LABELS[c.size_category] || c.size_category}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-center text-xs text-gray-500">{REGION_LABELS[c.region] || c.region || '-'}</td>
                        <td className="px-3 py-2 text-center font-semibold">{c.collateral_count}</td>
                        <td className="px-3 py-2 text-right">{formatAmount(c.total_value, 'billion')}</td>
                        <td className="px-3 py-2 text-right">{formatAmount(c.total_recognized, 'billion')}</td>
                        <td className="px-3 py-2 text-center">
                          <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                            c.avg_ltv >= 0.8 ? 'bg-red-100 text-red-700' :
                            c.avg_ltv >= 0.7 ? 'bg-yellow-100 text-yellow-700' :
                            c.avg_ltv >= 0.6 ? 'bg-blue-100 text-blue-700' :
                            'bg-green-100 text-green-700'
                          }`}>
                            {formatPercent(c.avg_ltv * 100)}
                          </span>
                        </td>
                        <td className={`px-3 py-2 text-right ${c.total_margin >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatAmount(c.total_margin, 'billion')}
                        </td>
                        <td className="px-3 py-2 text-center">
                          <Eye size={16} className="text-blue-500 mx-auto" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {(custData?.total_pages || 0) > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <span className="text-sm text-gray-500">
                    {custData?.total_count || 0}건 중 {(custPage - 1) * 15 + 1}-{Math.min(custPage * 15, custData?.total_count || 0)}
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setCustPage(p => Math.max(1, p - 1))}
                      disabled={custPage <= 1}
                      className="p-1.5 rounded border hover:bg-gray-50 disabled:opacity-30"
                    >
                      <ChevronLeft size={16} />
                    </button>
                    <span className="text-sm px-3">{custPage} / {custData?.total_pages || 1}</span>
                    <button
                      onClick={() => setCustPage(p => Math.min(custData?.total_pages || 1, p + 1))}
                      disabled={custPage >= (custData?.total_pages || 1)}
                      className="p-1.5 rounded border hover:bg-gray-50 disabled:opacity-30"
                    >
                      <ChevronRight size={16} />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </Card>
      </div>
    );
  };

  // Customer Detail Modal
  const renderDetailModal = () => {
    if (!selectedCustomer) return null;

    const cust = custDetail?.customer;
    const summary = custDetail?.summary;
    const collaterals = custDetail?.collaterals || [];
    const detailAlerts = custDetail?.alerts || [];

    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setSelectedCustomer(null)}>
        <div
          className="bg-white rounded-xl shadow-2xl w-[90vw] max-w-[1200px] max-h-[85vh] overflow-hidden flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Modal Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b bg-gray-50">
            <div>
              <h2 className="text-lg font-bold text-gray-900">
                {cust?.customer_name || selectedCustomer} - 담보 상세
              </h2>
              <p className="text-sm text-gray-500 mt-0.5">
                {cust?.industry_name} | {SIZE_LABELS[cust?.size_category] || cust?.size_category} | {REGION_LABELS[cust?.region] || cust?.region}
              </p>
            </div>
            <button onClick={() => setSelectedCustomer(null)} className="p-2 rounded-lg hover:bg-gray-200">
              <X size={20} />
            </button>
          </div>

          {/* Modal Body */}
          <div className="flex-1 overflow-y-auto px-6 py-4 space-y-5">
            {custDetailLoading ? (
              <div className="flex items-center justify-center h-40">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            ) : (
              <>
                {/* Summary Stats */}
                <div className="grid grid-cols-5 gap-3">
                  <div className="p-3 bg-blue-50 rounded-lg border border-blue-200 text-center">
                    <p className="text-xs text-blue-600">담보 건수</p>
                    <p className="text-xl font-bold text-blue-700">{summary?.collateral_count || 0}</p>
                  </div>
                  <div className="p-3 bg-green-50 rounded-lg border border-green-200 text-center">
                    <p className="text-xs text-green-600">총 담보가치</p>
                    <p className="text-xl font-bold text-green-700">{formatAmount(summary?.total_value || 0, 'billion')}</p>
                  </div>
                  <div className="p-3 bg-purple-50 rounded-lg border border-purple-200 text-center">
                    <p className="text-xs text-purple-600">총 인정가액</p>
                    <p className="text-xl font-bold text-purple-700">{formatAmount(summary?.total_recognized || 0, 'billion')}</p>
                  </div>
                  <div className="p-3 bg-yellow-50 rounded-lg border border-yellow-200 text-center">
                    <p className="text-xs text-yellow-600">평균 LTV</p>
                    <p className="text-xl font-bold text-yellow-700">{formatPercent((summary?.avg_ltv || 0) * 100)}</p>
                  </div>
                  <div className={`p-3 rounded-lg border text-center ${(summary?.total_margin || 0) >= 0 ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                    <p className={`text-xs ${(summary?.total_margin || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>담보여력</p>
                    <p className={`text-xl font-bold ${(summary?.total_margin || 0) >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                      {formatAmount(summary?.total_margin || 0, 'billion')}
                    </p>
                  </div>
                </div>

                {/* Collateral Detail Table */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">담보 목록</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b bg-gray-50">
                          <th className="px-2 py-2 text-left">유형</th>
                          <th className="px-2 py-2 text-left">세부유형</th>
                          <th className="px-2 py-2 text-right">시세</th>
                          <th className="px-2 py-2 text-right">감정가</th>
                          <th className="px-2 py-2 text-center">인정비율</th>
                          <th className="px-2 py-2 text-right">인정가액</th>
                          <th className="px-2 py-2 text-right">선순위</th>
                          <th className="px-2 py-2 text-right">담보여력</th>
                          <th className="px-2 py-2 text-center">LTV</th>
                          <th className="px-2 py-2 text-left">감정기관</th>
                          <th className="px-2 py-2 text-center">감정일</th>
                          <th className="px-2 py-2 text-center">이력</th>
                        </tr>
                      </thead>
                      <tbody>
                        {collaterals.map((col: any) => (
                          <React.Fragment key={col.collateral_id}>
                            <tr className={`border-b hover:bg-gray-50 ${expandedCollateral === col.collateral_id ? 'bg-blue-50' : ''}`}>
                              <td className="px-2 py-2">
                                <span className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-700 text-xs">
                                  {COLLATERAL_TYPE_LABELS[col.collateral_type] || col.collateral_type}
                                </span>
                              </td>
                              <td className="px-2 py-2">{col.collateral_subtype || '-'}</td>
                              <td className="px-2 py-2 text-right">{formatAmount(col.market_value || col.current_value, 'billion')}</td>
                              <td className="px-2 py-2 text-right">{col.appraisal_value ? formatAmount(col.appraisal_value, 'billion') : '-'}</td>
                              <td className="px-2 py-2 text-center">{col.recognition_ratio ? formatPercent(col.recognition_ratio * 100) : '-'}</td>
                              <td className="px-2 py-2 text-right">{col.recognized_value ? formatAmount(col.recognized_value, 'billion') : '-'}</td>
                              <td className="px-2 py-2 text-right">{formatAmount(col.prior_lien_amount || 0, 'billion')}</td>
                              <td className={`px-2 py-2 text-right ${(col.collateral_margin || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {col.collateral_margin != null ? formatAmount(col.collateral_margin, 'billion') : '-'}
                              </td>
                              <td className="px-2 py-2 text-center">
                                <span className={`px-1.5 py-0.5 rounded text-xs font-semibold ${
                                  (col.ltv || 0) >= 0.8 ? 'bg-red-100 text-red-700' :
                                  (col.ltv || 0) >= 0.7 ? 'bg-yellow-100 text-yellow-700' :
                                  'bg-green-100 text-green-700'
                                }`}>
                                  {col.ltv ? formatPercent(col.ltv * 100) : '-'}
                                </span>
                              </td>
                              <td className="px-2 py-2 text-gray-500">{col.appraiser || '-'}</td>
                              <td className="px-2 py-2 text-center text-gray-500">{col.last_appraisal_date || col.valuation_date || '-'}</td>
                              <td className="px-2 py-2 text-center">
                                <button
                                  onClick={(e) => { e.stopPropagation(); toggleValuationHistory(col.collateral_id); }}
                                  className="p-1 rounded hover:bg-blue-100 text-blue-500"
                                  title="감정 이력 조회"
                                >
                                  <TrendingUp size={14} />
                                </button>
                              </td>
                            </tr>
                            {/* Expanded Valuation History */}
                            {expandedCollateral === col.collateral_id && (
                              <tr>
                                <td colSpan={12} className="bg-blue-50 px-4 py-3">
                                  <div className="text-xs">
                                    <h4 className="font-semibold text-blue-700 mb-2">감정 이력 - {col.collateral_id}</h4>
                                    {!valuationHistory ? (
                                      <div className="flex items-center gap-2 text-gray-500">
                                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                                        로딩중...
                                      </div>
                                    ) : (valuationHistory.valuation_history || []).length === 0 ? (
                                      <p className="text-gray-500">감정 이력이 없습니다.</p>
                                    ) : (
                                      <table className="w-full">
                                        <thead>
                                          <tr className="border-b text-gray-500">
                                            <th className="px-2 py-1 text-left">일자</th>
                                            <th className="px-2 py-1 text-left">유형</th>
                                            <th className="px-2 py-1 text-left">출처</th>
                                            <th className="px-2 py-1 text-right">이전 가치</th>
                                            <th className="px-2 py-1 text-right">평가 가치</th>
                                            <th className="px-2 py-1 text-center">변동률</th>
                                            <th className="px-2 py-1 text-center">LTV 전</th>
                                            <th className="px-2 py-1 text-center">LTV 후</th>
                                          </tr>
                                        </thead>
                                        <tbody>
                                          {(valuationHistory.valuation_history || []).slice(0, 6).map((v: any) => (
                                            <tr key={v.valuation_id} className="border-b border-blue-100">
                                              <td className="px-2 py-1">{v.valuation_date}</td>
                                              <td className="px-2 py-1">{v.valuation_type}</td>
                                              <td className="px-2 py-1">{v.valuation_source}</td>
                                              <td className="px-2 py-1 text-right">{formatAmount(v.previous_value, 'billion')}</td>
                                              <td className="px-2 py-1 text-right">{formatAmount(v.current_value, 'billion')}</td>
                                              <td className={`px-2 py-1 text-center ${(v.change_pct || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                                {v.change_pct > 0 ? '+' : ''}{v.change_pct?.toFixed(1)}%
                                              </td>
                                              <td className="px-2 py-1 text-center">{formatPercent((v.ltv_before || 0) * 100)}</td>
                                              <td className="px-2 py-1 text-center">{formatPercent((v.ltv_after || 0) * 100)}</td>
                                            </tr>
                                          ))}
                                        </tbody>
                                      </table>
                                    )}
                                  </div>
                                </td>
                              </tr>
                            )}
                          </React.Fragment>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Customer Alerts */}
                {detailAlerts.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">담보 관련 알림 ({detailAlerts.length}건)</h3>
                    <div className="grid grid-cols-2 gap-3">
                      {detailAlerts.slice(0, 6).map((a: any) => (
                        <div key={a.alert_id} className={`p-3 rounded-lg border text-xs ${
                          a.alert_type === 'LTV_BREACH' ? 'border-red-200 bg-red-50' : 'border-yellow-200 bg-yellow-50'
                        }`}>
                          <div className="flex justify-between items-center mb-1">
                            <span className={`px-1.5 py-0.5 rounded font-medium ${
                              a.alert_type === 'LTV_BREACH' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                            }`}>{a.alert_type}</span>
                            <span className="text-gray-500">{a.alert_date}</span>
                          </div>
                          <p className="text-gray-700">LTV: {formatPercent((a.current_ltv || 0) * 100)} | 변동: {a.value_change_pct?.toFixed(1)}%</p>
                          {a.required_action && <p className="mt-1 text-gray-600">{a.required_action}</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            담보 모니터링
            <HelpButton onClick={() => openFeatureModal('collateral_overview')} />
          </h1>
          <p className="text-sm text-gray-500 mt-1">실시간 담보가치 추적 및 LTV 관리</p>
        </div>
        <RegionFilter value={region} onChange={setRegion} />
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b">
        <button
          onClick={() => setActiveTab('dashboard')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'dashboard'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          대시보드
        </button>
        <button
          onClick={() => setActiveTab('customers')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'customers'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          고객별 담보
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'dashboard' ? renderDashboard() : renderCustomerTab()}

      {/* Customer Detail Modal */}
      {renderDetailModal()}

      {/* Feature Modal */}
      <FeatureModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        feature={featureInfo}
      />
    </div>
  );
}
