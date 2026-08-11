import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Search, X } from 'lucide-react';
import { formatAmount, formatPercent } from '../utils/format';
import { SectionSkeleton, SectionEmpty } from '../components/AsyncSection';

/** 모바일 고객 조회 - RM 현장용 기업 요약 */
export default function MCustomers() {
  const [q, setQ] = useState('');
  const [list, setList] = useState<any[] | null>(null);
  const [target, setTarget] = useState<any>(null);
  const [detail, setDetail] = useState<any>(null);

  const search = (query: string) => {
    setList(null);
    axios.get('/api/customers', { params: { page: 1, page_size: 20, search: query || undefined } })
      .then(r => setList(r.data.data || []))
      .catch(() => setList([]));
  };
  useEffect(() => search(''), []);

  const openDetail = (c: any) => {
    setTarget(c);
    setDetail(null);
    axios.get(`/api/customers/${c.customer_id}`).then(r => setDetail(r.data)).catch(() => {});
  };

  return (
    <>
      <h1 className="text-lg font-bold text-gray-900 px-0.5">고객 조회</h1>

      <form onSubmit={e => { e.preventDefault(); search(q); }}
        className="flex items-center gap-2 bg-white border border-gray-200 rounded-xl px-3.5 py-1">
        <Search size={16} className="text-gray-400 flex-none" />
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="기업명 검색"
          className="flex-1 py-2.5 text-sm outline-none min-w-0" />
        {q && <button type="button" onClick={() => { setQ(''); search(''); }} className="text-gray-300"><X size={15} /></button>}
      </form>

      {list === null ? <SectionSkeleton rows={6} /> :
        list.length === 0 ? <SectionEmpty message="검색 결과가 없습니다" /> : (
          <div className="space-y-2">
            {list.map((c: any) => (
              <button key={c.customer_id} onClick={() => openDetail(c)}
                className="w-full text-left bg-white border border-gray-200 rounded-xl p-3.5 active:bg-gray-50">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-gray-900 truncate">{c.customer_name}</span>
                  <span className="text-xs font-bold text-[#00897B] flex-none">{c.credit_rating || '미평가'}</span>
                </div>
                <p className="text-[11px] text-gray-400 mt-0.5">
                  {c.industry_name} · {c.size_category} · 여신 {c.facility_count || 0}건 {formatAmount(c.total_exposure || 0, 'billion')}
                </p>
              </button>
            ))}
          </div>
        )}

      {/* 기업 요약 시트 */}
      {target && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-end" onClick={() => setTarget(null)}>
          <div className="w-full bg-white rounded-t-2xl max-h-[85dvh] overflow-y-auto p-4 pb-8" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-3">
              <div>
                <p className="text-base font-bold text-gray-900">{target.customer_name}</p>
                <p className="text-[11px] text-gray-400">{target.industry_name} · {target.address || '-'}</p>
              </div>
              <button onClick={() => setTarget(null)} className="p-1.5 text-gray-400"><X size={20} /></button>
            </div>

            {!detail ? <SectionSkeleton rows={4} /> : (
              <div className="space-y-3">
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="bg-gray-50 rounded-lg p-2.5">
                    <p className="text-[10px] text-gray-400">등급</p>
                    <p className="text-sm font-bold">{detail.basic_info?.credit_rating || target.credit_rating || '-'}</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-2.5">
                    <p className="text-[10px] text-gray-400">총여신</p>
                    <p className="text-sm font-bold tabular">
                      {formatAmount(detail.exposure_summary?.total_outstanding ?? target.total_exposure ?? 0, 'billion')}
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-2.5">
                    <p className="text-[10px] text-gray-400">PD</p>
                    <p className="text-sm font-bold tabular">
                      {formatPercent((detail.basic_info?.probability_default ?? target.probability_default ?? 0) * 100, 2)}
                    </p>
                  </div>
                </div>

                {(detail.facilities || []).length > 0 && (
                  <div>
                    <p className="text-xs font-bold text-gray-700 mb-1.5">보유 여신</p>
                    <div className="space-y-1.5">
                      {detail.facilities.slice(0, 5).map((f: any) => (
                        <div key={f.facility_id} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2 text-xs">
                          <span className="text-gray-600">{f.facility_type || f.product_name || f.facility_id}</span>
                          <span className="tabular font-semibold">{formatAmount(f.outstanding_amount || 0, 'billion')}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
