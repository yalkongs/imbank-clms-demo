import React, { useEffect, useState, useCallback } from 'react';
import {
  Search,
  User,
  CreditCard,
  Shield,
  Landmark,
  FileText,
  Building2,
  ChevronLeft,
  ChevronRight,
  Filter,
  X
} from 'lucide-react';
import { Card, StatCard } from '../components';
import { customersApi } from '../utils/api';
import { formatAmount, formatPercent, formatDate, getGradeColorClass, getStatusColorClass } from '../utils/format';

interface Customer {
  customer_id: string;
  customer_name: string;
  business_number: string;
  industry_code: string;
  industry_name: string;
  size_category: string;
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
  financials: { total_assets: number; annual_revenue: number };
  credit_ratings: Array<{
    rating: string; pd: number; lgd: number;
    rating_date: string; model_type: string; rating_reason: string;
  }>;
  facilities: Array<{
    facility_id: string; facility_type: string; product_name: string;
    limit_amount: number; outstanding_amount: number; available_amount: number;
    interest_rate: number; start_date: string; maturity_date: string; status: string;
  }>;
  facility_summary: {
    total_count: number; active_count: number;
    total_limit: number; total_outstanding: number; total_available: number;
  };
  risk_metrics: { total_rwa: number; total_ead: number; total_el: number };
  industry_limit: {
    limit_name: string; limit_amount: number;
    exposure_amount: number; utilization_rate: number;
  } | null;
  collaterals: Array<{
    collateral_id: string; collateral_type: string; collateral_subtype: string;
    original_value: number; current_value: number; ltv: number;
    valuation_date: string; priority_rank: number; facility_id: string;
  }>;
  applications: Array<{
    application_id: string; application_date: string; application_type: string;
    product_name: string; requested_amount: number; status: string;
    current_stage: string; purpose_detail: string;
  }>;
}

type TabKey = 'basic' | 'facilities' | 'credit' | 'collateral' | 'applications';

const TABS: { key: TabKey; label: string; icon: React.ReactNode }[] = [
  { key: 'basic', label: '기본정보', icon: <User size={16} /> },
  { key: 'facilities', label: '여신현황', icon: <CreditCard size={16} /> },
  { key: 'credit', label: '신용정보', icon: <Shield size={16} /> },
  { key: 'collateral', label: '담보현황', icon: <Landmark size={16} /> },
  { key: 'applications', label: '심사이력', icon: <FileText size={16} /> },
];

const sizeCategoryLabel = (s: string) =>
  s === 'LARGE' ? '대기업' : s === 'MEDIUM' ? '중견기업' : s === 'SMALL' ? '중소기업' : '소호';

const sizeBadgeClass = (s: string) =>
  s === 'LARGE' ? 'bg-blue-100 text-blue-800' :
  s === 'MEDIUM' ? 'bg-green-100 text-green-800' :
  s === 'SMALL' ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-800';

export default function CustomerBrowser() {
  // --- List state ---
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [pagination, setPagination] = useState({ page: 1, page_size: 15, total_count: 0, total_pages: 0 });
  const [search, setSearch] = useState('');
  const [sizeFilter, setSizeFilter] = useState('');
  const [industries, setIndustries] = useState<{ industry_code: string; industry_name: string; customer_count: number }[]>([]);
  const [industryFilter, setIndustryFilter] = useState('');

  // --- Detail state ---
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<CustomerDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<TabKey>('basic');

  // --- Load industries once ---
  useEffect(() => {
    customersApi.getIndustries().then(res => setIndustries(res.data)).catch(() => {});
  }, []);

  // --- Load customer list ---
  const loadCustomers = useCallback(async (page = 1) => {
    setListLoading(true);
    try {
      const res = await customersApi.getAll({
        page,
        page_size: pagination.page_size,
        search: search || undefined,
        industry_code: industryFilter || undefined,
        size_category: sizeFilter || undefined,
        sort_by: 'customer_name',
        sort_order: 'asc',
      });
      setCustomers(res.data.data);
      setPagination(res.data.pagination);
    } catch (e) {
      console.error('Load error:', e);
    } finally {
      setListLoading(false);
    }
  }, [search, industryFilter, sizeFilter, pagination.page_size]);

  // Debounced reload on filter change
  useEffect(() => {
    const t = setTimeout(() => loadCustomers(1), 250);
    return () => clearTimeout(t);
  }, [search, industryFilter, sizeFilter]);

  // --- Select customer ---
  const selectCustomer = async (id: string) => {
    if (id === selectedId) return;
    setSelectedId(id);
    setDetailLoading(true);
    setActiveTab('basic');
    try {
      const res = await customersApi.getById(id);
      setDetail(res.data);
    } catch (e) {
      console.error('Detail error:', e);
    } finally {
      setDetailLoading(false);
    }
  };

  // --- Navigate prev/next customer ---
  const navigateCustomer = (dir: -1 | 1) => {
    const idx = customers.findIndex(c => c.customer_id === selectedId);
    if (idx < 0) return;
    const next = customers[idx + dir];
    if (next) selectCustomer(next.customer_id);
  };

  const clearFilters = () => { setSearch(''); setSizeFilter(''); setIndustryFilter(''); };
  const hasFilters = !!(search || sizeFilter || industryFilter);

  // --- Tab renderers (detail right panel) ---

  const renderBasicInfo = () => {
    if (!detail) return null;
    const { basic_info, financials, industry_limit } = detail;
    return (
      <div className="space-y-5">
        <div className="grid grid-cols-2 gap-5">
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase mb-3">기본 정보</h4>
            <div className="space-y-2.5 text-sm">
              {[
                ['고객 ID', basic_info.customer_id],
                ['사업자번호', basic_info.business_number],
                ['업종', `${basic_info.industry_name} (${basic_info.industry_code})`],
                ['규모', sizeCategoryLabel(basic_info.size_category)],
                ['설립일', formatDate(basic_info.establishment_date)],
                ['종업원수', basic_info.employees ? `${basic_info.employees.toLocaleString()}명` : '-'],
                ['소재지', basic_info.address || '-'],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between">
                  <span className="text-gray-500">{label}</span>
                  <span className="font-medium text-gray-900 text-right">{value}</span>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase mb-3">재무 정보</h4>
            <div className="space-y-2.5 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">총자산</span>
                <span className="font-mono font-medium">{formatAmount(financials.total_assets, 'billion')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">매출액</span>
                <span className="font-mono font-medium">{formatAmount(financials.annual_revenue, 'billion')}</span>
              </div>
            </div>
            {industry_limit && (
              <div className="mt-5 pt-4 border-t border-gray-100">
                <h4 className="text-xs font-semibold text-gray-400 uppercase mb-3">업종 한도</h4>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600">{industry_limit.limit_name}</span>
                  <span className={`text-sm font-semibold ${
                    industry_limit.utilization_rate >= 90 ? 'text-red-600' :
                    industry_limit.utilization_rate >= 80 ? 'text-yellow-600' : 'text-green-600'
                  }`}>{formatPercent(industry_limit.utilization_rate)}</span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${
                    industry_limit.utilization_rate >= 90 ? 'bg-red-500' :
                    industry_limit.utilization_rate >= 80 ? 'bg-yellow-500' : 'bg-green-500'
                  }`} style={{ width: `${Math.min(industry_limit.utilization_rate, 100)}%` }} />
                </div>
                <div className="flex justify-between mt-2 text-xs text-gray-500">
                  <span>사용: {formatAmount(industry_limit.exposure_amount, 'billion')}</span>
                  <span>한도: {formatAmount(industry_limit.limit_amount, 'billion')}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderFacilities = () => {
    if (!detail) return null;
    const { facility_summary, facilities } = detail;
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-4 gap-3">
          {[
            ['여신건수', `${facility_summary.active_count}건`, 'Active'],
            ['총 한도', formatAmount(facility_summary.total_limit, 'billion'), '승인한도'],
            ['사용액', formatAmount(facility_summary.total_outstanding, 'billion'), '여신잔액'],
            ['가용한도', formatAmount(facility_summary.total_available, 'billion'), '잔여한도'],
          ].map(([title, value, sub]) => (
            <div key={title} className="p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-500">{title}</p>
              <p className="text-base font-bold text-gray-900">{value}</p>
              <p className="text-xs text-gray-400">{sub}</p>
            </div>
          ))}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-3 py-2 text-left font-semibold text-gray-700">상품</th>
                <th className="px-3 py-2 text-right font-semibold text-gray-700">한도</th>
                <th className="px-3 py-2 text-right font-semibold text-gray-700">잔액</th>
                <th className="px-3 py-2 text-right font-semibold text-gray-700">금리</th>
                <th className="px-3 py-2 text-center font-semibold text-gray-700">만기</th>
                <th className="px-3 py-2 text-center font-semibold text-gray-700">상태</th>
              </tr>
            </thead>
            <tbody>
              {facilities.map(f => (
                <tr key={f.facility_id} className="border-b border-gray-100">
                  <td className="px-3 py-2">
                    <p className="font-medium text-gray-900">{f.product_name}</p>
                    <p className="text-xs text-gray-500">{f.facility_type}</p>
                  </td>
                  <td className="px-3 py-2 text-right font-mono">{formatAmount(f.limit_amount, 'billion')}</td>
                  <td className="px-3 py-2 text-right font-mono">{formatAmount(f.outstanding_amount, 'billion')}</td>
                  <td className="px-3 py-2 text-right font-mono">{formatPercent(f.interest_rate)}</td>
                  <td className="px-3 py-2 text-center text-gray-600">{formatDate(f.maturity_date)}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColorClass(f.status)}`}>
                      {f.status === 'ACTIVE' ? '정상' : f.status}
                    </span>
                  </td>
                </tr>
              ))}
              {facilities.length === 0 && (
                <tr><td colSpan={6} className="px-3 py-6 text-center text-gray-400">여신 내역이 없습니다.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderCredit = () => {
    if (!detail) return null;
    const { credit_ratings, risk_metrics } = detail;
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-3 gap-3">
          {[
            ['총 RWA', formatAmount(risk_metrics.total_rwa, 'billion'), '위험가중자산'],
            ['총 EAD', formatAmount(risk_metrics.total_ead, 'billion'), '부도시익스포저'],
            ['예상손실(EL)', formatAmount(risk_metrics.total_el, 'billion'), 'Expected Loss'],
          ].map(([title, value, sub]) => (
            <div key={title} className="p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-500">{title}</p>
              <p className="text-base font-bold text-gray-900">{value}</p>
              <p className="text-xs text-gray-400">{sub}</p>
            </div>
          ))}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-3 py-2 text-left font-semibold text-gray-700">평가일</th>
                <th className="px-3 py-2 text-center font-semibold text-gray-700">등급</th>
                <th className="px-3 py-2 text-right font-semibold text-gray-700">PD</th>
                <th className="px-3 py-2 text-right font-semibold text-gray-700">LGD</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">모델</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">사유</th>
              </tr>
            </thead>
            <tbody>
              {credit_ratings.map((r, idx) => (
                <tr key={idx} className="border-b border-gray-100">
                  <td className="px-3 py-2 text-gray-600">{formatDate(r.rating_date)}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`font-semibold ${getGradeColorClass(r.rating)}`}>{r.rating}</span>
                  </td>
                  <td className="px-3 py-2 text-right font-mono">{formatPercent(r.pd * 100, 3)}</td>
                  <td className="px-3 py-2 text-right font-mono">{formatPercent(r.lgd * 100)}</td>
                  <td className="px-3 py-2 text-gray-600">{r.model_type}</td>
                  <td className="px-3 py-2 text-gray-600 max-w-[160px] truncate">{r.rating_reason || '-'}</td>
                </tr>
              ))}
              {credit_ratings.length === 0 && (
                <tr><td colSpan={6} className="px-3 py-6 text-center text-gray-400">신용등급 이력이 없습니다.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderCollateral = () => {
    if (!detail) return null;
    const { collaterals } = detail;
    const totalOriginal = collaterals.reduce((s, c) => s + (c.original_value || 0), 0);
    const totalCurrent = collaterals.reduce((s, c) => s + (c.current_value || 0), 0);
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-3 gap-3">
          {[
            ['담보 건수', `${collaterals.length}건`, '등록 담보'],
            ['감정가 합계', formatAmount(totalOriginal, 'billion'), '최초 감정가'],
            ['현재가 합계', formatAmount(totalCurrent, 'billion'), '현재 평가가'],
          ].map(([title, value, sub]) => (
            <div key={title} className="p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-500">{title}</p>
              <p className="text-base font-bold text-gray-900">{value}</p>
              <p className="text-xs text-gray-400">{sub}</p>
            </div>
          ))}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-3 py-2 text-left font-semibold text-gray-700">유형</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">세부</th>
                <th className="px-3 py-2 text-right font-semibold text-gray-700">감정가</th>
                <th className="px-3 py-2 text-right font-semibold text-gray-700">현재가</th>
                <th className="px-3 py-2 text-right font-semibold text-gray-700">LTV</th>
                <th className="px-3 py-2 text-center font-semibold text-gray-700">평가일</th>
                <th className="px-3 py-2 text-center font-semibold text-gray-700">순위</th>
              </tr>
            </thead>
            <tbody>
              {collaterals.map(c => (
                <tr key={c.collateral_id} className="border-b border-gray-100">
                  <td className="px-3 py-2 text-gray-900">{c.collateral_type}</td>
                  <td className="px-3 py-2 text-gray-600">{c.collateral_subtype || '-'}</td>
                  <td className="px-3 py-2 text-right font-mono">{formatAmount(c.original_value, 'billion')}</td>
                  <td className="px-3 py-2 text-right font-mono">{formatAmount(c.current_value, 'billion')}</td>
                  <td className="px-3 py-2 text-right font-mono">
                    <span className={c.ltv >= 80 ? 'text-red-600 font-semibold' : c.ltv >= 60 ? 'text-yellow-600' : 'text-green-600'}>
                      {formatPercent(c.ltv)}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center text-gray-600">{formatDate(c.valuation_date)}</td>
                  <td className="px-3 py-2 text-center">{c.priority_rank ? `${c.priority_rank}순위` : '-'}</td>
                </tr>
              ))}
              {collaterals.length === 0 && (
                <tr><td colSpan={7} className="px-3 py-6 text-center text-gray-400">담보 내역이 없습니다.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderApplications = () => {
    if (!detail) return null;
    const { applications } = detail;
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="px-3 py-2 text-center font-semibold text-gray-700">신청일</th>
              <th className="px-3 py-2 text-left font-semibold text-gray-700">유형</th>
              <th className="px-3 py-2 text-left font-semibold text-gray-700">상품</th>
              <th className="px-3 py-2 text-right font-semibold text-gray-700">신청금액</th>
              <th className="px-3 py-2 text-center font-semibold text-gray-700">상태</th>
              <th className="px-3 py-2 text-center font-semibold text-gray-700">단계</th>
              <th className="px-3 py-2 text-left font-semibold text-gray-700">목적</th>
            </tr>
          </thead>
          <tbody>
            {applications.map(a => (
              <tr key={a.application_id} className="border-b border-gray-100">
                <td className="px-3 py-2 text-center text-gray-600">{formatDate(a.application_date)}</td>
                <td className="px-3 py-2 text-gray-900">{a.application_type}</td>
                <td className="px-3 py-2 text-gray-600">{a.product_name || '-'}</td>
                <td className="px-3 py-2 text-right font-mono">{formatAmount(a.requested_amount, 'billion')}</td>
                <td className="px-3 py-2 text-center">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColorClass(a.status)}`}>{a.status}</span>
                </td>
                <td className="px-3 py-2 text-center text-gray-600">{a.current_stage || '-'}</td>
                <td className="px-3 py-2 text-gray-600 max-w-[160px] truncate">{a.purpose_detail || '-'}</td>
              </tr>
            ))}
            {applications.length === 0 && (
              <tr><td colSpan={7} className="px-3 py-6 text-center text-gray-400">여신신청 이력이 없습니다.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    );
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'basic': return renderBasicInfo();
      case 'facilities': return renderFacilities();
      case 'credit': return renderCredit();
      case 'collateral': return renderCollateral();
      case 'applications': return renderApplications();
    }
  };

  // ============= RENDER =============
  return (
    <div className="h-full flex flex-col -m-6">
      {/* Page Header */}
      <div className="px-6 pt-6 pb-4 bg-white border-b border-gray-200">
        <h1 className="text-2xl font-bold text-gray-900">고객 정보 조회</h1>
        <p className="text-sm text-gray-500 mt-1">고객별 여신/신용/담보 정보를 통합 브라우징합니다</p>
      </div>

      {/* Master-Detail layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* ===== LEFT: Customer List Panel ===== */}
        <div className={`flex flex-col border-r border-gray-200 bg-white transition-all ${selectedId ? 'w-[340px] min-w-[340px]' : 'w-full'}`}>
          {/* Search & Filters */}
          <div className="p-3 border-b border-gray-100 space-y-2">
            <div className="relative">
              <Search size={16} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="기업명, ID, 사업자번호..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full pl-8 pr-8 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              />
              {search && (
                <button onClick={() => setSearch('')} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                  <X size={14} />
                </button>
              )}
            </div>
            <div className="flex gap-2">
              <select
                value={industryFilter}
                onChange={e => setIndustryFilter(e.target.value)}
                className="flex-1 px-2 py-1.5 border border-gray-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">전체 업종</option>
                {industries.map(ind => (
                  <option key={ind.industry_code} value={ind.industry_code}>{ind.industry_name} ({ind.customer_count})</option>
                ))}
              </select>
              <select
                value={sizeFilter}
                onChange={e => setSizeFilter(e.target.value)}
                className="px-2 py-1.5 border border-gray-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">전체 규모</option>
                <option value="LARGE">대기업</option>
                <option value="MEDIUM">중견기업</option>
                <option value="SMALL">중소기업</option>
              </select>
              {hasFilters && (
                <button onClick={clearFilters} className="px-2 py-1.5 text-xs text-gray-500 hover:text-gray-700">
                  <X size={14} />
                </button>
              )}
            </div>
          </div>

          {/* Customer rows */}
          <div className="flex-1 overflow-y-auto">
            {listLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            ) : customers.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                <Search size={32} className="mb-2" />
                <p className="text-sm">검색 결과가 없습니다</p>
              </div>
            ) : (
              customers.map(c => (
                <button
                  key={c.customer_id}
                  onClick={() => selectCustomer(c.customer_id)}
                  className={`w-full text-left px-4 py-3 border-b border-gray-100 hover:bg-blue-50 transition-colors ${
                    selectedId === c.customer_id ? 'bg-blue-50 border-l-2 border-l-blue-600' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-gray-900 truncate">{c.customer_name}</p>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${sizeBadgeClass(c.size_category)}`}>
                          {sizeCategoryLabel(c.size_category)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-xs text-gray-500 font-mono">{c.customer_id}</span>
                        <span className="text-xs text-gray-400">|</span>
                        <span className="text-xs text-gray-500 truncate">{c.industry_name}</span>
                      </div>
                    </div>
                    <div className="flex flex-col items-end ml-3 shrink-0">
                      {c.credit_rating && (
                        <span className={`text-sm font-bold ${getGradeColorClass(c.credit_rating)}`}>{c.credit_rating}</span>
                      )}
                      {c.total_exposure > 0 && (
                        <span className="text-xs text-gray-500 font-mono">{formatAmount(c.total_exposure, 'billion')}</span>
                      )}
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>

          {/* Pagination */}
          {pagination.total_pages > 0 && (
            <div className="flex items-center justify-between px-3 py-2 border-t border-gray-200 text-xs text-gray-600">
              <span>{pagination.total_count.toLocaleString()}건</span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => loadCustomers(pagination.page - 1)}
                  disabled={pagination.page <= 1}
                  className="p-1 rounded hover:bg-gray-100 disabled:opacity-30"
                >
                  <ChevronLeft size={16} />
                </button>
                <span>{pagination.page}/{pagination.total_pages}</span>
                <button
                  onClick={() => loadCustomers(pagination.page + 1)}
                  disabled={pagination.page >= pagination.total_pages}
                  className="p-1 rounded hover:bg-gray-100 disabled:opacity-30"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ===== RIGHT: Detail Panel ===== */}
        {selectedId ? (
          <div className="flex-1 flex flex-col overflow-hidden bg-gray-50">
            {detailLoading ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
              </div>
            ) : detail ? (
              <>
                {/* Detail Header */}
                <div className="bg-white px-6 py-4 border-b border-gray-200">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-11 h-11 bg-blue-600 rounded-full flex items-center justify-center text-white text-lg font-bold shrink-0">
                        {detail.basic_info.customer_name.charAt(0)}
                      </div>
                      <div>
                        <h2 className="text-lg font-bold text-gray-900">{detail.basic_info.customer_name}</h2>
                        <p className="text-sm text-gray-500">
                          {detail.basic_info.customer_id} | {detail.basic_info.industry_name} | {sizeCategoryLabel(detail.basic_info.size_category)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-5">
                      {detail.credit_ratings.length > 0 && (
                        <div className="text-center">
                          <p className="text-[10px] text-gray-400 uppercase">등급</p>
                          <p className={`text-lg font-bold ${getGradeColorClass(detail.credit_ratings[0].rating)}`}>
                            {detail.credit_ratings[0].rating}
                          </p>
                        </div>
                      )}
                      <div className="text-center">
                        <p className="text-[10px] text-gray-400 uppercase">잔액</p>
                        <p className="text-lg font-bold text-gray-900">{formatAmount(detail.facility_summary.total_outstanding, 'billion')}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-[10px] text-gray-400 uppercase">건수</p>
                        <p className="text-lg font-bold text-gray-900">{detail.facility_summary.active_count}건</p>
                      </div>
                      {/* Prev/Next navigation */}
                      <div className="flex items-center gap-1 ml-2 border-l pl-3 border-gray-200">
                        <button
                          onClick={() => navigateCustomer(-1)}
                          disabled={customers.findIndex(c => c.customer_id === selectedId) <= 0}
                          className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 text-gray-500"
                          title="이전 고객"
                        >
                          <ChevronLeft size={18} />
                        </button>
                        <button
                          onClick={() => navigateCustomer(1)}
                          disabled={customers.findIndex(c => c.customer_id === selectedId) >= customers.length - 1}
                          className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 text-gray-500"
                          title="다음 고객"
                        >
                          <ChevronRight size={18} />
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Tabs */}
                  <div className="flex gap-1 mt-4 -mb-4">
                    {TABS.map(tab => (
                      <button
                        key={tab.key}
                        onClick={() => setActiveTab(tab.key)}
                        className={`flex items-center gap-1.5 px-3 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                          activeTab === tab.key
                            ? 'border-blue-600 text-blue-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        {tab.icon}
                        {tab.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Tab Content */}
                <div className="flex-1 overflow-y-auto p-6">
                  {renderTabContent()}
                </div>
              </>
            ) : null}
          </div>
        ) : (
          /* No selection - show empty state only when list is in narrow mode (shouldn't happen since we show full list) */
          !selectedId && customers.length > 0 ? null : (
            <div className="flex-1 flex flex-col items-center justify-center text-gray-400 bg-gray-50">
              <User size={48} className="mb-3" />
              <p className="text-lg font-medium">고객을 선택하세요</p>
              <p className="text-sm mt-1">왼쪽 목록에서 고객을 클릭하면 상세 정보를 확인할 수 있습니다</p>
            </div>
          )
        )}
      </div>
    </div>
  );
}
