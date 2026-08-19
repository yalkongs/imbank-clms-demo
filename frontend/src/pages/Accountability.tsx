import React, { useEffect, useState } from 'react';
import { ClipboardCheck, ShieldCheck, AlertTriangle, FileSearch } from 'lucide-react';
import { Card, StatCard, Badge } from '../components';
import { formatNumber } from '../utils/format';
import axios from 'axios';

/**
 * 책무구조도 통제증거 체인 (P5)
 *
 * 지배구조법 개정으로 임원에게 내부통제 관리의무가 부과됐고 책무구조도는
 * 2025.1 제출 완료 - 실무 쟁점은 "관리의무를 수행했다는 증거"다.
 * 이 화면은 여신 책무에 CLMS 통제활동을 매핑하고, 수행 증거(감사기록)를
 * 실측 집계한다. 수기 보고가 아니라 audit_log 가 곧 증거다.
 */

const STATUS_META: Record<string, { label: string; variant: 'success' | 'warning' | 'danger' }> = {
  EVIDENCED: { label: '증거 충족', variant: 'success' },
  GAP: { label: '증거 공백', variant: 'danger' },
  IDLE: { label: '활동 없음', variant: 'warning' },
};

export default function Accountability() {
  const [reg, setReg] = useState<any>(null);
  const [report, setReport] = useState<any>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      axios.get('/api/accountability/register'),
      axios.get('/api/accountability/report'),
    ])
      .then(([r, rp]) => { setReg(r.data); setReport(rp.data); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selected) { setEvidence(null); return; }
    axios.get(`/api/accountability/evidence/${selected}`)
      .then(r => setEvidence(r.data))
      .catch(console.error);
  }, [selected]);

  if (loading || !reg) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const s = reg.summary;
  const ctx = reg.regulatory_context;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">책무구조도 통제증거</h1>
          <p className="text-sm text-gray-500 mt-1">
            여신 책무 ↔ CLMS 통제활동 매핑 · 관리의무 수행 증거를 감사기록에서 실측 집계
          </p>
        </div>
        <span className="px-2.5 py-1 bg-amber-50 text-amber-700 text-xs rounded-full font-medium border border-amber-200">
          {ctx.risk}
        </span>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="여신 책무 항목"
          value={`${s.total}건`}
          subtitle={ctx.law}
          icon={<ClipboardCheck size={24} />}
          color="blue"
        />
        <StatCard
          title="증거 충족"
          value={`${s.EVIDENCED} / ${s.total}`}
          subtitle={`충족률 ${s.evidence_rate}% (감사기록 실측)`}
          icon={<ShieldCheck size={24} />}
          color="green"
        />
        <StatCard
          title="증거 공백"
          value={`${s.GAP}건`}
          subtitle="통제는 돌지만 감사기록이 연결 안 된 상태"
          icon={<AlertTriangle size={24} />}
          color={s.GAP > 0 ? 'red' : 'green'}
        />
        <StatCard
          title="증거 원장"
          value="audit_log"
          subtitle="수기 보고 아님 - 시스템 기록이 곧 증거"
          icon={<FileSearch size={24} />}
          color="gray"
        />
      </div>

      <div className="grid grid-cols-3 gap-6">
        <Card title="책무 레지스터" className="col-span-2"
          subtitle="행을 클릭하면 해당 책무의 증거 원장(감사기록)을 표시" noPadding>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                  <th className="py-2 px-4">책무</th>
                  <th className="py-2 px-3">책임자</th>
                  <th className="py-2 px-3 text-right">감사기록</th>
                  <th className="py-2 px-3 text-right">원천 활동</th>
                  <th className="py-2 px-3">최근 증거</th>
                  <th className="py-2 px-4 text-center">상태</th>
                </tr>
              </thead>
              <tbody>
                {reg.duties.map((d: any) => {
                  const meta = STATUS_META[d.evidence.status];
                  return (
                    <tr key={d.duty_id}
                      onClick={() => setSelected(selected === d.duty_id ? null : d.duty_id)}
                      className={`border-b border-gray-50 cursor-pointer hover:bg-gray-50 ${selected === d.duty_id ? 'bg-[#00BFA5]/5' : ''}`}>
                      <td className="py-2.5 px-4">
                        <p className="font-medium text-gray-900">{d.duty_id} · {d.title}</p>
                        <p className="text-[11px] text-gray-400 mt-0.5">{d.controls.length}개 통제활동 매핑</p>
                      </td>
                      <td className="py-2 px-3 text-gray-600 text-xs">{d.owner}<br />{d.owner_role}</td>
                      <td className="py-2 px-3 text-right tabular font-semibold">{d.evidence.audit_count}</td>
                      <td className="py-2 px-3 text-right tabular text-gray-500">
                        {formatNumber(d.evidence.activity_count)}
                        <span className="text-[10px] text-gray-400 ml-1">{d.evidence.activity_label}</span>
                      </td>
                      <td className="py-2 px-3 text-xs text-gray-500">{d.evidence.last_audit?.slice(0, 10) || '-'}</td>
                      <td className="py-2 px-4 text-center">
                        <Badge variant={meta.variant}>{meta.label}</Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>

        <div className="space-y-6">
          {/* 임원별 점검 리포트 */}
          <Card title="관리의무 점검 리포트" subtitle={report?.note}>
            <div className="space-y-3">
              {(report?.report || []).map((o: any) => (
                <div key={o.owner} className="p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-gray-900">{o.owner} <span className="text-xs text-gray-400 font-normal">{o.owner_role}</span></p>
                    <span className={`text-sm font-bold tabular ${o.evidence_rate >= 100 ? 'text-green-600' : 'text-amber-600'}`}>
                      {o.evidence_rate}%
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    담당 책무 {o.duties}건 · 증거 {o.audit_total}건 - {o.conclusion}
                  </p>
                  {o.gaps.length > 0 && (
                    <p className="text-[11px] text-red-500 mt-1">공백: {o.gaps.join(', ')}</p>
                  )}
                </div>
              ))}
            </div>
          </Card>

          {/* 선택된 책무 상세 */}
          {selected && evidence && (
            <Card title={`증거 원장 - ${evidence.duty_id}`} subtitle={evidence.title}>
              {evidence.entries.length === 0 ? (
                <p className="text-sm text-gray-400 py-4 text-center">
                  감사기록 없음 - 이 책무의 통제활동에 record_audit 연결이 필요합니다
                </p>
              ) : (
                <div className="space-y-2 max-h-72 overflow-y-auto">
                  {evidence.entries.map((e: any, i: number) => (
                    <div key={i} className="text-xs border-l-2 border-[#00BFA5] pl-2.5 py-0.5">
                      <p className="font-medium text-gray-900">{e.action} <span className="text-gray-400">· {e.target}</span></p>
                      <p className="text-gray-500">{e.timestamp?.slice(0, 16)} · {e.user} ({e.dept})</p>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}
        </div>
      </div>

      {/* 선택된 책무의 통제활동 상세 */}
      {selected && (
        <Card title="매핑된 통제활동">
          <div className="grid grid-cols-2 gap-2">
            {(reg.duties.find((d: any) => d.duty_id === selected)?.controls || []).map((c: string, i: number) => (
              <div key={i} className="flex items-start gap-2 text-sm text-gray-700 p-2 bg-gray-50 rounded-lg">
                <ShieldCheck size={15} className="text-[#00897B] mt-0.5 flex-none" />
                {c}
              </div>
            ))}
          </div>
        </Card>
      )}

      <p className="text-xs text-gray-400">
        {ctx.im_context} · 캄보디아 제재("기준은 있었으나 지켜지지 않았다")와 배임 장기
        미적발이 보여주듯, 관리의무의 실무 쟁점은 통제의 존재가 아니라 수행 증거다.
      </p>
    </div>
  );
}
