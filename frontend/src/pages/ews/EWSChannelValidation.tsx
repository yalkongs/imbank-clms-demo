import React, { useEffect, useState } from 'react';
import { FlaskConical, Scale, ShieldCheck } from 'lucide-react';
import { Card, Badge } from '../../components';
import { formatPercent } from '../../utils/format';
import axios from 'axios';

/**
 * EWS 채널 선행성 검증 (8채널 확장 Phase 3)
 * "가중치는 주장이 아니라 백테스트로 정한다" - 채널별 리드타임·탐지율·
 * 오경보율을 실측하고, 가중치 재조정은 부서장 이상 승인으로만 발효된다.
 */

const SEGMENTS = [
  { key: 'SOHO', label: '개인사업자' },
  { key: 'UNLISTED', label: '비상장' },
  { key: 'LISTED', label: '상장' },
];

const CH_LABEL: Record<string, string> = {
  card_sales: '카드매출', employment: '고용', b2b_delinq: '상거래연체',
  transaction: '거래행태', public: '공적정보', market: '시장신호',
  news: '뉴스감성', supply: '공급망', financial: '재무',
};

export default function EWSChannelValidation() {
  const [val, setVal] = useState<any>(null);
  const [prop, setProp] = useState<any>(null);
  const [seg, setSeg] = useState('SOHO');
  const [reason, setReason] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = () => Promise.all([
    axios.get('/api/ews-advanced/channel-validation'),
    axios.get('/api/ews-advanced/weight-proposal'),
  ]).then(([v, p]) => { setVal(v.data); setProp(p.data); });

  useEffect(() => { load().catch(console.error).finally(() => setLoading(false)); }, []);

  const approve = () => {
    if (reason.trim().length < 5) {
      setMsg('승인 사유를 5자 이상 입력하세요');
      return;
    }
    setBusy(true);
    setMsg(null);
    axios.post('/api/ews-advanced/weight-proposal/approve', null, { params: { reason } })
      .then(r => {
        setMsg(`발효 완료: ${r.data.version} (${r.data.approved_by}) - ${r.data.recomputed_customers}사 종합점수 재계산·감사기록`);
        setReason('');
        return load();
      })
      .catch(e => setMsg(e?.response?.data?.detail || '발효 실패 - 부서장 이상 로그인이 필요합니다'))
      .finally(() => setBusy(false));
  };

  if (loading || !val || !prop) {
    return <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
    </div>;
  }

  const cur = prop.current[seg] || {};
  const pr = prop.proposal[seg] || {};

  return (
    <div className="space-y-6">
      <Card title="채널 선행성 백테스트" subtitle={`${val.methodology.events} · 오경보: ${val.methodology.false_alarm}`} noPadding>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                <th className="py-2 px-4">채널</th>
                <th className="py-2 px-3 text-right">이벤트 표본</th>
                <th className="py-2 px-3 text-right">탐지율</th>
                <th className="py-2 px-3 text-right">리드타임 (중앙값)</th>
                <th className="py-2 px-3 text-right">3개월+ 선행</th>
                <th className="py-2 px-3 text-right">6개월+ 선행</th>
                <th className="py-2 px-4 text-right">오경보율</th>
              </tr>
            </thead>
            <tbody>
              {val.channels.map((c: any) => (
                <tr key={c.channel} className="border-b border-gray-50">
                  <td className="py-2 px-4 font-medium text-gray-900">
                    {c.label}
                    {['card_sales', 'employment', 'b2b_delinq'].includes(c.channel) &&
                      <Badge variant="info">신규</Badge>}
                  </td>
                  <td className="py-2 px-3 text-right tabular">{c.n_events}사</td>
                  <td className={`py-2 px-3 text-right tabular font-semibold ${c.detection_rate >= 70 ? 'text-green-600' : c.detection_rate >= 25 ? 'text-amber-600' : 'text-gray-500'}`}>
                    {formatPercent(c.detection_rate, 1)}
                  </td>
                  <td className="py-2 px-3 text-right tabular font-semibold">
                    {c.median_lead_months != null ? `${c.median_lead_months}개월 전` : '-'}
                  </td>
                  <td className="py-2 px-3 text-right tabular">{formatPercent(c.pct_before_3m ?? 0, 0)}</td>
                  <td className="py-2 px-3 text-right tabular">{formatPercent(c.pct_before_6m ?? 0, 0)}</td>
                  <td className={`py-2 px-4 text-right tabular ${(c.false_alarm_rate ?? 0) > 25 ? 'text-red-500 font-semibold' : 'text-gray-700'}`}>
                    {formatPercent(c.false_alarm_rate ?? 0, 1)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="px-4 py-3 text-[11px] text-gray-400">
          {val.methodology.window} · 탐지율과 오경보율은 반드시 쌍으로 본다 - 뉴스감성처럼
          오경보가 높은 채널은 리드타임이 좋아도 가중치를 낮게 가져간다.
        </p>
      </Card>

      <div className="grid grid-cols-3 gap-6">
        <Card title="가중치: 현행 vs 백테스트 제안" className="col-span-2"
          subtitle={`${prop.bound_note} · 현행 ${prop.current_version?.version || ''}`} noPadding>
          <div className="px-4 pt-3 flex gap-2">
            {SEGMENTS.map(s => (
              <button key={s.key} onClick={() => setSeg(s.key)}
                className={`px-3 py-1 text-xs rounded-full border font-medium ${
                  seg === s.key ? 'bg-[#00897B] text-white border-[#00897B]' : 'border-gray-300 text-gray-600'}`}>
                {s.label}
              </button>
            ))}
          </div>
          <div className="overflow-x-auto mt-2">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                  <th className="py-2 px-4">채널</th>
                  <th className="py-2 px-3 text-right">현행</th>
                  <th className="py-2 px-3 text-right">제안</th>
                  <th className="py-2 px-4 text-right">변화</th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(cur).filter(ch => (cur[ch] || 0) > 0 || (pr[ch] || 0) > 0).map(ch => {
                  const d = ((pr[ch] || 0) - (cur[ch] || 0)) * 100;
                  return (
                    <tr key={ch} className="border-b border-gray-50">
                      <td className="py-1.5 px-4 font-medium text-gray-900">{CH_LABEL[ch] || ch}</td>
                      <td className="py-1.5 px-3 text-right tabular">{((cur[ch] || 0) * 100).toFixed(1)}%</td>
                      <td className="py-1.5 px-3 text-right tabular font-semibold">{((pr[ch] || 0) * 100).toFixed(1)}%</td>
                      <td className={`py-1.5 px-4 text-right tabular font-semibold ${d > 0.05 ? 'text-green-600' : d < -0.05 ? 'text-red-500' : 'text-gray-400'}`}>
                        {d > 0 ? '+' : ''}{d.toFixed(1)}%p
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="가중치 발효 (거버넌스)">
          <div className="space-y-3">
            <p className="text-xs text-gray-500 leading-relaxed flex items-start gap-1.5">
              <Scale size={14} className="mt-0.5 flex-none text-[#00897B]" />
              {prop.governance}
            </p>
            <input value={reason} onChange={e => setReason(e.target.value)}
              placeholder="승인 사유 (필수, 5자 이상)"
              className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg" />
            <button onClick={approve} disabled={busy}
              className="w-full py-2 text-sm font-semibold bg-[#00897B] text-white rounded-lg hover:bg-[#00695F] disabled:opacity-50">
              제안 가중치 발효 (부서장 이상)
            </button>
            {msg && <p className="text-xs font-medium text-[#00695F]">{msg}</p>}
            <p className="text-[11px] text-gray-400 leading-relaxed flex items-start gap-1.5">
              <ShieldCheck size={13} className="mt-0.5 flex-none" />
              발효 시 rule_register 에 새 버전이 생기고(이전 버전 자동 마감),
              전 고객 종합점수가 정본 산식으로 재계산되며, 감사기록이 남습니다.
              모형 가중치가 조용히 바뀌는 일은 없습니다.
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}
