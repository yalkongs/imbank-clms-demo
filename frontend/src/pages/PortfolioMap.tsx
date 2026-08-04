import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import axios from 'axios';
import { RotateCcw, MousePointerClick, Move, Info } from 'lucide-react';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer,
} from 'recharts';
import { Card, RegionFilter, FeatureModal } from '../components';
import { formatAmount, formatPercent } from '../utils/format';

/**
 * 포트폴리오 맵 - 기업 다차원 산점도
 * ------------------------------------
 * 여신 보유 699개사를 선택 가능한 2축 + 크기(잔액) + 색(범주)으로 배치한다.
 * · 포인트 클릭  → 우측에 기업 프로필(레이더 6축 백분위)
 * · 빈 곳 드래그 → 영역(브러시) 선택 → 집합 요약
 * · PD·EWS·한도소진율 축에서는 포인트를 '드래그'해 what-if 모의 조정
 *   (백엔드가 동일 산식으로 EL·RAROC·분류·충당금을 재계산 - 실데이터 불변)
 */

interface Company {
  customer_id: string; name: string; industry: string; region: string;
  size_category: string; exposure: number; dpd: number; classification: string;
  pd: number; grade: string | null; raroc: number | null; ews_score: number | null;
  ews_grade: string | null; util: number | null; dd: number | null;
  sentiment: number | null; debt_ratio: number | null; icr: number | null;
  altman_z: number | null; provision_ratio: number | null;
}

type MetricKey = 'pd' | 'raroc' | 'ews_score' | 'util' | 'debt_ratio' | 'icr'
  | 'dd' | 'sentiment' | 'provision_ratio' | 'altman_z';

const METRICS: Record<MetricKey, {
  label: string; unit: string; fmt: (v: number) => string;
  draggable?: boolean; threshold?: { v: number; label: string };
}> = {
  pd:        { label: 'PD (부도확률)', unit: '%', fmt: v => v.toFixed(2) + '%', draggable: true },
  raroc:     { label: 'RAROC', unit: '%', fmt: v => v.toFixed(1) + '%', threshold: { v: 15, label: '허들 15%' } },
  ews_score: { label: 'EWS 종합점수', unit: '점', fmt: v => v.toFixed(0) + '점', draggable: true,
               threshold: { v: 55, label: 'SICR 55' } },
  util:      { label: '한도소진율', unit: '%', fmt: v => v.toFixed(0) + '%', draggable: true,
               threshold: { v: 80, label: '주의 80%' } },
  debt_ratio:{ label: '부채비율', unit: '%', fmt: v => v.toFixed(0) + '%', threshold: { v: 200, label: '기준 200%' } },
  icr:       { label: '이자보상배율', unit: '배', fmt: v => v.toFixed(2), threshold: { v: 1.5, label: '기준 1.5' } },
  dd:        { label: '부도거리 DD (상장사)', unit: '', fmt: v => v.toFixed(2), threshold: { v: 2, label: '경보 2.0' } },
  sentiment: { label: '뉴스 감성지수', unit: '', fmt: v => v.toFixed(2), threshold: { v: -0.3, label: '경보 -0.3' } },
  provision_ratio: { label: '충당율 (ECL/잔액)', unit: '%', fmt: v => v.toFixed(2) + '%' },
  altman_z:  { label: 'Altman Z-Score', unit: '', fmt: v => v.toFixed(2), threshold: { v: 1.81, label: '부실권 1.81' } },
};

type ColorMode = 'classification' | 'region' | 'size' | 'grade';

/** (i) 버튼이 여는 유용성 설명 - 이 화면이 표·순위와 무엇이 다른지 */
const MAP_FEATURE = {
  title: '포트폴리오 맵은 무엇이 유용한가',
  description:
    '여신 보유 기업 전체를 지표 공간에 배치해, 표와 순위로는 보이지 않는 ' +
    '포트폴리오의 "지형"을 봅니다. 어디에 쏠려 있는지, 누가 무리에서 벗어나 있는지, ' +
    '누가 임계선 바로 앞에 서 있는지가 한 화면에 드러납니다.',
  benefits: [
    '이상치 발견 - 고위험인데 저수익(PD 높고 RAROC 낮음)처럼 우선 점검할 기업이 시각적으로 돌출됩니다',
    '쏠림 진단 - 색(분류·지역·규모·등급대)과 크기(잔액)를 겹쳐 특정 구역의 익스포저 집중을 확인합니다',
    '임계 관리 - RAROC 허들 15%, SICR 55점, 부채비율 200% 등 기준선에 근접한 기업을 미리 봅니다',
    '영역 선택(브러시) - 문제 구역을 마우스로 묶으면 개사 수·잔액 합계·평균 PD·NPL 잔액이 즉시 집계됩니다',
    'What-if 드래그 - PD·EWS·한도소진율 축에서 포인트를 끌면 EL·RAROC·건전성 분류·필요충당금 파급을 ' +
    '동일 산식으로 재계산합니다. "이 기업의 PD가 두 배가 되면?"에 회의 중 바로 답할 수 있습니다',
    '기업 프로필 - 클릭 한 번으로 6축 백분위 레이더(안전성·수익성·EWS·한도여유·재무구조·감성)를 확인합니다',
  ],
  methodology:
    'What-if 는 자산건전성 분류·ECL 모듈과 **동일한 산식**(보수주의 분류, 감독규정 최저적립률, ' +
    'EL = PD x LGD x EAD)을 재사용한 모의 계산이며, **실데이터는 변경되지 않습니다**.\n\n' +
    '축 도메인은 1~99% 분위수로 잘라 극단 이상치가 본체 분포를 압착하지 않게 합니다. ' +
    'PD 축의 세로 띠는 등급별 고정 PD(등급 체계의 구조)가 그대로 드러난 것입니다.',
};

const CLASS_COLORS: Record<string, string> = {
  NORMAL: '#00BFA5', PRECAUTIONARY: '#f59e0b', SUBSTANDARD: '#f97316',
  DOUBTFUL: '#ef4444', LOSS: '#7f1d1d',
};
const CLASS_LABELS: Record<string, string> = {
  NORMAL: '정상', PRECAUTIONARY: '요주의', SUBSTANDARD: '고정',
  DOUBTFUL: '회수의문', LOSS: '추정손실',
};
const REGION_COLORS: Record<string, string> = {
  CAPITAL: '#3b82f6', DAEGU_GB: '#00BFA5', BUSAN_GN: '#8b5cf6',
};
const REGION_LABELS: Record<string, string> = {
  CAPITAL: '수도권', DAEGU_GB: '대구경북', BUSAN_GN: '부산경남',
};
const SIZE_COLORS: Record<string, string> = {
  LARGE: '#1d4ed8', MEDIUM: '#00BFA5', SMALL: '#f59e0b', SOHO: '#ec4899',
};
const SIZE_LABELS: Record<string, string> = {
  LARGE: '대기업', MEDIUM: '중견', SMALL: '중소', SOHO: '개인사업자',
};

function gradeBand(grade: string | null): string {
  if (!grade) return '무등급';
  if (/^A/.test(grade)) return 'A등급대';
  if (/^BBB/.test(grade)) return 'BBB';
  if (/^BB/.test(grade)) return 'BB';
  return 'B 이하';
}
const GRADE_COLORS: Record<string, string> = {
  'A등급대': '#0ea5e9', BBB: '#00BFA5', BB: '#f59e0b', 'B 이하': '#ef4444', 무등급: '#9ca3af',
};

function colorOf(c: Company, mode: ColorMode): string {
  if (mode === 'classification') return CLASS_COLORS[c.classification] || '#9ca3af';
  if (mode === 'region') return REGION_COLORS[c.region] || '#9ca3af';
  if (mode === 'size') return SIZE_COLORS[c.size_category] || '#9ca3af';
  return GRADE_COLORS[gradeBand(c.grade)];
}
function legendOf(mode: ColorMode): [string, string][] {
  if (mode === 'classification') return Object.keys(CLASS_COLORS).map(k => [CLASS_LABELS[k], CLASS_COLORS[k]]);
  if (mode === 'region') return Object.keys(REGION_COLORS).map(k => [REGION_LABELS[k], REGION_COLORS[k]]);
  if (mode === 'size') return Object.keys(SIZE_COLORS).map(k => [SIZE_LABELS[k], SIZE_COLORS[k]]);
  return Object.entries(GRADE_COLORS);
}

// ── 차트 기하 ────────────────────────────────────────────
const W = 920, H = 560, M = { l: 56, r: 16, t: 14, b: 40 };

function makeScale(values: number[], range: [number, number]) {
  // 극단 이상치가 본체 분포를 압착하지 않도록 1~99% 분위수로 도메인을 자른다.
  // 범위 밖 포인트는 가장자리에 고정(clamp)되어 표시된다.
  const sorted = [...values].sort((a, b) => a - b);
  const q = (p: number) => sorted[Math.min(sorted.length - 1, Math.floor(p * sorted.length))];
  let min = q(0.01), max = q(0.99);
  if (min === max) { min -= 1; max += 1; }
  const pad = (max - min) * 0.06;
  min -= pad; max += pad;
  const k = (range[1] - range[0]) / (max - min);
  const lo = Math.min(range[0], range[1]), hi = Math.max(range[0], range[1]);
  const scale = (v: number) => Math.max(lo, Math.min(hi, range[0] + (v - min) * k));
  scale.invert = (px: number) => min + (px - range[0]) / k;
  scale.ticks = () => {
    const step = (max - min) / 5;
    const mag = Math.pow(10, Math.floor(Math.log10(step)));
    const nice = [1, 2, 2.5, 5, 10].find(n => n * mag >= step)! * mag;
    const start = Math.ceil(min / nice) * nice;
    const out: number[] = [];
    for (let v = start; v <= max; v += nice) out.push(+v.toFixed(6));
    return out;
  };
  return scale as ((v: number) => number) & { invert: (px: number) => number; ticks: () => number[] };
}

/** 백분위(0~100) - 레이더 정규화용. dirHigh=true 면 값이 클수록 100에 가깝다 */
function percentile(values: number[], v: number, dirHigh: boolean): number {
  const arr = values.filter(x => x !== null && !isNaN(x));
  if (!arr.length) return 50;
  const below = arr.filter(x => x < v).length;
  const p = below / arr.length * 100;
  return Math.round(dirHigh ? p : 100 - p);
}

export default function PortfolioMap() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [region, setRegion] = useState('');
  const [xKey, setXKey] = useState<MetricKey>('pd');
  const [yKey, setYKey] = useState<MetricKey>('raroc');
  const [colorMode, setColorMode] = useState<ColorMode>('classification');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [infoOpen, setInfoOpen] = useState(false);
  const [brushSel, setBrushSel] = useState<Company[] | null>(null);
  // what-if: 드래그로 덮어쓴 축 값 {pd?, ews_score?, util?}
  const [simOverride, setSimOverride] = useState<Record<string, number>>({});
  const [simResult, setSimResult] = useState<any>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const dragRef = useRef<{ id: string; moved: boolean } | null>(null);
  const brushRef = useRef<{ x0: number; y0: number; x1: number; y1: number } | null>(null);
  const [brushRect, setBrushRect] = useState<{ x: number; y: number; w: number; h: number } | null>(null);

  useEffect(() => {
    axios.get('/api/portfolio-map/companies')
      .then(r => setCompanies(r.data.companies || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(
    () => companies.filter(c => !region || c.region === region),
    [companies, region]
  );

  // 현재 축 값 (선택 기업은 모의값 우선)
  const valOf = useCallback((c: Company, key: MetricKey): number | null => {
    if (c.customer_id === selectedId && simOverride[key] !== undefined) return simOverride[key];
    return c[key] as number | null;
  }, [selectedId, simOverride]);

  const plotted = useMemo(
    () => filtered.filter(c => valOf(c, xKey) !== null && valOf(c, yKey) !== null),
    [filtered, xKey, yKey, valOf]
  );

  const xScale = useMemo(
    () => makeScale(plotted.map(c => valOf(c, xKey)!), [M.l, W - M.r]),
    [plotted, xKey, valOf]
  );
  const yScale = useMemo(
    () => makeScale(plotted.map(c => valOf(c, yKey)!), [H - M.b, M.t]),
    [plotted, yKey, valOf]
  );
  const maxExp = useMemo(() => Math.max(...filtered.map(c => c.exposure), 1), [filtered]);
  const rOf = (c: Company) => 3 + Math.sqrt(c.exposure / maxExp) * 14;

  const selected = filtered.find(c => c.customer_id === selectedId) || null;
  const hovered = filtered.find(c => c.customer_id === hoverId) || null;

  // ── what-if 호출 ──
  const runWhatIf = useCallback((cid: string, ov: Record<string, number>) => {
    const params: any = { customer_id: cid };
    if (ov.pd !== undefined) params.pd_sim = ov.pd;
    if (ov.ews_score !== undefined) params.ews_sim = ov.ews_score;
    if (ov.util !== undefined) params.util_sim = ov.util;
    axios.get('/api/portfolio-map/what-if', { params })
      .then(r => setSimResult(r.data))
      .catch(console.error);
  }, []);

  const resetSim = () => { setSimOverride({}); setSimResult(null); };

  // ── 포인터 이벤트 ──
  const svgPoint = (e: React.PointerEvent) => {
    const rect = svgRef.current!.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) * (W / rect.width),
      y: (e.clientY - rect.top) * (H / rect.height),
    };
  };

  const onPointDown = (c: Company) => (e: React.PointerEvent) => {
    e.stopPropagation();
    try { (e.target as Element).setPointerCapture(e.pointerId); } catch { /* 합성 이벤트 등 */ }
    dragRef.current = { id: c.customer_id, moved: false };
    if (c.customer_id !== selectedId) { setSelectedId(c.customer_id); setSimOverride({}); setSimResult(null); }
    setBrushSel(null);
  };

  const onPointMove = (e: React.PointerEvent) => {
    if (dragRef.current) {
      const draggableX = METRICS[xKey].draggable, draggableY = METRICS[yKey].draggable;
      if (!draggableX && !draggableY) return;
      dragRef.current.moved = true;
      const p = svgPoint(e);
      setSimOverride(prev => {
        const next = { ...prev };
        if (draggableX) next[xKey] = +xScale.invert(Math.max(M.l, Math.min(W - M.r, p.x))).toFixed(3);
        if (draggableY) next[yKey] = +yScale.invert(Math.max(M.t, Math.min(H - M.b, p.y))).toFixed(3);
        return next;
      });
    } else if (brushRef.current) {
      const p = svgPoint(e);
      brushRef.current.x1 = p.x; brushRef.current.y1 = p.y;
      const b = brushRef.current;
      setBrushRect({
        x: Math.min(b.x0, b.x1), y: Math.min(b.y0, b.y1),
        w: Math.abs(b.x1 - b.x0), h: Math.abs(b.y1 - b.y0),
      });
    }
  };

  const onPointerUp = () => {
    if (dragRef.current) {
      const { id, moved } = dragRef.current;
      dragRef.current = null;
      if (moved && Object.keys(simOverride).length) runWhatIf(id, simOverride);
      return;
    }
    if (brushRef.current && brushRect && brushRect.w > 8 && brushRect.h > 8) {
      const sel = plotted.filter(c => {
        const px = xScale(valOf(c, xKey)!), py = yScale(valOf(c, yKey)!);
        return px >= brushRect.x && px <= brushRect.x + brushRect.w &&
               py >= brushRect.y && py <= brushRect.y + brushRect.h;
      });
      setBrushSel(sel);
      setSelectedId(null); resetSim();
    }
    brushRef.current = null;
    setBrushRect(null);
  };

  const onBgDown = (e: React.PointerEvent) => {
    const p = svgPoint(e);
    brushRef.current = { x0: p.x, y0: p.y, x1: p.x, y1: p.y };
    setSelectedId(null); setBrushSel(null); resetSim();
  };

  if (loading) {
    return <div className="flex items-center justify-center h-96">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
    </div>;
  }

  const xM = METRICS[xKey], yM = METRICS[yKey];
  const dragEnabled = xM.draggable || yM.draggable;

  // 레이더 데이터 (선택 기업, 백분위)
  const radarData = selected ? [
    { axis: '안전성(PD)', v: percentile(filtered.map(c => c.pd), selected.pd, false) },
    { axis: '수익성(RAROC)', v: percentile(filtered.map(c => c.raroc!), selected.raroc ?? 0, true) },
    { axis: 'EWS 건전', v: percentile(filtered.map(c => c.ews_score!), selected.ews_score ?? 0, true) },
    { axis: '한도여유', v: percentile(filtered.map(c => c.util!), selected.util ?? 0, false) },
    { axis: '재무구조', v: percentile(filtered.map(c => c.debt_ratio!), selected.debt_ratio ?? 0, false) },
    { axis: '뉴스감성', v: percentile(filtered.map(c => c.sentiment!), selected.sentiment ?? 0, true) },
  ] : [];

  const brushSummary = brushSel && brushSel.length ? {
    n: brushSel.length,
    exposure: brushSel.reduce((s, c) => s + c.exposure, 0),
    avgPd: brushSel.reduce((s, c) => s + c.pd, 0) / brushSel.length,
    nplExp: brushSel.filter(c => ['SUBSTANDARD', 'DOUBTFUL', 'LOSS'].includes(c.classification))
                    .reduce((s, c) => s + c.exposure, 0),
  } : null;

  return (
    <div className="space-y-6">
      <FeatureModal isOpen={infoOpen} onClose={() => setInfoOpen(false)} feature={MAP_FEATURE} />
      {/* 헤더 */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-1.5">
            <h1 className="text-2xl font-bold text-gray-900">포트폴리오 맵</h1>
            <button
              onClick={() => setInfoOpen(true)}
              aria-label="포트폴리오 맵의 유용성 설명"
              title="이 화면이 왜 유용한가"
              className="p-1 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
            >
              <Info size={18} />
            </button>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            여신 보유 {companies.length}개사 다차원 분석 - 크기는 여신잔액
          </p>
        </div>
        <RegionFilter value={region} onChange={setRegion} />
      </div>

      {/* 컨트롤 */}
      <div className="flex items-center gap-4 flex-wrap text-sm">
        {([['X축', xKey, setXKey], ['Y축', yKey, setYKey]] as const).map(([label, key, setter]) => (
          <label key={label} className="flex items-center gap-2">
            <span className="text-gray-500">{label}</span>
            <select value={key}
              onChange={e => { (setter as any)(e.target.value); resetSim(); }}
              className="border rounded-lg px-2 py-1.5 text-sm bg-white">
              {(Object.keys(METRICS) as MetricKey[]).map(k => (
                <option key={k} value={k}>{METRICS[k].label}{METRICS[k].draggable ? ' ⇕' : ''}</option>
              ))}
            </select>
          </label>
        ))}
        <label className="flex items-center gap-2">
          <span className="text-gray-500">색상</span>
          <select value={colorMode} onChange={e => setColorMode(e.target.value as ColorMode)}
            className="border rounded-lg px-2 py-1.5 text-sm bg-white">
            <option value="classification">건전성 분류</option>
            <option value="region">지역</option>
            <option value="size">기업규모</option>
            <option value="grade">신용등급대</option>
          </select>
        </label>
        <span className="flex items-center gap-1.5 text-xs text-gray-400">
          {dragEnabled
            ? <><Move size={13} /> ⇕ 표시 축에서는 포인트를 드래그하면 what-if 모의 조정</>
            : <><MousePointerClick size={13} /> 포인트 클릭=기업 상세 · 빈 곳 드래그=영역 선택</>}
        </span>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 items-start">
        {/* 산점도 */}
        <Card className="xl:col-span-2" noPadding>
          <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} className="w-full select-none touch-none"
               onPointerDown={onBgDown} onPointerMove={onPointMove} onPointerUp={onPointerUp}>
            {/* 격자·축 */}
            {xScale.ticks().map(t => (
              <g key={`x${t}`}>
                <line x1={xScale(t)} y1={M.t} x2={xScale(t)} y2={H - M.b} stroke="#f1f5f9" />
                <text x={xScale(t)} y={H - M.b + 16} textAnchor="middle" fontSize={10} fill="#94a3b8">
                  {xM.fmt(t)}
                </text>
              </g>
            ))}
            {yScale.ticks().map(t => (
              <g key={`y${t}`}>
                <line x1={M.l} y1={yScale(t)} x2={W - M.r} y2={yScale(t)} stroke="#f1f5f9" />
                <text x={M.l - 6} y={yScale(t) + 3} textAnchor="end" fontSize={10} fill="#94a3b8">
                  {yM.fmt(t)}
                </text>
              </g>
            ))}
            {/* 임계 기준선 */}
            {xM.threshold && (
              <g>
                <line x1={xScale(xM.threshold.v)} y1={M.t} x2={xScale(xM.threshold.v)} y2={H - M.b}
                      stroke="#f59e0b" strokeDasharray="5 4" strokeWidth={1.2} />
                <text x={xScale(xM.threshold.v) + 4} y={M.t + 10} fontSize={9} fill="#d97706">{xM.threshold.label}</text>
              </g>
            )}
            {yM.threshold && (
              <g>
                <line x1={M.l} y1={yScale(yM.threshold.v)} x2={W - M.r} y2={yScale(yM.threshold.v)}
                      stroke="#f59e0b" strokeDasharray="5 4" strokeWidth={1.2} />
                <text x={W - M.r - 4} y={yScale(yM.threshold.v) - 4} fontSize={9} fill="#d97706" textAnchor="end">{yM.threshold.label}</text>
              </g>
            )}
            {/* 축 라벨 */}
            <text x={(M.l + W - M.r) / 2} y={H - 6} textAnchor="middle" fontSize={11} fill="#475569" fontWeight={600}>
              {xM.label}
            </text>
            <text x={14} y={(M.t + H - M.b) / 2} textAnchor="middle" fontSize={11} fill="#475569" fontWeight={600}
                  transform={`rotate(-90 14 ${(M.t + H - M.b) / 2})`}>
              {yM.label}
            </text>

            {/* 포인트 */}
            {plotted.map(c => {
              const isSel = c.customer_id === selectedId;
              const isHover = c.customer_id === hoverId;
              return (
                <circle
                  key={c.customer_id}
                  cx={xScale(valOf(c, xKey)!)}
                  cy={yScale(valOf(c, yKey)!)}
                  r={rOf(c) * (isSel ? 1.25 : 1)}
                  fill={colorOf(c, colorMode)}
                  fillOpacity={isSel || isHover ? 0.95 : 0.62}
                  stroke={isSel ? '#111827' : '#ffffff'}
                  strokeWidth={isSel ? 2 : 0.8}
                  style={{ cursor: dragEnabled && isSel ? 'grab' : 'pointer' }}
                  onPointerDown={onPointDown(c)}
                  onPointerEnter={() => setHoverId(c.customer_id)}
                  onPointerLeave={() => setHoverId(null)}
                />
              );
            })}

            {/* 브러시 */}
            {brushRect && (
              <rect x={brushRect.x} y={brushRect.y} width={brushRect.w} height={brushRect.h}
                    fill="#3b82f6" fillOpacity={0.08} stroke="#3b82f6" strokeDasharray="4 3" />
            )}

            {/* 호버 툴팁 */}
            {hovered && !dragRef.current && (
              <g pointerEvents="none">
                {(() => {
                  const px = xScale(valOf(hovered, xKey)!), py = yScale(valOf(hovered, yKey)!);
                  const tx = Math.min(px + 12, W - 210), ty = Math.max(py - 58, M.t);
                  return (
                    <>
                      <rect x={tx} y={ty} width={200} height={52} rx={7} fill="#111827" fillOpacity={0.92} />
                      <text x={tx + 10} y={ty + 17} fontSize={11} fill="#fff" fontWeight={600}>{hovered.name}</text>
                      <text x={tx + 10} y={ty + 31} fontSize={9.5} fill="#cbd5e1">
                        {hovered.industry} · {formatAmount(hovered.exposure, 'billion')}
                      </text>
                      <text x={tx + 10} y={ty + 44} fontSize={9.5} fill="#cbd5e1">
                        {xM.label} {xM.fmt(valOf(hovered, xKey)!)} · {yM.label} {yM.fmt(valOf(hovered, yKey)!)}
                      </text>
                    </>
                  );
                })()}
              </g>
            )}
          </svg>
        </Card>

        {/* 우측 패널 */}
        <div className="space-y-4">
          {selected ? (
            <Card title={selected.name}
              headerAction={
                <button onClick={() => { setSelectedId(null); resetSim(); }}
                  className="text-sm text-gray-500 hover:text-gray-700">닫기</button>
              }>
              <p className="text-xs text-gray-400 -mt-1 mb-3">
                {selected.customer_id} · {selected.industry} · {REGION_LABELS[selected.region] || selected.region}
                · {SIZE_LABELS[selected.size_category] || selected.size_category}
              </p>
              <div className="grid grid-cols-2 gap-2 text-sm mb-3">
                {[
                  ['여신잔액', formatAmount(selected.exposure, 'billion')],
                  ['등급', selected.grade || '-'],
                  ['건전성', CLASS_LABELS[selected.classification]],
                  ['DPD', `${selected.dpd}일`],
                  ['PD', formatPercent(selected.pd)],
                  ['RAROC', selected.raroc != null ? formatPercent(selected.raroc, 1) : '-'],
                ].map(([l, v]) => (
                  <div key={l as string} className="flex justify-between bg-gray-50 rounded px-2.5 py-1.5">
                    <span className="text-gray-500 text-xs">{l}</span>
                    <span className="font-semibold text-xs tabular">{v}</span>
                  </div>
                ))}
              </div>
              <ResponsiveContainer width="100%" height={190}>
                <RadarChart data={radarData} outerRadius={70}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="axis" tick={{ fontSize: 9.5 }} />
                  <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar dataKey="v" stroke="#00BFA5" fill="#00BFA5" fillOpacity={0.35} />
                </RadarChart>
              </ResponsiveContainer>
              <p className="text-[10px] text-gray-400 text-center -mt-1">전체 대비 백분위 (바깥쪽 = 우량)</p>
              <a href={`/customer-browser?q=${encodeURIComponent(selected.name)}`}
                 className="block text-center text-xs text-blue-600 hover:underline mt-2">
                기업 360° 상세 조회 →
              </a>
            </Card>
          ) : brushSummary ? (
            <Card title={`영역 선택: ${brushSummary.n}개사`}
              headerAction={<button onClick={() => setBrushSel(null)}
                className="text-sm text-gray-500 hover:text-gray-700">닫기</button>}>
              <dl className="space-y-1.5 text-sm mb-3">
                <div className="flex justify-between"><dt className="text-gray-500">잔액 합계</dt>
                  <dd className="tabular font-semibold">{formatAmount(brushSummary.exposure, 'billion')}</dd></div>
                <div className="flex justify-between"><dt className="text-gray-500">평균 PD</dt>
                  <dd className="tabular font-semibold">{formatPercent(brushSummary.avgPd)}</dd></div>
                <div className="flex justify-between"><dt className="text-gray-500">NPL 잔액</dt>
                  <dd className={`tabular font-semibold ${brushSummary.nplExp ? 'text-red-600' : ''}`}>
                    {formatAmount(brushSummary.nplExp, 'billion')}</dd></div>
              </dl>
              <div className="max-h-64 overflow-y-auto divide-y divide-gray-50">
                {brushSel!.slice(0, 30).sort((a, b) => b.exposure - a.exposure).map(c => (
                  <button key={c.customer_id}
                    onClick={() => { setSelectedId(c.customer_id); setBrushSel(null); }}
                    className="w-full flex justify-between items-center text-xs py-1.5 hover:bg-gray-50 px-1 rounded">
                    <span className="truncate">{c.name}</span>
                    <span className="tabular text-gray-500 flex-none">{formatAmount(c.exposure, 'billion')}</span>
                  </button>
                ))}
              </div>
              {brushSel!.length > 30 && (
                <p className="text-[10px] text-gray-400 text-center mt-1">잔액 상위 30개만 표시</p>
              )}
            </Card>
          ) : (
            <Card title="범례 · 사용법">
              <div className="space-y-1.5 mb-4">
                {legendOf(colorMode).map(([label, color]) => (
                  <div key={label} className="flex items-center gap-2 text-sm">
                    <span className="w-3 h-3 rounded-full" style={{ background: color }} />
                    <span className="text-gray-600">{label}</span>
                  </div>
                ))}
              </div>
              <ul className="text-xs text-gray-500 space-y-1.5 list-disc ml-4">
                <li>포인트 크기 = 여신잔액</li>
                <li>포인트 클릭 → 기업 프로필 + 6축 레이더</li>
                <li>빈 곳을 드래그 → 영역 선택 후 집합 요약</li>
                <li><b>⇕ 표시 축(PD·EWS·한도소진율)</b>에서 선택 포인트를 드래그하면
                    what-if 모의 조정 - EL·RAROC·분류·충당금 재계산</li>
              </ul>
            </Card>
          )}

          {/* what-if 결과 */}
          {simResult && (
            <Card title="What-if 모의 조정"
              headerAction={
                <button onClick={resetSim}
                  className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700">
                  <RotateCcw size={12} /> 원위치
                </button>
              }>
              <span className="inline-block px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-[10px] font-semibold mb-2">
                모의 - 실데이터 불변
              </span>
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-400 border-b">
                    <th className="text-left py-1">지표</th>
                    <th className="text-right py-1">현재</th>
                    <th className="text-right py-1">모의</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ['예상손실(EL)', formatAmount(simResult.base.el, 'billion'), formatAmount(simResult.sim.el, 'billion'),
                      simResult.sim.el > simResult.base.el],
                    ['RAROC', formatPercent(simResult.base.raroc, 1), formatPercent(simResult.sim.raroc, 1),
                      simResult.sim.raroc < simResult.base.raroc],
                    ['건전성 분류', CLASS_LABELS[simResult.base.classification], CLASS_LABELS[simResult.sim.classification],
                      simResult.sim.classification !== simResult.base.classification],
                    ['필요충당금', formatAmount(simResult.base.required_provision, 'billion'),
                      formatAmount(simResult.sim.required_provision, 'billion'),
                      simResult.sim.required_provision > simResult.base.required_provision],
                  ].map(([l, b, s, worse]) => (
                    <tr key={l as string} className="border-b border-gray-50">
                      <td className="py-1.5 text-gray-600">{l}</td>
                      <td className="py-1.5 text-right tabular text-gray-500">{b}</td>
                      <td className={`py-1.5 text-right tabular font-bold ${worse ? 'text-red-600' : 'text-green-600'}`}>{s}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-[10px] text-gray-400 mt-2">{simResult.note}</p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
