import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { ClipboardCheck, Clock, ArrowUpRight, CheckCircle2 } from 'lucide-react';
import { Card, StatCard } from '../../components';

/**
 * EWS 조치 관리 - 경보를 '점수'가 아니라 '조치 의무'로 관리한다.
 * 경보마다 Playbook 단계·담당·기한이 붙고, 기한초과는 자동 상향보고 표시.
 */

export default function EWSActionCenter() {
  const [summary, setSummary] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [target, setTarget] = useState<any>(null);
  const [taken, setTaken] = useState('');
  const [busy, setBusy] = useState(false);

  const load = () => {
    Promise.all([
      axios.get('/api/ews-actions/summary'),
      axios.get('/api/ews-actions'),
    ]).then(([s, a]) => {
      setSummary(s.data);
      setAlerts(a.data.alerts || []);
    }).catch(console.error).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const complete = async () => {
    if (!target) return;
    setBusy(true);
    try {
      await axios.post(`/api/ews-actions/${target.action_id}/complete`, { action_taken: taken });
      setTarget(null); setTaken('');
      load();
    } catch (e: any) {
      alert(e?.response?.data?.detail || '처리 실패');
    } finally { setBusy(false); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" /></div>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-4">
        <StatCard title="조치 항목" value={summary?.total || 0}
          subtitle={`완료율 ${summary?.completion_rate || 0}%`}
          icon={<ClipboardCheck size={22} />} color="blue" />
        <StatCard title="미결 조치" value={summary?.open || 0}
          icon={<Clock size={22} />} color="yellow" />
        <StatCard title="기한 초과" value={summary?.overdue || 0}
          subtitle="즉시 처리 필요" icon={<Clock size={22} />} color="red" />
        <StatCard title="자동 상향보고" value={summary?.escalated || 0}
          subtitle="부서장 보고됨" icon={<ArrowUpRight size={22} />} color="red" />
      </div>

      <div className="space-y-4">
        {alerts.map(a => {
          const openSteps = a.actions.filter((x: any) => x.status !== 'DONE').length;
          return (
            <Card key={a.alert_id}
              title={a.description || `${a.customer_name || a.customer_id} - ${a.alert_type}`}
              subtitle={`경보일 ${a.alert_date} · 중대도 ${a.severity || '-'}`}
              headerAction={openSteps === 0
                ? <span className="flex items-center gap-1 text-xs text-green-600 font-semibold"><CheckCircle2 size={13} /> 조치 완결</span>
                : <span className="text-xs text-amber-600 font-semibold">미결 {openSteps}단계</span>}>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                    <th className="py-1.5 w-8">#</th>
                    <th className="py-1.5">Playbook 단계</th>
                    <th className="py-1.5">담당</th>
                    <th className="py-1.5 text-center">기한</th>
                    <th className="py-1.5 text-center">상태</th>
                    <th className="py-1.5">조치 내용</th>
                    <th className="py-1.5 text-center">처리</th>
                  </tr>
                </thead>
                <tbody>
                  {a.actions.map((x: any) => (
                    <tr key={x.action_id} className="border-b border-gray-50">
                      <td className="py-2 text-xs text-gray-400">{x.step_no}</td>
                      <td className="py-2 font-medium">{x.step}</td>
                      <td className="py-2 text-xs text-gray-500">{x.owner}</td>
                      <td className="py-2 text-center text-xs">
                        <span className={x.overdue ? 'text-red-600 font-bold' : 'text-gray-500'}>{x.due_date}</span>
                        {x.escalated && (
                          <span className="ml-1 px-1.5 py-0.5 bg-red-600 text-white rounded text-[10px] font-bold">상향보고</span>
                        )}
                      </td>
                      <td className="py-2 text-center">
                        <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                          x.status === 'DONE' ? 'bg-green-100 text-green-700' :
                          x.status === 'IN_PROGRESS' ? 'bg-blue-100 text-blue-700' :
                          x.overdue ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-500'
                        }`}>
                          {x.status === 'DONE' ? '완료' : x.status === 'IN_PROGRESS' ? '진행중' : '대기'}
                        </span>
                      </td>
                      <td className="py-2 text-xs text-gray-600 max-w-xs truncate">
                        {x.action_taken || '-'}
                        {x.completed_at && <span className="text-gray-400"> ({x.completed_at})</span>}
                      </td>
                      <td className="py-2 text-center">
                        {x.status !== 'DONE' && (
                          <button onClick={() => { setTarget(x); setTaken(''); }}
                            className="px-2.5 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700">
                            완료 처리
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          );
        })}
      </div>

      {/* 완료 처리 모달 */}
      {target && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="modal-in w-full max-w-md bg-white rounded-2xl shadow-2xl p-6">
            <h3 className="text-base font-bold text-gray-900 mb-1">조치 완료 처리</h3>
            <p className="text-xs text-gray-500 mb-4">{target.step} (담당 {target.owner} · 기한 {target.due_date})</p>
            <label className="block text-sm">
              <span className="text-gray-500 text-xs">조치 내용 (근거 필수 - 감사 기록에 남습니다)</span>
              <textarea value={taken} onChange={e => setTaken(e.target.value)} rows={3}
                placeholder="예: 고객 면담 실시 - 한도소진 원인은 계절성 재고 매입으로 확인, 3개월 후 재점검"
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm" />
            </label>
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={() => setTarget(null)}
                className="px-4 py-2 text-sm border border-gray-300 rounded-lg">취소</button>
              <button onClick={complete} disabled={busy || taken.trim().length < 5}
                className="btn-accent px-5 text-sm disabled:opacity-50">
                {busy ? '처리 중...' : '완료 기록'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
