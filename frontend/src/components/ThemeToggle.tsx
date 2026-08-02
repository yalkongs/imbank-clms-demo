import React from 'react';
import { Palette } from 'lucide-react';
import { useTheme } from '../context/ThemeProvider';

/** Classic ↔ Gradient Mesh 세그먼트 토글 (헤더용) */
export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="flex items-center bg-gray-100 rounded-lg p-0.5" role="group" aria-label="테마 선택">
      <button
        onClick={() => setTheme('classic')}
        className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
          theme === 'classic' ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'
        }`}
      >
        Classic
      </button>
      <button
        onClick={() => setTheme('mesh')}
        className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
          theme === 'mesh' ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'
        }`}
      >
        <Palette size={13} />
        Mesh
      </button>
    </div>
  );
}
