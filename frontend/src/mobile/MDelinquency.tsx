import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { formatAmount, formatPercent } from '../utils/format';
import { SectionSkeleton, SectionEmpty } from '../components/AsyncSection';

const STAGE_STYLE: Record<string, string> = {
  EARLY: 'bg-yellow-100 text-yellow-800',
  MID: 'bg-orange-100 text-orange-800',
  LATE: 'bg-red-100 text-red-800',
  NPL: 'bg-red-200 text-red-900',
  WRITEOFF: 'bg-gray-200 text-gray-900',
};

/** 모바일 연체 현황 */
export default function MDelinquency() {
  const [dash, setDash] = useState<any>(null);
  const [items, setItems] = useState<any[] | null>(null);

  useEffect(() => {
    axios.get('/api/delinquency/dashboard').then(r => setDash(r.data)).catch(() => {});
    axios.get('/api/delinquency/active', { params: { limit: 30 } })
      .then(r => setItems(r.data.items || [])).catch(() => setItems([]));
  }, []);

  return (
    <>
      <h1 className="text-lg font-bold text-gray-900 px-0.5">연체 현황</h1>

      <div className="grid grid-cols-2 gap-2">
        <div className="bg-white border border-gray-200 rounded-xl p-3.5">
          <p className="text-[10px] text-gray-400">연체율</p>
          <p className="text-xl font-bold tabular text-red-600">{formatPercent(dash?.delinquency_rate || 0)}</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-3.5">
          <p className="text-[10px] text-gray-400">연체 익스포저</p>
          <p className="text-xl font-bold tabular">{formatAmount(dash?.total_delinquent || 0, 'billion')}</p>
        </div>
      </div>

      {/* 단계 버킷 */}
      {dash?.buckets && (
        <div className="bg-white border border-gray-200 rounded-xl p-3.5">
          <p className="text-xs font-bold text-gray-700 mb-2">단계별 현황</p>
          <div className="space-y-1.5">
            {dash.buckets.map((b: any) => (
              <div key={b.stage} className="flex items-center gap-2 text-xs">
                <span className={`w-14 text-center py-0.5 rounded font-semibold flex-none text-[10px] ${STAGE_STYLE[b.stage] || 'bg-gray-100'}`}>
                  {b.label_ko}
                </span>
                <span className="text-gray-500 flex-none">{b.count}건</span>
                <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full bg-red-400 rounded-full"
                    style={{ width: `${Math.min((b.exposure / (dash.total_delinquent || 1)) * 100, 100)}%` }} />
                </div>
                <span className="tabular text-gray-700 flex-none">{formatAmount(b.exposure, 'billion')}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs font-bold text-gray-700 px-0.5">연체 목록</p>
      {items === null ? <SectionSkeleton rows={5} /> :
        items.length === 0 ? <SectionEmpty message="연체 건이 없습니다" /> : (
          <div className="space-y-2">
            {items.map((it: any) => (
              <div key={it.delinquency_id} className="bg-white border border-gray-200 rounded-xl p-3.5">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-gray-900 truncate">{it.company_name}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold flex-none ${STAGE_STYLE[it.stage] || 'bg-gray-100'}`}>
                    {it.stage_label} D+{it.dpd}
                  </span>
                </div>
                <p className="text-[11px] text-gray-400 mt-1">
                  연체 {formatAmount(it.overdue_amount, 'billion')} · 잔액 {formatAmount(it.outstanding, 'billion')} · 담당 {it.assigned_officer || '-'}
                </p>
              </div>
            ))}
          </div>
        )}
    </>
  );
}
