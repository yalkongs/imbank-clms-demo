import React, { useEffect, useState } from 'react';
import { HeartHandshake, TrendingUp, AlertTriangle, Store } from 'lucide-react';
import { Card, StatCard } from '../components';
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

  useEffect(() => {
    Promise.all([
      axios.get('/api/inclusive/summary'),
      axios.get('/api/inclusive/trend?months=12'),
      axios.get('/api/inclusive/breakdown'),
    ])
      .then(([s, t, b]) => {
        setSummary(s.data);
        setTrend(t.data.map((r: any) => ({
          period: r.month,
          mid_credit: Math.round(r.mid_credit / 1e8),
          soho: Math.round(r.soho / 1e8),
        })));
        setBreakdown(b.data);
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
    </div>
  );
}
