// 숫자 포맷팅 유틸리티

/**
 * 금액 포맷 (억원 단위)
 */
export function formatAmount(value: number, unit: 'won' | 'million' | 'billion' | 'trillion' = 'million'): string {
  if (value === null || value === undefined) return '-';

  switch (unit) {
    case 'won':
      return new Intl.NumberFormat('ko-KR').format(value) + '원';
    case 'million':
      return new Intl.NumberFormat('ko-KR').format(value / 1_000_000) + '백만원';
    case 'billion':
      return new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 1 }).format(value / 100_000_000) + '억원';
    case 'trillion':
      return new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 2 }).format(value / 1_000_000_000_000) + '조원';
    default:
      return new Intl.NumberFormat('ko-KR').format(value);
  }
}

/**
 * 퍼센트 포맷
 */
export function formatPercent(value: number, decimals: number = 2): string {
  if (value === null || value === undefined) return '-';
  return value.toFixed(decimals) + '%';
}

/**
 * 비율 포맷 (0.0x -> x%)
 */
export function formatRatio(value: number, decimals: number = 2): string {
  if (value === null || value === undefined) return '-';
  return (value * 100).toFixed(decimals) + '%';
}

/**
 * 날짜 포맷
 */
export function formatDate(dateStr: string, format: 'short' | 'long' | 'full' = 'short'): string {
  if (!dateStr) return '-';
  const date = new Date(dateStr);

  switch (format) {
    case 'short':
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    case 'long':
      return `${date.getFullYear()}년 ${date.getMonth() + 1}월 ${date.getDate()}일`;
    case 'full':
      return date.toLocaleString('ko-KR');
    default:
      return dateStr;
  }
}

/**
 * 숫자 포맷 (천단위 콤마)
 */
export function formatNumber(value: number, decimals: number = 0): string {
  if (value === null || value === undefined) return '-';
  return new Intl.NumberFormat('ko-KR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(value);
}

/**
 * 등급 색상 클래스
 */
export function getGradeColorClass(grade: string): string {
  if (!grade) return '';
  const upperGrade = grade.toUpperCase();

  if (upperGrade.startsWith('AAA') || upperGrade.startsWith('AA')) return 'text-blue-700';
  if (upperGrade.startsWith('A')) return 'text-blue-600';
  if (upperGrade.startsWith('BBB')) return 'text-green-600';
  if (upperGrade.startsWith('BB')) return 'text-yellow-600';
  if (upperGrade.startsWith('B')) return 'text-orange-600';
  if (upperGrade.startsWith('CCC') || upperGrade.startsWith('CC') || upperGrade.startsWith('C')) return 'text-red-600';
  if (upperGrade === 'D') return 'text-red-800';
  return '';
}

/**
 * 전략 코드 색상 클래스
 */
export function getStrategyColorClass(strategy: string): string {
  switch (strategy) {
    case 'EXPAND': return 'bg-green-100 text-green-800';
    case 'SELECTIVE': return 'bg-blue-100 text-blue-800';
    case 'MAINTAIN': return 'bg-gray-100 text-gray-800';
    case 'REDUCE': return 'bg-yellow-100 text-yellow-800';
    case 'EXIT': return 'bg-red-100 text-red-800';
    default: return 'bg-gray-100 text-gray-600';
  }
}

/**
 * 전략 코드 한글 변환
 */
export function getStrategyLabel(strategy: string): string {
  switch (strategy) {
    case 'EXPAND': return '확대';
    case 'SELECTIVE': return '선별';
    case 'MAINTAIN': return '유지';
    case 'REDUCE': return '축소';
    case 'EXIT': return '퇴출';
    default: return strategy;
  }
}

/**
 * 상태 배지 색상 클래스
 */
export function getStatusColorClass(status: string): string {
  const upperStatus = status?.toUpperCase() || '';

  if (['ACTIVE', 'APPROVED', 'NORMAL', 'HEALTHY'].includes(upperStatus)) {
    return 'bg-green-100 text-green-800';
  }
  if (['PENDING', 'REVIEW', 'UNDER_REVIEW', 'WARNING'].includes(upperStatus)) {
    return 'bg-yellow-100 text-yellow-800';
  }
  if (['REJECTED', 'CRITICAL', 'BREACH', 'ALERT'].includes(upperStatus)) {
    return 'bg-red-100 text-red-800';
  }
  if (['INACTIVE', 'EXPIRED', 'CLOSED'].includes(upperStatus)) {
    return 'bg-gray-100 text-gray-600';
  }
  return 'bg-blue-100 text-blue-800';
}

/**
 * 한도 사용률에 따른 색상 클래스
 */
export function getUtilizationColorClass(rate: number): string {
  if (rate >= 100) return 'text-red-600';
  if (rate >= 90) return 'text-orange-600';
  if (rate >= 80) return 'text-yellow-600';
  return 'text-green-600';
}

/**
 * RAROC에 따른 색상 클래스
 */
export function getRarocColorClass(raroc: number, hurdle: number = 15): string {
  if (raroc >= hurdle * 1.2) return 'text-green-600';
  if (raroc >= hurdle) return 'text-blue-600';
  if (raroc >= hurdle * 0.8) return 'text-yellow-600';
  return 'text-red-600';
}

/**
 * 숫자에서 콤마 제거 후 숫자로 변환
 */
export function parseFormattedNumber(value: string): number {
  const cleaned = value.replace(/[^\d.-]/g, '');
  return Number(cleaned) || 0;
}

/**
 * 입력용 금액 포맷 (콤마만 추가, 단위 없음)
 */
export function formatInputAmount(value: number | string): string {
  const num = typeof value === 'string' ? parseFormattedNumber(value) : value;
  if (isNaN(num)) return '';
  return new Intl.NumberFormat('ko-KR').format(num);
}
