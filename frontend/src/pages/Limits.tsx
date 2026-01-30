import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  Search,
  Filter,
  Gauge,
  Building2,
  ChevronDown
} from 'lucide-react';
import { Card, StatCard, Table, Badge, CellFormatters, TrendChart, COLORS } from '../components';
import { limitsApi } from '../utils/api';
import { formatAmount, formatPercent, formatInputAmount, parseFormattedNumber } from '../utils/format';

export default function Limits() {
  const [loading, setLoading] = useState(true);
  const [limits, setLimits] = useState<any[]>([]);
  const [industryLimits, setIndustryLimits] = useState<any[]>([]);
  const [filter, setFilter] = useState('ALL');

  // 고객 목록 (드롭다운용)
  const [customers, setCustomers] = useState<any[]>([]);

  // 한도 체크 시뮬레이션
  const [checkInput, setCheckInput] = useState({
    customer_id: '',
    industry_code: '',
    amount: 10000000000
  });
  const [checkResult, setCheckResult] = useState<any>(null);
  const [checkLoading, setCheckLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [limitsRes, indRes, custRes] = await Promise.all([
        limitsApi.getAll(),
        limitsApi.getIndustry(),
        limitsApi.getCustomers()
      ]);
      setLimits(limitsRes.data || []);
      setIndustryLimits(indRes.data || []);
      setCustomers(custRes.data || []);
    } catch (error) {
      console.error('Limits data load error:', error);
    } finally {
      setLoading(false);
    }
  };

  // 고객 선택 시 업종코드 자동 설정 및 즉시 체크
  const handleCustomerChange = (customerId: string) => {
    const customer = customers.find(c => c.customer_id === customerId);
    const newInput = {
      ...checkInput,
      customer_id: customerId,
      industry_code: customer?.industry_code || ''
    };
    setCheckResult(null);
    handleCheckInputChange(newInput, true); // 고객 변경 시 즉시 실행
  };

  const [debounceTimer, setDebounceTimer] = useState<NodeJS.Timeout | null>(null);

  const runLimitCheck = async (params?: typeof checkInput) => {
    const currentParams = params || checkInput;
    if (!currentParams.customer_id) return;
    setCheckLoading(true);
    try {
      const response = await limitsApi.check({
        customer_id: currentParams.customer_id,
        amount: currentParams.amount,
        industry_code: currentParams.industry_code || undefined
      });
      setCheckResult(response.data);
    } catch (error) {
      console.error('Limit check error:', error);
    } finally {
      setCheckLoading(false);
    }
  };

  // 디바운스된 한도 체크
  const handleCheckInputChange = (newInput: typeof checkInput, immediate: boolean = false) => {
    setCheckInput(newInput);

    if (!newInput.customer_id) return;

    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }

    if (immediate) {
      runLimitCheck(newInput);
    } else {
      const timer = setTimeout(() => {
        runLimitCheck(newInput);
      }, 300);
      setDebounceTimer(timer);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // 상태별 카운트
  const statusCounts = limits.reduce((acc: any, limit) => {
    acc[limit.status] = (acc[limit.status] || 0) + 1;
    return acc;
  }, { ALL: limits.length, NORMAL: 0, WARNING: 0, CRITICAL: 0, BREACH: 0 });

  const filteredLimits = limits.filter(l => {
    if (filter === 'ALL') return true;
    return l.status === filter;
  });

  const columns = [
    {
      key: 'limit_name',
      header: '한도명',
      render: (value: string, row: any) => (
        <div>
          <p className="font-medium text-gray-900">{value}</p>
          <p className="text-xs text-gray-500">{row.limit_type}</p>
        </div>
      )
    },
    {
      key: 'target_name',
      header: '대상',
      render: (value: string, row: any) => (
        <span className="text-sm">{value || row.target_id}</span>
      )
    },
    {
      key: 'limit_amount',
      header: '한도금액',
      align: 'right' as const,
      render: (value: number) => CellFormatters.amountBillion(value)
    },
    {
      key: 'current_usage',
      header: '사용금액',
      align: 'right' as const,
      render: (value: number) => CellFormatters.amountBillion(value)
    },
    {
      key: 'utilization_rate',
      header: '사용률',
      align: 'right' as const,
      render: (value: number, row: any) => {
        const color = value >= 100 ? 'text-red-600' :
                      value >= row.critical_threshold ? 'text-red-500' :
                      value >= row.warning_threshold ? 'text-yellow-600' : 'text-green-600';
        return <span className={`font-mono font-semibold ${color}`}>{formatPercent(value)}</span>;
      }
    },
    {
      key: 'status',
      header: '상태',
      align: 'center' as const,
      render: (value: string) => {
        const variants: Record<string, 'success' | 'warning' | 'danger'> = {
          NORMAL: 'success',
          WARNING: 'warning',
          CRITICAL: 'danger',
          BREACH: 'danger'
        };
        return <Badge variant={variants[value] || 'info'}>{value}</Badge>;
      }
    }
  ];

  return (
    <div className="space-y-6">
      {/* 페이지 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">한도관리</h1>
          <p className="text-sm text-gray-500 mt-1">규제 및 내부 한도 사용현황 모니터링</p>
        </div>
      </div>

      {/* 상태별 요약 */}
      <div className="grid grid-cols-5 gap-4">
        {[
          { key: 'ALL', label: '전체', icon: <Gauge size={20} />, color: 'blue' },
          { key: 'NORMAL', label: '정상', icon: <CheckCircle size={20} />, color: 'green' },
          { key: 'WARNING', label: '주의', icon: <AlertTriangle size={20} />, color: 'yellow' },
          { key: 'CRITICAL', label: '경계', icon: <AlertTriangle size={20} />, color: 'orange' },
          { key: 'BREACH', label: '위반', icon: <XCircle size={20} />, color: 'red' }
        ].map(item => (
          <button
            key={item.key}
            onClick={() => setFilter(item.key)}
            className={`p-4 rounded-lg border transition-all ${
              filter === item.key
                ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                : 'border-gray-200 bg-white hover:border-gray-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className={`p-2 rounded-lg ${
                item.color === 'green' ? 'bg-green-100 text-green-600' :
                item.color === 'yellow' ? 'bg-yellow-100 text-yellow-600' :
                item.color === 'orange' ? 'bg-orange-100 text-orange-600' :
                item.color === 'red' ? 'bg-red-100 text-red-600' :
                'bg-blue-100 text-blue-600'
              }`}>
                {item.icon}
              </div>
              <span className="text-2xl font-bold text-gray-900">
                {statusCounts[item.key] || 0}
              </span>
            </div>
            <p className="text-sm text-gray-600 mt-2 text-left">{item.label}</p>
          </button>
        ))}
      </div>

      {/* 한도 목록 */}
      <Card title="한도 현황" noPadding>
        <Table
          columns={columns}
          data={filteredLimits}
          loading={loading}
        />
      </Card>

      {/* 업종별 한도 */}
      <Card title="업종별 한도 현황">
        <div className="space-y-4">
          {industryLimits.slice(0, 10).map((ind: any, index: number) => {
            const utilization = ind.current / ind.limit * 100;
            return (
              <div key={index} className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center">
                    <Building2 size={16} className="text-gray-400 mr-2" />
                    <span className="font-medium text-gray-900">{ind.industry_name}</span>
                    <span className={`ml-2 px-2 py-0.5 rounded text-xs font-medium ${
                      ind.strategy_code === 'EXPAND' ? 'bg-green-100 text-green-800' :
                      ind.strategy_code === 'SELECTIVE' ? 'bg-blue-100 text-blue-800' :
                      ind.strategy_code === 'MAINTAIN' ? 'bg-gray-100 text-gray-800' :
                      ind.strategy_code === 'REDUCE' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {ind.strategy_code}
                    </span>
                  </div>
                  <span className={`text-sm font-semibold ${
                    utilization >= 100 ? 'text-red-600' :
                    utilization >= 90 ? 'text-yellow-600' : 'text-green-600'
                  }`}>
                    {formatPercent(utilization)}
                  </span>
                </div>
                <div className="relative h-3 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`absolute left-0 top-0 h-full rounded-full transition-all duration-500 ${
                      utilization >= 100 ? 'bg-red-500' :
                      utilization >= 90 ? 'bg-yellow-500' : 'bg-green-500'
                    }`}
                    style={{ width: `${Math.min(utilization, 100)}%` }}
                  />
                  <div
                    className="absolute top-0 w-0.5 h-full bg-yellow-600"
                    style={{ left: '80%' }}
                    title="경고선 80%"
                  />
                  <div
                    className="absolute top-0 w-0.5 h-full bg-red-600"
                    style={{ left: '90%' }}
                    title="위험선 90%"
                  />
                </div>
                <div className="flex justify-between mt-2 text-xs text-gray-500">
                  <span>사용: {formatAmount(ind.current, 'billion')}</span>
                  <span>한도: {formatAmount(ind.limit, 'billion')}</span>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* 한도 체크 시뮬레이션 */}
      <Card title="한도 사전 체크" headerAction={
        checkLoading ? (
          <div className="flex items-center text-sm text-blue-600">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
            체크 중...
          </div>
        ) : null
      }>
        <div className="grid grid-cols-2 gap-6">
          {/* 입력 */}
          <div className="space-y-4">
            <h4 className="text-sm font-medium text-gray-700">체크 조건 <span className="text-xs text-blue-500 font-normal">(입력 시 자동 체크)</span></h4>
            <div>
              <label className="block text-sm text-gray-600 mb-1">고객 선택</label>
              <div className="relative">
                <select
                  value={checkInput.customer_id}
                  onChange={(e) => handleCustomerChange(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none bg-white"
                >
                  <option value="">고객을 선택하세요</option>
                  {customers.map((cust) => (
                    <option key={cust.customer_id} value={cust.customer_id}>
                      {cust.customer_name} ({cust.customer_id}) - {cust.industry_name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 pointer-events-none" size={16} />
              </div>
            </div>

            {/* 선택된 고객 정보 표시 */}
            {checkInput.customer_id && (
              <div className="p-3 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-800">
                  <span className="font-medium">업종:</span> {customers.find(c => c.customer_id === checkInput.customer_id)?.industry_name || '-'}
                </p>
                <p className="text-sm text-blue-800">
                  <span className="font-medium">현재 익스포저:</span> {formatAmount(customers.find(c => c.customer_id === checkInput.customer_id)?.current_exposure || 0, 'billion')}
                </p>
              </div>
            )}

            <div>
              <label className="block text-sm text-gray-600 mb-1">신청 금액</label>
              <input
                type="text"
                value={formatInputAmount(checkInput.amount)}
                onChange={(e) => {
                  const newAmount = parseFormattedNumber(e.target.value);
                  handleCheckInputChange({...checkInput, amount: newAmount});
                }}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-right font-mono"
              />
              <p className="text-xs text-gray-500 mt-1 text-right">{formatAmount(checkInput.amount, 'billion')}</p>
            </div>
          </div>

          {/* 결과 */}
          <div className="space-y-4">
            <h4 className="text-sm font-medium text-gray-700">체크 결과</h4>
            {checkResult ? (
              <div className="space-y-3">
                <div className={`p-4 rounded-lg ${
                  checkResult.can_proceed ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
                }`}>
                  <div className="flex items-center">
                    {checkResult.can_proceed ? (
                      <CheckCircle className="text-green-600 mr-2" size={24} />
                    ) : (
                      <XCircle className="text-red-600 mr-2" size={24} />
                    )}
                    <span className={`font-semibold ${checkResult.can_proceed ? 'text-green-800' : 'text-red-800'}`}>
                      {checkResult.can_proceed ? '모든 한도 통과' : '한도 초과 발생'}
                    </span>
                  </div>
                </div>

                {checkResult.checks?.map((check: any, index: number) => (
                  <div key={index} className={`p-3 rounded-lg ${
                    check.is_sufficient ? 'bg-gray-50' : 'bg-red-50'
                  }`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        {check.is_sufficient ? (
                          <CheckCircle className="text-green-500 mr-2" size={16} />
                        ) : (
                          <XCircle className="text-red-500 mr-2" size={16} />
                        )}
                        <span className="text-sm font-medium">{check.limit_type}</span>
                      </div>
                      <Badge variant={check.is_sufficient ? 'success' : 'danger'}>
                        {check.status}
                      </Badge>
                    </div>
                    <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-gray-500">한도:</span>
                        <span className="ml-1 font-mono">{formatAmount(check.limit_amount, 'billion')}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">현재:</span>
                        <span className="ml-1 font-mono">{formatAmount(check.current_exposure, 'billion')}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">신청 후:</span>
                        <span className={`ml-1 font-mono ${!check.is_sufficient ? 'text-red-600 font-semibold' : ''}`}>
                          {formatAmount(check.after_exposure, 'billion')}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500">사용률:</span>
                        <span className={`ml-1 font-mono ${check.utilization_after >= 100 ? 'text-red-600 font-semibold' : ''}`}>
                          {formatPercent(check.utilization_after)}
                        </span>
                      </div>
                    </div>
                    <div className="mt-2 text-xs">
                      <span className="text-gray-500">잔여 한도:</span>
                      <span className={`ml-1 font-semibold ${check.available < 0 ? 'text-red-600' : 'text-green-600'}`}>
                        {formatAmount(check.available, 'billion')}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center h-40 text-gray-400">
                고객을 선택하고 체크를 실행하세요
              </div>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
