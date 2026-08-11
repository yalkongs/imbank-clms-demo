import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Monitor, ChevronRight, Moon, Palette, Sun, FileText, TrendingUp } from 'lucide-react';
import { navGroups } from '../components/Layout';
import { useTheme } from '../context/ThemeProvider';

/**
 * 모바일 '전체' 탭 - 모바일 전용 화면 + 전 데스크탑 화면(Tier 2) 진입.
 * 데스크탑 화면은 모바일 기반 계층(CSS·카드 변환) 덕에 폰에서도 조회 가능하다.
 */

const MOBILE_SCREENS = [
  { to: '/m/customers', label: '고객 조회', desc: '현장용 기업 요약' },
  { to: '/m/delinquency', label: '연체 현황', desc: 'DPD 버킷·연체 목록' },
  { to: '/m/cases', label: '전자 여신철', desc: '승인 기록·봉인 조회' },
];

export default function MMore() {
  const navigate = useNavigate();
  const { theme, setTheme } = useTheme();

  const goDesktop = () => {
    try { localStorage.setItem('clms-view-mode', 'desktop'); } catch { /* 무시 */ }
    navigate('/');
  };

  return (
    <>
      <h1 className="text-lg font-bold text-gray-900 px-0.5">전체 기능</h1>

      {/* 모바일 전용 화면 */}
      <div>
        <h2 className="text-xs font-semibold text-gray-400 mb-2 px-0.5">모바일 화면</h2>
        <div className="bg-white border border-gray-200 rounded-xl divide-y divide-gray-100">
          {MOBILE_SCREENS.map(s => (
            <Link key={s.to} to={s.to} className="flex items-center justify-between px-4 py-3 active:bg-gray-50">
              <div>
                <p className="text-sm font-medium text-gray-900">{s.label}</p>
                <p className="text-[11px] text-gray-400">{s.desc}</p>
              </div>
              <ChevronRight size={15} className="row-chevron" />
            </Link>
          ))}
        </div>
      </div>

      {/* 테마 */}
      <div>
        <h2 className="text-xs font-semibold text-gray-400 mb-2 px-0.5">화면 테마</h2>
        <div className="flex gap-1.5">
          {([['classic', 'Classic', Sun], ['mesh', 'Mesh', Palette], ['dark', 'Dark', Moon]] as const).map(([key, label, Icon]) => (
            <button key={key} onClick={() => setTheme(key)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-xs font-semibold border ${
                theme === key ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-500 border-gray-200'}`}>
              <Icon size={14} /> {label}
            </button>
          ))}
        </div>
      </div>

      {/* 전체 데스크탑 화면 (Tier 2) */}
      <div>
        <h2 className="text-xs font-semibold text-gray-400 mb-2 px-0.5">
          전체 화면 열기 <span className="font-normal">- 폰에서도 조회 가능, 상세 분석은 PC 권장</span>
        </h2>
        <div className="space-y-2.5">
          {navGroups.map(group => (
            <div key={group.title} className="bg-white border border-gray-200 rounded-xl overflow-hidden">
              <p className="px-4 pt-2.5 pb-1 text-[10px] font-bold text-gray-400 tracking-wider">{group.title}</p>
              <div className="divide-y divide-gray-50">
                {group.items.map(item => (
                  <Link key={item.path} to={item.path}
                    className="flex items-center justify-between px-4 py-2.5 active:bg-gray-50">
                    <span className="flex items-center gap-2.5 text-sm text-gray-700">
                      <span className="text-gray-300">{item.icon}</span>
                      {item.label}
                    </span>
                    <ChevronRight size={14} className="row-chevron" />
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* PC 화면 전환 */}
      <button onClick={goDesktop}
        className="w-full flex items-center justify-center gap-2 py-3 bg-white border border-gray-300 rounded-xl text-sm font-semibold text-gray-700">
        <Monitor size={16} /> PC 화면으로 보기
      </button>

      <div className="text-center space-y-1 pb-2">
        <p className="text-[10px] text-gray-400">
          <FileText size={10} className="inline mr-0.5 -mt-0.5" />
          모의 데이터 기반 PoC · 의사결정에 사용할 수 없습니다
        </p>
        <p className="text-[10px] text-gray-400">
          <TrendingUp size={10} className="inline mr-0.5 -mt-0.5" />
          iM뱅크 CLMS · © 2026 yalkongs
        </p>
      </div>
    </>
  );
}
