import React, { useEffect, useState } from 'react';
import { Network, AlertTriangle, Link2, TrendingDown, Search, MousePointerClick } from 'lucide-react';
import { Card, StatCard } from '../../components';
import { ewsAdvancedApi } from '../../utils/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { formatPercent } from '../../utils/format';

interface Props { region: string }

/**
 * 공급망 탭 — 마스터·디테일 구조.
 *
 * 기존에는 기업 목록이 화면 최하단에 있고 '상세'를 누르면 상세 카드가 목록
 * *위쪽*(뷰포트 밖)에 삽입돼, 클릭해도 아무 반응이 없는 것처럼 보였다.
 * 좌측 목록에서 기업을 고르면 우측에 즉시 시계열·거래처 상세가 나타나도록
 * 재배치해 상호작용의 인과를 화면 안에서 완결시킨다.
 */
export default function EWSSupplyChain({ region }: Props) {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>(null);
  const [customers, setCustomers] = useState<any[]>([]);
  const [customerData, setCustomerData] = useState<any>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [riskOnly, setRiskOnly] = useState(false);

  useEffect(() => { loadData(); }, [region]);

  const loadData = async () => {
    setLoading(true);
    try {
      const r = region || undefined;
      const [dashRes, custRes] = await Promise.all([
        ewsAdvancedApi.getSupplyChainDashboard(r),
        ewsAdvancedApi.getSupplyChainCustomers(r),
      ]);
      setDashboard(dashRes.data);
      setCustomers(custRes.data || []);
    } catch (e) {
      console.error(e);
      setDashboard(null);
      setCustomers([]);
    } finally { setLoading(false); }
  };

  const loadCustomer = async (cid: string) => {
    try {
      const res = await ewsAdvancedApi.getSupplyChainTemporal(cid);
      setCustomerData(res.data);
    } catch (e) { console.error(e); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" /></div>;

  const filtered = customers
    .filter((c: any) => !riskOnly || c.avg_chain_pd > 0.15)
    .filter((c: any) => !searchTerm ||
      c.customer_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.customer_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (c.industry || '').toLowerCase().includes(searchTerm.toLowerCase()));

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

      {/* 마스터(좌: 기업 목록) · 디테일(우: 시계열/거래처 상세) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* 기업 목록 */}
        <Card title={`분석 대상 기업 (${filtered.length})`} className="lg:col-span-1"
          headerAction={
            <button
              onClick={() => setRiskOnly(v => !v)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
                riskOnly
                  ? 'bg-red-50 border-red-300 text-red-700'
                  : 'bg-white border-gray-300 text-gray-500 hover:border-red-300 hover:text-red-600'
              }`}
            >
              고위험만
            </button>
          }>
          <div className="mb-3 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="기업명, ID, 업종 검색..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full border rounded px-3 py-2 pl-9 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <p className="text-[11px] text-gray-400 mb-2">연쇄PD 높은 순 · 기업을 선택하면 우측에 상세가 표시됩니다</p>
          <div className="max-h-[560px] overflow-y-auto divide-y divide-gray-100 -mx-1">
            {filtered.slice(0, 100).map((c: any) => {
              const selected = customerData?.customer_id === c.customer_id;
              return (
                <button
                  key={c.customer_id}
                  onClick={() => loadCustomer(c.customer_id)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors ${
                    selected ? 'bg-blue-50 ring-1 ring-blue-200' : 'hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className={`text-sm font-medium truncate ${selected ? 'text-blue-800' : 'text-gray-900'}`}>
                      {c.customer_name}
                    </span>
                    <span className={`flex-none text-xs font-semibold tabular ${
                      c.avg_chain_pd > 0.15 ? 'text-red-600' : 'text-gray-500'
                    }`}>
                      {formatPercent(c.avg_chain_pd * 100, 1)}
                    </span>
                  </div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    {c.industry} · 거래처 {c.partner_count} · {c.customer_id}
                  </div>
                </button>
              );
            })}
            {filtered.length === 0 && (
              <p className="text-sm text-gray-400 text-center py-8">조건에 맞는 기업이 없습니다</p>
            )}
          </div>
          {filtered.length > 100 && (
            <p className="text-[11px] text-gray-400 mt-2 text-center">
              상위 100개만 표시 — 검색으로 범위를 좁혀보세요
            </p>
          )}
        </Card>

        {/* 상세 (선택 전에는 전체 추이) */}
        <div className="lg:col-span-2 space-y-6">
          {customerData ? (
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
          ) : (
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
              <div className="mt-3 flex items-center justify-center gap-2 text-sm text-gray-400 border-t border-gray-100 pt-3">
                <MousePointerClick size={15} />
                좌측 목록에서 기업을 선택하면 기업별 시계열과 거래처 상세가 여기에 표시됩니다
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
