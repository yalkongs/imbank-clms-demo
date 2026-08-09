import React, { useEffect, useState } from 'react';
import {
  FileCheck, AlertTriangle, CheckCircle, XCircle,
  Clock, RefreshCw, ChevronDown, ChevronUp, Shield, Info
} from 'lucide-react';
import { Card, Badge, RegionFilter, PageLoader } from '../components';
import { covenantApi } from '../utils/api';
import { formatAmount, formatDate } from '../utils/format';

// ============================================================
// 타입 및 상수
// ============================================================
const SEVERITY_META: Record<string, { label: string; color: string }> = {
  EVENT_OF_DEFAULT: { label: '기한이익상실', color: 'bg-red-100 text-red-700 border-red-200' },
  MAJOR:            { label: '중대 위반',    color: 'bg-orange-100 text-orange-700 border-orange-200' },
  MINOR:            { label: '경미 위반',    color: 'bg-yellow-100 text-yellow-700 border-yellow-200' },
};

const RESULT_META: Record<string, { label: string; icon: React.ReactNode }> = {
  PASS:   { label: '이행', icon: <CheckCircle size={14} className="text-green-600" /> },
  BREACH: { label: '위반', icon: <XCircle size={14} className="text-red-600" /> },
  WAIVED: { label: '유예', icon: <Shield size={14} className="text-blue-600" /> },
};

const TYPE_LABELS: Record<string, string> = {
  FINANCIAL:   '재무',
  BEHAVIORAL:  '행동',
  INFORMATION: '정보',
};

// ============================================================
// 서브컴포넌트
// ============================================================
const SeverityBadge = ({ severity }: { severity: string | null }) => {
  if (!severity) return null;
  const meta = SEVERITY_META[severity];
  if (!meta) return <span className="text-xs text-gray-500">{severity}</span>;
  return (
    <span className={`text-xs px-2 py-0.5 rounded border font-medium ${meta.color}`}>
      {meta.label}
    </span>
  );
};

const ResultIcon = ({ result }: { result: string }) => {
  const meta = RESULT_META[result];
  if (!meta) return <Clock size={14} className="text-gray-400" />;
  return <>{meta.icon}</>;
};

// ============================================================
// 메인 컴포넌트
// ============================================================
export default function Covenant() {
  const [region, setRegion] = useState('');
  const [loading, setLoading] = useState(true);
  const [breachData, setBreachData] = useState<any>(null);
  const [dueData, setDueData] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'breach' | 'due' | 'all'>('breach');
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [historyCache, setHistoryCache] = useState<Record<string, any>>({});
  const [historyLoading, setHistoryLoading] = useState<string | null>(null);

  // 웨이버 모달
  const [showWaiverModal, setShowWaiverModal] = useState(false);
  const [waiverTarget, setWaiverTarget] = useState<any>(null);
  const [waiverForm, setWaiverForm] = useState({ reason: '', approved_by: '', days: 90 });
  const [waiverLoading, setWaiverLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, [region]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [breachRes, dueRes] = await Promise.all([
        covenantApi.getBreachStatus(region || undefined),
        covenantApi.getDueCheck(30, region || undefined),
      ]);
      setBreachData(breachRes.data);
      setDueData(dueRes.data);
    } catch (e) {
      console.error('Covenant load error:', e);
    } finally {
      setLoading(false);
    }
  };

  const toggleRow = async (covenantId: string) => {
    const newSet = new Set(expandedRows);
    if (newSet.has(covenantId)) {
      newSet.delete(covenantId);
    } else {
      newSet.add(covenantId);
      if (!historyCache[covenantId]) {
        setHistoryLoading(covenantId);
        try {
          const res = await covenantApi.getHistory(covenantId);
          setHistoryCache(prev => ({ ...prev, [covenantId]: res.data }));
        } catch (e) {
          console.error('History load error:', e);
        } finally {
          setHistoryLoading(null);
        }
      }
    }
    setExpandedRows(newSet);
  };

  const openWaiverModal = (covenant: any) => {
    setWaiverTarget(covenant);
    setWaiverForm({ reason: '', approved_by: '', days: 90 });
    setShowWaiverModal(true);
  };

  const submitWaiver = async () => {
    if (!waiverTarget || !waiverForm.reason || !waiverForm.approved_by) return;
    setWaiverLoading(true);
    try {
      await covenantApi.applyWaiver(waiverTarget.covenant_id, {
        reason: waiverForm.reason,
        approved_by: waiverForm.approved_by,
        waiver_period_days: waiverForm.days,
      });
      setShowWaiverModal(false);
      loadData();
    } catch (e) {
      console.error('Waiver error:', e);
    } finally {
      setWaiverLoading(false);
    }
  };

  // ──────────────── 렌더링 ────────────────
  if (loading) {
    return <PageLoader label="코베넌트 데이터를 불러오는 중" />;
  }

  const breach = breachData?.breach_summary || {};
  const breachList = breachData?.breaches || [];
  const dueList = dueData?.due_covenants || [];

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">코베넌트 관리</h1>
          <p className="text-sm text-gray-500 mt-1">여신 약정 조건 이행 모니터링 및 위반 관리</p>
        </div>
        <div className="flex items-center gap-3">
          <RegionFilter value={region} onChange={setRegion} />
          <button
            onClick={loadData}
            className="flex items-center px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
          >
            <RefreshCw size={16} className="mr-1.5" /> 새로고침
          </button>
        </div>
      </div>

      {/* KPI 카드 */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="p-4">
          <p className="text-xs text-gray-500 mb-1">전체 위반</p>
          <p className="text-3xl font-bold text-gray-800">{breach.total_breach ?? 0}</p>
          <p className="text-xs text-gray-400 mt-1">활성 위반 코베넌트</p>
        </Card>
        <Card className="p-4 border-red-100">
          <p className="text-xs text-red-600 mb-1 font-medium">기한이익상실</p>
          <p className="text-3xl font-bold text-red-600">{breach.event_of_default ?? 0}</p>
          <p className="text-xs text-gray-400 mt-1">즉시 조치 필요</p>
        </Card>
        <Card className="p-4 border-orange-100">
          <p className="text-xs text-orange-600 mb-1 font-medium">중대 위반</p>
          <p className="text-3xl font-bold text-orange-600">{breach.major ?? 0}</p>
          <p className="text-xs text-gray-400 mt-1">추가 담보 요구 검토</p>
        </Card>
        <Card className="p-4 border-yellow-100">
          <p className="text-xs text-yellow-600 mb-1 font-medium">점검 예정 (30일)</p>
          <p className="text-3xl font-bold text-yellow-600">{dueData?.total ?? 0}</p>
          <p className="text-xs text-gray-400 mt-1">
            기한 초과: <span className="font-semibold text-red-500">{dueData?.overdue ?? 0}</span>건
          </p>
        </Card>
      </div>

      {/* 탭 */}
      <Card className="overflow-hidden">
        <div className="flex border-b border-gray-200">
          {([
            { key: 'breach', label: `위반 현황 (${breachList.length})`, icon: XCircle },
            { key: 'due',    label: `점검 예정 (${dueList.length})`,    icon: Clock },
          ] as const).map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`flex items-center px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === key
                  ? 'border-blue-600 text-blue-600 bg-blue-50'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              <Icon size={16} className="mr-1.5" /> {label}
            </button>
          ))}
        </div>

        <div className="p-4">
          {/* ── 위반 현황 ── */}
          {activeTab === 'breach' && (
            breachList.length === 0 ? (
              <div className="text-center py-12 text-gray-400">
                <CheckCircle size={40} className="mx-auto mb-3 text-green-300" />
                <p>위반 코베넌트가 없습니다.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {breachList.map((b: any) => (
                  <div key={b.covenant_id} className="border border-gray-100 rounded-lg">
                    <div
                      className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-gray-50"
                      onClick={() => toggleRow(b.covenant_id)}
                    >
                      <div className="flex items-center gap-3">
                        <XCircle size={16} className="text-red-500 flex-shrink-0" />
                        <div>
                          <p className="text-sm font-medium text-gray-800">{b.customer_name}</p>
                          <p className="text-xs text-gray-500">{b.covenant_name} ({b.covenant_code})</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-gray-400 hidden sm:block">
                          {TYPE_LABELS[b.covenant_type]}
                        </span>
                        <SeverityBadge severity={b.breach_severity} />
                        <div className="text-right text-xs text-gray-500 hidden md:block">
                          <p>실측: <span className="font-medium">{b.actual_value?.toFixed(2) ?? '-'}</span></p>
                          <p>기준: {b.threshold_value?.toFixed(2) ?? '-'}</p>
                        </div>
                        {expandedRows.has(b.covenant_id)
                          ? <ChevronUp size={16} className="text-gray-400" />
                          : <ChevronDown size={16} className="text-gray-400" />
                        }
                      </div>
                    </div>

                    {/* 확장: 이행 이력 + 액션 버튼 */}
                    {expandedRows.has(b.covenant_id) && (
                      <div className="border-t border-gray-100 px-4 py-3 bg-gray-50 space-y-3">
                        {historyLoading === b.covenant_id ? (
                          <div className="text-xs text-gray-500 flex items-center">
                            <RefreshCw size={12} className="animate-spin mr-1" /> 이력 로딩 중...
                          </div>
                        ) : historyCache[b.covenant_id] ? (
                          <div>
                            <p className="text-xs font-semibold text-gray-600 mb-2">점검 이력</p>
                            <div className="space-y-1">
                              {historyCache[b.covenant_id].history?.slice(0, 5).map((h: any) => (
                                <div key={h.check_id} className="flex items-center justify-between text-xs text-gray-600 py-1 border-b border-gray-100 last:border-0">
                                  <div className="flex items-center gap-2">
                                    <ResultIcon result={h.result} />
                                    <span>{h.check_date}</span>
                                    <span>실측: {h.actual_value?.toFixed(2) ?? '-'}</span>
                                  </div>
                                  <SeverityBadge severity={h.breach_severity} />
                                </div>
                              ))}
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              이행률: {historyCache[b.covenant_id].stats?.pass_rate?.toFixed(1) ?? '-'}%
                              ({historyCache[b.covenant_id].stats?.pass}/{historyCache[b.covenant_id].stats?.total_checks})
                            </div>
                          </div>
                        ) : null}

                        <div className="flex gap-2">
                          <button
                            onClick={() => openWaiverModal(b)}
                            className="px-3 py-1.5 text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100"
                          >
                            웨이버(유예) 신청
                          </button>
                          <button
                            onClick={async () => {
                              try {
                                await covenantApi.runCheck(b.covenant_id, { checked_by: '심사담당자' });
                                setHistoryCache(prev => ({ ...prev, [b.covenant_id]: undefined as any }));
                                loadData();
                              } catch(e) { console.error(e); }
                            }}
                            className="px-3 py-1.5 text-xs bg-white text-gray-700 border border-gray-200 rounded hover:bg-gray-50"
                          >
                            재점검
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )
          )}

          {/* ── 점검 예정 ── */}
          {activeTab === 'due' && (
            dueList.length === 0 ? (
              <div className="text-center py-12 text-gray-400">
                <Clock size={40} className="mx-auto mb-3 text-gray-300" />
                <p>30일 이내 점검 예정 코베넌트가 없습니다.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs text-gray-500">고객명</th>
                      <th className="px-3 py-2 text-left text-xs text-gray-500">코베넌트</th>
                      <th className="px-3 py-2 text-center text-xs text-gray-500">유형</th>
                      <th className="px-3 py-2 text-center text-xs text-gray-500">점검 주기</th>
                      <th className="px-3 py-2 text-right text-xs text-gray-500">점검 예정일</th>
                      <th className="px-3 py-2 text-center text-xs text-gray-500">최근 결과</th>
                      <th className="px-3 py-2 text-center text-xs text-gray-500">액션</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {dueList.map((d: any) => (
                      <tr key={d.covenant_id} className={d.is_overdue ? 'bg-red-50' : ''}>
                        <td className="px-3 py-2">
                          <p className="font-medium">{d.customer_name}</p>
                          {d.is_overdue && (
                            <span className="text-xs text-red-600 font-medium">기한 초과</span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-gray-600">
                          <p>{d.covenant_name}</p>
                          <p className="text-xs text-gray-400">{d.covenant_code}</p>
                        </td>
                        <td className="px-3 py-2 text-center">
                          <span className="text-xs px-1.5 py-0.5 bg-gray-100 rounded">
                            {TYPE_LABELS[d.covenant_type]}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-center text-xs text-gray-500">{d.check_frequency}</td>
                        <td className="px-3 py-2 text-right text-xs">{d.next_check_date}</td>
                        <td className="px-3 py-2 text-center">
                          {d.last_result ? (
                            <div className="flex items-center justify-center gap-1">
                              <ResultIcon result={d.last_result} />
                              <span className="text-xs">{RESULT_META[d.last_result]?.label}</span>
                            </div>
                          ) : <span className="text-xs text-gray-400">미점검</span>}
                        </td>
                        <td className="px-3 py-2 text-center">
                          <button
                            onClick={async () => {
                              try {
                                await covenantApi.runCheck(d.covenant_id, { checked_by: '심사담당자' });
                                loadData();
                              } catch(e) { console.error(e); }
                            }}
                            className="px-2 py-1 text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100"
                          >
                            점검 실행
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}
        </div>
      </Card>

      {/* 웨이버 모달 */}
      {showWaiverModal && waiverTarget && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md">
            <div className="flex items-center justify-between p-5 border-b">
              <h3 className="text-lg font-semibold text-gray-900">웨이버(유예) 신청</h3>
              <button onClick={() => setShowWaiverModal(false)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <div className="p-5 space-y-4">
              <div className="bg-yellow-50 rounded-lg p-3">
                <p className="text-sm font-medium text-yellow-800">{waiverTarget.covenant_name}</p>
                <p className="text-xs text-yellow-600 mt-1">{waiverTarget.customer_name}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">웨이버 사유 <span className="text-red-500">*</span></label>
                <textarea
                  value={waiverForm.reason}
                  onChange={e => setWaiverForm(f => ({ ...f, reason: e.target.value }))}
                  rows={3}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="일시적 유동성 위기, 경기 요인 등 구체적 사유를 입력하세요"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">승인자 <span className="text-red-500">*</span></label>
                <input
                  value={waiverForm.approved_by}
                  onChange={e => setWaiverForm(f => ({ ...f, approved_by: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  placeholder="여신심사부장"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">유예 기간</label>
                <select
                  value={waiverForm.days}
                  onChange={e => setWaiverForm(f => ({ ...f, days: Number(e.target.value) }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                >
                  <option value={30}>30일</option>
                  <option value={90}>90일</option>
                  <option value={180}>180일</option>
                </select>
              </div>
              {waiverForm.approved_by && (
                <div className="bg-blue-50 rounded-lg p-3 text-xs text-blue-700">
                  <Info size={12} className="inline mr-1" />
                  웨이버 횟수가 2회 이상이면 경영진 보고가 필요합니다.
                </div>
              )}
            </div>
            <div className="flex justify-end gap-3 p-5 border-t">
              <button
                onClick={() => setShowWaiverModal(false)}
                className="px-4 py-2 text-sm text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                취소
              </button>
              <button
                onClick={submitWaiver}
                disabled={waiverLoading || !waiverForm.reason || !waiverForm.approved_by}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {waiverLoading ? '처리 중...' : '웨이버 승인'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
