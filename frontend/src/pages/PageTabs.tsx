import React from 'react';
import { useSearchParams } from 'react-router-dom';

/**
 * 같은 대상의 '현황'과 '최적화·시뮬레이션' 화면을 한 페이지의 탭으로 묶는다.
 *
 * 자본관리↔자본최적화, 포트폴리오↔포트폴리오최적화, 한도관리↔동적한도는
 * 각각 같은 대상을 보는 두 국면인데 좌측 메뉴에 따로 나열돼 있어
 * 처음 보는 사람은 차이를 알기 어려웠다. 메뉴 항목을 줄이고 업무 흐름
 * (현황을 보다 그 자리에서 시뮬레이션)에 맞추기 위해 탭으로 합쳤다.
 *
 * 각 하위 페이지는 자체 제목을 그대로 갖고 있으므로 여기서는 탭 바만 얹는다.
 * 선택 상태는 ?tab= 로 URL 에 남겨 새로고침·공유에도 유지된다.
 */

export interface TabDef {
  key: string;
  label: string;
  element: React.ReactNode;
}

interface Props {
  tabs: TabDef[];
}

export default function PageTabs({ tabs }: Props) {
  const [params, setParams] = useSearchParams();
  const requested = params.get('tab');
  const active = tabs.some(t => t.key === requested) ? requested! : tabs[0].key;

  const select = (key: string) => {
    const next = new URLSearchParams(params);
    if (key === tabs[0].key) next.delete('tab');
    else next.set('tab', key);
    setParams(next, { replace: true });
  };

  return (
    <div>
      <div className="flex gap-1 border-b border-gray-200 mb-5" role="tablist">
        {tabs.map(t => {
          const on = t.key === active;
          return (
            <button
              key={t.key}
              role="tab"
              aria-selected={on}
              onClick={() => select(t.key)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
                on
                  ? 'border-blue-600 text-blue-700'
                  : 'border-transparent text-gray-500 hover:text-gray-800 hover:border-gray-300'
              }`}
            >
              {t.label}
            </button>
          );
        })}
      </div>
      {tabs.find(t => t.key === active)?.element}
    </div>
  );
}
