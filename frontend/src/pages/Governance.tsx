import React, { useEffect, useState } from 'react';
import { Printer, ShieldCheck, ScrollText, Stamp } from 'lucide-react';
import { Card } from '../components';
import { formatAmount, formatPercent, formatNumber } from '../utils/format';
import axios from 'axios';

/**
 * 보고·감사 — 업무보고서 · 전결 규정 · 감사 추적
 *
 * 내부통제의 실효성을 화면으로 증빙한다. 업무보고서는 감독당국 보고 서식에
 * 준하는 집계이고, 전결 규정은 승인 API 가 실제 검증에 쓰는 정본이며,
 * 감사 추적은 모든 의미 있는 쓰기 작업의 이력이다.
 */


/** 감사 기록의 before/after JSON 을 사람이 읽는 형태로 변환한다.
 *  원문 {"status": "APPROVED", ...} 노출은 감사 화면의 목적(증빙 가독성)에 어긋난다. */
const AUDIT_FIELD_LABELS: Record<string, string> = {
  status: '상태', approved_amount: '승인금액', approval_level: '전결',
  inserted: '신규', updated: '갱신', stage: 'Stage', ecl_final: 'ECL',
  instrument: '상품', notional: '명목금액',
};
const AUDIT_VALUE_LABELS: Record<string, string> = {
  APPROVED: '승인', REJECTED: '반려', CONDITIONAL: '조건부승인',
  STAFF: '담당자', TEAM_LEAD: '팀장', DEPT_HEAD: '부서장',
  EXECUTIVE: '임원', COMMITTEE: '여신위원회',
};

function formatAuditValue(key: string, v: any): string {
  if (v === null || v === undefined) return '';
  if (typeof v === 'number' && ['approved_amount', 'ecl_final', 'notional'].includes(key)) {
    return `${(v / 1e8).toLocaleString('ko-KR', { maximumFractionDigits: 1 })}억`;
  }
  if (typeof v === 'number') return v.toLocaleString('ko-KR');
  return AUDIT_VALUE_LABELS[String(v)] || String(v);
}

function AuditChange({ raw }: { raw: string | null }) {
  if (!raw) return <span className="text-gray-300">—</span>;
  let obj: Record<string, any>;
  try { obj = JSON.parse(raw); } catch { return <span>{raw}</span>; }
  const entries = Object.entries(obj).filter(([, v]) => v !== null && v !== undefined && v !== '');
  if (entries.length === 0) return <span className="text-gray-300">—</span>;
  return (
    <span className="flex flex-wrap gap-1">
      {entries.map(([k, v]) => (
        <span key={k} className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-gray-100 rounded text-[11px]">
          <span className="text-gray-400">{AUDIT_FIELD_LABELS[k] || k}</span>
          <span className="font-medium text-gray-700">{formatAuditValue(k, v)}</span>
        </span>
      ))}
    </span>
  );
}

export default function Governance() {
  const [report, setReport] = useState<any>(null);
  const [authority, setAuthority] = useState<any[]>([]);
  const [audit, setAudit] = useState<any>(null);
  const [tab, setTab] = useState<'report' | 'authority' | 'audit'>('report');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      axios.get('/api/governance/report'),
      axios.get('/api/governance/approval-authority'),
      axios.get('/api/governance/audit-logs?limit=50'),
    ])
      .then(([r, a, l]) => {
        setReport(r.data);
        setAuthority(a.data);
        setAudit(l.data);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const s = report?.sections || {};

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">보고·감사</h1>
          <p className="text-sm text-gray-500 mt-1">
            업무보고서 · 전결 규정 · 감사 추적 — 내부통제 증빙
          </p>
        </div>
        {tab === 'report' && (
          <button
            onClick={() => window.print()}
            className="flex items-center gap-2 px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <Printer size={16} /> 인쇄
          </button>
        )}
      </div>

      <div className="flex gap-1 border-b border-gray-200" role="tablist">
        {([
          ['report', '업무보고서', <ScrollText key="r" size={15} />],
          ['authority', '전결 규정', <Stamp key="a" size={15} />],
          ['audit', '감사 추적', <ShieldCheck key="u" size={15} />],
        ] as const).map(([k, l, icon]) => (
          <button
            key={k}
            role="tab"
            aria-selected={tab === k}
            onClick={() => setTab(k)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === k
                ? 'border-blue-600 text-blue-700'
                : 'border-transparent text-gray-500 hover:text-gray-800'
            }`}
          >
            {icon} {l}
          </button>
        ))}
      </div>

      {tab === 'report' && report && (
        <div className="space-y-6 print:text-black">
          <div className="text-center py-4 border-b-2 border-gray-800">
            <h2 className="text-xl font-bold">{report.report_title}</h2>
            <p className="text-sm text-gray-500 mt-1">{report.period} · 기준일 {report.base_date}</p>
          </div>

          {/* 1. 자산건전성 */}
          <Card title={s.classification?.title}>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                  <th className="py-2">분류</th>
                  <th className="py-2 text-right">건수</th>
                  <th className="py-2 text-right">잔액</th>
                  <th className="py-2 text-right">비중</th>
                  <th className="py-2 text-right">필요충당금</th>
                </tr>
              </thead>
              <tbody>
                {s.classification?.rows?.map((r: any) => (
                  <tr key={r.grade} className="border-b border-gray-50">
                    <td className="py-2 font-medium">{r.grade}</td>
                    <td className="py-2 text-right tabular">{formatNumber(r.count)}</td>
                    <td className="py-2 text-right tabular">{formatAmount(r.exposure, 'billion')}</td>
                    <td className="py-2 text-right tabular">{formatPercent(r.share)}</td>
                    <td className="py-2 text-right tabular">{formatAmount(r.required_provision, 'billion')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-sm mt-3 font-medium">
              고정이하여신비율(NPL) <span className="tabular">{formatPercent(s.classification?.npl_ratio || 0)}</span>
            </p>
          </Card>

          <div className="grid grid-cols-2 gap-6">
            {/* 2. 연체 */}
            <Card title={s.delinquency?.title}>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between"><dt className="text-gray-500">1개월 이상 연체</dt>
                  <dd className="tabular font-medium">{formatAmount(s.delinquency?.delinquent_1m || 0, 'billion')}</dd></div>
                <div className="flex justify-between"><dt className="text-gray-500">3개월 이상 연체</dt>
                  <dd className="tabular font-medium">{formatAmount(s.delinquency?.delinquent_3m || 0, 'billion')}</dd></div>
                <div className="flex justify-between"><dt className="text-gray-500">연체율</dt>
                  <dd className="tabular font-bold">{formatPercent(s.delinquency?.delinquency_rate || 0)}</dd></div>
              </dl>
            </Card>

            {/* 3. 충당금 */}
            <Card title={s.provision?.title}>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between"><dt className="text-gray-500">감독규정 최저적립액</dt>
                  <dd className="tabular font-medium">{formatAmount(s.provision?.regulatory_minimum || 0, 'billion')}</dd></div>
                <div className="flex justify-between"><dt className="text-gray-500">IFRS9 ECL</dt>
                  <dd className="tabular font-medium">{formatAmount(s.provision?.ifrs9_ecl || 0, 'billion')}</dd></div>
                <div className="flex justify-between"><dt className="text-gray-500">대손준비금 적립 대상</dt>
                  <dd className="tabular font-bold">{formatAmount(s.provision?.loan_loss_reserve || 0, 'billion')}</dd></div>
              </dl>
              <p className="text-xs text-gray-400 mt-3">{s.provision?.note}</p>
            </Card>
          </div>

          {/* 4. 자본 */}
          <Card title={s.capital?.title}>
            <div className="grid grid-cols-4 gap-4 text-center">
              {[
                ['BIS 비율', s.capital?.bis_ratio],
                ['Tier1 비율', s.capital?.tier1_ratio],
                ['CET1 비율', s.capital?.cet1_ratio],
                ['레버리지 비율', s.capital?.leverage_ratio],
              ].map(([l, v]) => (
                <div key={l as string}>
                  <p className="text-2xl font-bold tabular">{formatPercent((v as number) || 0)}</p>
                  <p className="text-xs text-gray-500 mt-1">{l}</p>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-4 text-center">
              총자본 {formatAmount(s.capital?.total_capital || 0, 'billion')} · 총RWA {formatAmount(s.capital?.total_rwa || 0, 'billion')}
            </p>
          </Card>
        </div>
      )}

      {tab === 'authority' && (
        <Card title="여신 전결 규정 (승인 API 검증 기준)">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                <th className="py-2">전결 구분</th>
                <th className="py-2 text-right">전결 한도</th>
                <th className="py-2 text-right">시행일</th>
              </tr>
            </thead>
            <tbody>
              {authority.map(a => (
                <tr key={a.level} className="border-b border-gray-50">
                  <td className="py-2.5 font-medium">{a.name}</td>
                  <td className="py-2.5 text-right tabular">{a.limit_label}</td>
                  <td className="py-2.5 text-right text-gray-500">{a.effective_from}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-xs text-gray-400 mt-3">
            승인 처리 시 승인 금액이 결재자 전결 한도를 초과하면 시스템이 차단합니다.
          </p>
        </Card>
      )}

      {tab === 'audit' && (
        <Card title={`감사 추적 (총 ${formatNumber(audit?.total || 0)}건 · 최근 50건)`}>
          {(audit?.logs || []).length === 0 ? (
            <p className="py-8 text-sm text-gray-400 text-center">
              아직 기록이 없습니다 — 승인·분류실행·ECL 재산출 등 쓰기 작업이 수행되면 기록됩니다.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                    <th className="py-2 pr-4">시각</th>
                    <th className="py-2 pr-4">사용자</th>
                    <th className="py-2 pr-4">작업</th>
                    <th className="py-2 pr-4">대상</th>
                    <th className="py-2">변경 내용</th>
                  </tr>
                </thead>
                <tbody>
                  {audit.logs.map((l: any) => (
                    <tr key={l.log_id} className="border-b border-gray-50 align-top">
                      <td className="py-2 pr-4 text-xs text-gray-500 whitespace-nowrap">{l.timestamp}</td>
                      <td className="py-2 pr-4">{l.user_id}<p className="text-xs text-gray-400">{l.user_dept}</p></td>
                      <td className="py-2 pr-4">
                        <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs font-medium">{l.action_type}</span>
                      </td>
                      <td className="py-2 pr-4 text-xs">{l.target_entity}<p className="text-gray-400">{l.target_id}</p></td>
                      <td className="py-2 text-xs text-gray-600 max-w-md">
                        {l.before && <div className="mb-1 opacity-60"><span className="text-gray-400 mr-1">이전</span><AuditChange raw={l.before} /></div>}
                        <AuditChange raw={l.after} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
