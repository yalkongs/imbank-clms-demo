import React, { useEffect, useState } from 'react';
import {
  Briefcase,
  AlertTriangle,
  DollarSign,
  Clock,
  CheckCircle,
  XCircle,
  TrendingUp,
  FileText,
  X
} from 'lucide-react';
import { Card, StatCard, GroupedBarChart, DonutChart, COLORS, FeatureModal, HelpButton } from '../components';
import { workoutApi } from '../utils/api';
import { formatAmount, formatPercent } from '../utils/format';

export default function Workout() {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>(null);
  const [cases, setCases] = useState<any[]>([]);
  const [restructuringHistory, setRestructuringHistory] = useState<any[]>([]);
  const [selectedCase, setSelectedCase] = useState<any>(null);
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [caseModalOpen, setCaseModalOpen] = useState(false);
  const [featureModalOpen, setFeatureModalOpen] = useState(false);
  const [featureInfo, setFeatureInfo] = useState<any>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [dashRes, casesRes, histRes] = await Promise.all([
        workoutApi.getDashboard(),
        workoutApi.getCases(),
        workoutApi.getRestructuringHistory()
      ]);
      setDashboard(dashRes.data);
      setCases(casesRes.data.cases || []);
      setRestructuringHistory(histRes.data.restructurings || []);
    } catch (error) {
      console.error('Workout data load error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadCaseDetail = async (caseId: string) => {
    try {
      const [caseRes, scenarioRes] = await Promise.all([
        workoutApi.getCase(caseId),
        workoutApi.getScenarios(caseId)
      ]);
      setSelectedCase(caseRes.data);
      setScenarios(scenarioRes.data.scenarios || []);
      setCaseModalOpen(true);
    } catch (error) {
      console.error('Case detail load error:', error);
    }
  };

  const closeCaseModal = () => {
    setCaseModalOpen(false);
    setSelectedCase(null);
    setScenarios([]);
  };

  const openFeatureModal = async (featureId: string) => {
    try {
      const res = await workoutApi.getFeatureDescription(featureId);
      setFeatureInfo(res.data);
      setFeatureModalOpen(true);
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

  // Strategy distribution - API returns by_strategy not status_distribution
  const statusDist = dashboard?.by_strategy?.map((d: any) => ({
    name: d.strategy,
    value: d.count,
    color: d.strategy === 'NORMALIZATION' ? COLORS.success :
           d.strategy === 'RESTRUCTURING' ? COLORS.warning :
           d.strategy === 'ASSET_SALE' ? COLORS.primary :
           d.strategy === 'LEGAL_RECOVERY' ? COLORS.danger : COLORS.secondary
  })) || [];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            Workout 관리
            <HelpButton onClick={() => openFeatureModal('workout_overview')} />
          </h1>
          <p className="text-sm text-gray-500 mt-1">부실채권 관리 및 회수 시나리오 분석</p>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-5 gap-4">
        <StatCard
          title="활성 케이스"
          value={dashboard?.summary?.active_cases || 0}
          icon={<Briefcase size={24} />}
          color="yellow"
        />
        <StatCard
          title="총 부실채권"
          value={formatAmount(dashboard?.summary?.total_exposure || 0, 'billion')}
          icon={<AlertTriangle size={24} />}
          color="red"
        />
        <StatCard
          title="평균 회수율"
          value={formatPercent((dashboard?.summary?.avg_expected_recovery_rate || 0) * 100)}
          icon={<TrendingUp size={24} />}
          color={(dashboard?.summary?.avg_expected_recovery_rate || 0) >= 0.5 ? 'green' : 'yellow'}
        />
        <StatCard
          title="총 케이스"
          value={dashboard?.summary?.total_cases || 0}
          icon={<FileText size={24} />}
          color="blue"
        />
        <StatCard
          title="충당금"
          value={formatAmount(dashboard?.summary?.total_provision || 0, 'billion')}
          icon={<DollarSign size={24} />}
          color="green"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-3 gap-6">
        {/* Strategy Distribution */}
        <Card title="회수전략 분포">
          <DonutChart
            data={statusDist}
            height={240}
            innerRadius={50}
            outerRadius={80}
          />
        </Card>

        {/* Exposure by Strategy */}
        <Card
          title="전략별 익스포저"
          headerAction={<HelpButton onClick={() => openFeatureModal('recovery_scenario')} size="sm" />}
          className="col-span-2"
        >
          <GroupedBarChart
            data={dashboard?.by_strategy?.map((s: any) => ({
              name: s.strategy,
              익스포저: (s.exposure || 0) / 100000000,
              건수: s.count
            })) || []}
            bars={[
              { key: '익스포저', name: '익스포저(억)', color: COLORS.primary },
              { key: '건수', name: '건수', color: COLORS.success }
            ]}
            xAxisKey="name"
            height={240}
            showLegend
          />
        </Card>
      </div>

      {/* Cases Table */}
      <Card title="Workout 케이스 목록">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 text-left">기업명</th>
                <th className="px-3 py-2 text-center">상태</th>
                <th className="px-3 py-2 text-center">우선순위</th>
                <th className="px-3 py-2 text-right">부실금액</th>
                <th className="px-3 py-2 text-right">충당금</th>
                <th className="px-3 py-2 text-right">담보가치</th>
                <th className="px-3 py-2 text-center">예상회수율</th>
                <th className="px-3 py-2 text-left">현재전략</th>
                <th className="px-3 py-2 text-left">담당자</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c: any) => (
                <tr
                  key={c.case_id}
                  className="border-b hover:bg-blue-50 cursor-pointer transition-colors"
                  onClick={() => loadCaseDetail(c.case_id)}
                >
                  <td className="px-3 py-2 font-medium">{c.customer_name}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      c.case_status === 'OPEN' || c.case_status === 'IN_PROGRESS' ? 'bg-yellow-100 text-yellow-700' :
                      c.case_status === 'RECOVERED' ? 'bg-green-100 text-green-700' :
                      c.case_status === 'LIQUIDATED' ? 'bg-gray-100 text-gray-700' :
                      'bg-red-100 text-red-700'
                    }`}>
                      {c.case_status}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      (c.total_exposure || 0) >= 10000000000 ? 'bg-red-600 text-white' :
                      (c.total_exposure || 0) >= 5000000000 ? 'bg-red-100 text-red-700' :
                      (c.total_exposure || 0) >= 1000000000 ? 'bg-yellow-100 text-yellow-700' :
                      'bg-blue-100 text-blue-700'
                    }`}>
                      {(c.total_exposure || 0) >= 10000000000 ? 'CRITICAL' :
                       (c.total_exposure || 0) >= 5000000000 ? 'HIGH' :
                       (c.total_exposure || 0) >= 1000000000 ? 'MEDIUM' : 'LOW'}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right text-red-600">{formatAmount(c.total_exposure, 'billion')}</td>
                  <td className="px-3 py-2 text-right">{formatAmount(c.provision_amount, 'billion')}</td>
                  <td className="px-3 py-2 text-right">{formatAmount(c.secured_amount, 'billion')}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`font-semibold ${
                      (c.expected_recovery_rate || 0) >= 0.7 ? 'text-green-600' :
                      (c.expected_recovery_rate || 0) >= 0.5 ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {formatPercent((c.expected_recovery_rate || 0) * 100)}
                    </span>
                  </td>
                  <td className="px-3 py-2">{c.strategy}</td>
                  <td className="px-3 py-2 text-gray-600">{c.assigned_workout_officer}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Case Detail Modal */}
      {caseModalOpen && selectedCase && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl w-[90%] max-w-5xl max-h-[90vh] overflow-hidden">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gradient-to-r from-red-600 to-red-700">
              <div className="text-white">
                <h2 className="text-xl font-bold flex items-center">
                  <Briefcase className="mr-2" size={24} />
                  {selectedCase.case?.customer_name || selectedCase.customer_name}
                </h2>
                <p className="text-red-100 text-sm">Workout 케이스 상세 및 회수 시나리오</p>
              </div>
              <button
                onClick={closeCaseModal}
                className="text-white hover:bg-white/20 rounded-full p-2 transition-colors"
              >
                <X size={24} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="overflow-y-auto max-h-[calc(90vh-140px)] p-6">
              <div className="grid grid-cols-2 gap-6">
                {/* Left: Case Detail */}
                <div className="space-y-4">
                  <h3 className="text-lg font-bold text-gray-900 flex items-center">
                    <FileText className="mr-2 text-gray-600" size={20} />
                    케이스 상세
                  </h3>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-xs text-gray-500">케이스 개시일</p>
                      <p className="text-sm font-medium">{selectedCase.case?.case_open_date || '-'}</p>
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-xs text-gray-500">케이스 상태</p>
                      <p className="text-sm font-medium">
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          selectedCase.case?.case_status === 'IN_PROGRESS' ? 'bg-yellow-100 text-yellow-700' :
                          selectedCase.case?.case_status === 'RECOVERED' ? 'bg-green-100 text-green-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>
                          {selectedCase.case?.case_status || '-'}
                        </span>
                      </p>
                    </div>
                  </div>

                  <div className="p-4 bg-red-50 rounded-lg border border-red-200">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-red-700 flex items-center">
                        <AlertTriangle className="mr-1" size={16} />
                        총 익스포저
                      </span>
                      <span className="text-2xl font-bold text-red-600">{formatAmount(selectedCase.case?.total_exposure, 'billion')}</span>
                    </div>
                    <div className="mt-3 space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">충당금 적립</span>
                        <span className="font-medium">{formatAmount(selectedCase.case?.provision_amount, 'billion')}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">담보 가치</span>
                        <span className="font-medium">{formatAmount(selectedCase.case?.secured_amount, 'billion')}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">무담보 익스포저</span>
                        <span className="font-medium text-red-600">
                          {formatAmount((selectedCase.case?.total_exposure || 0) - (selectedCase.case?.secured_amount || 0), 'billion')}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <p className="text-sm text-blue-700 mb-2">현재 전략</p>
                    <p className="text-xl font-bold text-blue-800">{selectedCase.case?.strategy || '-'}</p>
                    <div className="mt-3 flex items-center justify-between">
                      <span className="text-sm text-gray-600">예상 회수율</span>
                      <span className={`text-lg font-semibold ${
                        (selectedCase.case?.expected_recovery_rate || 0) >= 0.7 ? 'text-green-600' :
                        (selectedCase.case?.expected_recovery_rate || 0) >= 0.5 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {formatPercent((selectedCase.case?.expected_recovery_rate || 0) * 100)}
                      </span>
                    </div>
                  </div>

                  {selectedCase.case?.assigned_workout_officer && (
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-xs text-gray-500 mb-1">담당자</p>
                      <p className="text-sm font-medium text-gray-700">{selectedCase.case.assigned_workout_officer}</p>
                    </div>
                  )}
                </div>

                {/* Right: Recovery Scenarios */}
                <div className="space-y-4">
                  <h3 className="text-lg font-bold text-gray-900 flex items-center">
                    <TrendingUp className="mr-2 text-green-600" size={20} />
                    회수 시나리오 분석
                  </h3>

                  {scenarios.length > 0 ? (
                    <div className="space-y-3">
                      {scenarios.map((scenario: any) => (
                        <div
                          key={scenario.scenario_id}
                          className={`p-4 rounded-lg border-2 transition-all ${
                            scenario.is_recommended
                              ? 'border-green-500 bg-green-50 shadow-md'
                              : 'border-gray-200 bg-white hover:border-gray-300'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-semibold text-gray-900">{scenario.scenario_name}</span>
                            {scenario.is_recommended && (
                              <span className="px-2 py-1 bg-green-500 text-white rounded text-xs font-bold flex items-center">
                                <CheckCircle size={12} className="mr-1" />
                                추천
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-gray-600 mb-3">{scenario.scenario_type}</p>

                          <div className="grid grid-cols-3 gap-3 text-sm">
                            <div className="p-2 bg-white rounded border">
                              <p className="text-xs text-gray-500">예상회수액</p>
                              <p className="font-bold text-green-600">{formatAmount(scenario.recovery_amount, 'billion')}</p>
                            </div>
                            <div className="p-2 bg-white rounded border">
                              <p className="text-xs text-gray-500">기대가치</p>
                              <p className="font-bold">{formatAmount(scenario.expected_value, 'billion')}</p>
                            </div>
                            <div className="p-2 bg-white rounded border">
                              <p className="text-xs text-gray-500">NPV</p>
                              <p className="font-bold text-blue-600">{formatAmount(scenario.npv, 'billion')}</p>
                            </div>
                          </div>

                          <div className="mt-3 pt-3 border-t border-gray-200 flex items-center justify-between text-xs text-gray-500">
                            <span className="flex items-center">
                              <Clock size={12} className="mr-1" />
                              {scenario.recovery_timeline_months}개월
                            </span>
                            <span>비용: {formatAmount(scenario.total_cost, 'million')}</span>
                            <span>성공확률: {formatPercent((scenario.probability || 0) * 100)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-gray-400">
                      <TrendingUp size={48} className="mx-auto mb-3 text-gray-300" />
                      <p>회수 시나리오 데이터가 없습니다</p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-end">
              <button
                onClick={closeCaseModal}
                className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Restructuring History */}
      <Card
        title="채무조정 이력"
        headerAction={<HelpButton onClick={() => openFeatureModal('debt_restructuring')} size="sm" />}
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 text-left">기업명</th>
                <th className="px-3 py-2 text-left">조정유형</th>
                <th className="px-3 py-2 text-right">원금감면</th>
                <th className="px-3 py-2 text-right">금리감면</th>
                <th className="px-3 py-2 text-center">만기연장</th>
                <th className="px-3 py-2 text-left">조정일</th>
                <th className="px-3 py-2 text-center">상태</th>
              </tr>
            </thead>
            <tbody>
              {restructuringHistory.slice(0, 10).map((r: any) => (
                <tr key={r.restructure_id} className="border-b hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium">{r.customer_name}</td>
                  <td className="px-3 py-2">{r.approval_level || '-'}</td>
                  <td className="px-3 py-2 text-right text-red-600">
                    {r.haircut_amount ? formatAmount(r.haircut_amount, 'billion') : '-'}
                    {r.haircut_pct ? ` (${r.haircut_pct}%)` : ''}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {r.original_rate && r.new_rate ? `${(r.original_rate - r.new_rate).toFixed(2)}%p` : '-'}
                  </td>
                  <td className="px-3 py-2 text-center">
                    {r.grace_period_months ? `${r.grace_period_months}개월` : '-'}
                  </td>
                  <td className="px-3 py-2">{r.restructure_date}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      r.status === 'COMPLETED' ? 'bg-green-100 text-green-700' :
                      r.status === 'IN_PROGRESS' || r.status === 'APPROVED' ? 'bg-blue-100 text-blue-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {r.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Feature Modal */}
      <FeatureModal
        isOpen={featureModalOpen}
        onClose={() => setFeatureModalOpen(false)}
        feature={featureInfo}
      />
    </div>
  );
}
