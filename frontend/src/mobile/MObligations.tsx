import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { SectionSkeleton, SectionEmpty } from '../components/AsyncSection';

const TYPE_COLORS: Record<string, string> = {
  '정책 예외 재검토': 'bg-red-50 text-red-700',
  'EWS 조치': 'bg-amber-50 text-amber-700',
  '코베넌트 점검': 'bg-blue-50 text-blue-700',
  '금리인하요구': 'bg-purple-50 text-purple-700',
  '승인조건 이행': 'bg-emerald-50 text-emerald-700',
};

/** 모바일 의무관리함 - 기한 도래·초과 의무를 한눈에 */
export default function MObligations() {
  const [data, setData] = useState<any>(null);
  const [overdueOnly, setOverdueOnly] = useState(false);

  useEffect(() => {
    axios.get('/api/obligations').then(r => setData(r.data)).catch(() => setData({ items: [] }));
  }, []);

  const items = (data?.items || []).filter((i: any) => !overdueOnly || i.overdue);

  return (
    <>
      <div className="flex items-baseline justify-between px-0.5">
        <h1 className="text-lg font-bold text-gray-900">의무관리함</h1>
        <span className="text-xs text-gray-400">
          기한 초과 <b className="text-red-600">{data?.overdue ?? 0}</b> / 전체 {data?.total ?? 0}건
        </span>
      </div>

      <div className="flex gap-1.5">
        <button onClick={() => setOverdueOnly(false)}
          className={`px-3 py-1.5 rounded-full text-xs font-semibold border ${
            !overdueOnly ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-500 border-gray-200'}`}>
          전체
        </button>
        <button onClick={() => setOverdueOnly(true)}
          className={`px-3 py-1.5 rounded-full text-xs font-semibold border ${
            overdueOnly ? 'bg-red-600 text-white border-red-600' : 'bg-white text-gray-500 border-gray-200'}`}>
          기한 초과만
        </button>
      </div>

      {!data ? <SectionSkeleton rows={6} /> :
        items.length === 0 ? <SectionEmpty message="해당하는 의무가 없습니다" /> : (
          <div className="space-y-2">
            {items.map((i: any, idx: number) => (
              <div key={`${i.type}-${i.ref_id}-${idx}`}
                className={`bg-white border rounded-xl p-3.5 ${i.overdue ? 'border-red-200' : 'border-gray-200'}`}>
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${TYPE_COLORS[i.type_ko] || 'bg-gray-100 text-gray-600'}`}>
                    {i.type_ko}
                  </span>
                  <span className={`text-[11px] ${i.overdue ? 'text-red-600 font-bold' : 'text-gray-400'}`}>
                    {i.overdue ? `기한초과 ${i.due_date || ''}` : (i.due_date || '-')}
                  </span>
                </div>
                <p className="text-xs text-gray-700 leading-snug">{i.subject}</p>
                <p className="text-[10px] text-gray-400 mt-1">{i.owner}</p>
              </div>
            ))}
          </div>
        )}
    </>
  );
}
