import React from 'react';

/**
 * 경량 마크다운 렌더러 (의존성 없음)
 *
 * 백엔드가 methodology·theoretical_background 등에 마크다운 텍스트를 내려주는데,
 * 화면마다 제각각의 간이 처리(또는 무처리)를 해서 `**`, `##`, 표 구분선이
 * 원문 그대로 노출되는 곳이 있었다. 렌더 지점을 이 컴포넌트로 일원화한다.
 *
 * 지원 문법 — 백엔드 텍스트가 실제로 쓰는 범위만:
 *   # ~ ### 헤더 · **볼드**(인라인 포함) · `인라인 코드` · - / 1. 리스트 ·
 *   | 표 | · ``` 코드 블록 · 빈 줄 단락
 */

/** 인라인 처리: **볼드**, `코드` */
function renderInline(text: string): React.ReactNode[] {
  const out: React.ReactNode[] = [];
  // **bold** 와 `code` 를 함께 분해
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith('**')) {
      out.push(<strong key={key++} className="font-semibold text-gray-900">{tok.slice(2, -2)}</strong>);
    } else {
      out.push(<code key={key++} className="px-1 py-0.5 bg-gray-100 rounded text-[0.92em] font-mono">{tok.slice(1, -1)}</code>);
    }
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export default function SimpleMarkdown({ text }: { text: string }) {
  const lines = text.split('\n');
  const nodes: React.ReactNode[] = [];
  let inCode = false;
  let codeBuf: string[] = [];

  lines.forEach((raw, i) => {
    const line = raw.replace(/\s+$/, '');
    const ls = line.trim();

    // 코드 블록
    if (ls.startsWith('```')) {
      if (inCode) {
        nodes.push(
          <pre key={`c${i}`} className="text-xs bg-gray-100 rounded-lg px-3 py-2 font-mono my-2 overflow-x-auto whitespace-pre">
            {codeBuf.join('\n')}
          </pre>
        );
        codeBuf = [];
      }
      inCode = !inCode;
      return;
    }
    if (inCode) { codeBuf.push(raw); return; }

    if (!ls) return;

    // 헤더
    const h = ls.match(/^(#{1,3})\s+(.*)/);
    if (h) {
      const level = h[1].length;
      const cls = level === 1 ? 'text-base font-bold mt-4 mb-2'
                : level === 2 ? 'text-sm font-bold mt-4 mb-2'
                : 'text-sm font-semibold mt-3 mb-1.5';
      nodes.push(<h4 key={i} className={`${cls} text-gray-900`}>{renderInline(h[2])}</h4>);
      return;
    }
    // 전체 줄 볼드 → 소제목 취급 (기존 콘텐츠 관례)
    if (/^\*\*[^*]+\*\*$/.test(ls)) {
      nodes.push(<h4 key={i} className="text-sm font-bold text-gray-900 mt-4 mb-2">{ls.slice(2, -2)}</h4>);
      return;
    }
    // 리스트
    if (ls.startsWith('- ')) {
      nodes.push(<li key={i} className="text-sm text-gray-700 ml-4 my-0.5 list-disc">{renderInline(ls.slice(2))}</li>);
      return;
    }
    const num = ls.match(/^(\d+)\.\s+(.*)/);
    if (num) {
      nodes.push(
        <li key={i} className="text-sm text-gray-700 ml-4 my-0.5 list-none">
          <span className="font-medium text-gray-500 mr-1">{num[1]}.</span>{renderInline(num[2])}
        </li>
      );
      return;
    }
    // 표
    if (ls.startsWith('|')) {
      const cells = ls.split('|').slice(1, -1).map(c => c.trim());
      if (cells.length && cells.every(c => /^:?-+:?$/.test(c))) return;   // 구분선
      const isHeaderRow = i + 1 < lines.length && /^\|[\s:|-]+\|$/.test(lines[i + 1].trim());
      nodes.push(
        <div key={i} className={`flex text-xs ${isHeaderRow ? 'font-semibold bg-gray-50' : ''}`}>
          {cells.map((cell, j) => (
            <span key={j} className="flex-1 px-2 py-1 border-b border-gray-200">{renderInline(cell)}</span>
          ))}
        </div>
      );
      return;
    }
    // 일반 문단
    nodes.push(<p key={i} className="text-sm text-gray-700 my-1 leading-relaxed">{renderInline(ls)}</p>);
  });

  return <div>{nodes}</div>;
}
