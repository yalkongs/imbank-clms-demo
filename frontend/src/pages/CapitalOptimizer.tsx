import { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Target,
  AlertTriangle,
  CheckCircle,
  ArrowRight,
  BarChart3,
  PieChart,
  Lightbulb,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  DollarSign,
  Percent,
  Building2,
  Shield,
  Zap
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart as RePieChart,
  Pie,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  LineChart,
  Line
} from 'recharts';
import { capitalOptimizerApi } from '../utils/api';

const COLORS = {
  primary: '#1e40af',
  success: '#059669',
  warning: '#d97706',
  danger: '#dc2626',
  info: '#0891b2',
  purple: '#7c3aed',
  pink: '#db2777'
};

const PRIORITY_COLORS: Record<string, string> = {
  HIGH: 'bg-red-100 text-red-800 border-red-200',
  MEDIUM: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  LOW: 'bg-green-100 text-green-800 border-green-200'
};

const STRATEGY_COLORS: Record<string, string> = {
  EXPAND: 'bg-emerald-100 text-emerald-800',
  SELECTIVE: 'bg-blue-100 text-blue-800',
  MAINTAIN: 'bg-yellow-100 text-yellow-800',
  REDUCE: 'bg-orange-100 text-orange-800',
  EXIT: 'bg-red-100 text-red-800'
};

const RECOMMENDATION_COLORS: Record<string, string> = {
  EXPAND: 'text-emerald-600',
  PROMOTE: 'text-blue-600',
  MAINTAIN: 'text-gray-600',
  REDUCE: 'text-orange-600',
  RESTRUCTURE: 'text-red-600'
};

function formatAmount(value: number, unit: 'won' | 'billion' | 'million' = 'billion'): string {
  if (!value && value !== 0) return '-';
  if (unit === 'billion') {
    return `${(value / 100000000).toLocaleString(undefined, { maximumFractionDigits: 0 })}억`;
  }
  if (unit === 'million') {
    return `${(value / 1000000).toLocaleString(undefined, { maximumFractionDigits: 0 })}백만`;
  }
  return value.toLocaleString();
}

export default function CapitalOptimizer() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'rwa' | 'allocation' | 'rebalancing'>('dashboard');
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [rwaData, setRwaData] = useState<any>(null);
  const [allocationData, setAllocationData] = useState<any>(null);
  const [rebalancingData, setRebalancingData] = useState<any>(null);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    collateral: true,
    upgrade: true,
    allocation: true,
    rebalancing: true
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [dashboard, rwa, allocation, rebalancing] = await Promise.all([
        capitalOptimizerApi.getEfficiencyDashboard(),
        capitalOptimizerApi.getRwaOptimization(),
        capitalOptimizerApi.getAllocationOptimization(),
        capitalOptimizerApi.getRebalancingSuggestions()
      ]);
      setDashboardData(dashboard.data);
      setRwaData(rwa.data);
      setAllocationData(allocation.data);
      setRebalancingData(rebalancing.data);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="animate-spin text-blue-600" size={48} />
      </div>
    );
  }

  const tabs = [
    { id: 'dashboard', label: '효율성 대시보드', icon: <BarChart3 size={18} /> },
    { id: 'rwa', label: 'RWA 최적화', icon: <Target size={18} /> },
    { id: 'allocation', label: '자본배분 최적화', icon: <PieChart size={18} /> },
    { id: 'rebalancing', label: '리밸런싱 제안', icon: <RefreshCw size={18} /> }
  ];

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">자본활용성 최적화</h1>
          <p className="text-sm text-gray-500 mt-1">Capital Efficiency Optimizer - RWA 최적화, 자본배분 효율화, 포트폴리오 리밸런싱</p>
        </div>
        <button
          onClick={loadData}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <RefreshCw size={16} />
          새로고침
        </button>
      </div>

      {/* 탭 네비게이션 */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-4">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-3 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* 탭 컨텐츠 */}
      {activeTab === 'dashboard' && dashboardData && (
        <EfficiencyDashboard data={dashboardData} rwaData={rwaData} />
      )}
      {activeTab === 'rwa' && rwaData && (
        <RwaOptimization
          data={rwaData}
          expandedSections={expandedSections}
          toggleSection={toggleSection}
        />
      )}
      {activeTab === 'allocation' && allocationData && (
        <AllocationOptimizer data={allocationData} />
      )}
      {activeTab === 'rebalancing' && rebalancingData && (
        <RebalancingSuggestions data={rebalancingData} />
      )}
    </div>
  );
}

// 효율성 대시보드 컴포넌트
function EfficiencyDashboard({ data, rwaData }: { data: any; rwaData: any }) {
  const capitalMetrics = data.capital_metrics;
  const efficiencyMetrics = data.efficiency_metrics;
  const dealQuality = data.deal_quality;

  // 딜 품질 차트 데이터
  const dealQualityChart = [
    { name: '목표 초과\n(>15%)', value: dealQuality.above_target, color: COLORS.success },
    { name: '허들 충족\n(12-15%)', value: dealQuality.meet_hurdle, color: COLORS.info },
    { name: '허들 미달\n(<12%)', value: dealQuality.below_hurdle, color: COLORS.danger }
  ];

  // RWA 밀도 차트 (산업별)
  const rwaByIndustry = rwaData?.industry_analysis?.map((ind: any) => ({
    name: ind.industry.length > 6 ? ind.industry.slice(0, 6) + '..' : ind.industry,
    fullName: ind.industry,
    밀도: ind.rwa_density,
    RAROC: ind.raroc
  })) || [];

  return (
    <div className="space-y-6">
      {/* KPI 카드 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-gray-500">포트폴리오 RAROC</span>
            <Target className="text-blue-600" size={20} />
          </div>
          <div className="text-3xl font-bold text-gray-900">{efficiencyMetrics.portfolio_raroc}%</div>
          <div className="text-xs text-gray-500 mt-1">허들레이트 12% | 목표 15%</div>
          <div className={`mt-2 flex items-center gap-1 text-sm ${efficiencyMetrics.portfolio_raroc >= 15 ? 'text-green-600' : efficiencyMetrics.portfolio_raroc >= 12 ? 'text-blue-600' : 'text-red-600'}`}>
            {efficiencyMetrics.portfolio_raroc >= 15 ? <CheckCircle size={14} /> : <AlertTriangle size={14} />}
            {efficiencyMetrics.portfolio_raroc >= 15 ? '목표 초과' : efficiencyMetrics.portfolio_raroc >= 12 ? '허들 충족' : '개선 필요'}
          </div>
        </div>

        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-gray-500">RWA 밀도</span>
            <BarChart3 className="text-purple-600" size={20} />
          </div>
          <div className="text-3xl font-bold text-gray-900">{efficiencyMetrics.rwa_density}%</div>
          <div className="text-xs text-gray-500 mt-1">RWA / 익스포저 비율</div>
          <div className={`mt-2 flex items-center gap-1 text-sm ${efficiencyMetrics.rwa_density <= 50 ? 'text-green-600' : efficiencyMetrics.rwa_density <= 65 ? 'text-yellow-600' : 'text-red-600'}`}>
            {efficiencyMetrics.rwa_density <= 50 ? <TrendingDown size={14} /> : <TrendingUp size={14} />}
            {efficiencyMetrics.rwa_density <= 50 ? '효율적' : efficiencyMetrics.rwa_density <= 65 ? '보통' : '개선 필요'}
          </div>
        </div>

        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-gray-500">예산 소진율</span>
            <Percent className="text-orange-600" size={20} />
          </div>
          <div className="text-3xl font-bold text-gray-900">{efficiencyMetrics.budget_utilization}%</div>
          <div className="text-xs text-gray-500 mt-1">RWA 예산 대비 사용</div>
          <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${efficiencyMetrics.budget_utilization >= 90 ? 'bg-red-500' : efficiencyMetrics.budget_utilization >= 70 ? 'bg-yellow-500' : 'bg-green-500'}`}
              style={{ width: `${Math.min(efficiencyMetrics.budget_utilization, 100)}%` }}
            />
          </div>
        </div>

        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-gray-500">딜 품질비율</span>
            <CheckCircle className="text-green-600" size={20} />
          </div>
          <div className="text-3xl font-bold text-gray-900">{dealQuality.quality_ratio}%</div>
          <div className="text-xs text-gray-500 mt-1">허들레이트 충족 비율</div>
          <div className="mt-2 flex items-center gap-2 text-sm text-gray-600">
            <span className="text-green-600">{dealQuality.above_target + dealQuality.meet_hurdle}</span> /
            <span>{dealQuality.total_deals}건</span>
          </div>
        </div>
      </div>

      {/* 자본 현황 & 딜 품질 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 자본 현황 */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Shield className="text-blue-600" size={20} />
            자본 현황
          </h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">총자본</span>
              <span className="font-mono font-semibold">{formatAmount(capitalMetrics.total_capital)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">총 RWA</span>
              <span className="font-mono font-semibold">{formatAmount(capitalMetrics.total_rwa)}</span>
            </div>
            <div className="border-t pt-3 flex justify-between items-center">
              <span className="text-gray-600">BIS 비율</span>
              <span className={`font-mono font-bold text-lg ${capitalMetrics.bis_ratio >= 13 ? 'text-green-600' : capitalMetrics.bis_ratio >= 10.5 ? 'text-yellow-600' : 'text-red-600'}`}>
                {capitalMetrics.bis_ratio}%
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">CET1 비율</span>
              <span className={`font-mono font-bold text-lg ${capitalMetrics.cet1_ratio >= 10 ? 'text-green-600' : capitalMetrics.cet1_ratio >= 7 ? 'text-yellow-600' : 'text-red-600'}`}>
                {capitalMetrics.cet1_ratio}%
              </span>
            </div>
            <div className="bg-blue-50 rounded-lg p-3 mt-4">
              <div className="flex justify-between items-center">
                <span className="text-blue-700 text-sm font-medium">자본여력 (규제대비)</span>
                <span className="font-mono font-bold text-blue-700">{formatAmount(capitalMetrics.capital_buffer)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* 딜 품질 분포 */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <PieChart className="text-purple-600" size={20} />
            RAROC 분포 (딜 품질)
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <RePieChart>
                <Pie
                  data={dealQualityChart}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={3}
                  dataKey="value"
                  label={({ name, value }) => `${value}건`}
                >
                  {dealQualityChart.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </RePieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* 산업별 RWA 밀도 & RAROC */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Building2 className="text-orange-600" size={20} />
          산업별 RWA 밀도 vs RAROC
        </h3>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rwaByIndustry} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="left" orientation="left" stroke={COLORS.primary} />
              <YAxis yAxisId="right" orientation="right" stroke={COLORS.success} />
              <Tooltip
                formatter={(value: any, name: string) => [`${value}%`, name]}
                labelFormatter={(label: string, payload: any) => payload[0]?.payload?.fullName || label}
              />
              <Legend />
              <Bar yAxisId="left" dataKey="밀도" fill={COLORS.primary} name="RWA밀도(%)" radius={[4, 4, 0, 0]} />
              <Bar yAxisId="right" dataKey="RAROC" fill={COLORS.success} name="RAROC(%)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 최적화 기회 */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl p-6 border border-blue-100">
        <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Lightbulb className="text-yellow-500" size={20} />
          최적화 기회
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {data.optimization_opportunities.key_actions.map((action: string, idx: number) => (
            <div key={idx} className="bg-white rounded-lg p-4 shadow-sm">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-blue-700 font-bold text-sm">{idx + 1}</span>
                </div>
                <p className="text-sm text-gray-700">{action}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 flex gap-4 text-sm">
          <div className="bg-white rounded-lg px-4 py-2">
            <span className="text-gray-500">RWA 절감 잠재력: </span>
            <span className="font-bold text-blue-700">{data.optimization_opportunities.rwa_reduction_potential}</span>
          </div>
          <div className="bg-white rounded-lg px-4 py-2">
            <span className="text-gray-500">RAROC 개선 잠재력: </span>
            <span className="font-bold text-green-700">{data.optimization_opportunities.raroc_improvement_potential}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// RWA 최적화 컴포넌트
function RwaOptimization({
  data,
  expandedSections,
  toggleSection
}: {
  data: any;
  expandedSections: Record<string, boolean>;
  toggleSection: (s: string) => void;
}) {
  const summary = data.summary;

  return (
    <div className="space-y-6">
      {/* 요약 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="text-sm text-gray-500 mb-1">총 포트폴리오 RWA</div>
          <div className="text-2xl font-bold text-gray-900">{formatAmount(summary.total_portfolio_rwa)}</div>
        </div>
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="text-sm text-gray-500 mb-1">고밀도 세그먼트 RWA</div>
          <div className="text-2xl font-bold text-orange-600">{formatAmount(summary.high_density_segment_rwa)}</div>
          <div className="text-xs text-gray-500">전체의 {summary.high_density_ratio}%</div>
        </div>
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="text-sm text-gray-500 mb-1">담보 최적화 기회</div>
          <div className="text-2xl font-bold text-blue-600">{formatAmount(summary.potential_rwa_reduction.collateral_optimization)}</div>
        </div>
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="text-sm text-gray-500 mb-1">등급개선 기회</div>
          <div className="text-2xl font-bold text-green-600">{formatAmount(summary.potential_rwa_reduction.rating_upgrade)}</div>
        </div>
      </div>

      {/* 산업별 분석 테이블 */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-4 border-b border-gray-100">
          <h3 className="font-semibold text-gray-900">산업별 RWA 밀도 분석</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">산업</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600">익스포저</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600">RWA</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600">RWA 밀도</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600">RAROC</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600">우선순위</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.industry_analysis.map((ind: any) => (
                <tr key={ind.industry_code} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{ind.industry}</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-600">{formatAmount(ind.exposure)}</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-600">{formatAmount(ind.rwa)}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      ind.rwa_density > 65 ? 'bg-red-100 text-red-700' :
                      ind.rwa_density > 50 ? 'bg-yellow-100 text-yellow-700' :
                      'bg-green-100 text-green-700'
                    }`}>
                      {ind.rwa_density}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`font-semibold ${ind.raroc >= 15 ? 'text-green-600' : ind.raroc >= 12 ? 'text-blue-600' : 'text-red-600'}`}>
                      {ind.raroc}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-1 rounded text-xs font-medium border ${PRIORITY_COLORS[ind.optimization_priority as keyof typeof PRIORITY_COLORS]}`}>
                      {ind.optimization_priority}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 담보 최적화 기회 */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <button
          onClick={() => toggleSection('collateral')}
          className="w-full p-4 border-b border-gray-100 flex items-center justify-between hover:bg-gray-50"
        >
          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
            <Shield className="text-blue-600" size={18} />
            담보 확보 우선 대상 (LGD 개선 기회)
          </h3>
          {expandedSections.collateral ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </button>
        {expandedSections.collateral && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">신청ID</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">고객명</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">산업</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600">익스포저</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600">현재 LGD</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600">현재 RWA</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600">담보시 RWA</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600">절감액</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.collateral_opportunities.map((opp: any) => (
                  <tr key={opp.application_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-sm text-blue-600">{opp.application_id}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{opp.customer_name}</td>
                    <td className="px-4 py-3 text-gray-600">{opp.industry}</td>
                    <td className="px-4 py-3 text-right font-mono text-gray-600">{formatAmount(opp.exposure)}</td>
                    <td className="px-4 py-3 text-center">
                      <span className="px-2 py-1 rounded bg-red-100 text-red-700 text-xs font-medium">
                        {opp.current_lgd}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-gray-600">{formatAmount(opp.current_rwa)}</td>
                    <td className="px-4 py-3 text-right font-mono text-blue-600">{formatAmount(opp.potential_rwa_if_collateralized)}</td>
                    <td className="px-4 py-3 text-right font-mono font-semibold text-green-600">
                      -{formatAmount(opp.rwa_savings)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 등급 업그레이드 후보 */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <button
          onClick={() => toggleSection('upgrade')}
          className="w-full p-4 border-b border-gray-100 flex items-center justify-between hover:bg-gray-50"
        >
          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
            <TrendingUp className="text-green-600" size={18} />
            등급 업그레이드 후보 (BBB급 중 우량 기업)
          </h3>
          {expandedSections.upgrade ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </button>
        {expandedSections.upgrade && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">고객ID</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">고객명</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">산업</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600">현재등급</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600">PD</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600">총익스포저</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600">자산규모</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">권고</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.upgrade_candidates.map((cand: any) => (
                  <tr key={cand.customer_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-sm text-gray-600">{cand.customer_id}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{cand.customer_name}</td>
                    <td className="px-4 py-3 text-gray-600">{cand.industry}</td>
                    <td className="px-4 py-3 text-center">
                      <span className="px-2 py-1 rounded bg-yellow-100 text-yellow-700 text-xs font-medium">
                        {cand.current_grade}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center font-mono text-sm">{cand.current_pd}%</td>
                    <td className="px-4 py-3 text-right font-mono text-gray-600">{formatAmount(cand.total_exposure)}</td>
                    <td className="px-4 py-3 text-right font-mono text-gray-600">{formatAmount(cand.asset_size)}</td>
                    <td className="px-4 py-3 text-sm text-blue-600">{cand.recommendation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// 자본배분 최적화 컴포넌트
function AllocationOptimizer({ data }: { data: any }) {
  const summary = data.summary;
  const allocations = data.allocation_analysis;
  const suggestions = data.reallocation_suggestions;

  return (
    <div className="space-y-6">
      {/* 요약 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="text-sm text-gray-500 mb-1">총 RWA 예산</div>
          <div className="text-2xl font-bold text-gray-900">{formatAmount(summary.total_rwa_budget)}</div>
        </div>
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="text-sm text-gray-500 mb-1">총 RWA 사용</div>
          <div className="text-2xl font-bold text-blue-600">{formatAmount(summary.total_rwa_used)}</div>
          <div className="text-xs text-gray-500">활용률 {summary.overall_utilization}%</div>
        </div>
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="text-sm text-gray-500 mb-1">확대 추천 세그먼트</div>
          <div className="text-2xl font-bold text-green-600">{summary.expand_candidates}개</div>
        </div>
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="text-sm text-gray-500 mb-1">축소 검토 세그먼트</div>
          <div className="text-2xl font-bold text-red-600">{summary.reduce_candidates}개</div>
        </div>
      </div>

      {/* 배분 분석 테이블 */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-4 border-b border-gray-100">
          <h3 className="font-semibold text-gray-900">세그먼트별 배분 효율성</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">세그먼트</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600">RWA 예산</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600">RWA 사용</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600">활용률</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600">RAROC 목표</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600">RAROC 실적</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600">효율점수</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600">권고</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {allocations.map((alloc: any) => (
                <tr key={alloc.segment_code} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{alloc.segment}</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-600">{formatAmount(alloc.rwa_budget)}</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-600">{formatAmount(alloc.rwa_used)}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <div className="w-16 bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${alloc.utilization_rate >= 90 ? 'bg-red-500' : alloc.utilization_rate >= 70 ? 'bg-yellow-500' : 'bg-green-500'}`}
                          style={{ width: `${Math.min(alloc.utilization_rate, 100)}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-600">{alloc.utilization_rate}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center text-gray-600">{alloc.raroc_target}%</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`font-semibold ${alloc.raroc_actual >= alloc.raroc_target ? 'text-green-600' : alloc.raroc_actual >= summary.hurdle_rate ? 'text-blue-600' : 'text-red-600'}`}>
                      {alloc.raroc_actual}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center font-mono font-semibold text-purple-600">
                    {alloc.efficiency_score.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-sm font-medium ${RECOMMENDATION_COLORS[alloc.recommendation]}`}>
                      {alloc.recommendation}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 재배분 제안 */}
      {suggestions.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-4 border-b border-gray-100">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <ArrowRight className="text-blue-600" size={18} />
              재배분 제안
            </h3>
          </div>
          <div className="p-4 space-y-3">
            {suggestions.map((sug: any, idx: number) => (
              <div key={idx} className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <span className="px-3 py-1 bg-red-100 text-red-700 rounded font-medium text-sm">
                      {sug.from_segment}
                    </span>
                    <ArrowRight className="text-gray-400" size={20} />
                    <span className="px-3 py-1 bg-green-100 text-green-700 rounded font-medium text-sm">
                      {sug.to_segment}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mt-2">{sug.reason}</p>
                </div>
                <div className="text-right">
                  <div className="font-mono font-bold text-lg text-blue-600">{formatAmount(sug.rwa_amount)}</div>
                  <div className="text-xs text-green-600">RAROC +{sug.expected_raroc_gain}%p</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// 리밸런싱 제안 컴포넌트
function RebalancingSuggestions({ data }: { data: any }) {
  const summary = data.portfolio_summary;
  const actions = data.rebalancing_actions;
  const recommendations = data.strategic_recommendations;

  return (
    <div className="space-y-6">
      {/* 포트폴리오 요약 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="text-sm text-gray-500 mb-1">총 익스포저</div>
          <div className="text-2xl font-bold text-gray-900">{formatAmount(summary.total_exposure)}</div>
        </div>
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="text-sm text-gray-500 mb-1">산업 수</div>
          <div className="text-2xl font-bold text-blue-600">{summary.industry_count}개</div>
        </div>
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="text-sm text-gray-500 mb-1">HHI 지수</div>
          <div className="text-2xl font-bold text-purple-600">{summary.hhi_index}</div>
          <div className={`text-xs ${summary.concentration_status === 'HIGH' ? 'text-red-600' : summary.concentration_status === 'MODERATE' ? 'text-yellow-600' : 'text-green-600'}`}>
            집중도: {summary.concentration_status}
          </div>
        </div>
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="text-sm text-gray-500 mb-1">액션 필요</div>
          <div className="flex gap-2 mt-2">
            <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs font-medium">
              HIGH {data.summary_by_priority.high}
            </span>
            <span className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded text-xs font-medium">
              MED {data.summary_by_priority.medium}
            </span>
          </div>
        </div>
      </div>

      {/* 전략적 권고사항 */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-100">
        <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Zap className="text-yellow-500" size={20} />
          전략적 권고사항
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {recommendations.map((rec: any, idx: number) => (
            <div key={idx} className="bg-white rounded-lg p-4 shadow-sm">
              <div className="text-xs font-medium text-blue-600 mb-2">{rec.category}</div>
              <p className="text-sm text-gray-700 mb-2">{rec.recommendation}</p>
              <div className="text-xs text-green-600 font-medium">기대효과: {rec.expected_impact}</div>
            </div>
          ))}
        </div>
      </div>

      {/* 리밸런싱 액션 */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-4 border-b border-gray-100">
          <h3 className="font-semibold text-gray-900">산업별 리밸런싱 액션</h3>
        </div>
        <div className="divide-y divide-gray-100">
          {actions.map((action: any) => (
            <div key={action.industry_code} className="p-4 hover:bg-gray-50">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="font-semibold text-gray-900">{action.industry}</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${STRATEGY_COLORS[action.strategy]}`}>
                      {action.strategy}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium border ${PRIORITY_COLORS[action.priority]}`}>
                      {action.priority}
                    </span>
                  </div>
                  <div className="flex gap-6 text-sm text-gray-600 mb-3">
                    <span>익스포저: {formatAmount(action.current_exposure)}</span>
                    <span>집중도: {action.concentration}%</span>
                    <span>RWA밀도: {action.rwa_density}%</span>
                    <span className={action.raroc >= 12 ? 'text-green-600' : 'text-red-600'}>RAROC: {action.raroc}%</span>
                    <span>한도사용: {action.limit_utilization}%</span>
                  </div>
                  <div className="space-y-2">
                    {action.actions.map((act: any, idx: number) => (
                      <div key={idx} className="flex items-start gap-2 bg-gray-50 rounded p-3">
                        <AlertTriangle className={`flex-shrink-0 mt-0.5 ${action.priority === 'HIGH' ? 'text-red-500' : 'text-yellow-500'}`} size={16} />
                        <div>
                          <div className="text-sm font-medium text-gray-700">{act.type}</div>
                          <div className="text-xs text-gray-600">{act.description}</div>
                          <div className="text-xs text-blue-600 font-medium mt-1">목표: {act.target}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
