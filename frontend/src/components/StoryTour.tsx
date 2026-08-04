import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, ChevronLeft, ChevronRight, MapPin } from 'lucide-react';

/**
 * 시나리오 스토리 투어
 *
 * 24개 화면을 나열하면 평가자는 어디를 봐야 할지 모른다. 한 기업
 * ((주)영남바이오)의 생애주기 악화 경로를 따라 화면을 순서대로 안내해,
 * "생애주기 관리"라는 시스템의 존재 이유를 몇 분 안에 증명한다.
 */

export interface TourStep {
  route: string;
  title: string;
  body: string;
  hint?: string;
}

export const TOUR_STEPS: TourStep[] = [
  {
    route: '/',
    title: '① 경보의 시작 - 대시보드',
    body: '(주)영남바이오(부동산PF 시행)의 한도소진율이 94%까지 치솟으며 EWS 경보가 발생했습니다. 우측 상단 종 아이콘과 대시보드 EWS 알림에서 확인됩니다.',
    hint: '종 아이콘의 경보 목록에서 기업을 클릭하면 상세로 이동합니다',
  },
  {
    route: '/ews-advanced',
    title: '② 5채널 조기경보',
    body: '거래행태(한도소진·출금 급증) 채널이 먼저 신호를 잡았습니다. 종합점수 41.2점(WARNING) - 재무제표에 나타나기 전에 행동 데이터가 먼저 움직입니다.',
  },
  {
    route: '/covenant',
    title: '③ 코베넌트 위반',
    body: '반기 점검에서 부채비율 247%로 약정(200% 이하)을 위반했습니다. MAJOR 위반 - 추가 담보 요구와 30일 치유 기간이 부여됐습니다.',
  },
  {
    route: '/asset-classification',
    title: '④ 건전성 강등',
    body: 'DPD·PD·EWS 중 가장 불리한 기준을 적용하는 보수주의 원칙에 따라 분류가 강등됩니다. 강등은 충당금 적립률 상승으로 직결됩니다 (요주의 7%, 고정 20%).',
  },
  {
    route: '/delinquency',
    title: '⑤ 연체 발생',
    body: '결국 이자 연체가 발생했습니다. DPD 버킷 관리와 추심 활동 기록이 시작되고, 90일 도달 시 워크아웃으로 자동 이관됩니다.',
  },
  {
    route: '/workout',
    title: '⑥ 워크아웃 - 회수 절차',
    body: '(주)영남바이오는 워크아웃 케이스로 이관되어 회수 시나리오(매각/법적회수/정상화)의 NPV를 비교하고, 절차 타임라인을 따라 회수가 진행 중입니다. 케이스를 클릭해 보세요.',
    hint: '이것이 심사→모니터링→회수로 이어지는 여신 생애주기 관리의 전체 흐름입니다',
  },
];

interface Props {
  step: number;
  onStep: (n: number) => void;
  onExit: () => void;
}

export default function StoryTour({ step, onStep, onExit }: Props) {
  const navigate = useNavigate();
  const cur = TOUR_STEPS[step];

  useEffect(() => {
    if (cur) navigate(cur.route);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

  // 투어가 어떤 경로로 끝나든(마치기·X) 시작점인 대시보드로 되돌린다.
  // 투어는 화면 6곳을 순회하므로, 끝난 자리에 그대로 두면 사용자가 길을 잃는다.
  const exitTour = () => {
    navigate('/');
    onExit();
  };

  if (!cur) return null;

  const isLast = step === TOUR_STEPS.length - 1;

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[65] w-full max-w-xl px-4">
      <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden">
        <div className="im-gradient h-1" />
        <div className="p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <span className="mt-0.5 w-8 h-8 flex-none rounded-full bg-blue-100 text-blue-700 flex items-center justify-center">
                <MapPin size={16} />
              </span>
              <div>
                <p className="text-sm font-bold text-gray-900">{cur.title}</p>
                <p className="text-sm text-gray-600 mt-1 leading-relaxed">{cur.body}</p>
                {cur.hint && <p className="text-xs text-blue-600 mt-1.5">💡 {cur.hint}</p>}
              </div>
            </div>
            <button onClick={exitTour} aria-label="투어 종료"
                    className="p-1 text-gray-400 hover:text-gray-600 rounded flex-none">
              <X size={16} />
            </button>
          </div>

          {isLast && (
            <p className="text-xs text-gray-400 mt-3">
              투어를 마치면 첫 화면(대시보드)으로 이동합니다.
            </p>
          )}

          <div className="flex items-center justify-between mt-4">
            <div className="flex gap-1">
              {TOUR_STEPS.map((_, i) => (
                <span key={i}
                      className={`w-1.5 h-1.5 rounded-full ${i === step ? 'bg-blue-600' : i < step ? 'bg-blue-300' : 'bg-gray-200'}`} />
              ))}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => onStep(step - 1)}
                disabled={step === 0}
                className="flex items-center gap-1 px-3 py-1.5 text-xs border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40"
              >
                <ChevronLeft size={14} /> 이전
              </button>
              {!isLast ? (
                <button onClick={() => onStep(step + 1)}
                        className="flex items-center gap-1 px-4 py-1.5 text-xs font-semibold bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                  다음 <ChevronRight size={14} />
                </button>
              ) : (
                <button onClick={exitTour} className="btn-accent px-4 py-1.5 text-xs">
                  투어 마치기
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
