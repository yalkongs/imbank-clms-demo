import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

/**
 * 긴급성·실시간성 공용 어휘 (2026-08-22)
 *
 * index.css 의 status-dot(is-live/is-warning/is-critical)·badge-alert 를
 * 화면들이 제각각 쓰지 않도록 컴포넌트로 묶는다. 세 가지 의미를 구분한다:
 *  · LiveBadge  - "이 숫자는 지금 갱신되고 있다" (실시간성 - 실제 폴링과 연동)
 *  · Deadline   - "언제까지 해야 하는가" (긴급성 - D-day 색 단계)
 *  · ActionBanner - "지금 처리해야 할 것이 있다" (즉각조치 - 건수 + 이동)
 * 모든 애니메이션은 prefers-reduced-motion 에서 index.css 가 비활성화한다.
 */

export function LiveBadge({ updatedAt, intervalSec }: { updatedAt: Date | null; intervalSec?: number }) {
  const [, tick] = useState(0);
  useEffect(() => {
    const t = setInterval(() => tick(v => v + 1), 5000);
    return () => clearInterval(t);
  }, []);
  const ago = updatedAt ? Math.max(0, Math.round((Date.now() - updatedAt.getTime()) / 1000)) : null;
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-[11px] font-medium text-emerald-700">
      <span className="status-dot is-live" />
      실시간
      {ago !== null && <span className="text-emerald-600/70">{ago < 5 ? '방금' : `${ago}초 전`} 갱신{intervalSec ? ` · ${intervalSec}초 주기` : ''}</span>}
    </span>
  );
}

export function Deadline({ date, days: daysProp, overdue }: { date?: string | null; days?: number; overdue?: boolean }) {
  if (!date && daysProp === undefined) return <span className="text-xs text-gray-400">-</span>;
  // 데모 기준일(AS_OF)과 실제 오늘이 다르므로, API 가 계산한 D-day 가 있으면 우선
  const days = daysProp !== undefined
    ? daysProp
    : Math.ceil((new Date(date! + (date!.length === 10 ? 'T00:00:00' : '')).getTime() - Date.now()) / 86400000);
  const isOver = overdue ?? days < 0;
  if (isOver) {
    return (
      <span className="badge-alert inline-flex items-center gap-1 px-1.5 py-0.5 bg-red-600 text-white rounded text-[10px] font-bold">
        D+{Math.abs(Math.min(days, 0))} 초과
      </span>
    );
  }
  if (days <= 3) {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded text-[10px] font-bold">
        <span className="status-dot is-warning" style={{ width: 6, height: 6 }} />
        D-{days}
      </span>
    );
  }
  return <span className="text-xs text-gray-500 tabular">D-{days}</span>;
}

export interface ActionItem {
  label: string;
  count: number;
  to: string;
  severity?: 'critical' | 'warning';
}

export function ActionBanner({ items }: { items: ActionItem[] }) {
  const active = items.filter(i => i.count > 0);
  if (active.length === 0) return null;
  const hasCritical = active.some(i => i.severity !== 'warning');
  return (
    <div className={`flex items-center flex-wrap gap-x-5 gap-y-1.5 px-4 py-2.5 rounded-xl border ${
      hasCritical ? 'bg-red-50/70 border-red-200' : 'bg-amber-50/70 border-amber-200'}`}>
      <span className="flex items-center gap-2 text-sm font-bold text-gray-900">
        <span className={`status-dot ${hasCritical ? 'is-critical' : 'is-warning'}`} />
        즉각 조치 필요
      </span>
      {active.map(i => (
        <Link key={i.to + i.label} to={i.to}
          className={`group inline-flex items-center gap-1 text-sm font-medium hover:underline ${
            i.severity === 'warning' ? 'text-amber-700' : 'text-red-600'}`}>
          {i.label} <b className="tabular">{i.count}건</b>
          <ChevronRight size={14} className="opacity-60 group-hover:translate-x-0.5 transition-transform" />
        </Link>
      ))}
    </div>
  );
}
