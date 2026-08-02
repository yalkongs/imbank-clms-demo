import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';

export type Theme = 'classic' | 'mesh';

const THEME_KEY = 'clms-theme';
const ONBOARDED_KEY = 'clms-onboarded';

interface ThemeContextValue {
  theme: Theme;
  setTheme: (t: Theme) => void;
  onboarded: boolean;
  setOnboarded: (v: boolean) => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

function readTheme(): Theme {
  try {
    const v = localStorage.getItem(THEME_KEY);
    return v === 'mesh' ? 'mesh' : 'classic';
  } catch {
    return 'classic';
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
    <ThemeContext.Provider value={{ theme, setTheme, onboarded, setOnboarded }}>
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
