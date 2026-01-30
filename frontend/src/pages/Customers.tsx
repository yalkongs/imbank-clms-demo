import React, { useEffect, useState, useCallback } from 'react';
import {
  Users,
  Building2,
  Search,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  Filter,
  CreditCard,
  TrendingUp,
  AlertTriangle,
  X
} from 'lucide-react';
import { Card, StatCard, Badge, DonutChart, COLORS } from '../components';
import { customersApi } from '../utils/api';
import { formatAmount, formatPercent, formatDate, getGradeColorClass, getStatusColorClass } from '../utils/format';

interface Customer {
  customer_id: string;
  customer_name: string;
  business_number: string;
  industry_code: string;
  industry_name: string;
  size_category: string;
  establishment_date: string;
  address: string;
  credit_rating: string;
  probability_default: number;
  total_exposure: number;
  facility_count: number;
}

interface CustomerDetail {
  basic_info: {
    customer_id: string;
    customer_name: string;
    business_number: string;
    industry_code: string;
    industry_name: string;
    size_category: string;
    establishment_date: string;
    employees: number;
    address: string;
  };
  financials: {
    total_assets: number;
    annual_revenue: number;
  };
  credit_ratings: Array<{
    rating: string;
    pd: number;
    lgd: number;
    rating_date: string;
    model_type: string;
    rating_reason: string;
  }>;
  facilities: Array<{
    facility_id: string;
    facility_type: string;
    product_name: string;
    limit_amount: number;
    outstanding_amount: number;
    available_amount: number;
    interest_rate: number;
    start_date: string;
    maturity_date: string;
    status: string;
  }>;
  facility_summary: {
    total_count: number;
    active_count: number;
    total_limit: number;
    total_outstanding: number;
    total_available: number;
  };
  risk_metrics: {
    total_rwa: number;
    total_ead: number;
    total_el: number;
  };
  industry_limit: {
    limit_name: string;
    limit_amount: number;
    exposure_amount: number;
    utilization_rate: number;
  } | null;
}

export default function Customers() {
  const [loading, setLoading] = useState(true);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [industries, setIndustries] = useState<any[]>([]);
  const [pagination, setPagination] = useState({
    page: 1,
    page_size: 20,
    total_count: 0,
    total_pages: 0
  });

  // Filters
  const [search, setSearch] = useState('');
  const [industryFilter, setIndustryFilter] = useState('');
  const [sizeFilter, setSizeFilter] = useState('');
  const [sortBy, setSortBy] = useState('customer_name');
  const [sortOrder, setSortOrder] = useState('asc');

  // Detail view
  const [selectedCustomer, setSelectedCustomer] = useState<string | null>(null);
  const [customerDetail, setCustomerDetail] = useState<CustomerDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const [summaryRes, industriesRes] = await Promise.all([
        customersApi.getSummary(),
        customersApi.getIndustries()
      ]);
      setSummary(summaryRes.data);
      setIndustries(industriesRes.data);
      await loadCustomers();
    } catch (error) {
      console.error('Initial data load error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadCustomers = useCallback(async (page = 1) => {
    try {
      const response = await customersApi.getAll({
        page,
        page_size: pagination.page_size,
        search: search || undefined,
        industry_code: industryFilter || undefined,
        size_category: sizeFilter || undefined,
        sort_by: sortBy,
        sort_order: sortOrder
      });
      setCustomers(response.data.data);
      setPagination(response.data.pagination);
    } catch (error) {
      console.error('Customers load error:', error);
    }
  }, [search, industryFilter, sizeFilter, sortBy, sortOrder, pagination.page_size]);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadCustomers(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search, industryFilter, sizeFilter, sortBy, sortOrder]);

  const loadCustomerDetail = async (customerId: string) => {
    setSelectedCustomer(customerId);
    setDetailLoading(true);
    try {
      const response = await customersApi.getById(customerId);
      setCustomerDetail(response.data);
    } catch (error) {
      console.error('Customer detail load error:', error);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
  };

  const clearFilters = () => {
    setSearch('');
    setIndustryFilter('');
    setSizeFilter('');
    setSortBy('customer_name');
    setSortOrder('asc');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // Size distribution for chart
  const sizeDistribution = summary?.by_size?.map((s: any) => ({
    name: s.size_category === 'LARGE' ? '대기업' :
          s.size_category === 'MEDIUM' ? '중견기업' :
          s.size_category === 'SMALL' ? '중소기업' :
          s.size_category === 'SOHO' ? '소호' : s.size_category,
    value: s.count,
    color: s.size_category === 'LARGE' ? COLORS.primary :
           s.size_category === 'MEDIUM' ? COLORS.success :
           s.size_category === 'SMALL' ? COLORS.warning : COLORS.secondary
  })) || [];

  // Rating distribution for chart
  const ratingDistribution = summary?.by_rating?.map((r: any, idx: number) => ({
    name: r.rating,
    value: r.count,
    color: ['#1e40af', '#2563eb', '#3b82f6', '#60a5fa', '#93c5fd', '#f59e0b', '#f97316', '#ef4444'][idx % 8]
  })) || [];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">고객 관리</h1>
          <p className="text-sm text-gray-500 mt-1">등록 기업 목록 및 상세 정보 조회</p>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="총 고객수"
          value={summary?.total_customers?.toLocaleString() || '0'}
          subtitle="등록 기업"
          icon={<Users size={24} />}
          color="blue"
        />
        <StatCard
          title="총 여신잔액"
          value={formatAmount(summary?.total_exposure || 0, 'billion')}
          subtitle="Active 여신"
          icon={<CreditCard size={24} />}
          color="green"
        />
        <StatCard
          title="업종 수"
          value={industries.length.toString()}
          subtitle="등록 업종"
          icon={<Building2 size={24} />}
          color="purple"
        />
        <StatCard
          title="등급별 분포"
          value={`${summary?.by_rating?.length || 0}개 등급`}
          subtitle="신용등급 범위"
          icon={<TrendingUp size={24} />}
          color="yellow"
        />
      </div>

      {/* Distribution Charts */}
      <div className="grid grid-cols-2 gap-6">
        <Card title="규모별 분포">
          <DonutChart
            data={sizeDistribution}
            height={200}
            innerRadius={40}
            outerRadius={70}
          />
        </Card>
        <Card title="신용등급 분포">
          <DonutChart
            data={ratingDistribution}
            height={200}
            innerRadius={40}
            outerRadius={70}
          />
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <div className="flex flex-wrap items-center gap-4">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="기업명, ID, 사업자번호 검색..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Industry Filter */}
          <div className="flex items-center gap-2">
            <Filter size={16} className="text-gray-500" />
            <select
              value={industryFilter}
              onChange={(e) => setIndustryFilter(e.target.value)}
              className="px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">전체 업종</option>
              {industries.map((ind) => (
                <option key={ind.industry_code} value={ind.industry_code}>
                  {ind.industry_name} ({ind.customer_count})
                </option>
              ))}
            </select>
          </div>

          {/* Size Filter */}
          <select
            value={sizeFilter}
            onChange={(e) => setSizeFilter(e.target.value)}
            className="px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">전체 규모</option>
            <option value="LARGE">대기업</option>
            <option value="MEDIUM">중견기업</option>
            <option value="SMALL">중소기업</option>
          </select>

          {/* Clear Filters */}
          {(search || industryFilter || sizeFilter) && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-1 px-3 py-2 text-sm text-gray-600 hover:text-gray-900"
            >
              <X size={16} />
              필터 초기화
            </button>
          )}
        </div>
      </Card>

      {/* Customer List */}
      <Card title={`고객 목록 (${pagination.total_count.toLocaleString()}건)`} noPadding>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th
                  className="px-4 py-3 text-left font-semibold text-gray-700 bg-gray-50 cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('customer_id')}
                >
                  <div className="flex items-center gap-1">
                    고객ID
                    <ArrowUpDown size={14} className={sortBy === 'customer_id' ? 'text-blue-600' : 'text-gray-400'} />
                  </div>
                </th>
                <th
                  className="px-4 py-3 text-left font-semibold text-gray-700 bg-gray-50 cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('customer_name')}
                >
                  <div className="flex items-center gap-1">
                    기업명
                    <ArrowUpDown size={14} className={sortBy === 'customer_name' ? 'text-blue-600' : 'text-gray-400'} />
                  </div>
                </th>
                <th
                  className="px-4 py-3 text-left font-semibold text-gray-700 bg-gray-50 cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('industry_name')}
                >
                  <div className="flex items-center gap-1">
                    업종
                    <ArrowUpDown size={14} className={sortBy === 'industry_name' ? 'text-blue-600' : 'text-gray-400'} />
                  </div>
                </th>
                <th className="px-4 py-3 text-center font-semibold text-gray-700 bg-gray-50">규모</th>
                <th
                  className="px-4 py-3 text-center font-semibold text-gray-700 bg-gray-50 cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('credit_rating')}
                >
                  <div className="flex items-center justify-center gap-1">
                    신용등급
                    <ArrowUpDown size={14} className={sortBy === 'credit_rating' ? 'text-blue-600' : 'text-gray-400'} />
                  </div>
                </th>
                <th
                  className="px-4 py-3 text-right font-semibold text-gray-700 bg-gray-50 cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('total_exposure')}
                >
                  <div className="flex items-center justify-end gap-1">
                    여신잔액
                    <ArrowUpDown size={14} className={sortBy === 'total_exposure' ? 'text-blue-600' : 'text-gray-400'} />
                  </div>
                </th>
                <th className="px-4 py-3 text-center font-semibold text-gray-700 bg-gray-50">여신건수</th>
                <th className="px-4 py-3 text-center font-semibold text-gray-700 bg-gray-50">상세</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((customer) => (
                <tr
                  key={customer.customer_id}
                  className={`border-b border-gray-100 hover:bg-gray-50 ${
                    selectedCustomer === customer.customer_id ? 'bg-blue-50' : ''
                  }`}
                >
                  <td className="px-4 py-3 font-mono text-gray-600">{customer.customer_id}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{customer.customer_name}</td>
                  <td className="px-4 py-3 text-gray-600">{customer.industry_name}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      customer.size_category === 'LARGE' ? 'bg-blue-100 text-blue-800' :
                      customer.size_category === 'MEDIUM' ? 'bg-green-100 text-green-800' :
                      customer.size_category === 'SMALL' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {customer.size_category === 'LARGE' ? '대기업' :
                       customer.size_category === 'MEDIUM' ? '중견' :
                       customer.size_category === 'SMALL' ? '중소' : '소호'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`font-semibold ${getGradeColorClass(customer.credit_rating)}`}>
                      {customer.credit_rating || '-'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right font-mono">
                    {formatAmount(customer.total_exposure, 'billion')}
                  </td>
                  <td className="px-4 py-3 text-center">{customer.facility_count}건</td>
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => loadCustomerDetail(customer.customer_id)}
                      className="px-3 py-1 text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded"
                    >
                      상세
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
          <p className="text-sm text-gray-600">
            총 {pagination.total_count.toLocaleString()}건 중 {((pagination.page - 1) * pagination.page_size) + 1} - {Math.min(pagination.page * pagination.page_size, pagination.total_count)}건
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => loadCustomers(pagination.page - 1)}
              disabled={pagination.page <= 1}
              className="p-2 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft size={20} />
            </button>
            <span className="text-sm text-gray-700">
              {pagination.page} / {pagination.total_pages}
            </span>
            <button
              onClick={() => loadCustomers(pagination.page + 1)}
              disabled={pagination.page >= pagination.total_pages}
              className="p-2 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight size={20} />
            </button>
          </div>
        </div>
      </Card>

      {/* Customer Detail Modal */}
      {selectedCustomer && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-900">
                {detailLoading ? '로딩 중...' : customerDetail?.basic_info.customer_name}
              </h2>
              <button
                onClick={() => {
                  setSelectedCustomer(null);
                  setCustomerDetail(null);
                }}
                className="p-2 hover:bg-gray-100 rounded-full"
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Content */}
            <div className="overflow-y-auto max-h-[calc(90vh-80px)] p-6">
              {detailLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : customerDetail && (
                <div className="space-y-6">
                  {/* Basic Info */}
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <h3 className="text-sm font-semibold text-gray-700 mb-3">기본 정보</h3>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-500">고객 ID</span>
                          <span className="font-mono">{customerDetail.basic_info.customer_id}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">사업자번호</span>
                          <span>{customerDetail.basic_info.business_number}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">업종</span>
                          <span>{customerDetail.basic_info.industry_name}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">규모</span>
                          <span>{customerDetail.basic_info.size_category === 'LARGE' ? '대기업' :
                                 customerDetail.basic_info.size_category === 'MEDIUM' ? '중견기업' :
                                 customerDetail.basic_info.size_category === 'SMALL' ? '중소기업' : '소호기업'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">설립일</span>
                          <span>{formatDate(customerDetail.basic_info.establishment_date)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">종업원수</span>
                          <span>{customerDetail.basic_info.employees?.toLocaleString()}명</span>
                        </div>
                      </div>
                    </div>

                    <div>
                      <h3 className="text-sm font-semibold text-gray-700 mb-3">재무 정보</h3>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-500">총자산</span>
                          <span className="font-mono">{formatAmount(customerDetail.financials.total_assets, 'billion')}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">매출액</span>
                          <span className="font-mono">{formatAmount(customerDetail.financials.annual_revenue, 'billion')}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">소재지</span>
                          <span>{customerDetail.basic_info.address || '-'}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Credit Rating History */}
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">신용등급 이력</h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="bg-gray-50">
                            <th className="px-3 py-2 text-left font-medium text-gray-600">평가일</th>
                            <th className="px-3 py-2 text-center font-medium text-gray-600">등급</th>
                            <th className="px-3 py-2 text-right font-medium text-gray-600">PD</th>
                            <th className="px-3 py-2 text-right font-medium text-gray-600">LGD</th>
                            <th className="px-3 py-2 text-left font-medium text-gray-600">모델</th>
                          </tr>
                        </thead>
                        <tbody>
                          {customerDetail.credit_ratings.slice(0, 5).map((rating, idx) => (
                            <tr key={idx} className="border-b border-gray-100">
                              <td className="px-3 py-2">{formatDate(rating.rating_date)}</td>
                              <td className="px-3 py-2 text-center">
                                <span className={`font-semibold ${getGradeColorClass(rating.rating)}`}>
                                  {rating.rating}
                                </span>
                              </td>
                              <td className="px-3 py-2 text-right font-mono">{formatPercent(rating.pd * 100, 3)}</td>
                              <td className="px-3 py-2 text-right font-mono">{formatPercent(rating.lgd * 100)}</td>
                              <td className="px-3 py-2 text-gray-600">{rating.model_type}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Facility Summary */}
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">여신 현황 요약</h3>
                    <div className="grid grid-cols-4 gap-4">
                      <div className="p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-500">총 여신건수</p>
                        <p className="text-lg font-bold text-gray-900">{customerDetail.facility_summary.active_count}건</p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-500">총 한도</p>
                        <p className="text-lg font-bold text-gray-900">{formatAmount(customerDetail.facility_summary.total_limit, 'billion')}</p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-500">사용액</p>
                        <p className="text-lg font-bold text-gray-900">{formatAmount(customerDetail.facility_summary.total_outstanding, 'billion')}</p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-500">가용한도</p>
                        <p className="text-lg font-bold text-green-600">{formatAmount(customerDetail.facility_summary.total_available, 'billion')}</p>
                      </div>
                    </div>
                  </div>

                  {/* Facilities List */}
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">여신 목록</h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="bg-gray-50">
                            <th className="px-3 py-2 text-left font-medium text-gray-600">상품</th>
                            <th className="px-3 py-2 text-right font-medium text-gray-600">한도</th>
                            <th className="px-3 py-2 text-right font-medium text-gray-600">잔액</th>
                            <th className="px-3 py-2 text-right font-medium text-gray-600">금리</th>
                            <th className="px-3 py-2 text-center font-medium text-gray-600">만기</th>
                            <th className="px-3 py-2 text-center font-medium text-gray-600">상태</th>
                          </tr>
                        </thead>
                        <tbody>
                          {customerDetail.facilities.map((facility) => (
                            <tr key={facility.facility_id} className="border-b border-gray-100">
                              <td className="px-3 py-2">
                                <div>
                                  <p className="font-medium text-gray-900">{facility.product_name}</p>
                                  <p className="text-xs text-gray-500">{facility.facility_type}</p>
                                </div>
                              </td>
                              <td className="px-3 py-2 text-right font-mono">{formatAmount(facility.limit_amount, 'billion')}</td>
                              <td className="px-3 py-2 text-right font-mono">{formatAmount(facility.outstanding_amount, 'billion')}</td>
                              <td className="px-3 py-2 text-right font-mono">{formatPercent(facility.interest_rate)}</td>
                              <td className="px-3 py-2 text-center">{formatDate(facility.maturity_date)}</td>
                              <td className="px-3 py-2 text-center">
                                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColorClass(facility.status)}`}>
                                  {facility.status === 'ACTIVE' ? '정상' : facility.status}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Risk Metrics */}
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">리스크 지표</h3>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-500">총 RWA</p>
                        <p className="text-lg font-bold text-gray-900">{formatAmount(customerDetail.risk_metrics.total_rwa, 'billion')}</p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-500">총 EAD</p>
                        <p className="text-lg font-bold text-gray-900">{formatAmount(customerDetail.risk_metrics.total_ead, 'billion')}</p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-500">예상손실(EL)</p>
                        <p className="text-lg font-bold text-red-600">{formatAmount(customerDetail.risk_metrics.total_el, 'billion')}</p>
                      </div>
                    </div>
                  </div>

                  {/* Industry Limit */}
                  {customerDetail.industry_limit && (
                    <div>
                      <h3 className="text-sm font-semibold text-gray-700 mb-3">업종 한도 현황</h3>
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm text-gray-600">{customerDetail.industry_limit.limit_name}</span>
                          <span className={`text-sm font-semibold ${
                            customerDetail.industry_limit.utilization_rate >= 90 ? 'text-red-600' :
                            customerDetail.industry_limit.utilization_rate >= 80 ? 'text-yellow-600' : 'text-green-600'
                          }`}>
                            {formatPercent(customerDetail.industry_limit.utilization_rate)}
                          </span>
                        </div>
                        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              customerDetail.industry_limit.utilization_rate >= 90 ? 'bg-red-500' :
                              customerDetail.industry_limit.utilization_rate >= 80 ? 'bg-yellow-500' : 'bg-green-500'
                            }`}
                            style={{ width: `${Math.min(customerDetail.industry_limit.utilization_rate, 100)}%` }}
                          />
                        </div>
                        <div className="flex justify-between mt-2 text-xs text-gray-500">
                          <span>사용: {formatAmount(customerDetail.industry_limit.exposure_amount, 'billion')}</span>
                          <span>한도: {formatAmount(customerDetail.industry_limit.limit_amount, 'billion')}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
