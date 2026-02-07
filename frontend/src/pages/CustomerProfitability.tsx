import React, { useEffect, useState } from 'react';
import {
  UserCheck,
  TrendingUp,
  DollarSign,
  Target,
  ShoppingCart,
  AlertTriangle,
  Users,
  Award
} from 'lucide-react';
import { Card, StatCard, GroupedBarChart, DonutChart, COLORS, FeatureModal, HelpButton } from '../components';
import { customerProfitabilityApi } from '../utils/api';
import { formatAmount, formatPercent } from '../utils/format';

const REGIONS = [
  { value: '', label: '전체 지역' },
  { value: 'CAPITAL', label: '수도권' },
  { value: 'DAEGU_GB', label: '대구경북' },
  { value: 'BUSAN_GN', label: '부산경남' },
];

export default function CustomerProfitability() {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>(null);
  const [rankings, setRankings] = useState<any[]>([]);
  const [crossSell, setCrossSell] = useState<any[]>([]);
  const [churnRisk, setChurnRisk] = useState<any[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<any>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [featureInfo, setFeatureInfo] = useState<any>(null);
  const [region, setRegion] = useState('');

  useEffect(() => {
    loadData();
  }, [region]);

  const loadData = async () => {
    const r = region || undefined;
    try {
      const [dashRes, rankRes, crossRes, churnRes] = await Promise.all([
        customerProfitabilityApi.getDashboard(r),
        customerProfitabilityApi.getRankings({ limit: 20, region: r }),
        customerProfitabilityApi.getCrossSellOpportunities({ status: 'IDENTIFIED', region: r }),
        customerProfitabilityApi.getChurnRisk({ min_risk: 0.3, region: r })
      ]);
      setDashboard(dashRes.data);
      setRankings(rankRes.data.rankings || []);
      setCrossSell(crossRes.data.opportunities || []);
      setChurnRisk(churnRes.data.at_risk_customers || []);
    } catch (error) {
      console.error('Customer profitability data load error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadCustomerDetail = async (customerId: string) => {
    try {
      const res = await customerProfitabilityApi.getCustomer(customerId);
      setSelectedCustomer(res.data);
    } catch (error) {
      console.error('Customer detail load error:', error);
    }
  };

  const openFeatureModal = async (featureId: string) => {
    try {
      const res = await customerProfitabilityApi.getFeatureDescription(featureId);
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

  // Profitability distribution - API returns by_size_category
  const profitabilityDist = dashboard?.by_size_category?.map((d: any) => ({
    name: d.size_category,
    value: d.count,
    color: d.size_category === 'LARGE' ? COLORS.primary :
           d.size_category === 'MEDIUM' ? COLORS.success :
           d.size_category === 'SMALL' ? COLORS.warning : COLORS.secondary
  })) || [];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            고객 수익성 분석 (RBC)
            <HelpButton onClick={() => openFeatureModal('rbc_overview')} />
          </h1>
          <p className="text-sm text-gray-500 mt-1">고객 생애가치(CLV), 교차판매, 이탈예측 분석</p>
        </div>
        <select
          value={region}
          onChange={(e) => setRegion(e.target.value)}
          className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {REGIONS.map((r) => (
            <option key={r.value} value={r.value}>{r.label}</option>
          ))}
        </select>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-5 gap-4">
        <StatCard
          title="총 분석 고객"
          value={dashboard?.summary?.customer_count || 0}
          icon={<Users size={24} />}
          color="blue"
        />
        <StatCard
          title="평균 RAROC"
          value={formatPercent(dashboard?.summary?.avg_raroc || 0)}
          icon={<TrendingUp size={24} />}
          color={(dashboard?.summary?.avg_raroc || 0) >= 15 ? 'green' : 'yellow'}
        />
        <StatCard
          title="평균 CLV"
          value={(dashboard?.summary?.avg_clv_score || 0).toFixed(1)}
          subtitle="CLV 점수"
          icon={<DollarSign size={24} />}
          color="green"
        />
        <StatCard
          title="교차판매 기회"
          value={crossSell.length || 0}
          subtitle="발굴된 기회"
          icon={<ShoppingCart size={24} />}
          color="blue"
        />
        <StatCard
          title="이탈 위험 고객"
          value={dashboard?.summary?.high_churn_risk_count || 0}
          icon={<AlertTriangle size={24} />}
          color="red"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-3 gap-6">
        {/* Profitability Distribution */}
        <Card title="수익성 분포">
          <DonutChart
            data={profitabilityDist}
            height={240}
            innerRadius={50}
            outerRadius={80}
          />
        </Card>

        {/* Top Customers by CLV */}
        <Card
          title="CLV 상위 고객"
          headerAction={<HelpButton onClick={() => openFeatureModal('clv')} size="sm" />}
          className="col-span-2"
        >
          <GroupedBarChart
            data={rankings.slice(0, 10).map(r => ({
              name: r.customer_name?.substring(0, 8) || '',
              CLV: r.clv_score || 0,
              RAROC: r.raroc
            }))}
            bars={[
              { key: 'CLV', name: 'CLV 점수', color: COLORS.primary }
            ]}
            xAxisKey="name"
            height={240}
            showLegend={false}
          />
        </Card>
      </div>

      {/* Customer Rankings Table */}
      <Card title="고객 수익성 순위">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 text-center">순위</th>
                <th className="px-3 py-2 text-left">기업명</th>
                <th className="px-3 py-2 text-right">총수익</th>
                <th className="px-3 py-2 text-right">총비용</th>
                <th className="px-3 py-2 text-right">순이익</th>
                <th className="px-3 py-2 text-right">RAROC</th>
                <th className="px-3 py-2 text-right">CLV</th>
                <th className="px-3 py-2 text-center">세그먼트</th>
                <th className="px-3 py-2 text-center">이탈위험</th>
              </tr>
            </thead>
            <tbody>
              {rankings.map((rank: any, index: number) => (
                <tr
                  key={rank.profitability_id}
                  className="border-b hover:bg-gray-50 cursor-pointer"
                  onClick={() => loadCustomerDetail(rank.customer_id)}
                >
                  <td className="px-3 py-2 text-center">
                    <span className={`w-6 h-6 inline-flex items-center justify-center rounded-full text-xs font-medium ${
                      index < 3 ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {index + 1}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-medium">{rank.customer_name}</td>
                  <td className="px-3 py-2 text-right text-green-600">{formatAmount(rank.total_revenue, 'million')}</td>
                  <td className="px-3 py-2 text-right text-red-600">{formatAmount(rank.total_cost, 'million')}</td>
                  <td className="px-3 py-2 text-right font-semibold">{formatAmount(rank.total_profit, 'million')}</td>
                  <td className="px-3 py-2 text-right">
                    <span className={rank.raroc >= 15 ? 'text-green-600' : 'text-red-600'}>
                      {formatPercent(rank.raroc)}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right font-semibold">{(rank.clv_score || 0).toFixed(1)}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      rank.raroc >= 15 ? 'bg-green-100 text-green-700' :
                      rank.raroc >= 10 ? 'bg-yellow-100 text-yellow-700' :
                      'bg-red-100 text-red-700'
                    }`}>
                      {rank.raroc >= 15 ? 'HIGH' : rank.raroc >= 10 ? 'MEDIUM' : 'LOW'}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${
                          (rank.churn_risk_score || 0) >= 0.7 ? 'bg-red-500' :
                          (rank.churn_risk_score || 0) >= 0.4 ? 'bg-yellow-500' : 'bg-green-500'
                        }`}
                        style={{ width: `${(rank.churn_risk_score || 0) * 100}%` }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Cross-sell and Churn */}
      <div className="grid grid-cols-2 gap-6">
        {/* Cross-sell Opportunities */}
        <Card
          title="교차판매 기회"
          headerAction={<HelpButton onClick={() => openFeatureModal('cross_sell')} size="sm" />}
        >
          <div className="space-y-3">
            {crossSell.slice(0, 8).map((opp: any) => (
              <div key={opp.opportunity_id} className="p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-gray-900">{opp.customer_name}</span>
                  <span className={`px-2 py-0.5 rounded text-xs ${
                    (opp.priority_score || 0) >= 70 ? 'bg-red-100 text-red-700' :
                    (opp.priority_score || 0) >= 50 ? 'bg-yellow-100 text-yellow-700' :
                    'bg-blue-100 text-blue-700'
                  }`}>
                    {(opp.priority_score || 0) >= 70 ? 'HIGH' : (opp.priority_score || 0) >= 50 ? 'MEDIUM' : 'LOW'}
                  </span>
                </div>
                <p className="text-sm text-gray-700">{opp.product_type}</p>
                <div className="flex items-center justify-between mt-2 text-xs">
                  <span className="text-gray-500">성공확률: {formatPercent((opp.probability || 0) * 100)}</span>
                  <span className="text-green-600 font-medium">기대수익: {formatAmount(opp.expected_revenue, 'million')}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Churn Risk */}
        <Card
          title="이탈 위험 고객"
          headerAction={<HelpButton onClick={() => openFeatureModal('churn_prediction')} size="sm" />}
        >
          <div className="space-y-3">
            {churnRisk.slice(0, 8).map((cust: any, index: number) => (
              <div key={cust.customer_id || index} className="p-3 bg-red-50 rounded-lg border border-red-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-gray-900">{cust.customer_name}</span>
                  <span className="text-red-600 font-semibold">{formatPercent((cust.churn_risk_score || 0) * 100)}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-500">CLV: {(cust.clv_score || 0).toFixed(1)}</span>
                  <span className="text-gray-500">RAROC: {formatPercent(cust.raroc)}</span>
                </div>
                <div className="mt-2 relative h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="absolute left-0 h-full bg-red-500 rounded-full"
                    style={{ width: `${(cust.churn_risk_score || 0) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Customer Detail Modal */}
      {selectedCustomer && (
        <Card
          title={`고객 상세: ${selectedCustomer.customer_name}`}
          headerAction={
            <button
              onClick={() => setSelectedCustomer(null)}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              닫기
            </button>
          }
        >
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">총 수익</p>
              <p className="text-xl font-bold text-green-600">{formatAmount(selectedCustomer.total_revenue, 'billion')}</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">총 비용</p>
              <p className="text-xl font-bold text-red-600">{formatAmount(selectedCustomer.total_cost, 'billion')}</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">RAROC</p>
              <p className={`text-xl font-bold ${selectedCustomer.raroc >= 15 ? 'text-green-600' : 'text-red-600'}`}>
                {formatPercent(selectedCustomer.raroc)}
              </p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">CLV</p>
              <p className="text-xl font-bold text-blue-600">{formatAmount(selectedCustomer.clv, 'billion')}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">수익 구성</h4>
              <div className="space-y-2">
                <div className="flex justify-between p-2 bg-gray-50 rounded">
                  <span className="text-sm">이자수익</span>
                  <span className="text-sm font-medium">{formatAmount(selectedCustomer.interest_income, 'million')}</span>
                </div>
                <div className="flex justify-between p-2 bg-gray-50 rounded">
                  <span className="text-sm">수수료수익</span>
                  <span className="text-sm font-medium">{formatAmount(selectedCustomer.fee_income, 'million')}</span>
                </div>
                <div className="flex justify-between p-2 bg-gray-50 rounded">
                  <span className="text-sm">기타수익</span>
                  <span className="text-sm font-medium">{formatAmount(selectedCustomer.other_income, 'million')}</span>
                </div>
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">비용 구성</h4>
              <div className="space-y-2">
                <div className="flex justify-between p-2 bg-gray-50 rounded">
                  <span className="text-sm">자금조달비용</span>
                  <span className="text-sm font-medium">{formatAmount(selectedCustomer.funding_cost, 'million')}</span>
                </div>
                <div className="flex justify-between p-2 bg-gray-50 rounded">
                  <span className="text-sm">신용비용</span>
                  <span className="text-sm font-medium">{formatAmount(selectedCustomer.credit_cost, 'million')}</span>
                </div>
                <div className="flex justify-between p-2 bg-gray-50 rounded">
                  <span className="text-sm">운영비용</span>
                  <span className="text-sm font-medium">{formatAmount(selectedCustomer.operating_cost, 'million')}</span>
                </div>
                <div className="flex justify-between p-2 bg-gray-50 rounded">
                  <span className="text-sm">자본비용</span>
                  <span className="text-sm font-medium">{formatAmount(selectedCustomer.capital_cost, 'million')}</span>
                </div>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Feature Modal */}
      <FeatureModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        feature={featureInfo}
      />
    </div>
  );
}
