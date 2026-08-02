import PageTabs from './PageTabs';
import Limits from './Limits';
import DynamicLimits from './DynamicLimits';

export default function LimitsHub() {
  return (
    <PageTabs
      tabs={[
        { key: 'usage',   label: '한도 현황', element: <Limits /> },
        { key: 'dynamic', label: '동적 조정', element: <DynamicLimits /> },
      ]}
    />
  );
}
