import React, { useEffect, useRef, useState } from 'react';
import { PiggyBank, Target, Layers, ArrowRightLeft } from 'lucide-react';
import { Card, StatCard, Badge } from '../components';
import { TrendChart, COLORS } from '../components/Charts';
import { formatNumber, formatPercent } from '../utils/format';
import axios from 'axios';

/**
 * CET1 경로 관리 (P2)
 *
 * CFO가 공언한 밸류업 1차 목표 CET1 12.3%를 규제 일정 위에서 관리한다.
 * - output floor 경과규정: 65%(2026) → 70%(2027) → 72.5%(2028)
 * - 생산적 금융 위험가중치 시나리오 (주담대 상향·주식 인하)는 시나리오
 *   입력으로만 - 가계여신 기능을 만드는 것이 아니다.
 * - RAROC 리밸런싱 후보는 기존 자본최적화 모듈을 재사용한다.
 */

export default function CET1Path() {
  const [proj, setProj] = useState<any>(null);
  const [rw, setRw] = useState<any>(null);
  const [rebal, setRebal] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  // 경로 레버
  const [growth, setGrowth] = useState(4);
  const [payout, setPayout] = useState(30);
  const [saMult, setSaMult] = useState(1.45);
  // RW 시나리오 레버
  const [rwTo, setRwTo] = useState(25);
  const [equityRelief, setEquityRelief] = useState(5000);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    axios.get('/api/capital-optimizer/rebalancing-suggestions')
      .then(r => setRebal(r.data.rebalancing_actions || []))
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (debounce.current) clearTimeout(debounce.current);
    debounce.current = setTimeout(() => {
      Promise.all([
        axios.get('/api/cet1-path/projection', {
          params: { asset_growth: growth, payout_ratio: payout, sa_multiplier: saMult },
        }),
        axios.get('/api/cet1-path/rw-scenario', {
          params: { mortgage_rw_to: rwTo, equity_rwa_relief_eok: equityRelief },
        }),
      ])
        .then(([p, r]) => { setProj(p.data); setRw(r.data); })
        .catch(console.error)
        .finally(() => setLoading(false));
    }, 250);
    return () => { if (debounce.current) clearTimeout(debounce.current); };
  }, [growth, payout, saMult, rwTo, equityRelief]);

  if (loading || !proj) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const pos = proj.position;
  const t = proj.targets;
  const path = proj.path;
  const last = path[path.length - 1];

  const chartData = path.map((p: any) => ({
    year: String(p.year),
    'CET1 비율': p.cet1_ratio,
  }));

  const Lever = ({ label, value, onChange, min, max, step, unit, decimals = 0 }: any) => (
    <div>
      <div className="flex items-center justify-between text-sm mb-1">
        <span className="font-medium text-gray-700">{label}</span>
        <span className="font-bold tabular text-gray-900">{value.toFixed(decimals)}{unit}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full accent-[#00897B]" />
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">CET1 경로 관리</h1>
          <p className="text-sm text-gray-500 mt-1">
            밸류업 1차 목표 12.3%를 output floor 단계 상향(65→72.5%) 일정 위에서 관리 (CFO 공언 목표)
          </p>
        </div>
        <span className="px-2.5 py-1 bg-amber-50 text-amber-700 text-xs rounded-full font-medium border border-amber-200">
          floor 일정은 확정 경과규정 · 성장률·SA배수는 가정
        </span>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="현재 CET1 (데모 실측)"
          value={formatPercent(pos.cet1_ratio, 2)}
          subtitle={`지주 공시 ${formatPercent(t.disclosed_group_cet1, 2)} (2026.6말)`}
          icon={<PiggyBank size={24} />}
          color="blue"
        />
        <StatCard
          title="밸류업 1차 목표"
          value={formatPercent(t.valueup_cet1, 1)}
          subtitle="조기 달성 → 연말까지 안정 관리"
          icon={<Target size={24} />}
          color="green"
        />
        <StatCard
          title="2028 output floor"
          value="72.5%"
          subtitle={`floor 추가 RWA ${formatNumber(last.floor_addon_rwa_eok)}억 (2028)`}
          icon={<Layers size={24} />}
          color={last.floor_binding ? 'yellow' : 'gray'}
        />
        <StatCard
          title="2028 전망 CET1"
          value={formatPercent(last.cet1_ratio, 2)}
          subtitle={last.meets_target ? '목표 유지' : `RWA ${formatNumber(last.rwa_cut_needed_eok)}억 감축 필요`}
          icon={<ArrowRightLeft size={24} />}
          color={last.meets_target ? 'green' : 'red'}
        />
      </div>

      <div className="grid grid-cols-3 gap-6">
        <Card title="연도별 CET1 경로" className="col-span-2"
          subtitle="output floor 단계 상향 반영 (신용 RWA 에 max(IRB, floor%×SA) 적용)">
          <TrendChart
            data={chartData}
            xAxisKey="year"
            lines={[{ key: 'CET1 비율', name: 'CET1 비율 (%)', color: COLORS.secondary }]}
            referenceLines={[
              { y: t.valueup_cet1, label: '밸류업 목표 12.3%', color: COLORS.success },
              { y: proj.requirement_bands.with_scb_assumed, label: '규제최저+SCB(가정) 9.0%', color: COLORS.warning },
            ]}
            height={260}
          />
          <div className="overflow-x-auto mt-3">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                  <th className="py-2 pr-3">연도</th>
                  <th className="py-2 px-3 text-right">floor</th>
                  <th className="py-2 px-3 text-center">floor 적용</th>
                  <th className="py-2 px-3 text-right">추가 RWA (억)</th>
                  <th className="py-2 px-3 text-right">총 RWA (억)</th>
                  <th className="py-2 px-3 text-right">CET1 (억)</th>
                  <th className="py-2 pl-3 text-right">CET1 비율</th>
                </tr>
              </thead>
              <tbody>
                {path.map((p: any) => (
                  <tr key={p.year} className="border-b border-gray-50">
                    <td className="py-2 pr-3 font-medium">{p.year}</td>
                    <td className="py-2 px-3 text-right tabular">{p.floor_pct}%</td>
                    <td className="py-2 px-3 text-center">
                      <Badge variant={p.floor_binding ? 'warning' : 'gray'}>
                        {p.floor_binding ? '물림' : '미적용'}
                      </Badge>
                    </td>
                    <td className="py-2 px-3 text-right tabular">{formatNumber(p.floor_addon_rwa_eok)}</td>
                    <td className="py-2 px-3 text-right tabular">{formatNumber(p.total_rwa_eok)}</td>
                    <td className="py-2 px-3 text-right tabular">{formatNumber(p.cet1_capital_eok)}</td>
                    <td className={`py-2 pl-3 text-right tabular font-semibold ${p.meets_target ? 'text-green-600' : 'text-red-500'}`}>
                      {formatPercent(p.cet1_ratio, 2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="정책 레버" subtitle="조정 즉시 경로 재계산">
          <div className="space-y-5">
            <Lever label="연 자산 성장률" value={growth} onChange={setGrowth}
              min={0} max={10} step={0.5} unit="%" decimals={1} />
            <Lever label="배당성향" value={payout} onChange={setPayout}
              min={0} max={50} step={5} unit="%" />
            <Lever label="SA/IRB 배수 (표준방법 RWA)" value={saMult} onChange={setSaMult}
              min={1.2} max={1.7} step={0.05} unit="배" decimals={2} />
            <p className="text-[11px] text-gray-400 leading-relaxed pt-2 border-t border-gray-100">
              중소기업 위주 포트폴리오는 SA/IRB 배수가 1.4~1.6에 분포 - 배수가
              클수록 2027~28년 floor 가 강하게 물린다. 이자이익 성장(성장률↑)과
              RWA 통제(floor 압박)의 상충이 이 화면의 관리 대상이다.
            </p>
            <div className="pt-2 border-t border-gray-100 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">규제최저 (CCyB 1% 포함)</span>
                <span className="font-bold tabular">{formatPercent(proj.requirement_bands.regulatory_min, 1)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">+ SCB 시행 시 (가정 1.0%p)</span>
                <span className="font-bold tabular text-amber-600">{formatPercent(proj.requirement_bands.with_scb_assumed, 1)}</span>
              </div>
              <p className="text-[11px] text-gray-400">{proj.requirement_bands.scb_note}</p>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* 생산적 금융 RW 시나리오 */}
        <Card title="생산적 금융 위험가중치 시나리오"
          subtitle="주담대 상향 발표(15→20%)·25% 검토 - 시행 미확인, 가정 입력">
          <div className="space-y-4">
            <div>
              <p className="text-sm font-medium text-gray-700 mb-1.5">주담대 RW 하한</p>
              <div className="flex gap-2">
                {[20, 25].map(v => (
                  <button key={v} onClick={() => setRwTo(v)}
                    className={`flex-1 py-1.5 text-sm rounded-lg border font-medium ${
                      rwTo === v ? 'bg-[#00897B] text-white border-[#00897B]' : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                    }`}>
                    20% → {v}%{v === 25 ? ' (검토)' : ''}
                  </button>
                ))}
              </div>
            </div>
            <Lever label="주식 RW 인하 등 완화 효과" value={equityRelief} onChange={setEquityRelief}
              min={0} max={20000} step={1000} unit="억 RWA" />
            {rw && (
              <div className="pt-3 border-t border-gray-100 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">순 RWA 효과</span>
                  <span className={`font-bold tabular ${rw.scenario.net_rwa_delta_eok > 0 ? 'text-red-500' : 'text-green-600'}`}>
                    {rw.scenario.net_rwa_delta_eok > 0 ? '+' : ''}{formatNumber(rw.scenario.net_rwa_delta_eok)}억
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">시나리오 후 CET1</span>
                  <span className="font-bold tabular">{formatPercent(rw.scenario.cet1_ratio_after, 2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">기업여신 여력 환산</span>
                  <span className="font-bold tabular text-[#00897B]">{formatNumber(rw.scenario.corporate_capacity_eok)}억</span>
                </div>
                <p className="text-[11px] text-gray-400 leading-relaxed">{rw.policy_note}</p>
              </div>
            )}
          </div>
        </Card>

        {/* RAROC 리밸런싱 후보 (기존 자본최적화 재사용) */}
        <Card title="RAROC 기준 리밸런싱 후보" className="col-span-2"
          subtitle="자본최적화 모듈 연동 - RWA 감축·증액의 업종별 우선순위" noPadding>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                  <th className="py-2 px-4">업종</th>
                  <th className="py-2 px-3 text-right">익스포저 (억)</th>
                  <th className="py-2 px-3 text-right">집중도</th>
                  <th className="py-2 px-3 text-right">RWA 밀도</th>
                  <th className="py-2 px-3 text-right">RAROC</th>
                  <th className="py-2 px-3 text-center">전략</th>
                  <th className="py-2 px-4 text-center">우선순위</th>
                </tr>
              </thead>
              <tbody>
                {rebal.slice(0, 6).map((a: any) => (
                  <tr key={a.industry_code} className="border-b border-gray-50">
                    <td className="py-2 px-4 font-medium text-gray-900">{a.industry}</td>
                    <td className="py-2 px-3 text-right tabular">{formatNumber(Math.round(a.current_exposure / 1e8))}</td>
                    <td className="py-2 px-3 text-right tabular">{formatPercent(a.concentration, 1)}</td>
                    <td className="py-2 px-3 text-right tabular">{formatPercent(a.rwa_density, 1)}</td>
                    <td className={`py-2 px-3 text-right tabular font-semibold ${a.raroc >= 15 ? 'text-green-600' : 'text-red-500'}`}>
                      {formatPercent(a.raroc, 1)}
                    </td>
                    <td className="py-2 px-3 text-center">
                      <Badge variant={a.strategy === 'REDUCE' ? 'danger' : a.strategy === 'EXPAND' ? 'success' : 'gray'}>
                        {a.strategy}
                      </Badge>
                    </td>
                    <td className="py-2 px-4 text-center">
                      <Badge variant={a.priority === 'HIGH' ? 'warning' : 'gray'}>{a.priority}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="px-4 py-3 text-[11px] text-gray-400">
            RAROC 허들 15% 미달 업종의 RWA 를 회수해 floor 압박(2027~28)에 대비하고,
            여력은 우량 제조업·수도권 확장(P3 지역 리밸런싱)에 배분한다.
          </p>
        </Card>
      </div>
    </div>
  );
}
