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

export default function OnboardingModal({ onClose }: { onClose: () => void }) {
  const { theme, setTheme } = useTheme();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="modal-in w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-white rounded-2xl shadow-2xl">
        {/* 헤더 */}
        <div className="relative px-6 pt-6 pb-5 rounded-t-2xl bg-gradient-to-br from-blue-600 to-blue-800 text-white overflow-hidden">
          <div className="absolute -top-8 -right-8 w-40 h-40 rounded-full" style={{ background: 'radial-gradient(circle, rgba(174,234,0,0.35), transparent 70%)' }} />
          <button
            onClick={onClose}
            aria-label="닫기"
            className="absolute top-4 right-4 p-1.5 rounded-lg text-white/80 hover:bg-white/15"
          >
            <X size={18} />
          </button>
          <div className="flex items-center gap-3 relative">
            <div className="w-11 h-11 rounded-xl bg-white/15 flex items-center justify-center">
              <Building2 size={24} />
            </div>
            <div>
              <h1 className="text-xl font-bold leading-tight">iM뱅크 CLMS</h1>
              <p className="text-sm text-white/80">기업여신 전(全) 생애주기 통합 관리 시스템</p>
            </div>
          </div>
          <p className="mt-4 text-sm text-white/90 leading-relaxed relative">
            심사 · 실행 · 모니터링 · 회수까지 — 기업여신의 리스크를 하나의 화면에서.
            Basel · IFRS9 기반의 리스크 계산 엔진과 5채널 조기경보(EWS)를 갖춘 PoC 데모입니다.
          </p>
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
              테마는 우측 상단 버튼으로 언제든 바꿀 수 있습니다.
            </p>
          </div>
        </div>

        {/* 푸터 */}
        <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between">
          <span className="text-xs text-gray-400">v1.0.0 · Demo Mode</span>
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-lg bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 transition-colors"
          >
            시작하기
          </button>
        </div>
      </div>
    </div>
  );
}
