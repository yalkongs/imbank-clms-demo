import { Link } from 'react-router-dom';
import React, { useCallback, useEffect, useState } from 'react';
import { Stamp, ShieldAlert } from 'lucide-react';
import { Card, Modal } from '../components';
import { formatAmount, formatNumber, formatInputAmount, parseFormattedNumber } from '../utils/format';
import { Link as RouterLink } from 'react-router-dom';
import { getAuth, onAuthChange } from '../utils/api';
import axios from 'axios';

type ConditionTemplate = {
  code: string; label: string; type: 'CP' | 'CS';
  due_days: number; type_name: string;
};

type DecideForm = {
  approved_amount: number;
  approved_rate: number;    // 화면 단위는 % - 전송 시 100 으로 나눈다
  approved_tenor: number;
  comments: string;
  conditions: string[];
};

const EMPTY_FORM: DecideForm = {
  approved_amount: 0, approved_rate: 0, approved_tenor: 0,
  comments: '', conditions: [],
};

/**
 * 결재함 - 전결권 체계의 실행 화면.
 *
 * 심사 진행 중인 신청을 필요 전결 레벨과 함께 보여주고, 현재 역할(헤더에서 전환)의
 * 권한으로 결재 가능한 건만 승인 버튼이 활성화된다. 권한을 넘는 건을 승인하려 하면
 * 서버가 403 으로 차단한다(전결권 검증) - 그 흐름을 그대로 체험시킨다.
 */
export default function ApprovalInbox() {
  const [auth, setAuth] = React.useState(getAuth());
  React.useEffect(() => onAuthChange(setAuth), []);
  const me = auth?.user
    ? { name: auth.user.name, title: auth.user.level_ko, level: auth.user.approval_level }
    : { name: '미로그인', title: '조회 전용', level: 'TEAM_LEAD' };
  const [data, setData] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null);
  const [loading, setLoading] = useState(true);

  // 결재 모달 - 승인은 금액·금리·기간·승인조건을 확정하는 자리다.
  // 종전에는 decision 만 보내 승인금리·기간·조건이 기록되지 않았다.
  const [target, setTarget] = useState<any>(null);
  const [mode, setMode] = useState<'APPROVE' | 'REJECT'>('APPROVE');
  const [form, setForm] = useState<DecideForm>(EMPTY_FORM);
  const [templates, setTemplates] = useState<ConditionTemplate[]>([]);
  const [loadingDefaults, setLoadingDefaults] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    axios.get('/api/applications/approval-inbox', { params: auth?.user ? {} : { level: me.level } })
      .then(r => setData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [me.level, auth?.user?.user_id]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    axios.get('/api/applications/condition-templates')
      .then(r => setTemplates(r.data.items || []))
      .catch(console.error);
  }, []);

  // 조건을 하나라도 달면 조건부승인 - 서버도 같은 규칙을 강제한다(불일치 시 422)
  const decision: 'APPROVE' | 'CONDITIONAL' | 'REJECT' =
    mode === 'REJECT' ? 'REJECT' : (form.conditions.length ? 'CONDITIONAL' : 'APPROVE');

  const openDecision = (item: any, kind: 'APPROVE' | 'REJECT') => {
    setMode(kind);
    setTarget(item);
    setMessage(null);
    setForm({ ...EMPTY_FORM, approved_amount: item.requested_amount || 0 });
    if (kind === 'REJECT') return;
    // 기본값은 심사 결과에서 가져온다 - 산출 금리·신청 기간을 그대로 승인하는 것이 기본
    setLoadingDefaults(true);
    axios.get(`/api/applications/${item.application_id}`)
      .then(r => {
        const a = r.data?.application, p = r.data?.pricing;
        setForm(f => ({
          ...f,
          approved_amount: a?.requested_amount ?? item.requested_amount ?? 0,
          approved_rate: Number((((p?.final_rate ?? a?.requested_rate) || 0) * 100).toFixed(2)),
          approved_tenor: a?.requested_tenor ?? 36,
        }));
      })
      .catch(console.error)
      .finally(() => setLoadingDefaults(false));
  };

  const toggleCondition = (code: string) => setForm(f => ({
    ...f,
    conditions: f.conditions.includes(code)
      ? f.conditions.filter(c => c !== code)
      : [...f.conditions, code],
  }));

  const submitDecision = async () => {
    if (!target) return;
    const id = target.application_id;
    setBusy(id);
    setMessage(null);
    try {
      const params: Record<string, any> = { decision };
      if (form.comments.trim()) params.comments = form.comments.trim();
      if (mode === 'APPROVE') {
        params.approved_amount = form.approved_amount;
        // 화면은 %, API 는 소수 - 이 변환을 빠뜨리면 서버가 422 로 막는다
        params.approved_rate = form.approved_rate / 100;
        params.approved_tenor = form.approved_tenor;
        if (form.conditions.length) {
          params.conditions_json = JSON.stringify(form.conditions.map(code => ({ code })));
        }
      }
      const r = await axios.post(`/api/applications/${id}/approve`, null, { params });
      const n = r.data?.conditions?.length || 0;
      setMessage({
        kind: 'ok',
        text: decision === 'REJECT'
          ? `${id} 반려 완료 - 감사 추적에 기록되었습니다`
          : `${id} ${decision === 'CONDITIONAL' ? `조건부승인 완료 - 승인조건 ${n}건 부여, 상위 결재자의 최종승인 대기` : '승인 완료'} (감사 추적 기록)`,
      });
      setTarget(null);
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
            {me.name} {me.title} - 전결 한도{' '}
            {data?.my_limit ? formatAmount(data.my_limit, 'billion') : '무제한'} ·
            결재 가능 {formatNumber(data?.actionable || 0)}건 / 전체 {formatNumber(data?.items?.length || 0)}건
          </p>
          <RouterLink to="/credit-cases" className="inline-block mt-1 text-xs text-blue-600 hover:underline">📁 전자 여신철 조회 →</RouterLink>
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
                <td className="py-2.5 pr-4">
                  {it.customer_name}
                  <Link to={`/credit-case/${it.application_id}`}
                        className="ml-2 text-[11px] text-blue-600 hover:underline">여신철</Link>
                </td>
                <td className="py-2.5 pr-4">{it.credit_grade || '-'}</td>
                <td className="py-2.5 pr-4 text-right tabular font-medium">
                  {formatAmount(it.requested_amount, 'billion')}
                </td>
                <td className="py-2.5 pr-4">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    it.can_approve ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                    {it.required_name}
                  </span>
                  {it.status === 'CONDITIONAL' && (
                    <span className="ml-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                      조건부 · 최종결재 대기
                    </span>
                  )}
                </td>
                <td className="py-2.5 text-right whitespace-nowrap">
                  {it.can_approve ? (
                    <>
                      <button
                        disabled={busy === it.application_id}
                        onClick={() => openDecision(it, 'APPROVE')}
                        className="px-3 py-1 text-xs font-semibold bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                      >승인</button>
                      <button
                        disabled={busy === it.application_id}
                        onClick={() => openDecision(it, 'REJECT')}
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

      <Modal
        isOpen={!!target}
        onClose={() => setTarget(null)}
        size="lg"
        title={mode === 'REJECT' ? '반려 처리' : '결재 - 승인조건 확정'}
      >
        {target && (
          <div className="space-y-4">
            <div className="rounded-lg bg-gray-50 px-4 py-3 text-sm">
              <p className="font-medium text-gray-900">
                {target.customer_name} · {target.application_id}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">
                신청금액 {formatAmount(target.requested_amount, 'billion')} ·
                등급 {target.credit_grade || '-'} · 필요 전결 {target.required_name}
              </p>
            </div>

            {mode === 'APPROVE' && (
              <>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">승인금액 (원)</label>
                    <input
                      type="text"
                      value={formatInputAmount(form.approved_amount)}
                      onChange={e => setForm({ ...form, approved_amount: parseFormattedNumber(e.target.value) })}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">승인금리 (%)</label>
                    <input
                      type="number" step="0.01"
                      value={form.approved_rate}
                      onChange={e => setForm({ ...form, approved_rate: Number(e.target.value) })}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">승인기간 (개월)</label>
                    <input
                      type="number"
                      value={form.approved_tenor}
                      onChange={e => setForm({ ...form, approved_tenor: Number(e.target.value) })}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                    />
                  </div>
                </div>
                {loadingDefaults && (
                  <p className="text-xs text-gray-400">심사 결과에서 기본값을 불러오는 중...</p>
                )}

                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1.5">
                    승인조건 — 선택 시 조건부승인으로 처리됩니다
                  </label>
                  <div className="border border-gray-200 rounded-lg divide-y divide-gray-100 max-h-56 overflow-y-auto">
                    {(['CP', 'CS'] as const).map(type => (
                      <div key={type} className="p-2">
                        <p className="text-[11px] font-semibold text-gray-400 px-1 mb-1">
                          {type === 'CP' ? '선행조건 — 실행 전 충족' : '후속조건 — 실행 후 이행'}
                        </p>
                        {templates.filter(t => t.type === type).map(t => (
                          <label key={t.code}
                                 className="flex items-center gap-2 px-1 py-1 text-sm cursor-pointer rounded hover:bg-gray-50">
                            <input
                              type="checkbox"
                              checked={form.conditions.includes(t.code)}
                              onChange={() => toggleCondition(t.code)}
                            />
                            <span className="text-gray-700">{t.label}</span>
                            <span className="text-[11px] text-gray-400">
                              {t.code}{t.due_days ? ` · ${t.due_days}일 내` : ''}
                            </span>
                          </label>
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}

            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                {mode === 'REJECT' ? '반려 사유' : '결재 의견'}
              </label>
              <textarea
                rows={2}
                value={form.comments}
                onChange={e => setForm({ ...form, comments: e.target.value })}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
              />
            </div>

            <div className="flex items-center justify-between pt-1">
              <p className="text-xs text-gray-500">
                결재 유형{' '}
                <span className="font-semibold text-gray-700">
                  {decision === 'CONDITIONAL' ? `조건부승인 (조건 ${form.conditions.length}건)`
                    : decision === 'REJECT' ? '반려' : '승인'}
                </span>
                {' · '}결재자 {me.name} {me.title}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setTarget(null)}
                  className="px-4 py-2 text-sm border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50"
                >취소</button>
                <button
                  disabled={busy === target.application_id}
                  onClick={submitDecision}
                  className={`px-4 py-2 text-sm font-semibold text-white rounded-lg disabled:opacity-50 ${
                    mode === 'REJECT' ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'}`}
                >{busy === target.application_id ? '처리 중...' : '결재 확정'}</button>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
