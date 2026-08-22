import React, { useState } from 'react';
import {
  AlertTriangle,
  Activity,
  CreditCard,
  FileWarning,
  TrendingUp,
  Newspaper,
  Network,
  ClipboardCheck,
} from 'lucide-react';
import { FeatureModal, HelpButton, RegionFilter } from '../components';
import { ewsAdvancedApi } from '../utils/api';
import EWSIntegratedDashboard from './ews/EWSIntegratedDashboard';
import EWSTransactionBehavior from './ews/EWSTransactionBehavior';
import EWSPublicRegistry from './ews/EWSPublicRegistry';
import EWSMarketSignals from './ews/EWSMarketSignals';
import EWSNewsSentiment from './ews/EWSNewsSentiment';
import EWSSupplyChain from './ews/EWSSupplyChain';
import EWSActionCenter from './ews/EWSActionCenter';
import EWSExtendedChannels from './ews/EWSExtendedChannels';
import EWSB2BDelinquency from './ews/EWSB2BDelinquency';
import EWSChannelValidation from './ews/EWSChannelValidation';

// 2단 IA (2026-08-22 감사 C): 1차 그룹 4개 - 개요 / 채널 모니터링 /
// 검증·거버넌스 / 조치. 채널 7종은 '채널 모니터링' 아래 2차 탭으로 둔다.
// activeTab 문자열 체계는 그대로 유지 - 그룹은 표시 계층일 뿐이다.
const TAB_GROUPS = [
  { id: 'overview', label: '개요', tabs: [
    { id: 'integrated', label: '통합 대시보드', icon: <Activity size={16} /> },
  ]},
  { id: 'channels', label: '채널 모니터링', tabs: [
    { id: 'transaction', label: '거래행태', icon: <CreditCard size={16} /> },
    { id: 'public', label: '공적정보', icon: <FileWarning size={16} /> },
    { id: 'market', label: '시장신호', icon: <TrendingUp size={16} /> },
    { id: 'news', label: '뉴스/감성', icon: <Newspaper size={16} /> },
    { id: 'supply', label: '공급망', icon: <Network size={16} /> },
    { id: 'extended', label: '매출·고용', icon: <CreditCard size={16} /> },
    { id: 'b2b', label: '상거래연체', icon: <FileWarning size={16} /> },
  ]},
  { id: 'governance', label: '검증·거버넌스', tabs: [
    { id: 'validation', label: '채널 검증', icon: <Activity size={16} /> },
  ]},
  { id: 'ops', label: '조치', tabs: [
    { id: 'actions', label: '조치 관리', icon: <ClipboardCheck size={16} /> },
  ]},
];
const groupOf = (tabId: string) =>
  TAB_GROUPS.find(g => g.tabs.some(t => t.id === tabId)) || TAB_GROUPS[0];
// 전역 지역 필터가 적용되는 탭 (신규 채널·검증 API 는 지역 파라미터 미지원)
const REGION_TABS = new Set(['integrated', 'transaction', 'public', 'market', 'news', 'supply']);

export default function EWSAdvanced() {
  const [activeTab, setActiveTab] = useState('integrated');
  const [region, setRegion] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [featureInfo, setFeatureInfo] = useState<any>(null);

  const openFeatureModal = async (featureId: string) => {
    try {
      const res = await ewsAdvancedApi.getFeatureDescription(featureId);
      setFeatureInfo(res.data);
      setModalOpen(true);
    } catch (error) {
      console.error('Feature description load error:', error);
    }
  };

  const renderTab = () => {
    switch (activeTab) {
      case 'integrated': return <EWSIntegratedDashboard region={region} />;
      case 'transaction': return <EWSTransactionBehavior region={region} />;
      case 'public': return <EWSPublicRegistry region={region} />;
      case 'market': return <EWSMarketSignals region={region} />;
      case 'news': return <EWSNewsSentiment region={region} />;
      case 'supply': return <EWSSupplyChain region={region} />;
      case 'extended': return <EWSExtendedChannels />;
      case 'b2b': return <EWSB2BDelinquency />;
      case 'validation': return <EWSChannelValidation />;
      case 'actions': return <EWSActionCenter />;
      default: return <EWSIntegratedDashboard region={region} />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            <AlertTriangle className="mr-2 text-yellow-600" size={24} />
            EWS 조기경보 시스템
            <HelpButton onClick={() => openFeatureModal('ews_overview')} />
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            8채널 선행지표 통합 모니터링 (거래행태·공적·시장·뉴스·공급망 + 카드매출·고용·상거래연체) · 채널 선행성 백테스트 검증
          </p>
        </div>
        {REGION_TABS.has(activeTab) && <RegionFilter value={region} onChange={setRegion} />}
      </div>

      {/* 2단 탭 네비게이션: 1차 그룹 → 2차 채널 */}
      <div className="border-b border-gray-200">
        <nav className="flex flex-wrap gap-1 -mb-px">
          {TAB_GROUPS.map(g => (
            <button
              key={g.id}
              onClick={() => setActiveTab(g.tabs[0].id)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors ${
                groupOf(activeTab).id === g.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {g.label}
              {g.tabs.length > 1 && (
                <span className="text-[10px] font-normal text-gray-400">{g.tabs.length}</span>
              )}
            </button>
          ))}
        </nav>
      </div>
      {groupOf(activeTab).tabs.length > 1 && (
        <div className="flex flex-wrap gap-1.5 -mt-2">
          {groupOf(activeTab).tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full border transition-colors ${
                activeTab === tab.id
                  ? 'bg-[#00897B] text-white border-[#00897B]'
                  : 'border-gray-300 text-gray-600 hover:bg-gray-50'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {/* 탭 컨텐츠 */}
      {renderTab()}

      {/* Feature Modal */}
      <FeatureModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        feature={featureInfo}
      />
    </div>
  );
}
