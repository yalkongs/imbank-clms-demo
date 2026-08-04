import React, { useEffect, useState } from 'react';
import { Newspaper, TrendingDown, AlertCircle, MessageSquare, MousePointerClick } from 'lucide-react';
import { Card, StatCard } from '../../components';
import { ewsAdvancedApi } from '../../utils/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';

interface Props { region: string }

/**
 * 뉴스/감성 탭 - 마스터·디테일 구조 (공급망 탭과 동일한 패턴).
 * 뉴스 피드가 최하단에 있고 '상세보기' 클릭 시 분석 카드가 뷰포트 밖 위쪽에
 * 삽입되던 구조를, 좌측 피드 → 우측 즉시 기업 분석 표시로 재배치.
 */
export default function EWSNewsSentiment({ region }: Props) {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>(null);
  const [feed, setFeed] = useState<any[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [customerData, setCustomerData] = useState<any>(null);
  const [sentimentFilter, setSentimentFilter] = useState<string>('');

  useEffect(() => { loadData(); }, [region]);
  useEffect(() => { loadFeed(); }, [region, sentimentFilter]);

  const loadData = async () => {
    setLoading(true);
    setSelectedId('');
    setCustomerData(null);
    try {
      const r = region || undefined;
      const res = await ewsAdvancedApi.getNewsDashboard(r);
      setDashboard(res.data);
    } catch (e) {
      console.error(e);
      setDashboard(null);
    } finally { setLoading(false); }
  };

  const loadFeed = async () => {
    try {
      const params: any = {};
      if (region) params.region = region;
      if (sentimentFilter) params.sentiment = sentimentFilter;
      const res = await ewsAdvancedApi.getNewsFeed(params);
      setFeed(res.data.feed || []);
    } catch (e) {
      console.error(e);
      setFeed([]);
    }
  };

  const loadCustomer = async (cid: string) => {
    setSelectedId(cid);
    try {
      const res = await ewsAdvancedApi.getNewsCustomer(cid);
      setCustomerData(res.data);
    } catch (e) { console.error(e); }
  };

  const closeDetail = () => { setSelectedId(''); setCustomerData(null); };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" /></div>;

  return (
    <div className="space-y-6">
      {/* 요약 */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard title="모니터링 기업" value={dashboard?.monitored_customers || 0}
          icon={<Newspaper size={22} />} color="blue" />
        <StatCard title="전체 감성지수" value={dashboard?.overall_sentiment?.toFixed(3) || '0'}
          subtitle={dashboard?.overall_sentiment < 0 ? '부정 우세' : '긍정 우세'}
          icon={<MessageSquare size={22} />} color={dashboard?.overall_sentiment < 0 ? 'red' : 'green'} />
        <StatCard title="부정 기사 비율" value={`${((dashboard?.avg_negative_ratio || 0) * 100).toFixed(1)}%`}
          icon={<TrendingDown size={22} />} color="yellow" />
        <StatCard title="부정감성 경보" value={dashboard?.negative_alert_count || 0}
          subtitle="감성지수 -0.3 미만" icon={<AlertCircle size={22} />} color="red" />
      </div>

      {/* 마스터(좌: 뉴스 피드) · 디테일(우: 기업 뉴스 분석) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        <Card title={`뉴스 피드 (${feed.length})`} className="lg:col-span-1"
          headerAction={
            <div className="flex gap-1">
              {['', 'negative', 'positive'].map(f => (
                <button key={f} onClick={() => setSentimentFilter(f)}
                  className={`px-2.5 py-1 rounded text-xs font-medium ${sentimentFilter === f ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                  {f === '' ? '전체' : f === 'negative' ? '부정' : '긍정'}
                </button>
              ))}
            </div>
          }>
          <p className="text-[11px] text-gray-400 mb-2">기사를 선택하면 우측에 해당 기업의 뉴스 분석이 표시됩니다</p>
          <div className="max-h-[560px] overflow-y-auto space-y-2">
            {feed.map((item: any, i: number) => {
              const selected = selectedId === item.customer_id;
              return (
                <button
                  key={i}
                  onClick={() => loadCustomer(item.customer_id)}
                  className={`w-full text-left p-3 rounded-lg border transition-colors ${
                    selected ? 'ring-1 ring-blue-300 border-blue-300 bg-blue-50' :
                    item.sentiment < -0.2 ? 'border-red-200 bg-red-50 hover:bg-red-100/60' :
                    item.sentiment > 0.2 ? 'border-green-200 bg-green-50 hover:bg-green-100/60' :
                    'border-gray-200 bg-gray-50 hover:bg-gray-100'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="flex-none px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-[11px]">{item.category}</span>
                      <span className="text-[11px] text-gray-400 truncate">{item.date} · {item.source}</span>
                    </div>
                    <span className={`flex-none text-xs font-semibold tabular ${
                      item.sentiment < -0.2 ? 'text-red-600' : item.sentiment > 0.2 ? 'text-green-600' : 'text-gray-500'
                    }`}>{item.sentiment?.toFixed(2)}</span>
                  </div>
                  <p className="text-sm font-medium text-gray-900 leading-snug">{item.headline}</p>
                  <p className="text-xs text-blue-600 mt-1">{item.customer_name}</p>
                </button>
              );
            })}
            {feed.length === 0 && <p className="text-center text-gray-400 py-8 text-sm">뉴스 데이터가 없습니다</p>}
          </div>
        </Card>

        {/* 상세 (선택 전에는 전체 추이) */}
        <div className="lg:col-span-2 space-y-6">
          {customerData ? (
            <Card title={`뉴스 분석: ${customerData.customer_name}`}
              headerAction={<button onClick={closeDetail} className="text-sm text-gray-500 hover:text-gray-700">닫기</button>}>
              <div className="space-y-5">
                <div>
                  <h4 className="text-sm font-semibold mb-2">월별 감성 추이</h4>
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={customerData.monthly || []}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="month" tick={{ fontSize: 9 }} />
                      <YAxis tick={{ fontSize: 9 }} domain={[-1, 1]} />
                      <Tooltip />
                      <Line type="monotone" dataKey="avg_sentiment" name="감성" stroke="#00BFA5" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <div>
                  <h4 className="text-sm font-semibold mb-2">최근 기사</h4>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {(customerData.recent_articles || []).map((a: any, i: number) => (
                      <div key={i} className={`p-2.5 rounded border text-xs ${
                        a.sentiment < -0.2 ? 'border-red-200 bg-red-50' :
                        a.sentiment > 0.2 ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-gray-50'
                      }`}>
                        <div className="flex justify-between gap-2">
                          <span className="font-medium">{a.headline}</span>
                          <span className={`flex-none ${a.sentiment < 0 ? 'text-red-600' : 'text-green-600'}`}>{a.sentiment?.toFixed(2)}</span>
                        </div>
                        <div className="text-gray-400 mt-1">{a.date} | {a.source} | {a.category}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          ) : (
            <>
              <Card title="월별 감성 추이">
                <ResponsiveContainer width="100%" height={230}>
                  <LineChart data={dashboard?.trend || []} margin={{ left: -10, right: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} domain={[-1, 1]} />
                    <Tooltip />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Line type="monotone" dataKey="avg_sentiment" name="평균 감성" stroke="#00BFA5" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="avg_negative_ratio" name="부정비율" stroke="#ef4444" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </Card>
              <Card title="월별 기사량">
                <ResponsiveContainer width="100%" height={230}>
                  <BarChart data={dashboard?.trend || []} margin={{ left: -10, right: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Bar dataKey="article_count" name="기사 수" fill="#00BFA5" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
                <div className="mt-3 flex items-center justify-center gap-2 text-sm text-gray-400 border-t border-gray-100 pt-3">
                  <MousePointerClick size={15} />
                  좌측 피드에서 기사를 선택하면 해당 기업의 뉴스 분석이 여기에 표시됩니다
                </div>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
