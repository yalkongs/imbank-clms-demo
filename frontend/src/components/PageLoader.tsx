import React from 'react';

/**
 * 브랜드 페이지 로더 - 민트 이중 링 + iM 심볼 + 안내 문구.
 * 라우트 청크 로딩(Suspense)과 화면 초기 로딩에 쓴다.
 */
export default function PageLoader({ label = '데이터를 불러오는 중' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-96 gap-4" role="status" aria-live="polite">
      <div className="relative w-16 h-16">
        <div className="absolute inset-0 rounded-full border-[3px] border-[#00C7A9]/15" />
        <div className="absolute inset-0 rounded-full border-[3px] border-transparent border-t-[#00C7A9] animate-spin"
             style={{ boxShadow: '0 0 14px rgba(0, 199, 169, 0.25)' }} />
        <div className="absolute inset-[7px] rounded-full border-2 border-transparent border-b-[#E2F15E] animate-spin"
             style={{ animationDirection: 'reverse', animationDuration: '1.4s' }} />
        <img src="/brand/im-symbol.jpg" alt="" className="absolute inset-0 m-auto w-6 h-6 rounded-full" />
      </div>
      <p className="text-sm text-gray-400 pm-loading-label">{label}</p>
    </div>
  );
}
