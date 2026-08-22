import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Link, useNavigate } from 'react-router-dom';
import { Inbox, Clock, ArrowUpRight, ChevronRight } from 'lucide-react';
import { Card, StatCard, PageLoader, ActionBanner, Deadline } from '../components';

/**
 * 통합 의무관리함 - 정책 예외 재검토·EWS 조치·코베넌트 점검·금리인하 SLA·
 * 승인조건 이행을 하나의 목록으로 본다. "무엇을 언제까지 해야 하고,
 * 무엇이 밀려 있는가"에 대한 단일 답.
 */

const TYPE_COLORS: Record<string, string> = {
  '정책 예외 재검토': 'bg-red-50 text-red-700',
  'EWS 조치': 'bg-amber-50 text-amber-700',
  '코베넌트 점검': 'bg-blue-50 text-blue-700',
  '금리인하요구': 'bg-purple-50 text-purple-700',
  '승인조건 이행': 'bg-emerald-50 text-emerald-700',
};

export default function ObligationInbox() {
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    axios.get('/api/obligations').then(r => setData(r.data)).catch(console.error);
  }, []);

  if (!data) return <PageLoader />;

  const items = data.items.filter((i: any) => !filter || i.type_ko === filter);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">의무관리함</h1>
        <p className="text-sm text-gray-500 mt-1">
          예외 재검토 · EWS 조치 · 코베넌트 점검 · 금리인하 SLA · 승인조건 이행을 한 곳에서
        </p>
      </div>

      <ActionBanner items={[
        { label: '기한초과 의무', count: data.overdue, to: '/obligations' },
      ]} />

      <div className="grid grid-cols-3 gap-4">
        <StatCard title="전체 의무" value={data.total} icon={<Inbox size={22} />} color="blue" />
        <StatCard title="기한 초과" value={data.overdue} subtitle="즉시 처리 필요"
          icon={<Clock size={22} />} color="red" />
        <StatCard title="이행률"
          value={`${data.total ? Math.round((1 - data.overdue / data.total) * 100) : 100}%`}
          subtitle="기한 내 관리 비율" icon={<ArrowUpRight size={22} />} color="green" />
      </div>

      <Card title={`의무 목록 (${items.length})`}
        headerAction={
          <div className="flex gap-1 flex-wrap">
            <button onClick={() => setFilter('')}
              className={`px-2.5 py-1 rounded-full text-xs font-medium border ${!filter ? 'bg-gray-900 text-white border-gray-900' : 'border-gray-200 text-gray-500'}`}>
              전체
            </button>
            {Object.entries(data.by_type).map(([t, v]: any) => (
              <button key={t} onClick={() => setFilter(t)}
                className={`px-2.5 py-1 rounded-full text-xs font-medium border ${filter === t ? 'bg-gray-900 text-white border-gray-900' : 'border-gray-200 text-gray-500'}`}>
                {t} {v.total}{v.overdue > 0 && <span className="text-red-500"> ({v.overdue})</span>}
              </button>
            ))}
          </div>
        }>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
              <th className="py-2">유형</th>
              <th className="py-2">대상</th>
              <th className="py-2">담당</th>
              <th className="py-2 text-center">기한</th>
              <th className="py-2 text-center">상태</th>
              <th className="py-2 text-center">이동</th>
              <th className="w-6"></th>
            </tr>
          </thead>
          <tbody>
            {items.map((i: any, idx: number) => (
              <tr key={`${i.type}-${i.ref_id}-${idx}`}
                onClick={() => navigate(i.link)}
                className={`border-b border-gray-50 cursor-pointer hover:bg-gray-50 ${i.overdue ? 'bg-red-50/40' : ''}`}>
                <td className="py-2">
                  <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${TYPE_COLORS[i.type_ko] || 'bg-gray-100 text-gray-600'}`}>
                    {i.type_ko}
                  </span>
                </td>
                <td className="py-2 text-xs max-w-md truncate">{i.subject}</td>
                <td className="py-2 text-xs text-gray-500">{i.owner}</td>
                <td className="py-2 text-center text-xs text-gray-500">
                  <div className="flex flex-col items-center gap-0.5">
                    <span>{i.due_date || '-'}</span>
                    <Deadline date={i.due_date} overdue={i.overdue} />
                  </div>
                </td>
                <td className="py-2 text-center">
                  {i.overdue ? (
                    <span className="px-1.5 py-0.5 bg-red-600 text-white rounded text-[10px] font-bold">
                      기한초과{i.escalated ? '·상향보고' : ''}
                    </span>
                  ) : (
                    <span className="text-[11px] text-gray-400">대기</span>
                  )}
                </td>
                <td className="py-2 text-center" onClick={e => e.stopPropagation()}>
                  <Link to={i.link} className="text-xs text-blue-600 hover:underline">처리</Link>
                </td>
                <td className="py-2 pr-1 text-right"><ChevronRight size={14} className="row-chevron inline" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
