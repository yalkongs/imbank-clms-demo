import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { FileText, Download, X, Sparkles } from 'lucide-react';
import { SectionSkeleton, SectionError } from './AsyncSection';

/**
 * AI 심사의견서 자동 초안 모달
 * -----------------------------
 * 시스템 보유 데이터(재무·등급·EWS·동일차주·담보·RAROC)를 근거로
 * 백엔드가 규칙 기반 생성한 심사의견서 초안을 표시하고 PDF 로 내려받는다.
 */

const VERDICT_STYLE: Record<string, string> = {
  APPROVE: 'bg-green-100 text-green-800 border-green-300',
  CONDITIONAL: 'bg-amber-100 text-amber-800 border-amber-300',
  CAUTION: 'bg-red-100 text-red-700 border-red-300',
};

export default function OpinionDraftModal({ applicationId, onClose }: {
  applicationId: string;
  onClose: () => void;
}) {
  const [draft, setDraft] = useState<any>(null);
  const [error, setError] = useState(false);

  const load = () => {
    setError(false);
    setDraft(null);
    axios.get(`/api/applications/${applicationId}/opinion-draft`)
      .then(r => setDraft(r.data))
      .catch(() => setError(true));
  };
  useEffect(load, [applicationId]);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4">
      <div className="modal-in bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[92vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b bg-gray-50">
          <div className="flex items-center gap-2.5">
            <span className="w-9 h-9 rounded-lg im-gradient text-white flex items-center justify-center">
              <Sparkles size={17} />
            </span>
            <div>
              <h3 className="text-base font-bold text-gray-900">AI 심사의견서 초안</h3>
              <p className="text-xs text-gray-500">
                시스템 보유 데이터 기반 자동 생성 - 심사역 검토·수정 전제
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <a href={`/api/applications/${applicationId}/opinion-draft/pdf`}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-sm font-medium
                         btn-accent rounded-lg" download>
              <Download size={15} /> PDF 저장
            </a>
            <button onClick={onClose} className="p-2 hover:bg-gray-200 rounded-lg">
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="overflow-y-auto p-6">
          {error ? (
            <SectionError onRetry={load} />
          ) : !draft ? (
            <SectionSkeleton rows={6} />
          ) : (
            <div className="space-y-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-lg font-bold text-gray-900">{draft.customer_name}</p>
                  <p className="text-xs text-gray-400">
                    {draft.application_id} · 기준일 {draft.as_of}
                  </p>
                </div>
                <span className={`px-4 py-2 rounded-lg border text-sm font-bold ${
                  VERDICT_STYLE[draft.verdict_code] || 'bg-gray-100 text-gray-700 border-gray-300'}`}>
                  {draft.verdict}
                </span>
              </div>

              {draft.sections.map((sec: any) => (
                <div key={sec.title}>
                  <h4 className="flex items-center gap-1.5 text-sm font-bold text-gray-800 mb-2">
                    <FileText size={13} className="text-[#00897B]" /> {sec.title}
                  </h4>
                  {sec.rows.length > 0 && (
                    <table className="w-full text-xs mb-2 border border-gray-100 rounded">
                      <tbody>
                        {sec.rows.map((row: string[], i: number) => (
                          <tr key={i} className={i % 2 ? 'bg-gray-50/60' : ''}>
                            {row.map((cell, j) => (
                              <td key={j} className={`px-3 py-1.5 ${
                                j === 0 ? 'text-gray-500 w-36' : 'text-gray-800'}`}>
                                {cell}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                  {sec.text.map((t: string, i: number) => (
                    <p key={i} className="text-[13px] text-gray-700 leading-relaxed">{t}</p>
                  ))}
                </div>
              ))}

              {draft.recommended_conditions.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                  <h4 className="text-sm font-bold text-amber-800 mb-2">권고 승인조건</h4>
                  <ol className="list-decimal list-inside space-y-1 text-[13px] text-amber-900">
                    {draft.recommended_conditions.map((c: string, i: number) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ol>
                </div>
              )}

              <p className="text-[11px] text-gray-400 border-t border-gray-100 pt-3">
                {draft.disclaimer}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
