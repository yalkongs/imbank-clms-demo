import React, { useEffect, useState } from 'react';
import { Network, AlertTriangle, Link2, TrendingDown } from 'lucide-react';
import { Card, StatCard } from '../../components';
import { ewsAdvancedApi } from '../../utils/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { formatPercent } from '../../utils/format';

interface Props { region: string }

export default function EWSSupplyChain({ region }: Props) {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>(null);
  const [customerData, setCustomerData] = useState<any>(null);

  useEffect(() => { loadData(); }, [region]);

  const loadData = async () => {
    setLoading(true);
    try {
      const r = region || undefined;
      const res = await ewsAdvancedApi.getSupplyChainDashboard(r);
      setDashboard(res.data);
    } catch (e) {
      console.error(e);
      setDashboard(null);
    } finally { setLoading(false); }
  };

  const loadCustomer = async (cid: string) => {
    try {
      const res = await ewsAdvancedApi.getSupplyChainTemporal(cid);
      setCustomerData(res.data);
    } catch (e) { console.error(e); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" /></div>;

  // 고객 시계열 차트 데이터: 월별 집계
  const customerChartData = customerData ? (() => {
    const byMonth: Record<string, { month: string; avgPd: number; count: number; delayed: number }> = {};
    (customerData.data || []).forEach((d: any) => {
      if (!byMonth[d.month]) byMonth[d.month] = { month: d.month, avgPd: 0, count: 0, delayed: 0 };
      byMonth[d.month].avgPd += d.chain_pd || 0;
      byMonth[d.month].count += 1;
      if (d.payment_status !== 'NORMAL') byMonth[d.month].delayed += 1;
    });
    return Object.values(byMonth).map(m => ({
      month: m.month, avg_chain_pd: m.count > 0 ? +(m.avgPd / m.count).toFixed(4) : 0, problem_count: m.delayed,
    })).sort((a, b) => a.month.localeCompare(b.month));
  })() : [];

  return (
    <div className="space-y-6">
      {/* 요약 */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard title="모니터링 기업" value={dashboard?.monitored_customers || 0}
          icon={<Network size={22} />} color="blue" />
        <StatCard title="거래처 수" value={dashboard?.partner_count || 0}
          icon={<Link2 size={22} />} color="green" />
        <StatCard title="평균 연쇄부도확률" value={formatPercent((dashboard?.avg_chain_default_prob || 0) * 100, 2)}
          icon={<TrendingDown size={22} />} color="yellow" />
        <StatCard title="고위험 관계" value={dashboard?.high_risk_relations || 0}
          subtitle={`연체 ${dashboard?.delinquent_count || 0} / 지연 ${dashboard?.delayed_count || 0}`}
          icon={<AlertTriangle size={22} />} color="red" />
      </div>

      {/* 추이 차트 */}
      <Card title="월별 공급망 리스크 추이">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={dashboard?.trend || []} margin={{ left: -10, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" tick={{ fontSize: 10 }} />
            <YAxis yAxisId="left" tick={{ fontSize: 10 }} />
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line yAxisId="left" type="monotone" dataKey="avg_chain_pd" name="평균 연쇄부도확률" stroke="#ef4444" strokeWidth={2} dot={false} />
            <Line yAxisId="right" type="monotone" dataKey="problem_count" name="문제거래 건수" stroke="#f59e0b" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      {/* 고객 상세 */}
      {customerData && (
        <Card title={`공급망 시계열: ${customerData.customer_name}`}
          headerAction={<button onClick={() => setCustomerData(null)} className="text-sm text-gray-500 hover:text-gray-700">닫기</button>}>
          <div className="space-y-4">
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={customerChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="avg_chain_pd" name="연쇄부도확률" stroke="#ef4444" />
                <Line type="monotone" dataKey="problem_count" name="문제거래" stroke="#f59e0b" />
              </LineChart>
            </ResponsiveContainer>

            {/* 최근 월 거래처별 상세 */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50">
                    <th className="px-3 py-2 text-left">거래처</th>
                    <th className="px-3 py-2 text-center">월</th>
                    <th className="px-3 py-2 text-right">거래금액(억)</th>
                    <th className="px-3 py-2 text-center">변동률</th>
                    <th className="px-3 py-2 text-center">결제상태</th>
                    <th className="px-3 py-2 text-center">등급</th>
                    <th className="px-3 py-2 text-center">연쇄PD</th>
                    <th className="px-3 py-2 text-center">의존도</th>
                  </tr>
                </thead>
                <tbody>
                  {(customerData.data || []).slice(0, 30).map((d: any, i: number) => (
                    <tr key={i} className="border-b hover:bg-gray-50">
                      <td className="px-3 py-2">{d.partner_name}</td>
                      <td className="px-3 py-2 text-center text-gray-500">{d.month}</td>
                      <td className="px-3 py-2 text-right">{d.transaction_amount?.toFixed(1)}</td>
                      <td className="px-3 py-2 text-center">
                        <span className={d.change_rate < -5 ? 'text-red-600' : ''}>{d.change_rate?.toFixed(1)}%</span>
                      </td>
                      <td className="px-3 py-2 text-center">
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          d.payment_status === 'DELINQUENT' ? 'bg-red-100 text-red-700' :
                          d.payment_status === 'DELAYED' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-green-100 text-green-700'
                        }`}>{d.payment_status}</span>
                      </td>
                      <td className="px-3 py-2 text-center">{d.partner_grade}</td>
                      <td className="px-3 py-2 text-center">{formatPercent((d.chain_pd || 0) * 100, 2)}</td>
                      <td className="px-3 py-2 text-center">{formatPercent((d.dependency || 0) * 100, 1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </Card>
      )}

      {/* 기업 검색 */}
      <Card title="공급망 분석 기업 검색">
        <p className="text-sm text-gray-500 mb-3">기업 ID를 입력하여 공급망 시계열 데이터를 조회합니다.</p>
        <div className="flex gap-2">
          <input type="text" placeholder="고객 ID (예: CUST_001)"
            className="border rounded px-3 py-2 text-sm flex-1"
            onKeyDown={(e) => { if (e.key === 'Enter') loadCustomer((e.target as HTMLInputElement).value); }}
          />
          <button onClick={(e) => {
            const input = (e.currentTarget.previousElementSibling as HTMLInputElement);
            if (input.value) loadCustomer(input.value);
          }} className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">조회</button>
        </div>
      </Card>
    </div>
  );
}
