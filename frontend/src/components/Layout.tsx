import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  PiggyBank,
  PieChart,
  Gauge,
  Activity,
  Brain,
  Building2,
  Bell,
  Settings,
  Users,
  TrendingUp,
  AlertTriangle,
  Target,
  UserCheck,
  Home,
  Layers,
  Briefcase,
  Leaf,
  TrendingDown
} from 'lucide-react';

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    title: '핵심 업무',
    items: [
      { path: '/', label: 'Dashboard', icon: <LayoutDashboard size={20} /> },
      { path: '/applications', label: '여신신청', icon: <FileText size={20} /> },
      { path: '/customers', label: '고객관리', icon: <Users size={20} /> },
    ]
  },
  {
    title: '자본/포트폴리오',
    items: [
      { path: '/capital', label: '자본관리', icon: <PiggyBank size={20} /> },
      { path: '/capital-optimizer', label: '자본최적화', icon: <TrendingUp size={20} /> },
      { path: '/portfolio', label: '포트폴리오', icon: <PieChart size={20} /> },
      { path: '/portfolio-optimization', label: '포트폴리오최적화', icon: <Layers size={20} /> },
    ]
  },
  {
    title: '리스크 관리',
    items: [
      { path: '/limits', label: '한도관리', icon: <Gauge size={20} /> },
      { path: '/dynamic-limits', label: '동적한도', icon: <Target size={20} /> },
      { path: '/ews-advanced', label: 'EWS고도화', icon: <AlertTriangle size={20} /> },
      { path: '/stress-test', label: '스트레스테스트', icon: <Activity size={20} /> },
      { path: '/alm', label: 'ALM', icon: <TrendingDown size={20} /> },
    ]
  },
  {
    title: '고객/담보',
    items: [
      { path: '/customer-profitability', label: '고객수익성', icon: <UserCheck size={20} /> },
      { path: '/collateral-monitoring', label: '담보모니터링', icon: <Home size={20} /> },
      { path: '/workout', label: 'Workout', icon: <Briefcase size={20} /> },
    ]
  },
  {
    title: 'ESG/모델',
    items: [
      { path: '/esg', label: 'ESG리스크', icon: <Leaf size={20} /> },
      { path: '/models', label: '모델관리', icon: <Brain size={20} /> },
    ]
  },
];

export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-50">
      {/* 사이드바 */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        {/* 로고 영역 */}
        <div className="h-16 flex items-center px-6 border-b border-gray-200">
          <Building2 className="text-blue-600 mr-3" size={28} />
          <div>
            <h1 className="text-lg font-bold text-gray-900">iM뱅크</h1>
            <p className="text-xs text-gray-500">CLMS 데모</p>
          </div>
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
            <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
            시스템 정상 운영중
          </div>
          <p className="text-xs text-gray-400 mt-1">v1.0.0 | Demo Mode</p>
        </div>
      </aside>

      {/* 메인 콘텐츠 영역 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 헤더 */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
          <div className="flex items-center space-x-4">
            <h2 className="text-xl font-semibold text-gray-900">기업여신심사시스템</h2>
            <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full font-medium">
              2024년 1월 기준
            </span>
          </div>

          <div className="flex items-center space-x-4">
            {/* 알림 */}
            <button className="relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg">
              <Bell size={20} />
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
            </button>

            {/* 설정 */}
            <button className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg">
              <Settings size={20} />
            </button>

            {/* 사용자 */}
            <div className="flex items-center">
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-medium">
                김
              </div>
              <div className="ml-2">
                <p className="text-sm font-medium text-gray-900">김여신</p>
                <p className="text-xs text-gray-500">심사역</p>
              </div>
            </div>
          </div>
        </header>

        {/* 페이지 콘텐츠 */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
