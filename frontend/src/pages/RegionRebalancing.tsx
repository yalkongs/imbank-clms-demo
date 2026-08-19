import React, { useEffect, useState } from 'react';
import { MapPin, TrendingUp, AlertTriangle, Scale } from 'lucide-react';
import { Card, StatCard } from '../components';
import { TrendChart, COLORS } from '../components/Charts';
import { formatNumber, formatPercent } from '../utils/format';
import axios from 'axios';

/**
 * 지역 편중 리스크 · 리밸런싱 관제 (P3)
 *
 * iM뱅크만의 긴장 구조: 시중은행 전환 인가 부대조건(본점 대구 유지)과
 * 지역재투자 평가(최우수)가 요구하는 지역 공급 **의무**, 대구·경북 집중이
 * 만드는 편중 **리스크** - 같은 지표가 두 제약 사이에 있어야 한다.
 */

export default function RegionRebalancing() {
  const [ov, setOv] = useState<any>(null);
  const [matrix, setMatrix] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      axios.get('/api/region-rebalancing/overview'),
      axios.get('/api/region-rebalancing/industry-matrix'),
    ])
      .then(([o, m]) => { setOv(o.data); setMatrix(m.data); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading || !ov) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const daegu = ov.regions.find((r: any) => r.region === 'DAEGU_GB') || {};
  const capital = ov.regions.find((r: any) => r.region === 'CAPITAL') || {};
  const lastTrend = ov.new_business_trend[ov.new_business_trend.length - 1] || {};
  const g = ov.gauge;

  // 양면 밴드 게이지: floor(의무 하한) ~ cap(편중 상한) 사이가 관리 밴드
  const bandMin = 30, bandMax = 80;
  const toPos = (v: number) => ((v - bandMin) / (bandMax - bandMin)) * 100;

  const heatColor = (rate: number) => {
    if (rate >= 2.5) return 'bg-red-100 text-red-700';
    if (rate >= 1.5) return 'bg-amber-100 text-amber-700';
    if (rate >= 0.7) return 'bg-yellow-50 text-yellow-700';
    return 'bg-emerald-50 text-emerald-700';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">지역 편중·리밸런싱 관제</h1>
          <p className="text-sm text-gray-500 mt-1">
            지역 공급 의무(재투자 최우수·본점 대구)와 편중 리스크의 균형 - 전국 우량기업 리밸런싱 진척 관리
          </p>
        </div>
        <span className="px-2.5 py-1 bg-amber-50 text-amber-700 text-xs rounded-full font-medium border border-amber-200">
          공시 대구경북 비중 {ov.benchmark.disclosed_daegu_share} · 데모 포트폴리오 {formatPercent(ov.daegu_share, 1)}
        </span>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="대구·경북 잔액 비중"
          value={formatPercent(daegu.share || 0, 1)}
          subtitle={`${formatNumber(daegu.exposure_eok || 0)}억 · ${formatNumber(daegu.customers || 0)}개사`}
          icon={<MapPin size={24} />}
          color="blue"
        />
        <StatCard
          title="신규취급 중 수도권 (최근월)"
          value={formatPercent(lastTrend.capital_share || 0, 1)}
          subtitle="리밸런싱 진척 - 신규는 이미 수도권 우위"
          icon={<TrendingUp size={24} />}
          color="green"
        />
        <StatCard
          title="지역 HHI"
          value={formatNumber(ov.region_hhi)}
          subtitle="1,800 이상 고집중 - 구조적 편중"
          icon={<Scale size={24} />}
          color={ov.region_hhi > 3000 ? 'red' : 'yellow'}
        />
        <StatCard
          title="대구·경북 연체율"
          value={formatPercent(daegu.delinquency_rate || 0)}
          subtitle={`수도권 ${formatPercent(capital.delinquency_rate || 0)} 대비 열위`}
          icon={<AlertTriangle size={24} />}
          color={(daegu.delinquency_rate || 0) > (capital.delinquency_rate || 0) * 1.5 ? 'red' : 'yellow'}
        />
      </div>

      {/* 양면 게이지: 의무 하한 ↔ 편중 상한 */}
      <Card title="지역 공급 의무 ↔ 편중 리스크 양면 게이지"
        subtitle="지역재투자 하한(의무)과 편중 상한(건전성) 사이가 관리 밴드 - 하한·상한은 내부 정책 가정치">
        <div className="px-4 py-6">
          <div className="relative h-4 rounded-full bg-gray-100">
            {/* 관리 밴드 */}
            <div className="absolute h-full bg-emerald-100 rounded-full"
              style={{ left: `${toPos(g.reinvestment_floor)}%`, width: `${toPos(g.concentration_cap) - toPos(g.reinvestment_floor)}%` }} />
            {/* 하한·상한 눈금 */}
            <div className="absolute top-[-6px] w-0.5 h-7 bg-emerald-600" style={{ left: `${toPos(g.reinvestment_floor)}%` }} />
            <div className="absolute top-[-6px] w-0.5 h-7 bg-red-500" style={{ left: `${toPos(g.concentration_cap)}%` }} />
            {/* 현재 값 */}
            <div className="absolute top-[-10px] -translate-x-1/2" style={{ left: `${toPos(g.value)}%` }}>
              <div className="w-6 h-6 rounded-full bg-[#00897B] border-4 border-white shadow-md" />
            </div>
          </div>
          <div className="relative mt-3 text-xs text-gray-500 h-10">
            <span className="absolute -translate-x-1/2 text-emerald-700 font-medium text-center"
              style={{ left: `${toPos(g.reinvestment_floor)}%` }}>
              재투자 하한<br />{formatPercent(g.reinvestment_floor, 0)}
            </span>
            <span className="absolute -translate-x-1/2 font-bold text-[#00897B] text-center"
              style={{ left: `${toPos(g.value)}%`, top: '-38px' }}>
              현재 {formatPercent(g.value, 1)}
            </span>
            <span className="absolute -translate-x-1/2 text-red-600 font-medium text-center"
              style={{ left: `${toPos(g.concentration_cap)}%` }}>
              편중 상한<br />{formatPercent(g.concentration_cap, 0)}
            </span>
          </div>
          <p className={`text-sm mt-2 font-medium ${g.in_band ? 'text-emerald-600' : 'text-red-500'}`}>
            {g.in_band
              ? '관리 밴드 안 - 의무를 지키면서 편중을 낮추는 리밸런싱 여지가 있습니다'
              : '관리 밴드 이탈 - 재투자 의무 또는 편중 상한 중 하나가 침해되고 있습니다'}
          </p>
        </div>
      </Card>

      <div className="grid grid-cols-3 gap-6">
        <Card title="신규취급 지역 구성 추이 (%)" className="col-span-2"
          subtitle="계약일 기준 12개월 - 잔액보다 앞서 움직이는 리밸런싱의 실측">
          <TrendChart
            data={ov.new_business_trend.map((t: any) => ({
              month: t.month.slice(2),
              '대구·경북': t.daegu_share,
              '수도권': t.capital_share,
              '부산·경남': t.busan_share,
            }))}
            xAxisKey="month"
            lines={[
              { key: '대구·경북', name: '대구·경북', color: COLORS.secondary },
              { key: '수도권', name: '수도권', color: COLORS.warning },
              { key: '부산·경남', name: '부산·경남', color: COLORS.gray },
            ]}
            height={260}
          />
        </Card>

        <Card title="지역별 건전성" subtitle="잔액·연체율·NPL - 편중의 질">
          <div className="space-y-3">
            {ov.regions.map((r: any) => (
              <div key={r.region} className="p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold text-gray-900">{r.label}</p>
                  <p className="text-sm font-bold tabular">{formatPercent(r.share, 1)}</p>
                </div>
                <div className="flex justify-between text-xs text-gray-500 mt-1.5">
                  <span>{formatNumber(r.exposure_eok)}억 · {formatNumber(r.customers)}개사</span>
                  <span className={r.delinquency_rate > 1.5 ? 'text-red-500 font-medium' : ''}>
                    연체 {formatPercent(r.delinquency_rate)} · NPL {formatPercent(r.npl_ratio)}
                  </span>
                </div>
              </div>
            ))}
            <p className="text-[11px] text-gray-400 leading-relaxed">
              편중 그 자체보다 편중의 질이 문제 - 대구·경북 연체율이 수도권의
              2배 수준이면 잔액 리밸런싱은 건전성 관리이기도 하다.
            </p>
          </div>
        </Card>
      </div>

      {/* 산업×지역 매트릭스 */}
      <Card title="산업 × 지역 교차 매트릭스" subtitle="셀 색상 = 연체율 · 값 = 익스포저(억)" noPadding>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                <th className="py-2 px-4">산업</th>
                <th className="py-2 px-3 text-right">합계 (억)</th>
                {Object.values(matrix.regions).map((label: any) => (
                  <th key={label} className="py-2 px-3 text-right">{label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matrix.matrix.map((row: any) => (
                <tr key={row.industry} className="border-b border-gray-50">
                  <td className="py-2 px-4 font-medium text-gray-900">{row.industry}</td>
                  <td className="py-2 px-3 text-right tabular font-semibold">{formatNumber(row.total_eok)}</td>
                  {Object.keys(matrix.regions).map((rk: string) => {
                    const cell = row.cells[rk];
                    return (
                      <td key={rk} className="py-1.5 px-2 text-right">
                        <div className={`inline-block px-2 py-1 rounded tabular ${heatColor(cell.delinquency_rate)}`}>
                          {formatNumber(cell.exposure_eok)}
                          <span className="text-[10px] ml-1 opacity-70">{formatPercent(cell.delinquency_rate, 1)}</span>
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="px-4 py-3 text-[11px] text-gray-400">
          리밸런싱 방향: 연체율 높은 지역×산업 셀(적색)의 만기 도래분을 회수하고,
          수도권 우량 제조업 셀로 신규를 배분한다. CET1 경로(P2)의 RWA 관리와 연동.
        </p>
      </Card>
    </div>
  );
}
