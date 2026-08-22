import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, Settings, Check } from 'lucide-react';
import { useTheme, Theme } from '../context/ThemeProvider';

/**
 * 헤더의 알림(종)·설정(기어) 메뉴.
 *
 * 종전에는 두 아이콘이 눌러도 아무 일이 없었고 종에는 빨간 점만 떠 있었다.
 * 동작하지 않는 장식은 시스템 전체의 신뢰를 깎으므로 실제 기능을 붙였다.
 *  · 알림: EWS 경보(/api/dashboard/ews-alerts)를 목록으로 띄우고, 항목을 누르면
 *    해당 화면으로 이동한다. 빨간 점은 미확인 건수에 연동되며 확인하면 사라진다.
 *  · 설정: 화면 테마(Classic/Mesh)와 기준일을 여기서 관리한다.
 *    테마 토글은 헤더에 따로 떠 있었는데 성격상 설정에 속한다.
 */

const SEVERITY_STYLE: Record<string, { dot: string; label: string }> = {
  CRITICAL: { dot: 'is-critical', label: '위험' },
  HIGH:     { dot: 'is-warning',  label: '높음' },
  MEDIUM:   { dot: 'is-warning',  label: '보통' },
  LOW:      { dot: 'is-idle',     label: '낮음' },
};

const SEEN_KEY = 'clms-alerts-seen';

interface Alert {
  alert_id: string;
  customer_name?: string;
  alert_date?: string;
  alert_type?: string;
  severity?: string;
  description?: string;
}

function useOutsideClose(onClose: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [onClose]);
  return ref;
}

export function AlertMenu() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [seen, setSeen] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem(SEEN_KEY) || '[]'); } catch { return []; }
  });
  const ref = useOutsideClose(() => setOpen(false));

  useEffect(() => {
    const load = () =>
      fetch('/api/dashboard/ews-alerts')
        .then(r => r.json())
        .then(d => setAlerts(Array.isArray(d) ? d : (d?.alerts ?? [])))
        .catch(() => setAlerts([]));
    load();
    const t = setInterval(load, 60000);   // 실시간성: 60초 주기 갱신
    return () => clearInterval(t);
  }, []);

  const unread = alerts.filter(a => !seen.includes(a.alert_id));

  const markAllRead = () => {
    const ids = alerts.map(a => a.alert_id);
    setSeen(ids);
    try { localStorage.setItem(SEEN_KEY, JSON.stringify(ids)); } catch { /* 무시 */ }
  };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(v => !v)}
        aria-label={`알림 ${unread.length}건`}
        className="relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
      >
        <Bell size={20} />
        {unread.length > 0 && (
          <span className={`absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 bg-red-500 text-white
                           text-[10px] font-bold rounded-full flex items-center justify-center ${
                             unread.some(a => a.severity === 'CRITICAL') ? 'badge-alert' : ''}`}>
            {unread.length}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-xl border border-gray-200 z-50 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <span className="text-sm font-semibold text-gray-900">EWS 경보</span>
            {unread.length > 0 && (
              <button onClick={markAllRead} className="text-xs text-blue-600 hover:underline">
                모두 읽음
              </button>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {alerts.length === 0 && (
              <p className="px-4 py-6 text-sm text-gray-400 text-center">새 경보가 없습니다</p>
            )}
            {alerts.map(a => {
              const sev = SEVERITY_STYLE[a.severity || 'LOW'] ?? SEVERITY_STYLE.LOW;
              const isNew = !seen.includes(a.alert_id);
              return (
                <button
                  key={a.alert_id}
                  onClick={() => { setOpen(false); navigate(`/customer-browser?q=${encodeURIComponent(a.customer_name || '')}`); }}
                  className={`w-full text-left px-4 py-3 hover:bg-gray-50 border-b border-gray-50
                              flex gap-3 ${isNew ? 'bg-blue-50/40' : ''}`}
                >
                  <span className={`status-dot ${sev.dot} mt-1.5`} />
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-medium text-gray-900 truncate">
                      {a.customer_name || a.alert_id}
                    </span>
                    <span className="block text-xs text-gray-500 mt-0.5">
                      {a.alert_type} · {sev.label} · {a.alert_date}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>

          <button
            onClick={() => { setOpen(false); navigate('/ews-advanced'); }}
            className="w-full px-4 py-2.5 text-xs text-blue-600 hover:bg-gray-50 border-t border-gray-100"
          >
            EWS 조기경보 전체보기
          </button>
        </div>
      )}
    </div>
  );
}

export function SettingsMenu({ asOfLabel }: { asOfLabel?: string }) {
  const { theme, setTheme } = useTheme();
  const [open, setOpen] = useState(false);
  const ref = useOutsideClose(() => setOpen(false));

  const themes: { key: Theme; label: string; desc: string }[] = [
    { key: 'classic', label: 'Classic',       desc: '깔끔한 플랫 UI' },
    { key: 'mesh',    label: 'Gradient Mesh', desc: '민트·라임 메시 배경' },
    { key: 'dark',    label: 'Dark',          desc: '어두운 배경의 다크 모드' },
  ];

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(v => !v)}
        aria-label="설정"
        className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
      >
        <Settings size={20} />
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-72 bg-white rounded-xl shadow-xl border border-gray-200 z-50 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100">
            <span className="text-sm font-semibold text-gray-900">설정</span>
          </div>

          <div className="px-4 py-3">
            <p className="text-xs font-semibold text-gray-400 mb-2">화면 테마</p>
            <div className="space-y-1">
              {themes.map(t => (
                <button
                  key={t.key}
                  onClick={() => setTheme(t.key)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-left
                    ${theme === t.key ? 'bg-blue-50' : 'hover:bg-gray-50'}`}
                >
                  <span>
                    <span className="block text-sm font-medium text-gray-900">{t.label}</span>
                    <span className="block text-xs text-gray-500">{t.desc}</span>
                  </span>
                  {theme === t.key && <Check size={16} className="text-blue-600 flex-none" />}
                </button>
              ))}
            </div>
          </div>

          <div className="px-4 py-3 border-t border-gray-100">
            <p className="text-xs font-semibold text-gray-400 mb-1">시스템 기준일</p>
            <p className="text-sm text-gray-700">{asOfLabel || '-'}</p>
            <p className="text-[11px] text-gray-400 mt-1">
              모든 지표는 이 시점을 기준으로 산출됩니다
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
