import React, { useEffect, useState } from 'react';
import { CreditCard, Clock, TrendingDown, AlertTriangle } from 'lucide-react';
import { Card, StatCard } from '../../components';
import { ewsAdvancedApi } from '../../utils/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { formatPercent } from '../../utils/format';

interface Props { region: string }

export default function EWSTransactionBehavior({ region }: Props) {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>(null);
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [customerData, setCustomerData] = useState<any>(null);
  const [selectedCustomer, setSelectedCustomer] = useState('');

  useEffect(() => { loadData(); }, [region]);

  const loadData = async () => {
    setLoading(true);
    try {
      const r = region || undefined;
      const [dashRes, anomRes] = await Promise.all([
        ewsAdvancedApi.getTransactionDashboard(r),
        ewsAdvancedApi.getTransactionAnomalies(r),
      ]);
      setDashboard(dashRes.data);
      setAnomalies(anomRes.data.anomalies || []);
    } catch (e) {
      console.error(e);
      setDashboard(null);
      setAnomalies([]);
    } finally { setLoading(false); }
  };

  const loadCustomer = async (cid: string) => {
    setSelectedCustomer(cid);
    try {
      const res = await ewsAdvancedApi.getTransactionCustomer(cid);
      setCustomerData(res.data);
    } catch (e) { console.error(e); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" /></div>;

  return (
    <div className="space-y-6">
      {/* 요약 통계 */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard title="모니터링 기업" value={dashboard?.total_customers || 0} icon={<CreditCard size={22} />} color="blue" />
        <StatCard title="평균 한도소진율" value={formatPercent((dashboard?.avg_utilization || 0) * 100, 1)}
          subtitle={`한도초과 ${dashboard?.high_utilization_count || 0}건`} icon={<TrendingDown size={22} />} color="yellow" />
        <StatCard title="평균 결제지연" value={`${dashboard?.avg_delay_days || 0}일`}
          subtitle={`지연발생 ${dashboard?.delayed_payment_count || 0}건`} icon={<Clock size={22} />} color="red" />
        <StatCard title="이상징후 기업" value={anomalies.length || 0}
          subtitle={`당좌대월 ${dashboard?.overdraft_count || 0}건`} icon={<AlertTriangle size={22} />} color="red" />
      </div>

      {/* 추이 차트 */}
      <div className="grid grid-cols-2 gap-6">
        <Card title="월별 한도소진율 / 예금유출률 추이">
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={dashboard?.trend || []} margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="avg_utilization" name="한도소진율" stroke="#3b82f6" dot={false} />
              <Line type="monotone" dataKey="avg_outflow" name="예금유출률" stroke="#ef4444" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card title="월별 평균 결제지연일수">
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={dashboard?.trend || []} margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Line type="monotone" dataKey="avg_delay" name="결제지연(일)" stroke="#f59e0b" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* 고객 상세 조회 */}
      {customerData && (
        <Card title={`고객 상세: ${customerData.customer_name}`}
          headerAction={<button onClick={() => setCustomerData(null)} className="text-sm text-gray-500 hover:text-gray-700">닫기</button>}
        >
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={customerData.data || []} margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="limit_utilization" name="한도소진율" stroke="#3b82f6" />
              <Line type="monotone" dataKey="deposit_outflow_rate" name="예금유출률" stroke="#ef4444" />
              <Line type="monotone" dataKey="payment_delay_days" name="결제지연(일)" stroke="#f59e0b" yAxisId="right" />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* 이상징후 테이블 */}
      <Card title="이상징후 탐지 목록">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 text-left">기업명</th>
                <th className="px-3 py-2 text-left">업종</th>
                <th className="px-3 py-2 text-center">한도소진율</th>
                <th className="px-3 py-2 text-center">결제지연</th>
                <th className="px-3 py-2 text-center">예금유출률</th>
                <th className="px-3 py-2 text-center">당좌대월</th>
                <th className="px-3 py-2 text-left">이상유형</th>
                <th className="px-3 py-2 text-center">상세</th>
              </tr>
            </thead>
            <tbody>
              {anomalies.map((a: any) => (
                <tr key={a.customer_id} className="border-b hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium">{a.customer_name}</td>
                  <td className="px-3 py-2 text-gray-600">{a.industry_name}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={a.limit_utilization > 0.8 ? 'text-red-600 font-semibold' : ''}>
                      {formatPercent((a.limit_utilization || 0) * 100, 1)}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className={a.payment_delay_days > 7 ? 'text-red-600 font-semibold' : ''}>
                      {a.payment_delay_days}일
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center">{formatPercent((a.deposit_outflow_rate || 0) * 100, 1)}</td>
                  <td className="px-3 py-2 text-center">{a.overdraft_count}회</td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      {(a.anomaly_types || []).map((t: string, i: number) => (
                        <span key={i} className="px-1.5 py-0.5 bg-red-100 text-red-700 rounded text-xs">{t}</span>
                      ))}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <button onClick={() => loadCustomer(a.customer_id)}
                      className="text-blue-600 hover:underline text-xs">조회</button>
                  </td>
                </tr>
              ))}
              {anomalies.length === 0 && (
                <tr><td colSpan={8} className="px-3 py-8 text-center text-gray-400">이상징후 탐지 기업이 없습니다.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
