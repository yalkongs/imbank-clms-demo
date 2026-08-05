import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, PageLoader } from '../components';
import { formatAmount, formatPercent } from '../utils/format';

/**
 * 동일차주 규제 범위 v0 (은행법 §35)
 * -----------------------------------
 * 그룹별 신용공여(대출+미사용약정+지급보증) 합산을 자기자본 25% 규제한도·
 * 내부 20% 집중한도와 대사하고, 그룹 선택 시 구성원별 '포함 근거'
 * (관계 유형·지분율·보증)와 효력일을 보여줘 판단을 재현한다.
 */

export default function BorrowerScope() {
  const [data, setData] = useState<any>(null);
  const [detail, setDetail] = useState<any>(null);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    axios.get('/api/group-credit/regulatory-scope').then(r => setData(r.data)).catch(console.error);
  }, []);
  useEffect(() => {
    if (!selected) { setDetail(null); return; }
    axios.get(`/api/group-credit/regulatory-scope/${selected}`)
      .then(r => setDetail(r.data)).catch(console.error);
  }, [selected]);

  if (!data) return <PageLoader />;

  const capital = data.capital || 1;

  return (
    <div className="space-y-6">
      <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-2.5 text-sm text-blue-800">
        <b>동일차주 신용공여 한도</b> - 은행법 §35: 자기자본({formatAmount(capital, 'billion')})의
        25% = <b>{formatAmount(data.regulatory_limit.amount, 'billion')}</b> ·
        내부 집중한도 20% = {formatAmount(data.internal_limit.amount, 'billion')} (조기경보) ·
        신용공여 = 대출잔액 + 미사용약정 + 그룹 내 지급보증
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 items-start">
        {/* 그룹 목록 */}
        <Card title={`차주그룹 합산 현황 (${data.groups.length}개 그룹)`}>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                <th className="py-2">그룹</th>
                <th className="py-2 text-right">신용공여 합산</th>
                <th className="py-2 text-right">자기자본 대비</th>
                <th className="py-2">한도 소진</th>
              </tr>
            </thead>
            <tbody>
              {data.groups.map((g: any) => (
                <tr key={g.group_id}
                  onClick={() => setSelected(g.group_id)}
                  className={`border-b border-gray-50 cursor-pointer hover:bg-blue-50 ${
                    selected === g.group_id ? 'bg-blue-50' : ''
                  }`}>
                  <td className="py-2.5">
                    <p className="font-medium">{g.group_name}</p>
                    <p className="text-xs text-gray-400">{g.members}개사</p>
                  </td>
                  <td className="py-2.5 text-right tabular">{formatAmount(g.total_credit, 'billion')}</td>
                  <td className="py-2.5 text-right tabular font-semibold">
                    <span className={g.regulatory_breach ? 'text-red-600' : g.internal_alert ? 'text-amber-600' : ''}>
                      {formatPercent(g.vs_capital_pct)}
                    </span>
                  </td>
                  <td className="py-2.5 w-32">
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden relative">
                      <div className={`h-full rounded-full ${
                        g.regulatory_breach ? 'bg-red-500' : g.internal_alert ? 'bg-amber-500' : 'bg-[#00BFA5]'
                      }`} style={{ width: `${Math.min(g.vs_capital_pct / 25 * 100, 100)}%` }} />
                      {/* 내부한도 20% 눈금 */}
                      <div className="absolute top-0 h-full w-0.5 bg-gray-400" style={{ left: '80%' }} />
                    </div>
                    <p className="text-[10px] text-gray-400 mt-0.5">규제 25% 기준</p>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-[11px] text-gray-400 mt-2">그룹을 선택하면 우측에 동일차주 판단 근거가 표시됩니다</p>
        </Card>

        {/* 판단 근거 */}
        {detail ? (
          <Card title={`동일차주 판단 근거: ${detail.group.group_name}`}
            headerAction={<button onClick={() => setSelected(null)} className="text-sm text-gray-500">닫기</button>}>
            <p className="text-xs font-semibold text-gray-500 mb-2">구성원과 포함 근거</p>
            <table className="w-full text-sm mb-4">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                  <th className="py-1.5">기업</th>
                  <th className="py-1.5">포함 근거</th>
                  <th className="py-1.5 text-right">지분율</th>
                  <th className="py-1.5 text-right">대출잔액</th>
                  <th className="py-1.5 text-right">미사용</th>
                </tr>
              </thead>
              <tbody>
                {detail.members.map((m: any) => (
                  <tr key={m.customer_id} className="border-b border-gray-50">
                    <td className="py-1.5 font-medium">{m.name}</td>
                    <td className="py-1.5 text-xs text-gray-600">{m.basis}</td>
                    <td className="py-1.5 text-right tabular text-xs">{m.ownership_pct != null ? `${Number(m.ownership_pct).toFixed(1)}%` : '-'}</td>
                    <td className="py-1.5 text-right tabular text-xs">{formatAmount(m.loans, 'billion')}</td>
                    <td className="py-1.5 text-right tabular text-xs">{formatAmount(m.undrawn, 'billion')}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {detail.risk_transfer.length > 0 && (
              <>
                <p className="text-xs font-semibold text-gray-500 mb-2">위험전이 관계 (그룹 내 보증)</p>
                <div className="space-y-1 mb-4">
                  {detail.risk_transfer.map((g: any, i: number) => (
                    <p key={i} className="text-xs text-gray-600">
                      {g.guarantor || g.guarantor_id} → {g.beneficiary || g.beneficiary_id}
                      {' '}<b className="tabular">{formatAmount(g.amount, 'billion')}</b>
                      <span className="text-gray-400"> ({g.type || '지급보증'} · 효력일 {g.effective_date})</span>
                    </p>
                  ))}
                </div>
              </>
            )}

            <div className="rounded-lg bg-gray-50 border border-gray-100 p-3">
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="flex justify-between"><span className="text-gray-500 text-xs">대출잔액</span>
                  <b className="tabular text-xs">{formatAmount(detail.aggregation.loans, 'billion')}</b></div>
                <div className="flex justify-between"><span className="text-gray-500 text-xs">미사용약정</span>
                  <b className="tabular text-xs">{formatAmount(detail.aggregation.undrawn, 'billion')}</b></div>
                <div className="flex justify-between"><span className="text-gray-500 text-xs">지급보증</span>
                  <b className="tabular text-xs">{formatAmount(detail.aggregation.guarantees, 'billion')}</b></div>
                <div className="flex justify-between"><span className="text-gray-500 text-xs">신용공여 합계</span>
                  <b className="tabular text-xs text-blue-700">{formatAmount(detail.aggregation.total_credit, 'billion')}</b></div>
              </div>
              <p className="text-sm mt-2 pt-2 border-t border-gray-200">
                자기자본 대비 <b className="tabular">{formatPercent(detail.aggregation.vs_capital_pct)}</b>
                <span className="text-xs text-gray-400"> / 규제한도 25% · 내부한도 20%</span>
              </p>
              <p className="text-[10px] text-gray-400 mt-1">{detail.aggregation.note}</p>
            </div>
          </Card>
        ) : (
          <Card title="판단 근거">
            <p className="text-sm text-gray-400 py-10 text-center">
              좌측에서 그룹을 선택하면 구성원별 포함 근거(관계·지분율)와<br />
              위험전이 관계(보증)·합산 내역이 표시됩니다
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}
