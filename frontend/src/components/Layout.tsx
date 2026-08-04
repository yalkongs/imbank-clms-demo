import React, { useState, useEffect } from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
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
  Info
} from 'lucide-react';
import { useTheme } from '../context/ThemeProvider';
import OnboardingModal from './OnboardingModal';
import { AlertMenu, SettingsMenu } from './HeaderMenus';
import MockDataNotice from './MockDataNotice';
import UserMenu from './UserMenu';
import CommandPalette from './CommandPalette';
import StoryTour from './StoryTour';

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
      { path: '/inclusive-finance', label: '포용금융 이행', icon: <HeartHandshake size={20} /> },
    ]
  },
  {
    title: '리스크 모니터링',
    items: [
      { path: '/ews-advanced', label: 'EWS 조기경보', icon: <AlertTriangle size={20} /> },
      { path: '/collateral-monitoring', label: '담보 모니터링', icon: <Home size={20} /> },
      { path: '/asset-classification', label: '자산건전성 분류', icon: <ListChecks size={20} /> },
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

export default function Layout() {
  const { setOnboarded, setIntroOpen } = useTheme();
  // 접속·새로고침 때마다 소개 팝업을 띄운다.
  // (종전에는 localStorage 의 clms-onboarded 로 최초 1회만 표시했다.)
  const [showOnboarding, setShowOnboarding] = useState(true);
  // 모의 데이터 고지 - 소개 팝업이 닫힌 직후 1회 표시하고 명시적 확인을 받는다.
  // (ⓘ 로 소개를 다시 열었다 닫을 때는 반복하지 않는다)
  const [showMockNotice, setShowMockNotice] = useState(false);
  const [mockNoticeDone, setMockNoticeDone] = useState(false);
  // 스토리 투어 - null 이면 비활성. 온보딩에서 '스토리 투어'로 닫으면 고지 확인 후 시작
  const [tourStep, setTourStep] = useState<number | null>(null);
  const [pendingTour, setPendingTour] = useState(false);
  // 기준일은 백엔드 단일 소스(AS_OF_DATE)에서 받는다 - 화면에 날짜를 박아두지 않는다.
  const [asOfLabel, setAsOfLabel] = useState('');

  const navigate = useNavigate();
  const location = useLocation();

  // 접속·새로고침 시에는 항상 대시보드에서 시작한다.
  // 소개 팝업 → 모의 데이터 고지 → 대시보드 카운트업으로 이어지는 진입 경험을
  // 어느 화면에서 새로고침해도 동일하게 유지하기 위함이다. (마운트 1회만 실행)
  useEffect(() => {
    if (location.pathname !== '/') {
      navigate('/', { replace: true });
    }
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
    if (!mockNoticeDone) {
      // 카운트업은 고지까지 닫힌 뒤 시작해야 하므로 introOpen 을 유지한다
      setShowMockNotice(true);
    } else {
      setIntroOpen(false);
      if (startTour) setTourStep(0);
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
    <div className="app-root flex h-screen bg-gray-50">
      {showOnboarding && <OnboardingModal onClose={closeOnboarding} />}
      {showMockNotice && <MockDataNotice onConfirm={confirmMockNotice} />}
      <CommandPalette />
      {tourStep !== null && (
        <StoryTour step={tourStep} onStep={setTourStep} onExit={() => setTourStep(null)} />
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
        <nav className="flex-1 py-4 overflow-y-auto">
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
            <h2 className="text-xl font-semibold text-gray-900">종합 기업여신 관리시스템</h2>
            <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full font-medium">
              {asOfLabel}
            </span>
          </div>

          <div className="flex items-center space-x-4">

            {/* 소개 팝업 다시 보기 */}
            <button
              onClick={() => { setShowOnboarding(true); setIntroOpen(true); }}
              aria-label="시스템 소개 다시 보기"
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              <Info size={20} />
            </button>

            {/* 전역 검색 (Cmd+K) */}
            <button
              onClick={() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }))}
              aria-label="검색"
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
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
