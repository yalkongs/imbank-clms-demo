import React, { useCallback, useEffect, useRef, useState } from 'react';

/**
 * 숫자 호버 애니메이션
 * ---------------------
 * 카드에 마우스를 올리면 값의 숫자 부분만 90%→100% 로 짧게(0.45s) 다시 세어
 * "살아있는 숫자" 반응을 준다. 포맷된 문자열("862,237.7억원", "16.81%")에서
 * 숫자를 추출해 소수 자릿수를 보존하고, prefers-reduced-motion 이면 건너뛴다.
 */
function parseNumeric(display: string | number) {
  const s = String(display);
  const m = s.match(/-?[\d,]+(?:\.\d+)?/);
  if (!m || m.index === undefined) return null;
  const raw = m[0];
  const num = parseFloat(raw.replace(/,/g, ''));
  if (!isFinite(num) || num === 0) return null;
  const dot = raw.indexOf('.');
  return {
    prefix: s.slice(0, m.index),
    num,
    suffix: s.slice(m.index + raw.length),
    decimals: dot >= 0 ? raw.length - dot - 1 : 0,
  };
}

function useHoverNumber(value: string | number) {
  const [overlay, setOverlay] = useState<string | null>(null);
  const raf = useRef<number | null>(null);

  // 값이 바뀌면(필터 전환 등) 진행 중인 애니메이션을 버린다
  useEffect(() => {
    if (raf.current) cancelAnimationFrame(raf.current);
    raf.current = null;
    setOverlay(null);
  }, [value]);
  useEffect(() => () => { if (raf.current) cancelAnimationFrame(raf.current); }, []);

  const animate = useCallback(() => {
    if (raf.current) return;   // 진행 중이면 무시
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const p = parseNumeric(value);
    if (!p) return;
    const start = performance.now();
    const DUR = 450;
    const tick = (t: number) => {
      const k = Math.min((t - start) / DUR, 1);
      const ease = 1 - Math.pow(1 - k, 3);
      const cur = p.num * (0.9 + 0.1 * ease);
      setOverlay(
        p.prefix +
        cur.toLocaleString('ko-KR', { minimumFractionDigits: p.decimals, maximumFractionDigits: p.decimals }) +
        p.suffix
      );
      if (k < 1) {
        raf.current = requestAnimationFrame(tick);
      } else {
        raf.current = null;
        setOverlay(null);
      }
    };
    raf.current = requestAnimationFrame(tick);
  }, [value]);

  return { text: overlay ?? String(value), animate };
}

interface CardProps {
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
  headerAction?: React.ReactNode;
  noPadding?: boolean;
}

export default function Card({
  title,
  subtitle,
  children,
  className = '',
  headerAction,
  noPadding = false
}: CardProps) {
  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 ${className}`}>
      {(title || headerAction) && (
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <div>
            {title && <h3 className="text-base font-semibold text-gray-900">{title}</h3>}
            {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
          </div>
          {headerAction && <div>{headerAction}</div>}
        </div>
      )}
      <div className={noPadding ? '' : 'p-4'}>{children}</div>
    </div>
  );
}

// 통계 카드 컴포넌트
interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  change?: number;
  icon?: React.ReactNode;
  color?: 'blue' | 'green' | 'red' | 'yellow' | 'gray';
}

export function StatCard({ title, value, subtitle, change, icon, color = 'blue' }: StatCardProps) {
  const { text, animate } = useHoverNumber(value);
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    red: 'bg-red-50 text-red-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    gray: 'bg-gray-50 text-gray-600',
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4" onMouseEnter={animate}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 font-medium">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1 tabular">{text}</p>
          {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
          {change !== undefined && (
            <p className={`text-sm mt-1 ${change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {change >= 0 ? '↑' : '↓'} {Math.abs(change).toFixed(1)}%
            </p>
          )}
        </div>
        {icon && (
          <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}

// 게이지 카드 컴포넌트
interface GaugeCardProps {
  title: string;
  value: number;
  max?: number;
  min?: number;
  target?: number;
  unit?: string;
  warning?: number;
  critical?: number;
}

export function GaugeCard({
  title,
  value,
  max = 100,
  min = 0,
  target,
  unit = '%',
  warning,
  critical
}: GaugeCardProps) {
  const percentage = ((value - min) / (max - min)) * 100;
  const targetPercentage = target ? ((target - min) / (max - min)) * 100 : null;
  const { text, animate } = useHoverNumber(`${value.toFixed(2)}${unit}`);

  let barColor = 'bg-green-500';
  if (critical && value <= critical) barColor = 'bg-red-500';
  else if (warning && value <= warning) barColor = 'bg-yellow-500';

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4" onMouseEnter={animate}>
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm text-gray-500 font-medium">{title}</p>
        <p className="text-lg font-bold text-gray-900 tabular">
          {text}
        </p>
      </div>
      <div className="relative h-3 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`absolute left-0 top-0 h-full ${barColor} rounded-full transition-all duration-500`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
        {targetPercentage && (
          <div
            className="absolute top-0 w-0.5 h-full bg-gray-800"
            style={{ left: `${targetPercentage}%` }}
          />
        )}
      </div>
      <div className="flex justify-between mt-1 text-xs text-gray-400">
        <span>{min}{unit}</span>
        {target && <span className="text-gray-600">목표: {target}{unit}</span>}
        <span>{max}{unit}</span>
      </div>
    </div>
  );
}
