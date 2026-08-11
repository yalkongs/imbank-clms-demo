import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { SectionSkeleton, SectionEmpty } from '../components/AsyncSection';

const SEV_STYLE: Record<string, string> = {
  CRITICAL: 'bg-red-600 text-white',
  HIGH: 'bg-red-100 text-red-700',
  MEDIUM: 'bg-amber-100 text-amber-700',
  LOW: 'bg-gray-100 text-gray-600',
};

const TYPE_KO: Record<string, string> = {
  BEHAVIOR: '거래행태', FINANCIAL: '재무', MARKET: '시장신호',
  PUBLIC: '공적정보', NEWS: '뉴스감성', SUPPLY: '공급망',
};

/** 모바일 EWS 경보 목록 */
export default function MAlerts() {
  const [alerts, setAlerts] = useState<any[] | null>(null);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    axios.get('/api/dashboard/ews-alerts').then(r => setAlerts(r.data || [])).catch(() => setAlerts([]));
  }, []);

  const list = (alerts || []).filter(a => !filter || a.severity === filter);

  return (
    <>
      <div className="flex items-baseline justify-between px-0.5">
        <h1 className="text-lg font-bold text-gray-900">EWS 경보</h1>
        <span className="text-xs text-gray-400">{alerts?.length ?? 0}건</span>
      </div>

      <div className="flex gap-1.5">
        {['', 'CRITICAL', 'HIGH', 'MEDIUM'].map(s => (
          <button key={s} onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold border ${
              filter === s ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-500 border-gray-200'}`}>
            {s || '전체'}
          </button>
        ))}
      </div>

      {alerts === null ? <SectionSkeleton rows={6} /> :
        list.length === 0 ? <SectionEmpty message="해당 등급의 경보가 없습니다" /> : (
          <div className="space-y-2">
            {list.map((a: any) => (
              <div key={a.alert_id} className="bg-white border border-gray-200 rounded-xl p-3.5">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-gray-900 truncate">{a.customer_name}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold flex-none ${SEV_STYLE[a.severity] || SEV_STYLE.LOW}`}>
                    {a.severity}
                  </span>
                </div>
                <p className="text-xs text-gray-600 mt-1.5">{a.trigger_condition}</p>
                <div className="flex items-center gap-2 mt-1.5 text-[10px] text-gray-400">
                  <span>{TYPE_KO[a.alert_type] || a.alert_type}</span>
                  <span>·</span>
                  <span>{a.alert_date}</span>
                  <span>·</span>
                  <span>{a.status === 'OPEN' ? '미해결' : a.status}</span>
                </div>
              </div>
            ))}
          </div>
        )}
    </>
  );
}
