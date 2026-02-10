import React, { useState } from 'react';
import {
  AlertTriangle,
  Activity,
  CreditCard,
  FileWarning,
  TrendingUp,
  Newspaper,
  Network,
} from 'lucide-react';
import { FeatureModal, HelpButton, RegionFilter } from '../components';
import { ewsAdvancedApi } from '../utils/api';
import EWSIntegratedDashboard from './ews/EWSIntegratedDashboard';
import EWSTransactionBehavior from './ews/EWSTransactionBehavior';
import EWSPublicRegistry from './ews/EWSPublicRegistry';
import EWSMarketSignals from './ews/EWSMarketSignals';
import EWSNewsSentiment from './ews/EWSNewsSentiment';
import EWSSupplyChain from './ews/EWSSupplyChain';

const TABS = [
  { id: 'integrated', label: '통합 대시보드', icon: <Activity size={16} /> },
  { id: 'transaction', label: '거래행태', icon: <CreditCard size={16} /> },
  { id: 'public', label: '공적정보', icon: <FileWarning size={16} /> },
  { id: 'market', label: '시장신호', icon: <TrendingUp size={16} /> },
  { id: 'news', label: '뉴스/감성', icon: <Newspaper size={16} /> },
  { id: 'supply', label: '공급망', icon: <Network size={16} /> },
];

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
            5채널 선행지표 통합 모니터링 (거래행태 / 공적정보 / 시장신호 / 뉴스감성 / 공급망)
          </p>
        </div>
        <RegionFilter value={region} onChange={setRegion} />
      </div>

      {/* 탭 네비게이션 */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-1 -mb-px">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

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
