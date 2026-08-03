import React, { useCallback, useEffect, useState } from 'react';
import { Stamp, ShieldAlert } from 'lucide-react';
import { Card } from '../components';
import { formatAmount, formatNumber } from '../utils/format';
import { useTheme, ROLES } from '../context/ThemeProvider';
import axios from 'axios';

/**
 * 결재함 — 전결권 체계의 실행 화면.
 *
 * 심사 진행 중인 신청을 필요 전결 레벨과 함께 보여주고, 현재 역할(헤더에서 전환)의
 * 권한으로 결재 가능한 건만 승인 버튼이 활성화된다. 권한을 넘는 건을 승인하려 하면
 * 서버가 403 으로 차단한다(전결권 검증) — 그 흐름을 그대로 체험시킨다.
 */
export default function ApprovalInbox() {
  const { role } = useTheme();
  const me = ROLES[role];
  const [data, setData] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    axios.get('/api/applications/approval-inbox', { params: { level: me.level } })
      .then(r => setData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [me.level]);

  useEffect(() => { load(); }, [load]);

  const decide = async (id: string, decision: 'APPROVE' | 'REJECT') => {
    setBusy(id);
    setMessage(null);
    try {
      await axios.post(`/api/applications/${id}/approve`, null, {
        params: {
          decision,
          approval_level: me.level,
          approver_name: `${me.name}(${me.title})`,
        },
      });
      setMessage({ kind: 'ok', text: `${id} ${decision === 'APPROVE' ? '승인' : '반려'} 완료 — 감사 추적에 기록되었습니다` });
      load();
    } catch (e: any) {
      setMessage({ kind: 'err', text: e?.response?.data?.detail || '처리 실패' });
    } finally {
      setBusy(null);
    }
  };

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">결재함</h1>
          <p className="text-sm text-gray-500 mt-1">
            {me.name} {me.title} — 전결 한도{' '}
            {data?.my_limit ? formatAmount(data.my_limit, 'billion') : '무제한'} ·
            결재 가능 {formatNumber(data?.actionable || 0)}건 / 전체 {formatNumber(data?.items?.length || 0)}건
          </p>
        </div>
        <p className="text-xs text-gray-400">역할은 우측 상단 아바타에서 전환</p>
      </div>

      {message && (
        <div className={`rounded-xl px-4 py-3 text-sm ${
          message.kind === 'ok' ? 'bg-green-50 text-green-800 border border-green-200'
                                : 'bg-red-50 text-red-800 border border-red-200'}`}>
          {message.kind === 'err' && <ShieldAlert size={15} className="inline mr-1.5 -mt-0.5" />}
          {message.text}
        </div>
      )}

      <Card title="심사 진행 건">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
              <th className="py-2 pr-4">신청</th>
              <th className="py-2 pr-4">고객</th>
              <th className="py-2 pr-4">등급</th>
              <th className="py-2 pr-4 text-right">신청 금액</th>
              <th className="py-2 pr-4">필요 전결</th>
              <th className="py-2 text-right">처리</th>
            </tr>
          </thead>
          <tbody>
            {(data?.items || []).map((it: any) => (
              <tr key={it.application_id} className="border-b border-gray-50">
                <td className="py-2.5 pr-4">
                  <p className="font-medium text-gray-900">{it.application_id}</p>
                  <p className="text-xs text-gray-400">{it.application_date} · {it.current_stage}</p>
                </td>
                <td className="py-2.5 pr-4">{it.customer_name}</td>
                <td className="py-2.5 pr-4">{it.credit_grade || '—'}</td>
                <td className="py-2.5 pr-4 text-right tabular font-medium">
                  {formatAmount(it.requested_amount, 'billion')}
                </td>
                <td className="py-2.5 pr-4">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    it.can_approve ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                    {it.required_name}
                  </span>
                </td>
                <td className="py-2.5 text-right whitespace-nowrap">
                  {it.can_approve ? (
                    <>
                      <button
                        disabled={busy === it.application_id}
                        onClick={() => decide(it.application_id, 'APPROVE')}
                        className="px-3 py-1 text-xs font-semibold bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                      >승인</button>
                      <button
                        disabled={busy === it.application_id}
                        onClick={() => decide(it.application_id, 'REJECT')}
                        className="ml-1.5 px-3 py-1 text-xs font-semibold border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                      >반려</button>
                    </>
                  ) : (
                    <span className="text-xs text-gray-400 flex items-center justify-end gap-1">
                      <Stamp size={13} /> {it.required_name} 결재 필요
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(data?.items || []).length === 0 && (
          <p className="py-8 text-sm text-gray-400 text-center">심사 진행 중인 신청이 없습니다</p>
        )}
      </Card>
    </div>
  );
}
