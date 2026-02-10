import React, { useEffect, useState } from 'react';
import { Newspaper, TrendingDown, AlertCircle, MessageSquare } from 'lucide-react';
import { Card, StatCard } from '../../components';
import { ewsAdvancedApi } from '../../utils/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';

interface Props { region: string }

export default function EWSNewsSentiment({ region }: Props) {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>(null);
  const [feed, setFeed] = useState<any[]>([]);
  const [customerData, setCustomerData] = useState<any>(null);
  const [sentimentFilter, setSentimentFilter] = useState<string>('');

  useEffect(() => { loadData(); }, [region]);
  useEffect(() => { loadFeed(); }, [region, sentimentFilter]);

  const loadData = async () => {
    setLoading(true);
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
    try {
      const res = await ewsAdvancedApi.getNewsCustomer(cid);
      setCustomerData(res.data);
    } catch (e) { console.error(e); }
  };

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

      {/* 추이 차트 */}
      <div className="grid grid-cols-2 gap-6">
        <Card title="월별 감성 추이">
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={dashboard?.trend || []} margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} domain={[-1, 1]} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="avg_sentiment" name="평균 감성" stroke="#3b82f6" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="avg_negative_ratio" name="부정비율" stroke="#ef4444" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card title="월별 기사량">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={dashboard?.trend || []} margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="article_count" name="기사 수" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* 고객 상세 */}
      {customerData && (
        <Card title={`뉴스 분석: ${customerData.customer_name}`}
          headerAction={<button onClick={() => setCustomerData(null)} className="text-sm text-gray-500 hover:text-gray-700">닫기</button>}>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <h4 className="text-sm font-semibold mb-2">월별 감성 추이</h4>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={customerData.monthly || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fontSize: 9 }} />
                  <YAxis tick={{ fontSize: 9 }} domain={[-1, 1]} />
                  <Tooltip />
                  <Line type="monotone" dataKey="avg_sentiment" name="감성" stroke="#3b82f6" />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div>
              <h4 className="text-sm font-semibold mb-2">최근 기사</h4>
              <div className="space-y-2 max-h-52 overflow-y-auto">
                {(customerData.recent_articles || []).map((a: any, i: number) => (
                  <div key={i} className={`p-2 rounded border text-xs ${
                    a.sentiment < -0.2 ? 'border-red-200 bg-red-50' :
                    a.sentiment > 0.2 ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-gray-50'
                  }`}>
                    <div className="flex justify-between">
                      <span className="font-medium">{a.headline}</span>
                      <span className={a.sentiment < 0 ? 'text-red-600' : 'text-green-600'}>{a.sentiment?.toFixed(2)}</span>
                    </div>
                    <div className="text-gray-400 mt-1">{a.date} | {a.source} | {a.category}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* 뉴스 피드 */}
      <Card title="뉴스 피드" headerAction={
        <div className="flex gap-1">
          {['', 'negative', 'positive'].map(f => (
            <button key={f} onClick={() => setSentimentFilter(f)}
              className={`px-3 py-1 rounded text-xs font-medium ${sentimentFilter === f ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
              {f === '' ? '전체' : f === 'negative' ? '부정' : '긍정'}
            </button>
          ))}
        </div>
      }>
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {feed.map((item: any, i: number) => (
            <div key={i} className={`flex items-start justify-between p-3 rounded-lg border ${
              item.sentiment < -0.2 ? 'border-red-200 bg-red-50' :
              item.sentiment > 0.2 ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-gray-50'
            }`}>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">{item.category}</span>
                  <span className="text-xs text-gray-400">{item.date}</span>
                  <span className="text-xs text-gray-400">{item.source}</span>
                </div>
                <p className="text-sm font-medium text-gray-900">{item.headline}</p>
                <button onClick={() => loadCustomer(item.customer_id)}
                  className="text-xs text-blue-600 hover:underline mt-1">{item.customer_name} 상세보기</button>
              </div>
              <span className={`text-sm font-semibold px-2 ${
                item.sentiment < -0.2 ? 'text-red-600' : item.sentiment > 0.2 ? 'text-green-600' : 'text-gray-500'
              }`}>{item.sentiment?.toFixed(2)}</span>
            </div>
          ))}
          {feed.length === 0 && <p className="text-center text-gray-400 py-8">뉴스 데이터가 없습니다.</p>}
        </div>
      </Card>
    </div>
  );
}
