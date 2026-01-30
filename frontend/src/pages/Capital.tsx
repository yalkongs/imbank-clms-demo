import React, { useEffect, useState } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Target,
  AlertTriangle,
  Calculator,
  PieChart as PieChartIcon
} from 'lucide-react';
import { Card, StatCard, GaugeCard, TrendChart, DonutChart, GroupedBarChart, COLORS } from '../components';
import { capitalApi } from '../utils/api';
import { formatAmount, formatPercent, formatNumber, formatInputAmount, parseFormattedNumber } from '../utils/format';

export default function Capital() {
  const [loading, setLoading] = useState(true);
  const [position, setPosition] = useState<any>(null);
  const [trend, setTrend] = useState<any[]>([]);
  const [budget, setBudget] = useState<any>(null);
  const [efficiency, setEfficiency] = useState<any>(null);
  const [simulation, setSimulation] = useState<any>(null);

  // 시뮬레이션 입력
  const [simInput, setSimInput] = useState({
    amount: 100000000000,
    pd: 0.02,
    lgd: 0.45
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [posRes, trendRes, budgetRes, effRes] = await Promise.all([
        capitalApi.getPosition(),
        capitalApi.getTrend(12),
        capitalApi.getBudget(),
        capitalApi.getEfficiency()
      ]);
      setPosition(posRes.data);
      setTrend(trendRes.data || []);
      setBudget(budgetRes.data);
      setEfficiency(effRes.data);
    } catch (error) {
      console.error('Capital data load error:', error);
    } finally {
      setLoading(false);
    }
  };

  const [simLoading, setSimLoading] = useState(false);
  const [debounceTimer, setDebounceTimer] = useState<NodeJS.Timeout | null>(null);

  const runSimulation = async (params?: typeof simInput) => {
    const currentParams = params || simInput;
    setSimLoading(true);
    try {
      const response = await capitalApi.simulate(currentParams);
      setSimulation(response.data);
    } catch (error) {
      console.error('Simulation error:', error);
    } finally {
      setSimLoading(false);
    }
  };

  // 디바운스된 시뮬레이션
  const handleSimInputChange = (newInput: typeof simInput) => {
    setSimInput(newInput);

    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }

    const timer = setTimeout(() => {
      runSimulation(newInput);
    }, 300);
    setDebounceTimer(timer);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // RWA 구성 데이터
  const rwaComposition = [
    { name: '신용RWA', value: position?.credit_rwa || 0, color: COLORS.primary },
    { name: '시장RWA', value: position?.market_rwa || 0, color: COLORS.secondary },
    { name: '운영RWA', value: position?.operational_rwa || 0, color: COLORS.accent }
  ];

  // 예산 대비 실적 데이터
  const budgetData = budget?.by_segment?.map((seg: any) => ({
    name: seg.segment,
    예산: seg.rwa_budget / 100000000,
    실적: seg.rwa_actual / 100000000
  })) || [];

  return (
    <div className="space-y-6">
      {/* 페이지 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">자본관리</h1>
          <p className="text-sm text-gray-500 mt-1">자본비율 모니터링 및 RWA 예산 관리</p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="px-3 py-1 bg-green-100 text-green-700 text-sm rounded-full">
            자본적정성 양호
          </span>
        </div>
      </div>

      {/* 핵심 자본비율 */}
      <div className="grid grid-cols-4 gap-4">
        <GaugeCard
          title="BIS 비율"
          value={position?.bis_ratio || 0}
          max={20}
          min={8}
          target={13}
          warning={11}
          critical={10.5}
        />
        <GaugeCard
          title="Tier1 비율"
          value={position?.tier1_ratio || 0}
          max={18}
          min={6}
          target={11}
          warning={9}
          critical={8.5}
        />
        <GaugeCard
          title="CET1 비율"
          value={position?.cet1_ratio || 0}
          max={16}
          min={4}
          target={9}
          warning={7.5}
          critical={7}
        />
        <GaugeCard
          title="레버리지 비율"
          value={position?.leverage_ratio || 0}
          max={10}
          min={2}
          target={5}
          warning={4}
          critical={3}
        />
      </div>

      {/* 자본 현황 상세 */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="총 자기자본"
          value={formatAmount(position?.total_capital || 0, 'billion')}
          icon={<PieChartIcon size={24} />}
          color="blue"
        />
        <StatCard
          title="Tier1 자본"
          value={formatAmount(position?.tier1_capital || 0, 'billion')}
          icon={<TrendingUp size={24} />}
          color="blue"
        />
        <StatCard
          title="총 RWA"
          value={formatAmount(position?.total_rwa || 0, 'billion')}
          icon={<Target size={24} />}
          color="yellow"
        />
        <StatCard
          title="자본여력"
          value={formatAmount((position?.total_capital || 0) - (position?.total_rwa || 0) * 0.105, 'billion')}
          subtitle="규제최소 대비"
          icon={<AlertTriangle size={24} />}
          color="green"
        />
      </div>

      {/* 차트 영역 */}
      <div className="grid grid-cols-3 gap-6">
        {/* 자본비율 추이 */}
        <Card title="자본비율 추이" className="col-span-2">
          <TrendChart
            data={trend}
            lines={[
              { key: 'bis_ratio', name: 'BIS비율', color: COLORS.primary },
              { key: 'tier1_ratio', name: 'Tier1비율', color: COLORS.secondary },
              { key: 'cet1_ratio', name: 'CET1비율', color: COLORS.accent }
            ]}
            xAxisKey="period"
            referenceLines={[
              { y: 10.5, label: '규제최소 10.5%', color: COLORS.danger }
            ]}
            height={300}
          />
        </Card>

        {/* RWA 구성 */}
        <Card title="RWA 구성">
          <DonutChart
            data={rwaComposition}
            height={300}
            innerRadius={60}
            outerRadius={100}
            centerValue={formatAmount(position?.total_rwa || 0, 'billion')}
            centerText="총 RWA"
          />
        </Card>
      </div>

      {/* 예산 관리 */}
      <div className="grid grid-cols-2 gap-6">
        {/* 세그먼트별 RWA 예산 */}
        <Card title="세그먼트별 RWA 예산 vs 실적">
          <GroupedBarChart
            data={budgetData}
            bars={[
              { key: '예산', name: '예산', color: COLORS.secondary },
              { key: '실적', name: '실적', color: COLORS.primary }
            ]}
            xAxisKey="name"
            height={280}
          />
        </Card>

        {/* 예산 소진율 */}
        <Card title="예산 소진 현황">
          <div className="space-y-4">
            {budget?.by_segment?.map((seg: any, index: number) => {
              const utilization = (seg.rwa_actual / seg.rwa_budget) * 100;
              return (
                <div key={index} className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-700">{seg.segment}</span>
                    <span className={`font-medium ${
                      utilization >= 100 ? 'text-red-600' :
                      utilization >= 90 ? 'text-yellow-600' :
                      'text-green-600'
                    }`}>
                      {utilization.toFixed(1)}%
                    </span>
                  </div>
                  <div className="relative h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`absolute left-0 top-0 h-full rounded-full transition-all duration-500 ${
                        utilization >= 100 ? 'bg-red-500' :
                        utilization >= 90 ? 'bg-yellow-500' :
                        'bg-green-500'
                      }`}
                      style={{ width: `${Math.min(utilization, 100)}%` }}
                    />
                    <div
                      className="absolute top-0 w-0.5 h-full bg-gray-800"
                      style={{ left: '90%' }}
                      title="경고선 90%"
                    />
                  </div>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>실적: {formatAmount(seg.rwa_actual, 'billion')}</span>
                    <span>예산: {formatAmount(seg.rwa_budget, 'billion')}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* 자본 시뮬레이션 */}
      <Card title="신규 익스포저 영향 시뮬레이션" headerAction={
        simLoading ? (
          <div className="flex items-center text-sm text-blue-600">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
            계산 중...
          </div>
        ) : null
      }>
        <div className="grid grid-cols-2 gap-6">
          {/* 입력 */}
          <div className="space-y-4">
            <h4 className="text-sm font-medium text-gray-700">시뮬레이션 조건 <span className="text-xs text-blue-500 font-normal">(입력 시 자동 계산)</span></h4>
            <div>
              <label className="block text-sm text-gray-600 mb-1">신규 익스포저</label>
              <input
                type="text"
                value={formatInputAmount(simInput.amount)}
                onChange={(e) => {
                  const newAmount = parseFormattedNumber(e.target.value);
                  handleSimInputChange({...simInput, amount: newAmount});
                }}
                className="input text-right font-mono"
              />
              <p className="text-xs text-gray-500 mt-1 text-right">{formatAmount(simInput.amount, 'billion')}</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-600 mb-1">PD (%)</label>
                <input
                  type="number"
                  step="0.001"
                  value={simInput.pd * 100}
                  onChange={(e) => handleSimInputChange({...simInput, pd: Number(e.target.value) / 100})}
                  className="input text-right font-mono"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">LGD (%)</label>
                <input
                  type="number"
                  step="0.01"
                  value={simInput.lgd * 100}
                  onChange={(e) => handleSimInputChange({...simInput, lgd: Number(e.target.value) / 100})}
                  className="input text-right font-mono"
                />
              </div>
            </div>
          </div>

          {/* 결과 */}
          <div className="space-y-4">
            <h4 className="text-sm font-medium text-gray-700">시뮬레이션 결과</h4>
            {simulation ? (
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">추가 RWA</p>
                  <p className="text-xl font-bold text-gray-900">
                    {formatAmount(simulation.additional_rwa || 0, 'billion')}
                  </p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">변경 후 BIS비율</p>
                  <p className={`text-xl font-bold ${
                    simulation.new_bis_ratio >= 10.5 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {formatPercent(simulation.new_bis_ratio)}
                  </p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">BIS비율 변화</p>
                  <p className={`text-xl font-bold ${
                    simulation.bis_ratio_change >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {simulation.bis_ratio_change >= 0 ? '+' : ''}{formatPercent(simulation.bis_ratio_change)}
                  </p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">자본여력 변화</p>
                  <p className="text-xl font-bold text-gray-900">
                    {formatAmount(simulation.capital_buffer_change || 0, 'billion')}
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-40 text-gray-400">
                시뮬레이션을 실행하세요
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* 자본 효율성 분석 */}
      <div className="grid grid-cols-2 gap-6">
        {/* 산업별 RAROC */}
        <Card title="산업별 자본 효율성 (RAROC)">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="px-4 py-3 text-left font-semibold text-gray-700">산업</th>
                  <th className="px-4 py-3 text-right font-semibold text-gray-700">익스포저</th>
                  <th className="px-4 py-3 text-right font-semibold text-gray-700">RAROC</th>
                  <th className="px-4 py-3 text-center font-semibold text-gray-700">효율성</th>
                </tr>
              </thead>
              <tbody>
                {efficiency?.by_industry?.map((seg: any, index: number) => (
                  <tr key={index} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{seg.segment}</td>
                    <td className="px-4 py-3 text-right font-mono">
                      {formatAmount(seg.exposure, 'billion')}
                    </td>
                    <td className={`px-4 py-3 text-right font-mono font-bold ${
                      seg.raroc >= 18 ? 'text-green-600' :
                      seg.raroc >= 15 ? 'text-blue-600' :
                      seg.raroc >= 12 ? 'text-yellow-600' :
                      'text-red-600'
                    }`}>
                      {formatPercent(seg.raroc)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        seg.raroc >= 18 ? 'bg-green-100 text-green-800' :
                        seg.raroc >= 15 ? 'bg-blue-100 text-blue-800' :
                        seg.raroc >= 12 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {seg.raroc >= 18 ? '우수' :
                         seg.raroc >= 15 ? '양호' :
                         seg.raroc >= 12 ? '보통' : '미흡'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* 등급별 RAROC */}
        <Card title="등급별 자본 효율성 (RAROC)">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="px-4 py-3 text-left font-semibold text-gray-700">등급</th>
                  <th className="px-4 py-3 text-right font-semibold text-gray-700">익스포저</th>
                  <th className="px-4 py-3 text-right font-semibold text-gray-700">RAROC</th>
                  <th className="px-4 py-3 text-center font-semibold text-gray-700">효율성</th>
                </tr>
              </thead>
              <tbody>
                {efficiency?.by_rating?.map((seg: any, index: number) => (
                  <tr key={index} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{seg.segment}</td>
                    <td className="px-4 py-3 text-right font-mono">
                      {formatAmount(seg.exposure, 'billion')}
                    </td>
                    <td className={`px-4 py-3 text-right font-mono font-bold ${
                      seg.raroc >= 18 ? 'text-green-600' :
                      seg.raroc >= 15 ? 'text-blue-600' :
                      seg.raroc >= 12 ? 'text-yellow-600' :
                      'text-red-600'
                    }`}>
                      {formatPercent(seg.raroc)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        seg.raroc >= 18 ? 'bg-green-100 text-green-800' :
                        seg.raroc >= 15 ? 'bg-blue-100 text-blue-800' :
                        seg.raroc >= 12 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {seg.raroc >= 18 ? '우수' :
                         seg.raroc >= 15 ? '양호' :
                         seg.raroc >= 12 ? '보통' : '미흡'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
