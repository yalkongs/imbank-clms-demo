import React, { useEffect, useState } from 'react';
import {
  Brain,
  Activity,
  AlertTriangle,
  Clock,
  TrendingUp,
  TrendingDown,
  X,
  CheckCircle,
  XCircle,
  BarChart3,
  GitBranch,
  Calendar,
  FileText,
  BookOpen
} from 'lucide-react';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine, Cell, ComposedChart, Area
} from 'recharts';
import { Card, StatCard, Table, Badge, CellFormatters, TrendChart, COLORS } from '../components';
import { modelsApi } from '../utils/api';
import { formatPercent, formatDate } from '../utils/format';

type TabType = 'registry' | 'backtest' | 'override' | 'vintage';

export default function Models() {
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>('registry');
  const [models, setModels] = useState<any[]>([]);
  const [status, setStatus] = useState<any>(null);
  const [overrides, setOverrides] = useState<any>(null);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [modelDetail, setModelDetail] = useState<any>(null);
  const [backtestData, setBacktestData] = useState<any>(null);
  const [overridePerformance, setOverridePerformance] = useState<any>(null);
  const [vintageData, setVintageData] = useState<any>(null);
  const [modelSpecs, setModelSpecs] = useState<any>(null);
  const [showSpecsModal, setShowSpecsModal] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (activeTab === 'backtest' && !backtestData) {
      loadBacktestData();
    }
    if (activeTab === 'override' && !overridePerformance) {
      loadOverridePerformance();
    }
    if (activeTab === 'vintage' && !vintageData) {
      loadVintageData();
    }
  }, [activeTab]);

  const loadData = async () => {
    try {
      const [modelsRes, statusRes, overridesRes] = await Promise.all([
        modelsApi.getAll(),
        modelsApi.getStatus(),
        modelsApi.getOverrides()
      ]);
      setModels(modelsRes.data || []);
      setStatus(statusRes.data);
      setOverrides(overridesRes.data);
    } catch (error) {
      console.error('Models data load error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadBacktestData = async () => {
    try {
      const response = await modelsApi.getBacktestSummary();
      setBacktestData(response.data);
    } catch (error) {
      console.error('Backtest data load error:', error);
      setBacktestData({ backtest_results: [], summary: {}, alerts: [] });
    }
  };

  const loadOverridePerformance = async () => {
    try {
      const response = await modelsApi.getOverridePerformance();
      setOverridePerformance(response.data);
    } catch (error) {
      console.error('Override performance load error:', error);
      setOverridePerformance({ outcome_distribution: [], accuracy_by_direction: [], error_analysis: {}, details: [] });
    }
  };

  const loadVintageData = async () => {
    try {
      const response = await modelsApi.getVintageAnalysis();
      setVintageData(response.data);
    } catch (error) {
      console.error('Vintage data load error:', error);
      setVintageData({ vintages: [], summary_by_type: [], monthly_trend: [] });
    }
  };

  const loadModelDetail = async (modelId: string) => {
    setSelectedModel(modelId);
    try {
      const response = await modelsApi.getById(modelId);
      setModelDetail(response.data);
    } catch (error) {
      console.error('Model detail load error:', error);
    }
  };

  const loadModelSpecs = async (modelId: string) => {
    try {
      const response = await modelsApi.getModelSpecifications(modelId);
      setModelSpecs(response.data);
      setShowSpecsModal(true);
    } catch (error) {
      console.error('Model specs load error:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const tabs = [
    { id: 'registry', label: '모델 레지스트리', icon: <Brain size={16} /> },
    { id: 'backtest', label: 'PD Backtest', icon: <BarChart3 size={16} /> },
    { id: 'override', label: 'Override 성과', icon: <GitBranch size={16} /> },
    { id: 'vintage', label: 'Vintage 분석', icon: <Calendar size={16} /> }
  ];

  return (
    <div className="space-y-6">
      {/* 페이지 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">모델관리 (MRM)</h1>
          <p className="text-sm text-gray-500 mt-1">신용평가모델 성능 모니터링 및 검증 관리</p>
        </div>
      </div>

      {/* 요약 카드 */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="등록 모델"
          value={`${models.length}개`}
          subtitle={`활성: ${status?.status_summary?.ACTIVE || 0}개`}
          icon={<Brain size={24} />}
          color="blue"
        />
        <StatCard
          title="검증 예정"
          value={`${status?.upcoming_validations?.length || 0}건`}
          subtitle="30일 이내"
          icon={<Clock size={24} />}
          color="yellow"
        />
        <StatCard
          title="성능 경보"
          value={`${status?.recent_alerts?.length || 0}건`}
          subtitle="최근 30일"
          icon={<AlertTriangle size={24} />}
          color={status?.recent_alerts?.length > 0 ? 'red' : 'green'}
        />
        <StatCard
          title="Override 비율"
          value={formatPercent(overrides?.override_rate || 0)}
          subtitle={`한도: ${overrides?.thresholds?.max_override_rate}%`}
          icon={<Activity size={24} />}
          color={overrides?.override_rate > overrides?.thresholds?.max_override_rate ? 'red' : 'green'}
        />
      </div>

      {/* 탭 네비게이션 */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as TabType)}
              className={`flex items-center py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* 탭 콘텐츠 */}
      {activeTab === 'registry' && (
        <RegistryTab
          models={models}
          modelDetail={modelDetail}
          selectedModel={selectedModel}
          overrides={overrides}
          status={status}
          onSelectModel={loadModelDetail}
          onOpenSpecs={loadModelSpecs}
        />
      )}

      {activeTab === 'backtest' && (
        <BacktestTab data={backtestData} />
      )}

      {activeTab === 'override' && (
        <OverrideTab data={overridePerformance} />
      )}

      {activeTab === 'vintage' && (
        <VintageTab data={vintageData} />
      )}

      {/* 모델 상세 사양 모달 */}
      {showSpecsModal && modelSpecs && (
        <ModelSpecsModal specs={modelSpecs} onClose={() => setShowSpecsModal(false)} />
      )}
    </div>
  );
}

// 모델 레지스트리 탭
function RegistryTab({
  models,
  modelDetail,
  selectedModel,
  overrides,
  status,
  onSelectModel,
  onOpenSpecs
}: {
  models: any[];
  modelDetail: any;
  selectedModel: string | null;
  overrides: any;
  status: any;
  onSelectModel: (id: string) => void;
  onOpenSpecs: (id: string) => void;
}) {
  const columns = [
    {
      key: 'model_name',
      header: '모델명',
      render: (value: string, row: any) => (
        <div>
          <p className="font-medium text-gray-900">{value}</p>
          <p className="text-xs text-gray-500">{row.model_id}</p>
        </div>
      )
    },
    {
      key: 'model_type',
      header: '유형',
      render: (value: string) => (
        <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">{value}</span>
      )
    },
    {
      key: 'risk_tier',
      header: '위험등급',
      align: 'center' as const,
      render: (value: string) => (
        <Badge variant={value === 'TIER1' ? 'danger' : value === 'TIER2' ? 'warning' : 'success'}>
          {value}
        </Badge>
      )
    },
    {
      key: 'last_validation_date',
      header: '최근검증',
      render: (value: string) => CellFormatters.date(value)
    },
    {
      key: 'next_validation_date',
      header: '차기검증',
      render: (value: string) => {
        if (!value) return '-';
        const date = new Date(value);
        const now = new Date();
        const daysUntil = Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
        return (
          <div>
            <p className="text-sm">{CellFormatters.date(value)}</p>
            {daysUntil <= 30 && (
              <p className={`text-xs ${daysUntil <= 7 ? 'text-red-600' : 'text-yellow-600'}`}>
                {daysUntil}일 후
              </p>
            )}
          </div>
        );
      }
    },
    {
      key: 'status',
      header: '상태',
      align: 'center' as const,
      render: (value: string) => CellFormatters.status(value)
    },
    {
      key: 'model_id',
      header: '상세',
      align: 'center' as const,
      render: (_: string, row: any) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onOpenSpecs(row.model_id);
          }}
          className="p-1 text-blue-600 hover:bg-blue-50 rounded"
          title="상세 사양 보기"
        >
          <BookOpen size={16} />
        </button>
      )
    }
  ];

  return (
    <>
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <Card title="모델 레지스트리" noPadding>
            <Table
              columns={columns}
              data={models}
              onRowClick={(row) => onSelectModel(row.model_id)}
              selectedKey="model_id"
              selectedValue={selectedModel || undefined}
            />
          </Card>
        </div>

        <div className="col-span-1 space-y-4">
          {modelDetail ? (
            <>
              <Card title="모델 정보">
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-500">모델명</span>
                    <span className="text-sm font-medium">{modelDetail.model?.model_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-500">목적</span>
                    <span className="text-sm">{modelDetail.model?.model_purpose}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-500">담당부서</span>
                    <span className="text-sm">{modelDetail.model?.owner_dept}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-500">개발일</span>
                    <span className="text-sm">{formatDate(modelDetail.model?.development_date)}</span>
                  </div>
                  <button
                    onClick={() => onOpenSpecs(modelDetail.model?.model_id)}
                    className="w-full mt-3 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center"
                  >
                    <BookOpen size={16} className="mr-2" />
                    상세 사양 보기
                  </button>
                </div>
              </Card>

              <Card title="성능 추이">
                {modelDetail.performance_history?.length > 0 ? (
                  <TrendChart
                    data={modelDetail.performance_history}
                    lines={[
                      { key: 'gini', name: 'Gini', color: COLORS.primary },
                      { key: 'psi', name: 'PSI', color: COLORS.danger }
                    ]}
                    height={200}
                    referenceLines={[
                      { y: 0.40, label: 'Gini 경고', color: COLORS.warning },
                      { y: 0.10, label: 'PSI 경고', color: COLORS.warning }
                    ]}
                  />
                ) : (
                  <div className="text-center py-8 text-gray-400">성능 데이터 없음</div>
                )}
              </Card>

              <Card title="버전 현황">
                <div className="space-y-2">
                  {modelDetail.versions?.slice(0, 3).map((ver: any, index: number) => (
                    <div key={index} className="p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-gray-900">{ver.version_no}</span>
                        <Badge variant={ver.status === 'ACTIVE' ? 'success' : 'gray'}>{ver.status}</Badge>
                      </div>
                      <div className="flex justify-between mt-1 text-xs text-gray-500">
                        <span>{ver.deployment_env}</span>
                        <span>{formatDate(ver.effective_from)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </>
          ) : (
            <Card>
              <div className="text-center py-12 text-gray-400">
                <Brain size={48} className="mx-auto mb-3 text-gray-300" />
                <p>모델을 선택하세요</p>
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* Override 현황 */}
      <Card title="Override 현황">
        <div className="grid grid-cols-4 gap-6">
          <div className="col-span-1">
            <h4 className="text-sm font-medium text-gray-700 mb-3">방향별 분포</h4>
            <div className="space-y-3">
              {overrides?.summary?.map((s: any, index: number) => (
                <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center">
                    {s.direction === 'UPGRADE' ? (
                      <TrendingUp className="text-green-500 mr-2" size={16} />
                    ) : (
                      <TrendingDown className="text-red-500 mr-2" size={16} />
                    )}
                    <span className="text-sm">{s.direction}</span>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold">{s.count}건</p>
                    <p className="text-xs text-gray-500">평균 {s.avg_notch?.toFixed(1)}노치</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="col-span-3">
            <h4 className="text-sm font-medium text-gray-700 mb-3">최근 Override</h4>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="px-3 py-2 text-left font-medium text-gray-500">일자</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-500">신청번호</th>
                    <th className="px-3 py-2 text-center font-medium text-gray-500">시스템</th>
                    <th className="px-3 py-2 text-center font-medium text-gray-500">변경</th>
                    <th className="px-3 py-2 text-center font-medium text-gray-500">최종</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-500">사유</th>
                    <th className="px-3 py-2 text-center font-medium text-gray-500">결과</th>
                  </tr>
                </thead>
                <tbody>
                  {overrides?.recent_overrides?.slice(0, 8).map((o: any, index: number) => (
                    <tr key={index} className="border-b border-gray-100">
                      <td className="px-3 py-2 text-gray-600">{formatDate(o.date)}</td>
                      <td className="px-3 py-2 font-mono text-blue-600">{o.application_id}</td>
                      <td className="px-3 py-2 text-center">{CellFormatters.grade(o.system_value)}</td>
                      <td className="px-3 py-2 text-center">
                        <span className={`inline-flex items-center ${
                          o.direction === 'UPGRADE' ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {o.direction === 'UPGRADE' ? <TrendingUp size={12} className="mr-1" /> : <TrendingDown size={12} className="mr-1" />}
                          {o.notch_change}노치
                        </span>
                      </td>
                      <td className="px-3 py-2 text-center">{CellFormatters.grade(o.override_value)}</td>
                      <td className="px-3 py-2 text-gray-600 max-w-xs truncate">{o.reason}</td>
                      <td className="px-3 py-2 text-center">
                        {o.outcome === 'PERFORMING' ? (
                          <Badge variant="success">정상</Badge>
                        ) : o.outcome === 'DEFAULT' ? (
                          <Badge variant="danger">부실</Badge>
                        ) : (
                          <Badge variant="gray">미확정</Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </Card>
    </>
  );
}

// PD Backtest 탭
function BacktestTab({ data }: { data: any }) {
  if (!data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // 연도별 통계 준비
  const yearStats: { [key: string]: { pass: number; warning: number; fail: number } } = {};
  data.backtest_results?.forEach((r: any) => {
    if (!yearStats[r.year]) {
      yearStats[r.year] = { pass: 0, warning: 0, fail: 0 };
    }
    if (r.result === 'PASS') yearStats[r.year].pass++;
    else if (r.result === 'WARNING') yearStats[r.year].warning++;
    else if (r.result === 'FAIL') yearStats[r.year].fail++;
  });

  const yearChartData = Object.entries(yearStats).map(([year, stats]) => ({
    year,
    ...stats,
    total: stats.pass + stats.warning + stats.fail
  }));

  // 등급별 PD vs DR 비교 (최근 연도)
  const latestYear = Math.max(...Object.keys(yearStats).map(Number));
  const gradeComparison = data.backtest_results
    ?.filter((r: any) => r.year === latestYear)
    ?.sort((a: any, b: any) => a.grade.localeCompare(b.grade))
    ?.map((r: any) => ({
      grade: r.grade,
      predicted: (r.predicted_pd * 100).toFixed(2),
      actual: (r.actual_dr * 100).toFixed(2),
      result: r.result
    }));

  return (
    <div className="space-y-6">
      {/* 요약 */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="검정 통과"
          value={data.summary?.PASS || 0}
          subtitle="Binomial Test"
          icon={<CheckCircle size={24} />}
          color="green"
        />
        <StatCard
          title="경고"
          value={data.summary?.WARNING || 0}
          subtitle="p-value < 0.05"
          icon={<AlertTriangle size={24} />}
          color="yellow"
        />
        <StatCard
          title="실패"
          value={data.summary?.FAIL || 0}
          subtitle="p-value < 0.01"
          icon={<XCircle size={24} />}
          color="red"
        />
        <StatCard
          title="신뢰수준"
          value="95%"
          subtitle="검정 기준"
          icon={<BarChart3 size={24} />}
          color="blue"
        />
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* 연도별 결과 분포 */}
        <Card title="연도별 검정 결과">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={yearChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="pass" name="통과" stackId="a" fill="#10B981" />
              <Bar dataKey="warning" name="경고" stackId="a" fill="#F59E0B" />
              <Bar dataKey="fail" name="실패" stackId="a" fill="#EF4444" />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* 등급별 PD vs DR */}
        <Card title={`등급별 예측 PD vs 실제 DR (${latestYear}년)`}>
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={gradeComparison}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="grade" fontSize={11} />
              <YAxis unit="%" />
              <Tooltip formatter={(value: any) => `${value}%`} />
              <Legend />
              <Bar dataKey="predicted" name="예측 PD" fill="#3B82F6" />
              <Line type="monotone" dataKey="actual" name="실제 DR" stroke="#EF4444" strokeWidth={2} dot={{ r: 4 }} />
            </ComposedChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* 경보 목록 */}
      {data.alerts?.length > 0 && (
        <Card title="Backtest 경보">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="px-4 py-2 text-left font-medium text-gray-500">모델</th>
                  <th className="px-4 py-2 text-center font-medium text-gray-500">연도</th>
                  <th className="px-4 py-2 text-center font-medium text-gray-500">등급</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-500">예측 PD</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-500">실제 DR</th>
                  <th className="px-4 py-2 text-center font-medium text-gray-500">결과</th>
                </tr>
              </thead>
              <tbody>
                {data.alerts.slice(0, 15).map((alert: any, index: number) => (
                  <tr key={index} className="border-b border-gray-100">
                    <td className="px-4 py-2 font-medium text-gray-900">{alert.model_name}</td>
                    <td className="px-4 py-2 text-center">{alert.year}</td>
                    <td className="px-4 py-2 text-center">{CellFormatters.grade(alert.grade)}</td>
                    <td className="px-4 py-2 text-right font-mono">{(alert.predicted_pd * 100).toFixed(3)}%</td>
                    <td className="px-4 py-2 text-right font-mono">{(alert.actual_dr * 100).toFixed(3)}%</td>
                    <td className="px-4 py-2 text-center">
                      <Badge variant={alert.result === 'FAIL' ? 'danger' : 'warning'}>
                        {alert.result}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* 방법론 설명 */}
      <Card title="Backtest 방법론">
        <div className="bg-blue-50 rounded-lg p-4">
          <h4 className="font-medium text-blue-900 mb-2">Binomial Test</h4>
          <p className="text-sm text-blue-800 mb-2">{data.methodology?.description}</p>
          <div className="grid grid-cols-3 gap-4 mt-3 text-sm">
            <div className="bg-white rounded p-3">
              <p className="text-gray-500">검정 유형</p>
              <p className="font-medium">{data.methodology?.test_type}</p>
            </div>
            <div className="bg-white rounded p-3">
              <p className="text-gray-500">경고 기준</p>
              <p className="font-medium">p-value &lt; {data.methodology?.warning_threshold}</p>
            </div>
            <div className="bg-white rounded p-3">
              <p className="text-gray-500">실패 기준</p>
              <p className="font-medium">p-value &lt; {data.methodology?.fail_threshold}</p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

// Override 성과 탭
function OverrideTab({ data }: { data: any }) {
  if (!data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // 정확도 차트 데이터
  const accuracyData = data.accuracy_by_direction?.map((a: any) => ({
    direction: a.direction,
    accuracy: a.accuracy_rate,
    correct: a.correct,
    total: a.total
  })) || [];

  return (
    <div className="space-y-6">
      {/* 요약 */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="Override 정확도"
          value={`${((data.accuracy_by_direction?.reduce((sum: number, a: any) => sum + (a.correct || 0), 0) /
            data.accuracy_by_direction?.reduce((sum: number, a: any) => sum + (a.total || 0), 0)) * 100 || 0).toFixed(1)}%`}
          subtitle="전체 평균"
          icon={<CheckCircle size={24} />}
          color="blue"
        />
        <StatCard
          title="Type I 오류"
          value={data.error_analysis?.type1_errors || 0}
          subtitle="등급상향 후 부도"
          icon={<TrendingUp size={24} />}
          color="red"
        />
        <StatCard
          title="Type II 오류"
          value={data.error_analysis?.type2_errors || 0}
          subtitle="등급하향 후 정상"
          icon={<TrendingDown size={24} />}
          color="yellow"
        />
        <StatCard
          title="분석 건수"
          value={data.details?.length || 0}
          subtitle="전체 Override"
          icon={<Activity size={24} />}
          color="gray"
        />
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* 방향별 정확도 */}
        <Card title="Override 방향별 정확도">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={accuracyData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" domain={[0, 100]} unit="%" />
              <YAxis type="category" dataKey="direction" width={80} />
              <Tooltip formatter={(value: any) => `${value}%`} />
              <Bar dataKey="accuracy" name="정확도">
                {accuracyData.map((entry: any, index: number) => (
                  <Cell
                    key={index}
                    fill={entry.accuracy >= 70 ? '#10B981' : entry.accuracy >= 50 ? '#F59E0B' : '#EF4444'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-4 text-sm text-gray-600">
            <p className="flex items-center">
              <span className="w-3 h-3 bg-green-500 rounded-full mr-2"></span>
              70% 이상: 양호
            </p>
            <p className="flex items-center mt-1">
              <span className="w-3 h-3 bg-yellow-500 rounded-full mr-2"></span>
              50-70%: 주의
            </p>
            <p className="flex items-center mt-1">
              <span className="w-3 h-3 bg-red-500 rounded-full mr-2"></span>
              50% 미만: 개선필요
            </p>
          </div>
        </Card>

        {/* 오류 분석 */}
        <Card title="오류 유형 분석">
          <div className="space-y-4">
            <div className="p-4 bg-red-50 rounded-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <TrendingUp className="text-red-500 mr-3" size={24} />
                  <div>
                    <h4 className="font-medium text-red-900">Type I 오류 (과신)</h4>
                    <p className="text-sm text-red-700">{data.error_analysis?.type1_description}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-red-600">{data.error_analysis?.type1_errors}</p>
                  <p className="text-xs text-red-500">허용: {data.thresholds?.acceptable_type1_rate}% 이하</p>
                </div>
              </div>
            </div>

            <div className="p-4 bg-yellow-50 rounded-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <TrendingDown className="text-yellow-600 mr-3" size={24} />
                  <div>
                    <h4 className="font-medium text-yellow-900">Type II 오류 (과소)</h4>
                    <p className="text-sm text-yellow-700">{data.error_analysis?.type2_description}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-yellow-600">{data.error_analysis?.type2_errors}</p>
                  <p className="text-xs text-yellow-600">허용: {data.thresholds?.acceptable_type2_rate}% 이하</p>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* 상세 내역 */}
      <Card title="Override 성과 상세">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="px-4 py-2 text-left font-medium text-gray-500">신청번호</th>
                <th className="px-4 py-2 text-center font-medium text-gray-500">시스템등급</th>
                <th className="px-4 py-2 text-center font-medium text-gray-500">변경등급</th>
                <th className="px-4 py-2 text-center font-medium text-gray-500">방향</th>
                <th className="px-4 py-2 text-center font-medium text-gray-500">실제결과</th>
                <th className="px-4 py-2 text-center font-medium text-gray-500">판정정확</th>
                <th className="px-4 py-2 text-left font-medium text-gray-500">사유</th>
              </tr>
            </thead>
            <tbody>
              {data.details?.slice(0, 15).map((d: any, index: number) => (
                <tr key={index} className="border-b border-gray-100">
                  <td className="px-4 py-2 font-mono text-blue-600">{d.application_id}</td>
                  <td className="px-4 py-2 text-center">{CellFormatters.grade(d.system_grade)}</td>
                  <td className="px-4 py-2 text-center">{CellFormatters.grade(d.override_grade)}</td>
                  <td className="px-4 py-2 text-center">
                    <span className={`inline-flex items-center ${
                      d.direction === 'UPGRADE' ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {d.direction === 'UPGRADE' ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-center">
                    <Badge variant={
                      d.outcome === 'PERFORMING' ? 'success' :
                      d.outcome === 'DEFAULT' || d.outcome === 'NPL' ? 'danger' :
                      d.outcome === 'DELINQUENT' ? 'warning' : 'gray'
                    }>
                      {d.outcome || '미확정'}
                    </Badge>
                  </td>
                  <td className="px-4 py-2 text-center">
                    {d.correct === true ? (
                      <CheckCircle className="text-green-500 mx-auto" size={18} />
                    ) : d.correct === false ? (
                      <XCircle className="text-red-500 mx-auto" size={18} />
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-gray-600 max-w-xs truncate">{d.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

// Vintage 분석 탭
function VintageTab({ data }: { data: any }) {
  if (!data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // 월별 트렌드 차트
  const trendData = data.monthly_trend?.slice(-12) || [];

  // 코호트별 요약
  const summaryByType = data.summary_by_type || [];

  return (
    <div className="space-y-6">
      {/* 요약 */}
      <div className="grid grid-cols-4 gap-4">
        {summaryByType.map((s: any, index: number) => (
          <StatCard
            key={index}
            title={s.cohort_type === 'OVERALL' ? '전체 평균' : s.cohort_type === 'GRADE' ? '등급별' : '업종별'}
            value={`${s.avg_mob12_default?.toFixed(2) || 0}%`}
            subtitle={`MOB12 부도율 (누적 손실: ${s.avg_cumulative_loss?.toFixed(2) || 0}%)`}
            icon={<Calendar size={24} />}
            color={s.cohort_type === 'OVERALL' ? 'blue' : s.cohort_type === 'GRADE' ? 'yellow' : 'green'}
          />
        ))}
        <StatCard
          title="분석 빈티지"
          value={`${data.vintages?.length || 0}개`}
          subtitle="코호트 수"
          icon={<BarChart3 size={24} />}
          color="gray"
        />
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* 월별 연체율 추이 */}
        <Card title="월별 연체/부도율 추이">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" fontSize={11} />
              <YAxis unit="%" />
              <Tooltip formatter={(value: any) => `${value}%`} />
              <Legend />
              <Line type="monotone" dataKey="mob3" name="MOB3 연체" stroke="#3B82F6" strokeWidth={2} />
              <Line type="monotone" dataKey="mob6" name="MOB6 연체" stroke="#F59E0B" strokeWidth={2} />
              <Line type="monotone" dataKey="mob12_dr" name="MOB12 부도" stroke="#EF4444" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        {/* 코호트별 손실률 */}
        <Card title="코호트별 누적 손실률 비교">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={summaryByType}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="cohort_type" />
              <YAxis unit="%" />
              <Tooltip formatter={(value: any) => `${value}%`} />
              <Legend />
              <Bar dataKey="avg_mob3_delinquency" name="MOB3 연체" fill="#3B82F6" />
              <Bar dataKey="avg_mob6_delinquency" name="MOB6 연체" fill="#F59E0B" />
              <Bar dataKey="avg_cumulative_loss" name="누적 손실" fill="#EF4444" />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* 빈티지 상세 테이블 */}
      <Card title="빈티지 상세">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="px-4 py-2 text-left font-medium text-gray-500">빈티지</th>
                <th className="px-4 py-2 text-left font-medium text-gray-500">코호트</th>
                <th className="px-4 py-2 text-right font-medium text-gray-500">건수</th>
                <th className="px-4 py-2 text-right font-medium text-gray-500">금액(백만)</th>
                <th className="px-4 py-2 text-right font-medium text-gray-500">MOB3</th>
                <th className="px-4 py-2 text-right font-medium text-gray-500">MOB6</th>
                <th className="px-4 py-2 text-right font-medium text-gray-500">MOB12 DR</th>
                <th className="px-4 py-2 text-right font-medium text-gray-500">누적손실</th>
              </tr>
            </thead>
            <tbody>
              {data.vintages?.slice(0, 20).map((v: any, index: number) => (
                <tr key={index} className="border-b border-gray-100">
                  <td className="px-4 py-2 font-medium">{v.month}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-1 rounded text-xs ${
                      v.cohort_type === 'OVERALL' ? 'bg-blue-100 text-blue-800' :
                      v.cohort_type === 'GRADE' ? 'bg-purple-100 text-purple-800' :
                      'bg-green-100 text-green-800'
                    }`}>
                      {v.cohort_type}: {v.cohort_value}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">{v.count?.toLocaleString()}</td>
                  <td className="px-4 py-2 text-right">{v.amount?.toLocaleString()}</td>
                  <td className="px-4 py-2 text-right font-mono">
                    {v.mob_3_del_rate ? `${(v.mob_3_del_rate * 100).toFixed(2)}%` : '-'}
                  </td>
                  <td className="px-4 py-2 text-right font-mono">
                    {v.mob_6_del_rate ? `${(v.mob_6_del_rate * 100).toFixed(2)}%` : '-'}
                  </td>
                  <td className={`px-4 py-2 text-right font-mono ${
                    v.mob_12_dr && v.mob_12_dr > 0.03 ? 'text-red-600 font-semibold' : ''
                  }`}>
                    {v.mob_12_dr ? `${(v.mob_12_dr * 100).toFixed(2)}%` : '-'}
                  </td>
                  <td className="px-4 py-2 text-right font-mono">
                    {v.loss_rate ? `${(v.loss_rate * 100).toFixed(2)}%` : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* 분석 설명 */}
      <Card title="Vintage 분석 개요">
        <div className="bg-gray-50 rounded-lg p-4">
          <p className="text-sm text-gray-700 mb-3">{data.analysis_info?.description}</p>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-gray-500 mb-1">MOB 기간</p>
              <p className="font-medium">{data.analysis_info?.mob_periods?.join(', ')}</p>
            </div>
            <div>
              <p className="text-gray-500 mb-1">코호트 유형</p>
              <p className="font-medium">{data.analysis_info?.cohort_types?.join(', ')}</p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

// 모델 상세 사양 모달
function ModelSpecsModal({ specs, onClose }: { specs: any; onClose: () => void }) {
  const s = specs.specifications;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-[90%] max-w-5xl max-h-[90vh] overflow-hidden">
        {/* 헤더 */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gradient-to-r from-blue-600 to-blue-700">
          <div className="text-white">
            <h2 className="text-xl font-bold">{specs.model?.model_name}</h2>
            <p className="text-blue-100 text-sm">{s.korean_name} ({s.full_name})</p>
          </div>
          <button
            onClick={onClose}
            className="text-white hover:bg-white/20 rounded-full p-2 transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* 본문 */}
        <div className="overflow-y-auto max-h-[calc(90vh-80px)] p-6">
          {/* 개요 */}
          <section className="mb-8">
            <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center">
              <FileText className="mr-2 text-blue-600" size={20} />
              모델 개요
            </h3>
            <div className="bg-blue-50 rounded-lg p-4">
              <p className="text-gray-700">{s.description}</p>
              <div className="mt-3 grid grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-gray-500">모델 유형</p>
                  <p className="font-medium">{specs.model?.model_type}</p>
                </div>
                <div>
                  <p className="text-gray-500">위험 등급</p>
                  <p className="font-medium">{specs.model?.risk_tier}</p>
                </div>
                <div>
                  <p className="text-gray-500">담당 부서</p>
                  <p className="font-medium">{specs.model?.owner_dept}</p>
                </div>
                <div>
                  <p className="text-gray-500">상태</p>
                  <p className="font-medium">{specs.model?.status}</p>
                </div>
              </div>
            </div>
          </section>

          {/* Description (이론적 배경) */}
          {s.theoretical_background && (
            <section className="mb-8">
              <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center">
                <BookOpen className="mr-2 text-purple-600" size={20} />
                Description
              </h3>
              <div className="bg-gray-50 rounded-lg p-4 prose prose-sm max-w-none">
                <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans">
                  {s.theoretical_background}
                </pre>
              </div>
            </section>
          )}

          {/* Formula (수학 공식) */}
          {s.formulas && Object.keys(s.formulas).length > 0 && (
            <section className="mb-8">
              <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center">
                <span className="mr-2 text-green-600 text-xl">∑</span>
                Formula
              </h3>
              <div className="space-y-4">
                {Object.values(s.formulas).map((f: any, index: number) => (
                  <div key={index} className="bg-gradient-to-r from-gray-50 to-white border border-gray-200 rounded-lg p-4">
                    <h4 className="font-semibold text-gray-900 mb-2">{f.name}</h4>
                    <div className="bg-gray-900 text-green-400 rounded px-4 py-3 font-mono text-sm overflow-x-auto">
                      {f.formula}
                    </div>
                    <p className="text-sm text-gray-600 mt-2">{f.description}</p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* 주요 변수 */}
          {s.key_variables?.length > 0 && (
            <section className="mb-8">
              <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center">
                <Activity className="mr-2 text-orange-600" size={20} />
                주요 변수
              </h3>
              <div className="grid grid-cols-2 gap-3">
                {s.key_variables.map((v: any, index: number) => (
                  <div key={index} className="bg-orange-50 border border-orange-100 rounded-lg p-3">
                    <p className="font-medium text-orange-900">{v.name}</p>
                    <p className="text-sm text-orange-700">{v.examples}</p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* 장점/단점/한계 */}
          <section className="mb-8">
            <h3 className="text-lg font-bold text-gray-900 mb-3">장단점 및 한계</h3>
            <div className="grid grid-cols-3 gap-4">
              {/* 장점 */}
              <div className="bg-green-50 rounded-lg p-4">
                <h4 className="font-semibold text-green-800 mb-2 flex items-center">
                  <CheckCircle className="mr-2" size={16} />
                  장점
                </h4>
                <ul className="space-y-2">
                  {s.advantages?.map((a: string, index: number) => (
                    <li key={index} className="text-sm text-green-700 flex items-start">
                      <span className="text-green-500 mr-2">•</span>
                      {a}
                    </li>
                  ))}
                </ul>
              </div>

              {/* 단점 */}
              <div className="bg-yellow-50 rounded-lg p-4">
                <h4 className="font-semibold text-yellow-800 mb-2 flex items-center">
                  <AlertTriangle className="mr-2" size={16} />
                  단점
                </h4>
                <ul className="space-y-2">
                  {s.disadvantages?.map((d: string, index: number) => (
                    <li key={index} className="text-sm text-yellow-700 flex items-start">
                      <span className="text-yellow-500 mr-2">•</span>
                      {d}
                    </li>
                  ))}
                </ul>
              </div>

              {/* 한계 */}
              <div className="bg-red-50 rounded-lg p-4">
                <h4 className="font-semibold text-red-800 mb-2 flex items-center">
                  <XCircle className="mr-2" size={16} />
                  한계
                </h4>
                <ul className="space-y-2">
                  {s.limitations?.map((l: string, index: number) => (
                    <li key={index} className="text-sm text-red-700 flex items-start">
                      <span className="text-red-500 mr-2">•</span>
                      {l}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>

          {/* 규제 요건 */}
          {s.regulatory_requirements && (
            <section className="mb-4">
              <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center">
                <FileText className="mr-2 text-indigo-600" size={20} />
                규제 요건
              </h3>
              <div className="bg-indigo-50 rounded-lg p-4">
                <div className="grid grid-cols-2 gap-4">
                  {Object.entries(s.regulatory_requirements).map(([key, value]: [string, any]) => (
                    <div key={key}>
                      <p className="text-xs text-indigo-600 uppercase font-medium">{key}</p>
                      <p className="text-sm text-indigo-900">{value}</p>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          )}
        </div>

        {/* 푸터 */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}
