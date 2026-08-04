import React, { useEffect, useState } from 'react';
import { CreditCard, Clock, TrendingDown, AlertTriangle, Search, MousePointerClick } from 'lucide-react';
import { Card, StatCard } from '../../components';
import { ewsAdvancedApi } from '../../utils/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { formatPercent } from '../../utils/format';

interface Props { region: string }

/**
 * 거래행태 탭 — 마스터·디테일 구조 (공급망 탭과 동일한 패턴).
 * 이상징후 목록이 최하단에 있고 '조회' 시 상세가 뷰포트 밖 위쪽에 삽입되던
 * 구조를, 좌측 목록 → 우측 즉시 상세 표시로 재배치.
 */
export default function EWSTransactionBehavior({ region }: Props) {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>(null);
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [selectedAnomaly, setSelectedAnomaly] = useState<any>(null);
  const [customerData, setCustomerData] = useState<any>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => { loadData(); }, [region]);

  const loadData = async () => {
    setLoading(true);
    setSelectedAnomaly(null);
    setCustomerData(null);
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

  const loadCustomer = async (a: any) => {
    setSelectedAnomaly(a);
    try {
      const res = await ewsAdvancedApi.getTransactionCustomer(a.customer_id);
      setCustomerData(res.data);
    } catch (e) { console.error(e); }
  };

  const closeDetail = () => { setSelectedAnomaly(null); setCustomerData(null); };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" /></div>;

  const filtered = anomalies.filter((a: any) => !searchTerm ||
    a.customer_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (a.industry_name || '').toLowerCase().includes(searchTerm.toLowerCase()));

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

      {/* 마스터(좌: 이상징후 목록) · 디테일(우: 기업 거래행태) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        <Card title={`이상징후 탐지 기업 (${filtered.length})`} className="lg:col-span-1">
          <div className="mb-3 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="기업명, 업종 검색..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full border rounded px-3 py-2 pl-9 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <p className="text-[11px] text-gray-400 mb-2">기업을 선택하면 우측에 상세가 표시됩니다</p>
          <div className="max-h-[560px] overflow-y-auto divide-y divide-gray-100 -mx-1">
            {filtered.map((a: any) => {
              const selected = selectedAnomaly?.customer_id === a.customer_id;
              return (
                <button
                  key={a.customer_id}
                  onClick={() => loadCustomer(a)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors ${
                    selected ? 'bg-blue-50 ring-1 ring-blue-200' : 'hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className={`text-sm font-medium truncate ${selected ? 'text-blue-800' : 'text-gray-900'}`}>
                      {a.customer_name}
                    </span>
                    <span className={`flex-none text-xs font-semibold tabular ${
                      a.limit_utilization > 0.8 ? 'text-red-600' : 'text-gray-500'
                    }`}>
                      소진 {formatPercent((a.limit_utilization || 0) * 100, 0)}
                    </span>
                  </div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    {a.industry_name} · 지연 {a.payment_delay_days}일 · 당좌 {a.overdraft_count}회
                  </div>
                  {(a.anomaly_types || []).length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {(a.anomaly_types || []).map((t: string, i: number) => (
                        <span key={i} className="px-1.5 py-0.5 bg-red-100 text-red-700 rounded text-[11px]">{t}</span>
                      ))}
                    </div>
                  )}
                </button>
              );
            })}
            {filtered.length === 0 && (
              <p className="text-sm text-gray-400 text-center py-8">이상징후 탐지 기업이 없습니다</p>
            )}
          </div>
        </Card>

        {/* 상세 (선택 전에는 전체 추이) */}
        <div className="lg:col-span-2 space-y-6">
          {customerData ? (
            <Card title={`고객 상세: ${customerData.customer_name}`}
              headerAction={<button onClick={closeDetail} className="text-sm text-gray-500 hover:text-gray-700">닫기</button>}>
              {selectedAnomaly && (
                <div className="grid grid-cols-4 gap-3 mb-4">
                  {[
                    { l: '한도소진율', v: formatPercent((selectedAnomaly.limit_utilization || 0) * 100, 1), bad: selectedAnomaly.limit_utilization > 0.8 },
                    { l: '결제지연', v: `${selectedAnomaly.payment_delay_days}일`, bad: selectedAnomaly.payment_delay_days > 7 },
                    { l: '예금유출률', v: formatPercent((selectedAnomaly.deposit_outflow_rate || 0) * 100, 1), bad: false },
                    { l: '당좌대월', v: `${selectedAnomaly.overdraft_count}회`, bad: selectedAnomaly.overdraft_count > 0 },
                  ].map(m => (
                    <div key={m.l} className="rounded-lg bg-gray-50 border border-gray-100 px-3 py-2">
                      <p className="text-[11px] text-gray-400">{m.l}</p>
                      <p className={`text-sm font-bold tabular ${m.bad ? 'text-red-600' : 'text-gray-900'}`}>{m.v}</p>
                    </div>
                  ))}
                </div>
              )}
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={customerData.data || []} margin={{ left: -10, right: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                  <YAxis yAxisId="left" tick={{ fontSize: 10 }} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line yAxisId="left" type="monotone" dataKey="limit_utilization" name="한도소진율" stroke="#00BFA5" />
                  <Line yAxisId="left" type="monotone" dataKey="deposit_outflow_rate" name="예금유출률" stroke="#ef4444" />
                  <Line yAxisId="right" type="monotone" dataKey="payment_delay_days" name="결제지연(일)" stroke="#f59e0b" />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          ) : (
            <>
              <Card title="월별 한도소진율 / 예금유출률 추이">
                <ResponsiveContainer width="100%" height={230}>
                  <LineChart data={dashboard?.trend || []} margin={{ left: -10, right: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Line type="monotone" dataKey="avg_utilization" name="한도소진율" stroke="#00BFA5" dot={false} />
                    <Line type="monotone" dataKey="avg_outflow" name="예금유출률" stroke="#ef4444" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </Card>
              <Card title="월별 평균 결제지연일수">
                <ResponsiveContainer width="100%" height={230}>
                  <LineChart data={dashboard?.trend || []} margin={{ left: -10, right: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="avg_delay" name="결제지연(일)" stroke="#f59e0b" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
                <div className="mt-3 flex items-center justify-center gap-2 text-sm text-gray-400 border-t border-gray-100 pt-3">
                  <MousePointerClick size={15} />
                  좌측 목록에서 기업을 선택하면 기업별 거래행태 추이가 여기에 표시됩니다
                </div>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
