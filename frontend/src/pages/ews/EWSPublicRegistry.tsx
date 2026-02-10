import React, { useEffect, useState } from 'react';
import { FileWarning, AlertCircle, CheckCircle, Users, Search } from 'lucide-react';
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

export default function EWSPublicRegistry({ region }: Props) {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [customers, setCustomers] = useState<any[]>([]);
  const [customerData, setCustomerData] = useState<any>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => { loadData(); }, [region]);

  const loadData = async () => {
    setLoading(true);
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

  const loadCustomer = async (cid: string) => {
    try {
      const res = await ewsAdvancedApi.getPublicRegistryCustomer(cid);
      setCustomerData(res.data);
    } catch (e) { console.error(e); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" /></div>;

  const byType = dashboard?.by_type || [];

  const filtered = searchTerm
    ? customers.filter((c: any) =>
        c.customer_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.customer_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (c.industry || '').toLowerCase().includes(searchTerm.toLowerCase())
      )
    : customers;

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

      {/* 유형별 뱃지 */}
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

      {/* 월별 타임라인 차트 */}
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
            <Bar dataKey="AUDIT_OPINION" name="감사의견" stackId="a" fill="#3b82f6" />
            <Bar dataKey="MGMT_CHANGE" name="경영진변동" stackId="a" fill="#6b7280" />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      {/* 고객별 상세 */}
      {customerData && (
        <Card title={`이벤트 이력: ${customerData.customer_name}`}
          headerAction={<button onClick={() => setCustomerData(null)} className="text-sm text-gray-500 hover:text-gray-700">닫기</button>}>
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
      )}

      {/* 기업 목록 선택 */}
      <Card title={`공적정보 발생 기업 목록 (${filtered.length}개)`}>
        <div className="mb-3">
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="기업명, ID, 업종으로 검색..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full border rounded px-3 py-2 pl-9 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
        <div className="overflow-x-auto max-h-80 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-white">
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 text-left">기업명</th>
                <th className="px-3 py-2 text-left">업종</th>
                <th className="px-3 py-2 text-center">이벤트 수</th>
                <th className="px-3 py-2 text-center">미해결</th>
                <th className="px-3 py-2 text-center">심각</th>
                <th className="px-3 py-2 text-left">유형</th>
                <th className="px-3 py-2 text-center">조회</th>
              </tr>
            </thead>
            <tbody>
              {filtered.slice(0, 100).map((c: any) => (
                <tr
                  key={c.customer_id}
                  className={`border-b hover:bg-blue-50 cursor-pointer ${
                    customerData?.customer_id === c.customer_id ? 'bg-blue-50' : ''
                  }`}
                  onClick={() => loadCustomer(c.customer_id)}
                >
                  <td className="px-3 py-2">
                    <div className="font-medium">{c.customer_name}</div>
                    <div className="text-xs text-gray-400">{c.customer_id}</div>
                  </td>
                  <td className="px-3 py-2 text-gray-600">{c.industry}</td>
                  <td className="px-3 py-2 text-center">{c.event_count}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={c.unresolved > 0 ? 'text-red-600 font-medium' : ''}>
                      {c.unresolved}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className={c.severe_count > 0 ? 'text-red-600 font-medium' : ''}>
                      {c.severe_count}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      {(c.event_types || []).map((t: string) => (
                        <span key={t} className="px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                          {EVENT_LABELS[t] || t}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <button
                      className="px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700"
                      onClick={(e) => { e.stopPropagation(); loadCustomer(c.customer_id); }}
                    >
                      상세
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
