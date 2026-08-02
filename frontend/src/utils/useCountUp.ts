import { useEffect, useRef, useState } from 'react';

/**
 * 대시보드 첫 렌더에서 숫자를 0부터 세어 올린다.
 *
 * 브랜드 가이드의 Animation 절이 "Numbers count up on first render on dashboard"
 * 를 규정하고 있어 그대로 따른다. 같은 절이 "Subtle. No bouncy springs." 도
 * 명시하므로 0.8초 안에 ease-out 으로 끝내고 튀는 구간을 두지 않는다.
 *
 * - 세션당 1회만 동작한다. 화면을 오갈 때마다 숫자가 다시 구르면 업무용
 *   화면에서는 방해가 된다.
 * - prefers-reduced-motion 이면 즉시 최종값을 보여준다.
 */

const DURATION = 800;
const played = new Set<string>();

function prefersReducedMotion(): boolean {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch {
    return false;
  }
}

export function useCountUp(target: number, key: string, enabled: boolean = true): number {
  const skip = played.has(key) || prefersReducedMotion();
  const [value, setValue] = useState(skip ? target : 0);
  const frame = useRef<number>();

  useEffect(() => {
    // 소개 팝업이 떠 있는 동안은 시작하지 않는다. 팝업 뒤에서 애니메이션이
    // 끝나버리면 정작 화면을 보는 순간에는 이미 최종값이라 효과가 없다.
    if (!enabled) return;
    if (!Number.isFinite(target)) {
      setValue(target);
      return;
    }
    if (played.has(key) || prefersReducedMotion()) {
      setValue(target);
      return;
    }
    played.add(key);

    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min((now - start) / DURATION, 1);
      // ease-out cubic — 빠르게 올라가다 부드럽게 멈춘다
      const eased = 1 - Math.pow(1 - p, 3);
      setValue(target * eased);
      if (p < 1) frame.current = requestAnimationFrame(tick);
      else setValue(target);
    };
    frame.current = requestAnimationFrame(tick);

    return () => {
      if (frame.current) cancelAnimationFrame(frame.current);
    };
    // target 이 늦게 도착하는 API 응답이므로 값이 바뀌면 다시 계산한다
  }, [target, key, enabled]);

  return value;
}
