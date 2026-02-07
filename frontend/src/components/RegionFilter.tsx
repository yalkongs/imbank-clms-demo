import React from 'react';

const REGIONS = [
  { value: '', label: '전체' },
  { value: 'CAPITAL', label: '수도권' },
  { value: 'DAEGU_GB', label: '대구경북' },
  { value: 'BUSAN_GN', label: '부산경남' },
];

interface RegionFilterProps {
  value: string;
  onChange: (value: string) => void;
  size?: 'sm' | 'md';
}

export default function RegionFilter({ value, onChange, size = 'md' }: RegionFilterProps) {
  const base = size === 'sm'
    ? 'px-2.5 py-1 text-xs'
    : 'px-3 py-1.5 text-sm';

  return (
    <div className="inline-flex rounded-lg border border-gray-300 overflow-hidden">
      {REGIONS.map((r) => (
        <button
          key={r.value}
          type="button"
          onClick={() => onChange(r.value)}
          className={`${base} font-medium transition-colors whitespace-nowrap
            ${value === r.value
              ? 'bg-blue-600 text-white'
              : 'bg-white text-gray-600 hover:bg-gray-50'
            }
            ${r.value !== '' ? 'border-l border-gray-300' : ''}
          `}
        >
          {r.label}
        </button>
      ))}
    </div>
  );
}

export { REGIONS };
