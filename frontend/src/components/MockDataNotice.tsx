import React from 'react';
import { AlertTriangle } from 'lucide-react';

/**
 * 모의 데이터 고지 다이얼로그
 *
 * 소개 팝업이 닫힌 직후 표시한다. 이 시스템의 수치는 실제 원장에 근거하지 않은
 * 모의(Mock) 데이터인데, 화면 완성도가 높을수록 실제 수치로 오인할 위험이 커진다.
 * 의사결정·보고에 인용되는 사고를 막기 위해 명시적 확인을 받는다.
 */
export default function MockDataNotice({ onConfirm }: { onConfirm: () => void }) {
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="mock-notice-title"
        className="modal-in w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden"
      >
        {/* 경고 헤더 */}
        <div className="px-6 pt-6 pb-4 flex items-start gap-4">
          <span className="w-11 h-11 shrink-0 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center">
            <AlertTriangle size={22} />
          </span>
          <div>
            <h2 id="mock-notice-title" className="text-lg font-bold text-gray-900">
              모의 데이터 안내
            </h2>
            <p className="text-sm text-gray-600 mt-2 leading-relaxed">
              본 시스템의 모든 수치·고객·여신 정보는 실제 원장에 근거하지 않은{' '}
              <span className="font-semibold text-gray-900">모의(Mock) 데이터</span>입니다.
            </p>
          </div>
        </div>

        <div className="mx-6 mb-5 rounded-xl bg-amber-50 border border-amber-200 px-4 py-3">
          <ul className="text-xs text-amber-800 space-y-1.5 leading-relaxed">
            <li>· 산식과 업무 흐름 검증을 위한 PoC 목적으로 생성된 데이터입니다</li>
            <li>· 실제 고객·계좌·거래와 무관하며, 유사한 명칭은 우연의 일치입니다</li>
            <li>· 어떠한 수치도 의사결정·보고·공시에 인용할 수 없습니다</li>
          </ul>
        </div>

        <div className="px-6 py-4 border-t border-gray-100 flex justify-end">
          <button onClick={onConfirm} className="btn-mint px-6 text-sm">
            이해했습니다
          </button>
        </div>
      </div>
    </div>
  );
}
