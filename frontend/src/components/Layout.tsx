import React, { useState, useEffect } from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Menu,
  LayoutGrid,
  LayoutDashboard,
  FileText,
  PiggyBank,
  PieChart,
  Gauge,
  Activity,
  Brain,
  Building2,
  Users,
  TrendingUp,
  AlertTriangle,
  Target,
  UserCheck,
  Home,
  Layers,
  Briefcase,
  Leaf,
  TrendingDown,
  Search,
  FileCheck,
  ListChecks,
  AlertOctagon,
  HeartHandshake,
  ShieldCheck,
  Stamp,
  Landmark,
  Info,
  Percent
} from 'lucide-react';
import { useTheme } from '../context/ThemeProvider';
import OnboardingModal from './OnboardingModal';
import { AlertMenu, SettingsMenu } from './HeaderMenus';
import MockDataNotice from './MockDataNotice';
import UserMenu from './UserMenu';
import TopProgressBar from './TopProgressBar';
import CommandPalette from './CommandPalette';
import StoryTour from './StoryTour';
import DevJourneyModal from './DevJourneyModal';

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

export const navGroups: NavGroup[] = [
  {
    title: '현황',
    items: [
      { path: '/', label: '대시보드', icon: <LayoutDashboard size={20} /> },
      { path: '/governance', label: '보고·감사', icon: <ShieldCheck size={20} /> },
      { path: '/obligations', label: '의무관리함', icon: <ListChecks size={20} /> },
    ]
  },
  {
    // 여신 생애주기 순서로 배치한다: 심사·실행 → 모니터링 → 회수.
    // 종전 '여신 심사 고도화' · '부실 관리' 는 개발 Phase 이름이 그대로 노출된 것이었다.
    title: '여신 업무',
    items: [
      { path: '/applications', label: '여신신청', icon: <FileText size={20} /> },
      { path: '/approval-inbox', label: '결재함', icon: <Stamp size={20} /> },
      { path: '/covenant', label: '코베넌트 관리', icon: <FileCheck size={20} /> },
      { path: '/rate-reduction', label: '금리인하요구권', icon: <Percent size={20} /> },
      { path: '/inclusive-finance', label: '포용금융 이행', icon: <HeartHandshake size={20} /> },
    ]
  },
  {
    title: '리스크 모니터링',
    items: [
      { path: '/ews-advanced', label: 'EWS 조기경보', icon: <AlertTriangle size={20} /> },
      { path: '/collateral-monitoring', label: '담보 모니터링', icon: <Home size={20} /> },
      { path: '/asset-classification', label: '자산건전성 분류', icon: <ListChecks size={20} /> },
      { path: '/portfolio-map', label: '포트폴리오 맵', icon: <Target size={20} /> },
      { path: '/pf-monitoring', label: 'PF 사업장', icon: <Landmark size={20} /> },
    ]
  },
  {
    title: '회수·정상화',
    items: [
      { path: '/delinquency', label: '연체 관리', icon: <AlertOctagon size={20} /> },
      { path: '/workout', label: '부실채권 관리', icon: <Briefcase size={20} /> },
    ]
  },
  {
    // 조회 화면과 최적화 시뮬레이션은 같은 대상의 두 국면이라 페이지 안 탭으로 합쳤다.
    // (구 /capital-optimizer · /portfolio-optimization · /dynamic-limits)
    title: '포트폴리오·자본',
    items: [
      { path: '/portfolio', label: '포트폴리오', icon: <PieChart size={20} /> },
      { path: '/capital', label: '자본관리', icon: <PiggyBank size={20} /> },
      { path: '/limits', label: '한도관리', icon: <Gauge size={20} /> },
      { path: '/alm', label: 'ALM', icon: <TrendingDown size={20} /> },
    ]
  },
  {
    title: '분석·모델',
    items: [
      { path: '/stress-test', label: '스트레스 테스트', icon: <Activity size={20} /> },
      { path: '/esg', label: 'ESG 리스크', icon: <Leaf size={20} /> },
      { path: '/models', label: '모델관리 (MRM)', icon: <Brain size={20} /> },
    ]
  },
  {
    title: '고객',
    items: [
      { path: '/customers', label: '고객관리', icon: <Users size={20} /> },
      { path: '/customer-browser', label: '고객 조회', icon: <Search size={20} /> },
      { path: '/customer-profitability', label: '고객 수익성', icon: <UserCheck size={20} /> },
    ]
  },
];

// 브라우저 새로고침(스크립트 재로드)과 SPA 내 재마운트를 구분하는 세션 플래그.
// '/m 에서 데스크탑 화면으로 이동' 시 소개 팝업·대시보드 리다이렉트가 다시
// 발동하면 Tier 2 진입이 불가능해진다.
let bootConsumed = false;

export default function Layout() {
  const { setOnboarded, setIntroOpen } = useTheme();
  // 접속·새로고침 때마다 소개 팝업을 먼저 띄우고 대시보드에서 시작한다
  // (사용자 지정 동작 - 소개 → 고지 → 대시보드 카운트업 진입 경험을
  //  어느 화면에서 새로고침해도 동일하게 유지한다)
  const [showOnboarding, setShowOnboarding] = useState(() => !bootConsumed && window.innerWidth >= 768);
  // 개발 여정 대형 팝업 - 소개 팝업에서 진입하거나, 첫 방문 필수 코스로 표시
  const [showDevJourney, setShowDevJourney] = useState(false);
  const [devJourneyForced, setDevJourneyForced] = useState(false);
  // 첫 방문 여부 (개발 여정 필수 코스를 이미 봤는가)
  const [journeySeen] = useState(() => {
    try { return localStorage.getItem('clms-devjourney-seen') === '1'; } catch { return true; }
  });
  // 모바일(Tier 2): 데스크탑 화면을 폰에서 열었을 때 사이드바를 오버레이로 토글
  const [sidebarOpen, setSidebarOpen] = useState(false);
  // 모의 데이터 고지 - 소개 팝업이 닫힌 직후 1회 표시하고 명시적 확인을 받는다.
  // (ⓘ 로 소개를 다시 열었다 닫을 때는 반복하지 않는다)
  const [showMockNotice, setShowMockNotice] = useState(false);
  const [mockNoticeDone, setMockNoticeDone] = useState(false);
  // 스토리 투어 - null 이면 비활성. 온보딩에서 '스토리 투어'로 닫으면 고지 확인 후 시작
  const [tourStep, setTourStep] = useState<number | null>(null);
  const [pendingTour, setPendingTour] = useState(false);
  // 투어 종료 직후 잠깐 표시하는 안내 (대시보드로 이동했음을 알린다)
  const [tourEndNotice, setTourEndNotice] = useState(false);
  useEffect(() => {
    if (!tourEndNotice) return;
    const t = setTimeout(() => setTourEndNotice(false), 3500);
    return () => clearTimeout(t);
  }, [tourEndNotice]);
  // 기준일은 백엔드 단일 소스(AS_OF_DATE)에서 받는다 - 화면에 날짜를 박아두지 않는다.
  const [asOfLabel, setAsOfLabel] = useState('');

  const navigate = useNavigate();
  const location = useLocation();

  // 접속·새로고침 시에는 항상 대시보드에서 시작한다. (스크립트 로드 후 최초 1회만 -
  // 모바일 화면에서 돌아온 재마운트에서는 열려던 화면을 유지한다)
  useEffect(() => {
    if (!bootConsumed && location.pathname !== '/') {
      navigate('/', { replace: true });
    }
    bootConsumed = true;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 모바일 진입은 소개 팝업을 건너뛰므로 카운트업 게이트도 즉시 해제
  useEffect(() => {
    if (window.innerWidth < 768) setIntroOpen(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetch('/api/system/as-of')
      .then(r => r.json())
      .then(d => setAsOfLabel(d.label_ko))
      .catch(() => setAsOfLabel(''));
  }, []);

  const closeOnboarding = (startTour?: boolean) => {
    setShowOnboarding(false);
    // 테마 선택은 계속 저장한다 - 팝업 표시 여부와는 무관하다.
    setOnboarded(true);
    if (startTour) setPendingTour(true);

    // 첫 방문 필수 코스: 소개 → [개발 여정] → 고지 → 대시보드/투어.
    // 어떻게 만들어졌는지(바이브 코딩)를 반드시 보고 지나가게 한다.
    let seen = journeySeen;
    try { seen = localStorage.getItem('clms-devjourney-seen') === '1'; } catch { /* 무시 */ }
    if (!seen) {
      setDevJourneyForced(true);
      setShowDevJourney(true);
      return;   // 모의 데이터 고지는 개발 여정을 닫은 뒤 이어진다
    }

    if (!mockNoticeDone) {
      // 카운트업은 고지까지 닫힌 뒤 시작해야 하므로 introOpen 을 유지한다
      setShowMockNotice(true);
    } else {
      setIntroOpen(false);
      if (startTour) setTourStep(0);
    }
  };

  // 개발 여정 닫기 - 필수 코스였다면 다음 단계(고지 → 대시보드/투어)로 이어간다
  const closeDevJourney = () => {
    setShowDevJourney(false);
    if (!devJourneyForced) return;
    setDevJourneyForced(false);
    try { localStorage.setItem('clms-devjourney-seen', '1'); } catch { /* 무시 */ }
    if (!mockNoticeDone) {
      setShowMockNotice(true);
    } else {
      setIntroOpen(false);
      if (pendingTour) { setPendingTour(false); setTourStep(0); }
    }
  };

  const confirmMockNotice = () => {
    setShowMockNotice(false);
    setMockNoticeDone(true);
    setIntroOpen(false);   // 이제 대시보드 카운트업 시작
    if (pendingTour) {
      setPendingTour(false);
      setTourStep(0);
    }
  };

  return (
    <div className={`app-root flex h-screen bg-gray-50 ${sidebarOpen ? 'sidebar-open' : ''}`}>
      {showOnboarding && <OnboardingModal onClose={closeOnboarding} onDevJourney={() => setShowDevJourney(true)} journeyNext={!journeySeen} />}
      {showMockNotice && <MockDataNotice onConfirm={confirmMockNotice} />}
      {showDevJourney && <DevJourneyModal forced={devJourneyForced} onClose={closeDevJourney} />}
      <TopProgressBar />
      <CommandPalette />
      {tourStep !== null && (
        <StoryTour step={tourStep} onStep={setTourStep}
          onExit={() => { setTourStep(null); setTourEndNotice(true); }}
          onDevJourney={() => setShowDevJourney(true)} />
      )}
      {tourEndNotice && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[65] px-4 py-2.5 bg-gray-900/90 text-white text-sm rounded-full shadow-lg">
          스토리 투어가 종료되어 대시보드로 이동했습니다
        </div>
      )}

      {/* 모바일 하단 탭바 - 데스크탑 화면(Tier 2)을 폰에서 볼 때도 모바일 동선 유지 */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-[60] bg-white border-t border-gray-200 flex"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
        {[
          { to: '/m', label: '홈', icon: Home },
          { to: '/m/approval', label: '결재', icon: Stamp },
          { to: '/m/alerts', label: '경보', icon: AlertTriangle },
          { to: '/m/obligations', label: '의무', icon: ListChecks },
          { to: '/m/more', label: '전체', icon: LayoutGrid },
        ].map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to}
            className="flex-1 flex flex-col items-center justify-center gap-0.5 h-[3.75rem] text-[10px] font-medium text-gray-400">
            <Icon size={20} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* 사이드바 오버레이 백드롭 (모바일 전용) */}
      {sidebarOpen && (
        <div className="md:hidden fixed inset-0 z-[65] bg-black/40"
          onClick={() => setSidebarOpen(false)} />
      )}

      {/* 사이드바 */}
      <aside className="app-sidebar w-64 bg-white border-r border-gray-200 flex flex-col">
        {/* 로고 영역 - 공식 가로형 국문 시그니처 (iM Financial Design System).
            시스템명은 상단 헤더에 있으므로 로고만 둔다. */}
        <div className="h-16 flex items-center px-6 border-b border-gray-200">
          <img
            src="/brand/imbank-logo-h-kr.jpg"
            alt="iM뱅크"
            className="h-7 w-auto"
          />
        </div>

        {/* 네비게이션 */}
        <nav className="flex-1 py-4 overflow-y-auto" onClick={() => setSidebarOpen(false)}>
          {navGroups.map((group) => (
            <div key={group.title} className="mb-4">
              <h3 className="px-6 mb-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                {group.title}
              </h3>
              <ul className="space-y-0.5 px-3">
                {group.items.map((item) => (
                  <li key={item.path}>
                    <NavLink
                      to={item.path}
                      className={({ isActive }) =>
                        `flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-200 ${
                          isActive
                            ? 'bg-blue-50 text-blue-700'
                            : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                        }`
                      }
                    >
                      <span className="mr-3">{item.icon}</span>
                      {item.label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        {/* 하단 정보 */}
        <div className="p-4 border-t border-gray-200">
          <div className="flex items-center text-xs text-gray-500">
            <span className="status-dot is-live mr-2"></span>
            시스템 정상 운영중
          </div>
          <p className="text-xs text-gray-400 mt-1">v1.0.0 | PoC</p>
          <p className="text-[10px] text-gray-400 mt-1">© 2026 yalkongs</p>
        </div>
      </aside>

      {/* 메인 콘텐츠 영역 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 헤더 */}
        <header className="app-header relative z-40 h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
          <div className="flex items-center space-x-4">
            <button onClick={() => setSidebarOpen(v => !v)} aria-label="메뉴"
              className="md:hidden p-2 -ml-2 text-gray-600 hover:bg-gray-100 rounded-lg">
              <Menu size={22} />
            </button>
            <h2 className="text-xl font-semibold text-gray-900 truncate">종합 기업여신 관리시스템</h2>
            <span className="hide-on-mobile px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full font-medium">
              {asOfLabel}
            </span>
            <button onClick={() => { try { localStorage.setItem('clms-view-mode', 'mobile'); } catch {} navigate('/m'); }}
              className="md:hidden flex-none px-2 py-1 bg-[#00C7A9]/10 text-[#00897B] text-xs rounded-full font-semibold">
              모바일 홈
            </button>
          </div>

          <div className="flex items-center space-x-4">

            {/* 소개 팝업 다시 보기 */}
            <button
              onClick={() => { setShowOnboarding(true); setIntroOpen(true); }}
              aria-label="시스템 소개 다시 보기"
              className="hide-on-mobile p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              <Info size={20} />
            </button>

            {/* 전역 검색 (Cmd+K) */}
            <button
              onClick={() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }))}
              aria-label="검색"
              className="hide-on-mobile p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              <Search size={20} />
            </button>

            {/* 알림 - EWS 경보 연동 */}
            <AlertMenu />

            {/* 설정 - 화면 테마·기준일 */}
            <SettingsMenu asOfLabel={asOfLabel} />

            {/* 사용자 - 역할 전환 */}
            <UserMenu />
          </div>
        </header>

        {/* 페이지 콘텐츠 */}
        <main className="app-main flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
