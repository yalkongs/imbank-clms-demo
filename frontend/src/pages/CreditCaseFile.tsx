import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import {
  FileText, Building2, Database, Cpu, Stamp, AlertTriangle,
  Landmark, Activity, BookOpen, ArrowLeft,
} from 'lucide-react';
import { Card, PageLoader } from '../components';
import { formatAmount, formatPercent } from '../utils/format';

/**
 * 전자 여신철 (Credit Case File)
 * --------------------------------
 * "왜 승인했는가"를 사후에 재현하는 심사·승인 기록 (여신철).
 * 신청→자료 근거(기준일·출처)→모델 산출(버전)→승인 체인(전결)→정책 예외→
 * 실행→사후관리를 시간 순서의 단일 화면으로 보여준다.
 */

const CLS_KO: Record<string, string> = {
  NORMAL: '정상', PRECAUTIONARY: '요주의', SUBSTANDARD: '고정',
  DOUBTFUL: '회수의문', LOSS: '추정손실',
};
const LEVEL_KO: Record<string, string> = {
  STAFF: '담당자', TEAM_LEAD: '팀장', DEPT_HEAD: '부서장',
  EXECUTIVE: '임원', COMMITTEE: '여신위원회',
};

// 결재 API 는 APPROVE/CONDITIONAL/REJECT 로 기록하고 시드에는 APPROVED 도 남아 있다.
// 종전에는 APPROVED 외 전부를 반려로 칠해 조건부승인이 빨간 배지로 보였다.
const DECISION_STYLE: Record<string, { ko: string; cls: string }> = {
  APPROVE:     { ko: '승인',     cls: 'bg-green-100 text-green-700' },
  APPROVED:    { ko: '승인',     cls: 'bg-green-100 text-green-700' },
  CONDITIONAL: { ko: '조건부승인', cls: 'bg-blue-100 text-blue-700' },
  REJECT:      { ko: '반려',     cls: 'bg-red-100 text-red-700' },
  REJECTED:    { ko: '반려',     cls: 'bg-red-100 text-red-700' },
};

function Section({ icon, title, badge, children }: {
  icon: React.ReactNode; title: string; badge?: React.ReactNode; children: React.ReactNode;
}) {
  return (
    <div className="relative pl-10 pb-6 border-l-2 border-gray-100 last:border-l-transparent last:pb-0">
      <span className="absolute -left-[15px] top-0 w-7 h-7 rounded-full bg-white border-2 border-[#00BFA5] text-[#00897B] flex items-center justify-center">
        {icon}
      </span>
      <div className="flex items-center gap-2 mb-2">
        <h3 className="text-sm font-bold text-gray-900">{title}</h3>
        {badge}
      </div>
      {children}
    </div>
  );
}

function KV({ items }: { items: [string, React.ReactNode][] }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
      {items.map(([l, v]) => (
        <div key={l} className="bg-gray-50 rounded-lg px-3 py-2">
          <p className="text-[11px] text-gray-400">{l}</p>
          <p className="text-sm font-semibold text-gray-900 tabular truncate">{v ?? '-'}</p>
        </div>
      ))}
    </div>
  );
}

export default function CreditCaseFile() {
  const { applicationId } = useParams();
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    axios.get(`/api/credit-case/${applicationId}`)
      .then(r => setData(r.data))
      .catch(e => setError(e?.response?.data?.detail || '여신철을 불러오지 못했습니다'));
  }, [applicationId]);

  if (error) return <div className="p-8 text-sm text-red-600">{error}</div>;
  if (!data) return <PageLoader label="여신철을 여는 중" />;

  const { application: app, borrower, data_basis: basis, model_outputs: model,
          approvals, exceptions, execution, post_management: post, applied_rules } = data;

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/approval-inbox" className="inline-flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 mb-1">
            <ArrowLeft size={12} /> 결재함
          </Link>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            전자 여신철
            <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs font-semibold">{app.application_id}</span>
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            심사·승인의 근거자료와 결재 경과를 승인 당시 기준으로 재현합니다 - 사후관리 항목만 현재 기준 (기준일 {data.as_of})
          </p>
        </div>
      </div>

      {data.snapshot && (
        <Card>
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div>
              <p className="text-sm font-bold text-gray-900 flex items-center gap-2">
                🔒 승인 당시 확정 기록 (원본 보존)
                {data.snapshot.backfilled && (
                  <span className="px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded text-[10px]">과거 승인건 소급 등재</span>
                )}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                확정일 {String(data.snapshot.sealed_at).slice(0, 10)} · 무결성 검증값 {String(data.snapshot.hash).slice(0, 16)}… ·
                이후 자료가 갱신되어도 이 기록은 변경되지 않습니다
              </p>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-3">
            {[
              ['승인 당시 등급', data.snapshot.input?.rating?.final_grade || '산출 전',
               data.snapshot.input?.rating ? `${data.snapshot.input.rating.model_id} · ${data.snapshot.input.rating.rating_date}` : ''],
              ['승인 당시 재무', data.snapshot.input?.financial_statement ? `FY${data.snapshot.input.financial_statement.fiscal_year}` : '-',
               data.snapshot.input?.financial_statement?.source || ''],
              ['동일차주 소진', data.snapshot.input?.borrower_scope?.vs_capital_pct != null
                ? `${data.snapshot.input.borrower_scope.vs_capital_pct}%` : '그룹 없음',
               '자기자본 대비'],
              ['한도 검증', data.snapshot.input?.limit_check?.within_limit === false ? '초과' :
                data.snapshot.input?.limit_check?.within_limit === true ? '충족' : '-', '규제 25% 기준'],
            ].map(([l, v, sub]) => (
              <div key={l as string} className="bg-emerald-50/60 border border-emerald-100 rounded-lg px-3 py-2">
                <p className="text-[11px] text-gray-400">{l}</p>
                <p className="text-sm font-bold text-gray-900">{v}</p>
                {sub && <p className="text-[10px] text-gray-400">{sub}</p>}
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card title="현재 기준 조회 (참고)" subtitle="아래는 현행 자료를 신청일 기준으로 정리한 참고 화면입니다 - 정본은 위의 확정 기록입니다">
        <div className="pt-2">
          {/* ① 신청 */}
          <Section icon={<FileText size={14} />} title="① 신청"
            badge={<span className="text-[11px] text-gray-400">{app.application_date}</span>}>
            <KV items={[
              ['상품', app.product_name || app.product_code],
              ['신청금액', formatAmount(app.requested_amount, 'billion')],
              ['기간', `${app.tenor}개월`],
              ['취급점', app.branch],
            ]} />
          </Section>

          {/* ② 차주 */}
          <Section icon={<Building2 size={14} />} title="② 차주">
            <KV items={[
              ['기업명', borrower?.name],
              ['업종 / 지역', `${borrower?.industry || '-'}`],
              ['규모 / 상장', `${borrower?.size || '-'} / ${borrower?.listing || '-'}`],
              ['차주그룹', borrower?.group?.group_name || '해당 없음'],
            ]} />
          </Section>

          {/* ③ 자료 근거 */}
          <Section icon={<Database size={14} />} title="③ 자료 근거"
            badge={<span className="text-[11px] text-gray-400">무엇을 · 언제 기준으로 · 어디서</span>}>
            {basis.financial_statement ? (
              <div className="text-sm text-gray-700 space-y-1">
                <p>
                  <b>{basis.financial_statement.fiscal_year}</b> 회계연도 재무제표
                  ({basis.financial_statement.audited ? '감사보고서' : '자체결산'} ·
                  출처 {basis.financial_statement.source}) -
                  매출 {formatAmount(basis.financial_statement.revenue, 'billion')} ·
                  총자산 {formatAmount(basis.financial_statement.total_assets, 'billion')}
                </p>
                {basis.financial_ratio && (
                  <p className="text-xs text-gray-500">
                    재무비율 산출일 {String(basis.financial_ratio.calc_date).slice(0, 10)} - 부채비율 {basis.financial_ratio.debt_ratio?.toFixed(0)}% ·
                    이자보상배율 {basis.financial_ratio.icr?.toFixed(2)}
                  </p>
                )}
              </div>
            ) : <p className="text-sm text-gray-400">재무자료 없음</p>}
          </Section>

          {/* ④ 모델 산출 */}
          <Section icon={<Cpu size={14} />} title="④ 모델 산출 (자동)"
            badge={model.rating && (
              <span className="text-[11px] px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded">
                {model.rating.model_id} v{model.rating.model_version} · {model.rating.rating_date}
              </span>
            )}>
            {!model.rating && (
              <p className="text-xs text-amber-600 mb-2">
                등급 산출 전 - 심사 진행 중인 신규 차주입니다 (승인 전 등급·리스크 파라미터 산출 필요)
              </p>
            )}
            <KV items={[
              ['신용등급', model.rating?.final_grade],
              ['PD', model.rating ? formatPercent((model.rating.pd || 0) * 100) : '-'],
              ['LGD', model.risk_parameter ? formatPercent((model.risk_parameter.lgd || 0) * 100, 1) : '-'],
              ['예상손실(EL)', model.risk_parameter ? formatAmount(model.risk_parameter.expected_loss, 'billion') : '-'],
            ]} />
            {model.rating?.override && (
              <div className="mt-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
                <b>수동조정(Override)</b>: {model.rating.override.grade} - {model.rating.override.reason}
                <span className="text-amber-600"> (승인: {model.rating.override.by})</span>
              </div>
            )}
          </Section>

          {/* ⑤ 정책 예외 */}
          <Section icon={<AlertTriangle size={14} />} title="⑤ 정책 예외"
            badge={exceptions.length > 0 && (
              <span className="text-[11px] px-1.5 py-0.5 bg-red-50 text-red-600 rounded font-semibold">{exceptions.length}건</span>
            )}>
            {exceptions.length === 0 ? (
              <p className="text-sm text-gray-400">정책 예외 없음 - 정상 승인</p>
            ) : (
              <div className="space-y-2">
                {exceptions.map((e: any, i: number) => (
                  <div key={i} className="border border-red-100 bg-red-50/50 rounded-lg p-3 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-gray-900">{e.rule_ref} <span className="font-normal text-gray-400">({e.rule_version})</span></span>
                      <span className={`px-1.5 py-0.5 rounded font-semibold ${
                        e.status === 'ACTIVE' ? 'bg-red-100 text-red-700' :
                        e.status === 'CLOSED' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                      }`}>{e.status === 'ACTIVE' ? '유효' : e.status === 'CLOSED' ? '종결' : '만료'}</span>
                    </div>
                    <p className="mt-1 text-gray-700">사유: {e.reason}</p>
                    <p className="text-gray-700">완화수단: {e.mitigation}</p>
                    <p className="text-gray-400 mt-1">
                      승인 {e.approver_name}({e.approver_level}) {e.approved_at} · 유효기간 ~{e.valid_until} · 재검토일 {e.review_date}
                    </p>
                    {e.outcome && <p className="text-green-700 mt-1">성과: {e.outcome}</p>}
                  </div>
                ))}
              </div>
            )}
          </Section>

          {/* ⑥ 승인 체인 */}
          <Section icon={<Stamp size={14} />} title="⑥ 승인 (전결 체인)">
            {approvals.length === 0 ? (
              <p className="text-sm text-gray-400">결재 이력 없음</p>
            ) : (
              <div className="space-y-2.5">
                {approvals.map((a: any, i: number) => (
                  <div key={i} className="text-sm">
                    <div className="flex items-center gap-3">
                      <span className="w-20 flex-none text-xs font-semibold text-gray-500">{LEVEL_KO[a.level] || a.level}</span>
                      <span className="font-medium">{a.approver}</span>
                      <span className={`px-1.5 py-0.5 rounded text-[11px] font-semibold ${
                        DECISION_STYLE[a.decision]?.cls || 'bg-gray-100 text-gray-600'
                      }`}>{DECISION_STYLE[a.decision]?.ko || a.decision}</span>
                      <span className="text-xs text-gray-400">{a.decided_at}</span>
                    </div>
                    {/* 구조화 승인조건 - 선행/후속 구분과 이행기한을 그대로 보여준다.
                        구조화 값이 없는 과거 결재는 자유 텍스트로 남아 있다. */}
                    {a.conditions_structured?.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5 mt-1.5 ml-[5.75rem]">
                        {a.conditions_structured.map((c: any) => (
                          <span key={c.code}
                                className={`px-2 py-0.5 rounded text-[11px] border ${
                                  c.type === 'CP'
                                    ? 'bg-amber-50 text-amber-700 border-amber-200'
                                    : 'bg-blue-50 text-blue-700 border-blue-200'}`}>
                            <span className="font-semibold">{c.type === 'CP' ? '선행' : '후속'}</span>
                            {' '}{c.label}
                            {c.due_days ? <span className="text-gray-400"> · {c.due_days}일 내</span> : null}
                          </span>
                        ))}
                      </div>
                    ) : a.conditions ? (
                      <p className="text-xs text-blue-600 mt-1 ml-[5.75rem]">조건: {a.conditions}</p>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </Section>

          {/* ⑦ 실행 */}
          <Section icon={<Landmark size={14} />} title="⑦ 실행 (시설·담보)">
            {execution.facilities.map((f: any) => (
              <div key={f.facility_id} className="text-sm text-gray-700 mb-1">
                {f.facility_id} - 승인 {formatAmount(f.approved, 'billion')} ·
                잔액 {formatAmount(f.outstanding, 'billion')} ·
                금리 {formatPercent((f.rate || 0) * 100)} ·
                계약 {f.contract_date} ~ {f.maturity}
                <span className={`ml-2 px-1.5 py-0.5 rounded text-[11px] font-semibold ${
                  f.classification === 'NORMAL' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'
                }`}>{CLS_KO[f.classification] || f.classification}{f.dpd > 0 ? ` · DPD ${f.dpd}일` : ''}</span>
              </div>
            ))}
            {execution.collaterals.length > 0 ? (
              <p className="text-xs text-gray-500 mt-1">
                담보: {execution.collaterals.map((c: any) =>
                  `${c.type} ${formatAmount(c.value, 'billion')} (인정률 ${((c.recognition_ratio || 0) * 100).toFixed(0)}% · 평가 ${c.valuation_date})`
                ).join(' · ')}
              </p>
            ) : <p className="text-xs text-gray-400 mt-1">담보 없음 (신용)</p>}
          </Section>

          {/* ⑧ 사후관리 */}
          <Section icon={<Activity size={14} />} title="⑧ 사후관리">
            <div className="text-sm text-gray-700 space-y-1">
              {post.ews && (
                <p>EWS 종합 <b className="tabular">{post.ews.score?.toFixed(1)}점</b>
                  <span className="text-xs text-gray-400"> ({post.ews.grade} · {post.ews.score_date})</span></p>
              )}
              {post.covenants.length > 0 && (
                <p className="text-xs text-gray-500">
                  코베넌트 {post.covenants.length}건 - 최근 점검:{' '}
                  {post.covenants.slice(0, 3).map((c: any) =>
                    `${c.type || '재무약정'} ${c.result || '-'}`).join(' · ')}
                </p>
              )}
              {post.audit_trail.length > 0 && (
                <p className="text-xs text-gray-400">감사 기록 {post.audit_trail.length}건 (최근: {post.audit_trail[0].action} · {String(post.audit_trail[0].at).slice(0, 16)})</p>
              )}
            </div>
          </Section>

          {/* ⑨ 적용 규정 */}
          <Section icon={<BookOpen size={14} />} title="⑨ 적용 규정·버전">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
              {applied_rules.map((r: any) => (
                <p key={r.rule} className="text-xs text-gray-500">
                  <b className="text-gray-700">{r.rule}</b> - {r.basis} <span className="text-gray-400">({r.version})</span>
                </p>
              ))}
            </div>
          </Section>
        </div>
      </Card>
    </div>
  );
}
