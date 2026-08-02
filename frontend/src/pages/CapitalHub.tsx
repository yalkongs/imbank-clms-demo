import PageTabs from './PageTabs';
import Capital from './Capital';
import CapitalOptimizer from './CapitalOptimizer';

export default function CapitalHub() {
  return (
    <PageTabs
      tabs={[
        { key: 'position',  label: '자본 현황',   element: <Capital /> },
        { key: 'optimizer', label: '자본 최적화', element: <CapitalOptimizer /> },
      ]}
    />
  );
}
