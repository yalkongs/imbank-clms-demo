import React, { useEffect, useState } from 'react';
import { TrendingUp, BarChart3, AlertTriangle, Activity } from 'lucide-react';
import { Card, StatCard } from '../../components';
import { ewsAdvancedApi } from '../../utils/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface Props { region: string }

export default function EWSMarketSignals({ region }: Props) {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [customerData, setCustomerData] = useState<any>(null);

  useEffect(() => { loadData(); }, [region]);

  const loadData = async () => {
    setLoading(true);
    try {
      const r = region || undefined;
      const [dashRes, alertRes] = await Promise.all([
        ewsAdvancedApi.getMarketDashboard(r),
        ewsAdvancedApi.getMarketAlerts(r),
      ]);
      setDashboard(dashRes.data);
      setAlerts(alertRes.data.alerts || []);
    } catch (e) {
      console.error(e);
      setDashboard(null);
      setAlerts([]);
    } finally { setLoading(false); }
  };

  const loadCustomer = async (cid: string) => {
    try {
      const res = await ewsAdvancedApi.getMarketCustomer(cid);
      setCustomerData(res.data);
    } catch (e) { console.error(e); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" /></div>;

  return (
    <div className="space-y-6">
      <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-2 text-sm text-blue-700">
        상장기업 {dashboard?.listed_count || 0}사 대상 시장 데이터 모니터링
      </div>

      {/* 요약 */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard title="평균 부도거리(DD)" value={dashboard?.avg_distance_to_default?.toFixed(2) || '0'}
          subtitle="높을수록 안전" icon={<BarChart3 size={22} />} color="blue" />
        <StatCard title="평균 CDS 스프레드" value={`${dashboard?.avg_cds_spread?.toFixed(0) || 0}bp`}
          icon={<Activity size={22} />} color="yellow" />
        <StatCard title="내재 PD" value={`${((dashboard?.avg_implied_pd || 0) * 100).toFixed(2)}%`}
          icon={<TrendingUp size={22} />} color="red" />
        <StatCard title="시장 경보" value={alerts.length || 0}
          subtitle={`DD<2: ${dashboard?.low_dd_count || 0}, CDS>200: ${dashboard?.high_cds_count || 0}`}
          icon={<AlertTriangle size={22} />} color="red" />
      </div>

      {/* 차트 */}
      <div className="grid grid-cols-2 gap-6">
        <Card title="DD / CDS 스프레드 추이">
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={dashboard?.trend || []} margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} />
              <YAxis yAxisId="left" tick={{ fontSize: 10 }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line yAxisId="left" type="monotone" dataKey="avg_dd" name="DD (좌)" stroke="#3b82f6" strokeWidth={2} dot={false} />
              <Line yAxisId="right" type="monotone" dataKey="avg_cds" name="CDS bp (우)" stroke="#ef4444" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card title="내재 PD / 주가변동률 추이">
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={dashboard?.trend || []} margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} />
              <YAxis yAxisId="left" tick={{ fontSize: 10 }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line yAxisId="left" type="monotone" dataKey="avg_implied_pd" name="내재PD (좌)" stroke="#7c3aed" strokeWidth={2} dot={false} />
              <Line yAxisId="right" type="monotone" dataKey="avg_stock_change" name="주가변동% (우)" stroke="#10b981" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* 고객 상세 */}
      {customerData && (
        <Card title={`시장 데이터: ${customerData.customer_name}`}
          headerAction={<button onClick={() => setCustomerData(null)} className="text-sm text-gray-500 hover:text-gray-700">닫기</button>}>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={customerData.data || []} margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} />
              <YAxis yAxisId="left" tick={{ fontSize: 10 }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line yAxisId="left" type="monotone" dataKey="distance_to_default" name="DD" stroke="#3b82f6" />
              <Line yAxisId="right" type="monotone" dataKey="cds_spread" name="CDS" stroke="#ef4444" />
              <Line yAxisId="left" type="monotone" dataKey="stock_price_change" name="주가%" stroke="#10b981" />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* 시장 경보 테이블 */}
      <Card title="시장 경보 목록">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 text-left">기업명</th>
                <th className="px-3 py-2 text-left">업종</th>
                <th className="px-3 py-2 text-center">주가변동%</th>
                <th className="px-3 py-2 text-center">CDS(bp)</th>
                <th className="px-3 py-2 text-center">DD</th>
                <th className="px-3 py-2 text-center">내재PD</th>
                <th className="px-3 py-2 text-left">경보사유</th>
                <th className="px-3 py-2 text-center">상세</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a: any) => (
                <tr key={a.customer_id} className="border-b hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium">{a.customer_name}</td>
                  <td className="px-3 py-2 text-gray-600">{a.industry_name}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={a.stock_price_change < -10 ? 'text-red-600 font-semibold' : ''}>
                      {a.stock_price_change?.toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className={a.cds_spread > 200 ? 'text-red-600 font-semibold' : ''}>{a.cds_spread?.toFixed(0)}</span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className={a.distance_to_default < 2 ? 'text-red-600 font-semibold' : ''}>{a.distance_to_default?.toFixed(2)}</span>
                  </td>
                  <td className="px-3 py-2 text-center">{((a.implied_pd || 0) * 100).toFixed(2)}%</td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      {(a.alert_reasons || []).map((r: string, i: number) => (
                        <span key={i} className="px-1.5 py-0.5 bg-red-100 text-red-700 rounded text-xs">{r}</span>
                      ))}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <button onClick={() => loadCustomer(a.customer_id)}
                      className="text-blue-600 hover:underline text-xs">조회</button>
                  </td>
                </tr>
              ))}
              {alerts.length === 0 && (
                <tr><td colSpan={8} className="px-3 py-8 text-center text-gray-400">시장 경보가 없습니다.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
