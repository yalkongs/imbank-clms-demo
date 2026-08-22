import React, { useEffect, useState } from 'react';
import { CreditCard, Users, AlertTriangle, ShieldCheck } from 'lucide-react';
import { Card, StatCard, Badge } from '../../components';
import { formatNumber, formatPercent } from '../../utils/format';
import axios from 'axios';

/**
 * EWS 확장 채널 - 카드매출·고용 (8채널 확장 Phase 2)
 * 재무제표보다 6~12개월 빠른 실측 행동 데이터. 동의(신용정보법 §32) 유효
 * 기업만 점수에 반영되고, 만료·철회는 자동 결측 전환된다.
 */

export default function EWSExtendedChannels() {
  const [data, setData] = useState<any>(null);
  const [consent, setConsent] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      axios.get('/api/ews-advanced/card-employment/dashboard'),
      axios.get('/api/ews-advanced/consent/summary'),
    ])
      .then(([d, c]) => { setData(d.data); setConsent(c.data); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading || !data) {
    return <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
    </div>;
  }

  const s = data.summary;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-4">
        <StatCard title="카드매출 동의 기업" value={formatNumber(s.card_consented)}
          subtitle="SOHO·유통 적격 - 신용정보법 §32 동의" icon={<CreditCard size={24} />} color="blue" />
        <StatCard title="카드매출 경보" value={`${s.card_alerts}건`}
          subtitle="채널 점수 55 미만 (WATCH 경계)" icon={<AlertTriangle size={24} />}
          color={s.card_alerts > 0 ? 'red' : 'green'} />
        <StatCard title="고용 동의 기업" value={formatNumber(s.emp_consented)}
          subtitle="4대보험·마이데이터 동의" icon={<Users size={24} />} color="blue" />
        <StatCard title="고용 경보" value={`${s.emp_alerts}건`}
          subtitle="감원·보험료 체납 신호" icon={<AlertTriangle size={24} />}
          color={s.emp_alerts > 0 ? 'red' : 'green'} />
      </div>

      <div className="grid grid-cols-2 gap-6">
        <Card title="카드매출 급락 기업" subtitle="YoY 하락 순 - 재무제표보다 먼저 움직이는 실측 매출" noPadding>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                  <th className="py-2 px-4">고객</th>
                  <th className="py-2 px-3 text-right">YoY</th>
                  <th className="py-2 px-3 text-right">동업종 백분위</th>
                  <th className="py-2 px-3 text-right">영업일</th>
                  <th className="py-2 px-4 text-right">채널점수</th>
                </tr>
              </thead>
              <tbody>
                {data.card_decliners.slice(0, 10).map((r: any) => (
                  <tr key={r.customer_id} className="border-b border-gray-50">
                    <td className="py-2 px-4">
                      <p className="font-medium text-gray-900">{r.customer_name}</p>
                      <p className="text-[11px] text-gray-400">{r.industry}</p>
                    </td>
                    <td className={`py-2 px-3 text-right tabular font-semibold ${r.yoy_pct <= -15 ? 'text-red-500' : 'text-gray-700'}`}>
                      {formatPercent(r.yoy_pct, 1)}
                    </td>
                    <td className="py-2 px-3 text-right tabular">{r.industry_percentile?.toFixed(0)}%</td>
                    <td className="py-2 px-3 text-right tabular">{r.active_days}일</td>
                    <td className={`py-2 px-4 text-right tabular font-bold ${(r.score ?? 100) < 55 ? 'text-red-500' : 'text-gray-900'}`}>
                      {r.score?.toFixed(0) ?? '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="고용 리스크 기업" subtitle="피보험자 감소·보험료 체납 - 감원은 연체보다 먼저 온다" noPadding>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                  <th className="py-2 px-4">고객</th>
                  <th className="py-2 px-3 text-right">피보험자</th>
                  <th className="py-2 px-3 text-right">3개월 증감</th>
                  <th className="py-2 px-3 text-center">체납</th>
                  <th className="py-2 px-4 text-right">채널점수</th>
                </tr>
              </thead>
              <tbody>
                {data.employment_risks.slice(0, 10).map((r: any) => (
                  <tr key={r.customer_id} className="border-b border-gray-50">
                    <td className="py-2 px-4">
                      <p className="font-medium text-gray-900">{r.customer_name}</p>
                      <p className="text-[11px] text-gray-400">{r.industry}</p>
                    </td>
                    <td className="py-2 px-3 text-right tabular">{formatNumber(r.insured_count)}명</td>
                    <td className={`py-2 px-3 text-right tabular font-semibold ${r.insured_change_3m < 0 ? 'text-red-500' : 'text-gray-700'}`}>
                      {r.insured_change_3m > 0 ? '+' : ''}{formatNumber(r.insured_change_3m)}명
                    </td>
                    <td className="py-2 px-3 text-center">
                      {r.arrears_months > 0
                        ? <Badge variant="danger">{r.arrears_months}개월</Badge>
                        : <Badge variant="gray">-</Badge>}
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

      {/* 동의 현황 */}
      {consent && (
        <Card title="채널 동의 현황" subtitle={consent.note}>
          <div className="grid grid-cols-3 gap-6">
            {Object.entries(consent.by_channel).map(([ch, st]: [string, any]) => (
              <div key={ch} className="p-3 bg-gray-50 rounded-lg">
                <p className="text-sm font-semibold text-gray-900 flex items-center gap-1.5">
                  <ShieldCheck size={15} className="text-[#00897B]" />
                  {ch === 'CARD_SALES' ? '카드매출' : ch === 'EMPLOYMENT' ? '고용' : ch}
                </p>
                <div className="flex gap-3 mt-1.5 text-xs text-gray-500">
                  <span>유효 {formatNumber(st.ACTIVE || 0)}</span>
                  <span className="text-amber-600">만료 {formatNumber(st.EXPIRED || 0)}</span>
                  <span className="text-red-500">철회 {formatNumber(st.WITHDRAWN || 0)}</span>
                </div>
              </div>
            ))}
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="text-sm font-semibold text-amber-800">만료 임박 (30일)</p>
              <p className="text-xs text-amber-700 mt-1">
                {consent.expiring_30d.length}건 - 갱신하지 않으면 채널이 결측 전환됩니다
              </p>
              <p className="text-[11px] text-amber-600 mt-0.5 truncate">
                {consent.expiring_30d.slice(0, 3).map((e: any) => e.customer_name).join(', ')}
                {consent.expiring_30d.length > 3 ? ' 외' : ''}
              </p>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
