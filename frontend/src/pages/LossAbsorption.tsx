import React, { useEffect, useRef, useState } from 'react';
import { ShieldAlert, TrendingDown, Target, AlertTriangle } from 'lucide-react';
import { Card, StatCard } from '../components';
import { TrendChart, GroupedBarChart, COLORS } from '../components/Charts';
import { formatNumber, formatPercent } from '../utils/format';
import axios from 'axios';

/**
 * 손실흡수력 관리 (P1 - 커버리지 조종석)
 *
 * iM금융 2026.2Q 컨퍼런스콜에서 CRO가 공언한 "NPL커버리지 연말 100% 회복"을
 * 관리하는 화면. 지주 커버리지(대손준비금 제외)는 1Q 93.6% → 2Q 82.2%로
 * 급락했고, 이 화면은 충당금 적립·상각·NPL 매각 세 레버로 연말까지의
 * 커버리지 경로를 설계한다.
 *
 * 초기값은 공시 수치(지주/은행 기준 구분), NPL 절대액은 가정치(조정 가능).
 * 하단 'CLMS 포트폴리오 실측'은 데모 DB 계산으로 공시 벤치마크와 구분한다.
 */

const CLASS_LABEL: Record<string, string> = {
  NORMAL: '정상',
  PRECAUTIONARY: '요주의',
  SUBSTANDARD: '고정',
  DOUBTFUL: '회수의문',
  ESTIMATED_LOSS: '추정손실',
};

export default function LossAbsorption() {
  const [overview, setOverview] = useState<any>(null);
  const [sim, setSim] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  // P7: ECL 전망모형 점검 (FLI)
  const [valReport, setValReport] = useState<any>(null);
  const [overlays, setOverlays] = useState<any>(null);
  const [ovlAmount, setOvlAmount] = useState('');
  const [ovlReason, setOvlReason] = useState('');
  const [ovlDriver, setOvlDriver] = useState('부동산PF');
  const [ovlMsg, setOvlMsg] = useState<string | null>(null);
  const [ovlBusy, setOvlBusy] = useState(false);

  const loadFli = () => Promise.all([
    axios.get('/api/ecl/validation-report'),
    axios.get('/api/ecl/overlays'),
  ]).then(([v, o]) => { setValReport(v.data); setOverlays(o.data); }).catch(console.error);

  const submitOverlay = () => {
    if (!ovlAmount || !ovlReason || ovlReason.length < 5) {
      setOvlMsg('금액과 사유(5자 이상)를 입력하세요');
      return;
    }
    setOvlBusy(true);
    setOvlMsg(null);
    axios.post('/api/ecl/overlay', null, {
      params: { amount_eok: Number(ovlAmount), reason: ovlReason, risk_driver: ovlDriver },
    })
      .then(r => {
        setOvlMsg(`오버레이 ${r.data.amount_eok}억 등록 (재검토 기한 ${r.data.expiry_review}, 감사기록)`);
        setOvlAmount(''); setOvlReason('');
        return loadFli();
      })
      .catch(e => setOvlMsg(e?.response?.data?.detail || '등록 실패 - 부서장 이상 로그인이 필요합니다'))
      .finally(() => setOvlBusy(false));
  };
  // 레버
  const [monthlyProv, setMonthlyProv] = useState<number | null>(null);  // null = 현행 페이스
  const [writeoff, setWriteoff] = useState(0);
  const [sale, setSale] = useState(0);
  const [saleMonth, setSaleMonth] = useState(3);
  const [npl0, setNpl0] = useState(8000);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    axios.get('/api/loss-absorption/overview')
      .then(r => {
        setOverview(r.data);
        setMonthlyProv(r.data.defaults.current_pace_eok);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
    loadFli();
  }, []);

  useEffect(() => {
    if (monthlyProv === null) return;
    if (debounce.current) clearTimeout(debounce.current);
    debounce.current = setTimeout(() => {
      axios.get('/api/loss-absorption/simulate', {
        params: {
          monthly_provision: monthlyProv,
          quarterly_writeoff: writeoff,
          npl_sale: sale,
          sale_month: saleMonth,
          npl0,
        },
      }).then(r => setSim(r.data)).catch(console.error);
    }, 250);
    return () => { if (debounce.current) clearTimeout(debounce.current); };
  }, [monthlyProv, writeoff, sale, saleMonth, npl0]);

  if (loading || !overview) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const bm = overview.benchmark;
  const pf = overview.portfolio;
  const pace = overview.defaults.current_pace_eok;

  const chartData = (sim?.scenario_path || []).map((p: any, i: number) => ({
    month: p.month,
    시나리오: p.coverage,
    현행페이스: sim.baseline_path[i]?.coverage,
  }));

  const defaultedChange = ((bm.defaulted_2025_eok - bm.defaulted_2024_eok) / bm.defaulted_2024_eok) * 100;

  const Lever = ({ label, value, onChange, min, max, step, unit }: any) => (
    <div>
      <div className="flex items-center justify-between text-sm mb-1">
        <span className="font-medium text-gray-700">{label}</span>
        <span className="font-bold tabular text-gray-900">{formatNumber(value)}{unit}</span>
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
          <h1 className="text-2xl font-bold text-gray-900">손실흡수력 관리</h1>
          <p className="text-sm text-gray-500 mt-1">
            NPL커버리지 연말 100% 회복 경로 - 충당금 적립·상각·매각 레버 설계 (CRO 공언 목표)
          </p>
        </div>
        <span className="px-2.5 py-1 bg-amber-50 text-amber-700 text-xs rounded-full font-medium border border-amber-200">
          초기값: 2026.2Q 공시 · NPL 절대액은 가정치
        </span>
      </div>

      {/* 공시 벤치마크 */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="지주 NPL커버리지 (준비금 제외)"
          value={formatPercent(bm.group_coverage_ex_reserve, 1)}
          subtitle={`직전 분기 ${formatPercent(bm.group_coverage_ex_reserve_1q, 1)} → 급락`}
          icon={<TrendingDown size={24} />}
          color="red"
        />
        <StatCard
          title="대손준비금 포함"
          value={formatPercent(bm.group_coverage_incl_reserve, 1)}
          subtitle="CRO 컨퍼런스콜 언급 기준"
          icon={<ShieldAlert size={24} />}
          color="blue"
        />
        <StatCard
          title="연말 목표 (제외 기준)"
          value={formatPercent(bm.target_coverage, 0)}
          subtitle={`${bm.target_month}까지 · ${sim?.months || 5}개월 남음`}
          icon={<Target size={24} />}
          color="green"
        />
        <StatCard
          title="부도여신 (은행, 2025)"
          value={`${formatNumber(bm.defaulted_2025_eok)}억`}
          subtitle={`전년 대비 +${defaultedChange.toFixed(1)}% - 유입 가속`}
          icon={<AlertTriangle size={24} />}
          color="yellow"
        />
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* 경로 차트 */}
        <Card title="커버리지 경로 (월별)" className="col-span-2"
          subtitle={`시나리오 연말 ${sim ? formatPercent(sim.end_coverage, 1) : '-'} ${sim?.hits_target ? '· 목표 달성' : '· 목표 미달'}`}>
          <TrendChart
            data={chartData}
            xAxisKey="month"
            lines={[
              { key: '시나리오', name: '시나리오', color: COLORS.secondary },
              { key: '현행페이스', name: `현행 페이스 (${formatNumber(pace)}억/월)`, color: COLORS.gray, strokeDasharray: '5 5' },
            ]}
            referenceLines={[{ y: 100, label: '목표 100%', color: COLORS.danger }]}
            height={280}
          />
          {sim && !sim.hits_target && (
            <p className="text-xs text-red-500 mt-2">
              현재 레버 조합으로는 연말 {formatPercent(sim.end_coverage, 1)}에 그칩니다 - 적립 증액 또는 상각·매각 병행이 필요합니다
            </p>
          )}
        </Card>

        {/* 레버 패널 */}
        <Card title="정책 레버" subtitle="조정 즉시 경로 재계산">
          <div className="space-y-5">
            <Lever label="월 충당금 적립" value={monthlyProv ?? pace} onChange={setMonthlyProv}
              min={0} max={1500} step={50} unit="억/월" />
            <Lever label="분기 상각 (100% 적립분)" value={writeoff} onChange={setWriteoff}
              min={0} max={2000} step={100} unit="억/분기" />
            <Lever label="NPL 매각 (1회)" value={sale} onChange={setSale}
              min={0} max={3000} step={250} unit="억" />
            <Lever label="그룹 고정이하여신 가정" value={npl0} onChange={setNpl0}
              min={5000} max={12000} step={500} unit="억" />

            <div className="pt-3 border-t border-gray-100 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">목표 달성 필요 적립액</span>
                <span className="font-bold tabular text-[#00897B]">
                  {sim ? `${formatNumber(sim.required_monthly_provision_eok)}억/월` : '-'}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">적립만으로 달성 시</span>
                <span className="font-bold tabular text-gray-700">
                  {sim ? `${formatNumber(sim.required_provision_only_eok)}억/월` : '-'}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">현행 페이스 대비</span>
                <span className={`font-bold tabular ${sim && sim.required_gap_vs_pace_eok > 0 ? 'text-red-500' : 'text-green-600'}`}>
                  {sim ? `${sim.required_gap_vs_pace_eok > 0 ? '+' : ''}${formatNumber(sim.required_gap_vs_pace_eok)}억/월` : '-'}
                </span>
              </div>
              <p className="text-[11px] text-gray-400 leading-relaxed pt-1">
                상각은 충당금 100% 적립분 소각(분모·분자 동시 감소), 매각은 매각
                NPL의 적립분 60%만 소진되는 것으로 가정. 유입은 부도여신 공시
                (6,587억/년÷12) 기준.
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* CLMS 포트폴리오 실측 */}
      <div className="grid grid-cols-3 gap-6">
        <Card title="CLMS 포트폴리오 실측 - 분류별 충당금" className="col-span-2"
          subtitle={`기준일 ${pf.base_date} · 데모 DB 계산 (공시 벤치마크와 구분)`}
          noPadding>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                  <th className="py-2 px-4">분류</th>
                  <th className="py-2 px-3 text-right">건수</th>
                  <th className="py-2 px-3 text-right">익스포저 (억)</th>
                  <th className="py-2 px-3 text-right">감독 요구 (억)</th>
                  <th className="py-2 px-3 text-right">기적립 (억)</th>
                  <th className="py-2 px-4 text-right">적립부족 (억)</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(pf.by_class).map(([cls, v]: [string, any]) => (
                  <tr key={cls} className="border-b border-gray-50">
                    <td className="py-2 px-4 font-medium text-gray-900">{CLASS_LABEL[cls] || cls}</td>
                    <td className="py-2 px-3 text-right tabular">{formatNumber(v.count)}</td>
                    <td className="py-2 px-3 text-right tabular">{formatNumber(v.exposure_eok)}</td>
                    <td className="py-2 px-3 text-right tabular">{formatNumber(v.required_eok)}</td>
                    <td className="py-2 px-3 text-right tabular">{formatNumber(v.existing_eok)}</td>
                    <td className={`py-2 px-4 text-right tabular font-semibold ${v.gap_eok > 0 ? 'text-red-500' : 'text-green-600'}`}>
                      {formatNumber(v.gap_eok)}
                    </td>
                  </tr>
                ))}
                <tr className="bg-gray-50 font-semibold">
                  <td className="py-2 px-4">합계</td>
                  <td className="py-2 px-3 text-right tabular"></td>
                  <td className="py-2 px-3 text-right tabular">{formatNumber(pf.total_exposure_eok)}</td>
                  <td className="py-2 px-3 text-right tabular">{formatNumber(pf.supervisory_required_eok)}</td>
                  <td className="py-2 px-3 text-right tabular">{formatNumber(pf.existing_provision_eok)}</td>
                  <td className="py-2 px-4 text-right tabular text-red-500">{formatNumber(pf.provision_gap_eok)}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="px-4 py-3 text-xs text-gray-400 flex flex-wrap gap-x-6 gap-y-1">
            <span>NPL(고정이하) {formatNumber(pf.npl_exposure_eok)}억 · NPL비율 {formatPercent(pf.npl_ratio)}</span>
            <span>IFRS9 ECL {formatNumber(pf.ecl_total_eok)}억</span>
            <span className="text-amber-600 font-medium">
              대손준비금 필요액 {formatNumber(pf.reserve_needed_eok)}억 (감독 §29 요구 - ECL 미달분)
            </span>
          </div>
        </Card>

        <Card title="월별 신규 연체 발생" subtitle="부실 유입의 선행 지표 (억원)">
          <GroupedBarChart
            data={overview.formation_trend.map((f: any) => ({
              name: f.month.slice(2),
              발생액: f.amount_eok,
            }))}
            bars={[{ key: '발생액', name: '신규 연체액', color: COLORS.warning }]}
            height={240}
          />
          <p className="text-[11px] text-gray-400 mt-2">
            최근 3개월 신규 연체가 가속 - 커버리지 분모(NPL)의 선행 압력
          </p>
        </Card>
      </div>

      {/* ── P7: ECL 전망모형 점검 (FLI) ─────────────────────────── */}
      {valReport && (
        <div className="grid grid-cols-3 gap-6">
          <Card title="ECL 전망모형 점검 (FLI)" className="col-span-2"
            subtitle={valReport.framework}>
            <div className="grid grid-cols-4 gap-3 mb-4">
              {Object.entries(valReport.fli.scenarios).map(([k, sc]: [string, any]) => (
                <div key={k} className="p-3 bg-gray-50 rounded-lg text-center">
                  <p className="text-xs text-gray-500">{sc.label} (가중 {Math.round(sc.weight * 100)}%)</p>
                  <p className="text-lg font-bold tabular mt-0.5">
                    {formatNumber(Math.round(valReport.fli.base_ecl_eok * sc.factor))}억
                  </p>
                  <p className="text-[11px] text-gray-400">×{sc.factor}</p>
                </div>
              ))}
              <div className="p-3 bg-[#00BFA5]/10 rounded-lg text-center border border-[#00BFA5]/30">
                <p className="text-xs text-[#00695F] font-medium">가중 반영 ECL</p>
                <p className="text-lg font-bold tabular mt-0.5 text-[#00695F]">
                  {formatNumber(valReport.fli.final_ecl_eok)}억
                </p>
                <p className="text-[11px] text-gray-400">계수 {valReport.fli.weighted_macro_factor}</p>
              </div>
            </div>
            <div className="space-y-1.5">
              {valReport.findings.map((f: string, i: number) => (
                <p key={i} className={`text-sm ${f.includes('없음') ? 'text-green-600' : 'text-amber-700'}`}>
                  {f.includes('없음') ? '✓' : '⚑'} {f}
                </p>
              ))}
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-gray-400 mt-3 pt-3 border-t border-gray-100">
              <span>감독 §29 요구 {formatNumber(valReport.adequacy.supervisory_required_eok)}억</span>
              <span>조정 후 ECL {formatNumber(valReport.adequacy.adjusted_ecl_eok)}억</span>
              <span className="text-amber-600 font-medium">대손준비금 필요 {formatNumber(valReport.adequacy.reserve_needed_eok)}억</span>
              <span>오버레이 비중 {formatPercent(valReport.overlay.share_of_ecl, 1)}</span>
            </div>
          </Card>

          <Card title="관리자 오버레이" subtitle="모형 밖 경영진 판단 조정 - 부서장 이상 + 재검토 기한 강제">
            <div className="space-y-3">
              <div className="flex gap-2">
                <input value={ovlAmount} onChange={e => setOvlAmount(e.target.value)}
                  placeholder="금액 (억)" type="number"
                  className="w-24 px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg" />
                <select value={ovlDriver} onChange={e => setOvlDriver(e.target.value)}
                  className="flex-1 px-2 py-1.5 text-sm border border-gray-200 rounded-lg bg-white">
                  {['부동산PF', '자영업·소상공인', '금리·경기', '특정 업종', '기타'].map(d => (
                    <option key={d}>{d}</option>
                  ))}
                </select>
              </div>
              <input value={ovlReason} onChange={e => setOvlReason(e.target.value)}
                placeholder="판단 근거 (필수, 5자 이상)"
                className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg" />
              <button onClick={submitOverlay} disabled={ovlBusy}
                className="w-full py-1.5 text-sm font-semibold bg-[#00897B] text-white rounded-lg hover:bg-[#00695F] disabled:opacity-50">
                오버레이 등록
              </button>
              {ovlMsg && <p className="text-xs font-medium text-[#00695F]">{ovlMsg}</p>}
              <div className="pt-2 border-t border-gray-100 space-y-2 max-h-48 overflow-y-auto">
                {(overlays?.overlays || []).map((o: any) => (
                  <div key={o.overlay_id} className="text-xs p-2 bg-gray-50 rounded-lg">
                    <div className="flex justify-between font-medium text-gray-900">
                      <span>{o.risk_driver || o.segment}</span>
                      <span className="tabular">{o.direction === 'ADD' ? '+' : ''}{formatNumber(o.amount_eok)}억</span>
                    </div>
                    <p className="text-gray-500 mt-0.5">{o.reason}</p>
                    <p className="text-gray-400 mt-0.5">{o.approved_by} ({o.approved_level}) · 재검토 {o.expiry_review}</p>
                  </div>
                ))}
                {(overlays?.overlays || []).length === 0 && (
                  <p className="text-xs text-gray-400 text-center py-2">등록된 오버레이 없음</p>
                )}
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
