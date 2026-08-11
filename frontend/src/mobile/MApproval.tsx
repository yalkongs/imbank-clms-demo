import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useOutletContext } from 'react-router-dom';
import { X, CheckCircle2, XCircle, Lock } from 'lucide-react';
import { formatAmount } from '../utils/format';
import { SectionSkeleton, SectionEmpty } from '../components/AsyncSection';

/**
 * 모바일 결재함 - 이동 중 결재라는 모바일 킬러 시나리오.
 * 서버 결정 전결권·직무분리·단계 가드가 모바일에서도 그대로 적용된다.
 */
export default function MApproval() {
  const { auth, openLogin } = useOutletContext<any>();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [target, setTarget] = useState<any>(null);      // 상세 시트 대상
  const [opinion, setOpinion] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<Record<string, string>>({});

  const load = () => {
    setLoading(true);
    axios.get('/api/applications/approval-inbox')
      .then(r => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  };
  useEffect(load, [auth]);

  const openDetail = (item: any) => {
    setTarget(item);
    setOpinion(null);
    axios.get(`/api/applications/${item.application_id}/opinion-draft`)
      .then(r => setOpinion(r.data)).catch(() => {});
  };

  const decide = async (decision: 'APPROVE' | 'REJECT') => {
    if (!target) return;
    setBusy(true);
    try {
      await axios.post(`/api/applications/${target.application_id}/approve`,
        null, { params: { decision } });
      setDone(d => ({ ...d, [target.application_id]: decision }));
      setTarget(null);
      load();
    } catch (e: any) {
      alert(e?.response?.data?.detail || '처리 실패');
    } finally {
      setBusy(false);
    }
  };

  if (!auth) {
    return (
      <div className="text-center py-16">
        <Lock size={28} className="mx-auto text-gray-300 mb-3" />
        <p className="text-sm text-gray-500 mb-4">결재함은 로그인 후 이용할 수 있습니다</p>
        <button onClick={openLogin} className="px-5 py-2.5 bg-[#00C7A9] text-white rounded-full text-sm font-semibold">
          체험 계정 로그인
        </button>
      </div>
    );
  }

  const items = data?.items || [];

  return (
    <>
      <div className="flex items-baseline justify-between px-0.5">
        <h1 className="text-lg font-bold text-gray-900">결재함</h1>
        <span className="text-xs text-gray-400">
          내 전결 가능 <b className="text-[#00897B]">{data?.actionable ?? 0}</b> / 전체 {items.length}건
        </span>
      </div>
      <p className="text-[11px] text-gray-400 px-0.5 -mt-2">
        {data?.level_name} 전결한도 {data?.my_limit ? formatAmount(data.my_limit, 'billion') : '무제한'} ·
        초과 건은 상위 결재 필요
      </p>

      {loading ? <SectionSkeleton rows={5} /> :
        items.length === 0 ? <SectionEmpty message="결재 대기 건이 없습니다" /> : (
          <div className="space-y-2">
            {items.map((it: any) => (
              <button key={it.application_id} onClick={() => openDetail(it)}
                className="w-full text-left bg-white border border-gray-200 rounded-xl p-3.5 active:bg-gray-50">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-gray-900 truncate">{it.customer_name}</span>
                  <span className="text-sm font-bold tabular text-gray-900 flex-none">
                    {formatAmount(it.requested_amount, 'billion')}
                  </span>
                </div>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-[11px] text-gray-400">
                    {it.application_date} · {it.credit_grade || '등급 미평가'}
                  </span>
                  {done[it.application_id] ? (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 font-bold">처리됨</span>
                  ) : it.can_approve ? (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#00C7A9]/10 text-[#00897B] font-bold">결재 가능</span>
                  ) : (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-50 text-amber-700 font-bold">
                      {it.required_name} 전결
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}

      {/* 상세 시트 */}
      {target && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-end" onClick={() => setTarget(null)}>
          <div className="w-full bg-white rounded-t-2xl max-h-[88dvh] flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 flex-none">
              <div>
                <p className="text-base font-bold text-gray-900">{target.customer_name}</p>
                <p className="text-[11px] text-gray-400">{target.application_id}</p>
              </div>
              <button onClick={() => setTarget(null)} className="p-1.5 text-gray-400"><X size={20} /></button>
            </div>

            <div className="overflow-y-auto px-4 py-3 space-y-3">
              <div className="grid grid-cols-2 gap-2 text-center">
                <div className="bg-gray-50 rounded-lg p-2.5">
                  <p className="text-[10px] text-gray-400">신청금액</p>
                  <p className="text-base font-bold tabular">{formatAmount(target.requested_amount, 'billion')}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-2.5">
                  <p className="text-[10px] text-gray-400">신용등급</p>
                  <p className="text-base font-bold">{target.credit_grade || '-'}</p>
                </div>
              </div>

              {/* 심사의견 요약 */}
              {!opinion ? (
                <SectionSkeleton rows={3} />
              ) : (
                <div className="border border-gray-200 rounded-xl p-3.5">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs font-bold text-gray-700">심사의견서 초안 요약</p>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                      opinion.verdict_code === 'APPROVE' ? 'bg-green-100 text-green-700' :
                      opinion.verdict_code === 'CONDITIONAL' ? 'bg-amber-100 text-amber-700' :
                      'bg-red-100 text-red-700'}`}>
                      {opinion.verdict}
                    </span>
                  </div>
                  {opinion.sections?.slice(-1)[0]?.text?.map((t: string, i: number) => (
                    <p key={i} className="text-[12px] text-gray-600 leading-relaxed">{t}</p>
                  ))}
                  {opinion.recommended_conditions?.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-gray-100">
                      <p className="text-[10px] font-bold text-amber-700 mb-1">권고 승인조건</p>
                      {opinion.recommended_conditions.map((c: string, i: number) => (
                        <p key={i} className="text-[11px] text-gray-500">· {c}</p>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {!target.can_approve && (
                <p className="text-[11px] text-amber-700 bg-amber-50 rounded-lg px-3 py-2">
                  이 건은 {target.required_name} 이상 전결권이 필요합니다 - 승인 시도 시 서버가 차단합니다
                </p>
              )}
            </div>

            <div className="flex gap-2 p-4 border-t border-gray-100 flex-none"
              style={{ paddingBottom: 'calc(1rem + env(safe-area-inset-bottom))' }}>
              <button disabled={busy} onClick={() => decide('REJECT')}
                className="flex-1 flex items-center justify-center gap-1.5 py-3 border border-red-200 text-red-600 rounded-xl text-sm font-bold disabled:opacity-50">
                <XCircle size={16} /> 반려
              </button>
              <button disabled={busy} onClick={() => decide('APPROVE')}
                className="flex-[2] flex items-center justify-center gap-1.5 py-3 bg-[#00C7A9] text-white rounded-xl text-sm font-bold disabled:opacity-50">
                <CheckCircle2 size={16} /> {busy ? '처리 중...' : '승인'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
