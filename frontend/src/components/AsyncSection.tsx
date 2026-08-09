import React from 'react';
import { RefreshCw, Inbox } from 'lucide-react';

/**
 * 섹션 단위 비동기 상태 표준 컴포넌트
 * ------------------------------------
 * "로딩 중..." 텍스트 하나로 로딩·빈 데이터·오류를 뭉뚱그리면
 * 데이터가 없거나 요청이 실패했을 때 무한 로딩처럼 보인다.
 * 세 상태를 분리해 표기한다:
 *   loading → 스켈레톤 셔머 (대기 체감 감소)
 *   error   → 안내 + 재시도 버튼
 *   empty   → "데이터 없음" 안내
 */

export type AsyncStatus = 'idle' | 'loading' | 'ready' | 'error';

/** 표 형태 섹션의 로딩 스켈레톤 */
export function SectionSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="py-4 space-y-3" role="status" aria-label="불러오는 중">
      <div className="skeleton h-4 w-1/3" />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-3">
          <div className="skeleton h-9 flex-[2]" />
          <div className="skeleton h-9 flex-1" />
          <div className="skeleton h-9 flex-1" />
          <div className="skeleton h-9 flex-1 hidden md:block" />
        </div>
      ))}
    </div>
  );
}

/** 요청 실패 - 원인 안내 + 재시도 */
export function SectionError({ onRetry, message }: { onRetry?: () => void; message?: string }) {
  return (
    <div className="text-center py-12">
      <p className="text-sm text-gray-500">{message || '데이터를 불러오지 못했습니다'}</p>
      {onRetry && (
        <button onClick={onRetry}
          className="mt-3 inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium
                     border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-700">
          <RefreshCw size={14} /> 다시 불러오기
        </button>
      )}
    </div>
  );
}

/** 정상 응답이지만 표시할 데이터가 없음 */
export function SectionEmpty({ message }: { message?: string }) {
  return (
    <div className="text-center py-12 text-gray-400">
      <Inbox size={28} className="mx-auto mb-2 opacity-60" />
      <p className="text-sm">{message || '표시할 데이터가 없습니다'}</p>
    </div>
  );
}
