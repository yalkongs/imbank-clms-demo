import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2,
  TrendingUp,
  AlertTriangle,
  FileText,
  PiggyBank,
  Target,
  Activity,
  Users
} from 'lucide-react';
import { Card, StatCard, GaugeCard, TrendChart, DonutChart, COLORS, RegionFilter } from '../components';
import { dashboardApi } from '../utils/api';
import { formatAmount, formatPercent, formatNumber } from '../utils/format';

const REGIONS = [
  { value: '', label: '전체 지역' },
  { value: 'CAPITAL', label: '수도권' },
  { value: 'DAEGU_GB', label: '대구경북' },
  { value: 'BUSAN_GN', label: '부산경남' },
];

export default function Dashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [region, setRegion] = useState('');
  const [summary, setSummary] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [kpis, setKpis] = useState<any>(null);
  const [capitalTrend, setCapitalTrend] = useState<any[]>([]);

  useEffect(() => {
    loadData();
  }, [region]);

  const loadData = async () => {
    try {
      const r = region || undefined;
      const [summaryRes, alertsRes, kpisRes, trendRes] = await Promise.all([
        dashboardApi.getSummary(r),
        dashboardApi.getEWSAlerts(r),
        dashboardApi.getKPIs(r),
        dashboardApi.getCapitalTrend()
      ]);
      setSummary(summaryRes.data);
      setAlerts(alertsRes.data || []);
      setKpis(kpisRes.data);
      setCapitalTrend(trendRes.data || []);
    } catch (error) {
      console.error('Dashboard data load error:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const capital = summary?.capital || {};
  const portfolio = summary?.portfolio || {};
  const applications = summary?.applications || {};
  const alertSummary = summary?.alerts || {};

  // 포트폴리오 등급 분포 데이터
  const gradeDistribution = [
    { name: 'AAA~A', value: 35, color: '#1e40af' },
    { name: 'BBB', value: 30, color: '#10b981' },
    { name: 'BB', value: 20, color: '#f59e0b' },
    { name: 'B이하', value: 15, color: '#ef4444' }
  ];


  return (
    <div className="space-y-6">
      {/* 페이지 제목 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">기업여신 포트폴리오 현황 및 핵심 지표</p>
        </div>
        <div className="flex items-center space-x-4">
          <RegionFilter value={region} onChange={setRegion} />
          <div className="flex items-center space-x-2 text-sm text-gray-500">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
            <span>실시간 업데이트</span>
          </div>
        </div>
      </div>

      {/* 핵심 지표 카드 */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="총 여신 포트폴리오"
          value={formatAmount(portfolio.total_exposure || 0, 'billion')}
          subtitle={`${formatNumber(portfolio.total_customers || 0)}개 기업`}
          icon={<Building2 size={24} />}
          color="blue"
        />
        <StatCard
          title="BIS 자본비율"
          value={formatPercent(capital.bis_ratio || 0)}
          subtitle="규제비율 10.5%"
          change={0.5}
          icon={<PiggyBank size={24} />}
          color="green"
        />
        <StatCard
          title="평균 RAROC"
          value={formatPercent(portfolio.avg_raroc || 0)}
          subtitle="허들레이트 15%"
          icon={<Target size={24} />}
          color="blue"
        />
        <StatCard
          title="대기 심사건"
          value={`${applications.pending_count || 0}건`}
          subtitle={formatAmount(applications.pending_amount || 0, 'billion')}
          icon={<FileText size={24} />}
          color="yellow"
        />
      </div>

      {/* 자본비율 게이지 */}
      <div className="grid grid-cols-4 gap-4">
        <GaugeCard
          title="BIS 비율"
          value={capital.bis_ratio || 0}
          max={20}
          min={8}
          target={13}
          warning={11}
          critical={10.5}
        />
        <GaugeCard
          title="Tier1 비율"
          value={capital.tier1_ratio || 0}
          max={18}
          min={6}
          target={11}
          warning={9}
          critical={8.5}
        />
        <GaugeCard
          title="CET1 비율"
          value={capital.cet1_ratio || 0}
          max={16}
          min={4}
          target={9}
          warning={7.5}
          critical={7}
        />
        <GaugeCard
          title="레버리지 비율"
          value={capital.leverage_ratio || 0}
          max={10}
          min={2}
          target={5}
          warning={4}
          critical={3}
        />
      </div>

      {/* 차트 영역 */}
      <div className="grid grid-cols-3 gap-6">
        {/* 자본비율 추이 */}
        <Card title="자본비율 추이" className="col-span-2">
          <TrendChart
            data={capitalTrend}
            lines={[
              { key: 'bis', name: 'BIS비율', color: COLORS.primary },
              { key: 'tier1', name: 'Tier1비율', color: COLORS.secondary },
              { key: 'cet1', name: 'CET1비율', color: COLORS.accent }
            ]}
            referenceLines={[
              { y: 10.5, label: '규제최소', color: COLORS.danger }
            ]}
            height={280}
          />
        </Card>

        {/* 등급분포 */}
        <Card title="포트폴리오 등급 분포">
          <DonutChart
            data={gradeDistribution}
            height={280}
            innerRadius={50}
            outerRadius={90}
            centerValue={portfolio.avg_rating || 'BBB'}
            centerText="평균등급"
          />
        </Card>
      </div>

      {/* 알림 및 KPI */}
      <div className="grid grid-cols-3 gap-6">
        {/* EWS 알림 */}
        <Card
          title="EWS 알림"
          className="col-span-2"
          headerAction={
            <span className="text-sm text-blue-600 cursor-pointer hover:underline">전체보기</span>
          }
        >
          {alerts.length > 0 ? (
            <div className="space-y-3">
              {alerts.slice(0, 5).map((alert: any, index: number) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer"
                >
                  <div className="flex items-center">
                    <div className={`p-2 rounded-lg mr-3 ${
                      alert.severity === 'HIGH' ? 'bg-red-100 text-red-600' :
                      alert.severity === 'MEDIUM' ? 'bg-yellow-100 text-yellow-600' :
                      'bg-blue-100 text-blue-600'
                    }`}>
                      <AlertTriangle size={16} />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{alert.customer_name}</p>
                      <p className="text-xs text-gray-500">{alert.alert_type}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`text-sm font-medium ${
                      alert.severity === 'HIGH' ? 'text-red-600' :
                      alert.severity === 'MEDIUM' ? 'text-yellow-600' :
                      'text-blue-600'
                    }`}>
                      {alert.severity}
                    </p>
                    <p className="text-xs text-gray-500">{alert.alert_date}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Activity size={48} className="mx-auto mb-3 text-gray-300" />
              <p>활성 알림이 없습니다</p>
            </div>
          )}
        </Card>

        {/* 주요 KPI */}
        <Card title="주요 KPI">
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 border-b border-gray-100">
              <span className="text-sm text-gray-600">가중평균 PD</span>
              <span className="text-sm font-semibold text-gray-900">
                {formatPercent(portfolio.weighted_pd * 100 || 0)}
              </span>
            </div>
            <div className="flex items-center justify-between p-3 border-b border-gray-100">
              <span className="text-sm text-gray-600">가중평균 LGD</span>
              <span className="text-sm font-semibold text-gray-900">
                {formatPercent(portfolio.weighted_lgd * 100 || 0)}
              </span>
            </div>
            <div className="flex items-center justify-between p-3 border-b border-gray-100">
              <span className="text-sm text-gray-600">총 RWA</span>
              <span className="text-sm font-semibold text-gray-900">
                {formatAmount(capital.total_rwa || 0, 'billion')}
              </span>
            </div>
            <div className="flex items-center justify-between p-3 border-b border-gray-100">
              <span className="text-sm text-gray-600">한도 경보</span>
              <span className={`text-sm font-semibold ${alertSummary.limit_breaches > 0 ? 'text-red-600' : 'text-green-600'}`}>
                {alertSummary.limit_breaches || 0}건
              </span>
            </div>
            <div className="flex items-center justify-between p-3">
              <span className="text-sm text-gray-600">모델 경보</span>
              <span className={`text-sm font-semibold ${alertSummary.model_alerts > 0 ? 'text-yellow-600' : 'text-green-600'}`}>
                {alertSummary.model_alerts || 0}건
              </span>
            </div>
          </div>
        </Card>
      </div>

      {/* 빠른 액션 버튼 */}
      <div className="grid grid-cols-4 gap-4">
        <button
          onClick={() => navigate('/applications')}
          className="flex items-center justify-center p-4 bg-white rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-colors group"
        >
          <FileText className="text-gray-400 group-hover:text-blue-600 mr-2" size={20} />
          <span className="text-sm font-medium text-gray-700 group-hover:text-blue-700">신규 심사</span>
        </button>
        <button
          onClick={() => navigate('/portfolio')}
          className="flex items-center justify-center p-4 bg-white rounded-lg border border-gray-200 hover:border-green-300 hover:bg-green-50 transition-colors group"
        >
          <TrendingUp className="text-gray-400 group-hover:text-green-600 mr-2" size={20} />
          <span className="text-sm font-medium text-gray-700 group-hover:text-green-700">포트폴리오 분석</span>
        </button>
        <button
          onClick={() => navigate('/stress-test')}
          className="flex items-center justify-center p-4 bg-white rounded-lg border border-gray-200 hover:border-purple-300 hover:bg-purple-50 transition-colors group"
        >
          <Activity className="text-gray-400 group-hover:text-purple-600 mr-2" size={20} />
          <span className="text-sm font-medium text-gray-700 group-hover:text-purple-700">스트레스 테스트</span>
        </button>
        <button
          onClick={() => navigate('/customers')}
          className="flex items-center justify-center p-4 bg-white rounded-lg border border-gray-200 hover:border-orange-300 hover:bg-orange-50 transition-colors group"
        >
          <Users className="text-gray-400 group-hover:text-orange-600 mr-2" size={20} />
          <span className="text-sm font-medium text-gray-700 group-hover:text-orange-700">고객 조회</span>
        </button>
      </div>
    </div>
  );
}
