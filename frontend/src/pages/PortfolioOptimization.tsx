import React, { useEffect, useState } from 'react';
import {
  Layers,
  TrendingUp,
  Target,
  BarChart3,
  PieChart,
  ArrowRight
} from 'lucide-react';
import { Card, StatCard, GroupedBarChart, DonutChart, TrendChart, COLORS, FeatureModal, HelpButton } from '../components';
import { portfolioOptimizationApi } from '../utils/api';
import { formatAmount, formatPercent } from '../utils/format';

const REGIONS = [
  { value: '', label: '전체 지역' },
  { value: 'CAPITAL', label: '수도권' },
  { value: 'DAEGU_GB', label: '대구경북' },
  { value: 'BUSAN_GN', label: '부산경남' },
];

export default function PortfolioOptimization() {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>(null);
  const [optimizationRuns, setOptimizationRuns] = useState<any[]>([]);
  const [latestRecommendations, setLatestRecommendations] = useState<any[]>([]);
  const [currentVsOptimal, setCurrentVsOptimal] = useState<any>(null);
  const [constraints, setConstraints] = useState<any>(null);
  const [selectedRun, setSelectedRun] = useState<any>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [featureInfo, setFeatureInfo] = useState<any>(null);
  const [region, setRegion] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    loadRegionData();
  }, [region]);

  const loadData = async () => {
    try {
      const [dashRes, runsRes, recsRes, compRes, constRes] = await Promise.all([
        portfolioOptimizationApi.getDashboard(),
        portfolioOptimizationApi.getOptimizationRuns(),
        portfolioOptimizationApi.getLatestRecommendations(),
        portfolioOptimizationApi.getCurrentVsOptimal(),
        portfolioOptimizationApi.getConstraints()
      ]);
      setDashboard(dashRes.data);
      setOptimizationRuns(runsRes.data.runs || []);
      setLatestRecommendations(recsRes.data.recommendations || []);
      setCurrentVsOptimal(compRes.data);
      setConstraints(constRes.data);
    } catch (error) {
      console.error('Portfolio optimization data load error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadRegionData = async () => {
    try {
      const r = region || undefined;
      const [recsRes, compRes] = await Promise.all([
        portfolioOptimizationApi.getLatestRecommendations(r),
        portfolioOptimizationApi.getCurrentVsOptimal(r),
      ]);
      setLatestRecommendations(recsRes.data.recommendations || []);
      setCurrentVsOptimal(compRes.data);
    } catch (error) {
      console.error('Region data load error:', error);
    }
  };

  const loadRunDetail = async (runId: string) => {
    try {
      const res = await portfolioOptimizationApi.getOptimizationResult(runId);
      setSelectedRun(res.data);
    } catch (error) {
      console.error('Optimization result load error:', error);
    }
  };

  const openFeatureModal = async (featureId: string) => {
    try {
      const res = await portfolioOptimizationApi.getFeatureDescription(featureId);
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

  // Chart data for current vs optimal - convert exposure to allocation percentage
  const totalCurrentExposure = currentVsOptimal?.comparison?.reduce((sum: number, c: any) => sum + (c.current_exposure || 0), 0) || 1;
  const totalOptimalExposure = currentVsOptimal?.comparison?.reduce((sum: number, c: any) => sum + (c.optimal_exposure || 0), 0) || 1;

  const comparisonData = currentVsOptimal?.comparison?.map((c: any) => ({
    name: c.segment_name?.substring(0, 6) || c.segment_id,
    현재: ((c.current_exposure || 0) / totalCurrentExposure * 100).toFixed(1),
    최적: ((c.optimal_exposure || 0) / totalOptimalExposure * 100).toFixed(1)
  })) || [];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            포트폴리오 최적화
            <HelpButton onClick={() => openFeatureModal('optimization_overview')} />
          </h1>
          <p className="text-sm text-gray-500 mt-1">효율적 프론티어 기반 최적 자산배분 도출</p>
        </div>
        <select
          value={region}
          onChange={(e) => setRegion(e.target.value)}
          className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {REGIONS.map(r => (
            <option key={r.value} value={r.value}>{r.label}</option>
          ))}
        </select>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-5 gap-4">
        <StatCard
          title="현재 평균 RAROC"
          value={formatPercent(dashboard?.efficiency_gap?.current_avg_raroc || 0)}
          icon={<TrendingUp size={24} />}
          color={(dashboard?.efficiency_gap?.current_avg_raroc || 0) >= 15 ? 'green' : 'yellow'}
        />
        <StatCard
          title="최적 평균 RAROC"
          value={formatPercent(dashboard?.efficiency_gap?.optimal_avg_raroc || 0)}
          icon={<Target size={24} />}
          color="green"
        />
        <StatCard
          title="RAROC 개선 여력"
          value={formatPercent(dashboard?.efficiency_gap?.improvement_potential || 0)}
          icon={<TrendingUp size={24} />}
          color="blue"
        />
        <StatCard
          title="조정 필요 세그먼트"
          value={dashboard?.segments_needing_adjustment || 0}
          subtitle="개"
          icon={<BarChart3 size={24} />}
          color="yellow"
        />
        <StatCard
          title="리밸런싱 제안"
          value={latestRecommendations.length}
          subtitle="건"
          icon={<Layers size={24} />}
          color="blue"
        />
      </div>

      {/* Current vs Optimal Allocation */}
      <Card
        title="현재 vs 최적 배분 비교"
        headerAction={<HelpButton onClick={() => openFeatureModal('efficient_frontier')} size="sm" />}
      >
        <GroupedBarChart
          data={comparisonData}
          bars={[
            { key: '현재', name: '현재 배분(%)', color: COLORS.secondary },
            { key: '최적', name: '최적 배분(%)', color: COLORS.primary }
          ]}
          xAxisKey="name"
          height={300}
          showLegend
        />
      </Card>

      {/* Rebalancing Recommendations */}
      <Card
        title="리밸런싱 제안"
        headerAction={<HelpButton onClick={() => openFeatureModal('rebalancing')} size="sm" />}
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 text-left">세그먼트</th>
                <th className="px-3 py-2 text-right">현재 익스포저</th>
                <th className="px-3 py-2 text-center"></th>
                <th className="px-3 py-2 text-right">최적 익스포저</th>
                <th className="px-3 py-2 text-right">변경률</th>
                <th className="px-3 py-2 text-left">액션</th>
                <th className="px-3 py-2 text-right">RAROC 개선</th>
                <th className="px-3 py-2 text-center">우선순위</th>
              </tr>
            </thead>
            <tbody>
              {latestRecommendations.map((rec: any, idx: number) => (
                <tr key={idx} className="border-b hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium">{rec.segment_name}</td>
                  <td className="px-3 py-2 text-right">{formatAmount(rec.current_exposure, 'billion')}</td>
                  <td className="px-3 py-2 text-center">
                    <ArrowRight size={16} className="text-gray-400" />
                  </td>
                  <td className="px-3 py-2 text-right font-semibold">{formatAmount(rec.optimal_exposure, 'billion')}</td>
                  <td className={`px-3 py-2 text-right font-semibold ${
                    rec.change_pct > 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {rec.change_pct > 0 ? '+' : ''}{formatPercent(rec.change_pct)}
                  </td>
                  <td className="px-3 py-2">
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      rec.recommendation === 'INCREASE' ? 'bg-green-100 text-green-700' :
                      rec.recommendation === 'DECREASE' ? 'bg-red-100 text-red-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {rec.recommendation}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right text-green-600">
                    {rec.optimal_raroc > rec.current_raroc ? '+' : ''}{formatPercent((rec.optimal_raroc || 0) - (rec.current_raroc || 0))}
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      rec.priority <= 2 ? 'bg-red-100 text-red-700' :
                      rec.priority <= 4 ? 'bg-yellow-100 text-yellow-700' :
                      'bg-blue-100 text-blue-700'
                    }`}>
                      {rec.priority}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Constraints and Optimization History */}
      <div className="grid grid-cols-2 gap-6">
        {/* Constraints */}
        <Card title="최적화 제약조건">
          <div className="space-y-3">
            {/* 기본 제약조건 */}
            {constraints?.default_constraints && (
              <div className="p-3 bg-blue-50 rounded-lg mb-4">
                <p className="text-sm font-medium text-blue-900 mb-2">기본 제약조건</p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-600">BIS 비율 최소</span>
                    <span className="font-mono">{formatPercent(constraints.default_constraints.bis_ratio_min * 100)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">CET1 비율 최소</span>
                    <span className="font-mono">{formatPercent(constraints.default_constraints.cet1_ratio_min * 100)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">산업별 HHI 최대</span>
                    <span className="font-mono">{formatPercent(constraints.default_constraints.hhi_industry_max * 100)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">단일차주 최대</span>
                    <span className="font-mono">{formatPercent(constraints.default_constraints.single_borrower_max * 100)}</span>
                  </div>
                </div>
              </div>
            )}
            {/* 규제 한도 */}
            {(constraints?.regulatory_limits || []).slice(0, 5).map((con: any, i: number) => (
              <div key={i} className="p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-gray-900">{con.limit_type}</span>
                  <span className="text-xs text-gray-500">{con.dimension_type}</span>
                </div>
                <div className="flex justify-between mt-2 text-xs text-gray-500">
                  <span>한도: {formatAmount(con.limit_amount, 'billion')}</span>
                  <span>
                    경고: {formatPercent(con.warning_level * 100)} / 위험: {formatPercent(con.alert_level * 100)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Optimization History */}
        <Card title="최적화 실행 이력">
          <div className="space-y-3">
            {optimizationRuns.slice(0, 6).map((run: any) => (
              <div
                key={run.run_id}
                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                  selectedRun?.run_info?.run_id === run.run_id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 bg-gray-50 hover:border-blue-300'
                }`}
                onClick={() => loadRunDetail(run.run_id)}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-gray-900">{run.run_date}</span>
                  <span className={`px-2 py-0.5 rounded text-xs ${
                    run.status === 'COMPLETED' ? 'bg-green-100 text-green-700' :
                    run.status === 'RUNNING' ? 'bg-blue-100 text-blue-700' :
                    'bg-red-100 text-red-700'
                  }`}>
                    {run.status}
                  </span>
                </div>
                <p className="text-sm text-gray-600">{run.optimization_type}</p>
                <div className="flex justify-between mt-2 text-xs">
                  <span className="text-gray-500">목표값: {run.objective_value?.toFixed(2)}</span>
                  <span className="text-green-600">개선율: {formatPercent(run.improvement_pct || 0)}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Selected Run Detail */}
      {selectedRun && (
        <Card
          title={`최적화 결과 상세: ${selectedRun.run_info?.run_date}`}
          headerAction={
            <button
              onClick={() => setSelectedRun(null)}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              닫기
            </button>
          }
        >
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">최적화 유형</p>
              <p className="text-lg font-bold text-gray-900">{selectedRun.run_info?.optimization_type}</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">목표값</p>
              <p className="text-lg font-bold text-green-600">{selectedRun.run_info?.objective_value?.toFixed(2)}</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">상태</p>
              <p className="text-lg font-bold text-gray-900">{selectedRun.run_info?.status}</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">개선율</p>
              <p className="text-lg font-bold text-blue-600">{formatPercent(selectedRun.run_info?.improvement_pct || 0)}</p>
            </div>
          </div>

          {selectedRun.allocations && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">세그먼트별 최적 배분</h4>
              <div className="grid grid-cols-4 gap-3">
                {selectedRun.allocations.map((alloc: any) => (
                  <div key={alloc.allocation_id} className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-sm font-medium text-gray-900">{alloc.segment_name}</p>
                    <div className="flex items-baseline justify-between mt-2">
                      <span className="text-xs text-gray-500">변경률</span>
                      <span className={`text-lg font-bold ${alloc.change_pct > 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {alloc.change_pct > 0 ? '+' : ''}{formatPercent(alloc.change_pct)}
                      </span>
                    </div>
                    <div className="flex items-baseline justify-between mt-1">
                      <span className="text-xs text-gray-500">최적 RAROC</span>
                      <span className="text-sm font-semibold text-green-600">{formatPercent(alloc.optimal_raroc)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
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
