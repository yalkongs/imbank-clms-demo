import React, { useEffect, useState } from 'react';
import {
  UserCheck,
  TrendingUp,
  DollarSign,
  Target,
  ShoppingCart,
  AlertTriangle,
  Users,
  Award,
  ChevronRight
} from 'lucide-react';
import { Card, StatCard, GroupedBarChart, DonutChart, COLORS, FeatureModal, HelpButton, RegionFilter } from '../components';
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
        customerProfitabilityApi.getCrossSellOpportunities({ region: r }),
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
          <p className="text-sm text-gray-500 mt-1">고객 생애가치(CLV), 교차판매, 이탈예측 분석 · 여신수익·EL·자본은 여신 정본(계약금리·risk_parameter) 연동, 비여신 관계는 자본 소모가 작아 RAROC이 높게 표시됩니다</p>
        </div>
        {/* 지역 구분은 전 화면에서 같은 형태로 모두 노출한다.
            드롭다운은 선택지가 숨겨져 화면마다 조작 방식이 달라 보였다. */}
        <RegionFilter value={region} onChange={setRegion} />
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
                <th className="w-8"></th>
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
                  <td className="px-2 py-2 text-right"><ChevronRight size={14} className="row-chevron inline" /></td>
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
                  <div className="flex items-center gap-1.5">
                    <span className={`px-1.5 py-0.5 rounded text-xs ${
                      opp.status === 'IDENTIFIED' ? 'bg-blue-100 text-blue-700' :
                      opp.status === 'CONTACTED' ? 'bg-indigo-100 text-indigo-700' :
                      opp.status === 'PROPOSED' ? 'bg-yellow-100 text-yellow-700' :
                      opp.status === 'WON' ? 'bg-green-100 text-green-700' :
                      opp.status === 'LOST' ? 'bg-gray-100 text-gray-500' :
                      'bg-red-100 text-red-700'
                    }`}>
                      {opp.status === 'IDENTIFIED' ? '발굴' :
                       opp.status === 'CONTACTED' ? '접촉' :
                       opp.status === 'PROPOSED' ? '제안' :
                       opp.status === 'WON' ? '성사' :
                       opp.status === 'LOST' ? '탈락' : '거절'}
                    </span>
                    <span className={`px-1.5 py-0.5 rounded text-xs ${
                      (opp.priority_score || 0) >= 70 ? 'bg-red-100 text-red-700' :
                      (opp.priority_score || 0) >= 50 ? 'bg-yellow-100 text-yellow-700' :
                      'bg-blue-100 text-blue-700'
                    }`}>
                      {(opp.priority_score || 0) >= 70 ? 'HIGH' : (opp.priority_score || 0) >= 50 ? 'MEDIUM' : 'LOW'}
                    </span>
                  </div>
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setSelectedCustomer(null)}>
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl mx-4 max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b sticky top-0 bg-white rounded-t-xl">
              <div>
                <h3 className="text-lg font-bold text-gray-900">{selectedCustomer.customer_info?.customer_name}</h3>
                <p className="text-xs text-gray-500">{selectedCustomer.customer_info?.industry_name} · {selectedCustomer.customer_info?.size_category}</p>
              </div>
              <button onClick={() => setSelectedCustomer(null)} className="p-1 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
            </div>
            <div className="p-6 space-y-6">
              <div className="grid grid-cols-4 gap-3">
                <div className="p-3 bg-gray-50 rounded-lg text-center">
                  <p className="text-xs text-gray-500">총 수익</p>
                  <p className="text-lg font-bold text-green-600">{formatAmount(selectedCustomer.profitability?.total?.revenue, 'billion')}</p>
                </div>
                <div className="p-3 bg-gray-50 rounded-lg text-center">
                  <p className="text-xs text-gray-500">총 비용</p>
                  <p className="text-lg font-bold text-red-600">{formatAmount(selectedCustomer.profitability?.total?.cost, 'billion')}</p>
                </div>
                <div className="p-3 bg-gray-50 rounded-lg text-center">
                  <p className="text-xs text-gray-500">RAROC</p>
                  <p className={`text-lg font-bold ${(selectedCustomer.profitability?.raroc || 0) >= 15 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatPercent(selectedCustomer.profitability?.raroc)}
                  </p>
                </div>
                <div className="p-3 bg-gray-50 rounded-lg text-center">
                  <p className="text-xs text-gray-500">CLV 점수</p>
                  <p className="text-lg font-bold text-blue-600">{(selectedCustomer.lifecycle_metrics?.clv_score || 0).toFixed(1)}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-6">
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">수익 구성</h4>
                  <div className="space-y-1.5">
                    {[
                      ['여신', selectedCustomer.profitability?.loan?.revenue],
                      ['수신', selectedCustomer.profitability?.deposit?.revenue],
                      ['수수료', selectedCustomer.profitability?.fee?.revenue],
                      ['외환/파생', selectedCustomer.profitability?.fx?.revenue],
                    ].map(([label, val]) => (
                      <div key={label as string} className="flex justify-between p-2 bg-gray-50 rounded text-sm">
                        <span>{label}</span>
                        <span className="font-medium">{formatAmount(val as number, 'million')}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">비용 구성</h4>
                  <div className="space-y-1.5">
                    {[
                      ['여신비용', selectedCustomer.profitability?.loan?.cost],
                      ['예상손실(EL)', selectedCustomer.profitability?.loan?.el],
                      ['자본비용', selectedCustomer.profitability?.loan?.capital_cost],
                      ['수신비용', selectedCustomer.profitability?.deposit?.cost],
                    ].map(([label, val]) => (
                      <div key={label as string} className="flex justify-between p-2 bg-gray-50 rounded text-sm">
                        <span>{label}</span>
                        <span className="font-medium">{formatAmount(val as number, 'million')}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Cross-sell 기회 */}
              {selectedCustomer.cross_sell_opportunities?.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">교차판매 기회</h4>
                  <div className="space-y-1.5">
                    {selectedCustomer.cross_sell_opportunities.map((opp: any, i: number) => (
                      <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded text-sm">
                        <span>{opp.product_type}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-gray-500">확률 {formatPercent((opp.probability || 0) * 100)}</span>
                          <span className={`px-1.5 py-0.5 rounded text-xs ${
                            opp.status === 'WON' ? 'bg-green-100 text-green-700' :
                            opp.status === 'LOST' || opp.status === 'DECLINED' ? 'bg-gray-100 text-gray-500' :
                            'bg-blue-100 text-blue-700'
                          }`}>{opp.status}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
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
