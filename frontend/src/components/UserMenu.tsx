import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { LogIn, LogOut, ShieldCheck } from 'lucide-react';
import { getAuth, setAuth, onAuthChange } from '../utils/api';

/**
 * 헤더 사용자 메뉴 - 데모 계정 로그인.
 *
 * 종전의 '역할 전환기'는 클라이언트가 승인자를 마음대로 정하는 구조라
 * 감사 증빙이 성립하지 않았다 (제3자 리뷰 P0-1). 이제 서버 검증 PIN 으로
 * 로그인하면 승인자·부서·전결권을 서버가 토큰에서 결정한다.
 * PoC 특성상 계정·PIN 은 화면에 공개된다.
 */
export default function UserMenu() {
  const [auth, setAuthState] = useState(getAuth());
  const [open, setOpen] = useState(false);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [pin, setPin] = useState('');
  const [pinFor, setPinFor] = useState<any>(null);
  const [err, setErr] = useState('');
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => onAuthChange(setAuthState), []);
  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);
  useEffect(() => {
    if (open && accounts.length === 0) {
      axios.get('/api/auth/accounts').then(r => setAccounts(r.data.accounts || [])).catch(console.error);
    }
  }, [open, accounts.length]);

  const login = async (acc: any, pinValue: string) => {
    setErr('');
    try {
      const r = await axios.post('/api/auth/login', { user_id: acc.user_id, pin: pinValue });
      setAuth(r.data);
      setPinFor(null); setPin(''); setOpen(false);
    } catch (e: any) {
      setErr(e?.response?.data?.detail || '로그인 실패');
    }
  };

  const user = auth?.user;

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen(v => !v)}
        className="flex items-center gap-2 hover:bg-gray-100 rounded-lg px-1.5 py-1">
        {user ? (
          <>
            <span className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-medium">
              {user.name[0]}
            </span>
            <span className="text-left leading-tight">
              <span className="block text-sm font-medium text-gray-900">{user.name}</span>
              <span className="block text-xs text-gray-500">{user.level_ko}</span>
            </span>
          </>
        ) : (
          <>
            <span className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center text-gray-500">
              <LogIn size={15} />
            </span>
            <span className="text-left leading-tight">
              <span className="block text-sm font-medium text-gray-500">로그인</span>
              <span className="block text-[10px] text-gray-400">쓰기 작업용</span>
            </span>
          </>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-72 bg-white rounded-xl shadow-xl border border-gray-200 z-50 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100">
            <p className="text-sm font-semibold text-gray-900 flex items-center gap-1.5">
              <ShieldCheck size={14} className="text-[#00897B]" /> 데모 계정 로그인
            </p>
            <p className="text-[11px] text-gray-400 mt-0.5">
              승인자·전결권은 서버가 로그인 사용자로 결정합니다 (PoC - PIN 공개)
            </p>
          </div>

          {user && (
            <div className="px-4 py-2.5 bg-blue-50/60 flex items-center justify-between">
              <span className="text-xs text-blue-800">
                <b>{user.name}</b> ({user.level_ko}) 로그인 중
              </span>
              <button onClick={() => { setAuth(null); setOpen(false); }}
                className="flex items-center gap-1 text-xs text-gray-500 hover:text-red-600">
                <LogOut size={12} /> 로그아웃
              </button>
            </div>
          )}

          {accounts.map(acc => (
            <div key={acc.user_id}
              className={`px-4 py-2.5 border-b border-gray-50 last:border-0 ${user?.user_id === acc.user_id ? 'bg-blue-50' : ''}`}>
              {pinFor?.user_id === acc.user_id ? (
                <form onSubmit={e => { e.preventDefault(); login(acc, pin); }} className="flex items-center gap-2">
                  <span className="text-sm font-medium flex-none">{acc.name}</span>
                  <input autoFocus type="password" value={pin} onChange={e => setPin(e.target.value)}
                    placeholder={`PIN (힌트: ${acc.pin_hint})`}
                    aria-label={`${acc.name} PIN 번호 입력`}
                    inputMode="numeric" autoComplete="off"
                    className="flex-1 border rounded px-2 py-1 text-xs" />
                  <button type="submit" className="px-2.5 py-1 bg-blue-600 text-white rounded text-xs">확인</button>
                </form>
              ) : (
                <button onClick={() => { setPinFor(acc); setPin(''); setErr(''); }}
                  className="w-full flex items-center justify-between text-left">
                  <span>
                    <span className="block text-sm font-medium text-gray-900">{acc.name} · {acc.level_ko}</span>
                    <span className="block text-[11px] text-gray-400">{acc.dept} · PIN 힌트 {acc.pin_hint}</span>
                  </span>
                  <LogIn size={14} className="text-gray-300" />
                </button>
              )}
            </div>
          ))}
          {err && <p className="px-4 py-2 text-xs text-red-600 bg-red-50">{err}</p>}
        </div>
      )}
    </div>
  );
}
