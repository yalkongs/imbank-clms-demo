import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Link, useOutletContext } from 'react-router-dom';
import { Stamp, AlertTriangle, ListChecks, Search, ChevronRight, TrendingUp } from 'lucide-react';
import { formatAmount, formatPercent } from '../utils/format';

/** 모바일 홈 - 핵심 지표 + 오늘 할 일 */
export default function MHome() {
  const { auth, openLogin } = useOutletContext<any>();
  const [summary, setSummary] = useState<any>(null);
  const [inbox, setInbox] = useState<any>(null);
  const [obligations, setObligations] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);

  useEffect(() => {
    axios.get('/api/dashboard/summary').then(r => setSummary(r.data)).catch(() => {});
    axios.get('/api/applications/approval-inbox').then(r => setInbox(r.data)).catch(() => {});
    axios.get('/api/obligations').then(r => setObligations(r.data)).catch(() => {});
    axios.get('/api/dashboard/ews-alerts').then(r => setAlerts(r.data || [])).catch(() => {});
  }, [auth]);

  const p = summary?.portfolio || {};
  const c = summary?.capital || {};
  const highAlerts = alerts.filter((a: any) => ['HIGH', 'CRITICAL'].includes(a.severity)).length;

  const TODO = [
    { to: '/m/approval', icon: Stamp, color: 'text-[#00897B] bg-[#00C7A9]/10',
      label: '결재 대기', value: inbox ? `${inbox.actionable ?? 0}건` : '-',
      sub: auth ? `전체 ${inbox?.items?.length ?? 0}건 중 내 전결` : '로그인 후 확인' },
    { to: '/m/alerts', icon: AlertTriangle, color: 'text-red-600 bg-red-50',
      label: 'EWS 경보', value: `${alerts.length}건`, sub: `고위험 ${highAlerts}건` },
    { to: '/m/obligations', icon: ListChecks, color: 'text-amber-600 bg-amber-50',
      label: '의무 기한', value: `${obligations?.total ?? 0}건`, sub: `기한 초과 ${obligations?.overdue ?? 0}건` },
  ];

  return (
    <>
      {/* 히어로 */}
      <div className="im-gradient rounded-2xl p-4 text-imbank-ink">
        <p className="text-[11px] font-semibold opacity-70">기업여신 포트폴리오</p>
        <p className="text-2xl font-bold tabular mt-0.5">{formatAmount(p.total_exposure || 0, 'billion')}</p>
        <div className="flex gap-4 mt-2 text-xs">
          <span>BIS <b className="tabular">{formatPercent(c.bis_ratio || 0)}</b></span>
          <span>RAROC <b className="tabular">{formatPercent(p.avg_raroc || 0)}</b></span>
          <span>기업 <b className="tabular">{(p.total_customers || 0).toLocaleString()}</b>개사</span>
        </div>
      </div>

      {!auth && (
        <button onClick={openLogin}
          className="w-full bg-white border border-[#00C7A9]/40 rounded-xl p-3.5 text-left">
          <p className="text-sm font-bold text-gray-900">로그인하고 모바일 결재 체험하기</p>
          <p className="text-xs text-gray-500 mt-0.5">체험 계정 4종 (심사역~임원, 전결권별) - PIN 힌트 제공</p>
        </button>
      )}

      {/* 오늘 할 일 */}
      <div>
        <h2 className="text-xs font-semibold text-gray-400 mb-2 px-0.5">오늘 할 일</h2>
        <div className="space-y-2">
          {TODO.map(t => (
            <Link key={t.to} to={t.to}
              className="flex items-center gap-3 bg-white border border-gray-200 rounded-xl p-3.5 active:bg-gray-50">
              <span className={`w-9 h-9 rounded-lg flex items-center justify-center flex-none ${t.color}`}>
                <t.icon size={17} />
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-900">{t.label} <b className="text-[#00897B]">{t.value}</b></p>
                <p className="text-[11px] text-gray-400">{t.sub}</p>
              </div>
              <ChevronRight size={16} className="row-chevron flex-none" />
            </Link>
          ))}
        </div>
      </div>

      {/* 최근 경보 미리보기 */}
      <div>
        <div className="flex items-center justify-between mb-2 px-0.5">
          <h2 className="text-xs font-semibold text-gray-400">최근 경보</h2>
          <Link to="/m/alerts" className="text-[11px] text-[#00897B] font-medium">전체보기</Link>
        </div>
        <div className="space-y-1.5">
          {alerts.slice(0, 3).map((a: any) => (
            <div key={a.alert_id} className="bg-white border border-gray-200 rounded-xl px-3.5 py-2.5">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-900 truncate">{a.customer_name}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold flex-none ${
                  a.severity === 'CRITICAL' ? 'bg-red-600 text-white' :
                  a.severity === 'HIGH' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>
                  {a.severity}
                </span>
              </div>
              <p className="text-[11px] text-gray-500 truncate mt-0.5">{a.trigger_condition}</p>
            </div>
          ))}
        </div>
      </div>

      {/* 빠른 조회 */}
      <div className="grid grid-cols-2 gap-2">
        <Link to="/m/customers" className="bg-white border border-gray-200 rounded-xl p-3.5 active:bg-gray-50">
          <Search size={16} className="text-gray-400 mb-1.5" />
          <p className="text-sm font-semibold text-gray-900">고객 조회</p>
          <p className="text-[11px] text-gray-400">현장에서 기업 요약 확인</p>
        </Link>
        <Link to="/m/delinquency" className="bg-white border border-gray-200 rounded-xl p-3.5 active:bg-gray-50">
          <TrendingUp size={16} className="text-gray-400 mb-1.5" />
          <p className="text-sm font-semibold text-gray-900">연체 현황</p>
          <p className="text-[11px] text-gray-400">DPD 버킷·연체율</p>
        </Link>
      </div>

      <p className="text-center text-[10px] text-gray-400 pt-1">
        모의 데이터 기반 PoC · <Link to="/m/more" className="underline">전체 기능은 '전체' 탭에서</Link>
      </p>
    </>
  );
}
