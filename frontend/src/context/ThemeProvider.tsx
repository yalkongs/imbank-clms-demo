import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';

export type Theme = 'classic' | 'mesh';

const THEME_KEY = 'clms-theme';
const ONBOARDED_KEY = 'clms-onboarded';

interface ThemeContextValue {
  theme: Theme;
  setTheme: (t: Theme) => void;
  onboarded: boolean;
  setOnboarded: (v: boolean) => void;
  /** 소개 팝업이 떠 있는가.
   *  대시보드 카운트업이 팝업 뒤에서 끝나버리지 않도록 시작 시점을 맞추는 데 쓴다. */
  introOpen: boolean;
  setIntroOpen: (v: boolean) => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

/** 기본 테마는 Gradient Mesh.
 *  브랜드 가이드가 민트→라임 그라디언트를 hero treatment 로 규정하고 있어
 *  첫 접속에서 브랜드가 바로 드러나는 쪽을 기본값으로 둔다.
 *  Classic 은 헤더 토글로 언제든 바꿀 수 있고, 선택은 localStorage 에 남는다. */
const DEFAULT_THEME: Theme = 'mesh';

function readTheme(): Theme {
  try {
    const v = localStorage.getItem(THEME_KEY);
    if (v === 'mesh' || v === 'classic') return v;
    return DEFAULT_THEME;
  } catch {
    return DEFAULT_THEME;
  }
}

function readOnboarded(): boolean {
  try {
    return localStorage.getItem(ONBOARDED_KEY) === '1';
  } catch {
    return false;
  }
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => readTheme());
  const [introOpen, setIntroOpen] = useState(true);
  const [onboarded, setOnboardedState] = useState<boolean>(() => readOnboarded());

  // data-theme 속성을 root(html)에 반영
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    try {
      localStorage.setItem(THEME_KEY, t);
    } catch {
      /* localStorage 불가 환경 무시 */
    }
  }, []);

  const setOnboarded = useCallback((v: boolean) => {
    setOnboardedState(v);
    try {
      localStorage.setItem(ONBOARDED_KEY, v ? '1' : '0');
    } catch {
      /* 무시 */
    }
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, onboarded, setOnboarded, introOpen, setIntroOpen }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return ctx;
}
