import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Percent, Clock, CheckCircle2, TrendingDown } from 'lucide-react';
import { Card, StatCard, PageLoader } from '../components';
import { formatPercent } from '../utils/format';

/**
 * 기업 금리인하요구권
 * --------------------
 * 은행법 시행령 §18-4 의 법정 절차: 접수 → 재산정 → 수용/부분/거절 결정 →
 * 10영업일 이내 사유 통지. SLA 타이머(D-day)와 결정·통지 증빙을 관리한다.
 */

export default function RateReduction() {
  const [summary, setSummary] = useState<any>(null);
  const [requests, setRequests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [decideTarget, setDecideTarget] = useState<any>(null);
  const [decision, setDecision] = useState('ACCEPTED');
  const [newRate, setNewRate] = useState('');
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);

  const load = () => {
    Promise.all([
      axios.get('/api/rate-reduction/summary'),
      axios.get('/api/rate-reduction/requests'),
    ]).then(([s, r]) => {
      setSummary(s.data);
      setRequests(r.data.requests || []);
    }).catch(console.error).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const openDecide = (r: any) => {
    setDecideTarget(r);
    setDecision('ACCEPTED');
    setNewRate(((r.old_rate || 0) * 100 - 0.3).toFixed(2));
    setReason('');
  };

  const submit = async () => {
    if (!decideTarget) return;
    setBusy(true);
    try {
      await axios.post(`/api/rate-reduction/requests/${decideTarget.request_id}/decide`, {
        decision,
        new_rate: decision === 'REJECTED' ? undefined : parseFloat(newRate) / 100,
        reason,
      });
      setDecideTarget(null);
      load();
    } catch (e: any) {
      alert(e?.response?.data?.detail || '처리 실패');
    } finally { setBusy(false); }
  };

  if (loading) return <PageLoader />;

  const pending = requests.filter(r => ['RECEIVED', 'REVIEWING'].includes(r.status));
  const done = requests.filter(r => !['RECEIVED', 'REVIEWING'].includes(r.status));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">금리인하요구권</h1>
        <p className="text-sm text-gray-500 mt-1">{summary?.sla_note}</p>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <StatCard title="처리 중" value={summary?.pending || 0} subtitle="접수·심사중"
          icon={<Clock size={22} />} color="blue" />
        <StatCard title="기한 초과" value={summary?.overdue || 0} subtitle="10영업일 SLA 위반"
          icon={<Clock size={22} />} color="red" />
        <StatCard title="수용률" value={formatPercent(summary?.acceptance_rate || 0, 1)}
          subtitle={`처리 완료 ${summary?.decided || 0}건`}
          icon={<CheckCircle2 size={22} />} color="green" />
        <StatCard title="평균 인하폭" value={`${summary?.avg_cut_bp || 0}bp`}
          icon={<TrendingDown size={22} />} color="yellow" />
      </div>

      {/* 처리 중 - SLA 타이머 */}
      <Card title={`처리 중인 요청 (${pending.length})`}>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
              <th className="py-2">기업</th>
              <th className="py-2">요구 사유</th>
              <th className="py-2 text-right">현재 금리</th>
              <th className="py-2 text-center">접수일</th>
              <th className="py-2 text-center">통지기한</th>
              <th className="py-2 text-center">SLA</th>
              <th className="py-2 text-center">처리</th>
            </tr>
          </thead>
          <tbody>
            {pending.map(r => (
              <tr key={r.request_id} className="border-b border-gray-50">
                <td className="py-2.5">
                  <span className="font-medium">{r.customer_name}</span>
                  <span className="text-xs text-gray-400 ml-1.5">{r.grade}</span>
                </td>
                <td className="py-2.5 text-xs text-gray-600">
                  <b>{r.grounds_label}</b> - {r.grounds_detail}
                </td>
                <td className="py-2.5 text-right tabular">{formatPercent((r.old_rate || 0) * 100)}</td>
                <td className="py-2.5 text-center text-xs text-gray-500">{r.request_date}</td>
                <td className="py-2.5 text-center text-xs text-gray-500">{r.due_date}</td>
                <td className="py-2.5 text-center">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                    r.overdue ? 'bg-red-600 text-white' :
                    (r.biz_days_left ?? 9) <= 2 ? 'bg-red-100 text-red-700' : 'bg-blue-50 text-blue-700'
                  }`}>
                    {r.overdue ? `기한초과 D+${-r.biz_days_left}` : `D-${r.biz_days_left}`}
                  </span>
                </td>
                <td className="py-2.5 text-center">
                  <button onClick={() => openDecide(r)}
                    className="px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700">
                    검토·결정
                  </button>
                </td>
              </tr>
            ))}
            {pending.length === 0 && (
              <tr><td colSpan={7} className="py-8 text-center text-sm text-gray-400">처리 중인 요청이 없습니다</td></tr>
            )}
          </tbody>
        </table>
      </Card>

      {/* 처리 완료 */}
      <Card title={`처리 완료 (${done.length})`}>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
              <th className="py-2">기업</th>
              <th className="py-2">사유</th>
              <th className="py-2 text-center">결정</th>
              <th className="py-2 text-right">금리 변화</th>
              <th className="py-2">결정 사유 (통지문)</th>
              <th className="py-2 text-center">통지일</th>
            </tr>
          </thead>
          <tbody>
            {done.map(r => (
              <tr key={r.request_id} className="border-b border-gray-50">
                <td className="py-2">{r.customer_name}</td>
                <td className="py-2 text-xs text-gray-500">{r.grounds_label}</td>
                <td className="py-2 text-center">
                  <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                    r.status === 'ACCEPTED' ? 'bg-green-100 text-green-700' :
                    r.status === 'PARTIAL' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>{r.status_label}</span>
                </td>
                <td className="py-2 text-right tabular text-xs">
                  {formatPercent((r.old_rate || 0) * 100)}
                  {r.status !== 'REJECTED' && (
                    <> → <b className="text-green-700">{formatPercent((r.decided_rate || 0) * 100)}</b></>
                  )}
                </td>
                <td className="py-2 text-xs text-gray-500 max-w-sm truncate">{r.decision_reason}</td>
                <td className="py-2 text-center text-xs text-gray-400">{r.notified_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* 결정 모달 */}
      {decideTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="modal-in w-full max-w-md bg-white rounded-2xl shadow-2xl p-6">
            <h3 className="text-base font-bold text-gray-900 mb-1">금리인하요구 결정</h3>
            <p className="text-xs text-gray-500 mb-4">
              {decideTarget.customer_name} · 현재 금리 {formatPercent((decideTarget.old_rate || 0) * 100)} ·
              통지기한 {decideTarget.due_date}
            </p>
            <div className="space-y-3">
              <div className="flex gap-2">
                {[['ACCEPTED', '수용'], ['PARTIAL', '부분수용'], ['REJECTED', '거절']].map(([v, l]) => (
                  <button key={v} onClick={() => setDecision(v)}
                    className={`flex-1 py-1.5 rounded-lg text-sm font-medium border ${
                      decision === v ? 'border-blue-600 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-500'
                    }`}>{l}</button>
                ))}
              </div>
              {decision !== 'REJECTED' && (
                <label className="block text-sm">
                  <span className="text-gray-500 text-xs">재산정 금리 (%)</span>
                  <input type="number" step="0.01" value={newRate}
                    onChange={e => setNewRate(e.target.value)}
                    className="mt-1 w-full border rounded-lg px-3 py-2 text-sm" />
                </label>
              )}
              <label className="block text-sm">
                <span className="text-gray-500 text-xs">결정 사유 (고객 통지문에 포함 - 필수)</span>
                <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3}
                  placeholder="예: 재산정 결과 신용원가 하락 확인 - 전액 수용"
                  className="mt-1 w-full border rounded-lg px-3 py-2 text-sm" />
              </label>
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={() => setDecideTarget(null)}
                className="px-4 py-2 text-sm border border-gray-300 rounded-lg">취소</button>
              <button onClick={submit} disabled={busy || reason.trim().length < 5}
                className="btn-accent px-5 text-sm disabled:opacity-50">
                {busy ? '처리 중...' : '결정·통지'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
