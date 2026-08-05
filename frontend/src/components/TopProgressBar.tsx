import React, { useEffect, useRef, useState } from 'react';
import { onNetActivity } from '../utils/api';

/**
 * 상단 전역 진행 표시줄
 * ----------------------
 * 진행 중인 API 요청이 있으면 헤더 바로 아래에 민트→라임 그라디언트 바가
 * 차오른다 (NProgress 방식의 trickle). 요청이 모두 끝나면 100% 로 마저 채우고
 * 부드럽게 사라진다. 화면별 코드 수정 없이 모든 로딩을 한 곳에서 시각화한다.
 */
export default function TopProgressBar() {
  const [visible, setVisible] = useState(false);
  const [width, setWidth] = useState(0);
  const trickleRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const hideRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return onNetActivity(pending => {
      if (pending > 0) {
        if (hideRef.current) { clearTimeout(hideRef.current); hideRef.current = null; }
        setVisible(true);
        setWidth(w => (w === 0 || w >= 100 ? 12 : w));
        if (!trickleRef.current) {
          trickleRef.current = setInterval(() => {
            setWidth(w => (w < 85 ? w + (85 - w) * 0.08 : w));
          }, 250);
        }
      } else {
        if (trickleRef.current) { clearInterval(trickleRef.current); trickleRef.current = null; }
        setWidth(100);
        hideRef.current = setTimeout(() => { setVisible(false); setWidth(0); }, 450);
      }
    });
  }, []);

  return (
    <div
      className="fixed top-0 left-0 right-0 z-[80] h-[3px] pointer-events-none"
      aria-hidden="true"
      style={{ opacity: visible ? 1 : 0, transition: 'opacity 0.3s ease' }}
    >
      <div
        className="h-full im-gradient rounded-r-full"
        style={{
          width: `${width}%`,
          transition: width === 0 ? 'none' : 'width 0.25s ease',
          boxShadow: '0 0 8px rgba(0, 199, 169, 0.55)',
        }}
      />
    </div>
  );
}
