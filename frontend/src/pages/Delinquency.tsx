import React, { useState, useEffect } from 'react';
import { delinquencyApi } from '../utils/api';
import {
  AlertCircle,
  PhoneCall,
  Mail,
  FileText,
  TrendingDown,
  Activity,
  ChevronDown,
  ChevronUp,
  Plus,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts';

const STAGE_COLORS: Record<string, string> = {
  EARLY:    '#f59e0b',
  MID:      '#f97316',
  LATE:     '#ef4444',
  NPL:      '#dc2626',
  WRITEOFF: '#7f1d1d',
};

const STAGE_BG: Record<string, string> = {
  EARLY:    'bg-yellow-100 text-yellow-800',
  MID:      'bg-orange-100 text-orange-800',
  LATE:     'bg-red-100 text-red-800',
  NPL:      'bg-red-200 text-red-900',
  WRITEOFF: 'bg-gray-200 text-gray-900',
};

const ACTIVITY_ICONS: Record<string, React.ReactNode> = {
  CALL:         <PhoneCall size={14} />,
  EMAIL:        <Mail size={14} />,
  LETTER:       <FileText size={14} />,
  SMS:          <Mail size={14} />,
  VISIT:        <AlertCircle size={14} />,
  LEGAL_NOTICE: <FileText size={14} />,
};

const fmtAmt = (v: number) => `${(v / 100000000).toFixed(1)}억`;

interface DashboardData {
  total_outstanding: number;
  total_delinquent: number;
  delinquency_rate: number;
  npl_exposure: number;
  npl_ratio: number;
  new_7days: { count: number; amount: number };
  buckets: any[];
}

interface DelinquencyItem {
  delinquency_id: string;
  facility_id: string;
  company_name: string;
  dpd: number;
  stage: string;
  stage_label: string;
  stage_color: string;
  overdue_amount: number;
  overdue_date: string;
  outstanding: number;
  credit_grade: string;
  assigned_officer: string;
}

interface ActivityModalState {
  open: boolean;
  delinquencyId: string;
  facilityId: string;
  companyName: string;
}

export default function Delinquency() {
  const [tab, setTab] = useState<'dashboard' | 'list' | 'rollrate' | 'performance'>('dashboard');
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [items, setItems]         = useState<DelinquencyItem[]>([]);
  const [rollRate, setRollRate]   = useState<any[]>([]);
  const [performance, setPerformance] = useState<any>(null);
  const [filterStage, setFilterStage] = useState<string>('');
  const [expandedId, setExpandedId]   = useState<string | null>(null);
  const [expandedDetail, setExpandedDetail] = useState<any>(null);
  const [loading, setLoading]     = useState(true);
  const [activityModal, setActivityModal] = useState<ActivityModalState>({
    open: false, delinquencyId: '', facilityId: '', companyName: '',
  });
  const [activityForm, setActivityForm] = useState({
    type: 'CALL', result: 'REACHED', notes: '', officer: '김여신',
  });

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const res = await delinquencyApi.getDashboard();
      setDashboard(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadList = async (stage?: string) => {
    try {
      const res = await delinquencyApi.getActive(stage || undefined, 50);
      setItems(res.data.items || []);
    } catch (e) {
      console.error(e);
    }
  };

  const loadRollRate = async () => {
    try {
      const res = await delinquencyApi.getRollRate();
      setRollRate(res.data.roll_rates || []);
    } catch (e) {
      console.error(e);
    }
  };

  const loadPerformance = async () => {
    try {
      const res = await delinquencyApi.getCollectionPerformance(3);
      setPerformance(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleTabChange = (t: typeof tab) => {
    setTab(t);
    if (t === 'list' && items.length === 0) loadList();
    if (t === 'rollrate' && rollRate.length === 0) loadRollRate();
    if (t === 'performance' && !performance) loadPerformance();
  };

  const handleExpandRow = async (id: string, facilityId: string) => {
    if (expandedId === id) {
      setExpandedId(null);
      setExpandedDetail(null);
      return;
    }
    setExpandedId(id);
    try {
      const res = await delinquencyApi.getFacility(facilityId);
      setExpandedDetail(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleRecordActivity = async () => {
    try {
      await delinquencyApi.recordActivity({
        delinquency_id: activityModal.delinquencyId,
        facility_id:    activityModal.facilityId,
        activity_type:  activityForm.type,
        contact_result: activityForm.result,
        notes:          activityForm.notes,
        officer:        activityForm.officer,
      });
      alert('추심 활동 기록 완료');
      setActivityModal({ ...activityModal, open: false });
      if (tab === 'list') loadList(filterStage);
    } catch (e) {
      alert('기록 실패');
    }
  };

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">연체 관리</h1>
          <p className="text-sm text-gray-500 mt-1">
            DPD 추적 · 연체 단계 관리 · 추심 활동 기록 · Roll Rate 분석
          </p>
        </div>
      </div>

      {/* KPI 카드 */}
      {dashboard && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">연체율</p>
            <p className={`text-2xl font-bold ${dashboard.delinquency_rate > 2 ? 'text-red-600' : 'text-gray-900'}`}>
              {dashboard.delinquency_rate.toFixed(3)}%
            </p>
            <p className="text-xs text-gray-400 mt-1">총 {fmtAmt(dashboard.total_delinquent)}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            {/* 감독규정상 NPL 은 '고정이하여신비율'이라 자산건전성 화면의 값(고정+회수의문+
                추정손실 기준)이 정식 정의다. 여기 값은 연체일수 기준이라 숫자가 달라
                같은 이름을 쓰면 혼선이 생긴다. 지표 이름을 정의대로 적는다. */}
            <p className="text-xs text-gray-500 mb-1">91일+ 연체비율</p>
            <p className={`text-2xl font-bold ${dashboard.npl_ratio > 1 ? 'text-red-600' : 'text-gray-900'}`}>
              {dashboard.npl_ratio.toFixed(3)}%
            </p>
            <p className="text-xs text-gray-400 mt-1">연체일수 기준 · NPL은 자산건전성 참조</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">7일 신규 연체</p>
            <p className="text-2xl font-bold text-orange-600">{dashboard.new_7days.count}건</p>
            <p className="text-xs text-gray-400 mt-1">{fmtAmt(dashboard.new_7days.amount)}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">총 여신 잔액</p>
            <p className="text-2xl font-bold text-gray-900">{fmtAmt(dashboard.total_outstanding)}</p>
          </div>
        </div>
      )}

      {/* 탭 */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="border-b border-gray-200 px-6">
          <nav className="flex gap-6">
            {[
              { key: 'dashboard',   label: '버킷 현황',   icon: <Activity size={14} /> },
              { key: 'list',        label: '연체 목록',   icon: <AlertCircle size={14} /> },
              { key: 'rollrate',    label: 'Roll Rate',   icon: <TrendingDown size={14} /> },
              { key: 'performance', label: '추심 성과',   icon: <PhoneCall size={14} /> },
            ].map(({ key, label, icon }) => (
              <button
                key={key}
                onClick={() => handleTabChange(key as typeof tab)}
                className={`flex items-center gap-1.5 py-3 text-sm font-medium border-b-2 transition-colors ${
                  tab === key
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {icon}{label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {/* 버킷 현황 탭 */}
          {tab === 'dashboard' && dashboard && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">DPD 버킷별 연체 잔액</h3>
                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={dashboard.buckets}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="label_ko" tick={{ fontSize: 11 }} />
                      <YAxis tickFormatter={(v) => `${(v / 100000000).toFixed(0)}억`} tick={{ fontSize: 11 }} />
                      <Tooltip formatter={(v: number) => fmtAmt(v)} />
                      <Bar dataKey="exposure" name="익스포저" radius={[4,4,0,0]}>
                        {dashboard.buckets.map((entry: any, i: number) => (
                          <Bar key={i} dataKey="exposure" fill={STAGE_COLORS[entry.stage] || '#94a3b8'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">버킷별 상세</h3>
                  <div className="space-y-3">
                    {dashboard.buckets.map((b: any) => (
                      <div key={b.stage} className="flex items-center gap-3">
                        <div className="w-20 text-right">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STAGE_BG[b.stage] || 'bg-gray-100 text-gray-700'}`}>
                            {b.label_ko}
                          </span>
                        </div>
                        <div className="flex-1 bg-gray-100 rounded-full h-3">
                          <div
                            className="h-3 rounded-full"
                            style={{
                              width: `${Math.min((b.exposure / dashboard.total_outstanding) * 100 * 10, 100)}%`,
                              backgroundColor: STAGE_COLORS[b.stage] || '#94a3b8',
                            }}
                          />
                        </div>
                        <span className="text-xs text-gray-600 w-20 text-right">{b.count}건 / {fmtAmt(b.overdue_amt)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 연체 목록 탭 */}
          {tab === 'list' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <select
                  value={filterStage}
                  onChange={(e) => {
                    setFilterStage(e.target.value);
                    loadList(e.target.value);
                  }}
                  className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-700"
                >
                  <option value="">전체 단계</option>
                  {['EARLY', 'MID', 'LATE', 'NPL', 'WRITEOFF'].map((s) => (
                    <option key={s} value={s}>
                      {s === 'EARLY' ? '초기(1-30일)' : s === 'MID' ? '중기(31-60일)' :
                       s === 'LATE' ? '장기(61-90일)' : s === 'NPL' ? 'NPL(91-180일)' : '상각대상(181일+)'}
                    </option>
                  ))}
                </select>
                <span className="text-sm text-gray-500">{items.length}건</span>
              </div>

              <div className="space-y-2">
                {items.map((item) => (
                  <div key={item.delinquency_id} className="border border-gray-200 rounded-lg overflow-hidden">
                    <div
                      className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-50"
                      onClick={() => handleExpandRow(item.delinquency_id, item.facility_id)}
                    >
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STAGE_BG[item.stage] || ''}`}>
                          {item.stage_label}
                        </span>
                        <span className="font-medium text-gray-800">{item.company_name}</span>
                        <span className="text-xs text-gray-500">등급: {item.credit_grade}</span>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-gray-600">
                        <span>DPD <strong>{item.dpd}</strong>일</span>
                        <span>연체액 <strong>{fmtAmt(item.overdue_amount)}</strong></span>
                        <span>연체일 {item.overdue_date}</span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setActivityModal({
                              open: true,
                              delinquencyId: item.delinquency_id,
                              facilityId: item.facility_id,
                              companyName: item.company_name,
                            });
                          }}
                          className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 border border-blue-200 rounded px-2 py-1"
                        >
                          <Plus size={12} />추심 기록
                        </button>
                        {expandedId === item.delinquency_id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </div>
                    </div>

                    {expandedId === item.delinquency_id && expandedDetail && (
                      <div className="border-t border-gray-100 bg-gray-50 p-4">
                        {expandedDetail.delinquencies?.map((d: any) => (
                          <div key={d.delinquency_id} className="mb-3">
                            <div className="text-xs font-semibold text-gray-600 mb-2">추심 활동 이력</div>
                            {d.activities.length === 0 ? (
                              <p className="text-xs text-gray-400">추심 활동 없음</p>
                            ) : (
                              <div className="space-y-1.5">
                                {d.activities.map((a: any, i: number) => (
                                  <div key={i} className="flex items-center gap-3 text-xs bg-white rounded-lg border border-gray-100 px-3 py-2">
                                    <span className="text-gray-400">{ACTIVITY_ICONS[a.type] || <Activity size={14} />}</span>
                                    <span className="font-medium text-gray-700">{a.type}</span>
                                    <span className={`px-1.5 py-0.5 rounded text-xs ${
                                      a.result === 'PROMISE_TO_PAY' ? 'bg-green-100 text-green-700' :
                                      a.result === 'REACHED' ? 'bg-blue-100 text-blue-700' :
                                      'bg-gray-100 text-gray-600'
                                    }`}>{a.result}</span>
                                    <span className="text-gray-500">{a.date}</span>
                                    {a.notes && <span className="text-gray-500 truncate max-w-xs">{a.notes}</span>}
                                    <span className="ml-auto text-gray-400">{a.officer}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                {items.length === 0 && (
                  <div className="text-center py-12 text-gray-400">연체 데이터가 없습니다</div>
                )}
              </div>
            </div>
          )}

          {/* Roll Rate 탭 */}
          {tab === 'rollrate' && (
            <div>
              {rollRate.length === 0 ? (
                <div className="text-center py-12 text-gray-400">Roll Rate 데이터 로딩 중...</div>
              ) : (
                <div>
                  <p className="text-sm text-gray-500 mb-4">
                    각 연체 단계에서 다음 기간(30일 내)에 이동한 비율
                  </p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs border-collapse">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="border border-gray-200 px-3 py-2 text-left font-medium text-gray-600">단계</th>
                          <th className="border border-gray-200 px-3 py-2 text-center">초기</th>
                          <th className="border border-gray-200 px-3 py-2 text-center">중기</th>
                          <th className="border border-gray-200 px-3 py-2 text-center">장기</th>
                          <th className="border border-gray-200 px-3 py-2 text-center">NPL</th>
                          <th className="border border-gray-200 px-3 py-2 text-center">상각</th>
                          <th className="border border-gray-200 px-3 py-2 text-center">정상화</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rollRate.map((row: any) => (
                          <tr key={row.from_stage} className="hover:bg-gray-50">
                            <td className="border border-gray-200 px-3 py-2 font-medium"
                              style={{ color: STAGE_COLORS[row.from_stage] }}>
                              {row.from_label}
                            </td>
                            {['early', 'mid', 'late', 'npl', 'writeoff', 'cured'].map((s) => {
                              const rate = row[`to_${s}_rate`] || 0;
                              return (
                                <td key={s} className={`border border-gray-200 px-3 py-2 text-center ${
                                  rate > 30 ? 'bg-red-50 text-red-700 font-medium' :
                                  rate > 10 ? 'bg-orange-50 text-orange-700' :
                                  rate > 0  ? 'text-gray-700' : 'text-gray-300'
                                }`}>
                                  {rate > 0 ? `${rate}%` : '-'}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 추심 성과 탭 */}
          {tab === 'performance' && (
            <div>
              {!performance ? (
                <div className="text-center py-12 text-gray-400">로딩 중...</div>
              ) : (
                <div className="space-y-6">
                  {/* 회수 요약 */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <p className="text-xs text-gray-500">총 연체 원금</p>
                      <p className="text-xl font-bold text-gray-900 mt-1">
                        {fmtAmt(performance.recovery_summary.total_original)}
                      </p>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <p className="text-xs text-gray-500">총 회수액</p>
                      <p className="text-xl font-bold text-green-600 mt-1">
                        {fmtAmt(performance.recovery_summary.total_recovered)}
                      </p>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <p className="text-xs text-gray-500">전체 회수율</p>
                      <p className="text-xl font-bold text-blue-600 mt-1">
                        {performance.recovery_summary.overall_recovery_rate.toFixed(1)}%
                      </p>
                    </div>
                  </div>

                  {/* 활동 유형별 성과 */}
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">활동 유형별 접촉 성과</h3>
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-200 text-left">
                          <th className="pb-2 text-gray-500 font-medium">활동 유형</th>
                          <th className="pb-2 text-right text-gray-500 font-medium">총 건수</th>
                          <th className="pb-2 text-right text-gray-500 font-medium">접촉 성공률</th>
                          <th className="pb-2 text-right text-gray-500 font-medium">상환 약속률</th>
                          <th className="pb-2 text-right text-gray-500 font-medium">약속 금액</th>
                        </tr>
                      </thead>
                      <tbody>
                        {performance.by_activity_type.map((row: any, i: number) => (
                          <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                            <td className="py-2 flex items-center gap-2">
                              <span className="text-gray-400">{ACTIVITY_ICONS[row.activity_type] || <Activity size={14} />}</span>
                              <span className="text-gray-800 font-medium">{row.activity_type}</span>
                            </td>
                            <td className="py-2 text-right text-gray-700">{row.total}</td>
                            <td className="py-2 text-right">
                              <span className={`font-medium ${row.reached_rate > 50 ? 'text-green-600' : 'text-gray-700'}`}>
                                {row.reached_rate}%
                              </span>
                            </td>
                            <td className="py-2 text-right">
                              <span className={`font-medium ${row.promise_rate > 20 ? 'text-blue-600' : 'text-gray-700'}`}>
                                {row.promise_rate}%
                              </span>
                            </td>
                            <td className="py-2 text-right text-gray-700">{fmtAmt(row.total_promised)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 추심 활동 기록 모달 */}
      {activityModal.open && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 mb-1">추심 활동 기록</h3>
            <p className="text-sm text-gray-500 mb-4">{activityModal.companyName}</p>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-500 font-medium">활동 유형</label>
                <select
                  value={activityForm.type}
                  onChange={(e) => setActivityForm({ ...activityForm, type: e.target.value })}
                  className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                >
                  {['CALL', 'SMS', 'EMAIL', 'LETTER', 'VISIT', 'LEGAL_NOTICE'].map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500 font-medium">접촉 결과</label>
                <select
                  value={activityForm.result}
                  onChange={(e) => setActivityForm({ ...activityForm, result: e.target.value })}
                  className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                >
                  {['REACHED', 'NO_ANSWER', 'PROMISE_TO_PAY', 'REFUSED', 'LEFT_MESSAGE'].map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500 font-medium">메모</label>
                <textarea
                  value={activityForm.notes}
                  onChange={(e) => setActivityForm({ ...activityForm, notes: e.target.value })}
                  rows={2}
                  className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  placeholder="추심 활동 내용 기록..."
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 font-medium">담당자</label>
                <input
                  value={activityForm.officer}
                  onChange={(e) => setActivityForm({ ...activityForm, officer: e.target.value })}
                  className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setActivityModal({ ...activityModal, open: false })}
                className="flex-1 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 hover:bg-gray-50"
              >
                취소
              </button>
              <button
                onClick={handleRecordActivity}
                className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
              >
                기록
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
