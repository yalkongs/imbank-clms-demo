import React, { useEffect, useRef, useState } from 'react';
import { Check } from 'lucide-react';
import { useTheme, ROLES, Role } from '../context/ThemeProvider';

/**
 * 헤더 사용자 메뉴 — 역할 전환기.
 *
 * 아바타가 장식으로만 있던 것을 페르소나 전환기로 만든다. 역할에 따라
 * 결재함의 전결 레벨이 바뀌어, 같은 신청 건이 "내가 결재 가능한가"가 달라진다.
 * 전결권 체계를 화면에서 체험시키는 장치다.
 */
export default function UserMenu() {
  const { role, setRole } = useTheme();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  const me = ROLES[role];

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen(v => !v)} className="flex items-center gap-2 hover:bg-gray-100 rounded-lg px-1.5 py-1">
        <span className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-medium">
          {me.name[0]}
        </span>
        <span className="text-left leading-tight">
          <span className="block text-sm font-medium text-gray-900">{me.name}</span>
          <span className="block text-xs text-gray-500">{me.title}</span>
        </span>
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-64 bg-white rounded-xl shadow-xl border border-gray-200 z-50 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100">
            <p className="text-sm font-semibold text-gray-900">역할 전환</p>
            <p className="text-[11px] text-gray-400 mt-0.5">역할에 따라 결재 가능 범위가 달라집니다</p>
          </div>
          {(Object.keys(ROLES) as Role[]).map(r => (
            <button
              key={r}
              onClick={() => { setRole(r); setOpen(false); }}
              className={`w-full flex items-center justify-between px-4 py-2.5 text-left hover:bg-gray-50 ${role === r ? 'bg-blue-50' : ''}`}
            >
              <span>
                <span className="block text-sm font-medium text-gray-900">{ROLES[r].name} · {ROLES[r].title}</span>
                <span className="block text-xs text-gray-500">전결 레벨: {ROLES[r].level}</span>
              </span>
              {role === r && <Check size={16} className="text-blue-600 flex-none" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
