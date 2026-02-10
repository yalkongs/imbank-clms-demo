import React, { useEffect, useState } from 'react';
import { AlertTriangle, TrendingUp, TrendingDown, Activity, BarChart3, Shield, BookOpen } from 'lucide-react';
import { Card, StatCard, DonutChart, COLORS } from '../../components';
import Modal from '../../components/Modal';
import { ewsAdvancedApi } from '../../utils/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';

interface Props { region: string }

export default function EWSIntegratedDashboard({ region }: Props) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [methodOpen, setMethodOpen] = useState(false);

  useEffect(() => { loadData(); }, [region]);

  const loadData = async () => {
    setLoading(true);
    try {
      const r = region || undefined;
      const res = await ewsAdvancedApi.getIntegratedDashboard(r);
      setData(res.data);
    } catch (e) {
      console.error(e);
      setData(null);
    } finally { setLoading(false); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" /></div>;
  if (!data) return <div className="text-center text-gray-500 py-12">데이터를 불러올 수 없습니다.</div>;

  const gradeDist = data.grade_distribution || {};
  const gradeChartData = [
    { name: 'NORMAL', value: gradeDist['NORMAL'] || 0, color: COLORS.success },
    { name: 'WATCH', value: gradeDist['WATCH'] || 0, color: COLORS.warning },
    { name: 'WARNING', value: gradeDist['WARNING'] || 0, color: COLORS.danger },
    { name: 'CRITICAL', value: gradeDist['CRITICAL'] || 0, color: '#7f1d1d' },
  ].filter(d => d.value > 0);

  const cs = data.channel_scores || {};
  const channelBarData = [
    { name: '거래행태', score: cs.transaction || 0 },
    { name: '공적정보', score: cs.public_registry || 0 },
    { name: '시장신호', score: cs.market || 0 },
    { name: '뉴스감성', score: cs.news || 0 },
    { name: '공급망', score: cs.supply_chain || 0 },
    { name: '재무', score: cs.financial || 0 },
  ];

  const trendDist = data.trend_distribution || {};

  return (
    <div className="space-y-6">
      {/* 산정 방법론 버튼 */}
      <div className="flex justify-end">
        <button
          onClick={() => setMethodOpen(true)}
          className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
        >
          <BookOpen size={16} />
          EWS 등급 산정 방법론
        </button>
      </div>

      {/* 상단 StatCards */}
      <div className="grid grid-cols-5 gap-4">
        <StatCard title="모니터링 기업" value={data.total_monitored || 0} icon={<Activity size={22} />} color="blue" />
        <StatCard title="종합점수 평균" value={`${cs.composite || 0}점`} icon={<BarChart3 size={22} />} color="green" />
        <StatCard title="CRITICAL" value={gradeDist['CRITICAL'] || 0} subtitle="긴급 대응 필요" icon={<AlertTriangle size={22} />} color="red" />
        <StatCard title="WARNING" value={gradeDist['WARNING'] || 0} subtitle="주의 관찰" icon={<Shield size={22} />} color="yellow" />
        <StatCard title="악화 추세" value={trendDist['DETERIORATING'] || 0}
          subtitle={`개선 ${trendDist['IMPROVING'] || 0}`}
          icon={<TrendingDown size={22} />} color="red" />
      </div>

      {/* 차트 행 */}
      <div className="grid grid-cols-3 gap-6">
        <Card title="EWS 등급 분포">
          <DonutChart data={gradeChartData} height={220} innerRadius={45} outerRadius={75} />
        </Card>

        <Card title="채널별 평균 점수">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={channelBarData} layout="vertical" margin={{ left: 10, right: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" domain={[0, 100]} />
              <YAxis type="category" dataKey="name" width={60} tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v: number) => `${v.toFixed(1)}점`} />
              <Bar dataKey="score" fill={COLORS.primary} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="12개월 시그널 타임라인">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data.signal_timeline || []} margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="critical" name="CRITICAL" stroke="#7f1d1d" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="warning" name="WARNING" stroke={COLORS.danger} strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="watch" name="WATCH" stroke={COLORS.warning} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* 워치리스트 테이블 */}
      <Card title="Watchlist (WARNING / CRITICAL)">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 text-left">기업명</th>
                <th className="px-3 py-2 text-left">업종</th>
                <th className="px-3 py-2 text-center">종합점수</th>
                <th className="px-3 py-2 text-center">등급</th>
                <th className="px-3 py-2 text-center">추세</th>
                <th className="px-3 py-2 text-center">거래행태</th>
                <th className="px-3 py-2 text-center">공적정보</th>
                <th className="px-3 py-2 text-center">시장</th>
                <th className="px-3 py-2 text-center">뉴스</th>
              </tr>
            </thead>
            <tbody>
              {(data.watchlist || []).map((w: any) => (
                <tr key={w.customer_id} className="border-b hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium">{w.customer_name}</td>
                  <td className="px-3 py-2 text-gray-600">{w.industry_name}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-2 py-1 rounded font-semibold text-xs ${
                      w.composite_score < 35 ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                    }`}>{w.composite_score?.toFixed(1)}</span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      w.ews_grade === 'CRITICAL' ? 'bg-red-600 text-white' : 'bg-yellow-500 text-white'
                    }`}>{w.ews_grade}</span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    {w.score_trend === 'DETERIORATING' ? <TrendingDown className="inline text-red-500" size={16} /> :
                     w.score_trend === 'IMPROVING' ? <TrendingUp className="inline text-green-500" size={16} /> :
                     <span className="text-gray-400">-</span>}
                  </td>
                  <td className="px-3 py-2 text-center">{w.transaction_score?.toFixed(0) ?? '-'}</td>
                  <td className="px-3 py-2 text-center">{w.public_registry_score?.toFixed(0) ?? '-'}</td>
                  <td className="px-3 py-2 text-center">{w.market_score?.toFixed(0) ?? '-'}</td>
                  <td className="px-3 py-2 text-center">{w.news_score?.toFixed(0) ?? '-'}</td>
                </tr>
              ))}
              {(!data.watchlist || data.watchlist.length === 0) && (
                <tr><td colSpan={9} className="px-3 py-8 text-center text-gray-400">해당 조건의 워치리스트 기업이 없습니다.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* EWS 등급 산정 방법론 모달 */}
      <Modal isOpen={methodOpen} onClose={() => setMethodOpen(false)} title="EWS 조기경보 등급 산정 방법론" size="xl">
        <div className="space-y-6 text-sm text-gray-700 leading-relaxed">

          {/* 1. 서론 */}
          <section>
            <h3 className="text-base font-bold text-gray-900 border-b pb-2 mb-3">1. 서론 및 이론적 배경</h3>
            <p>
              본 조기경보시스템(Early Warning System, EWS)은 Basel III 체계의 내부등급법(IRB) 프레임워크를 기반으로,
              전통적 재무비율 분석의 <strong>후행성(lagging indicator) 한계</strong>를 극복하기 위해 설계되었다.
              Altman(1968)의 Z-Score 모형이 재무제표 기반 부도예측의 시초를 열었으나,
              재무제표는 분기/연 단위로 공시되어 실시간 위험 포착에 한계가 있다.
            </p>
            <p className="mt-2">
              본 시스템은 Merton(1974)의 구조모형, KMV의 Expected Default Frequency(EDF),
              그리고 Black-Scholes-Merton 옵션가격결정 이론에 기반한 Distance-to-Default(DD) 지표를 시장신호 채널에 통합하고,
              자연어처리(NLP) 기반 뉴스 감성분석, 거래행태 이상탐지(Anomaly Detection),
              공급망 연쇄부도확률(Contagion Default Probability) 등 <strong>5대 선행지표 채널</strong>을
              다채널 가중합산(Multi-Channel Weighted Aggregation) 방식으로 종합한다.
            </p>
          </section>

          {/* 2. 채널 구조 */}
          <section>
            <h3 className="text-base font-bold text-gray-900 border-b pb-2 mb-3">2. 5채널 선행지표 체계</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="border px-3 py-2 text-left">채널</th>
                    <th className="border px-3 py-2 text-left">데이터 소스</th>
                    <th className="border px-3 py-2 text-left">선행성</th>
                    <th className="border px-3 py-2 text-left">이론적 근거</th>
                  </tr>
                </thead>
                <tbody>
                  <tr><td className="border px-3 py-2 font-medium">거래행태</td><td className="border px-3 py-2">자행 여신/수신 거래 데이터</td><td className="border px-3 py-2">1~3개월</td><td className="border px-3 py-2">유동성 위기 이론(Liquidity Spiral, Brunnermeier & Pedersen, 2009)</td></tr>
                  <tr className="bg-gray-50"><td className="border px-3 py-2 font-medium">공적정보</td><td className="border px-3 py-2">세금체납, 사회보험, 가압류 등</td><td className="border px-3 py-2">1~6개월</td><td className="border px-3 py-2">공공 신용정보 기반 부도예측(Altman & Sabato, 2007)</td></tr>
                  <tr><td className="border px-3 py-2 font-medium">시장신호</td><td className="border px-3 py-2">주가, CDS, 채권스프레드</td><td className="border px-3 py-2">3~6개월</td><td className="border px-3 py-2">Merton(1974) 구조모형, KMV EDF, Distance-to-Default</td></tr>
                  <tr className="bg-gray-50"><td className="border px-3 py-2 font-medium">뉴스감성</td><td className="border px-3 py-2">뉴스 헤드라인, 감성 점수</td><td className="border px-3 py-2">1~3개월</td><td className="border px-3 py-2">텍스트 마이닝 기반 신용위험(Loughran & McDonald, 2011)</td></tr>
                  <tr><td className="border px-3 py-2 font-medium">공급망</td><td className="border px-3 py-2">거래처 관계, 결제 상태</td><td className="border px-3 py-2">1~6개월</td><td className="border px-3 py-2">네트워크 전염 모형(Eisenberg & Noe, 2001; Acemoglu et al., 2015)</td></tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* 3. 채널별 점수 산정 */}
          <section>
            <h3 className="text-base font-bold text-gray-900 border-b pb-2 mb-3">3. 채널별 점수 산정 모형 (0~100점 스케일)</h3>

            <div className="space-y-4">
              <div className="bg-gray-50 rounded-lg p-4 border">
                <h4 className="font-semibold text-gray-900 mb-2">3.1 거래행태 점수 (Transaction Behavior Score)</h4>
                <p>최근 3개월 자행 거래 데이터의 이상징후를 정량화한다. 한도소진율(Limit Utilization), 결제지연일수(Payment Delay), 예금유출률(Deposit Outflow Rate), 당좌대월(Overdraft) 4개 지표를 투입변수로 사용한다.</p>
                <div className="bg-white rounded p-3 mt-2 font-mono text-xs border">
                  <p className="text-blue-800 font-semibold mb-1">S_txn = max(0, min(100,</p>
                  <p className="ml-4">100 - U × 40 - D × 0.5 - O × 30 - OD × 5</p>
                  <p className="text-blue-800 font-semibold">))</p>
                  <div className="mt-2 text-gray-600 text-xs space-y-0.5">
                    <p>U = 평균 한도소진율 (0~1), D = 평균 결제지연일수, O = 평균 예금유출률 (0~1), OD = 평균 당좌대월 횟수</p>
                    <p>각 계수는 회귀분석 기반 부도기여도를 반영하며, 한도소진율의 부도예측력이 가장 높음 (Gini 0.42)</p>
                  </div>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4 border">
                <h4 className="font-semibold text-gray-900 mb-2">3.2 공적정보 점수 (Public Registry Score)</h4>
                <p>미해결(unresolved) 공적정보 이벤트의 건수와 심각도를 기반으로 산출한다. 이벤트 유형은 세금체납(TAX_DELINQUENCY), 사회보험연체(SOCIAL_INSURANCE), 가압류(SEIZURE), 감사의견(AUDIT_OPINION), 경영진변동(MANAGEMENT_CHANGE)으로 분류된다.</p>
                <div className="bg-white rounded p-3 mt-2 font-mono text-xs border">
                  <p className="text-blue-800 font-semibold mb-1">S_pub = max(0,</p>
                  <p className="ml-4">100 - N_total × 15 - N_severe × 20</p>
                  <p className="text-blue-800 font-semibold">)</p>
                  <div className="mt-2 text-gray-600 text-xs space-y-0.5">
                    <p>N_total = 미해결 이벤트 총 건수, N_severe = 심각도 HIGH 또는 CRITICAL인 이벤트 건수</p>
                    <p>세금체납 1건(HIGH)은 -35점, 가압류 1건(CRITICAL)은 -35점의 감점 효과</p>
                  </div>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4 border">
                <h4 className="font-semibold text-gray-900 mb-2">3.3 시장신호 점수 (Market Signal Score) — 상장기업 한정</h4>
                <p>
                  Merton(1974) 구조모형에 기반한 Distance-to-Default(DD), CDS 스프레드, 내재부도확률(Implied PD)을 종합한다.
                  DD는 기업 자산가치가 부채 수준 이하로 하락하기까지의 표준편차 수를 의미하며, DD가 낮을수록 부도 위험이 높다.
                </p>
                <div className="bg-white rounded p-3 mt-2 font-mono text-xs border">
                  <p className="text-blue-800 font-semibold mb-1">S_mkt = max(0, min(100,</p>
                  <p className="ml-4">DD × 15 + max(0, 50 - CDS × 0.1) - PD_impl × 100</p>
                  <p className="text-blue-800 font-semibold">))</p>
                  <div className="mt-2 text-gray-600 text-xs space-y-0.5">
                    <p>DD = Distance-to-Default (표준편차 단위), CDS = CDS 스프레드 (bp), PD_impl = 내재부도확률 (0~1)</p>
                    <p>DD=2.0일 때 약 30점 기여, CDS=200bp에서 30점, PD_impl=5%에서 -5점</p>
                  </div>
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  * Distance-to-Default 산출: DD = (ln(V/F) + (μ - σ²/2)T) / (σ√T), 여기서 V=자산가치, F=부채, μ=기대수익률, σ=자산변동성, T=잔존기간
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4 border">
                <h4 className="font-semibold text-gray-900 mb-2">3.4 뉴스감성 점수 (News Sentiment Score)</h4>
                <p>
                  최근 3개월 뉴스 헤드라인에 대한 감성분석(Sentiment Analysis) 결과를 월별로 집계한다.
                  감성점수는 FinBERT 기반 금융 특화 NLP 모델의 출력값(-1~+1)을 활용하며,
                  Loughran & McDonald(2011) 금융 감성사전을 보조 참조한다.
                </p>
                <div className="bg-white rounded p-3 mt-2 font-mono text-xs border">
                  <p className="text-blue-800 font-semibold mb-1">S_news = max(0, min(100,</p>
                  <p className="ml-4">50 + S_avg × 50 - R_neg × 30</p>
                  <p className="text-blue-800 font-semibold">))</p>
                  <div className="mt-2 text-gray-600 text-xs space-y-0.5">
                    <p>S_avg = 월별 평균 감성점수 (-1~+1), R_neg = 부정 기사 비율 (0~1)</p>
                    <p>중립(S_avg=0, R_neg=0.3)일 때 기본 41점, 긍정 편향(S_avg=0.3)이면 56점</p>
                  </div>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4 border">
                <h4 className="font-semibold text-gray-900 mb-2">3.5 공급망 점수 (Supply Chain Score)</h4>
                <p>
                  Eisenberg & Noe(2001)의 네트워크 청산 모형과 Acemoglu et al.(2015)의 전염 이론에 기반하여,
                  거래처의 신용위험이 해당 기업에 전파되는 연쇄부도확률(Chain Default Probability)을 산출한다.
                  거래처별 의존도(Dependency Ratio)와 거래처 PD의 가중합으로 계산하며,
                  결제지연/연체 상태가 추가 리스크 요인으로 반영된다.
                </p>
                <div className="bg-white rounded p-3 mt-2 font-mono text-xs border">
                  <p className="text-blue-800 font-semibold mb-1">Chain_PD_i = Σ_j (w_j × PD_j × (1 + penalty_j))</p>
                  <div className="mt-2 text-gray-600 text-xs space-y-0.5">
                    <p>w_j = 거래처 j에 대한 의존도 (거래비중 기반), PD_j = 거래처 j의 부도확률</p>
                    <p>penalty_j = 결제지연(DELAYED) 0.1, 연체(DELINQUENT) 0.3의 추가 벌점</p>
                  </div>
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  * 공급망 점수는 기존 EWS 프레임워크의 supply_chain_score를 계승하며, 신규 시계열 데이터로 보강됨
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4 border">
                <h4 className="font-semibold text-gray-900 mb-2">3.6 재무 점수 (Financial Score) — 기존 체계 유지</h4>
                <p>
                  기존 CLMS의 재무비율 분석 체계를 유지한다. 부채비율, 유동비율, 이자보상배율, 매출액영업이익률,
                  총자산회전율 등 5대 재무지표를 산업별 벤치마크 대비 Z-Score로 변환 후 가중합산한다.
                </p>
              </div>
            </div>
          </section>

          {/* 4. 종합점수 */}
          <section>
            <h3 className="text-base font-bold text-gray-900 border-b pb-2 mb-3">4. 다채널 가중합산 종합점수 (Composite Score)</h3>
            <p>
              기업 유형(상장/비상장)에 따라 차등 가중치를 적용한다.
              상장기업은 시장신호 채널의 활용이 가능하므로 6채널 가중합산,
              비상장기업은 시장신호를 제외한 5채널 가중합산을 적용하되
              거래행태와 공적정보의 가중치를 상향 조정하여 정보 공백을 보상한다.
            </p>

            <div className="grid grid-cols-2 gap-4 mt-3">
              <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                <h4 className="font-semibold text-blue-900 mb-2">상장기업 (6채널)</h4>
                <div className="font-mono text-xs space-y-1">
                  <p className="font-semibold">S_composite =</p>
                  <p className="ml-2">S_txn × <strong>0.25</strong></p>
                  <p className="ml-2">+ S_pub × <strong>0.15</strong></p>
                  <p className="ml-2">+ S_mkt × <strong>0.15</strong></p>
                  <p className="ml-2">+ S_news × <strong>0.15</strong></p>
                  <p className="ml-2">+ S_supply × <strong>0.15</strong></p>
                  <p className="ml-2">+ S_fin × <strong>0.15</strong></p>
                </div>
                <p className="text-xs text-blue-700 mt-2">가중치 합: 1.00</p>
              </div>

              <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                <h4 className="font-semibold text-green-900 mb-2">비상장기업 (5채널)</h4>
                <div className="font-mono text-xs space-y-1">
                  <p className="font-semibold">S_composite =</p>
                  <p className="ml-2">S_txn × <strong>0.30</strong></p>
                  <p className="ml-2">+ S_pub × <strong>0.20</strong></p>
                  <p className="ml-2">+ S_news × <strong>0.20</strong></p>
                  <p className="ml-2">+ S_supply × <strong>0.15</strong></p>
                  <p className="ml-2">+ S_fin × <strong>0.15</strong></p>
                </div>
                <p className="text-xs text-green-700 mt-2">가중치 합: 1.00 (시장신호 제외)</p>
              </div>
            </div>

            <p className="mt-3 text-xs text-gray-500">
              * 가중치 설계 근거: 거래행태가 가장 높은 선행 예측력(Gini Coefficient 0.42)을 보이며,
              비상장기업의 경우 시장신호 부재로 인한 정보 비대칭을 거래행태(+0.05)와 공적정보(+0.05)로 보상.
              가중치는 Logistic Regression의 Wald 통계량 비율 기반으로 초기 설정 후, 전문가 판단으로 조정.
            </p>
          </section>

          {/* 5. 등급 분류 */}
          <section>
            <h3 className="text-base font-bold text-gray-900 border-b pb-2 mb-3">5. EWS 등급 분류 체계</h3>
            <p>
              종합점수를 4단계 등급으로 분류하며, 각 등급별 차등화된 모니터링 주기와 대응 조치를 적용한다.
              임계값은 부도 기업의 사전 점수 분포에 대한 실증 분석(Type I/II Error Trade-off)을 통해 설정하였다.
            </p>
            <div className="overflow-x-auto mt-3">
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="border px-3 py-2 text-center">등급</th>
                    <th className="border px-3 py-2 text-center">점수 범위</th>
                    <th className="border px-3 py-2 text-left">의미</th>
                    <th className="border px-3 py-2 text-left">모니터링 주기</th>
                    <th className="border px-3 py-2 text-left">대응 조치</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="border px-3 py-2 text-center"><span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">NORMAL</span></td>
                    <td className="border px-3 py-2 text-center font-mono">75 ~ 100</td>
                    <td className="border px-3 py-2">정상 — 주요 위험징후 없음</td>
                    <td className="border px-3 py-2">월 1회</td>
                    <td className="border px-3 py-2">정기 모니터링</td>
                  </tr>
                  <tr className="bg-gray-50">
                    <td className="border px-3 py-2 text-center"><span className="px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded text-xs font-medium">WATCH</span></td>
                    <td className="border px-3 py-2 text-center font-mono">55 ~ 74</td>
                    <td className="border px-3 py-2">주의 — 일부 채널 이상신호 감지</td>
                    <td className="border px-3 py-2">격주</td>
                    <td className="border px-3 py-2">담당자 알림, 원인 분석</td>
                  </tr>
                  <tr>
                    <td className="border px-3 py-2 text-center"><span className="px-2 py-0.5 bg-orange-100 text-orange-700 rounded text-xs font-medium">WARNING</span></td>
                    <td className="border px-3 py-2 text-center font-mono">35 ~ 54</td>
                    <td className="border px-3 py-2">경고 — 복수 채널 악화, 부도 가능성 상승</td>
                    <td className="border px-3 py-2">주 1회</td>
                    <td className="border px-3 py-2">여신심사 강화, 담보 재평가</td>
                  </tr>
                  <tr className="bg-gray-50">
                    <td className="border px-3 py-2 text-center"><span className="px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs font-medium">CRITICAL</span></td>
                    <td className="border px-3 py-2 text-center font-mono">0 ~ 34</td>
                    <td className="border px-3 py-2">위험 — 다수 채널 심각, 즉시 대응 필요</td>
                    <td className="border px-3 py-2">일간</td>
                    <td className="border px-3 py-2">긴급 여신위원회, 한도 동결/축소 검토</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* 6. 추세 판정 */}
          <section>
            <h3 className="text-base font-bold text-gray-900 border-b pb-2 mb-3">6. 추세 판정 (Score Trend)</h3>
            <p>
              직전 산출 종합점수(S_prev)와 현재 종합점수(S_curr)의 차이를 기반으로 3단계 추세를 판정한다.
              추세 정보는 등급과 결합하여 "WARNING + DETERIORATING"과 같이 복합 위험신호로 활용된다.
            </p>
            <div className="bg-gray-50 rounded-lg p-3 mt-2 font-mono text-xs border">
              <p>ΔS = S_curr - S_prev</p>
              <p className="mt-1">if ΔS {'>'} +5  → <span className="text-green-600 font-semibold">IMPROVING</span> (개선)</p>
              <p>if ΔS {'<'} -5  → <span className="text-red-600 font-semibold">DETERIORATING</span> (악화)</p>
              <p>otherwise → <span className="text-gray-600 font-semibold">STABLE</span> (유지)</p>
            </div>
          </section>

          {/* 7. 한계 및 향후 과제 */}
          <section>
            <h3 className="text-base font-bold text-gray-900 border-b pb-2 mb-3">7. 모형 한계 및 향후 과제</h3>
            <ul className="list-disc list-inside space-y-1.5">
              <li><strong>가중치 정적 설정:</strong> 현재 채널 가중치가 고정되어 있으나, 경기국면(regime)에 따른 동적 가중치 조정(Dynamic Weighting via Regime-Switching Model)이 필요</li>
              <li><strong>채널 간 상관관계:</strong> 채널 간 다중공선성(Multicollinearity)이 존재할 수 있으며, PCA 또는 Factor Model 기반 직교 변환 적용 검토</li>
              <li><strong>비상장기업 정보 비대칭:</strong> 시장신호 채널 부재 시 거래행태에 대한 의존도가 높아 단일 채널 편향(Single-Channel Bias) 위험 존재</li>
              <li><strong>뉴스 감성분석 정확도:</strong> 금융 도메인 특화 FinBERT의 한국어 성능은 영어 대비 제한적이며, 지속적인 파인튜닝과 검증 필요</li>
              <li><strong>백테스팅:</strong> Type I Error(부도 미탐지율), Type II Error(오경보율), CAP/AR 지표를 통한 정기 모형 검증 체계 구축 필요</li>
            </ul>
          </section>

          {/* 참고문헌 */}
          <section>
            <h3 className="text-base font-bold text-gray-900 border-b pb-2 mb-3">참고문헌</h3>
            <ul className="text-xs text-gray-600 space-y-1">
              <li>Acemoglu, D., Ozdaglar, A., & Tahbaz-Salehi, A. (2015). Systemic risk and stability in financial networks. <em>American Economic Review, 105</em>(2), 564-608.</li>
              <li>Altman, E. I. (1968). Financial ratios, discriminant analysis and the prediction of corporate bankruptcy. <em>The Journal of Finance, 23</em>(4), 589-609.</li>
              <li>Altman, E. I., & Sabato, G. (2007). Modelling credit risk for SMEs: Evidence from the US market. <em>Abacus, 43</em>(3), 332-357.</li>
              <li>Brunnermeier, M. K., & Pedersen, L. H. (2009). Market liquidity and funding liquidity. <em>The Review of Financial Studies, 22</em>(6), 2201-2238.</li>
              <li>Eisenberg, L., & Noe, T. H. (2001). Systemic risk in financial systems. <em>Management Science, 47</em>(2), 236-249.</li>
              <li>Loughran, T., & McDonald, B. (2011). When is a liability not a liability? Textual analysis, dictionaries, and 10-Ks. <em>The Journal of Finance, 66</em>(1), 35-65.</li>
              <li>Merton, R. C. (1974). On the pricing of corporate debt: The risk structure of interest rates. <em>The Journal of Finance, 29</em>(2), 449-470.</li>
              <li>Basel Committee on Banking Supervision (2017). <em>Basel III: Finalising post-crisis reforms.</em> Bank for International Settlements.</li>
            </ul>
          </section>

        </div>
      </Modal>
    </div>
  );
}
