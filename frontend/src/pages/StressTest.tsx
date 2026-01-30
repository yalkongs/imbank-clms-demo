import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  TrendingDown,
  BarChart3,
  Play,
  Download
} from 'lucide-react';
import { Card, StatCard, Table, Badge, TrendChart, GroupedBarChart, COLORS } from '../components';
import { stressTestApi } from '../utils/api';
import { formatAmount, formatPercent } from '../utils/format';

export default function StressTest() {
  const [loading, setLoading] = useState(true);
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [results, setResults] = useState<any>(null);
  const [resultLoading, setResultLoading] = useState(false);

  useEffect(() => {
    loadScenarios();
  }, []);

  const loadScenarios = async () => {
    try {
      const response = await stressTestApi.getScenarios();
      setScenarios(response.data || []);
      if (response.data?.length > 0) {
        loadResults(response.data[0].scenario_id);
      }
    } catch (error) {
      console.error('Scenarios load error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadResults = async (scenarioId: string) => {
    setSelectedScenario(scenarioId);
    setResultLoading(true);
    try {
      const response = await stressTestApi.getResults(scenarioId);
      setResults(response.data);
    } catch (error) {
      console.error('Results load error:', error);
    } finally {
      setResultLoading(false);
    }
  };

  const runStressTest = async () => {
    if (!selectedScenario) return;
    setResultLoading(true);
    try {
      const response = await stressTestApi.run(selectedScenario, {});
      setResults(response.data);
    } catch (error) {
      console.error('Stress test error:', error);
    } finally {
      setResultLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const selectedScenarioData = scenarios.find(s => s.scenario_id === selectedScenario);

  // 업종별 영향 데이터
  const industryImpact = results?.by_industry?.slice(0, 10).map((ind: any) => ({
    name: ind.industry_name,
    'RWA 증가': ind.rwa_increase_rate,
    'PD 증가': ind.pd_stress_impact * 100
  })) || [];

  return (
    <div className="space-y-6">
      {/* 페이지 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">스트레스 테스트</h1>
          <p className="text-sm text-gray-500 mt-1">시나리오 기반 포트폴리오 충격 분석</p>
        </div>
        <button
          onClick={runStressTest}
          disabled={!selectedScenario || resultLoading}
          className="btn btn-primary"
        >
          <Play size={16} className="mr-2" />
          테스트 실행
        </button>
      </div>

      {/* 시나리오 선택 */}
      <div className="grid grid-cols-5 gap-4">
        {scenarios.map(scenario => (
          <button
            key={scenario.scenario_id}
            onClick={() => loadResults(scenario.scenario_id)}
            className={`p-4 rounded-lg border text-left transition-all ${
              selectedScenario === scenario.scenario_id
                ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                : 'border-gray-200 bg-white hover:border-gray-300'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                scenario.severity === 'MILD' ? 'bg-green-100 text-green-800' :
                scenario.severity === 'MODERATE' ? 'bg-yellow-100 text-yellow-800' :
                scenario.severity === 'SEVERE' ? 'bg-orange-100 text-orange-800' :
                scenario.severity === 'EXTREME' ? 'bg-red-100 text-red-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {scenario.severity}
              </span>
            </div>
            <h3 className="font-medium text-gray-900">{scenario.scenario_name}</h3>
            <p className="text-xs text-gray-500 mt-1 line-clamp-2">{scenario.description}</p>
            <div className="mt-3 text-xs text-gray-600 space-y-1">
              <div className="flex justify-between">
                <span>PD 충격</span>
                <span className="font-mono">×{scenario.pd_stress_factor}</span>
              </div>
              <div className="flex justify-between">
                <span>LGD 충격</span>
                <span className="font-mono">×{scenario.lgd_stress_factor}</span>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* 결과 요약 */}
      {results && (
        <>
          <div className="grid grid-cols-4 gap-4">
            <StatCard
              title="스트레스 RWA"
              value={formatAmount(results.summary?.stressed_rwa || 0, 'billion')}
              subtitle={`기준: ${formatAmount(results.summary?.base_rwa || 0, 'billion')}`}
              icon={<BarChart3 size={24} />}
              color="red"
            />
            <StatCard
              title="RWA 증가"
              value={formatPercent(results.summary?.rwa_increase_rate || 0)}
              subtitle={formatAmount(results.summary?.rwa_increase || 0, 'billion') + ' 증가'}
              icon={<TrendingDown size={24} />}
              color="red"
            />
            <StatCard
              title="스트레스 EL"
              value={formatAmount(results.summary?.stressed_el || 0, 'billion')}
              subtitle={`기준: ${formatAmount(results.summary?.base_el || 0, 'billion')}`}
              icon={<AlertTriangle size={24} />}
              color="yellow"
            />
            <StatCard
              title="자본비율 영향"
              value={formatPercent(results.summary?.capital_ratio_impact || 0)}
              subtitle={`변경 후: ${formatPercent(results.summary?.stressed_bis_ratio || 0)}`}
              icon={<Activity size={24} />}
              color={results.summary?.stressed_bis_ratio >= 10.5 ? 'green' : 'red'}
            />
          </div>

          {/* 상세 결과 */}
          <div className="grid grid-cols-2 gap-6">
            {/* 주요 지표 비교 */}
            <Card title="스트레스 전후 비교">
              {resultLoading ? (
                <div className="flex justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4 text-sm font-medium text-gray-500 pb-2 border-b">
                    <span>지표</span>
                    <span className="text-right">기준</span>
                    <span className="text-right">스트레스</span>
                  </div>

                  <div className="grid grid-cols-3 gap-4 items-center">
                    <span className="text-sm text-gray-700">총 RWA</span>
                    <span className="text-right font-mono">{formatAmount(results.summary?.base_rwa || 0, 'billion')}</span>
                    <span className="text-right font-mono text-red-600">{formatAmount(results.summary?.stressed_rwa || 0, 'billion')}</span>
                  </div>

                  <div className="grid grid-cols-3 gap-4 items-center">
                    <span className="text-sm text-gray-700">예상손실(EL)</span>
                    <span className="text-right font-mono">{formatAmount(results.summary?.base_el || 0, 'billion')}</span>
                    <span className="text-right font-mono text-red-600">{formatAmount(results.summary?.stressed_el || 0, 'billion')}</span>
                  </div>

                  <div className="grid grid-cols-3 gap-4 items-center">
                    <span className="text-sm text-gray-700">BIS 비율</span>
                    <span className="text-right font-mono">{formatPercent(results.summary?.base_bis_ratio || 0)}</span>
                    <span className={`text-right font-mono font-semibold ${
                      results.summary?.stressed_bis_ratio >= 10.5 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {formatPercent(results.summary?.stressed_bis_ratio || 0)}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-4 items-center">
                    <span className="text-sm text-gray-700">Tier1 비율</span>
                    <span className="text-right font-mono">{formatPercent(results.summary?.base_tier1_ratio || 0)}</span>
                    <span className={`text-right font-mono font-semibold ${
                      results.summary?.stressed_tier1_ratio >= 8.5 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {formatPercent(results.summary?.stressed_tier1_ratio || 0)}
                    </span>
                  </div>

                  <div className="pt-4 border-t">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700">규제 준수 여부</span>
                      {results.summary?.stressed_bis_ratio >= 10.5 ? (
                        <Badge variant="success">준수</Badge>
                      ) : (
                        <Badge variant="danger">위반</Badge>
                      )}
                    </div>
                    {results.summary?.stressed_bis_ratio < 10.5 && (
                      <p className="text-sm text-red-600 mt-2">
                        규제비율 10.5% 대비 {formatPercent(10.5 - results.summary?.stressed_bis_ratio)} 부족
                      </p>
                    )}
                  </div>
                </div>
              )}
            </Card>

            {/* 업종별 영향 */}
            <Card title="업종별 RWA 영향">
              <GroupedBarChart
                data={industryImpact}
                bars={[
                  { key: 'RWA 증가', name: 'RWA 증가율(%)', color: COLORS.danger }
                ]}
                xAxisKey="name"
                layout="vertical"
                height={300}
                showLegend={false}
              />
            </Card>
          </div>

          {/* 업종별 상세 테이블 */}
          <Card title="업종별 스트레스 영향 상세" noPadding>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="px-4 py-3 text-left font-semibold text-gray-700 bg-gray-50">업종</th>
                    <th className="px-4 py-3 text-right font-semibold text-gray-700 bg-gray-50">기준 RWA</th>
                    <th className="px-4 py-3 text-right font-semibold text-gray-700 bg-gray-50">스트레스 RWA</th>
                    <th className="px-4 py-3 text-right font-semibold text-gray-700 bg-gray-50">증가율</th>
                    <th className="px-4 py-3 text-right font-semibold text-gray-700 bg-gray-50">기준 PD</th>
                    <th className="px-4 py-3 text-right font-semibold text-gray-700 bg-gray-50">스트레스 PD</th>
                    <th className="px-4 py-3 text-center font-semibold text-gray-700 bg-gray-50">위험도</th>
                  </tr>
                </thead>
                <tbody>
                  {results.by_industry?.map((ind: any, index: number) => (
                    <tr key={index} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">{ind.industry_name}</td>
                      <td className="px-4 py-3 text-right font-mono">
                        {formatAmount(ind.base_rwa, 'billion')}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-red-600">
                        {formatAmount(ind.stressed_rwa, 'billion')}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className={`font-mono font-semibold ${
                          ind.rwa_increase_rate >= 30 ? 'text-red-600' :
                          ind.rwa_increase_rate >= 20 ? 'text-orange-600' :
                          ind.rwa_increase_rate >= 10 ? 'text-yellow-600' : 'text-green-600'
                        }`}>
                          +{formatPercent(ind.rwa_increase_rate)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono">
                        {formatPercent(ind.base_pd * 100, 3)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-red-600">
                        {formatPercent(ind.stressed_pd * 100, 3)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          ind.rwa_increase_rate >= 30 ? 'bg-red-100 text-red-800' :
                          ind.rwa_increase_rate >= 20 ? 'bg-orange-100 text-orange-800' :
                          ind.rwa_increase_rate >= 10 ? 'bg-yellow-100 text-yellow-800' :
                          'bg-green-100 text-green-800'
                        }`}>
                          {ind.rwa_increase_rate >= 30 ? '고위험' :
                           ind.rwa_increase_rate >= 20 ? '중위험' :
                           ind.rwa_increase_rate >= 10 ? '주의' : '양호'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* 시나리오 상세 정보 */}
          {selectedScenarioData && (
            <Card title="시나리오 상세">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-3">시나리오 설명</h4>
                  <p className="text-sm text-gray-600">{selectedScenarioData.description}</p>

                  <h4 className="text-sm font-medium text-gray-700 mt-4 mb-3">충격 계수</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">PD 충격 배수</span>
                      <span className="text-sm font-mono">×{selectedScenarioData.pd_stress_factor}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">LGD 충격 배수</span>
                      <span className="text-sm font-mono">×{selectedScenarioData.lgd_stress_factor}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">RWA 충격 배수</span>
                      <span className="text-sm font-mono">×{selectedScenarioData.rwa_stress_factor}</span>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-3">거시경제 가정</h4>
                  <div className="space-y-2 text-sm">
                    {selectedScenarioData.macro_assumptions && Object.entries(selectedScenarioData.macro_assumptions).map(([key, value]: [string, any]) => (
                      <div key={key} className="flex justify-between">
                        <span className="text-gray-600">{key}</span>
                        <span className="font-mono">{value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
