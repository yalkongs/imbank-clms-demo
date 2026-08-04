import React, { useEffect, useState } from 'react';
import { TrendingUp, BarChart3, AlertTriangle, Activity, Search, MousePointerClick } from 'lucide-react';
import { Card, StatCard } from '../../components';
import { ewsAdvancedApi } from '../../utils/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface Props { region: string }

/**
 * 시장신호 탭 — 마스터·디테일 구조 (공급망 탭과 동일한 패턴).
 * 경보 목록이 최하단에 있고 '조회' 시 상세가 뷰포트 밖 위쪽에 삽입되던
 * 구조를, 좌측 경보 목록 → 우측 즉시 상세 표시로 재배치.
 */
export default function EWSMarketSignals({ region }: Props) {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [selectedAlert, setSelectedAlert] = useState<any>(null);
  const [customerData, setCustomerData] = useState<any>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => { loadData(); }, [region]);

  const loadData = async () => {
    setLoading(true);
    setSelectedAlert(null);
    setCustomerData(null);
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

  const loadCustomer = async (a: any) => {
    setSelectedAlert(a);
    try {
      const res = await ewsAdvancedApi.getMarketCustomer(a.customer_id);
      setCustomerData(res.data);
    } catch (e) { console.error(e); }
  };

  const closeDetail = () => { setSelectedAlert(null); setCustomerData(null); };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" /></div>;

  const filtered = alerts.filter((a: any) => !searchTerm ||
    a.customer_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (a.industry_name || '').toLowerCase().includes(searchTerm.toLowerCase()));

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

      {/* 마스터(좌: 경보 목록) · 디테일(우: 기업 시장 데이터) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        <Card title={`시장 경보 기업 (${filtered.length})`} className="lg:col-span-1">
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
              const selected = selectedAlert?.customer_id === a.customer_id;
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
                      a.distance_to_default < 2 ? 'text-red-600' : 'text-gray-500'
                    }`}>
                      DD {a.distance_to_default?.toFixed(2)}
                    </span>
                  </div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    {a.industry_name} · CDS {a.cds_spread?.toFixed(0)}bp · 주가 {a.stock_price_change?.toFixed(1)}%
                  </div>
                  {(a.alert_reasons || []).length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {(a.alert_reasons || []).map((r: string, i: number) => (
                        <span key={i} className="px-1.5 py-0.5 bg-red-100 text-red-700 rounded text-[11px]">{r}</span>
                      ))}
                    </div>
                  )}
                </button>
              );
            })}
            {filtered.length === 0 && (
              <p className="text-sm text-gray-400 text-center py-8">시장 경보가 없습니다</p>
            )}
          </div>
        </Card>

        {/* 상세 (선택 전에는 전체 추이) */}
        <div className="lg:col-span-2 space-y-6">
          {customerData ? (
            <Card title={`시장 데이터: ${customerData.customer_name}`}
              headerAction={<button onClick={closeDetail} className="text-sm text-gray-500 hover:text-gray-700">닫기</button>}>
              {selectedAlert && (
                <div className="grid grid-cols-4 gap-3 mb-4">
                  {[
                    { l: '주가변동', v: `${selectedAlert.stock_price_change?.toFixed(1)}%`, bad: selectedAlert.stock_price_change < -10 },
                    { l: 'CDS 스프레드', v: `${selectedAlert.cds_spread?.toFixed(0)}bp`, bad: selectedAlert.cds_spread > 200 },
                    { l: '부도거리(DD)', v: selectedAlert.distance_to_default?.toFixed(2), bad: selectedAlert.distance_to_default < 2 },
                    { l: '내재 PD', v: `${((selectedAlert.implied_pd || 0) * 100).toFixed(2)}%`, bad: false },
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
                  <Line yAxisId="left" type="monotone" dataKey="distance_to_default" name="DD" stroke="#00BFA5" />
                  <Line yAxisId="right" type="monotone" dataKey="cds_spread" name="CDS" stroke="#ef4444" />
                  <Line yAxisId="left" type="monotone" dataKey="stock_price_change" name="주가%" stroke="#10b981" />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          ) : (
            <>
              <Card title="DD / CDS 스프레드 추이">
                <ResponsiveContainer width="100%" height={230}>
                  <LineChart data={dashboard?.trend || []} margin={{ left: -10, right: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                    <YAxis yAxisId="left" tick={{ fontSize: 10 }} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Line yAxisId="left" type="monotone" dataKey="avg_dd" name="DD (좌)" stroke="#00BFA5" strokeWidth={2} dot={false} />
                    <Line yAxisId="right" type="monotone" dataKey="avg_cds" name="CDS bp (우)" stroke="#ef4444" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </Card>
              <Card title="내재 PD / 주가변동률 추이">
                <ResponsiveContainer width="100%" height={230}>
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
                <div className="mt-3 flex items-center justify-center gap-2 text-sm text-gray-400 border-t border-gray-100 pt-3">
                  <MousePointerClick size={15} />
                  좌측 경보 목록에서 기업을 선택하면 기업별 시장 데이터가 여기에 표시됩니다
                </div>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
