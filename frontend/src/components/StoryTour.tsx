import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, ChevronLeft, ChevronRight, MapPin } from 'lucide-react';

/**
 * 시나리오 스토리 투어
 *
 * 40여 개 화면을 나열하면 평가자는 어디를 봐야 할지 모른다. 한 기업
 * ((주)영남바이오)의 생애주기 악화 경로(경보→위반→연장통제→강등→연체→회수)를
 * 따라간 뒤, 은행 전체의 손실흡수력과 자본(CET1 경로)까지 올라가
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
    title: '② 8채널 조기경보',
    body: '거래행태(한도소진·출금 급증) 채널이 먼저 신호를 잡았습니다. 종합점수 41.2점(WARNING) - 재무제표에 나타나기 전에 행동 데이터가 먼저 움직입니다.',
  },
  {
    route: '/portfolio-map?sel=CUST00339',
    title: '③ 포트폴리오 맵 - 무리에서 벗어나다',
    body: '포트폴리오 지형에서 보면 (주)영남바이오는 한도소진율 94%로 1,999개사 무리에서 멀리 벗어나 있습니다. 하단 ▶ 재생을 누르면 최근 12개월간 우측(고소진)으로 이동해 온 악화 경로가 재생됩니다.',
    hint: '선택된 포인트를 드래그하면 what-if 모의 조정(EL·분류·충당금 재계산)도 해볼 수 있습니다',
  },
  {
    route: '/covenant',
    title: '④ 코베넌트 위반',
    body: '반기 점검에서 부채비율 247%로 약정(200% 이하)을 위반했습니다. MAJOR 위반 - 추가 담보 요구와 30일 치유 기간이 부여됐습니다.',
  },
  {
    route: '/lifecycle',
    title: '⑤ 만기연장 요청 - 에버그리닝 통제',
    body: '위기의 기업은 만기연장을 원합니다. 연장 심사에는 EWS·건전성 분류·약정 위반 이력이 서버에서 강제 표시되고, 플래그가 있으면 부서장 이상 결재로 자동 상향됩니다 - 만기연장으로 부실을 이연(에버그리닝)하는 관행을 통제하는 장치입니다.',
    hint: '위험 표식이 있는 여신에 [연장]을 눌러 보세요 - 플래그가 결재선을 바꿉니다',
  },
  {
    route: '/asset-classification',
    title: '⑥ 건전성 강등',
    body: 'DPD·PD·EWS 중 가장 불리한 기준을 적용하는 보수주의 원칙에 따라 분류가 강등됩니다. 강등은 충당금 적립률 상승으로 직결됩니다 (요주의 7%, 고정 20%).',
  },
  {
    route: '/delinquency',
    title: '⑦ 연체 발생',
    body: '결국 이자 연체가 발생했습니다. DPD 버킷 관리와 추심 활동 기록이 시작되고, 90일 도달 시 워크아웃으로 자동 이관됩니다.',
  },
  {
    route: '/workout',
    title: '⑧ 워크아웃 - 회수 절차',
    body: '(주)영남바이오는 워크아웃 케이스로 이관되어 회수 시나리오(매각/법적회수/정상화)의 NPV를 비교하고, 절차 타임라인을 따라 회수가 진행 중입니다.',
  },
  {
    route: '/loss-absorption',
    title: '⑨ 손실흡수력 관리',
    body: '개별 부실은 은행 전체의 손실흡수력 문제로 이어집니다. NPL커버리지 목표 경로를 충당금 적립·상각·NPL 매각 세 레버로 설계하고, 목표 달성에 필요한 적립액을 역산합니다.',
    hint: '레버를 움직이면 연말 커버리지 경로와 필요 적립액이 즉시 재계산됩니다',
  },
  {
    route: '/cet1-path',
    title: '⑩ CET1 경로 - 자본이라는 최후의 층',
    body: '손실을 흡수하는 마지막 층은 자본입니다. 밸류업 목표 CET1 12.3%를 output floor 단계 상향(65→72.5%) 일정 위에서 관리합니다. 심사→모니터링→회수→손실흡수·자본까지, 이것이 여신 생애주기 관리의 전체 흐름입니다.',
  },
];

interface Props {
  step: number;
  onStep: (n: number) => void;
  onExit: () => void;
  /** 개발 여정 팝업 열기 - 투어 카드 하단 링크에서 진입 */
  onDevJourney?: () => void;
}

export default function StoryTour({ step, onStep, onExit, onDevJourney }: Props) {
  const navigate = useNavigate();
  const cur = TOUR_STEPS[step];

  useEffect(() => {
    if (cur) navigate(cur.route);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

  // 투어가 어떤 경로로 끝나든(마치기·X) 시작점인 대시보드로 되돌린다.
  // 투어는 화면 10곳을 순회하므로, 끝난 자리에 그대로 두면 사용자가 길을 잃는다.
  const exitTour = () => {
    navigate('/');
    onExit();
  };

  if (!cur) return null;

  const isLast = step === TOUR_STEPS.length - 1;

  return (
    <>
      {/* 옅은 스크림 - 카드로 시선을 모으되 클릭은 통과시켜 화면 탐색을 막지 않는다 */}
      <div className="fixed inset-0 z-[64] bg-black/25 pointer-events-none transition-opacity" aria-hidden="true" />
      <div className="fixed bottom-12 left-1/2 -translate-x-1/2 z-[65] w-full max-w-2xl px-4">
      <div className="modal-in bg-white rounded-2xl border border-gray-200 overflow-hidden"
           style={{ boxShadow: '0 24px 60px rgba(0,0,0,0.35), 0 0 0 4px rgba(0,199,169,0.25)' }}>
        <div className="im-gradient h-1.5" />
        <div className="p-6">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3.5">
              <span className="mt-0.5 w-10 h-10 flex-none rounded-full im-gradient text-white flex items-center justify-center shadow-md">
                <MapPin size={18} />
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-base font-bold text-gray-900">{cur.title}</p>
                  <span className="px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded text-[11px] font-semibold flex-none">
                    {step + 1} / {TOUR_STEPS.length}
                  </span>
                </div>
                <p className="text-[15px] text-gray-600 mt-1.5 leading-relaxed">{cur.body}</p>
                {cur.hint && <p className="text-sm text-blue-600 mt-2">💡 {cur.hint}</p>}
              </div>
            </div>
            <button onClick={exitTour} aria-label="투어 종료"
                    className="p-1 text-gray-400 hover:text-gray-600 rounded flex-none">
              <X size={18} />
            </button>
          </div>

          {isLast && (
            <p className="text-xs text-gray-400 mt-3">
              투어를 마치면 첫 화면(대시보드)으로 이동합니다.
            </p>
          )}

          <div className="flex items-center justify-between mt-5">
            <div className="flex items-center gap-3">
              <div className="flex gap-1.5">
                {TOUR_STEPS.map((_, i) => (
                  <span key={i}
                        className={`h-2 rounded-full transition-all ${
                          i === step ? 'w-6 bg-[#00BFA5]' : i < step ? 'w-2 bg-[#00BFA5]/40' : 'w-2 bg-gray-200'
                        }`} />
                ))}
              </div>
              {onDevJourney && (
                <button onClick={onDevJourney}
                  className="text-xs font-medium text-[#00897B] hover:text-[#00BFA5] hover:underline">
                  ✨ 개발 여정
                </button>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => onStep(step - 1)}
                disabled={step === 0}
                className="flex items-center gap-1 px-3.5 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40"
              >
                <ChevronLeft size={15} /> 이전
              </button>
              {!isLast ? (
                <button onClick={() => onStep(step + 1)}
                        className="flex items-center gap-1 px-5 py-2 text-sm font-semibold bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                  다음 <ChevronRight size={15} />
                </button>
              ) : (
                <button onClick={exitTour} className="btn-accent px-5 py-2 text-sm">
                  투어 마치기
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
      </div>
    </>
  );
}
