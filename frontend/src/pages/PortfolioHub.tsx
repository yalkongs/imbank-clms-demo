import PageTabs from './PageTabs';
import Portfolio from './Portfolio';
import PortfolioOptimization from './PortfolioOptimization';

export default function PortfolioHub() {
  return (
    <PageTabs
      tabs={[
        { key: 'strategy',  label: '포트폴리오 전략', element: <Portfolio /> },
        { key: 'optimizer', label: '최적화',          element: <PortfolioOptimization /> },
      ]}
    />
  );
}
