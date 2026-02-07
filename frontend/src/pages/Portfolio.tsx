import React, { useEffect, useState } from 'react';
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Users,
  Building2,
  BarChart3
} from 'lucide-react';
import { Card, StatCard, Table, CellFormatters, DonutChart, GroupedBarChart, COLORS, RegionFilter } from '../components';
import { portfolioApi } from '../utils/api';
import { formatAmount, formatPercent, formatRatio, getStrategyColorClass, getStrategyLabel } from '../utils/format';

const REGIONS = [
  { value: '', label: '전체 지역' },
  { value: 'CAPITAL', label: '수도권' },
  { value: 'DAEGU_GB', label: '대구경북' },
  { value: 'BUSAN_GN', label: '부산경남' },
];

export default function Portfolio() {
  const [loading, setLoading] = useState(true);
  const [strategyMatrix, setStrategyMatrix] = useState<any>(null);
  const [concentration, setConcentration] = useState<any>(null);
  const [selectedIndustry, setSelectedIndustry] = useState<string | null>(null);
  const [industryDetail, setIndustryDetail] = useState<any>(null);
  const [region, setRegion] = useState('');
  const [regionAnalysis, setRegionAnalysis] = useState<any>(null);
  const [selectedMetric, setSelectedMetric] = useState<string>('avg_pd');
  const [showRegionAnalysis, setShowRegionAnalysis] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    loadData();
    if (selectedIndustry) {
      loadIndustryDetail(selectedIndustry);
    }
  }, [region]);

  const loadData = async () => {
    try {
      const [matrixRes, concRes, regionRes] = await Promise.all([
        portfolioApi.getStrategyMatrix(region || undefined),
        portfolioApi.getConcentration(region || undefined),
        portfolioApi.getIndustryRegionAnalysis()
      ]);
      setStrategyMatrix(matrixRes.data);
      setConcentration(concRes.data);
      setRegionAnalysis(regionRes.data);
    } catch (error) {
      console.error('Portfolio data load error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadIndustryDetail = async (code: string) => {
    setSelectedIndustry(code);
    try {
      const response = await portfolioApi.getIndustryDetail(code, region || undefined);
      setIndustryDetail(response.data);
    } catch (error) {
      console.error('Industry detail load error:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // 전략 분포 데이터
  const strategyDistribution = strategyMatrix?.strategy_distribution?.map((s: any) => ({
    name: getStrategyLabel(s.strategy),
    value: s.exposure,
    color: s.strategy === 'EXPAND' ? '#10b981' :
           s.strategy === 'SELECTIVE' ? '#3b82f6' :
           s.strategy === 'MAINTAIN' ? '#6b7280' :
           s.strategy === 'REDUCE' ? '#f59e0b' : '#ef4444'
  })) || [];

  // 업종별 집중도 데이터
  const industryConcentration = concentration?.by_industry?.slice(0, 10).map((ind: any) => ({
    name: ind.industry_name,
    익스포저: ind.exposure / 100000000,
    비중: ind.share
  })) || [];

  // 등급 그리드
  const grades = ['AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC'];

  return (
    <div className="space-y-6">
      {/* 페이지 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">포트폴리오 전략</h1>
          <p className="text-sm text-gray-500 mt-1">업종별/등급별 여신 전략 및 집중도 관리</p>
        </div>
        <RegionFilter value={region} onChange={setRegion} />
      </div>

      {/* 집중도 요약 */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="총 익스포저"
          value={formatAmount(concentration?.total_exposure || 0, 'billion')}
          icon={<Building2 size={24} />}
          color="blue"
        />
        <StatCard
          title="HHI (업종)"
          value={formatPercent((concentration?.hhi_industry || 0) * 100, 0)}
          subtitle={concentration?.hhi_industry > 0.25 ? '집중도 높음' : '집중도 적정'}
          icon={<BarChart3 size={24} />}
          color={concentration?.hhi_industry > 0.25 ? 'red' : 'green'}
        />
        <StatCard
          title="Top 10 기업 비중"
          value={formatPercent(concentration?.top_customers?.reduce((sum: number, c: any) => sum + c.share, 0) || 0)}
          icon={<Users size={24} />}
          color="yellow"
        />
        <StatCard
          title="Top 5 그룹 비중"
          value={formatPercent(concentration?.top_groups?.reduce((sum: number, g: any) => sum + g.share, 0) || 0)}
          icon={<AlertTriangle size={24} />}
          color="yellow"
        />
      </div>

      {/* 전략 매트릭스 */}
      <Card title="업종-등급 전략 매트릭스">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr>
                <th className="px-3 py-2 bg-gray-50 text-left font-semibold text-gray-700 border-b">업종</th>
                {grades.map(grade => (
                  <th key={grade} className="px-3 py-2 bg-gray-50 text-center font-semibold text-gray-700 border-b">
                    {grade}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {strategyMatrix?.industries?.map((ind: any) => (
                <tr
                  key={ind.industry_code}
                  className={`border-b hover:bg-gray-50 cursor-pointer ${
                    selectedIndustry === ind.industry_code ? 'bg-blue-50' : ''
                  }`}
                  onClick={() => loadIndustryDetail(ind.industry_code)}
                >
                  <td className="px-3 py-2 font-medium text-gray-900">
                    {ind.industry_name}
                  </td>
                  {grades.map(grade => {
                    const strategy = ind.strategies?.[grade] || 'MAINTAIN';
                    return (
                      <td key={grade} className="px-3 py-2 text-center">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getStrategyColorClass(strategy)}`}>
                          {getStrategyLabel(strategy)}
                        </span>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-4 flex items-center justify-center space-x-4 text-xs">
          <span className="flex items-center"><span className="w-3 h-3 bg-green-100 rounded mr-1"></span>확대</span>
          <span className="flex items-center"><span className="w-3 h-3 bg-blue-100 rounded mr-1"></span>선별</span>
          <span className="flex items-center"><span className="w-3 h-3 bg-gray-100 rounded mr-1"></span>유지</span>
          <span className="flex items-center"><span className="w-3 h-3 bg-yellow-100 rounded mr-1"></span>축소</span>
          <span className="flex items-center"><span className="w-3 h-3 bg-red-100 rounded mr-1"></span>퇴출</span>
        </div>
      </Card>

      {/* 차트 영역 */}
      <div className="grid grid-cols-3 gap-6">
        {/* 전략별 분포 */}
        <Card title="전략별 익스포저 분포">
          <DonutChart
            data={strategyDistribution}
            height={280}
            innerRadius={50}
            outerRadius={90}
          />
        </Card>

        {/* 업종별 집중도 */}
        <Card title="업종별 익스포저 (상위 10)" className="col-span-2">
          <GroupedBarChart
            data={industryConcentration}
            bars={[
              { key: '익스포저', name: '익스포저(억)', color: COLORS.primary }
            ]}
            xAxisKey="name"
            layout="vertical"
            height={280}
            showLegend={false}
          />
        </Card>
      </div>

      {/* 집중도 상세 */}
      <div className="grid grid-cols-2 gap-6">
        {/* 대기업 집중도 */}
        <Card title="Top 10 기업 집중도">
          <div className="space-y-3">
            {concentration?.top_customers?.map((cust: any, index: number) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center">
                  <span className="w-6 h-6 flex items-center justify-center bg-blue-100 text-blue-700 text-xs font-medium rounded-full mr-3">
                    {index + 1}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{cust.customer_name}</p>
                    <p className="text-xs text-gray-500">{cust.industry_name}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-gray-900">
                    {formatAmount(cust.exposure, 'billion')}
                  </p>
                  <p className="text-xs text-gray-500">{formatPercent(cust.share)}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* 그룹 집중도 */}
        <Card title="Top 5 그룹 집중도">
          <div className="space-y-3">
            {concentration?.top_groups?.map((group: any, index: number) => (
              <div key={index} className="p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center">
                    <span className="w-6 h-6 flex items-center justify-center bg-purple-100 text-purple-700 text-xs font-medium rounded-full mr-3">
                      {index + 1}
                    </span>
                    <p className="text-sm font-medium text-gray-900">{group.group_name}</p>
                  </div>
                  <span className="text-sm font-semibold text-gray-900">
                    {formatAmount(group.exposure, 'billion')}
                  </span>
                </div>
                <div className="relative h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="absolute left-0 top-0 h-full bg-purple-500 rounded-full"
                    style={{ width: `${Math.min(group.share * 10, 100)}%` }}
                  />
                </div>
                <div className="flex justify-between mt-1 text-xs text-gray-500">
                  <span>{group.member_count}개 계열사</span>
                  <span>{formatPercent(group.share)}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* 지역별 산업 리스크 비교 분석 */}
      <Card
        title="지역별 산업 리스크 비교 분석"
        headerAction={
          <div className="flex items-center gap-3">
            <select
              value={selectedMetric}
              onChange={(e) => setSelectedMetric(e.target.value)}
              className="px-2 py-1 border border-gray-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="avg_pd">평균 PD</option>
              <option value="avg_lgd">평균 LGD</option>
              <option value="raroc">RAROC</option>
              <option value="rwa_density">RWA 밀도</option>
              <option value="total_exposure">익스포저</option>
              <option value="customer_count">고객 수</option>
            </select>
            <button
              onClick={() => setShowRegionAnalysis(!showRegionAnalysis)}
              className="text-xs text-blue-600 hover:text-blue-800 font-medium"
            >
              {showRegionAnalysis ? '요약 보기' : '상세 보기'}
            </button>
          </div>
        }
      >
        {regionAnalysis?.industries && (
          <>
            {/* 요약 비교 테이블 */}
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b bg-gray-50">
                    <th className="px-3 py-2 text-left font-semibold text-gray-700 w-32">업종</th>
                    <th className="px-3 py-2 text-center font-semibold text-gray-700" colSpan={2}>
                      <span className="text-blue-600">수도권</span>
                    </th>
                    <th className="px-3 py-2 text-center font-semibold text-gray-700" colSpan={2}>
                      <span className="text-green-600">대구경북</span>
                    </th>
                    <th className="px-3 py-2 text-center font-semibold text-gray-700" colSpan={2}>
                      <span className="text-orange-600">부산경남</span>
                    </th>
                    <th className="px-3 py-2 text-center font-semibold text-gray-500">전국</th>
                  </tr>
                  <tr className="border-b bg-gray-50">
                    <th className="px-3 py-1"></th>
                    {['수도권', '대구경북', '부산경남'].map(r => (
                      <React.Fragment key={r}>
                        <th className="px-2 py-1 text-center text-gray-500 font-normal">
                          {selectedMetric === 'total_exposure' ? '익스포저' :
                           selectedMetric === 'customer_count' ? '고객수' :
                           selectedMetric === 'avg_pd' ? 'PD' :
                           selectedMetric === 'avg_lgd' ? 'LGD' :
                           selectedMetric === 'raroc' ? 'RAROC' : 'RWA밀도'}
                        </th>
                        {showRegionAnalysis && (
                          <th className="px-2 py-1 text-center text-gray-500 font-normal">고객수</th>
                        )}
                      </React.Fragment>
                    ))}
                    <th className="px-2 py-1 text-center text-gray-500 font-normal">
                      {selectedMetric === 'total_exposure' ? '익스포저' :
                       selectedMetric === 'customer_count' ? '고객수' :
                       selectedMetric === 'avg_pd' ? 'PD' :
                       selectedMetric === 'avg_lgd' ? 'LGD' :
                       selectedMetric === 'raroc' ? 'RAROC' : 'RWA밀도'}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {regionAnalysis.industries.map((ind: any) => {
                    const regions = ['CAPITAL', 'DAEGU_GB', 'BUSAN_GN'];
                    const regionColors = ['text-blue-700', 'text-green-700', 'text-orange-700'];

                    const formatMetric = (val: number, metric: string) => {
                      if (metric === 'total_exposure') return formatAmount(val, 'billion');
                      if (metric === 'customer_count') return val.toLocaleString();
                      if (metric === 'raroc') return formatPercent(val);
                      if (metric === 'rwa_density') return formatPercent(val);
                      if (metric === 'avg_pd') return formatRatio(val);
                      if (metric === 'avg_lgd') return formatRatio(val);
                      return val.toFixed(2);
                    };

                    // 지역 간 최대/최소 찾기 (색상 하이라이트용)
                    const vals = regions.map(rgn => ind.regions[rgn]?.[selectedMetric] || 0);
                    const maxVal = Math.max(...vals);
                    const minVal = Math.min(...vals.filter(v => v > 0));

                    return (
                      <tr key={ind.industry_code} className="border-b hover:bg-gray-50">
                        <td className="px-3 py-2 font-medium text-gray-900">{ind.industry_name}</td>
                        {regions.map((rgn, idx) => {
                          const data = ind.regions[rgn] || {};
                          const val = data[selectedMetric] || 0;
                          const isMax = val === maxVal && maxVal > 0;
                          const isMin = val === minVal && minVal > 0 && maxVal !== minVal;
                          const highlight = selectedMetric === 'raroc'
                            ? (isMax ? 'bg-green-50 font-semibold' : isMin ? 'bg-red-50' : '')
                            : selectedMetric === 'total_exposure' || selectedMetric === 'customer_count'
                            ? (isMax ? 'bg-blue-50 font-semibold' : '')
                            : (isMin ? 'bg-green-50 font-semibold' : isMax ? 'bg-red-50' : '');

                          return (
                            <React.Fragment key={rgn}>
                              <td className={`px-2 py-2 text-center ${regionColors[idx]} ${highlight}`}>
                                {val > 0 ? formatMetric(val, selectedMetric) : '-'}
                              </td>
                              {showRegionAnalysis && (
                                <td className="px-2 py-2 text-center text-gray-500">
                                  {data.customer_count || 0}
                                </td>
                              )}
                            </React.Fragment>
                          );
                        })}
                        <td className="px-2 py-2 text-center text-gray-600 bg-gray-50">
                          {formatMetric(ind.total[selectedMetric] || 0, selectedMetric)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* 범례 */}
            <div className="mt-3 flex items-center justify-end gap-4 text-xs text-gray-500">
              {selectedMetric === 'raroc' ? (
                <>
                  <span className="flex items-center"><span className="w-3 h-3 bg-green-50 border border-green-200 rounded mr-1"></span>최고 수익성</span>
                  <span className="flex items-center"><span className="w-3 h-3 bg-red-50 border border-red-200 rounded mr-1"></span>최저 수익성</span>
                </>
              ) : selectedMetric === 'total_exposure' || selectedMetric === 'customer_count' ? (
                <span className="flex items-center"><span className="w-3 h-3 bg-blue-50 border border-blue-200 rounded mr-1"></span>최대</span>
              ) : (
                <>
                  <span className="flex items-center"><span className="w-3 h-3 bg-green-50 border border-green-200 rounded mr-1"></span>가장 우량</span>
                  <span className="flex items-center"><span className="w-3 h-3 bg-red-50 border border-red-200 rounded mr-1"></span>리스크 높음</span>
                </>
              )}
            </div>
          </>
        )}
      </Card>

      {/* 업종 상세 (선택 시) */}
      {industryDetail && (
        <Card
          title={`${industryDetail.industry_name} 업종 상세`}
          headerAction={
            <button
              onClick={() => setSelectedIndustry(null)}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              닫기
            </button>
          }
        >
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">총 익스포저</p>
              <p className="text-xl font-bold text-gray-900">
                {formatAmount(industryDetail.total_exposure || 0, 'billion')}
              </p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">평균 등급</p>
              <p className="text-xl font-bold text-blue-600">
                {industryDetail.avg_grade || '-'}
              </p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">평균 RAROC</p>
              <p className={`text-xl font-bold ${
                industryDetail.avg_raroc >= 15 ? 'text-green-600' : 'text-red-600'
              }`}>
                {formatPercent(industryDetail.avg_raroc || 0)}
              </p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">한도 사용률</p>
              <p className={`text-xl font-bold ${
                industryDetail.limit_usage >= 90 ? 'text-red-600' :
                industryDetail.limit_usage >= 80 ? 'text-yellow-600' : 'text-green-600'
              }`}>
                {formatPercent(industryDetail.limit_usage || 0)}
              </p>
            </div>
          </div>

          {/* 업종 내 등급 분포 */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-gray-700">등급별 분포</h4>
            {industryDetail.by_grade?.map((grade: any) => (
              <div key={grade.grade} className="flex items-center">
                <span className="w-12 text-sm font-medium text-gray-700">{grade.grade}</span>
                <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden mx-2">
                  <div
                    className="h-full bg-blue-500 rounded-full"
                    style={{ width: `${grade.share}%` }}
                  />
                </div>
                <span className="w-20 text-right text-sm text-gray-600">
                  {formatAmount(grade.exposure, 'billion')}
                </span>
                <span className="w-16 text-right text-sm text-gray-500">
                  ({formatPercent(grade.share)})
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
