import React, { useEffect, useState } from 'react';
import { CalendarClock, Recycle, AlertTriangle, Eye } from 'lucide-react';
import { Card, StatCard, Badge, Deadline } from '../components';
import { formatNumber, formatPercent } from '../utils/format';
import axios from 'axios';

/**
 * 여신 거래 생애주기 (P6 씬슬라이스)
 *
 * 기한연장 + 조건변경 재승인 두 거래. 에버그리닝(만기연장 부실 이연) 통제가
 * 중심 - 연장 심사 시 서버가 EWS·분류·약정·연속연장 이력을 강제 수집하고,
 * 플래그가 있으면 부서장 이상 전결로 상향된다. 기업대출 연체율 2.43%
 * (장기평균 상회) 국면의 고전적 감독 관심사를 시스템 통제로 만든 화면.
 */

export default function FacilityLifecycle() {
  const [maturing, setMaturing] = useState<any>(null);
  const [txns, setTxns] = useState<any[]>([]);
  const [watch, setWatch] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [modRate, setModRate] = useState<Record<string, string>>({});

  const reload = () =>
    Promise.all([
      axios.get('/api/lifecycle/maturing', { params: { days_ahead: 90 } }),
      axios.get('/api/lifecycle/transactions'),
      axios.get('/api/lifecycle/evergreening-watch'),
    ]).then(([m, t, w]) => {
      setMaturing(m.data);
      setTxns(t.data.transactions);
      setWatch(w.data);
    }).catch(console.error);

  useEffect(() => { reload().finally(() => setLoading(false)); }, []);

  const act = (key: string, fn: () => Promise<any>) => {
    setBusy(key);
    setMsg(null);
    fn()
      .then(r => {
        const flags = r.data?.evergreen_flags;
        if (flags && flags.length) {
          setMsg(`⚠ 에버그리닝 플래그 ${flags.length}건 - 부서장 이상 결재로 상향: ${flags[0]}`);
        } else if (r.data?.decision) {
          setMsg(`${r.data.decision === 'APPROVED' ? '승인' : '반려'} 완료 (${r.data.decided_level} ${r.data.decided_by}, 감사기록)`);
        } else {
          setMsg('신청 완료 - 심사중 거래로 이동했습니다');
        }
        return reload();
      })
      .catch(e => setMsg(e?.response?.data?.detail || '처리 실패 - 로그인/전결권을 확인하세요'))
      .finally(() => setBusy(null));
  };

  if (loading || !maturing) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const pending = txns.filter(t => t.status === 'REQUESTED');
  const riskyCount = maturing.facilities.filter((f: any) => f.risk_marks.length > 0).length;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">여신 거래 생애주기</h1>
          <p className="text-sm text-gray-500 mt-1">
            기한연장·조건변경 재승인 - 에버그리닝 플래그는 부서장 이상 전결로 자동 상향
          </p>
        </div>
        <span className="px-2.5 py-1 bg-amber-50 text-amber-700 text-xs rounded-full font-medium border border-amber-200">
          기업대출 연체율 2.43% (장기평균 1.62% 상회) - 만기연장 이연 통제 국면
        </span>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="만기 도래 (90일)"
          value={`${maturing.total}건`}
          subtitle={`${formatNumber(maturing.facilities.reduce((s: number, f: any) => s + f.outstanding_eok, 0))}억 - 연장 심사 파이프라인`}
          icon={<CalendarClock size={24} />}
          color="blue"
        />
        <StatCard
          title="위험 표식 보유"
          value={`${riskyCount}건`}
          subtitle="연체·분류하락·EWS악화·기연장 - 연장 시 플래그"
          icon={<AlertTriangle size={24} />}
          color={riskyCount > 0 ? 'red' : 'green'}
        />
        <StatCard
          title="심사중 거래"
          value={`${pending.length}건`}
          subtitle="연장·조건변경 결재 대기"
          icon={<Recycle size={24} />}
          color="yellow"
        />
        <StatCard
          title="에버그리닝 관제"
          value={`${watch?.items?.length || 0}건`}
          subtitle="플래그 안고 승인된 거래의 사후 추적"
          icon={<Eye size={24} />}
          color="gray"
        />
      </div>

      {msg && (
        <div className="px-4 py-2.5 bg-[#00BFA5]/10 border border-[#00BFA5]/30 rounded-lg text-sm font-medium text-[#00695F]">
          {msg}
        </div>
      )}

      {/* 만기 도래 파이프라인 */}
      <Card title="만기 도래 여신" subtitle="연장 신청 시 리스크 스냅샷을 서버가 강제 수집 - 좋은 값만 골라 낼 수 없다" noPadding>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                <th className="py-2 px-4">고객 / 여신</th>
                <th className="py-2 px-3 text-right">잔액 (억)</th>
                <th className="py-2 px-3 text-right">만기</th>
                <th className="py-2 px-3 text-right">EWS</th>
                <th className="py-2 px-3">위험 표식</th>
                <th className="py-2 px-3 text-right">변경금리 (%)</th>
                <th className="py-2 px-4 text-center">거래</th>
              </tr>
            </thead>
            <tbody>
              {maturing.facilities.slice(0, 12).map((f: any) => (
                <tr key={f.facility_id} className="border-b border-gray-50">
                  <td className="py-2 px-4">
                    <p className="font-medium text-gray-900">{f.customer_name}</p>
                    <p className="text-[11px] text-gray-400">{f.facility_type} · {f.facility_id}</p>
                  </td>
                  <td className="py-2 px-3 text-right tabular">{formatNumber(f.outstanding_eok)}</td>
                  <td className="py-2 px-3 text-right">
                    <Deadline date={f.maturity_date} days={f.days_to_maturity} />
                  </td>
                  <td className={`py-2 px-3 text-right tabular ${f.ews_score !== null && f.ews_score < 50 ? 'text-red-500 font-semibold' : ''}`}>
                    {f.ews_score !== null ? f.ews_score.toFixed(1) : '-'}
                  </td>
                  <td className="py-2 px-3">
                    <div className="flex flex-wrap gap-1">
                      {f.risk_marks.length === 0
                        ? <Badge variant="success">정상</Badge>
                        : f.risk_marks.map((m: string) => <Badge key={m} variant="danger">{m}</Badge>)}
                    </div>
                  </td>
                  <td className="py-2 px-3 text-right">
                    <input value={modRate[f.facility_id] || ''} placeholder="4.2"
                      onChange={e => setModRate({ ...modRate, [f.facility_id]: e.target.value })}
                      className="w-16 px-2 py-1 text-xs text-right border border-gray-200 rounded" />
                  </td>
                  <td className="py-2 px-4">
                    <div className="flex gap-1.5 justify-center">
                      <button disabled={f.pending_txn || busy !== null}
                        onClick={() => act(f.facility_id, () =>
                          axios.post(`/api/lifecycle/extension/${f.facility_id}`, null, { params: { extension_months: 12 } }))}
                        className="px-2.5 py-1 text-xs font-medium bg-[#00897B] text-white rounded-lg hover:bg-[#00695F] disabled:opacity-40">
                        {f.pending_txn ? '심사중' : '연장 12개월'}
                      </button>
                      <button disabled={f.pending_txn || busy !== null || !modRate[f.facility_id]}
                        onClick={() => act(f.facility_id, () =>
                          axios.post(`/api/lifecycle/modification/${f.facility_id}`, null, { params: { new_rate: Number(modRate[f.facility_id]) } }))}
                        className="px-2.5 py-1 text-xs font-medium border border-[#00897B] text-[#00897B] rounded-lg hover:bg-[#00BFA5]/10 disabled:opacity-40">
                        금리변경
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-6">
        {/* 심사중 거래 결재 */}
        <Card title="심사중 거래 결재" subtitle="플래그 있으면 부서장 미만 결재 403 - 서버가 판정">
          {pending.length === 0 ? (
            <p className="text-sm text-gray-400 py-6 text-center">심사중 거래 없음 - 위 파이프라인에서 연장·변경을 신청해 보세요</p>
          ) : (
            <div className="space-y-3">
              {pending.map((t: any) => (
                <div key={t.txn_id} className={`p-3 rounded-lg border ${t.evergreen_flags.length ? 'badge-alert border-red-200 bg-red-50/40' : 'border-gray-200 bg-gray-50'}`}>
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-gray-900">
                      {t.customer_name}
                      <span className="ml-2 text-xs font-normal text-gray-500">
                        {t.txn_type === 'EXTENSION' ? `기한연장 +${t.extension_months}개월` : '조건변경'}
                      </span>
                    </p>
                    <span className="text-[11px] text-gray-400">{t.requested_by} 신청</span>
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-gray-500 mt-1.5">
                    <span>잔액 {formatNumber(Math.round((t.review.outstanding || 0) / 1e8))}억</span>
                    <span>분류 {t.review.classification}</span>
                    <span>DPD {t.review.dpd}일</span>
                    <span>EWS {t.review.ews_score?.toFixed?.(1) ?? '-'}</span>
                    {t.txn_type === 'EXTENSION' && <span>연속연장 {t.consecutive_extensions}회차</span>}
                    {t.change?.rate && <span>금리 {formatPercent(t.change.rate.from, 2)} → {formatPercent(t.change.rate.to, 2)}</span>}
                  </div>
                  {t.evergreen_flags.length > 0 && (
                    <div className="mt-2 space-y-0.5">
                      {t.evergreen_flags.map((fl: string) => (
                        <p key={fl} className="text-[11px] text-red-600 font-medium">⚑ {fl}</p>
                      ))}
                    </div>
                  )}
                  <div className="flex gap-2 mt-2.5">
                    <button disabled={busy !== null}
                      onClick={() => act(t.txn_id, () =>
                        axios.post(`/api/lifecycle/transactions/${t.txn_id}/decide`, null,
                          { params: { decision: 'APPROVED', reason: t.evergreen_flags.length ? '조건부 연장 - 사후관리 강화' : '정상 갱신' } }))}
                      className="px-3 py-1 text-xs font-semibold bg-[#00897B] text-white rounded-lg hover:bg-[#00695F] disabled:opacity-40">
                      승인
                    </button>
                    <button disabled={busy !== null}
                      onClick={() => act(t.txn_id, () =>
                        axios.post(`/api/lifecycle/transactions/${t.txn_id}/decide`, null,
                          { params: { decision: 'REJECTED', reason: '상환계획 미흡' } }))}
                      className="px-3 py-1 text-xs font-semibold border border-red-300 text-red-500 rounded-lg hover:bg-red-50 disabled:opacity-40">
                      반려
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* 에버그리닝 관제 */}
        <Card title="에버그리닝 관제" subtitle={watch?.note}>
          {(watch?.items || []).length === 0 ? (
            <p className="text-sm text-gray-400 py-6 text-center">플래그를 안고 승인된 거래 없음</p>
          ) : (
            <div className="space-y-3">
              {watch.items.map((w: any) => (
                <div key={w.txn_id} className="p-3 bg-amber-50/60 border border-amber-200 rounded-lg">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-gray-900">{w.customer_name}</p>
                    <Badge variant="warning">{w.decided_level} {w.decided_by}</Badge>
                  </div>
                  <div className="mt-1 space-y-0.5">
                    {w.flags.map((fl: string) => (
                      <p key={fl} className="text-[11px] text-amber-700">⚑ {fl}</p>
                    ))}
                  </div>
                  <p className="text-[11px] text-gray-500 mt-1.5">
                    현재 DPD {w.current_dpd}일 · 분류 {w.current_class} · 승인 {w.decided_at?.slice(0, 10)}
                  </p>
                </div>
              ))}
            </div>
          )}
          <p className="text-[11px] text-gray-400 mt-3 leading-relaxed">
            플래그를 무시한 연장은 존재할 수 있다 - 단, 반드시 부서장 이상의 실명
            결재로 남고 이 관제 목록에서 사후 건전성을 추적한다. 통제는 금지가
            아니라 책임의 귀속이다.
          </p>
        </Card>
      </div>

      {/* 처리 완료 이력 */}
      <Card title="거래 이력" noPadding>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                <th className="py-2 px-4">거래</th>
                <th className="py-2 px-3">고객</th>
                <th className="py-2 px-3">유형</th>
                <th className="py-2 px-3">신청</th>
                <th className="py-2 px-3">결재</th>
                <th className="py-2 px-4 text-center">상태</th>
              </tr>
            </thead>
            <tbody>
              {txns.slice(0, 8).map((t: any) => (
                <tr key={t.txn_id} className="border-b border-gray-50">
                  <td className="py-2 px-4 text-xs font-mono text-gray-500">{t.txn_id}</td>
                  <td className="py-2 px-3 font-medium text-gray-900">{t.customer_name}</td>
                  <td className="py-2 px-3 text-xs text-gray-600">
                    {t.txn_type === 'EXTENSION' ? `연장 +${t.extension_months}M` : '조건변경'}
                    {t.evergreen_flags.length > 0 && <span className="text-red-500 ml-1">⚑{t.evergreen_flags.length}</span>}
                  </td>
                  <td className="py-2 px-3 text-xs text-gray-500">{t.requested_by} · {t.requested_at?.slice(0, 10)}</td>
                  <td className="py-2 px-3 text-xs text-gray-500">{t.decided_by ? `${t.decided_by} (${t.decided_level})` : '-'}</td>
                  <td className="py-2 px-4 text-center">
                    <Badge variant={t.status === 'APPROVED' ? 'success' : t.status === 'REJECTED' ? 'danger' : 'warning'}>
                      {t.status === 'APPROVED' ? '승인' : t.status === 'REJECTED' ? '반려' : '심사중'}
                    </Badge>
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
