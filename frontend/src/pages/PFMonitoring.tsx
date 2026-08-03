import React, { useEffect, useState } from 'react';
import { Building, AlertTriangle, Scale, Landmark } from 'lucide-react';
import { Card, StatCard, RegionFilter } from '../components';
import { COLORS } from '../components/Charts';
import { formatAmount, formatPercent, formatNumber } from '../utils/format';
import axios from 'axios';

/**
 * 부동산PF 사업장 관리
 *
 * 2027 시행 예정인 PF 제도 개편은 사업장 자기자본비율에 위험가중치·충당금을
 * 연동한다(자기자본 20% 수준 유도). 사업장 단위로 공정률·분양률·자기자본비율을
 * 감시하고, 제도 적용 시 자본·충당금 영향을 시뮬레이션한다.
 *
 * 공정률-분양률 괴리는 PF 부실의 대표 선행신호 — 골조는 올라가는데 분양이 안 되면
 * 준공 시점에 상환재원이 없다.
 */

export default function PFMonitoring() {
  const [dashboard, setDashboard] = useState<any>(null);
  const [projects, setProjects] = useState<any[]>([]);
  const [simulation, setSimulation] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [region, setRegion] = useState('');
  const [tab, setTab] = useState<'projects' | 'simulation'>('projects');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      axios.get('/api/pf/dashboard'),
      axios.get('/api/pf/regulation-simulation'),
      axios.get('/api/pf/alerts'),
    ])
      .then(([d, s, a]) => {
        setDashboard(d.data);
        setSimulation(s.data);
        setAlerts(a.data);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    axios
      .get('/api/pf/projects', { params: region ? { region } : {} })
      .then(r => setProjects(r.data))
      .catch(console.error);
  }, [region]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">부동산PF 사업장 관리</h1>
          <p className="text-sm text-gray-500 mt-1">
            사업장 자기자본·공정·분양 상시 감시 및 2027 제도 개편 영향 시뮬레이션
          </p>
        </div>
        <RegionFilter value={region} onChange={setRegion} />
      </div>

      {/* KPI */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="PF 익스포저"
          value={formatAmount(dashboard?.total_exposure || 0, 'billion')}
          subtitle={`${formatNumber(dashboard?.project_count || 0)}개 사업장`}
          icon={<Landmark size={24} />}
          color="blue"
        />
        <StatCard
          title="워치리스트"
          value={`${dashboard?.watchlist_count || 0}곳`}
          subtitle={formatAmount(dashboard?.watchlist_exposure || 0, 'billion')}
          icon={<AlertTriangle size={24} />}
          color={(dashboard?.watchlist_count || 0) > 0 ? 'red' : 'green'}
        />
        <StatCard
          title="저자본 사업장 비중"
          value={formatPercent(dashboard?.low_equity_share || 0)}
          subtitle="자기자본비율 10% 미만"
          icon={<Scale size={24} />}
          color={(dashboard?.low_equity_share || 0) > 40 ? 'red' : 'yellow'}
        />
        <StatCard
          title="제도 적용 시 RWA 증가"
          value={`+${formatPercent(simulation?.delta?.rwa_pct || 0)}`}
          subtitle={`충당금 ${formatAmount(simulation?.delta?.provision || 0, 'billion')} 추가`}
          icon={<Building size={24} />}
          color="yellow"
        />
      </div>

      {/* 괴리 경보 */}
      {alerts.length > 0 && (
        <Card title={`공정-분양 괴리 경보 (${alerts.length}건)`}>
          <div className="space-y-2">
            {alerts.slice(0, 5).map(a => (
              <div key={a.project_id} className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <span className="status-dot is-critical" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">{a.project_name}</p>
                    <p className="text-xs text-gray-500">
                      {a.region_label} · 공정 {formatPercent(a.progress_rate)} vs 분양 {formatPercent(a.presale_rate)}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-red-600 tabular">괴리 {a.gap}%p</p>
                  <p className="text-xs text-gray-500">{formatAmount(a.exposure, 'billion')}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* 탭: 사업장 목록 / 제도 시뮬레이션 */}
      <div className="flex gap-1 border-b border-gray-200" role="tablist">
        {([['projects', '사업장 목록'], ['simulation', '2027 제도 시뮬레이션']] as const).map(([k, l]) => (
          <button
            key={k}
            role="tab"
            aria-selected={tab === k}
            onClick={() => setTab(k)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === k
                ? 'border-blue-600 text-blue-700'
                : 'border-transparent text-gray-500 hover:text-gray-800'
            }`}
          >
            {l}
          </button>
        ))}
      </div>

      {tab === 'projects' && (
        <Card title={`사업장 목록 (${projects.length}곳 · 괴리 큰 순)`}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                  <th className="py-2 pr-4">사업장</th>
                  <th className="py-2 pr-4">유형</th>
                  <th className="py-2 pr-4">지역</th>
                  <th className="py-2 pr-4 text-right">익스포저</th>
                  <th className="py-2 pr-4 text-right">자기자본비율</th>
                  <th className="py-2 pr-4 text-right">공정률</th>
                  <th className="py-2 pr-4 text-right">분양률</th>
                  <th className="py-2 pr-4 text-right">괴리</th>
                  <th className="py-2">상태</th>
                </tr>
              </thead>
              <tbody>
                {projects.map(p => (
                  <tr key={p.project_id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2.5 pr-4">
                      <p className="font-medium text-gray-900">{p.project_name}</p>
                      <p className="text-xs text-gray-400">{p.developer} · {p.constructor}</p>
                    </td>
                    <td className="py-2.5 pr-4">{p.type_label}</td>
                    <td className="py-2.5 pr-4">{p.region_label}</td>
                    <td className="py-2.5 pr-4 text-right tabular">{formatAmount(p.exposure, 'billion')}</td>
                    <td className={`py-2.5 pr-4 text-right tabular ${p.equity_ratio < 10 ? 'text-red-600 font-semibold' : ''}`}>
                      {formatPercent(p.equity_ratio)}
                    </td>
                    <td className="py-2.5 pr-4 text-right tabular">
                      {p.project_type === 'BRIDGE' ? '—' : formatPercent(p.progress_rate)}
                    </td>
                    <td className="py-2.5 pr-4 text-right tabular">
                      {p.project_type === 'BRIDGE' ? '—' : formatPercent(p.presale_rate)}
                    </td>
                    <td className={`py-2.5 pr-4 text-right tabular ${p.gap_alert ? 'text-red-600 font-bold' : ''}`}>
                      {p.project_type === 'BRIDGE' ? '—' : `${p.gap}%p`}
                    </td>
                    <td className="py-2.5">
                      {p.status === 'WATCHLIST' ? (
                        <span className="badge-alert inline-block px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs font-medium">
                          워치리스트
                        </span>
                      ) : (
                        <span className="inline-block px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full text-xs">정상</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {tab === 'simulation' && simulation && (
        <div className="space-y-6">
          <Card title="자기자본비율 구간별 제도 영향">
            <p className="text-xs text-amber-600 mb-4">⚠ {simulation.note}</p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                    <th className="py-2 pr-4">자기자본비율 구간</th>
                    <th className="py-2 pr-4 text-right">사업장</th>
                    <th className="py-2 pr-4 text-right">익스포저</th>
                    <th className="py-2 pr-4 text-right">위험가중치</th>
                    <th className="py-2 pr-4 text-right">충당금률</th>
                    <th className="py-2 pr-4 text-right">시나리오 RWA</th>
                    <th className="py-2 text-right">시나리오 충당금</th>
                  </tr>
                </thead>
                <tbody>
                  {simulation.bands.map((b: any) => (
                    <tr key={b.band} className="border-b border-gray-50">
                      <td className="py-2.5 pr-4 font-medium">{b.band}</td>
                      <td className="py-2.5 pr-4 text-right tabular">{b.count}곳</td>
                      <td className="py-2.5 pr-4 text-right tabular">{formatAmount(b.exposure, 'billion')}</td>
                      <td className={`py-2.5 pr-4 text-right tabular ${b.risk_weight >= 1.5 ? 'text-red-600 font-semibold' : ''}`}>
                        {Math.round(b.risk_weight * 100)}%
                      </td>
                      <td className="py-2.5 pr-4 text-right tabular">{formatPercent(b.provision_rate * 100)}</td>
                      <td className="py-2.5 pr-4 text-right tabular">{formatAmount(b.scenario_rwa, 'billion')}</td>
                      <td className="py-2.5 text-right tabular">{formatAmount(b.scenario_provision, 'billion')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <div className="grid grid-cols-3 gap-4">
            <Card title="현행 기준">
              <p className="text-2xl font-bold tabular">{formatAmount(simulation.current.rwa, 'billion')}</p>
              <p className="text-xs text-gray-500 mt-1">RWA (일률 RW {Math.round(simulation.current.risk_weight * 100)}%)</p>
              <p className="text-sm tabular mt-3">{formatAmount(simulation.current.provision, 'billion')}</p>
              <p className="text-xs text-gray-500">충당금</p>
            </Card>
            <Card title="제도 적용 시나리오">
              <p className="text-2xl font-bold tabular text-amber-600">{formatAmount(simulation.scenario.rwa, 'billion')}</p>
              <p className="text-xs text-gray-500 mt-1">RWA (구간별 차등)</p>
              <p className="text-sm tabular mt-3">{formatAmount(simulation.scenario.provision, 'billion')}</p>
              <p className="text-xs text-gray-500">충당금</p>
            </Card>
            <Card title="증감">
              <p className="text-2xl font-bold tabular text-red-600">+{formatPercent(simulation.delta.rwa_pct)}</p>
              <p className="text-xs text-gray-500 mt-1">RWA 증가율</p>
              <p className="text-sm tabular mt-3 text-red-600">+{formatAmount(simulation.delta.provision, 'billion')}</p>
              <p className="text-xs text-gray-500">충당금 추가 적립</p>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
