import React, { useEffect, useState } from 'react';
import { FileWarning, AlertCircle, CheckCircle, Users, Search, MousePointerClick } from 'lucide-react';
import { Card, StatCard } from '../../components';
import { ewsAdvancedApi } from '../../utils/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface Props { region: string }

const EVENT_LABELS: Record<string, string> = {
  TAX_DELINQUENT: '세금체납',
  SOCIAL_INSURANCE: '사회보험미납',
  SEIZURE: '가압류',
  AUDIT_OPINION: '감사의견',
  MGMT_CHANGE: '경영진변동',
};

/**
 * 공적정보 탭 — 마스터·디테일 구조 (공급망 탭과 동일한 패턴).
 * 기업 목록이 최하단에 있고 '상세' 클릭 시 이력 카드가 뷰포트 밖 위쪽에
 * 삽입되던 구조를, 좌측 목록 → 우측 즉시 상세 표시로 재배치.
 */
export default function EWSPublicRegistry({ region }: Props) {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [customers, setCustomers] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [customerData, setCustomerData] = useState<any>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => { loadData(); }, [region]);

  const loadData = async () => {
    setLoading(true);
    setSelected(null);
    setCustomerData(null);
    try {
      const r = region || undefined;
      const [dashRes, tlRes, custRes] = await Promise.all([
        ewsAdvancedApi.getPublicRegistryDashboard(r),
        ewsAdvancedApi.getPublicRegistryTimeline(r),
        ewsAdvancedApi.getPublicRegistryCustomers(r),
      ]);
      setDashboard(dashRes.data);
      setCustomers(custRes.data || []);

      // 타임라인을 월별로 피벗
      const raw = tlRes.data.timeline || [];
      const months = [...new Set(raw.map((r: any) => r.month))].sort();
      const pivoted = months.map(m => {
        const entry: any = { month: m };
        raw.filter((r: any) => r.month === m).forEach((r: any) => {
          entry[r.event_type] = r.count;
        });
        return entry;
      });
      setTimeline(pivoted);
    } catch (e) {
      console.error(e);
      setDashboard(null);
      setTimeline([]);
      setCustomers([]);
    } finally { setLoading(false); }
  };

  const loadCustomer = async (c: any) => {
    setSelected(c);
    try {
      const res = await ewsAdvancedApi.getPublicRegistryCustomer(c.customer_id);
      setCustomerData(res.data);
    } catch (e) { console.error(e); }
  };

  const closeDetail = () => { setSelected(null); setCustomerData(null); };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" /></div>;

  const byType = dashboard?.by_type || [];

  const filtered = customers.filter((c: any) => !searchTerm ||
    c.customer_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.customer_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (c.industry || '').toLowerCase().includes(searchTerm.toLowerCase()));

  return (
    <div className="space-y-6">
      {/* 요약 */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard title="총 이벤트" value={dashboard?.total_events || 0} icon={<FileWarning size={22} />} color="yellow" />
        <StatCard title="미해결 이벤트" value={dashboard?.unresolved_events || 0}
          subtitle="즉시 조치 필요" icon={<AlertCircle size={22} />} color="red" />
        <StatCard title="영향 기업 수" value={dashboard?.affected_customers || 0}
          icon={<Users size={22} />} color="blue" />
        <StatCard title="해결률" value={dashboard?.total_events
          ? `${Math.round(((dashboard.total_events - dashboard.unresolved_events) / dashboard.total_events) * 100)}%`
          : '0%'} icon={<CheckCircle size={22} />} color="green" />
      </div>

      {/* 마스터(좌: 기업 목록) · 디테일(우: 이벤트 이력) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        <Card title={`공적정보 발생 기업 (${filtered.length})`} className="lg:col-span-1">
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
          <p className="text-[11px] text-gray-400 mb-2">기업을 선택하면 우측에 이벤트 이력이 표시됩니다</p>
          <div className="max-h-[560px] overflow-y-auto divide-y divide-gray-100 -mx-1">
            {filtered.slice(0, 100).map((c: any) => {
              const isSel = selected?.customer_id === c.customer_id;
              return (
                <button
                  key={c.customer_id}
                  onClick={() => loadCustomer(c)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors ${
                    isSel ? 'bg-blue-50 ring-1 ring-blue-200' : 'hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className={`text-sm font-medium truncate ${isSel ? 'text-blue-800' : 'text-gray-900'}`}>
                      {c.customer_name}
                    </span>
                    {c.unresolved > 0 && (
                      <span className="flex-none text-xs font-semibold text-red-600">미해결 {c.unresolved}</span>
                    )}
                  </div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    {c.industry} · 이벤트 {c.event_count}
                    {c.severe_count > 0 && <span className="text-red-500"> · 심각 {c.severe_count}</span>}
                  </div>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {(c.event_types || []).map((t: string) => (
                      <span key={t} className="px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded text-[11px]">
                        {EVENT_LABELS[t] || t}
                      </span>
                    ))}
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

        {/* 상세 (선택 전에는 전체 현황) */}
        <div className="lg:col-span-2 space-y-6">
          {customerData ? (
            <Card title={`이벤트 이력: ${customerData.customer_name}`}
              headerAction={<button onClick={closeDetail} className="text-sm text-gray-500 hover:text-gray-700">닫기</button>}>
              {selected && (
                <div className="flex items-center gap-4 mb-4 text-sm">
                  <span className="text-gray-500">이벤트 <b className="text-gray-900">{selected.event_count}</b></span>
                  <span className="text-gray-500">미해결 <b className={selected.unresolved > 0 ? 'text-red-600' : 'text-gray-900'}>{selected.unresolved}</b></span>
                  <span className="text-gray-500">심각 <b className={selected.severe_count > 0 ? 'text-red-600' : 'text-gray-900'}>{selected.severe_count}</b></span>
                </div>
              )}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-gray-50">
                      <th className="px-3 py-2 text-left">일자</th>
                      <th className="px-3 py-2 text-left">유형</th>
                      <th className="px-3 py-2 text-center">심각도</th>
                      <th className="px-3 py-2 text-left">설명</th>
                      <th className="px-3 py-2 text-right">금액(억)</th>
                      <th className="px-3 py-2 text-center">해결</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(customerData.events || []).map((ev: any, i: number) => (
                      <tr key={i} className="border-b hover:bg-gray-50">
                        <td className="px-3 py-2">{ev.event_date}</td>
                        <td className="px-3 py-2">{EVENT_LABELS[ev.event_type] || ev.event_type}</td>
                        <td className="px-3 py-2 text-center">
                          <span className={`px-2 py-0.5 rounded text-xs ${
                            ev.severity === 'CRITICAL' ? 'bg-red-600 text-white' :
                            ev.severity === 'HIGH' ? 'bg-red-100 text-red-700' :
                            ev.severity === 'MEDIUM' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>{ev.severity}</span>
                        </td>
                        <td className="px-3 py-2 text-gray-600">{ev.description}</td>
                        <td className="px-3 py-2 text-right">{ev.amount ?? '-'}</td>
                        <td className="px-3 py-2 text-center">
                          {ev.resolved ? <CheckCircle className="inline text-green-500" size={16} /> :
                            <AlertCircle className="inline text-red-500" size={16} />}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          ) : (
            <>
              <Card title="이벤트 유형별 현황">
                <div className="flex flex-wrap gap-3">
                  {byType.map((t: any) => (
                    <div key={t.event_type} className="flex items-center gap-2 px-4 py-3 bg-gray-50 rounded-lg border">
                      <span className="text-sm font-medium text-gray-700">{EVENT_LABELS[t.event_type] || t.event_type}</span>
                      <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs font-semibold">{t.count}</span>
                      {t.severe_count > 0 && (
                        <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs font-semibold">심각 {t.severe_count}</span>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
              <Card title="월별 공적정보 이벤트 추이">
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={timeline} margin={{ left: -10, right: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="TAX_DELINQUENT" name="세금체납" stackId="a" fill="#ef4444" />
                    <Bar dataKey="SOCIAL_INSURANCE" name="사회보험" stackId="a" fill="#f59e0b" />
                    <Bar dataKey="SEIZURE" name="가압류" stackId="a" fill="#7c3aed" />
                    <Bar dataKey="AUDIT_OPINION" name="감사의견" stackId="a" fill="#00BFA5" />
                    <Bar dataKey="MGMT_CHANGE" name="경영진변동" stackId="a" fill="#6b7280" />
                  </BarChart>
                </ResponsiveContainer>
                <div className="mt-3 flex items-center justify-center gap-2 text-sm text-gray-400 border-t border-gray-100 pt-3">
                  <MousePointerClick size={15} />
                  좌측 목록에서 기업을 선택하면 이벤트 이력이 여기에 표시됩니다
                </div>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
