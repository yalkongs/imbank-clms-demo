import React from 'react';
import {
  Building2, FileText, PiggyBank, AlertTriangle, Activity,
  ListChecks, Brain, Check, X, Sparkles
} from 'lucide-react';
import { useTheme, Theme } from '../context/ThemeProvider';

interface Feature {
  icon: React.ReactNode;
  title: string;
  desc: string;
}

const FEATURES: Feature[] = [
  { icon: <FileText size={18} />,  title: '여신 심사 · RAROC', desc: '신청 심사, What-if 시뮬레이션, 위험조정수익률' },
  { icon: <PiggyBank size={18} />, title: '자본 · RWA',        desc: 'BIS 자본비율, Basel IRB RWA, 자본배분 최적화' },
  { icon: <AlertTriangle size={18} />, title: 'EWS 5채널 조기경보', desc: '재무·공급망·거래행태·시장신호·공적정보' },
  { icon: <Activity size={18} />,  title: '스트레스 테스트',   desc: 'BASELINE→EXTREME 5단계 시나리오 분석' },
  { icon: <ListChecks size={18} />, title: 'IFRS9 ECL · 부실관리', desc: '자산건전성 분류, 충당금, 연체·Workout' },
  { icon: <Brain size={18} />,     title: '모델 관리 · MRM',   desc: 'PD/LGD/EAD 모형, 성능 모니터링, Override' },
];

function ThemeCard({
  value, label, desc, selected, onSelect, previewClass,
}: {
  value: Theme; label: string; desc: string;
  selected: boolean; onSelect: (t: Theme) => void; previewClass: string;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(value)}
      className={`relative flex-1 text-left rounded-xl border-2 p-3 transition-all ${
        selected
          ? 'border-blue-600 ring-2 ring-blue-200 bg-blue-50'
          : 'border-gray-200 hover:border-blue-300 bg-white'
      }`}
    >
      {selected && (
        <span className="absolute top-2 right-2 w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center">
          <Check size={12} />
        </span>
      )}
      <div className={`h-16 w-full rounded-lg mb-2 border border-gray-200 ${previewClass}`} />
      <p className="text-sm font-semibold text-gray-900">{label}</p>
      <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
    </button>
  );
}

export default function OnboardingModal({ onClose }: { onClose: (startTour?: boolean) => void }) {
  const { theme, setTheme } = useTheme();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="modal-in w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-white rounded-2xl shadow-2xl">
        {/* 헤더 - 공식 로고는 흰 배경 시그니처이므로 흰 바탕에 두고,
            브랜드 그라디언트(민트→라임)는 그 아래 띠로 쓴다. */}
        <div className="relative rounded-t-2xl overflow-hidden">
          <button
            onClick={() => onClose()}
            aria-label="닫기"
            className="absolute top-4 right-4 z-10 p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <X size={18} />
          </button>

          <div className="px-6 pt-6 pb-5 bg-white">
            <div className="flex items-center gap-4">
              <img
                src="/brand/imbank-logo-h-kr.jpg"
                alt="iM뱅크"
                className="h-9 w-auto"
              />
              <div className="pl-4 border-l border-gray-200">
                <h1 className="text-xl font-bold leading-tight text-gray-900">CLMS</h1>
                <p className="text-sm text-gray-500">기업여신 전(全) 생애주기 통합 관리 시스템</p>
              </div>
            </div>
            <p className="mt-4 text-sm text-gray-600 leading-relaxed">
              심사 · 실행 · 모니터링 · 회수까지 - 기업여신의 리스크를 하나의 화면에서.
              Basel · IFRS9 기반의 리스크 계산 엔진과 5채널 조기경보(EWS)를 갖춘 PoC 시스템입니다.
            </p>
          </div>

          {/* 브랜드 그라디언트 띠 */}
          <div className="im-gradient h-1.5" />
        </div>

        {/* 기능 소개 */}
        <div className="px-6 py-5">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">주요 기능</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {FEATURES.map((f) => (
              <div key={f.title} className="flex items-start gap-3 p-2.5 rounded-lg bg-gray-50">
                <span className="mt-0.5 w-8 h-8 shrink-0 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center">
                  {f.icon}
                </span>
                <div>
                  <p className="text-sm font-semibold text-gray-900">{f.title}</p>
                  <p className="text-xs text-gray-500 leading-snug">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>

          {/* 테마 선택 */}
          <div className="mt-5">
            <div className="flex items-center gap-1.5 mb-3">
              <Sparkles size={14} className="text-blue-600" />
              <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">화면 테마 선택</h2>
            </div>
            <div className="flex gap-3">
              <ThemeCard
                value="classic" label="Classic" desc="깔끔한 플랫 UI"
                selected={theme === 'classic'} onSelect={setTheme} previewClass="mini-flat"
              />
              <ThemeCard
                value="mesh" label="Gradient Mesh" desc="민트·라임 메시 배경"
                selected={theme === 'mesh'} onSelect={setTheme} previewClass="mini-mesh"
              />
            </div>
            <p className="text-xs text-gray-400 mt-2">
              테마는 우측 상단 설정(⚙)에서 언제든 바꿀 수 있습니다.
            </p>
          </div>
        </div>

        {/* 구축 규모 - '무엇을 하는 시스템인가' 만으로는 PoC 완성도가 전달되지 않는다.
            실제로 얼마나 만들어졌는지 숫자로 보여준다. */}
        <div className="px-6 pb-5">
          <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3">
            <p className="text-[11px] font-semibold text-gray-400 tracking-wider mb-2">구축 규모</p>
            <div className="grid grid-cols-4 gap-3 text-center">
              {[
                { n: '25',     l: '화면' },
                { n: '210',    l: 'API' },
                { n: '84',     l: 'DB 테이블' },
                { n: '1,200',  l: '여신' },
              ].map(s => (
                <div key={s.l}>
                  <p className="text-base font-bold text-gray-900 tabular leading-tight">{s.n}</p>
                  <p className="text-[11px] text-gray-500">{s.l}</p>
                </div>
              ))}
            </div>
            <p className="text-[11px] text-gray-500 mt-2.5 leading-relaxed">
              Basel IRB · IFRS 9 · 금융감독규정 기준 산식 내장 -
              고객 1,010개 · 자산건전성 분류 이력 14,400건
            </p>
          </div>
        </div>

        {/* 푸터 */}
        <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between">
          <span className="text-xs text-gray-400">v1.0.0 · PoC · © 2026 yalkongs</span>
          <div className="flex items-center gap-2">
            {/* 스토리 투어 - 한 기업의 생애주기 악화 경로(경보→위반→강등→연체→회수)를
                화면 순서대로 안내한다 */}
            <button
              onClick={() => onClose(true)}
              className="btn-mint px-5 text-sm"
            >
              🧭 스토리 투어
            </button>
            <button
              onClick={() => onClose()}
              className="btn-accent px-5 text-sm"
            >
              시작하기
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
