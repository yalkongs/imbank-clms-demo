import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import axios from 'axios';
import { navGroups } from './Layout';

/**
 * 전역 검색 (Cmd+K / Ctrl+K)
 *
 * 고객 1,010명·여신 1,200건·PF 사업장 40곳을 페이지별 필터 없이 한 입력으로
 * 찾아 바로 이동한다. 화면 이동(메뉴 21개)도 같은 입력으로 검색된다.
 */

interface Item {
  type: string;
  type_label: string;
  title: string;
  subtitle?: string;
  route: string;
}

export default function CommandPalette() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState('');
  const [items, setItems] = useState<Item[]>([]);
  const [idx, setIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>();

  // 메뉴 항목 → 검색 대상
  const menuItems: Item[] = navGroups.flatMap(g =>
    g.items.map(i => ({
      type: 'menu', type_label: '화면', title: i.label, subtitle: g.title, route: i.path,
    })));

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setOpen(v => !v);
      }
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, []);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 30);
    else { setQ(''); setItems([]); setIdx(0); }
  }, [open]);

  useEffect(() => {
    if (!q.trim()) { setItems([]); setIdx(0); return; }
    const menuHits = menuItems.filter(m => m.title.includes(q)).slice(0, 4);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      axios.get('/api/search', { params: { q } })
        .then(r => setItems([...menuHits, ...(r.data.results || [])]))
        .catch(() => setItems(menuHits));
    }, 180);
    setItems(menuHits);
    setIdx(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  const go = useCallback((item: Item) => {
    setOpen(false);
    navigate(item.route);
  }, [navigate]);

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setIdx(i => Math.min(i + 1, items.length - 1)); }
    if (e.key === 'ArrowUp') { e.preventDefault(); setIdx(i => Math.max(i - 1, 0)); }
    if (e.key === 'Enter' && items[idx]) go(items[idx]);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[70] bg-black/40 backdrop-blur-sm flex items-start justify-center pt-[15vh]"
         onClick={() => setOpen(false)}>
      <div className="w-full max-w-xl bg-white rounded-2xl shadow-2xl overflow-hidden"
           onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100">
          <Search size={18} className="text-gray-400 flex-none" />
          <input
            ref={inputRef}
            value={q}
            onChange={e => setQ(e.target.value)}
            onKeyDown={onKey}
            placeholder="고객명 · 여신ID · PF 사업장 · 화면 이름 검색..."
            className="flex-1 text-sm outline-none placeholder:text-gray-400"
          />
          <kbd className="text-[10px] px-1.5 py-0.5 bg-gray-100 text-gray-400 rounded">ESC</kbd>
        </div>
        <div className="max-h-80 overflow-y-auto">
          {items.length === 0 && q && (
            <p className="px-4 py-6 text-sm text-gray-400 text-center">검색 결과가 없습니다</p>
          )}
          {items.map((it, i) => (
            <button
              key={`${it.type}-${it.title}-${i}`}
              onClick={() => go(it)}
              onMouseEnter={() => setIdx(i)}
              className={`w-full flex items-center gap-3 px-4 py-2.5 text-left ${i === idx ? 'bg-blue-50' : ''}`}
            >
              <span className="text-[10px] w-14 flex-none px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded text-center">
                {it.type_label}
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-medium text-gray-900 truncate">{it.title}</span>
                {it.subtitle && <span className="block text-xs text-gray-400 truncate">{it.subtitle}</span>}
              </span>
            </button>
          ))}
        </div>
        {!q && (
          <p className="px-4 py-3 text-xs text-gray-400 border-t border-gray-100">
            ⌘K / Ctrl+K 로 언제든 열 수 있습니다
          </p>
        )}
      </div>
    </div>
  );
}
