import React, { useState, useEffect } from 'react';
import { assetClassificationApi } from '../utils/api';
import {
  AlertTriangle,
  TrendingDown,
  RefreshCw,
  BarChart3,
  ChevronRight,
  Shield,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

// 분류 색상 매핑
const CLASS_COLORS: Record<string, string> = {
  NORMAL:         '#22c55e',
  PRECAUTIONARY:  '#f59e0b',
  SUBSTANDARD:    '#f97316',
  DOUBTFUL:       '#ef4444',
  LOSS:           '#991b1b',
};

const CLASS_BG: Record<string, string> = {
  NORMAL:         'bg-green-100 text-green-800',
  PRECAUTIONARY:  'bg-yellow-100 text-yellow-800',
  SUBSTANDARD:    'bg-orange-100 text-orange-800',
  DOUBTFUL:       'bg-red-100 text-red-800',
  LOSS:           'bg-red-200 text-red-900',
};

interface ClassItem {
  classification: string;
  label_ko: string;
  color: string;
  count: number;
  exposure: number;
  exposure_share: number;
  required_provision: number;
  existing_provision: number;
  provision_gap: number;
  provision_rate: number;
}

interface PortfolioData {
  total_exposure: number;
  total_required_prov: number;
  total_existing_prov: number;
  total_provision_gap: number;
  npl_ratio: number;
  by_classification: ClassItem[];
}

interface MigrationRow {
  from_class: string;
  from_label: string;
  [key: string]: any;
}

const fmtAmt = (v: number) => `${(v / 100000000).toFixed(1)}억`;
const fmtPct = (v: number) => `${v.toFixed(2)}%`;

export default function AssetClassification() {
  const [tab, setTab] = useState<'portfolio' | 'migration' | 'gap'>('portfolio');
  const [portfolio, setPortfolio] = useState<PortfolioData | null>(null);
  const [migration, setMigration] = useState<any>(null);
  const [gapData, setGapData]   = useState<any>(null);
  const [trend, setTrend]       = useState<any[]>([]);
  const [loading, setLoading]   = useState(true);
  const [running, setRunning]   = useState(false);

  useEffect(() => {
    loadPortfolio();
    loadTrend();
  }, []);

  const loadPortfolio = async () => {
    setLoading(true);
    try {
      const res = await assetClassificationApi.getPortfolio();
      setPortfolio(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadMigration = async () => {
    try {
      const res = await assetClassificationApi.getMigrationMatrix();
      setMigration(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const loadGap = async () => {
    try {
      const res = await assetClassificationApi.getProvisionGap();
      setGapData(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const loadTrend = async () => {
    try {
      const res = await assetClassificationApi.getTrend(12);
      setTrend(res.data.trend || []);
    } catch (e) {
      console.error(e);
    }
  };

  const handleTabChange = (t: typeof tab) => {
    setTab(t);
    if (t === 'migration' && !migration) loadMigration();
    if (t === 'gap' && !gapData) loadGap();
  };

  const handleRunClassification = async () => {
    if (running) return;
    setRunning(true);
    try {
      await assetClassificationApi.runClassification();
      await loadPortfolio();
      await loadTrend();
      alert('분류 완료');
    } catch (e) {
      alert('분류 실행 실패');
    } finally {
      setRunning(false);
    }
  };

  const classKeys = ['NORMAL', 'PRECAUTIONARY', 'SUBSTANDARD', 'DOUBTFUL', 'LOSS'];
  const classLabels: Record<string, string> = {
    NORMAL: '정상', PRECAUTIONARY: '요주의', SUBSTANDARD: '고정',
    DOUBTFUL: '회수의문', LOSS: '추정손실',
  };

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">자산건전성 분류</h1>
          <p className="text-sm text-gray-500 mt-1">
            금감원 기준 5단계 분류 — DPD · PD · EWS 보수주의 원칙 적용
          </p>
        </div>
        <button
          onClick={handleRunClassification}
          disabled={running}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
        >
          <RefreshCw size={16} className={running ? 'animate-spin' : ''} />
          월말 일괄 분류 실행
        </button>
      </div>

      {/* KPI 카드 */}
      {portfolio && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">총 여신 잔액</p>
            <p className="text-2xl font-bold text-gray-900">{fmtAmt(portfolio.total_exposure)}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            {/* 감독규정상 NPL = 고정이하여신비율. 이 값이 정식 정의다. */}
            <p className="text-xs text-gray-500 mb-1">고정이하여신비율 (NPL)</p>
            <p className={`text-2xl font-bold ${portfolio.npl_ratio > 3 ? 'text-red-600' : 'text-gray-900'}`}>
              {fmtPct(portfolio.npl_ratio)}
            </p>
            <p className="text-xs text-gray-400 mt-1">고정 + 회수의문 + 추정손실</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">필요 충당금</p>
            <p className="text-2xl font-bold text-gray-900">{fmtAmt(portfolio.total_required_prov)}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">충당금 부족액</p>
            <p className={`text-2xl font-bold ${portfolio.total_provision_gap > 0 ? 'text-red-600' : 'text-green-600'}`}>
              {fmtAmt(portfolio.total_provision_gap)}
            </p>
          </div>
        </div>
      )}

      {/* 탭 */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="border-b border-gray-200 px-6">
          <nav className="flex gap-6">
            {[
              { key: 'portfolio', label: '분류 현황', icon: <Shield size={14} /> },
              { key: 'migration', label: '이동 행렬', icon: <ChevronRight size={14} /> },
              { key: 'gap',       label: '충당금 부족', icon: <AlertTriangle size={14} /> },
            ].map(({ key, label, icon }) => (
              <button
                key={key}
                onClick={() => handleTabChange(key as typeof tab)}
                className={`flex items-center gap-1.5 py-3 text-sm font-medium border-b-2 transition-colors ${
                  tab === key
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {icon}{label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {/* 분류 현황 탭 */}
          {tab === 'portfolio' && portfolio && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-6">
                {/* 파이차트 */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">분류별 비중 (잔액 기준)</h3>
                  <ResponsiveContainer width="100%" height={240}>
                    <PieChart>
                      <Pie
                        data={portfolio.by_classification}
                        dataKey="exposure"
                        nameKey="label_ko"
                        cx="50%"
                        cy="50%"
                        outerRadius={90}
                        label={({ label_ko, exposure_share }) =>
                          exposure_share > 2 ? `${label_ko} ${exposure_share.toFixed(1)}%` : ''
                        }
                      >
                        {portfolio.by_classification.map((entry, i) => (
                          <Cell key={i} fill={CLASS_COLORS[entry.classification] || '#94a3b8'} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v: number) => fmtAmt(v)} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                {/* 바차트 — 충당금 */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">분류별 충당금 현황</h3>
                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={portfolio.by_classification}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="label_ko" tick={{ fontSize: 11 }} />
                      <YAxis tickFormatter={(v) => `${(v / 100000000).toFixed(0)}억`} tick={{ fontSize: 11 }} />
                      <Tooltip formatter={(v: number) => fmtAmt(v)} />
                      <Bar dataKey="required_provision" name="필요충당금" fill="#00BFA5" radius={[4,4,0,0]} />
                      <Bar dataKey="existing_provision" name="기존충당금" fill="#22c55e" radius={[4,4,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* 분류 테이블 */}
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-left">
                    <th className="pb-2 text-gray-500 font-medium">분류</th>
                    <th className="pb-2 text-right text-gray-500 font-medium">건수</th>
                    <th className="pb-2 text-right text-gray-500 font-medium">잔액</th>
                    <th className="pb-2 text-right text-gray-500 font-medium">비중</th>
                    <th className="pb-2 text-right text-gray-500 font-medium">적립률</th>
                    <th className="pb-2 text-right text-gray-500 font-medium">필요충당금</th>
                    <th className="pb-2 text-right text-gray-500 font-medium">부족액</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio.by_classification.map((item) => (
                    <tr key={item.classification} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-2.5">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${CLASS_BG[item.classification] || 'bg-gray-100 text-gray-700'}`}>
                          {item.label_ko}
                        </span>
                      </td>
                      <td className="py-2.5 text-right text-gray-700">{item.count.toLocaleString()}</td>
                      <td className="py-2.5 text-right text-gray-700">{fmtAmt(item.exposure)}</td>
                      <td className="py-2.5 text-right text-gray-700">{fmtPct(item.exposure_share)}</td>
                      <td className="py-2.5 text-right text-gray-700">{fmtPct(item.provision_rate * 100)}</td>
                      <td className="py-2.5 text-right text-gray-700">{fmtAmt(item.required_provision)}</td>
                      <td className={`py-2.5 text-right font-medium ${item.provision_gap > 0 ? 'text-red-600' : 'text-green-600'}`}>
                        {item.provision_gap > 0 ? '+' : ''}{fmtAmt(item.provision_gap)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* 이동 행렬 탭 */}
          {tab === 'migration' && (
            <div>
              {!migration ? (
                <div className="text-center py-12 text-gray-400">로딩 중...</div>
              ) : migration.error ? (
                <div className="text-center py-12 text-gray-400">{migration.error}</div>
              ) : (
                <div>
                  <p className="text-sm text-gray-500 mb-4">
                    {migration.from_date} → {migration.to_date} 분류 변동 현황 (건수 기준)
                  </p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs border-collapse">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="border border-gray-200 px-3 py-2 text-left font-medium text-gray-600">
                            이전↓ / 현재→
                          </th>
                          {migration.class_keys.map((ck: string) => (
                            <th key={ck} className="border border-gray-200 px-3 py-2 text-center font-medium"
                              style={{ color: CLASS_COLORS[ck] }}>
                              {classLabels[ck] || ck}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {migration.matrix.map((row: MigrationRow) => (
                          <tr key={row.from_class} className="hover:bg-gray-50">
                            <td className="border border-gray-200 px-3 py-2 font-medium"
                              style={{ color: CLASS_COLORS[row.from_class] }}>
                              {row.from_label}
                            </td>
                            {migration.class_keys.map((ck: string) => {
                              const cell = row[ck];
                              const cnt = cell?.count || 0;
                              const isDiag = row.from_class === ck;
                              const isDown = migration.class_keys.indexOf(ck) > migration.class_keys.indexOf(row.from_class);
                              return (
                                <td key={ck}
                                  className={`border border-gray-200 px-3 py-2 text-center ${
                                    isDiag ? 'bg-blue-50 font-medium text-blue-700' :
                                    isDown && cnt > 0 ? 'bg-red-50 text-red-700' :
                                    !isDiag && cnt > 0 ? 'bg-green-50 text-green-700' : 'text-gray-400'
                                  }`}>
                                  {cnt > 0 ? cnt : '-'}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="text-xs text-gray-400 mt-3">
                    파란색: 유지, 빨간색: 하향, 초록색: 상향
                  </p>
                </div>
              )}
            </div>
          )}

          {/* 충당금 부족 탭 */}
          {tab === 'gap' && (
            <div>
              {!gapData ? (
                <div className="text-center py-12 text-gray-400">로딩 중...</div>
              ) : (
                <div className="space-y-4">
                  <div className="p-4 bg-red-50 rounded-lg border border-red-200">
                    <p className="text-sm font-semibold text-red-700">
                      총 충당금 부족액: {fmtAmt(gapData.total_provision_gap)}
                    </p>
                    <p className="text-xs text-red-600 mt-1">아래는 부족액 상위 20개 여신</p>
                  </div>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200 text-left">
                        <th className="pb-2 text-gray-500 font-medium">기업명</th>
                        <th className="pb-2 text-gray-500 font-medium">업종</th>
                        <th className="pb-2 text-gray-500 font-medium">분류</th>
                        <th className="pb-2 text-right text-gray-500 font-medium">익스포저</th>
                        <th className="pb-2 text-right text-gray-500 font-medium">필요충당금</th>
                        <th className="pb-2 text-right text-gray-500 font-medium">기존충당금</th>
                        <th className="pb-2 text-right text-gray-500 font-medium">부족액</th>
                      </tr>
                    </thead>
                    <tbody>
                      {gapData.top20_facilities.map((item: any, i: number) => (
                        <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                          <td className="py-2 font-medium text-gray-800">{item.company_name}</td>
                          <td className="py-2 text-gray-500 text-xs">{item.industry}</td>
                          <td className="py-2">
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${CLASS_BG[item.classification] || ''}`}>
                              {item.label_ko}
                            </span>
                          </td>
                          <td className="py-2 text-right text-gray-700">{fmtAmt(item.exposure)}</td>
                          <td className="py-2 text-right text-gray-700">{fmtAmt(item.required_provision)}</td>
                          <td className="py-2 text-right text-gray-700">{fmtAmt(item.existing_provision)}</td>
                          <td className="py-2 text-right font-semibold text-red-600">{fmtAmt(item.provision_gap)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 월별 추이 */}
      {trend.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <TrendingDown size={16} className="text-red-500" />
            분류별 월별 추이 (건수)
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={trend.slice(-12)}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="base_date" tickFormatter={(v) => v.slice(0, 7)} tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              {classKeys.map((ck) => (
                <Bar key={ck} dataKey={`${ck}.count`} name={classLabels[ck]} stackId="a"
                  fill={CLASS_COLORS[ck]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
