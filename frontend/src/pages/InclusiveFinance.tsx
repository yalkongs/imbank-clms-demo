import React, { useEffect, useState } from 'react';
import { HeartHandshake, TrendingUp, AlertTriangle, Store, LifeBuoy } from 'lucide-react';
import { Card, StatCard, Badge } from '../components';
import { TrendChart, GroupedBarChart, COLORS } from '../components/Charts';
import { formatAmount, formatPercent, formatNumber } from '../utils/format';
import axios from 'axios';

/**
 * 포용금융 이행 현황
 *
 * iM뱅크는 시중은행 전환 인가(2024.5) 시 중신용 중소기업·개인사업자 여신 확대를
 * 공언했다. 이 화면의 목적은 그 이행 실적과 그 여신의 건전성을 한 화면에서 보는 것 -
 * 공급만 보면 부실을 놓치고, 건전성만 보면 인가 조건 미이행을 놓친다.
 */

interface SegmentStat {
  count: number;
  exposure: number;
  delinquency_rate: number;
  npl_ratio: number;
  share: number;
  target_share: number;
  achievement: number;
}

export default function InclusiveFinance() {
  const [summary, setSummary] = useState<any>(null);
  const [trend, setTrend] = useState<any[]>([]);
  const [breakdown, setBreakdown] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  // P4: 개인사업자 건전성 심화
  const [sohoDeep, setSohoDeep] = useState<any>(null);
  const [candidates, setCandidates] = useState<any>(null);
  const [referring, setReferring] = useState<string | null>(null);
  const [referMsg, setReferMsg] = useState<string | null>(null);

  const loadCandidates = () =>
    axios.get('/api/inclusive/soho/restructuring-candidates')
      .then(r => setCandidates(r.data)).catch(console.error);

  useEffect(() => {
    Promise.all([
      axios.get('/api/inclusive/summary'),
      axios.get('/api/inclusive/trend?months=12'),
      axios.get('/api/inclusive/breakdown'),
      axios.get('/api/inclusive/soho/dashboard'),
    ])
      .then(([s, t, b, sd]) => {
        setSummary(s.data);
        setTrend(t.data.map((r: any) => ({
          period: r.month,
          mid_credit: Math.round(r.mid_credit / 1e8),
          soho: Math.round(r.soho / 1e8),
        })));
        setBreakdown(b.data);
        setSohoDeep(sd.data);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
    loadCandidates();
  }, []);

  const refer = (c: any) => {
    setReferring(c.customer_id);
    setReferMsg(null);
    axios.post('/api/inclusive/soho/restructuring-referral', null, {
      params: { customer_id: c.customer_id, track: c.recommended_track },
    })
      .then(r => {
        setReferMsg(`${r.data.customer_name} → ${r.data.track} 연계 등록 (감사기록 완료)`);
        loadCandidates();
      })
      .catch(e => setReferMsg(e?.response?.data?.detail || '등록 실패 - 팀장 이상 로그인이 필요합니다'))
      .finally(() => setReferring(null));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const mid: SegmentStat = summary?.segments?.MID_CREDIT || {};
  const soho: SegmentStat = summary?.segments?.SOHO || {};

  const AchievementBar = ({ seg, label }: { seg: SegmentStat; label: string }) => {
    const pct = Math.min(seg.achievement || 0, 100);
    const behind = (seg.achievement || 0) < 100;
    return (
      <div>
        <div className="flex items-center justify-between text-sm mb-1">
          <span className="font-medium text-gray-700">{label}</span>
          <span className={`font-bold tabular ${behind ? 'text-amber-600' : 'text-green-600'}`}>
            목표 대비 {formatPercent(seg.achievement || 0)}
          </span>
        </div>
        <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full ${behind ? 'bg-amber-400' : 'bg-blue-500'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>현재 비중 {formatPercent(seg.share || 0)}</span>
          <span>목표 {formatPercent(seg.target_share || 0)}</span>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">포용금융 이행 현황</h1>
          <p className="text-sm text-gray-500 mt-1">
            시중은행 전환 인가 시 공언한 중신용·개인사업자 여신 확대 - 공급 실적과 건전성을 함께 관리
          </p>
        </div>
        <a href="/api/export/inclusive.csv" download
           className="flex items-center gap-1.5 px-3 py-1.5 text-xs border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-600 whitespace-nowrap">
          ⬇ CSV 내려받기
        </a>
      </div>

      {/* 핵심 지표: 공급(왼쪽 2개) + 건전성(오른쪽 2개) */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="중신용 기업여신"
          value={formatAmount(mid.exposure || 0, 'billion')}
          subtitle={`${formatNumber(mid.count || 0)}건 · 비중 ${formatPercent(mid.share || 0)}`}
          icon={<HeartHandshake size={24} />}
          color="blue"
        />
        <StatCard
          title="개인사업자 여신"
          value={formatAmount(soho.exposure || 0, 'billion')}
          subtitle={`${formatNumber(soho.count || 0)}건 · 비중 ${formatPercent(soho.share || 0)}`}
          icon={<Store size={24} />}
          color="blue"
        />
        <StatCard
          title="중신용 연체율"
          value={formatPercent(mid.delinquency_rate || 0)}
          subtitle={`전체 ${formatPercent(summary?.total_delinquency_rate || 0)} 대비`}
          icon={<AlertTriangle size={24} />}
          color={(mid.delinquency_rate || 0) > (summary?.total_delinquency_rate || 0) * 1.5 ? 'red' : 'yellow'}
        />
        <StatCard
          title="개인사업자 연체율"
          value={formatPercent(soho.delinquency_rate || 0)}
          subtitle={`NPL ${formatPercent(soho.npl_ratio || 0)}`}
          icon={<TrendingUp size={24} />}
          color={(soho.delinquency_rate || 0) > (summary?.total_delinquency_rate || 0) * 1.5 ? 'red' : 'yellow'}
        />
      </div>

      {/* 목표 달성률 */}
      <Card title="인가 공언 목표 대비 달성률">
        <div className="grid grid-cols-2 gap-8 py-2">
          <AchievementBar seg={mid} label="중신용 기업 (BBB+ 이하)" />
          <AchievementBar seg={soho} label="개인사업자 (SOHO)" />
        </div>
        <p className="text-xs text-gray-400 mt-3">{summary?.note}</p>
      </Card>

      <div className="grid grid-cols-3 gap-6">
        {/* 월별 신규취급 추이 */}
        <Card title="월별 신규취급액 추이 (억원)" className="col-span-2">
          <TrendChart
            data={trend}
            lines={[
              { key: 'mid_credit', name: '중신용', color: COLORS.primary },
              { key: 'soho', name: '개인사업자', color: COLORS.accent },
            ]}
            height={260}
          />
        </Card>

        {/* 지역별 분포 - 어디서 공급되고 어디가 부실한가 */}
        <Card title="지역별 포용금융 현황">
          <div className="space-y-3">
            {(breakdown?.by_region || []).map((r: any) => (
              <div key={r.region} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-gray-900">{r.region_label}</p>
                  <p className="text-xs text-gray-500">{formatNumber(r.count)}건</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold tabular">{formatAmount(r.exposure, 'billion')}</p>
                  <p className={`text-xs ${r.delinquency_rate > 1.5 ? 'text-red-500' : 'text-gray-500'}`}>
                    연체율 {formatPercent(r.delinquency_rate)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* 중신용 등급 분포 */}
      <Card title="중신용 세그먼트 등급별 익스포저 (억원)">
        <GroupedBarChart
          data={(breakdown?.by_grade || []).map((g: any) => ({
            name: g.grade,
            exposure: Math.round(g.exposure / 1e8),
          }))}
          bars={[{ key: 'exposure', name: '익스포저', color: COLORS.primary }]}
          height={220}
        />
      </Card>

      {/* ── P4: 개인사업자 건전성 심화 ─────────────────────────── */}
      <div className="flex items-start justify-between pt-2">
        <div>
          <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <LifeBuoy size={20} className="text-[#00897B]" />
            개인사업자 건전성 심화
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            업권 개인사업자 연체율 상승(0.84%, 2026.5) 국면 - 새출발기금 연계·자체 프리워크아웃 관리
          </p>
        </div>
        {sohoDeep && (
          <span className="px-2.5 py-1 bg-amber-50 text-amber-700 text-xs rounded-full font-medium border border-amber-200">
            새출발기금 {sohoDeep.benchmark.policy.deadline}까지 · 한도 {sohoDeep.benchmark.policy.debt_cap_eok}억
          </span>
        )}
      </div>

      {sohoDeep && (
        <div className="grid grid-cols-3 gap-6">
          <Card title="SOHO 연체 버킷 (DPD)" subtitle="익스포저 기준 (억원)">
            <GroupedBarChart
              data={sohoDeep.dpd_buckets.filter((b: any) => b.bucket !== '정상').map((b: any) => ({
                name: b.bucket,
                exposure: b.exposure_eok,
              }))}
              bars={[{ key: 'exposure', name: '연체 익스포저', color: COLORS.warning }]}
              height={200}
            />
            <p className="text-[11px] text-gray-400 mt-2">
              정상 {formatNumber(sohoDeep.dpd_buckets[0]?.count || 0)}건 ·{' '}
              {formatNumber(sohoDeep.dpd_buckets[0]?.exposure_eok || 0)}억 제외 표시
            </p>
          </Card>

          <Card title="SOHO 업종×지역 히트맵" className="col-span-2"
            subtitle="셀 색상 = 연체율 · 값 = 익스포저(억)" noPadding>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                    <th className="py-2 px-4">업종</th>
                    <th className="py-2 px-3 text-right">대구·경북</th>
                    <th className="py-2 px-3 text-right">수도권</th>
                    <th className="py-2 px-3 text-right">부산·경남</th>
                  </tr>
                </thead>
                <tbody>
                  {sohoDeep.matrix.slice(0, 7).map((row: any) => (
                    <tr key={row.industry} className="border-b border-gray-50">
                      <td className="py-1.5 px-4 font-medium text-gray-900">{row.industry}</td>
                      {['DAEGU_GB', 'CAPITAL', 'BUSAN_GN'].map(rk => {
                        const cell = row.cells[rk] || { exposure_eok: 0, delinquency_rate: 0 };
                        const heat = cell.delinquency_rate >= 3 ? 'bg-red-100 text-red-700'
                          : cell.delinquency_rate >= 1.5 ? 'bg-amber-100 text-amber-700'
                          : cell.delinquency_rate > 0 ? 'bg-yellow-50 text-yellow-700'
                          : 'bg-emerald-50 text-emerald-700';
                        return (
                          <td key={rk} className="py-1 px-2 text-right">
                            <span className={`inline-block px-2 py-0.5 rounded tabular ${heat}`}>
                              {formatNumber(cell.exposure_eok)}
                              <span className="text-[10px] ml-1 opacity-70">{formatPercent(cell.delinquency_rate, 1)}</span>
                            </span>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {candidates && (
        <Card title="채무조정 연계 후보"
          subtitle={`부실차주 ${candidates.summary.npl} · 부실우려 ${candidates.summary.at_risk} · EWS 선제 ${candidates.summary.preemptive} - 새출발기금 요건 자동 매칭`}
          noPadding>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                  <th className="py-2 px-4">고객</th>
                  <th className="py-2 px-3">업종 / 지역</th>
                  <th className="py-2 px-3 text-right">여신 (억)</th>
                  <th className="py-2 px-3 text-right">DPD</th>
                  <th className="py-2 px-3 text-right">EWS</th>
                  <th className="py-2 px-3 text-center">구분</th>
                  <th className="py-2 px-3">권고 트랙</th>
                  <th className="py-2 px-4 text-center">조치</th>
                </tr>
              </thead>
              <tbody>
                {candidates.candidates.slice(0, 10).map((c: any) => (
                  <tr key={c.customer_id} className="border-b border-gray-50">
                    <td className="py-2 px-4 font-medium text-gray-900">{c.customer_name}</td>
                    <td className="py-2 px-3 text-gray-500 text-xs">{c.industry} / {c.region === 'DAEGU_GB' ? '대구경북' : c.region === 'CAPITAL' ? '수도권' : '부산경남'}</td>
                    <td className="py-2 px-3 text-right tabular">{formatNumber(c.exposure_eok)}</td>
                    <td className={`py-2 px-3 text-right tabular font-semibold ${c.max_dpd >= 90 ? 'text-red-500' : c.max_dpd >= 30 ? 'text-amber-600' : 'text-gray-600'}`}>
                      {c.max_dpd}일
                    </td>
                    <td className="py-2 px-3 text-right tabular">{c.ews_score ?? '-'}</td>
                    <td className="py-2 px-3 text-center">
                      <Badge variant={c.category === '부실차주' ? 'danger' : c.category === '부실우려차주' ? 'warning' : 'info'}>
                        {c.category}
                      </Badge>
                    </td>
                    <td className="py-2 px-3 text-xs text-gray-600">{c.recommended_track}</td>
                    <td className="py-2 px-4 text-center">
                      {c.already_referred ? (
                        <Badge variant="success">등록됨</Badge>
                      ) : (
                        <button onClick={() => refer(c)} disabled={referring === c.customer_id}
                          className="px-2.5 py-1 text-xs font-medium bg-[#00897B] text-white rounded-lg hover:bg-[#00695F] disabled:opacity-50">
                          {referring === c.customer_id ? '등록 중' : '연계 등록'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-3 flex items-center justify-between">
            <p className="text-[11px] text-gray-400">
              {candidates.policy.note} · 연계 등록은 팀장 이상 전결 + 감사기록 (자동화 파이프라인으로 추적)
            </p>
            {referMsg && <p className="text-xs font-medium text-[#00897B]">{referMsg}</p>}
          </div>
        </Card>
      )}
    </div>
  );
}
