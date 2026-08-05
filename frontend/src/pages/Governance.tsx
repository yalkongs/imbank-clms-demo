import React, { useEffect, useState } from 'react';
import { Printer, ShieldCheck, ScrollText, Stamp, FileDown, AlertTriangle } from 'lucide-react';
import { Card } from '../components';
import { formatAmount, formatPercent, formatNumber } from '../utils/format';
import axios from 'axios';

/**
 * 보고·감사 - 업무보고서 · 전결 규정 · 감사 추적
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
  if (!raw) return <span className="text-gray-300">-</span>;
  let obj: Record<string, any>;
  try { obj = JSON.parse(raw); } catch { return <span>{raw}</span>; }
  const entries = Object.entries(obj).filter(([, v]) => v !== null && v !== undefined && v !== '');
  if (entries.length === 0) return <span className="text-gray-300">-</span>;
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
  const [tab, setTab] = useState<'report' | 'authority' | 'audit' | 'exceptions' | 'rules'>('report');
  const [rules, setRules] = useState<any>(null);
  const [exceptions, setExceptions] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      axios.get('/api/governance/report'),
      axios.get('/api/governance/approval-authority'),
      axios.get('/api/governance/audit-logs?limit=50'),
      axios.get('/api/credit-case/exceptions'),
      axios.get('/api/rules'),
    ])
      .then(([r, a, l, ex, ru]) => {
        setReport(r.data);
        setAuthority(a.data);
        setAudit(l.data);
        setExceptions(ex.data);
        setRules(ru.data);
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
            업무보고서 · 전결 규정 · 감사 추적 - 내부통제 증빙
          </p>
        </div>
        {tab === 'report' && (
          <div className="flex items-center gap-2">
            <a
              href="/api/governance/report/pdf"
              className="btn-accent flex items-center gap-2 px-4 py-2 text-sm"
            >
              <FileDown size={16} /> PDF 저장
            </a>
            <button
              onClick={() => window.print()}
              className="flex items-center gap-2 px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <Printer size={16} /> 인쇄
            </button>
          </div>
        )}
      </div>

      <div className="flex gap-1 border-b border-gray-200" role="tablist">
        {([
          ['report', '업무보고서', <ScrollText key="r" size={15} />],
          ['authority', '전결 규정', <Stamp key="a" size={15} />],
          ['audit', '감사 추적', <ShieldCheck key="u" size={15} />],
          ['exceptions', '정책 예외', <AlertTriangle key="e" size={15} />],
          ['rules', '규정 레지스터', <ScrollText key="ru" size={15} />],
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
            <p className="text-xs text-gray-400 text-left">문서번호 {report.doc_no}</p>
            <h2 className="text-xl font-bold">{report.report_title}</h2>
            <p className="text-sm text-gray-500 mt-1">{report.period} · 기준일 {report.base_date}</p>
          </div>

          {/* 총괄 */}
          <Card title="총괄">
            <div className="grid grid-cols-3 lg:grid-cols-6 gap-4 text-center">
              {[
                ['총여신 잔액', formatAmount(s.summary?.total_outstanding || 0, 'billion')],
                ['여신 / 차주', `${formatNumber(s.summary?.facility_count || 0)}건 / ${formatNumber(s.summary?.borrower_count || 0)}개사`],
                ['당년 신규취급', `${formatAmount(s.summary?.new_amount || 0, 'billion')} (${s.summary?.new_count || 0}건)`],
                ['NPL 비율', formatPercent(s.summary?.npl_ratio || 0)],
                ['연체율(30일+)', formatPercent(s.summary?.delinquency_rate || 0, 3)],
                ['BIS 비율', formatPercent(s.summary?.bis_ratio || 0)],
              ].map(([l, v]) => (
                <div key={l as string}>
                  <p className="text-base font-bold tabular leading-tight">{v}</p>
                  <p className="text-[11px] text-gray-500 mt-1">{l}</p>
                </div>
              ))}
            </div>
          </Card>

          {/* 1. 자산건전성 */}
          <Card title={s.classification?.title}>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                  <th className="py-2">분류</th>
                  <th className="py-2 text-right">건수</th>
                  <th className="py-2 text-right">잔액</th>
                  <th className="py-2 text-right">비중</th>
                  <th className="py-2 text-right">증감</th>
                  <th className="py-2 text-right">필요충당금</th>
                </tr>
              </thead>
              <tbody>
                {s.classification?.rows?.map((r: any) => {
                  const adverse = r.grade !== '정상';
                  const worse = adverse ? r.change > 0 : r.change < 0;
                  return (
                    <tr key={r.grade} className="border-b border-gray-50">
                      <td className="py-2 font-medium">{r.grade}</td>
                      <td className="py-2 text-right tabular">{formatNumber(r.count)}</td>
                      <td className="py-2 text-right tabular">{formatAmount(r.exposure, 'billion')}</td>
                      <td className="py-2 text-right tabular">{formatPercent(r.share)}</td>
                      <td className={`py-2 text-right tabular text-xs ${
                        !r.change ? 'text-gray-300' : worse ? 'text-red-600' : 'text-green-600'
                      }`}>
                        {r.change ? `${r.change > 0 ? '+' : ''}${formatAmount(r.change, 'billion')}` : '-'}
                      </td>
                      <td className="py-2 text-right tabular">{formatAmount(r.required_provision, 'billion')}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="text-sm mt-3 font-medium">
              고정이하여신 {formatAmount(s.classification?.npl_exposure || 0, 'billion')} ·
              NPL 비율 <span className="tabular">{formatPercent(s.classification?.npl_ratio || 0)}</span>
              {s.classification?.prev_date && (
                <span className="text-xs text-gray-400 font-normal"> (증감은 직전 분류 {s.classification.prev_date} 대비)</span>
              )}
            </p>
          </Card>

          <div className="grid grid-cols-2 gap-6">
            {/* 2. 연체 */}
            <Card title={s.delinquency?.title}>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                    <th className="py-1.5">연체 구간(DPD)</th>
                    <th className="py-1.5 text-right">건수</th>
                    <th className="py-1.5 text-right">잔액</th>
                  </tr>
                </thead>
                <tbody>
                  {s.delinquency?.buckets?.map((b: any) => (
                    <tr key={b.label} className="border-b border-gray-50">
                      <td className="py-1.5">{b.label}</td>
                      <td className="py-1.5 text-right tabular">{b.count}</td>
                      <td className="py-1.5 text-right tabular">{formatAmount(b.amount, 'billion')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-xs text-gray-500 mt-3">
                연체율 30일+ <b className="tabular">{formatPercent(s.delinquency?.delinquency_rate || 0, 3)}</b> ·
                90일+ <b className="tabular">{formatPercent(s.delinquency?.delinquency_rate_3m || 0, 3)}</b><br />
                워크아웃 이관임박(DPD 75~89) {s.delinquency?.transfer_imminent_count}건 {formatAmount(s.delinquency?.transfer_imminent_amount || 0, 'billion')}
              </p>
            </Card>

            {/* 3. 충당금 */}
            <Card title={s.provision?.title}>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                    <th className="py-1.5">구분</th>
                    <th className="py-1.5 text-right">건수</th>
                    <th className="py-1.5 text-right">EAD</th>
                    <th className="py-1.5 text-right">ECL</th>
                  </tr>
                </thead>
                <tbody>
                  {s.provision?.stages?.map((st: any) => (
                    <tr key={st.stage} className="border-b border-gray-50">
                      <td className="py-1.5">Stage {st.stage}{st.stage === 3 ? ' (신용손상)' : ''}</td>
                      <td className="py-1.5 text-right tabular">{formatNumber(st.count)}</td>
                      <td className="py-1.5 text-right tabular">{formatAmount(st.ead, 'billion')}</td>
                      <td className="py-1.5 text-right tabular">{formatAmount(st.ecl, 'billion')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <dl className="space-y-1.5 text-sm mt-3 pt-3 border-t border-gray-100">
                <div className="flex justify-between"><dt className="text-gray-500">감독규정 최저적립액</dt>
                  <dd className="tabular font-medium">{formatAmount(s.provision?.regulatory_minimum || 0, 'billion')}</dd></div>
                <div className="flex justify-between"><dt className="text-gray-500">IFRS9 ECL</dt>
                  <dd className="tabular font-medium">{formatAmount(s.provision?.ifrs9_ecl || 0, 'billion')}</dd></div>
                <div className="flex justify-between"><dt className="text-gray-500">대손준비금 적립 대상</dt>
                  <dd className="tabular font-bold">{formatAmount(s.provision?.loan_loss_reserve || 0, 'billion')}</dd></div>
                <div className="flex justify-between"><dt className="text-gray-500">NPL 커버리지</dt>
                  <dd className="tabular font-medium">{formatPercent(s.provision?.coverage_ratio || 0, 1)}</dd></div>
              </dl>
            </Card>
          </div>

          {/* 4. 자본 */}
          <Card title={s.capital?.title}>
            <div className="grid grid-cols-4 gap-4 text-center">
              {[
                ['BIS 비율', s.capital?.bis_ratio, s.capital?.bis_change],
                ['Tier1 비율', s.capital?.tier1_ratio, null],
                ['CET1 비율', s.capital?.cet1_ratio, null],
                ['레버리지 비율', s.capital?.leverage_ratio, null],
              ].map(([l, v, chg]) => (
                <div key={l as string}>
                  <p className="text-2xl font-bold tabular">{formatPercent((v as number) || 0)}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {l}
                    {chg !== null && chg !== undefined && (
                      <span className={(chg as number) >= 0 ? 'text-green-600' : 'text-red-600'}>
                        {' '}({(chg as number) >= 0 ? '+' : ''}{(chg as number).toFixed(2)}%p)
                      </span>
                    )}
                  </p>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-4 text-center">
              총자본 {formatAmount(s.capital?.total_capital || 0, 'billion')} · 총RWA {formatAmount(s.capital?.total_rwa || 0, 'billion')}
            </p>
          </Card>

          {/* 5. 포트폴리오 */}
          <Card title={s.portfolio?.title}>
            <p className="text-xs font-semibold text-gray-500 mb-2">업종별 (상위 8개)</p>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                  <th className="py-1.5">업종</th>
                  <th className="py-1.5 text-right">건수</th>
                  <th className="py-1.5 text-right">잔액</th>
                  <th className="py-1.5 text-right">비중</th>
                  <th className="py-1.5 text-right">NPL비율</th>
                </tr>
              </thead>
              <tbody>
                {s.portfolio?.by_industry?.map((r: any) => (
                  <tr key={r.name} className="border-b border-gray-50">
                    <td className="py-1.5">{r.name}</td>
                    <td className="py-1.5 text-right tabular">{formatNumber(r.count)}</td>
                    <td className="py-1.5 text-right tabular">{formatAmount(r.exposure, 'billion')}</td>
                    <td className="py-1.5 text-right tabular">{formatPercent(r.share, 1)}</td>
                    <td className={`py-1.5 text-right tabular ${r.npl_ratio > 1 ? 'text-red-600' : ''}`}>{formatPercent(r.npl_ratio)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="grid grid-cols-2 gap-6 mt-4">
              <div>
                <p className="text-xs font-semibold text-gray-500 mb-2">지역별</p>
                {s.portfolio?.by_region?.map((r: any) => (
                  <div key={r.name} className="flex justify-between text-sm py-1 border-b border-gray-50">
                    <span>{r.name}</span>
                    <span className="tabular text-gray-600">
                      {formatAmount(r.exposure, 'billion')} ({formatPercent(r.share, 1)}) · 연체 {formatPercent(r.delinquency_rate, 3)}
                    </span>
                  </div>
                ))}
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-500 mb-2">기업규모별</p>
                {s.portfolio?.by_size?.map((r: any) => (
                  <div key={r.name} className="flex justify-between text-sm py-1 border-b border-gray-50">
                    <span>{r.name}</span>
                    <span className="tabular text-gray-600">
                      {formatNumber(r.count)}건 · {formatAmount(r.exposure, 'billion')} ({formatPercent(r.share, 1)})
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </Card>

          <div className="grid grid-cols-2 gap-6">
            {/* 6. PF */}
            <Card title={s.pf?.title}>
              <dl className="space-y-1.5 text-sm">
                <div className="flex justify-between"><dt className="text-gray-500">사업장 수</dt>
                  <dd className="tabular font-medium">{s.pf?.project_count}개 (브릿지 {s.pf?.bridge_count})</dd></div>
                <div className="flex justify-between"><dt className="text-gray-500">총 익스포저</dt>
                  <dd className="tabular font-medium">{formatAmount(s.pf?.exposure || 0, 'billion')}</dd></div>
                <div className="flex justify-between"><dt className="text-gray-500">워치리스트</dt>
                  <dd className={`tabular font-bold ${s.pf?.watchlist_count ? 'text-red-600' : ''}`}>{s.pf?.watchlist_count}개</dd></div>
                <div className="flex justify-between"><dt className="text-gray-500">공정-분양 괴리 경보(≥30%p)</dt>
                  <dd className={`tabular font-bold ${s.pf?.gap_alert_count ? 'text-red-600' : ''}`}>{s.pf?.gap_alert_count}개</dd></div>
                <div className="flex justify-between"><dt className="text-gray-500">평균 사업장 자기자본비율</dt>
                  <dd className="tabular font-medium">{formatPercent(s.pf?.avg_equity_ratio || 0, 1)}</dd></div>
              </dl>
            </Card>

            {/* 7. 포용금융 */}
            <Card title={s.inclusive?.title}>
              {[
                ['중신용 기업 (BBB+ 이하)', s.inclusive?.mid_credit],
                ['개인사업자 (SOHO)', s.inclusive?.soho],
              ].map(([label, seg]: any) => (
                <div key={label} className="mb-3 last:mb-0">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium">{label}</span>
                    <span className="tabular text-gray-600">
                      {formatPercent(seg?.share || 0, 1)} / 목표 {formatPercent(seg?.target || 0, 0)}
                    </span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full"
                      style={{ width: `${Math.min((seg?.share || 0) / (seg?.target || 1) * 100, 100)}%` }} />
                  </div>
                  <p className="text-[11px] text-gray-400 mt-1">
                    {formatNumber(seg?.count || 0)}건 · {formatAmount(seg?.exposure || 0, 'billion')} · 연체율 {formatPercent(seg?.delinquency_rate || 0, 3)}
                  </p>
                </div>
              ))}
            </Card>
          </div>

          <div className="grid grid-cols-3 gap-6">
            {/* 8. 워크아웃 */}
            <Card title={s.workout?.title}>
              <dl className="space-y-1.5 text-sm">
                <div className="flex justify-between"><dt className="text-gray-500">진행 중 케이스</dt>
                  <dd className="tabular font-medium">{s.workout?.active_cases}건</dd></div>
                <div className="flex justify-between"><dt className="text-gray-500">관리 익스포저</dt>
                  <dd className="tabular font-medium">{formatAmount(s.workout?.active_exposure || 0, 'billion')}</dd></div>
                <div className="flex justify-between"><dt className="text-gray-500">예상 회수액</dt>
                  <dd className="tabular font-medium">
                    {formatAmount(s.workout?.expected_recovery || 0, 'billion')} ({formatPercent(s.workout?.expected_recovery_rate || 0, 1)})
                  </dd></div>
              </dl>
              <div className="flex flex-wrap gap-1 mt-3">
                {s.workout?.by_strategy?.map((x: any) => (
                  <span key={x.name} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                    {x.name} {x.count}
                  </span>
                ))}
              </div>
            </Card>

            {/* 9. EWS */}
            <Card title={s.ews?.title}>
              <dl className="space-y-1.5 text-sm">
                <div className="flex justify-between"><dt className="text-gray-500">미해결 경보</dt>
                  <dd className="tabular font-bold">{s.ews?.open_alerts}건</dd></div>
                <div className="flex justify-between"><dt className="text-gray-500">고위험(HIGH/CRITICAL)</dt>
                  <dd className={`tabular font-bold ${s.ews?.high_alerts ? 'text-red-600' : ''}`}>{s.ews?.high_alerts}건</dd></div>
                <div className="flex justify-between"><dt className="text-gray-500">누적 경보</dt>
                  <dd className="tabular font-medium">{s.ews?.total_alerts}건</dd></div>
              </dl>
            </Card>

            {/* 10. 내부통제 */}
            <Card title={s.internal_control?.title}>
              <dl className="space-y-1.5 text-sm">
                <div className="flex justify-between"><dt className="text-gray-500">코베넌트 위반(미해소)</dt>
                  <dd className="tabular font-medium">{s.internal_control?.covenant_breaches}건 (중대 {s.internal_control?.covenant_major})</dd></div>
                <div className="flex justify-between"><dt className="text-gray-500">여신 신청 처리</dt>
                  <dd className="tabular font-medium text-right">
                    승인 {formatNumber(s.internal_control?.applications_approved || 0)} · 심사중 {s.internal_control?.applications_reviewing} · 부결 {s.internal_control?.applications_rejected}
                  </dd></div>
                <div className="flex justify-between"><dt className="text-gray-500">감사 기록</dt>
                  <dd className="tabular font-medium">{formatNumber(s.internal_control?.audit_log_count || 0)}건</dd></div>
              </dl>
            </Card>
          </div>
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


      {tab === 'exceptions' && exceptions && (
        <Card title={`정책 예외 관리 대장 (유효 ${exceptions.active}건 / 총 ${exceptions.total}건)`}
          subtitle="예외는 자유 메모가 아니라 규정→사유→완화수단→승인→재검토→성과의 구조로 관리됩니다">
          {exceptions.review_due > 0 && (
            <div className="mb-3 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              재검토일이 도래한 유효 예외 <b>{exceptions.review_due}건</b> - 재검토 후 연장 또는 종결 처리가 필요합니다
            </div>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                  <th className="py-2 pr-3">대상 규정</th>
                  <th className="py-2 pr-3">기업 / 신청</th>
                  <th className="py-2 pr-3">사유 → 완화수단</th>
                  <th className="py-2 pr-3">승인</th>
                  <th className="py-2 pr-3 text-center">재검토일</th>
                  <th className="py-2 text-center">상태</th>
                </tr>
              </thead>
              <tbody>
                {exceptions.exceptions.map((e: any) => (
                  <tr key={e.exception_id} className={`border-b border-gray-50 align-top ${e.review_due ? 'bg-red-50/40' : ''}`}>
                    <td className="py-2.5 pr-3">
                      <p className="font-medium text-xs">{e.rule_ref}</p>
                      <p className="text-[10px] text-gray-400">{e.rule_version}</p>
                    </td>
                    <td className="py-2.5 pr-3 text-xs">
                      {e.customer_name}
                      <p className="text-[10px] text-gray-400">{e.application_id}</p>
                    </td>
                    <td className="py-2.5 pr-3 text-xs text-gray-600 max-w-md">
                      {e.reason}
                      <p className="text-blue-700 mt-0.5">완화: {e.mitigation}</p>
                      {e.outcome && <p className="text-green-700 mt-0.5">성과: {e.outcome}</p>}
                    </td>
                    <td className="py-2.5 pr-3 text-xs">
                      {e.approver_name}
                      <p className="text-[10px] text-gray-400">{e.approver_level} · {e.approved_at}</p>
                    </td>
                    <td className={`py-2.5 pr-3 text-center text-xs ${e.review_due ? 'text-red-600 font-bold' : 'text-gray-500'}`}>
                      {e.review_date}
                    </td>
                    <td className="py-2.5 text-center">
                      <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                        e.status === 'ACTIVE' ? 'bg-amber-100 text-amber-700' :
                        e.status === 'CLOSED' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                      }`}>{e.status === 'ACTIVE' ? '유효' : e.status === 'CLOSED' ? '종결' : '만료'}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}


      {tab === 'rules' && rules && (
        <Card title={`규정 레지스터 (${rules.rules.length}건)`}
          subtitle="산식·임계값은 하드코딩 대신 이 레지스터의 버전·효력일을 근거로 관리됩니다">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                  <th className="py-2 pr-3">도메인</th>
                  <th className="py-2 pr-3">규정</th>
                  <th className="py-2 pr-3">근거</th>
                  <th className="py-2 pr-3">버전</th>
                  <th className="py-2 pr-3 text-center">효력기간</th>
                  <th className="py-2 pr-3">파라미터</th>
                  <th className="py-2">적용 위치</th>
                </tr>
              </thead>
              <tbody>
                {rules.rules.map((r: any) => (
                  <tr key={r.rule_id} className={`border-b border-gray-50 align-top ${!r.effective_now ? 'opacity-50' : ''}`}>
                    <td className="py-2 pr-3">
                      <span className="px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded text-[10px] font-semibold">{r.domain}</span>
                    </td>
                    <td className="py-2 pr-3 text-xs font-medium">{r.name}</td>
                    <td className="py-2 pr-3 text-xs text-gray-500">{r.basis}</td>
                    <td className="py-2 pr-3 text-xs">{r.version}</td>
                    <td className="py-2 pr-3 text-center text-[11px] text-gray-500">
                      {r.valid_from} ~ {r.valid_to || '현행'}
                    </td>
                    <td className="py-2 pr-3 text-[10px] text-gray-500 font-mono max-w-xs truncate">
                      {JSON.stringify(r.params)}
                    </td>
                    <td className="py-2 text-[11px] text-gray-400 max-w-[10rem]">{r.applied_in}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {tab === 'audit' && (
        <Card title={`감사 추적 (총 ${formatNumber(audit?.total || 0)}건 · 최근 50건)`}>
          {(audit?.logs || []).length === 0 ? (
            <p className="py-8 text-sm text-gray-400 text-center">
              아직 기록이 없습니다 - 승인·분류실행·ECL 재산출 등 쓰기 작업이 수행되면 기록됩니다.
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
