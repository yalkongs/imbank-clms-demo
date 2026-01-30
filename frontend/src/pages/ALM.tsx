import React, { useEffect, useState } from 'react';
import {
  TrendingDown,
  TrendingUp,
  Activity,
  BarChart3,
  Shield,
  AlertTriangle,
  DollarSign,
  Percent
} from 'lucide-react';
import { Card, StatCard, GroupedBarChart, TrendChart, DonutChart, COLORS, FeatureModal, HelpButton } from '../components';
import { almApi } from '../utils/api';
import { formatAmount, formatPercent } from '../utils/format';

export default function ALM() {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>(null);
  const [gapAnalysis, setGapAnalysis] = useState<any>(null);
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [scenarioResults, setScenarioResults] = useState<any>(null);
  const [hedgePositions, setHedgePositions] = useState<any>(null);
  const [hedgeRecommendations, setHedgeRecommendations] = useState<any[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [featureInfo, setFeatureInfo] = useState<any>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [dashRes, gapRes, scenRes, resultRes, hedgeRes, recRes] = await Promise.all([
        almApi.getDashboard(),
        almApi.getGapAnalysis(),
        almApi.getScenarios(),
        almApi.getScenarioResults(),
        almApi.getHedgePositions(),
        almApi.getHedgeRecommendations()
      ]);
      setDashboard(dashRes.data);
      setGapAnalysis(gapRes.data);
      setScenarios(scenRes.data.scenarios || []);
      setScenarioResults(resultRes.data);
      setHedgePositions(hedgeRes.data);
      setHedgeRecommendations(recRes.data.recommendations || []);
    } catch (error) {
      console.error('ALM data load error:', error);
    } finally {
      setLoading(false);
    }
  };

  const openFeatureModal = async (featureId: string) => {
    try {
      const res = await almApi.getFeatureDescription(featureId);
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

  // Gap chart data
  const gapChartData = gapAnalysis?.gaps?.map((g: any) => ({
    name: g.bucket,
    '자산': g.assets?.total / 100000000 || 0,
    '부채': -(g.liabilities?.total / 100000000 || 0),
    '갭': g.gaps?.repricing_gap / 100000000 || 0
  })) || [];

  // Instrument distribution
  const instrumentDist = hedgePositions?.by_instrument?.map((i: any) => ({
    name: i.instrument_type,
    value: i.total_notional / 100000000,
    color: i.instrument_type === 'IRS' ? COLORS.primary :
           i.instrument_type === 'FRA' ? COLORS.success :
           i.instrument_type === 'CAP' ? COLORS.warning : COLORS.danger
  })) || [];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            ALM (금리 리스크 관리)
            <HelpButton onClick={() => openFeatureModal('alm_overview')} />
          </h1>
          <p className="text-sm text-gray-500 mt-1">금리 갭 분석, 시나리오 분석, 헷지 전략</p>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-5 gap-4">
        <StatCard
          title="총 금리갭"
          value={formatAmount(dashboard?.gap_summary?.total_repricing_gap || 0, 'billion')}
          subtitle={dashboard?.gap_summary?.risk_assessment}
          icon={<BarChart3 size={24} />}
          color={dashboard?.gap_summary?.total_repricing_gap > 0 ? 'green' : 'red'}
        />
        <StatCard
          title="NIM 민감도"
          value={`${dashboard?.gap_summary?.nim_sensitivity_100bp || 0}bp`}
          subtitle="100bp 충격시"
          icon={<Percent size={24} />}
          color={Math.abs(dashboard?.gap_summary?.nim_sensitivity_100bp || 0) > 10 ? 'red' : 'green'}
        />
        <StatCard
          title="EVE 민감도"
          value={formatAmount(dashboard?.gap_summary?.eve_sensitivity_100bp || 0, 'billion')}
          subtitle="100bp 충격시"
          icon={<DollarSign size={24} />}
          color={Math.abs(dashboard?.gap_summary?.eve_sensitivity_100bp || 0) > 1000 ? 'red' : 'green'}
        />
        <StatCard
          title="헷지 포지션"
          value={formatAmount(hedgePositions?.summary?.total_notional || 0, 'trillion')}
          subtitle={`${hedgePositions?.summary?.position_count || 0}건`}
          icon={<Shield size={24} />}
          color="blue"
        />
        <StatCard
          title="헷지 제안"
          value={hedgeRecommendations.length}
          subtitle="건"
          icon={<AlertTriangle size={24} />}
          color="yellow"
        />
      </div>

      {/* Gap Analysis */}
      <Card
        title="금리 갭 분석"
        headerAction={<HelpButton onClick={() => openFeatureModal('gap_analysis')} size="sm" />}
      >
        <GroupedBarChart
          data={gapChartData}
          bars={[
            { key: '자산', name: '자산(억)', color: COLORS.primary },
            { key: '부채', name: '부채(억)', color: COLORS.danger },
            { key: '갭', name: '갭(억)', color: COLORS.success }
          ]}
          xAxisKey="name"
          height={300}
          showLegend
        />
      </Card>

      {/* Gap Details Table */}
      <Card title="만기별 금리 갭 상세">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 text-left">만기구간</th>
                <th className="px-3 py-2 text-right">고정금리자산</th>
                <th className="px-3 py-2 text-right">변동금리자산</th>
                <th className="px-3 py-2 text-right">총자산</th>
                <th className="px-3 py-2 text-right">고정금리부채</th>
                <th className="px-3 py-2 text-right">변동금리부채</th>
                <th className="px-3 py-2 text-right">총부채</th>
                <th className="px-3 py-2 text-right">재조정갭</th>
                <th className="px-3 py-2 text-right">누적갭</th>
                <th className="px-3 py-2 text-right">NIM민감도</th>
              </tr>
            </thead>
            <tbody>
              {gapAnalysis?.gaps?.map((gap: any) => (
                <tr key={gap.gap_id} className="border-b hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium">{gap.bucket}</td>
                  <td className="px-3 py-2 text-right">{formatAmount(gap.assets?.fixed || 0, 'billion')}</td>
                  <td className="px-3 py-2 text-right">{formatAmount(gap.assets?.floating || 0, 'billion')}</td>
                  <td className="px-3 py-2 text-right font-semibold">{formatAmount(gap.assets?.total || 0, 'billion')}</td>
                  <td className="px-3 py-2 text-right">{formatAmount(gap.liabilities?.fixed || 0, 'billion')}</td>
                  <td className="px-3 py-2 text-right">{formatAmount(gap.liabilities?.floating || 0, 'billion')}</td>
                  <td className="px-3 py-2 text-right font-semibold">{formatAmount(gap.liabilities?.total || 0, 'billion')}</td>
                  <td className={`px-3 py-2 text-right font-semibold ${
                    gap.gaps?.repricing_gap > 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {formatAmount(gap.gaps?.repricing_gap || 0, 'billion')}
                  </td>
                  <td className="px-3 py-2 text-right">{formatAmount(gap.gaps?.cumulative_gap || 0, 'billion')}</td>
                  <td className="px-3 py-2 text-right">{gap.sensitivity?.nim_100bp?.toFixed(2)}bp</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Scenario Analysis and Hedge Positions */}
      <div className="grid grid-cols-2 gap-6">
        {/* Scenario Results */}
        <Card title="금리 시나리오 분석">
          <div className="space-y-3">
            {scenarioResults?.results?.slice(0, 6).map((result: any) => (
              <div key={result.result_id} className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-gray-900">{result.scenario_name}</span>
                  <span className={`px-2 py-0.5 rounded text-xs ${
                    result.scenario_type === 'PARALLEL_UP' || result.scenario_type === 'SHORT_UP' ? 'bg-red-100 text-red-700' :
                    result.scenario_type === 'PARALLEL_DOWN' || result.scenario_type === 'SHORT_DOWN' ? 'bg-green-100 text-green-700' :
                    'bg-blue-100 text-blue-700'
                  }`}>
                    {result.scenario_type}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-sm">
                  <div>
                    <p className="text-xs text-gray-500">NIM 변동</p>
                    <p className={`font-semibold ${result.nim_impact?.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {result.nim_impact?.change >= 0 ? '+' : ''}{result.nim_impact?.change?.toFixed(2)}%
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">EVE 변동</p>
                    <p className={`font-semibold ${result.eve_impact?.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatAmount(result.eve_impact?.change || 0, 'billion')}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">자본 영향</p>
                    <p className={`font-semibold ${result.capital_impact >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatAmount(result.capital_impact || 0, 'billion')}
                    </p>
                  </div>
                </div>
                <div className="mt-2 flex items-center text-xs text-gray-500">
                  <span>단기: {result.rate_shock?.short_term_bp >= 0 ? '+' : ''}{result.rate_shock?.short_term_bp}bp</span>
                  <span className="mx-2">|</span>
                  <span>장기: {result.rate_shock?.long_term_bp >= 0 ? '+' : ''}{result.rate_shock?.long_term_bp}bp</span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Hedge Positions */}
        <Card
          title="헷지 포지션"
          headerAction={<HelpButton onClick={() => openFeatureModal('hedge_strategy')} size="sm" />}
        >
          <div className="mb-4">
            <DonutChart
              data={instrumentDist}
              height={180}
              innerRadius={40}
              outerRadius={70}
            />
          </div>

          <div className="space-y-3">
            {hedgePositions?.positions?.slice(0, 5).map((pos: any) => (
              <div key={pos.position_id} className="p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-gray-900">{pos.instrument_type}</span>
                  <span className={`text-sm font-semibold ${pos.mtm_value >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatAmount(pos.mtm_value || 0, 'million')}
                  </span>
                </div>
                <div className="flex justify-between text-xs text-gray-500">
                  <span>명목: {formatAmount(pos.notional_amount || 0, 'billion')}</span>
                  <span>{pos.pay_leg} ↔ {pos.receive_leg}</span>
                  <span>만기: {pos.maturity_date}</span>
                </div>
                <div className="mt-2 flex items-center justify-between text-xs">
                  <span className="text-gray-500">DV01: {pos.dv01?.toFixed(0)}만원</span>
                  <span className={`font-medium ${
                    pos.hedge_effectiveness >= 0.8 ? 'text-green-600' : 'text-yellow-600'
                  }`}>
                    효과성: {formatPercent(pos.hedge_effectiveness * 100)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Hedge Recommendations */}
      <Card title="헷지 제안">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 text-center">우선순위</th>
                <th className="px-3 py-2 text-left">만기구간</th>
                <th className="px-3 py-2 text-right">현재 갭</th>
                <th className="px-3 py-2 text-right">목표 갭</th>
                <th className="px-3 py-2 text-left">추천 상품</th>
                <th className="px-3 py-2 text-right">추천 규모</th>
                <th className="px-3 py-2 text-right">예상 비용</th>
                <th className="px-3 py-2 text-right">예상 효과</th>
                <th className="px-3 py-2 text-right">순효과</th>
                <th className="px-3 py-2 text-left">근거</th>
              </tr>
            </thead>
            <tbody>
              {hedgeRecommendations.map((rec: any) => (
                <tr key={rec.recommendation_id} className="border-b hover:bg-gray-50">
                  <td className="px-3 py-2 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                      rec.priority === 1 ? 'bg-red-100 text-red-700' :
                      rec.priority === 2 ? 'bg-yellow-100 text-yellow-700' :
                      'bg-blue-100 text-blue-700'
                    }`}>
                      {rec.priority}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-medium">{rec.gap_bucket}</td>
                  <td className="px-3 py-2 text-right">{formatAmount(rec.current_gap || 0, 'billion')}</td>
                  <td className="px-3 py-2 text-right">{formatAmount(rec.target_gap || 0, 'billion')}</td>
                  <td className="px-3 py-2">{rec.recommended_instrument}</td>
                  <td className="px-3 py-2 text-right font-semibold">{formatAmount(rec.recommended_notional || 0, 'billion')}</td>
                  <td className="px-3 py-2 text-right text-red-600">{formatAmount(rec.expected_cost || 0, 'million')}</td>
                  <td className="px-3 py-2 text-right text-green-600">{formatAmount(rec.expected_benefit || 0, 'million')}</td>
                  <td className={`px-3 py-2 text-right font-semibold ${
                    rec.net_benefit > 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {formatAmount(rec.net_benefit || 0, 'million')}
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-600 max-w-xs truncate" title={rec.rationale}>
                    {rec.rationale}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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
