import React, { useEffect, useState } from 'react';
import { FileWarning, AlertCircle, CheckCircle, Users } from 'lucide-react';
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
  const [customerData, setCustomerData] = useState<any>(null);

  useEffect(() => { loadData(); }, [region]);

  const loadData = async () => {
    setLoading(true);
    try {
      const r = region || undefined;
      const [dashRes, tlRes] = await Promise.all([
        ewsAdvancedApi.getPublicRegistryDashboard(r),
        ewsAdvancedApi.getPublicRegistryTimeline(r),
      ]);
      setDashboard(dashRes.data);

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

      {/* 영향 기업 테이블 (by_type에서 상위 기업 → 실제로는 dashboard API에서 제공하지 않으므로 뱃지 클릭으로 대체) */}
      <Card title="공적정보 발생 기업 검색">
        <p className="text-sm text-gray-500 mb-3">기업 ID를 입력하여 공적정보 이력을 조회합니다.</p>
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
