import React, { useEffect, useState } from 'react';
import { Handshake, Radar } from 'lucide-react';
import { Card, StatCard, Badge } from '../../components';
import { formatNumber } from '../../utils/format';
import axios from 'axios';

/**
 * EWS 상거래연체 채널 (8채널 확장 Phase 2)
 * 기업 간 결제 지연은 은행 연체보다 먼저 온다. 핵심 화면 메시지:
 * "은행 DPD 0 인데 상거래연체가 있는 기업" = 이 채널이 먼저 본 구간.
 */

const EVENT_LABEL: Record<string, string> = {
  PAYMENT_DELAY: '대금 지연',
  NOTE_EXTENSION: '어음 연장',
  COMMERCIAL_DEFAULT: '상거래 부도',
};

export default function EWSB2BDelinquency() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get('/api/ews-advanced/b2b-delinquency/dashboard')
      .then(r => setData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading || !data) {
    return <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
    </div>;
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <StatCard title="미해소 상거래연체" value={`${data.summary.total_open}건`}
          subtitle="CB 집중 데이터 (법정 집중 - 동의 불요)" icon={<Handshake size={24} />} color="yellow" />
        <StatCard title="선행 포착" value={`${data.summary.leading_signals}건`}
          subtitle="은행 DPD 0 + 상거래연체 有 - 이 채널이 먼저 봤다"
          icon={<Radar size={24} />} color={data.summary.leading_signals > 0 ? 'red' : 'green'} />
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <p className="text-sm text-gray-500 font-medium">채널의 존재 이유</p>
          <p className="text-xs text-gray-600 mt-2 leading-relaxed">{data.summary.note}</p>
        </div>
      </div>

      <Card title="미해소 이벤트" subtitle="상거래 부도 → 즉시 CRITICAL 직행 · 대금 지연·어음 연장은 누적 감점" noPadding>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                <th className="py-2 px-4">고객</th>
                <th className="py-2 px-3">유형</th>
                <th className="py-2 px-3 text-right">발생일</th>
                <th className="py-2 px-3 text-right">경과</th>
                <th className="py-2 px-3 text-right">금액 (억)</th>
                <th className="py-2 px-3 text-right">거래처</th>
                <th className="py-2 px-3 text-right">은행 DPD</th>
                <th className="py-2 px-3 text-center">선행 신호</th>
                <th className="py-2 px-4 text-right">채널점수</th>
              </tr>
            </thead>
            <tbody>
              {data.open_events.map((r: any, i: number) => (
                <tr key={i} className={`border-b border-gray-50 ${r.leading_signal ? 'bg-amber-50/40' : ''}`}>
                  <td className="py-2 px-4">
                    <p className="font-medium text-gray-900">{r.customer_name}</p>
                    <p className="text-[11px] text-gray-400">{r.industry}</p>
                  </td>
                  <td className="py-2 px-3">
                    <Badge variant={r.event_type === 'COMMERCIAL_DEFAULT' ? 'danger' : 'warning'}>
                      {EVENT_LABEL[r.event_type] || r.event_type}
                    </Badge>
                  </td>
                  <td className="py-2 px-3 text-right tabular text-xs">{r.event_date}</td>
                  <td className="py-2 px-3 text-right tabular">{r.overdue_days}일</td>
                  <td className="py-2 px-3 text-right tabular">{formatNumber(r.overdue_amount_eok)}</td>
                  <td className="py-2 px-3 text-right tabular">{r.counterparties}곳</td>
                  <td className={`py-2 px-3 text-right tabular ${r.bank_dpd > 0 ? 'text-red-500 font-semibold' : 'text-gray-500'}`}>
                    {r.bank_dpd}일
                  </td>
                  <td className="py-2 px-3 text-center">
                    {r.leading_signal
                      ? <Badge variant="info">은행보다 먼저</Badge>
                      : <span className="text-xs text-gray-400">-</span>}
                  </td>
                  <td className={`py-2 px-4 text-right tabular font-bold ${(r.score ?? 100) < 55 ? 'text-red-500' : 'text-gray-900'}`}>
                    {r.score?.toFixed(0) ?? '-'}
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
