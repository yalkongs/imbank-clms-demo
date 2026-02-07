import React, { useEffect, useState } from 'react';
import {
  Home,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Building,
  BarChart3,
  MapPin
} from 'lucide-react';
import { Card, StatCard, TrendChart, GroupedBarChart, DonutChart, COLORS, FeatureModal, HelpButton, RegionFilter } from '../components';
import { collateralMonitoringApi } from '../utils/api';
import { formatAmount, formatPercent } from '../utils/format';

const REGIONS = [
  { value: '', label: '전체 지역' },
  { value: 'CAPITAL', label: '수도권' },
  { value: 'DAEGU_GB', label: '대구경북' },
  { value: 'BUSAN_GN', label: '부산경남' },
];

export default function CollateralMonitoring() {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>(null);
  const [realEstateIndex, setRealEstateIndex] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [ltvAnalysis, setLtvAnalysis] = useState<any>(null);
  const [region, setRegion] = useState<string>('');
  const [chartRegion, setChartRegion] = useState<string>('');
  const [modalOpen, setModalOpen] = useState(false);
  const [featureInfo, setFeatureInfo] = useState<any>(null);

  useEffect(() => {
    loadData();
  }, [region]);

  const loadData = async () => {
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
    } finally {
      setLoading(false);
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // LTV distribution for chart - API returns ltv_bucket field
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

  // Prepare chart data - API returns region_code and reference_date
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
        {/* LTV Distribution */}
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

        {/* Real Estate Index */}
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

        {/* High LTV Cases - API returns high_ltv_collaterals */}
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
                      <td className="px-3 py-2">{item.collateral_type}</td>
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

      {/* Feature Modal */}
      <FeatureModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        feature={featureInfo}
      />
    </div>
  );
}
