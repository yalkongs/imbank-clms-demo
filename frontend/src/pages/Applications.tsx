import React, { useEffect, useState, useCallback } from 'react';
import {
  Search,
  Filter,
  FileText,
  Clock,
  CheckCircle,
  XCircle,
  ChevronRight,
  AlertTriangle,
  Calculator,
  X,
  TrendingUp,
  TrendingDown,
  Building2,
  CreditCard,
  Shield,
  BarChart3,
  FileCheck,
  Users,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  AlertCircle,
  Info,
  Check,
  Minus
} from 'lucide-react';
import { Card, Table, Badge, CellFormatters } from '../components';
import { applicationsApi } from '../utils/api';
import { formatAmount, formatPercent, formatDate, formatInputAmount, parseFormattedNumber } from '../utils/format';

// 심사 단계 정의
const REVIEW_STAGES = [
  { key: 'RECEIVED', name: '접수', icon: FileText },
  { key: 'DOC_REVIEW', name: '서류검토', icon: FileCheck },
  { key: 'CREDIT_REVIEW', name: '신용평가', icon: BarChart3 },
  { key: 'COLLATERAL_REVIEW', name: '담보평가', icon: Shield },
  { key: 'LIMIT_CHECK', name: '한도심사', icon: AlertTriangle },
  { key: 'PRICING', name: '가격결정', icon: Calculator },
  { key: 'FINAL_REVIEW', name: '최종심사', icon: Users },
  { key: 'COMPLETED', name: '완료', icon: CheckCircle }
];

// 체크리스트 아이콘
const ChecklistIcon = ({ status }: { status: string }) => {
  if (status === 'checked') return <Check className="text-green-600" size={16} />;
  if (status === 'warning') return <AlertCircle className="text-yellow-600" size={16} />;
  if (status === 'danger') return <XCircle className="text-red-600" size={16} />;
  if (status === 'N/A') return <Minus className="text-gray-400" size={16} />;
  return <Clock className="text-gray-400" size={16} />;
};

export default function Applications() {
  const [loading, setLoading] = useState(true);
  const [applications, setApplications] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [selectedApp, setSelectedApp] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [filter, setFilter] = useState('ALL');
  const [stageFilter, setStageFilter] = useState<string | null>(null);

  // 탭 상태
  const [activeTab, setActiveTab] = useState<'info' | 'credit' | 'collateral' | 'limit' | 'pricing' | 'checklist'>('info');

  // 확장/축소 상태
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    existing: false,
    facilities: false,
    history: false
  });

  // 상세 모달 상태
  const [showDetailModal, setShowDetailModal] = useState(false);

  // What-if 모달 상태
  const [showWhatIfModal, setShowWhatIfModal] = useState(false);
  const [whatIfLoading, setWhatIfLoading] = useState(false);
  const [whatIfResult, setWhatIfResult] = useState<any>(null);
  const [whatIfParams, setWhatIfParams] = useState({
    amount: 0,
    rate: 0,
    tenor: 0
  });

  // 승인 모달 상태
  const [showApprovalModal, setShowApprovalModal] = useState(false);
  const [approvalLoading, setApprovalLoading] = useState(false);
  const [approvalData, setApprovalData] = useState({
    decision: 'APPROVE',
    approval_level: '',
    approver_name: '',
    conditions: '',
    comments: '',
    approved_amount: 0,
    approved_rate: 0,
    approved_tenor: 0
  });

  // 디바운스 타이머
  const [debounceTimer, setDebounceTimer] = useState<NodeJS.Timeout | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [appsRes, summaryRes] = await Promise.all([
        applicationsApi.getPending(),
        applicationsApi.getSummary()
      ]);
      setApplications(appsRes.data || []);
      setSummary(summaryRes.data);
    } catch (error) {
      console.error('Data load error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadDetail = async (id: string) => {
    setDetailLoading(true);
    try {
      const response = await applicationsApi.getById(id);
      setSelectedApp(response.data);
      setActiveTab('info');
    } catch (error) {
      console.error('Detail load error:', error);
    } finally {
      setDetailLoading(false);
    }
  };

  // 상세 로드 후 모달 열기
  const handleRowClick = async (id: string) => {
    await loadDetail(id);
    setShowDetailModal(true);
  };

  // 모달 닫기
  const closeDetailModal = () => {
    setShowDetailModal(false);
  };

  // What-if 모달 열기
  const openWhatIfModal = useCallback(async () => {
    if (!selectedApp) return;
    const initialParams = {
      amount: selectedApp.application?.requested_amount || 0,
      rate: (selectedApp.pricing?.final_rate || 0.05) * 100,
      tenor: selectedApp.application?.requested_tenor || 36
    };
    setWhatIfParams(initialParams);
    setWhatIfResult(null);
    setShowWhatIfModal(true);

    setWhatIfLoading(true);
    try {
      const response = await applicationsApi.simulate(
        selectedApp.application.application_id,
        {
          amount: initialParams.amount,
          rate: initialParams.rate / 100,
          tenor: initialParams.tenor
        }
      );
      setWhatIfResult(response.data);
    } catch (error) {
      console.error('Initial simulation error:', error);
    } finally {
      setWhatIfLoading(false);
    }
  }, [selectedApp]);

  // What-if 시뮬레이션 실행
  const runWhatIfSimulation = useCallback(async (params: typeof whatIfParams) => {
    if (!selectedApp) return;
    setWhatIfLoading(true);
    try {
      const response = await applicationsApi.simulate(
        selectedApp.application.application_id,
        {
          amount: params.amount,
          rate: params.rate / 100,
          tenor: params.tenor
        }
      );
      setWhatIfResult(response.data);
    } catch (error) {
      console.error('What-if simulation error:', error);
    } finally {
      setWhatIfLoading(false);
    }
  }, [selectedApp]);

  const handleWhatIfParamChange = useCallback((newParams: typeof whatIfParams) => {
    setWhatIfParams(newParams);
    if (debounceTimer) clearTimeout(debounceTimer);
    const timer = setTimeout(() => runWhatIfSimulation(newParams), 300);
    setDebounceTimer(timer);
  }, [debounceTimer, runWhatIfSimulation]);

  // 승인 모달 열기
  const openApprovalModal = () => {
    if (!selectedApp) return;
    setApprovalData({
      decision: 'APPROVE',
      approval_level: selectedApp.required_authority?.level || 'STAFF',
      approver_name: '김여신',
      conditions: '',
      comments: '',
      approved_amount: selectedApp.application?.requested_amount || 0,
      approved_rate: (selectedApp.pricing?.final_rate || 0) * 100,
      approved_tenor: selectedApp.application?.requested_tenor || 36
    });
    setShowApprovalModal(true);
  };

  // 승인/반려 처리
  const handleApproval = async () => {
    if (!selectedApp) return;
    setApprovalLoading(true);
    try {
      await applicationsApi.approve(
        selectedApp.application.application_id,
        approvalData.decision,
        {
          approval_level: approvalData.approval_level,
          approver_name: approvalData.approver_name,
          conditions: approvalData.conditions || undefined,
          comments: approvalData.comments || undefined,
          approved_amount: approvalData.approved_amount,
          approved_rate: approvalData.approved_rate / 100,
          approved_tenor: approvalData.approved_tenor
        }
      );
      setShowApprovalModal(false);
      setShowDetailModal(false);
      await loadData();
    } catch (error) {
      console.error('Approval error:', error);
    } finally {
      setApprovalLoading(false);
    }
  };

  // 필터링
  const filteredApps = applications.filter(app => {
    if (filter !== 'ALL' && app.status !== filter) return false;
    if (stageFilter && app.current_stage !== stageFilter) return false;
    return true;
  });

  const columns = [
    {
      key: 'application_id',
      header: '신청번호',
      width: '120px',
      render: (value: string) => (
        <span className="font-mono text-blue-600 text-sm">{value}</span>
      )
    },
    {
      key: 'customer_name',
      header: '고객명',
      render: (value: string, row: any) => (
        <div>
          <p className="font-medium text-gray-900">{value}</p>
          <p className="text-xs text-gray-500">{row.industry_name}</p>
        </div>
      )
    },
    {
      key: 'requested_amount',
      header: '신청금액',
      align: 'right' as const,
      width: '120px',
      render: (value: number) => CellFormatters.amountBillion(value)
    },
    {
      key: 'stage_name',
      header: '심사단계',
      width: '100px',
      render: (value: string) => (
        <span className="text-xs px-2 py-1 bg-blue-50 text-blue-700 rounded-full">
          {value}
        </span>
      )
    },
    {
      key: 'priority',
      header: '우선순위',
      align: 'center' as const,
      width: '80px',
      render: (value: string) => {
        const colors: Record<string, string> = {
          HIGH: 'text-red-600 font-bold',
          NORMAL: 'text-gray-600',
          LOW: 'text-gray-400'
        };
        return <span className={`text-sm ${colors[value] || 'text-gray-600'}`}>{value}</span>;
      }
    },
    {
      key: 'required_authority',
      header: '승인권한',
      width: '100px',
      render: (value: any) => (
        <span className="text-sm text-orange-600 font-medium">{value?.name || '-'}</span>
      )
    },
    {
      key: 'final_grade',
      header: '신용등급',
      align: 'center' as const,
      width: '80px',
      render: (value: string) => (
        <span className="font-bold text-gray-900">{value || '-'}</span>
      )
    }
  ];

  const getStatusCounts = () => {
    const all = applications.length;
    const byStage: Record<string, number> = {};
    applications.forEach(app => {
      byStage[app.current_stage] = (byStage[app.current_stage] || 0) + 1;
    });
    return { all, byStage };
  };

  const counts = getStatusCounts();

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // 현재 단계 인덱스
  const getCurrentStageIndex = (stage: string) => {
    return REVIEW_STAGES.findIndex(s => s.key === stage);
  };

  return (
    <div className="space-y-4">
      {/* 페이지 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">여신심사</h1>
          <p className="text-sm text-gray-500 mt-1">기업여신 심사 및 승인 관리</p>
        </div>
        <button
          onClick={loadData}
          className="flex items-center px-3 py-2 text-sm text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          <RefreshCw size={16} className="mr-2" />
          새로고침
        </button>
      </div>

      {/* 심사 현황 요약 */}
      {summary && (
        <div className="grid grid-cols-6 gap-3">
          <div className="p-3 bg-white rounded-lg border border-gray-200">
            <p className="text-xs text-gray-500">금일 접수</p>
            <p className="text-xl font-bold text-blue-600">{summary.today?.received || 0}건</p>
          </div>
          <div className="p-3 bg-white rounded-lg border border-gray-200">
            <p className="text-xs text-gray-500">심사 대기</p>
            <p className="text-xl font-bold text-yellow-600">{summary.today?.pending_total || 0}건</p>
          </div>
          <div className="p-3 bg-white rounded-lg border border-gray-200">
            <p className="text-xs text-gray-500">긴급 건</p>
            <p className="text-xl font-bold text-red-600">{summary.today?.pending_high_priority || 0}건</p>
          </div>
          <div className="p-3 bg-white rounded-lg border border-gray-200">
            <p className="text-xs text-gray-500">금일 처리</p>
            <p className="text-xl font-bold text-green-600">{summary.today?.processed || 0}건</p>
          </div>
          <div className="p-3 bg-white rounded-lg border border-gray-200">
            <p className="text-xs text-gray-500">평균 처리일</p>
            <p className="text-xl font-bold text-gray-700">{summary.avg_processing_days || '-'}일</p>
          </div>
          <div className="p-3 bg-white rounded-lg border border-gray-200">
            <p className="text-xs text-gray-500">전체 건수</p>
            <p className="text-xl font-bold text-gray-700">{counts.all}건</p>
          </div>
        </div>
      )}

      {/* 단계별 필터 */}
      <div className="flex items-center space-x-2 overflow-x-auto pb-2">
        <button
          onClick={() => setStageFilter(null)}
          className={`px-3 py-1.5 text-sm rounded-full whitespace-nowrap transition-colors ${
            !stageFilter
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          전체 ({counts.all})
        </button>
        {REVIEW_STAGES.slice(0, -1).map(stage => {
          const count = counts.byStage[stage.key] || 0;
          const Icon = stage.icon;
          return (
            <button
              key={stage.key}
              onClick={() => setStageFilter(stage.key)}
              className={`flex items-center px-3 py-1.5 text-sm rounded-full whitespace-nowrap transition-colors ${
                stageFilter === stage.key
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <Icon size={14} className="mr-1.5" />
              {stage.name} ({count})
            </button>
          );
        })}
      </div>

      {/* 심사 대기 목록 (전체 너비) */}
      <Card
        title="심사 대기 목록"
        headerAction={
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={14} />
            <input
              type="text"
              placeholder="검색..."
              className="pl-8 pr-3 py-1 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 w-48"
            />
          </div>
        }
        noPadding
      >
        <Table
          columns={columns}
          data={filteredApps}
          loading={loading}
          onRowClick={(row) => handleRowClick(row.application_id)}
          selectedKey="application_id"
          selectedValue={selectedApp?.application?.application_id}
        />
      </Card>

      {/* 상세 정보 모달 */}
      {showDetailModal && selectedApp && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-6xl max-h-[95vh] overflow-hidden flex flex-col">
            {/* 모달 헤더 */}
            <div className="flex items-center justify-between p-4 border-b bg-gray-50">
              <div className="flex items-center space-x-6">
                <div>
                  <h3 className="text-xl font-bold text-gray-900">
                    {selectedApp.customer?.customer_name}
                  </h3>
                  <p className="text-sm text-gray-500">
                    {selectedApp.application?.application_id} | {selectedApp.customer?.industry_name}
                  </p>
                </div>
                <div className="pl-6 border-l">
                  <p className="text-2xl font-bold text-blue-600">
                    {formatAmount(selectedApp.application?.requested_amount || 0, 'billion')}
                  </p>
                  <p className="text-sm text-gray-500">
                    {selectedApp.application?.requested_tenor}개월 | {selectedApp.product?.product_name}
                  </p>
                </div>
              </div>
              <button onClick={closeDetailModal} className="p-2 hover:bg-gray-200 rounded-lg transition-colors">
                <X size={24} />
              </button>
            </div>

            {/* 단계 진행 표시 */}
            <div className="px-6 py-4 border-b bg-white">
              <div className="flex items-center justify-between">
                {REVIEW_STAGES.map((stage, index) => {
                  const currentIndex = getCurrentStageIndex(selectedApp.application?.current_stage);
                  const isCompleted = index < currentIndex;
                  const isCurrent = index === currentIndex;
                  const Icon = stage.icon;

                  return (
                    <React.Fragment key={stage.key}>
                      <div className="flex flex-col items-center">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          isCompleted ? 'bg-green-100 text-green-600' :
                          isCurrent ? 'bg-blue-600 text-white' :
                          'bg-gray-100 text-gray-400'
                        }`}>
                          {isCompleted ? <Check size={20} /> : <Icon size={20} />}
                        </div>
                        <span className={`text-xs mt-1 ${
                          isCurrent ? 'text-blue-600 font-medium' : 'text-gray-500'
                        }`}>
                          {stage.name}
                        </span>
                      </div>
                      {index < REVIEW_STAGES.length - 1 && (
                        <div className={`flex-1 h-0.5 mx-2 ${
                          index < currentIndex ? 'bg-green-400' : 'bg-gray-200'
                        }`} />
                      )}
                    </React.Fragment>
                  );
                })}
              </div>
            </div>

            {/* 탭 메뉴 */}
            <div className="flex border-b border-gray-200 bg-white px-4">
              {[
                { key: 'info', label: '기본정보', icon: Info },
                { key: 'credit', label: '신용평가', icon: BarChart3 },
                { key: 'collateral', label: '담보정보', icon: Shield },
                { key: 'limit', label: '한도심사', icon: AlertTriangle },
                { key: 'pricing', label: '수익성', icon: Calculator },
                { key: 'checklist', label: '체크리스트', icon: FileCheck }
              ].map(tab => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key as any)}
                    className={`flex items-center px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === tab.key
                        ? 'border-blue-600 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    <Icon size={16} className="mr-1.5" />
                    {tab.label}
                  </button>
                );
              })}
            </div>

            {/* 탭 콘텐츠 */}
            <div className="flex-1 overflow-y-auto p-6">
              {detailLoading ? (
                <div className="flex justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* 기본정보 탭 */}
                  {activeTab === 'info' && (
                    <div className="grid grid-cols-2 gap-6">
                      {/* 고객 정보 */}
                      <div>
                        <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                          <Building2 size={16} className="mr-1.5" />
                          고객 정보
                        </h4>
                        <div className="grid grid-cols-2 gap-3 bg-gray-50 p-4 rounded-lg">
                          <div>
                            <p className="text-xs text-gray-500">고객명</p>
                            <p className="text-sm font-medium">{selectedApp.customer?.customer_name}</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">사업자번호</p>
                            <p className="text-sm font-mono">{selectedApp.customer?.business_number}</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">업종</p>
                            <p className="text-sm">{selectedApp.customer?.industry_name}</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">기업규모</p>
                            <p className="text-sm">{selectedApp.customer?.size_category}</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">설립일</p>
                            <p className="text-sm">{selectedApp.customer?.establishment_date || '-'}</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">종업원수</p>
                            <p className="text-sm">{selectedApp.customer?.employees?.toLocaleString() || '-'}명</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">자산규모</p>
                            <p className="text-sm font-medium">{formatAmount(selectedApp.customer?.asset_size || 0, 'billion')}</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">매출규모</p>
                            <p className="text-sm font-medium">{formatAmount(selectedApp.customer?.revenue_size || 0, 'billion')}</p>
                          </div>
                        </div>
                      </div>

                      {/* 신청 정보 */}
                      <div>
                        <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                          <FileText size={16} className="mr-1.5" />
                          신청 정보
                        </h4>
                        <div className="grid grid-cols-2 gap-3 bg-gray-50 p-4 rounded-lg">
                          <div>
                            <p className="text-xs text-gray-500">신청금액</p>
                            <p className="text-sm font-bold text-blue-600">
                              {formatAmount(selectedApp.application?.requested_amount || 0, 'billion')}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">신청기간</p>
                            <p className="text-sm">{selectedApp.application?.requested_tenor}개월</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">상품유형</p>
                            <p className="text-sm">{selectedApp.product?.product_name}</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">신청일</p>
                            <p className="text-sm">{selectedApp.application?.application_date}</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">자금용도</p>
                            <p className="text-sm">{selectedApp.application?.purpose_detail || selectedApp.application?.purpose_code || '-'}</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">승인필요권한</p>
                            <p className="text-sm font-medium text-orange-600">
                              {selectedApp.required_authority?.name || '-'}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">전략코드</p>
                            <Badge variant={
                              selectedApp.strategy?.strategy_code === 'GROW' ? 'success' :
                              selectedApp.strategy?.strategy_code === 'REDUCE' ? 'danger' :
                              'info'
                            }>
                              {selectedApp.strategy?.strategy_code || '-'}
                            </Badge>
                          </div>
                        </div>
                      </div>

                      {/* 기존 여신 현황 */}
                      <div className="col-span-2">
                        <button
                          onClick={() => toggleSection('existing')}
                          className="w-full flex items-center justify-between text-sm font-semibold text-gray-700 mb-3"
                        >
                          <span className="flex items-center">
                            <CreditCard size={16} className="mr-1.5" />
                            기존 여신 현황
                            <span className="ml-2 text-xs font-normal text-gray-500">
                              ({selectedApp.existing_summary?.active_count || 0}건 /
                              {formatAmount(selectedApp.existing_summary?.total_outstanding || 0, 'billion')})
                            </span>
                          </span>
                          {expandedSections.existing ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </button>
                        {expandedSections.existing && (
                          <div className="bg-gray-50 p-4 rounded-lg">
                            <div className="grid grid-cols-4 gap-3 mb-4">
                              <div className="text-center p-3 bg-white rounded-lg">
                                <p className="text-xs text-gray-500">여신건수</p>
                                <p className="text-xl font-bold">{selectedApp.existing_summary?.active_count || 0}건</p>
                              </div>
                              <div className="text-center p-3 bg-white rounded-lg">
                                <p className="text-xs text-gray-500">총한도</p>
                                <p className="text-xl font-bold">{formatAmount(selectedApp.existing_summary?.total_limit || 0, 'billion')}</p>
                              </div>
                              <div className="text-center p-3 bg-white rounded-lg">
                                <p className="text-xs text-gray-500">사용잔액</p>
                                <p className="text-xl font-bold">{formatAmount(selectedApp.existing_summary?.total_outstanding || 0, 'billion')}</p>
                              </div>
                              <div className="text-center p-3 bg-blue-50 rounded-lg">
                                <p className="text-xs text-gray-500">승인후 총익스포저</p>
                                <p className="text-xl font-bold text-blue-600">{formatAmount(selectedApp.existing_summary?.new_total_exposure || 0, 'billion')}</p>
                              </div>
                            </div>
                            {selectedApp.existing_facilities?.length > 0 && (
                              <table className="w-full text-sm">
                                <thead>
                                  <tr className="border-b bg-white">
                                    <th className="text-left py-2 px-2">상품</th>
                                    <th className="text-right py-2">한도</th>
                                    <th className="text-right py-2">잔액</th>
                                    <th className="text-right py-2">금리</th>
                                    <th className="text-center py-2">만기</th>
                                    <th className="text-center py-2 px-2">상태</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {selectedApp.existing_facilities.map((f: any, idx: number) => (
                                    <tr key={idx} className="border-b border-gray-100">
                                      <td className="py-2 px-2">{f.product_name || f.facility_type}</td>
                                      <td className="text-right py-2 font-mono">{formatAmount(f.limit || 0, 'billion')}</td>
                                      <td className="text-right py-2 font-mono">{formatAmount(f.outstanding || 0, 'billion')}</td>
                                      <td className="text-right py-2 font-mono">{formatPercent((f.rate || 0) * 100)}</td>
                                      <td className="text-center py-2">{f.maturity || '-'}</td>
                                      <td className="text-center py-2 px-2">
                                        <Badge variant={f.status === 'ACTIVE' ? 'success' : 'secondary'}>
                                          {f.status}
                                        </Badge>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* 신용평가 탭 */}
                  {activeTab === 'credit' && (
                    <div className="space-y-6">
                      <div className="grid grid-cols-2 gap-6">
                        {/* 현재 등급 */}
                        <div className="bg-blue-50 p-6 rounded-lg text-center">
                          <p className="text-sm text-gray-600 mb-2">최종 신용등급</p>
                          <p className="text-5xl font-bold text-blue-700">{selectedApp.rating?.final_grade || '-'}</p>
                          <p className="text-sm text-gray-500 mt-2">평가일: {selectedApp.rating?.rating_date || '-'}</p>
                        </div>
                        <div className="space-y-3">
                          <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                            <span className="text-sm text-gray-600">PD (부도확률)</span>
                            <span className="text-lg font-bold font-mono">
                              {formatPercent((selectedApp.rating?.pd_value || 0) * 100, 3)}
                            </span>
                          </div>
                          <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                            <span className="text-sm text-gray-600">평가모델</span>
                            <span className="text-sm font-medium">{selectedApp.rating?.model_id || '-'}</span>
                          </div>
                          <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                            <span className="text-sm text-gray-600">Override</span>
                            <span className={`text-sm ${selectedApp.rating?.override_grade ? 'text-yellow-600 font-medium' : 'text-gray-500'}`}>
                              {selectedApp.rating?.override_grade || '없음'}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* 등급 이력 */}
                      {selectedApp.rating_history?.length > 0 && (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-700 mb-3">등급 이력</h4>
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b bg-gray-50">
                                <th className="text-left py-2 px-3">평가일</th>
                                <th className="text-center py-2">등급</th>
                                <th className="text-right py-2 px-3">PD</th>
                                <th className="text-left py-2 px-3">모델</th>
                              </tr>
                            </thead>
                            <tbody>
                              {selectedApp.rating_history.map((r: any, idx: number) => (
                                <tr key={idx} className="border-b hover:bg-gray-50">
                                  <td className="py-2 px-3">{r.rating_date}</td>
                                  <td className="text-center py-2 font-bold text-lg">{r.grade}</td>
                                  <td className="text-right py-2 px-3 font-mono">{formatPercent((r.pd || 0) * 100, 3)}</td>
                                  <td className="py-2 px-3 text-gray-500">{r.model}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}

                      {/* 리스크 파라미터 */}
                      {selectedApp.risk_parameter && (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-700 mb-3">리스크 파라미터</h4>
                          <div className="grid grid-cols-4 gap-4">
                            <div className="p-4 bg-gray-50 rounded-lg text-center">
                              <p className="text-xs text-gray-500">TTC PD</p>
                              <p className="text-xl font-bold font-mono">
                                {formatPercent((selectedApp.risk_parameter.ttc_pd || 0) * 100, 3)}
                              </p>
                            </div>
                            <div className="p-4 bg-gray-50 rounded-lg text-center">
                              <p className="text-xs text-gray-500">PIT PD</p>
                              <p className="text-xl font-bold font-mono">
                                {formatPercent((selectedApp.risk_parameter.pit_pd || 0) * 100, 3)}
                              </p>
                            </div>
                            <div className="p-4 bg-gray-50 rounded-lg text-center">
                              <p className="text-xs text-gray-500">LGD</p>
                              <p className="text-xl font-bold font-mono">
                                {formatPercent((selectedApp.risk_parameter.lgd || 0) * 100)}
                              </p>
                            </div>
                            <div className="p-4 bg-gray-50 rounded-lg text-center">
                              <p className="text-xs text-gray-500">EAD</p>
                              <p className="text-xl font-bold">
                                {formatAmount(selectedApp.risk_parameter.ead || 0, 'billion')}
                              </p>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* 담보정보 탭 */}
                  {activeTab === 'collateral' && (
                    <div className="space-y-6">
                      <div className="grid grid-cols-3 gap-4">
                        <div className="p-4 bg-gray-50 rounded-lg text-center">
                          <p className="text-xs text-gray-500">담보유형</p>
                          <p className="text-xl font-medium">{selectedApp.application?.collateral_type || '무담보'}</p>
                        </div>
                        <div className="p-4 bg-gray-50 rounded-lg text-center">
                          <p className="text-xs text-gray-500">담보가액</p>
                          <p className="text-xl font-bold">
                            {formatAmount(selectedApp.application?.collateral_value || 0, 'billion')}
                          </p>
                        </div>
                        <div className="p-4 bg-gray-50 rounded-lg text-center">
                          <p className="text-xs text-gray-500">LTV</p>
                          <p className={`text-xl font-bold ${
                            selectedApp.application?.collateral_value > 0 &&
                            (selectedApp.application?.requested_amount / selectedApp.application?.collateral_value * 100) > 70
                              ? 'text-red-600' : 'text-green-600'
                          }`}>
                            {selectedApp.application?.collateral_value > 0
                              ? formatPercent(selectedApp.application?.requested_amount / selectedApp.application?.collateral_value * 100)
                              : '-'
                            }
                          </p>
                        </div>
                      </div>

                      {selectedApp.collaterals?.length > 0 ? (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-700 mb-3">담보 목록</h4>
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b bg-gray-50">
                                <th className="text-left py-2 px-3">담보유형</th>
                                <th className="text-right py-2">감정가</th>
                                <th className="text-right py-2">현재가</th>
                                <th className="text-right py-2">LTV</th>
                                <th className="text-center py-2">순위</th>
                                <th className="text-center py-2 px-3">감정일</th>
                              </tr>
                            </thead>
                            <tbody>
                              {selectedApp.collaterals.map((c: any, idx: number) => (
                                <tr key={idx} className="border-b hover:bg-gray-50">
                                  <td className="py-2 px-3">{c.collateral_type} {c.collateral_subtype && `(${c.collateral_subtype})`}</td>
                                  <td className="text-right py-2 font-mono">{formatAmount(c.original_value || 0, 'billion')}</td>
                                  <td className="text-right py-2 font-mono">{formatAmount(c.current_value || 0, 'billion')}</td>
                                  <td className="text-right py-2 font-mono">{formatPercent((c.ltv || 0) * 100)}</td>
                                  <td className="text-center py-2">{c.priority_rank}순위</td>
                                  <td className="text-center py-2 px-3">{c.valuation_date || '-'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="text-center py-12 text-gray-500">
                          <Shield size={64} className="mx-auto mb-4 text-gray-300" />
                          <p className="text-lg">등록된 담보가 없습니다</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* 한도심사 탭 */}
                  {activeTab === 'limit' && (
                    <div className="space-y-6">
                      {selectedApp.limits?.length > 0 ? (
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b bg-gray-50">
                              <th className="text-left py-2 px-3">한도명</th>
                              <th className="text-center py-2">유형</th>
                              <th className="text-right py-2">한도액</th>
                              <th className="text-right py-2">사용액</th>
                              <th className="text-right py-2">사용률</th>
                              <th className="text-right py-2">승인후</th>
                              <th className="text-center py-2 px-3">상태</th>
                            </tr>
                          </thead>
                          <tbody>
                            {selectedApp.limits.map((l: any, idx: number) => (
                              <tr key={idx} className="border-b hover:bg-gray-50">
                                <td className="py-2 px-3 font-medium">{l.limit_name}</td>
                                <td className="text-center py-2 text-gray-500">{l.dimension_type}</td>
                                <td className="text-right py-2 font-mono">{formatAmount(l.limit_amount || 0, 'billion')}</td>
                                <td className="text-right py-2 font-mono">{formatAmount(l.exposure_amount || 0, 'billion')}</td>
                                <td className="text-right py-2">
                                  <span className={`font-mono ${
                                    (l.utilization_rate || 0) > 100 ? 'text-red-600 font-bold' :
                                    (l.utilization_rate || 0) > 90 ? 'text-yellow-600' : 'text-gray-600'
                                  }`}>
                                    {formatPercent(l.utilization_rate || 0)}
                                  </span>
                                </td>
                                <td className="text-right py-2">
                                  <span className={`font-mono ${
                                    (l.after_utilization || 0) > 100 ? 'text-red-600 font-bold' : 'text-gray-600'
                                  }`}>
                                    {formatPercent(l.after_utilization || 0)}
                                  </span>
                                </td>
                                <td className="text-center py-2 px-3">
                                  <Badge variant={
                                    l.status === 'BREACH' || (l.after_utilization || 0) > 100 ? 'danger' :
                                    (l.utilization_rate || 0) > 90 ? 'warning' : 'success'
                                  }>
                                    {l.status === 'BREACH' || (l.after_utilization || 0) > 100 ? '초과' :
                                     (l.utilization_rate || 0) > 90 ? '주의' : '정상'}
                                  </Badge>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      ) : (
                        <div className="text-center py-12 text-gray-500">
                          <AlertTriangle size={64} className="mx-auto mb-4 text-gray-300" />
                          <p className="text-lg">한도 정보가 없습니다</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* 수익성 탭 */}
                  {activeTab === 'pricing' && (
                    <div className="space-y-6">
                      {selectedApp.pricing ? (
                        <div className="grid grid-cols-2 gap-6">
                          {/* 금리 구조 */}
                          <div>
                            <h4 className="text-sm font-semibold text-gray-700 mb-3">금리 구조</h4>
                            <div className="space-y-2">
                              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                                <span className="text-sm text-gray-600">기준금리</span>
                                <span className="text-sm font-mono">{formatPercent((selectedApp.pricing.base_rate || 0) * 100)}</span>
                              </div>
                              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                                <span className="text-sm text-gray-600">FTP 스프레드</span>
                                <span className="text-sm font-mono">+{formatPercent((selectedApp.pricing.ftp_spread || 0) * 100)}</span>
                              </div>
                              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                                <span className="text-sm text-gray-600">신용 스프레드</span>
                                <span className="text-sm font-mono">+{formatPercent((selectedApp.pricing.credit_spread || 0) * 100)}</span>
                              </div>
                              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                                <span className="text-sm text-gray-600">자본비용 스프레드</span>
                                <span className="text-sm font-mono">+{formatPercent((selectedApp.pricing.capital_spread || 0) * 100)}</span>
                              </div>
                              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                                <span className="text-sm text-gray-600">전략 조정</span>
                                <span className="text-sm font-mono">{(selectedApp.pricing.strategy_adj || 0) >= 0 ? '+' : ''}{formatPercent((selectedApp.pricing.strategy_adj || 0) * 100)}</span>
                              </div>
                              <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg border border-blue-200">
                                <span className="text-sm font-medium text-blue-800">최종금리</span>
                                <span className="text-xl font-bold text-blue-700">{formatPercent((selectedApp.pricing.final_rate || 0) * 100)}</span>
                              </div>
                            </div>
                          </div>

                          {/* 수익성 지표 */}
                          <div>
                            <h4 className="text-sm font-semibold text-gray-700 mb-3">수익성 지표</h4>
                            <div className="space-y-2">
                              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                                <span className="text-sm text-gray-600">RWA</span>
                                <span className="text-sm font-mono">{formatAmount(selectedApp.risk_parameter?.rwa || 0, 'billion')}</span>
                              </div>
                              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                                <span className="text-sm text-gray-600">예상손실 (EL)</span>
                                <span className="text-sm font-mono">{formatAmount(selectedApp.risk_parameter?.expected_loss || 0, 'million')}</span>
                              </div>
                              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                                <span className="text-sm text-gray-600">경제자본 (EC)</span>
                                <span className="text-sm font-mono">{formatAmount(selectedApp.risk_parameter?.economic_capital || 0, 'million')}</span>
                              </div>
                              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                                <span className="text-sm text-gray-600">Hurdle Rate</span>
                                <span className="text-sm font-mono">{formatPercent((selectedApp.pricing.hurdle_rate || 0.12) * 100)}</span>
                              </div>
                              <div className={`flex justify-between items-center p-3 rounded-lg border ${
                                selectedApp.pricing.raroc_status === 'ABOVE_HURDLE' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
                              }`}>
                                <span className="text-sm font-medium">RAROC</span>
                                <span className={`text-xl font-bold ${
                                  selectedApp.pricing.raroc_status === 'ABOVE_HURDLE' ? 'text-green-700' : 'text-red-700'
                                }`}>
                                  {formatPercent((selectedApp.pricing.expected_raroc || 0) * 100)}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="text-center py-12 text-gray-500">
                          <Calculator size={64} className="mx-auto mb-4 text-gray-300" />
                          <p className="text-lg">가격결정 정보가 없습니다</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* 체크리스트 탭 */}
                  {activeTab === 'checklist' && (
                    <div className="grid grid-cols-2 gap-6">
                      {selectedApp.checklist?.map((category: any, idx: number) => (
                        <div key={idx}>
                          <h4 className="text-sm font-semibold text-gray-700 mb-3">{category.category}</h4>
                          <div className="bg-gray-50 rounded-lg divide-y divide-gray-200">
                            {category.items.map((item: any, itemIdx: number) => (
                              <div key={itemIdx} className="flex items-center justify-between p-3">
                                <div className="flex items-center">
                                  <ChecklistIcon status={item.status} />
                                  <span className="ml-2 text-sm">{item.item}</span>
                                  {item.value && (
                                    <span className="ml-2 text-sm text-gray-500">({item.value})</span>
                                  )}
                                </div>
                                {item.note && (
                                  <span className={`text-xs px-2 py-0.5 rounded ${
                                    item.status === 'danger' ? 'bg-red-100 text-red-700' :
                                    item.status === 'warning' ? 'bg-yellow-100 text-yellow-700' :
                                    'bg-gray-100 text-gray-600'
                                  }`}>
                                    {item.note}
                                  </span>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* 승인 이력 */}
                  {selectedApp.approval_history?.length > 0 && (
                    <div className="border-t pt-6">
                      <h4 className="text-sm font-semibold text-gray-700 mb-3">승인 이력</h4>
                      <div className="bg-gray-50 rounded-lg divide-y">
                        {selectedApp.approval_history.map((h: any, idx: number) => (
                          <div key={idx} className="p-3 flex items-center justify-between">
                            <div>
                              <p className="text-sm font-medium">
                                {h.approver} ({h.level})
                              </p>
                              <p className="text-xs text-gray-500">{h.decided_at}</p>
                              {h.comments && <p className="text-xs text-gray-600 mt-1">{h.comments}</p>}
                            </div>
                            <Badge variant={
                              h.decision === 'APPROVE' ? 'success' :
                              h.decision === 'CONDITIONAL' ? 'warning' : 'danger'
                            }>
                              {h.decision === 'APPROVE' ? '승인' :
                               h.decision === 'CONDITIONAL' ? '조건부' : '반려'}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* 모달 하단 액션 버튼 */}
            {selectedApp.application?.status !== 'APPROVED' && selectedApp.application?.status !== 'REJECTED' && (
              <div className="flex justify-end space-x-3 p-4 border-t bg-gray-50">
                <button
                  className="flex items-center px-4 py-2 text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                  onClick={closeDetailModal}
                >
                  닫기
                </button>
                <button
                  className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  onClick={openWhatIfModal}
                >
                  <Calculator size={18} className="mr-2" />
                  What-if 분석
                </button>
                <button
                  className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                  onClick={openApprovalModal}
                >
                  <CheckCircle size={18} className="mr-2" />
                  심사결정
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* What-if 분석 모달 */}
      {showWhatIfModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60]">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="text-lg font-bold text-gray-900">What-if 분석</h3>
              <button onClick={() => setShowWhatIfModal(false)} className="p-1 hover:bg-gray-100 rounded-lg">
                <X size={20} />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* 시뮬레이션 조건 */}
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-3">
                  시뮬레이션 조건
                  <span className="text-xs text-blue-500 font-normal ml-2">(입력 시 자동 계산)</span>
                </h4>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">금액 (원)</label>
                    <input
                      type="text"
                      value={formatInputAmount(whatIfParams.amount)}
                      onChange={(e) => handleWhatIfParamChange({
                        ...whatIfParams,
                        amount: parseFormattedNumber(e.target.value)
                      })}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-right font-mono"
                    />
                    <p className="text-xs text-gray-500 mt-1 text-right">{formatAmount(whatIfParams.amount, 'billion')}</p>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">금리 (%)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={whatIfParams.rate}
                      onChange={(e) => handleWhatIfParamChange({
                        ...whatIfParams,
                        rate: Number(e.target.value)
                      })}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-right font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">기간 (개월)</label>
                    <input
                      type="number"
                      value={whatIfParams.tenor}
                      onChange={(e) => handleWhatIfParamChange({
                        ...whatIfParams,
                        tenor: Number(e.target.value)
                      })}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-right font-mono"
                    />
                  </div>
                </div>
                {whatIfLoading && (
                  <div className="mt-2 flex items-center text-sm text-blue-600">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                    계산 중...
                  </div>
                )}
              </div>

              {/* 시뮬레이션 결과 */}
              {whatIfResult && (
                <div className="space-y-4">
                  {/* 핵심 지표 */}
                  <div className="grid grid-cols-4 gap-4">
                    <div className="p-4 bg-blue-50 rounded-lg text-center">
                      <p className="text-sm text-gray-600">적용 금리</p>
                      <p className="text-2xl font-bold text-blue-700">
                        {formatPercent((whatIfResult.input?.rate || 0) * 100)}
                      </p>
                    </div>
                    <div className={`p-4 rounded-lg text-center ${
                      whatIfResult.raroc_status === 'ABOVE_HURDLE' ? 'bg-green-50' : 'bg-red-50'
                    }`}>
                      <p className="text-sm text-gray-600">예상 RAROC</p>
                      <p className={`text-2xl font-bold ${
                        whatIfResult.raroc_status === 'ABOVE_HURDLE' ? 'text-green-700' : 'text-red-700'
                      }`}>
                        {formatPercent((whatIfResult.raroc?.raroc || 0) * 100)}
                      </p>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg text-center">
                      <p className="text-sm text-gray-600">Hurdle Rate</p>
                      <p className="text-2xl font-bold text-gray-700">
                        {formatPercent(whatIfResult.hurdle_rate * 100)}
                      </p>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg text-center">
                      <p className="text-sm text-gray-600">손익분기 금리</p>
                      <p className="text-2xl font-bold text-orange-600">
                        {whatIfResult.breakeven_rate ? formatPercent(whatIfResult.breakeven_rate * 100) : '-'}
                      </p>
                    </div>
                  </div>

                  {/* RAROC 상태 */}
                  <div className={`p-4 rounded-lg ${
                    whatIfResult.raroc_status === 'ABOVE_HURDLE'
                      ? 'bg-green-50 border border-green-200'
                      : 'bg-red-50 border border-red-200'
                  }`}>
                    <div className="flex items-center">
                      {whatIfResult.raroc_status === 'ABOVE_HURDLE' ? (
                        <>
                          <TrendingUp className="text-green-600 mr-2" size={20} />
                          <span className="text-green-800 font-medium">Hurdle Rate 충족 - 승인 가능</span>
                        </>
                      ) : (
                        <>
                          <TrendingDown className="text-red-600 mr-2" size={20} />
                          <span className="text-red-800 font-medium">
                            Hurdle Rate 미달 - 금리 {whatIfResult.breakeven_rate ? formatPercent(whatIfResult.breakeven_rate * 100) : '-'} 이상 필요
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* 익스포저 영향 */}
                  <div>
                    <h5 className="text-sm font-medium text-gray-700 mb-2">익스포저 영향</h5>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="p-3 bg-gray-50 rounded-lg text-center">
                        <p className="text-xs text-gray-500">기존 익스포저</p>
                        <p className="text-lg font-bold">{formatAmount(whatIfResult.exposure_impact?.existing_exposure || 0, 'billion')}</p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-lg text-center">
                        <p className="text-xs text-gray-500">신규 익스포저</p>
                        <p className="text-lg font-bold text-blue-600">{formatAmount(whatIfResult.exposure_impact?.new_exposure || 0, 'billion')}</p>
                      </div>
                      <div className="p-3 bg-blue-50 rounded-lg text-center">
                        <p className="text-xs text-gray-500">총 익스포저</p>
                        <p className="text-lg font-bold text-blue-700">{formatAmount(whatIfResult.exposure_impact?.total_exposure || 0, 'billion')}</p>
                      </div>
                    </div>
                  </div>

                  {/* 금리 시나리오 */}
                  {whatIfResult.rate_scenarios && (
                    <div>
                      <h5 className="text-sm font-medium text-gray-700 mb-2">금리별 RAROC 시나리오</h5>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b bg-gray-50">
                              <th className="px-3 py-2 text-left">금리</th>
                              <th className="px-3 py-2 text-right">RAROC</th>
                              <th className="px-3 py-2 text-right">순이익</th>
                              <th className="px-3 py-2 text-center">상태</th>
                            </tr>
                          </thead>
                          <tbody>
                            {whatIfResult.rate_scenarios.map((scenario: any, idx: number) => (
                              <tr key={idx} className={`border-b hover:bg-gray-50 ${
                                Math.abs(scenario.rate - whatIfParams.rate / 100) < 0.0001 ? 'bg-blue-50' : ''
                              }`}>
                                <td className="px-3 py-2 font-mono">{formatPercent(scenario.rate * 100)}</td>
                                <td className={`px-3 py-2 text-right font-mono ${
                                  scenario.meets_hurdle ? 'text-green-600' : 'text-red-600'
                                }`}>
                                  {formatPercent(scenario.raroc * 100)}
                                </td>
                                <td className="px-3 py-2 text-right font-mono">
                                  {formatAmount(scenario.net_income || 0, 'million')}
                                </td>
                                <td className="px-3 py-2 text-center">
                                  <Badge variant={scenario.meets_hurdle ? 'success' : 'danger'}>
                                    {scenario.meets_hurdle ? '충족' : '미달'}
                                  </Badge>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 p-4 border-t bg-gray-50">
              <button
                onClick={() => setShowWhatIfModal(false)}
                className="px-4 py-2 text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 승인/반려 모달 */}
      {showApprovalModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60]">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg">
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="text-lg font-bold text-gray-900">여신 심사 결정</h3>
              <button onClick={() => setShowApprovalModal(false)} className="p-1 hover:bg-gray-100 rounded-lg">
                <X size={20} />
              </button>
            </div>

            <div className="p-6 space-y-4">
              {/* 신청 요약 */}
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm text-gray-600">
                      신청번호: <span className="font-mono font-medium">{selectedApp?.application?.application_id}</span>
                    </p>
                    <p className="text-lg font-bold text-gray-900">{selectedApp?.customer?.customer_name}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-500">신청금액</p>
                    <p className="text-xl font-bold text-blue-600">
                      {formatAmount(selectedApp?.application?.requested_amount || 0, 'billion')}
                    </p>
                  </div>
                </div>
                <div className="mt-2 pt-2 border-t border-gray-200">
                  <p className="text-sm text-gray-600">
                    승인 필요 권한: <span className="font-medium text-orange-600">{selectedApp?.required_authority?.name}</span>
                  </p>
                </div>
              </div>

              {/* 결정 선택 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">심사 결정</label>
                <div className="flex gap-2">
                  {[
                    { value: 'APPROVE', label: '승인', color: 'green' },
                    { value: 'CONDITIONAL', label: '조건부 승인', color: 'yellow' },
                    { value: 'REJECT', label: '반려', color: 'red' }
                  ].map(option => (
                    <button
                      key={option.value}
                      onClick={() => setApprovalData({ ...approvalData, decision: option.value })}
                      className={`flex-1 px-3 py-2 rounded-lg border-2 transition-all ${
                        approvalData.decision === option.value
                          ? option.color === 'green' ? 'border-green-500 bg-green-50 text-green-700'
                          : option.color === 'yellow' ? 'border-yellow-500 bg-yellow-50 text-yellow-700'
                          : 'border-red-500 bg-red-50 text-red-700'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 승인 조건 */}
              {approvalData.decision !== 'REJECT' && (
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">승인금액</label>
                    <input
                      type="text"
                      value={formatInputAmount(approvalData.approved_amount)}
                      onChange={(e) => setApprovalData({
                        ...approvalData,
                        approved_amount: parseFormattedNumber(e.target.value)
                      })}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-right font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">승인금리 (%)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={approvalData.approved_rate}
                      onChange={(e) => setApprovalData({
                        ...approvalData,
                        approved_rate: Number(e.target.value)
                      })}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-right font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">승인기간 (개월)</label>
                    <input
                      type="number"
                      value={approvalData.approved_tenor}
                      onChange={(e) => setApprovalData({
                        ...approvalData,
                        approved_tenor: Number(e.target.value)
                      })}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-right font-mono"
                    />
                  </div>
                </div>
              )}

              {/* 조건부 승인 시 조건 입력 */}
              {approvalData.decision === 'CONDITIONAL' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">승인 조건</label>
                  <textarea
                    value={approvalData.conditions}
                    onChange={(e) => setApprovalData({ ...approvalData, conditions: e.target.value })}
                    placeholder="승인 조건을 입력하세요..."
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    rows={2}
                  />
                </div>
              )}

              {/* 코멘트 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">심사 의견</label>
                <textarea
                  value={approvalData.comments}
                  onChange={(e) => setApprovalData({ ...approvalData, comments: e.target.value })}
                  placeholder="심사 의견을 입력하세요..."
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 p-4 border-t bg-gray-50">
              <button
                onClick={() => setShowApprovalModal(false)}
                className="px-4 py-2 text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                취소
              </button>
              <button
                onClick={handleApproval}
                disabled={approvalLoading}
                className={`px-4 py-2 text-white rounded-lg disabled:opacity-50 ${
                  approvalData.decision === 'APPROVE' ? 'bg-green-600 hover:bg-green-700'
                  : approvalData.decision === 'CONDITIONAL' ? 'bg-yellow-600 hover:bg-yellow-700'
                  : 'bg-red-600 hover:bg-red-700'
                }`}
              >
                {approvalLoading ? '처리 중...' : (
                  approvalData.decision === 'APPROVE' ? '승인 처리'
                  : approvalData.decision === 'CONDITIONAL' ? '조건부 승인'
                  : '반려 처리'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
