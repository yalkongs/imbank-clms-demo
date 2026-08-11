import React, { useEffect, useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Home, Stamp, AlertTriangle, ListChecks, LayoutGrid, X, LogOut } from 'lucide-react';
import { getAuth, setAuth } from '../utils/api';

/**
 * 모바일 전용 셸 (Tier 1)
 * ------------------------
 * 이동 중 업무(결재·경보·의무·조회)에 맞춘 하단 탭 구조.
 * 데스크탑 코드와 완전히 분리 - /m/* 라우트에서만 렌더된다.
 */

const TABS = [
  { to: '/m', end: true, label: '홈', icon: Home },
  { to: '/m/approval', label: '결재', icon: Stamp },
  { to: '/m/alerts', label: '경보', icon: AlertTriangle },
  { to: '/m/obligations', label: '의무', icon: ListChecks },
  { to: '/m/more', label: '전체', icon: LayoutGrid },
];

export default function MobileLayout() {
  const navigate = useNavigate();
  const [auth, setAuthState] = useState(getAuth());
  const [loginOpen, setLoginOpen] = useState(false);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [pinFor, setPinFor] = useState<any>(null);
  const [pin, setPin] = useState('');
  const [err, setErr] = useState('');
  const [asOf, setAsOf] = useState('');

  useEffect(() => {
    axios.get('/api/system/as-of').then(r => setAsOf(r.data.label_ko)).catch(() => {});
  }, []);

  const openLogin = () => {
    setLoginOpen(true);
    setPinFor(null);
    setErr('');
    if (accounts.length === 0) {
      axios.get('/api/auth/accounts').then(r => setAccounts(r.data.accounts || [])).catch(() => {});
    }
  };

  const doLogin = async (acc: any) => {
    try {
      const r = await axios.post('/api/auth/login', { user_id: acc.user_id, pin });
      setAuth({ token: r.data.token, user: r.data.user });
      setAuthState(getAuth());
      setLoginOpen(false);
      setPin('');
    } catch {
      setErr('PIN이 올바르지 않습니다');
    }
  };

  const logout = () => {
    setAuth(null);
    setAuthState(null);
  };

  return (
    <div className="min-h-dvh bg-gray-50 flex flex-col" style={{ paddingBottom: 'calc(3.75rem + env(safe-area-inset-bottom))' }}>
      {/* 상단 바 */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur border-b border-gray-200 px-4 h-12 flex items-center justify-between">
        <button onClick={() => navigate('/m')} className="flex items-center gap-2">
          <img src="/brand/im-symbol.jpg" alt="iM" className="h-6 w-6 rounded" />
          <span className="text-sm font-bold text-gray-900">CLMS</span>
          <span className="text-[10px] text-gray-400">{asOf}</span>
        </button>
        {auth ? (
          <button onClick={logout}
            className="flex items-center gap-1.5 px-2.5 py-1 bg-gray-100 rounded-full text-xs font-medium text-gray-700">
            {auth.user?.name} · {auth.user?.level_ko || auth.user?.approval_level}
            <LogOut size={12} className="text-gray-400" />
          </button>
        ) : (
          <button onClick={openLogin}
            className="px-3 py-1 bg-[#00C7A9] text-white rounded-full text-xs font-semibold">
            로그인
          </button>
        )}
      </header>

      {/* 본문 */}
      <main className="flex-1 p-3.5 space-y-3.5">
        <Outlet context={{ auth, openLogin }} />
      </main>

      {/* 하단 탭바 */}
      <nav className="fixed bottom-0 inset-x-0 z-40 bg-white border-t border-gray-200 flex"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
        {TABS.map(({ to, end, label, icon: Icon }) => (
          <NavLink key={to} to={to} end={end as any}
            className={({ isActive }) =>
              `flex-1 flex flex-col items-center justify-center gap-0.5 h-[3.75rem] text-[10px] font-medium ${
                isActive ? 'text-[#00897B]' : 'text-gray-400'}`}>
            <Icon size={20} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* 로그인 시트 */}
      {loginOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-end" onClick={() => setLoginOpen(false)}>
          <div className="w-full bg-white rounded-t-2xl p-5 pb-8" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-gray-900">체험 계정 로그인</h3>
              <button onClick={() => setLoginOpen(false)} className="p-1 text-gray-400"><X size={20} /></button>
            </div>
            <div className="space-y-2">
              {accounts.map(acc => (
                <div key={acc.user_id} className="border border-gray-200 rounded-xl p-3">
                  {pinFor?.user_id === acc.user_id ? (
                    <form onSubmit={e => { e.preventDefault(); doLogin(acc); }} className="flex items-center gap-2">
                      <span className="text-sm font-medium flex-none">{acc.name}</span>
                      <input autoFocus type="password" inputMode="numeric" value={pin}
                        onChange={e => setPin(e.target.value)}
                        placeholder={`PIN (힌트: ${acc.pin_hint})`}
                        aria-label={`${acc.name} PIN 입력`}
                        className="flex-1 border rounded-lg px-3 py-2 text-sm min-w-0" />
                      <button type="submit" className="px-3 py-2 bg-[#00C7A9] text-white rounded-lg text-xs font-semibold flex-none">확인</button>
                    </form>
                  ) : (
                    <button onClick={() => { setPinFor(acc); setPin(''); setErr(''); }}
                      className="w-full flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-900">{acc.name} · {acc.level_ko}</span>
                      <span className="text-xs text-gray-400">{acc.dept}</span>
                    </button>
                  )}
                </div>
              ))}
            </div>
            {err && <p className="text-xs text-red-600 mt-2">{err}</p>}
          </div>
        </div>
      )}
    </div>
  );
}
