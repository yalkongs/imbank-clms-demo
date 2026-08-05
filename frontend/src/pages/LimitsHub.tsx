import PageTabs from './PageTabs';
import Limits from './Limits';
import DynamicLimits from './DynamicLimits';
import BorrowerScope from './BorrowerScope';

export default function LimitsHub() {
  return (
    <PageTabs
      tabs={[
        { key: 'usage',   label: '한도 현황', element: <Limits /> },
        { key: 'dynamic', label: '동적 조정', element: <DynamicLimits /> },
        { key: 'borrower', label: '동일차주', element: <BorrowerScope /> },
      ]}
    />
  );
}
