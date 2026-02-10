import React, { useEffect, useState } from 'react';
import { AlertTriangle, TrendingUp, TrendingDown, Activity, BarChart3, Shield } from 'lucide-react';
import { Card, StatCard, DonutChart, COLORS } from '../../components';
import { ewsAdvancedApi } from '../../utils/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';

interface Props { region: string }

export default function EWSIntegratedDashboard({ region }: Props) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);

  useEffect(() => { loadData(); }, [region]);

  const loadData = async () => {
    setLoading(true);
    try {
      const r = region || undefined;
      const res = await ewsAdvancedApi.getIntegratedDashboard(r);
      setData(res.data);
    } catch (e) {
      console.error(e);
      setData(null);
    } finally { setLoading(false); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" /></div>;
  if (!data) return <div className="text-center text-gray-500 py-12">데이터를 불러올 수 없습니다.</div>;

  const gradeDist = data.grade_distribution || {};
  const gradeChartData = [
    { name: 'NORMAL', value: gradeDist['NORMAL'] || 0, color: COLORS.success },
    { name: 'WATCH', value: gradeDist['WATCH'] || 0, color: COLORS.warning },
    { name: 'WARNING', value: gradeDist['WARNING'] || 0, color: COLORS.danger },
    { name: 'CRITICAL', value: gradeDist['CRITICAL'] || 0, color: '#7f1d1d' },
  ].filter(d => d.value > 0);

  const cs = data.channel_scores || {};
  const channelBarData = [
    { name: '거래행태', score: cs.transaction || 0 },
    { name: '공적정보', score: cs.public_registry || 0 },
    { name: '시장신호', score: cs.market || 0 },
    { name: '뉴스감성', score: cs.news || 0 },
    { name: '공급망', score: cs.supply_chain || 0 },
    { name: '재무', score: cs.financial || 0 },
  ];

  const trendDist = data.trend_distribution || {};

  return (
    <div className="space-y-6">
      {/* 상단 StatCards */}
      <div className="grid grid-cols-5 gap-4">
        <StatCard title="모니터링 기업" value={data.total_monitored || 0} icon={<Activity size={22} />} color="blue" />
        <StatCard title="종합점수 평균" value={`${cs.composite || 0}점`} icon={<BarChart3 size={22} />} color="green" />
        <StatCard title="CRITICAL" value={gradeDist['CRITICAL'] || 0} subtitle="긴급 대응 필요" icon={<AlertTriangle size={22} />} color="red" />
        <StatCard title="WARNING" value={gradeDist['WARNING'] || 0} subtitle="주의 관찰" icon={<Shield size={22} />} color="yellow" />
        <StatCard title="악화 추세" value={trendDist['DETERIORATING'] || 0}
          subtitle={`개선 ${trendDist['IMPROVING'] || 0}`}
          icon={<TrendingDown size={22} />} color="red" />
      </div>

      {/* 차트 행 */}
      <div className="grid grid-cols-3 gap-6">
        <Card title="EWS 등급 분포">
          <DonutChart data={gradeChartData} height={220} innerRadius={45} outerRadius={75} />
        </Card>

        <Card title="채널별 평균 점수">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={channelBarData} layout="vertical" margin={{ left: 10, right: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" domain={[0, 100]} />
              <YAxis type="category" dataKey="name" width={60} tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v: number) => `${v.toFixed(1)}점`} />
              <Bar dataKey="score" fill={COLORS.primary} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="12개월 시그널 타임라인">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data.signal_timeline || []} margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="critical" name="CRITICAL" stroke="#7f1d1d" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="warning" name="WARNING" stroke={COLORS.danger} strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="watch" name="WATCH" stroke={COLORS.warning} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* 워치리스트 테이블 */}
      <Card title="Watchlist (WARNING / CRITICAL)">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 text-left">기업명</th>
                <th className="px-3 py-2 text-left">업종</th>
                <th className="px-3 py-2 text-center">종합점수</th>
                <th className="px-3 py-2 text-center">등급</th>
                <th className="px-3 py-2 text-center">추세</th>
                <th className="px-3 py-2 text-center">거래행태</th>
                <th className="px-3 py-2 text-center">공적정보</th>
                <th className="px-3 py-2 text-center">시장</th>
                <th className="px-3 py-2 text-center">뉴스</th>
              </tr>
            </thead>
            <tbody>
              {(data.watchlist || []).map((w: any) => (
                <tr key={w.customer_id} className="border-b hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium">{w.customer_name}</td>
                  <td className="px-3 py-2 text-gray-600">{w.industry_name}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-2 py-1 rounded font-semibold text-xs ${
                      w.composite_score < 35 ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                    }`}>{w.composite_score?.toFixed(1)}</span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      w.ews_grade === 'CRITICAL' ? 'bg-red-600 text-white' : 'bg-yellow-500 text-white'
                    }`}>{w.ews_grade}</span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    {w.score_trend === 'DETERIORATING' ? <TrendingDown className="inline text-red-500" size={16} /> :
                     w.score_trend === 'IMPROVING' ? <TrendingUp className="inline text-green-500" size={16} /> :
                     <span className="text-gray-400">-</span>}
                  </td>
                  <td className="px-3 py-2 text-center">{w.transaction_score?.toFixed(0) ?? '-'}</td>
                  <td className="px-3 py-2 text-center">{w.public_registry_score?.toFixed(0) ?? '-'}</td>
                  <td className="px-3 py-2 text-center">{w.market_score?.toFixed(0) ?? '-'}</td>
                  <td className="px-3 py-2 text-center">{w.news_score?.toFixed(0) ?? '-'}</td>
                </tr>
              ))}
              {(!data.watchlist || data.watchlist.length === 0) && (
                <tr><td colSpan={9} className="px-3 py-8 text-center text-gray-400">해당 조건의 워치리스트 기업이 없습니다.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
