import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { Search, Lock } from 'lucide-react';
import { Card, PageLoader } from '../components';
import { formatAmount } from '../utils/format';

/** 여신철 대장 - 승인·심사·종결 건을 검색해 여신철로 진입한다 */
export default function CaseLedger() {
  const [data, setData] = useState<any>(null);
  const [q, setQ] = useState('');

  const load = (query = '') => {
    axios.get('/api/credit-case', { params: query ? { q: query, limit: 80 } : { limit: 80 } })
      .then(r => setData(r.data)).catch(console.error);
  };
  useEffect(() => load(), []);

  if (!data) return <PageLoader />;

  const STATUS_KO: Record<string, string> = {
    APPROVED: '승인', DISBURSED: '실행', REVIEWING: '심사중', RECEIVED: '접수',
    REJECTED: '부결', WITHDRAWN: '철회', CONDITIONAL: '조건부',
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">여신철 대장</h1>
        <p className="text-sm text-gray-500 mt-1">
          의사결정 증거 패키지 검색 - 🔒 는 승인 시점 스냅샷이 봉인된 건입니다
        </p>
      </div>

      <Card>
        <form onSubmit={e => { e.preventDefault(); load(q); }} className="mb-3 relative max-w-md">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input value={q} onChange={e => setQ(e.target.value)}
            placeholder="기업명 또는 신청번호 검색..."
            className="w-full border rounded-lg px-3 py-2 pl-9 text-sm" />
        </form>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
              <th className="py-2">신청번호</th>
              <th className="py-2">기업</th>
              <th className="py-2 text-right">신청금액</th>
              <th className="py-2 text-center">상태</th>
              <th className="py-2 text-center">결재</th>
              <th className="py-2 text-center">예외</th>
              <th className="py-2 text-center">봉인</th>
              <th className="py-2 text-center">여신철</th>
            </tr>
          </thead>
          <tbody>
            {data.cases.map((c: any) => (
              <tr key={c.application_id} className="border-b border-gray-50">
                <td className="py-2 text-xs font-mono text-gray-500">{c.application_id}</td>
                <td className="py-2 font-medium">{c.customer_name}</td>
                <td className="py-2 text-right tabular text-xs">{formatAmount(c.requested_amount, 'billion')}</td>
                <td className="py-2 text-center">
                  <span className={`px-2 py-0.5 rounded text-xs ${
                    ['APPROVED', 'DISBURSED'].includes(c.status) ? 'bg-green-100 text-green-700' :
                    c.status === 'REJECTED' ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-600'
                  }`}>{STATUS_KO[c.status] || c.status}</span>
                </td>
                <td className="py-2 text-center text-xs tabular">{c.approvals}</td>
                <td className="py-2 text-center text-xs tabular">{c.exceptions || '-'}</td>
                <td className="py-2 text-center">
                  {c.sealed && <Lock size={13} className="inline text-[#00897B]" />}
                </td>
                <td className="py-2 text-center">
                  <Link to={`/credit-case/${c.application_id}`}
                    className="text-xs text-blue-600 hover:underline">열기</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
