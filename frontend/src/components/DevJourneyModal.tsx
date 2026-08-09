import React from 'react';
import {
  Sparkles, GitCommit, Monitor, Database, FlaskConical, Code2,
  Rocket, ShieldCheck, RefreshCw, CheckCircle2, Network, Bot, X,
} from 'lucide-react';
import { StatCard } from './index';

/**
 * 개발 여정 - 바이브 코딩 경진대회 메타 정보 (대형 팝업)
 * -------------------------------------------------------
 * 시스템 소개 팝업에서 진입한다. 결과물이 아니라 '과정'을 보여준다:
 * AI 페어 코딩으로 1인이 어느 규모를 어떤 품질 루프로 만들었는지의
 * 실측 기록 (git 이력·OpenAPI·DB 기준, 2026-08-09).
 */

const STATS = [
  { title: '개발 활동일', value: '13일', subtitle: '2026.1.30 ~ 8.9 (여가 시간)', icon: <GitCommit size={22} />, color: 'blue' as const },
  { title: '커밋', value: '92회', subtitle: '훅 검증 통과 후 자동 배포', icon: <Code2 size={22} />, color: 'blue' as const },
  { title: '화면', value: '42개', subtitle: 'React 18 + Vite SPA', icon: <Monitor size={22} />, color: 'green' as const },
  { title: 'API 엔드포인트', value: '242개', subtitle: 'FastAPI 39개 모듈', icon: <Network size={22} />, color: 'green' as const },
  { title: 'DB 테이블', value: '95개', subtitle: '고객 2,160 · 여신 3,734건 (모의)', icon: <Database size={22} />, color: 'yellow' as const },
  { title: '자동 테스트', value: '172개', subtitle: '규제 시나리오 회귀 포함', icon: <FlaskConical size={22} />, color: 'yellow' as const },
  { title: '코드', value: '4.4만 줄', subtitle: '프론트 2.3만 + 백엔드 2.1만', icon: <Code2 size={22} />, color: 'red' as const },
  { title: '운영 배포', value: '상시', subtitle: 'push → 빌드 → 배포 전자동', icon: <Rocket size={22} />, color: 'red' as const },
];

const LOOP = [
  { icon: <Bot size={18} />, title: '① 대화로 요구 전달', body: '"연체 Roll Rate가 계속 로딩 중이다. 점검하라" - 업무 언어 그대로. 명세서·티켓 없이 대화가 곧 요구사항이다.' },
  { icon: <Code2 size={18} />, title: '② AI가 원인 진단·구현', body: 'AI가 코드·DB를 직접 조사해 원인(전이 관측 데이터 부재 + 상태 설계 결함)을 찾고, 스키마 추가부터 화면 수정까지 일괄 구현한다.' },
  { icon: <FlaskConical size={18} />, title: '③ 자동 검증', body: '커밋 전 훅이 프론트를 빌드하고, 172개 테스트(전결권 우회·법정한도·봉인 불변성 등 규제 시나리오 포함)가 회귀를 차단한다.' },
  { icon: <Rocket size={18} />, title: '④ 자동 배포·확인', body: 'push 하면 Render가 자동 배포한다. AI가 라이브 응답을 재검증한 뒤에야 "반영 완료"를 보고한다.' },
];

const MILESTONES = [
  { period: '1월 말', title: '기반 구축', body: '95개 테이블 스키마, 심사·실행·사후관리 API 골격, 28개 화면 프레임 - 첫 이틀에 시스템의 뼈대가 섰다.' },
  { period: '2~7월', title: '업무 고도화', body: 'EWS 5채널 조기경보, RAROC 프라이싱, 자산건전성·ECL, 워크아웃 NPV, 금리인하요구권 SLA 상태기계 - 은행 실무 흐름을 하나씩 이식.' },
  { period: '7월', title: '차주 확대 + 성능', body: '여신 보유 기업 699 → 1,999개사로 확대하면서 응답을 7.7초 → 0.3초로 - gzip·인덱스 14개·TTL 캐시.' },
  { period: '8월 초', title: '내부통제 이식', body: '서버 결정 전결권, 직무분리(Maker-Checker), 승인 시점 심사자료 봉인(SHA-256), 신용공여 원장, 법정 3한도, 규정 레지스터.' },
  { period: '8월', title: '제3자 검증 루프', body: '외부 AI 리뷰(QA 92/100, 감사 관점 리뷰 2건)의 지적을 받아 당일 검증·수정·배포 - 지적 → 반영 평균 반나절.' },
];

export default function DevJourneyModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-[70] bg-black/60 flex items-center justify-center p-4">
      <div className="modal-in bg-gray-50 rounded-2xl shadow-2xl w-full max-w-6xl max-h-[92vh] overflow-hidden flex flex-col">
        {/* 헤더 */}
        <div className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200 flex-none">
          <div className="flex items-center gap-2.5">
            <span className="w-9 h-9 rounded-lg im-gradient text-white flex items-center justify-center">
              <Sparkles size={17} />
            </span>
            <div>
              <h3 className="text-base font-bold text-gray-900">개발 여정</h3>
              <p className="text-xs text-gray-500">
                이 시스템이 만들어진 과정 - AI 페어 코딩(바이브 코딩) 실측 기록
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg" aria-label="닫기">
            <X size={20} />
          </button>
        </div>

        {/* 본문 */}
        <div className="overflow-y-auto p-6 space-y-6">
          {/* 한 줄 요약 */}
          <div className="im-gradient rounded-xl p-6 text-white">
            <p className="text-lg font-bold">
              1명 + AI, 여가 시간 13일의 개발 활동으로 기업여신 전 생애주기를 다루는
              시스템을 만들고 운영 배포까지 자동화했습니다.
            </p>
            <p className="text-sm mt-2 opacity-90">
              기획서도 개발팀도 없이 - 업무를 아는 사람이 AI와 대화하며 직접 만드는
              방식이 어디까지 갈 수 있는지에 대한 실험입니다.
            </p>
          </div>

          {/* 실측 수치 */}
          <div className="grid grid-cols-4 gap-4">
            {STATS.map(s => <StatCard key={s.title} {...s} />)}
          </div>

          {/* 전통 개발 대비 - 바이브 코딩의 효과 */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-base font-bold text-gray-900 mb-1">같은 것을 사람이 만들었다면?</h3>
            <p className="text-xs text-gray-400 mb-5">
              코드 4.4만 줄 · 화면 42개 · API 242개 규모를 통상적 SI 산정 방식으로 환산한 비교
            </p>
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-xl border border-gray-200 p-5">
                <p className="text-xs font-semibold text-gray-400 mb-3">전통 개발 (금융 SI 기준 추정)</p>
                <div className="space-y-2.5">
                  <div className="flex justify-between items-baseline">
                    <span className="text-sm text-gray-500">투입 인력</span>
                    <span className="text-lg font-bold text-gray-800">8~10명</span>
                  </div>
                  <div className="flex justify-between items-baseline">
                    <span className="text-sm text-gray-500">개발 기간</span>
                    <span className="text-lg font-bold text-gray-800">12~18개월</span>
                  </div>
                  <div className="flex justify-between items-baseline">
                    <span className="text-sm text-gray-500">투입 공수</span>
                    <span className="text-lg font-bold text-gray-800">100~150인월</span>
                  </div>
                  <div className="flex justify-between items-baseline border-t border-gray-100 pt-2.5">
                    <span className="text-sm text-gray-500">환산 비용</span>
                    <span className="text-xl font-bold text-red-600">약 15~22억원</span>
                  </div>
                </div>
                <p className="mt-3 text-[11px] text-gray-400 leading-relaxed">
                  여신 업무 전문가 · Basel/IFRS9 리스크 계량 전문가 · 금융 SI 개발자 등
                  희소한 전문 인력으로 구성 - 인력 확보 자체가 병목이며 단가도 일반 SI 대비 높다
                </p>
              </div>
              <div className="rounded-xl border-2 border-[#00BFA5]/40 bg-[#00BFA5]/[0.04] p-5">
                <p className="text-xs font-semibold text-[#00897B] mb-3">바이브 코딩 (이 프로젝트 실적)</p>
                <div className="space-y-2.5">
                  <div className="flex justify-between items-baseline">
                    <span className="text-sm text-gray-500">투입 인력</span>
                    <span className="text-lg font-bold text-gray-800">1명 + AI</span>
                  </div>
                  <div className="flex justify-between items-baseline">
                    <span className="text-sm text-gray-500">개발 기간</span>
                    <span className="text-lg font-bold text-gray-800">활동일 13일 (여가 시간)</span>
                  </div>
                  <div className="flex justify-between items-baseline">
                    <span className="text-sm text-gray-500">투입 공수</span>
                    <span className="text-lg font-bold text-gray-800">1인월 미만</span>
                  </div>
                  <div className="flex justify-between items-baseline border-t border-[#00BFA5]/20 pt-2.5">
                    <span className="text-sm text-gray-500">직접 비용</span>
                    <span className="text-xl font-bold text-[#00897B]">AI 구독료 수십만원</span>
                  </div>
                </div>
              </div>
            </div>
            <p className="mt-4 text-center text-sm font-bold text-gray-800">
              비용 기준 약 <span className="text-[#00897B] text-lg">수천분의 1</span>,
              달력 기준 약 <span className="text-[#00897B] text-lg">30분의 1</span> 기간
            </p>
            <p className="mt-3 text-[11px] text-gray-400 leading-relaxed">
              산정 근거: COCOMO(organic) 모형 기준 44 KLOC ≈ 127인월(10.6인년)로, 도메인 전문성
              (Basel 자본규제·감독규정·IFRS9·여신 실무)이 필수라 생산성 할인 없이 100~150인월로 추정.
              비용은 금융 도메인 특급·고급 기술자 인월 단가 약 1,500만원 적용. 요구 정련·품질 수준이
              동일하다는 가정의 단순 비교이며, 운영계 전환 시 필요한 보안·연계·감리 비용은
              양쪽 모두 제외한 수치입니다.
            </p>
          </div>

          {/* 작업 루프 */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-base font-bold text-gray-900 mb-1">바이브 코딩 작업 루프</h3>
            <p className="text-xs text-gray-400 mb-5">
              모든 기능이 이 4단계를 돌았다 - 사람은 판단하고, AI 는 구현·검증하고, 파이프라인은 배포한다
            </p>
            <div className="grid grid-cols-4 gap-4">
              {LOOP.map((l, i) => (
                <div key={i} className="p-4 bg-gray-50 rounded-lg">
                  <span className="w-9 h-9 rounded-lg bg-white border border-gray-200 text-[#00897B] flex items-center justify-center mb-3">
                    {l.icon}
                  </span>
                  <p className="text-sm font-bold text-gray-800">{l.title}</p>
                  <p className="text-xs text-gray-500 mt-1.5 leading-relaxed">{l.body}</p>
                </div>
              ))}
            </div>
          </div>

          {/* 마일스톤 */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-base font-bold text-gray-900 mb-5">마일스톤</h3>
            <div>
              {MILESTONES.map((m, i) => (
                <div key={i} className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <span className="w-3 h-3 rounded-full im-gradient flex-none mt-1.5" />
                    {i < MILESTONES.length - 1 && <span className="w-px flex-1 bg-gray-200" />}
                  </div>
                  <div className="pb-6">
                    <p className="text-xs font-semibold text-[#00897B]">{m.period}</p>
                    <p className="text-sm font-bold text-gray-900 mt-0.5">{m.title}</p>
                    <p className="text-xs text-gray-500 mt-1 leading-relaxed">{m.body}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 품질 장치 */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <ShieldCheck size={20} className="text-[#00897B] mb-2.5" />
              <p className="text-sm font-bold text-gray-800">스스로를 지키는 파이프라인</p>
              <p className="text-xs text-gray-500 mt-1.5 leading-relaxed">
                커밋 전 훅이 빌드를 강제하고, push 전 훅이 배포 자산 누락을 차단한다.
                깨진 상태는 원천적으로 배포될 수 없다.
              </p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <RefreshCw size={20} className="text-[#00897B] mb-2.5" />
              <p className="text-sm font-bold text-gray-800">제3자 AI 교차 검증</p>
              <p className="text-xs text-gray-500 mt-1.5 leading-relaxed">
                별도 AI(Codex·AGY)에게 QA·감사 관점 리뷰를 맡기고, 지적을 코드로
                재검증해 당일 반영했다. 만든 AI 와 검증하는 AI 를 분리한 구조다.
              </p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <CheckCircle2 size={20} className="text-[#00897B] mb-2.5" />
              <p className="text-sm font-bold text-gray-800">정직한 경계 표시</p>
              <p className="text-xs text-gray-500 mt-1.5 leading-relaxed">
                모의 데이터 PoC 임을 모든 산출물에 명시한다. 자동 생성 문서는
                '초안', 근사 산식은 'PoC 근사'로 표기 - 과장이 없어야 신뢰가 남는다.
              </p>
            </div>
          </div>

          <p className="text-[11px] text-gray-400 text-center pb-1">
            수치 기준: git 이력 · OpenAPI 명세 · DB 실측 (2026-08-09) · 본 시스템은 모의 데이터 기반 PoC 입니다
          </p>
        </div>
      </div>
    </div>
  );
}
