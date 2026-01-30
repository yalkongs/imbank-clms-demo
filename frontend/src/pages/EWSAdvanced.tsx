import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Activity,
  Network,
  Radio,
  BarChart3,
  Search
} from 'lucide-react';
import { Card, StatCard, Table, CellFormatters, GroupedBarChart, DonutChart, COLORS, FeatureModal, HelpButton } from '../components';
import { ewsAdvancedApi } from '../utils/api';
import { formatAmount, formatPercent } from '../utils/format';

export default function EWSAdvanced() {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>(null);
  const [indicators, setIndicators] = useState<any[]>([]);
  const [compositeScores, setCompositeScores] = useState<any[]>([]);
  const [externalSignals, setExternalSignals] = useState<any[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<string | null>(null);
  const [supplyChain, setSupplyChain] = useState<any>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [featureInfo, setFeatureInfo] = useState<any>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [dashRes, indRes, scoreRes, signalRes] = await Promise.all([
        ewsAdvancedApi.getDashboard(),
        ewsAdvancedApi.getIndicators(),
        ewsAdvancedApi.getCompositeScores({ limit: 20 }),
        ewsAdvancedApi.getExternalSignals()
      ]);
      setDashboard(dashRes.data);
      setIndicators(indRes.data.indicators || []);
      setCompositeScores(scoreRes.data.scores || []);
      setExternalSignals(signalRes.data.signals || []);
    } catch (error) {
      console.error('EWS Advanced data load error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadSupplyChain = async (customerId: string) => {
    setSelectedCustomer(customerId);
    try {
      const res = await ewsAdvancedApi.getSupplyChain(customerId);
      setSupplyChain(res.data);
    } catch (error) {
      console.error('Supply chain load error:', error);
    }
  };

  const openFeatureModal = async (featureId: string) => {
    try {
      const res = await ewsAdvancedApi.getFeatureDescription(featureId);
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

  // Risk distribution for chart - API returns { CRITICAL: 32, HIGH: 174, LOW: 36, MEDIUM: 168 }
  const riskDist = dashboard?.risk_distribution || {};
  const scoreDistribution = [
    { name: 'LOW', value: riskDist['LOW'] || 0, color: COLORS.success },
    { name: 'MEDIUM', value: riskDist['MEDIUM'] || 0, color: COLORS.warning },
    { name: 'HIGH', value: riskDist['HIGH'] || 0, color: COLORS.danger },
    { name: 'CRITICAL', value: riskDist['CRITICAL'] || 0, color: '#7f1d1d' }
  ].filter(d => d.value > 0);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            EWS 고도화 (조기경보 시스템)
            <HelpButton onClick={() => openFeatureModal('ews_overview')} />
          </h1>
          <p className="text-sm text-gray-500 mt-1">선행지표, 공급망 분석, 외부 신호 통합 모니터링</p>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="고위험 기업"
          value={dashboard?.high_risk_count || 0}
          subtitle="점수 70점 이상"
          icon={<AlertTriangle size={24} />}
          color="red"
        />
        <StatCard
          title="모니터링 기업"
          value={dashboard?.total_monitored || 0}
          subtitle="복합점수 산출"
          icon={<Activity size={24} />}
          color="blue"
        />
        <StatCard
          title="외부 신호"
          value={dashboard?.active_signals || 0}
          subtitle="뉴스/신용정보"
          icon={<Radio size={24} />}
          color="yellow"
        />
        <StatCard
          title="평균 복합점수"
          value={formatPercent(dashboard?.avg_composite_score || 0, 0)}
          icon={<BarChart3 size={24} />}
          color={dashboard?.avg_composite_score > 50 ? 'red' : 'green'}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-3 gap-6">
        {/* Score Distribution */}
        <Card
          title="복합점수 분포"
          headerAction={<HelpButton onClick={() => openFeatureModal('composite_score')} size="sm" />}
        >
          <DonutChart
            data={scoreDistribution}
            height={240}
            innerRadius={50}
            outerRadius={80}
          />
        </Card>

        {/* Leading Indicators */}
        <Card
          title="선행지표 현황"
          headerAction={<HelpButton onClick={() => openFeatureModal('leading_indicator')} size="sm" />}
          className="col-span-2"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="px-3 py-2 text-left">지표명</th>
                  <th className="px-3 py-2 text-left">유형</th>
                  <th className="px-3 py-2 text-right">가중치</th>
                  <th className="px-3 py-2 text-right">경고 임계값</th>
                  <th className="px-3 py-2 text-center">분류</th>
                </tr>
              </thead>
              <tbody>
                {indicators.slice(0, 8).map((ind: any) => (
                  <tr key={ind.indicator_id} className="border-b hover:bg-gray-50">
                    <td className="px-3 py-2 font-medium">{ind.indicator_name}</td>
                    <td className="px-3 py-2">
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        ind.indicator_type === 'FINANCIAL' ? 'bg-blue-100 text-blue-700' :
                        ind.indicator_type === 'MARKET' ? 'bg-purple-100 text-purple-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {ind.indicator_type}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right">{ind.weight?.toFixed(1) || '-'}</td>
                    <td className="px-3 py-2 text-right">{ind.threshold_warning || ind.threshold_critical || '-'}</td>
                    <td className="px-3 py-2 text-center">{ind.category || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Composite Scores Table */}
      <Card
        title="복합 EWS 점수 현황"
        headerAction={<HelpButton onClick={() => openFeatureModal('composite_score')} size="sm" />}
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 text-left">기업명</th>
                <th className="px-3 py-2 text-center">복합점수</th>
                <th className="px-3 py-2 text-center">재무점수</th>
                <th className="px-3 py-2 text-center">시장점수</th>
                <th className="px-3 py-2 text-center">공급망점수</th>
                <th className="px-3 py-2 text-center">외부점수</th>
                <th className="px-3 py-2 text-center">등급</th>
                <th className="px-3 py-2 text-center">추세</th>
                <th className="px-3 py-2 text-center">액션</th>
              </tr>
            </thead>
            <tbody>
              {compositeScores.map((score: any) => (
                <tr key={score.score_id} className="border-b hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium">{score.customer_name}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-2 py-1 rounded font-semibold ${
                      score.composite_score >= 70 ? 'bg-red-100 text-red-700' :
                      score.composite_score >= 50 ? 'bg-yellow-100 text-yellow-700' :
                      'bg-green-100 text-green-700'
                    }`}>
                      {score.composite_score?.toFixed(1)}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center">{score.financial_score?.toFixed(1)}</td>
                  <td className="px-3 py-2 text-center">{score.market_score?.toFixed(1)}</td>
                  <td className="px-3 py-2 text-center">{score.supply_chain_score?.toFixed(1)}</td>
                  <td className="px-3 py-2 text-center">{score.external_score?.toFixed(1)}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      score.ews_grade === 'CRITICAL' ? 'bg-red-600 text-white' :
                      score.ews_grade === 'WARNING' ? 'bg-yellow-500 text-white' :
                      score.ews_grade === 'WATCH' ? 'bg-blue-100 text-blue-700' :
                      'bg-green-100 text-green-700'
                    }`}>
                      {score.ews_grade}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    {score.score_trend === 'UP' ? (
                      <TrendingUp className="inline text-red-500" size={16} />
                    ) : score.score_trend === 'DOWN' ? (
                      <TrendingDown className="inline text-green-500" size={16} />
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-center">
                    <button
                      onClick={() => loadSupplyChain(score.customer_id)}
                      className="p-1 text-blue-600 hover:bg-blue-50 rounded"
                      title="공급망 분석"
                    >
                      <Network size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* External Signals */}
      <Card
        title="외부 신호 모니터링"
        headerAction={<HelpButton onClick={() => openFeatureModal('ews_overview')} size="sm" />}
      >
        <div className="grid grid-cols-2 gap-4">
          {externalSignals.slice(0, 6).map((signal: any) => (
            <div
              key={signal.signal_id}
              className={`p-4 rounded-lg border ${
                signal.sentiment === 'NEGATIVE' ? 'border-red-200 bg-red-50' :
                signal.sentiment === 'POSITIVE' ? 'border-green-200 bg-green-50' :
                'border-gray-200 bg-gray-50'
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    signal.signal_type === 'NEWS' ? 'bg-purple-100 text-purple-700' :
                    signal.signal_type === 'CREDIT_RATING' ? 'bg-blue-100 text-blue-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {signal.signal_type}
                  </span>
                  <p className="mt-2 text-sm font-medium text-gray-900">{signal.customer_name}</p>
                  <p className="text-xs text-gray-600 mt-1">{signal.signal_content}</p>
                </div>
                <span className={`text-xs font-semibold ${
                  signal.sentiment === 'NEGATIVE' ? 'text-red-600' :
                  signal.sentiment === 'POSITIVE' ? 'text-green-600' : 'text-gray-600'
                }`}>
                  {signal.impact_score > 0 ? '+' : ''}{signal.impact_score}
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-2">{signal.signal_date}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* Supply Chain Modal */}
      {supplyChain && (
        <Card
          title={`공급망 분석: ${supplyChain.customer_name || selectedCustomer}`}
          headerAction={
            <div className="flex items-center space-x-2">
              <HelpButton onClick={() => openFeatureModal('supply_chain_analysis')} size="sm" />
              <button
                onClick={() => setSupplyChain(null)}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                닫기
              </button>
            </div>
          }
        >
          <div className="grid grid-cols-2 gap-6">
            {/* Suppliers */}
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">공급업체 (Upstream)</h4>
              <div className="space-y-2">
                {supplyChain.suppliers?.length > 0 ? supplyChain.suppliers.map((s: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="text-sm font-medium">{s.related_customer_name}</p>
                      <p className="text-xs text-gray-500">의존도: {formatPercent(s.dependency_ratio)}</p>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      s.risk_impact === 'HIGH' ? 'bg-red-100 text-red-700' :
                      s.risk_impact === 'MEDIUM' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-green-100 text-green-700'
                    }`}>
                      {s.risk_impact}
                    </span>
                  </div>
                )) : <p className="text-sm text-gray-500">공급업체 정보 없음</p>}
              </div>
            </div>

            {/* Customers */}
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">고객사 (Downstream)</h4>
              <div className="space-y-2">
                {supplyChain.customers?.length > 0 ? supplyChain.customers.map((c: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="text-sm font-medium">{c.related_customer_name}</p>
                      <p className="text-xs text-gray-500">의존도: {formatPercent(c.dependency_ratio)}</p>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      c.risk_impact === 'HIGH' ? 'bg-red-100 text-red-700' :
                      c.risk_impact === 'MEDIUM' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-green-100 text-green-700'
                    }`}>
                      {c.risk_impact}
                    </span>
                  </div>
                )) : <p className="text-sm text-gray-500">고객사 정보 없음</p>}
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
