import React, { useEffect, useState } from 'react';
import {
  Leaf,
  TrendingUp,
  Building,
  Award,
  AlertTriangle,
  BarChart3,
  Droplet,
  Users
} from 'lucide-react';
import { Card, StatCard, GroupedBarChart, DonutChart, COLORS, FeatureModal, HelpButton } from '../components';
import { esgApi } from '../utils/api';
import { formatAmount, formatPercent } from '../utils/format';

export default function ESG() {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>(null);
  const [assessments, setAssessments] = useState<any[]>([]);
  const [greenFinance, setGreenFinance] = useState<any[]>([]);
  const [gradeDistribution, setGradeDistribution] = useState<any[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<any>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [featureInfo, setFeatureInfo] = useState<any>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [dashRes, assessRes, greenRes, gradeRes] = await Promise.all([
        esgApi.getDashboard(),
        esgApi.getAssessments({ limit: 20 }),
        esgApi.getGreenFinance(),
        esgApi.getGradeDistribution()
      ]);
      setDashboard(dashRes.data);
      setAssessments(assessRes.data.assessments || []);
      setGreenFinance(greenRes.data.green_products || greenRes.data.products || []);
      setGradeDistribution(gradeRes.data.grade_distribution || gradeRes.data.distribution || []);
    } catch (error) {
      console.error('ESG data load error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadCustomerESG = async (customerId: string) => {
    try {
      const res = await esgApi.getAssessment(customerId);
      setSelectedCustomer(res.data);
    } catch (error) {
      console.error('Customer ESG load error:', error);
    }
  };

  const openFeatureModal = async (featureId: string) => {
    try {
      const res = await esgApi.getFeatureDescription(featureId);
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

  // Grade distribution for chart - API returns { grade: 'A', count: 10, ... }
  const gradeDist = gradeDistribution.map((d: any) => ({
    name: d.grade || d.esg_grade,
    value: d.count,
    color: (d.grade || d.esg_grade) === 'A' ? COLORS.success :
           (d.grade || d.esg_grade) === 'B' ? COLORS.primary :
           (d.grade || d.esg_grade) === 'C' ? COLORS.warning : COLORS.danger
  })).filter(d => d.value > 0);

  // Score comparison chart data - API returns e_score, s_score, g_score
  const scoreComparisonData = assessments.slice(0, 10).map((a: any) => ({
    name: a.customer_name?.substring(0, 6) || '',
    환경: a.e_score || a.environmental_score,
    사회: a.s_score || a.social_score,
    지배구조: a.g_score || a.governance_score
  }));

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            ESG 리스크 관리
            <HelpButton onClick={() => openFeatureModal('esg_overview')} />
          </h1>
          <p className="text-sm text-gray-500 mt-1">ESG 평가, 탄소배출 모니터링, 녹색금융</p>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-5 gap-4">
        <StatCard
          title="평균 ESG 점수"
          value={(dashboard?.summary?.avg_esg_score || 0).toFixed(1)}
          subtitle="100점 만점"
          icon={<Award size={24} />}
          color={(dashboard?.summary?.avg_esg_score || 0) >= 70 ? 'green' : (dashboard?.summary?.avg_esg_score || 0) >= 50 ? 'yellow' : 'red'}
        />
        <StatCard
          title="우수등급 기업"
          value={dashboard?.summary?.high_grade_count || 0}
          subtitle="A~B등급"
          icon={<TrendingUp size={24} />}
          color="green"
        />
        <StatCard
          title="저등급 기업"
          value={dashboard?.summary?.low_grade_count || 0}
          subtitle="D~E등급"
          icon={<AlertTriangle size={24} />}
          color="red"
        />
        <StatCard
          title="녹색금융 규모"
          value={formatAmount(dashboard?.green_finance?.total_outstanding || 0, 'billion')}
          icon={<Leaf size={24} />}
          color="green"
        />
        <StatCard
          title="총 평가 기업"
          value={dashboard?.summary?.total_assessed || 0}
          icon={<Users size={24} />}
          color="blue"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-3 gap-6">
        {/* Grade Distribution */}
        <Card title="ESG 등급 분포">
          <DonutChart
            data={gradeDist}
            height={240}
            innerRadius={50}
            outerRadius={80}
          />
        </Card>

        {/* Score Comparison */}
        <Card
          title="기업별 ESG 점수 비교"
          headerAction={<HelpButton onClick={() => openFeatureModal('esg_overview')} size="sm" />}
          className="col-span-2"
        >
          <GroupedBarChart
            data={scoreComparisonData}
            bars={[
              { key: '환경', name: 'E (환경)', color: COLORS.success },
              { key: '사회', name: 'S (사회)', color: COLORS.primary },
              { key: '지배구조', name: 'G (지배구조)', color: COLORS.warning }
            ]}
            xAxisKey="name"
            height={240}
            showLegend
          />
        </Card>
      </div>

      {/* ESG Assessments Table */}
      <Card title="ESG 평가 현황">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 text-left">기업명</th>
                <th className="px-3 py-2 text-center">ESG 등급</th>
                <th className="px-3 py-2 text-center">통합점수</th>
                <th className="px-3 py-2 text-center">E (환경)</th>
                <th className="px-3 py-2 text-center">S (사회)</th>
                <th className="px-3 py-2 text-center">G (지배구조)</th>
                <th className="px-3 py-2 text-right">탄소집약도</th>
                <th className="px-3 py-2 text-center">ESG 추세</th>
                <th className="px-3 py-2 text-center">PD 조정</th>
              </tr>
            </thead>
            <tbody>
              {assessments.map((a: any) => (
                <tr
                  key={a.assessment_id}
                  className={`border-b hover:bg-gray-50 cursor-pointer ${
                    selectedCustomer?.customer_id === a.customer_id ? 'bg-blue-50' : ''
                  }`}
                  onClick={() => loadCustomerESG(a.customer_id)}
                >
                  <td className="px-3 py-2 font-medium">{a.customer_name}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                      a.esg_grade === 'A' ? 'bg-green-100 text-green-700' :
                      a.esg_grade === 'B' ? 'bg-blue-100 text-blue-700' :
                      a.esg_grade === 'C' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-red-100 text-red-700'
                    }`}>
                      {a.esg_grade}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center font-semibold">{a.esg_score?.toFixed(1)}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={(a.e_score || 0) >= 70 ? 'text-green-600' : (a.e_score || 0) >= 50 ? 'text-yellow-600' : 'text-red-600'}>
                      {a.e_score?.toFixed(1)}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className={(a.s_score || 0) >= 70 ? 'text-green-600' : (a.s_score || 0) >= 50 ? 'text-yellow-600' : 'text-red-600'}>
                      {a.s_score?.toFixed(1)}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className={(a.g_score || 0) >= 70 ? 'text-green-600' : (a.g_score || 0) >= 50 ? 'text-yellow-600' : 'text-red-600'}>
                      {a.g_score?.toFixed(1)}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right text-gray-600">{((a.carbon_intensity || 0) / 10).toFixed(1)}kg/백만원</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      a.esg_trend === 'DECLINING' ? 'bg-red-100 text-red-700' :
                      a.esg_trend === 'STABLE' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-green-100 text-green-700'
                    }`}>
                      {a.esg_trend}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      (a.pd_adjustment || 0) > 0 ? 'bg-red-100 text-red-700' :
                      (a.pd_adjustment || 0) < 0 ? 'bg-green-100 text-green-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {(a.pd_adjustment || 0) > 0 ? '+' : ''}{((a.pd_adjustment || 0) * 100).toFixed(2)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Green Finance */}
      <Card
        title="녹색금융 상품"
        headerAction={<HelpButton onClick={() => openFeatureModal('green_finance')} size="sm" />}
      >
        <div className="grid grid-cols-3 gap-4">
          {greenFinance.map((product: any) => (
            <div key={product.green_id} className="p-4 bg-green-50 rounded-lg border border-green-200">
              <div className="flex items-center justify-between mb-2">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                  product.green_category === 'RENEWABLE_ENERGY' ? 'bg-green-100 text-green-700' :
                  product.green_category === 'ENERGY_EFFICIENCY' ? 'bg-blue-100 text-blue-700' :
                  product.green_category === 'GREEN_BUILDING' ? 'bg-purple-100 text-purple-700' :
                  'bg-yellow-100 text-yellow-700'
                }`}>
                  {product.green_category}
                </span>
                <span className={`px-2 py-0.5 rounded text-xs ${
                  product.status === 'ACTIVE' ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-700'
                }`}>
                  {product.status}
                </span>
              </div>
              <p className="text-sm font-medium text-gray-900">{product.customer_name}</p>
              <p className="text-lg font-bold text-green-600 mt-2">{formatAmount(product.approved_amount || product.outstanding_amount, 'billion')}</p>
              <div className="mt-3 space-y-1 text-xs text-gray-600">
                <p>RWA 할인: {(product.rwa_discount_pct || 0).toFixed(1)}%</p>
                <p>금리혜택: {(product.rate_discount_bp || 0)}bp</p>
              </div>
              {product.certification_type && (
                <p className="mt-2 text-xs text-gray-500 bg-white p-2 rounded">
                  인증: {product.certification_type}
                </p>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Customer ESG Detail */}
      {selectedCustomer && (
        <Card
          title={`ESG 상세: ${selectedCustomer.customer_name}`}
          headerAction={
            <button
              onClick={() => setSelectedCustomer(null)}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              닫기
            </button>
          }
        >
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="p-4 bg-green-50 rounded-lg border border-green-200 text-center">
              <p className="text-sm text-green-700">ESG 등급</p>
              <p className={`text-3xl font-bold ${
                selectedCustomer.esg_grade === 'A' ? 'text-green-600' :
                selectedCustomer.esg_grade === 'B' ? 'text-blue-600' :
                selectedCustomer.esg_grade === 'C' ? 'text-yellow-600' : 'text-red-600'
              }`}>
                {selectedCustomer.esg_grade}
              </p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">환경 (E)</p>
              <p className="text-2xl font-bold">{selectedCustomer.environmental_score?.toFixed(1)}</p>
              <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div className="h-full bg-green-500" style={{ width: `${selectedCustomer.environmental_score}%` }} />
              </div>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">사회 (S)</p>
              <p className="text-2xl font-bold">{selectedCustomer.social_score?.toFixed(1)}</p>
              <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500" style={{ width: `${selectedCustomer.social_score}%` }} />
              </div>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">지배구조 (G)</p>
              <p className="text-2xl font-bold">{selectedCustomer.governance_score?.toFixed(1)}</p>
              <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div className="h-full bg-yellow-500" style={{ width: `${selectedCustomer.governance_score}%` }} />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center mb-2">
                <Droplet className="text-blue-600 mr-2" size={20} />
                <span className="font-medium">탄소배출</span>
              </div>
              <p className="text-xl font-bold">{(selectedCustomer.carbon_emission / 1000).toFixed(1)}천톤</p>
              <p className="text-xs text-gray-500 mt-1">연간 CO2 배출량</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center mb-2">
                <AlertTriangle className={`mr-2 ${
                  selectedCustomer.transition_risk === 'HIGH' ? 'text-red-600' :
                  selectedCustomer.transition_risk === 'MEDIUM' ? 'text-yellow-600' : 'text-green-600'
                }`} size={20} />
                <span className="font-medium">전환 리스크</span>
              </div>
              <p className={`text-xl font-bold ${
                selectedCustomer.transition_risk === 'HIGH' ? 'text-red-600' :
                selectedCustomer.transition_risk === 'MEDIUM' ? 'text-yellow-600' : 'text-green-600'
              }`}>{selectedCustomer.transition_risk}</p>
              <p className="text-xs text-gray-500 mt-1">저탄소 전환 리스크</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center mb-2">
                <Building className={`mr-2 ${
                  selectedCustomer.physical_risk === 'HIGH' ? 'text-red-600' :
                  selectedCustomer.physical_risk === 'MEDIUM' ? 'text-yellow-600' : 'text-green-600'
                }`} size={20} />
                <span className="font-medium">물리적 리스크</span>
              </div>
              <p className={`text-xl font-bold ${
                selectedCustomer.physical_risk === 'HIGH' ? 'text-red-600' :
                selectedCustomer.physical_risk === 'MEDIUM' ? 'text-yellow-600' : 'text-green-600'
              }`}>{selectedCustomer.physical_risk}</p>
              <p className="text-xs text-gray-500 mt-1">기후변화 물리적 영향</p>
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
