import React, { useEffect, useState } from 'react';
import {
  Target,
  TrendingUp,
  TrendingDown,
  Activity,
  Calendar,
  Settings,
  Play
} from 'lucide-react';
import { Card, StatCard, GroupedBarChart, TrendChart, COLORS, FeatureModal, HelpButton } from '../components';
import { dynamicLimitsApi } from '../utils/api';
import { formatAmount, formatPercent } from '../utils/format';

export default function DynamicLimits() {
  const [loading, setLoading] = useState(true);
  const [economicCycle, setEconomicCycle] = useState<any>(null);
  const [rules, setRules] = useState<any[]>([]);
  const [adjustments, setAdjustments] = useState<any[]>([]);
  const [currentStatus, setCurrentStatus] = useState<any[]>([]);
  const [simulation, setSimulation] = useState<any>(null);
  const [simParams, setSimParams] = useState({ gdp_growth_shock: -2, interest_rate_shock: 1 });
  const [modalOpen, setModalOpen] = useState(false);
  const [featureInfo, setFeatureInfo] = useState<any>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [cycleRes, rulesRes, adjRes, statusRes] = await Promise.all([
        dynamicLimitsApi.getEconomicCycle(),
        dynamicLimitsApi.getRules(),
        dynamicLimitsApi.getAdjustments({ months: 12 }),
        dynamicLimitsApi.getCurrentStatus()
      ]);
      setEconomicCycle(cycleRes.data);
      setRules(rulesRes.data.rules || []);
      setAdjustments(adjRes.data.adjustments || []);
      setCurrentStatus(statusRes.data.status || []);
    } catch (error) {
      console.error('Dynamic limits data load error:', error);
    } finally {
      setLoading(false);
    }
  };

  const runSimulation = async () => {
    try {
      const res = await dynamicLimitsApi.simulate(simParams);
      setSimulation(res.data);
    } catch (error) {
      console.error('Simulation error:', error);
    }
  };

  const openFeatureModal = async (featureId: string) => {
    try {
      const res = await dynamicLimitsApi.getFeatureDescription(featureId);
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

  // API 응답 구조에 맞게 수정: cycles 배열의 첫 번째가 현재
  const currentCycle = economicCycle?.cycles?.[0];
  const cycleHistory = economicCycle?.cycles || [];

  // Chart data for cycle history
  const cycleChartData = cycleHistory.slice(0, 12).map((c: any) => ({
    date: c.reference_date?.substring(0, 7) || c.reference_date,
    'GDP성장률': c.gdp_growth,
    '기준금리': c.interest_rate,
    'CLI': c.confidence_index
  })).reverse();

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            동적 한도 관리
            <HelpButton onClick={() => openFeatureModal('dynamic_limits_overview')} />
          </h1>
          <p className="text-sm text-gray-500 mt-1">경기사이클 연동 자동 한도 조정 시스템</p>
        </div>
      </div>

      {/* Economic Cycle Summary */}
      <div className="grid grid-cols-5 gap-4">
        <StatCard
          title="현재 경기국면"
          value={currentCycle?.cycle_phase || '-'}
          icon={<Activity size={24} />}
          color={
            currentCycle?.cycle_phase === 'EXPANSION' ? 'green' :
            currentCycle?.cycle_phase === 'PEAK' ? 'yellow' :
            currentCycle?.cycle_phase === 'CONTRACTION' ? 'red' : 'blue'
          }
        />
        <StatCard
          title="GDP 성장률"
          value={formatPercent(currentCycle?.gdp_growth || 0)}
          icon={currentCycle?.gdp_growth >= 0 ? <TrendingUp size={24} /> : <TrendingDown size={24} />}
          color={currentCycle?.gdp_growth >= 2 ? 'green' : currentCycle?.gdp_growth >= 0 ? 'yellow' : 'red'}
        />
        <StatCard
          title="기준금리"
          value={formatPercent(currentCycle?.interest_rate || 0)}
          icon={<Target size={24} />}
          color="blue"
        />
        <StatCard
          title="CLI 지수"
          value={(currentCycle?.confidence_index || 100).toFixed(1)}
          subtitle="경기선행지수"
          icon={<Activity size={24} />}
          color={(currentCycle?.confidence_index || 100) >= 100 ? 'green' : 'yellow'}
        />
        <StatCard
          title="신용스프레드"
          value={`${(currentCycle?.credit_spread || 0).toFixed(0)}bp`}
          icon={<TrendingUp size={24} />}
          color={currentCycle?.credit_spread > 200 ? 'red' : 'green'}
        />
      </div>

      {/* Economic Cycle Chart */}
      <Card
        title="경기 사이클 추이"
        headerAction={<HelpButton onClick={() => openFeatureModal('economic_cycle')} size="sm" />}
      >
        <TrendChart
          data={cycleChartData}
          lines={[
            { key: 'GDP성장률', name: 'GDP성장률(%)', color: COLORS.primary },
            { key: '기준금리', name: '기준금리(%)', color: COLORS.warning },
            { key: 'CLI', name: 'CLI지수', color: COLORS.success }
          ]}
          xAxisKey="date"
          height={280}
          showLegend
        />
      </Card>

      {/* Rules and Status */}
      <div className="grid grid-cols-2 gap-6">
        {/* Dynamic Limit Rules */}
        <Card
          title="동적 한도 규칙"
          headerAction={<HelpButton onClick={() => openFeatureModal('trigger_rules')} size="sm" />}
        >
          <div className="space-y-3">
            {rules.map((rule: any) => (
              <div key={rule.rule_id} className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-gray-900">{rule.rule_name}</span>
                  <span className={`px-2 py-0.5 rounded text-xs ${
                    rule.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                  }`}>
                    {rule.is_active ? 'ACTIVE' : 'INACTIVE'}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-gray-500">트리거:</span>
                    <span className="ml-1 font-mono text-xs">{rule.trigger_condition}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">조정:</span>
                    <span className={`ml-1 font-semibold ${
                      rule.adjustment_pct > 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {rule.adjustment_pct > 0 ? '+' : ''}{formatPercent(rule.adjustment_pct)}
                    </span>
                  </div>
                </div>
                {rule.target_dimension && (
                  <p className="text-xs text-gray-500 mt-2">대상: {rule.target_dimension} ({rule.target_limit_type})</p>
                )}
              </div>
            ))}
          </div>
        </Card>

        {/* Current Status by Industry */}
        <Card title="업종별 한도 조정 현황">
          <div className="space-y-3">
            {currentStatus.map((status: any, i: number) => (
              <div key={i} className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-gray-900">{status.industry_name}</span>
                  <span className={`text-sm font-semibold ${
                    status.current_adjustment > 0 ? 'text-green-600' :
                    status.current_adjustment < 0 ? 'text-red-600' : 'text-gray-600'
                  }`}>
                    {status.current_adjustment > 0 ? '+' : ''}{formatPercent(status.current_adjustment)}
                  </span>
                </div>
                <div className="relative h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`absolute left-1/2 h-full ${
                      status.current_adjustment >= 0 ? 'bg-green-500' : 'bg-red-500'
                    }`}
                    style={{
                      width: `${Math.abs(status.current_adjustment) * 2}%`,
                      transform: status.current_adjustment < 0 ? 'translateX(-100%)' : 'none'
                    }}
                  />
                </div>
                <div className="flex justify-between mt-1 text-xs text-gray-500">
                  <span>기준한도: {formatAmount(status.base_limit, 'billion')}</span>
                  <span>조정한도: {formatAmount(status.adjusted_limit, 'billion')}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Simulation */}
      <Card title="한도 조정 시뮬레이션">
        <div className="grid grid-cols-3 gap-6">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">GDP 성장률 충격 (%)</label>
              <input
                type="range"
                min="-5"
                max="5"
                step="0.5"
                value={simParams.gdp_growth_shock}
                onChange={(e) => setSimParams(p => ({ ...p, gdp_growth_shock: parseFloat(e.target.value) }))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>-5%</span>
                <span className="font-semibold">{simParams.gdp_growth_shock}%</span>
                <span>+5%</span>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">금리 충격 (%p)</label>
              <input
                type="range"
                min="-2"
                max="3"
                step="0.25"
                value={simParams.interest_rate_shock}
                onChange={(e) => setSimParams(p => ({ ...p, interest_rate_shock: parseFloat(e.target.value) }))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>-2%p</span>
                <span className="font-semibold">{simParams.interest_rate_shock}%p</span>
                <span>+3%p</span>
              </div>
            </div>
            <button
              onClick={runSimulation}
              className="w-full flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Play size={16} className="mr-2" />
              시뮬레이션 실행
            </button>
          </div>

          <div className="col-span-2">
            {simulation ? (
              <div className="space-y-4">
                <div className="p-4 bg-blue-50 rounded-lg">
                  <p className="text-sm text-blue-800">
                    GDP {simParams.gdp_growth_shock}% 충격, 금리 {simParams.interest_rate_shock}%p 상승 시나리오
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  {simulation.results?.map((r: any, i: number) => (
                    <div key={i} className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-sm font-medium text-gray-900">{r.industry_name}</p>
                      <div className="flex items-baseline justify-between mt-2">
                        <span className="text-xs text-gray-500">조정률</span>
                        <span className={`text-lg font-bold ${
                          r.simulated_adjustment > 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {r.simulated_adjustment > 0 ? '+' : ''}{formatPercent(r.simulated_adjustment)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400">
                <p>시뮬레이션을 실행하면 결과가 표시됩니다</p>
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* Recent Adjustments */}
      <Card title="최근 한도 조정 이력">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 text-left">조정일</th>
                <th className="px-3 py-2 text-left">업종</th>
                <th className="px-3 py-2 text-left">적용규칙</th>
                <th className="px-3 py-2 text-right">조정률</th>
                <th className="px-3 py-2 text-right">기존한도</th>
                <th className="px-3 py-2 text-right">조정한도</th>
                <th className="px-3 py-2 text-left">트리거</th>
              </tr>
            </thead>
            <tbody>
              {adjustments.slice(0, 10).map((adj: any) => (
                <tr key={adj.adjustment_id} className="border-b hover:bg-gray-50">
                  <td className="px-3 py-2">{adj.adjustment_date}</td>
                  <td className="px-3 py-2 font-medium">{adj.industry_name}</td>
                  <td className="px-3 py-2">{adj.rule_name}</td>
                  <td className={`px-3 py-2 text-right font-semibold ${
                    adj.adjustment_pct > 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {adj.adjustment_pct > 0 ? '+' : ''}{formatPercent(adj.adjustment_pct)}
                  </td>
                  <td className="px-3 py-2 text-right">{formatAmount(adj.previous_limit, 'billion')}</td>
                  <td className="px-3 py-2 text-right">{formatAmount(adj.new_limit, 'billion')}</td>
                  <td className="px-3 py-2 text-xs text-gray-500">{adj.trigger_reason}</td>
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
