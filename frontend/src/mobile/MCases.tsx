import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Lock } from 'lucide-react';
import { formatAmount } from '../utils/format';
import { SectionSkeleton, SectionEmpty } from '../components/AsyncSection';

/** 모바일 전자 여신철 - 승인 기록·봉인 여부 조회 */
export default function MCases() {
  const [cases, setCases] = useState<any[] | null>(null);

  useEffect(() => {
    axios.get('/api/credit-case').then(r => setCases(r.data.cases || [])).catch(() => setCases([]));
  }, []);

  return (
    <>
      <div className="flex items-baseline justify-between px-0.5">
        <h1 className="text-lg font-bold text-gray-900">전자 여신철</h1>
        <span className="text-xs text-gray-400">{cases?.length ?? 0}건</span>
      </div>
      <p className="text-[11px] text-gray-400 px-0.5 -mt-2">
        🔒 표시는 승인 당시 심사자료가 확정·보존된 건입니다
      </p>

      {cases === null ? <SectionSkeleton rows={6} /> :
        cases.length === 0 ? <SectionEmpty /> : (
          <div className="space-y-2">
            {cases.map((c: any) => (
              <div key={c.application_id} className="bg-white border border-gray-200 rounded-xl p-3.5">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-gray-900 truncate">
                    {c.sealed && <Lock size={11} className="inline mr-1 text-[#00897B] -mt-0.5" />}
                    {c.customer_name}
                  </span>
                  <span className="text-sm font-bold tabular flex-none">{formatAmount(c.requested_amount, 'billion')}</span>
                </div>
                <div className="flex items-center justify-between mt-1 text-[11px] text-gray-400">
                  <span>{c.application_date} · 결재 {c.approvals}회{c.exceptions > 0 ? ` · 예외 ${c.exceptions}` : ''}</span>
                  <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-bold ${
                    c.status === 'APPROVED' || c.status === 'DISBURSED' ? 'bg-green-100 text-green-700' :
                    c.status === 'REJECTED' ? 'bg-gray-200 text-gray-600' : 'bg-blue-50 text-blue-700'}`}>
                    {c.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
    </>
  );
}
