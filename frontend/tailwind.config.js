/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // iM Financial Group 공식 브랜드 팔레트
        // 출처: Claude Design "iM Financial Design System" (공식 컬러 시스템 시트 기반)
        // 종전 값(#00BFA5 / #AEEA00 등)은 공식 hex를 몰라 도출한 추정치였다.
        'imbank': {
          primary: '#00C7A9',   // iM Mint — Pantone 326C
          secondary: '#00A58C',
          deep: '#008570',
          accent: '#E2F15E',    // iM Lime — Pantone 585C
          ink: '#18181B',
          logotype: '#666666',  // iM Gray — Pantone Cool Gray 10C (로고타입 전용)
          success: '#00C7A9',
          warning: '#F5A524',
          danger: '#E5484D',
          info: '#7DB5FF',
          dark: '#18181B',
          light: '#FAFAFA',
        },
        // 보조 팔레트 (공식 Secondary)
        'im-blue':       '#7DB5FF',   // Pantone 292C
        'im-purple':     '#D1B5FF',   // Pantone 264C
        'im-light-blue': '#53E1E5',   // Pantone 3105C
        'im-beige':      '#CDC9B7',   // Pantone 7528C
        // 라임 강조 스케일
        'lime-accent': {
          DEFAULT: '#E2F15E',
          soft: '#F1F8AE',
          deep: '#C9DC2E',
        },
        // Tailwind 기본 blue 스케일을 iM 민트 틴트로 리매핑
        // → 기존 페이지의 blue-600 등 하드코딩이 파일 수정 없이 민트로 전환
        // 공식 디자인 시스템의 민트 틴트 스케일을 그대로 쓴다.
        blue: {
          50:  '#E6FAF6',
          100: '#C2F3E8',
          200: '#8FE7D3',
          300: '#4FD6BA',
          400: '#1FCEB0',
          500: '#00C7A9',
          600: '#00A58C',
          700: '#008570',
          800: '#006855',
          900: '#004A3C',
          950: '#00332A',
        },
        // gray 스케일도 브랜드 값으로 리매핑한다.
        // 설계 문서의 Ink(#0F2E2A, 제목) 와 Surface(#F1F5F4, 배경)는 토큰만 정의돼 있고
        // 실제로는 text-gray-900 163곳 · bg-gray-50 247곳이 중립 회색 그대로였다.
        // 개별 파일을 고치는 대신 blue 와 같은 방식으로 스케일을 바꿔 전역 반영한다.
        // 중간 단계는 민트 쪽으로 아주 옅게 틴트만 넣어 본문 가독성을 유지한다.
        // 공식 중성 스케일 (warm-gray). iM Gray(#666666) 로고타입과 어울리도록 설계된 값.
        gray: {
          50:  '#FAFAFA',
          100: '#F4F4F5',
          200: '#E8E8EA',
          300: '#D4D4D8',
          400: '#A1A1A8',
          500: '#71717A',
          600: '#52525B',
          700: '#3F3F45',
          800: '#27272A',
          900: '#18181B',
          950: '#09090B',
        },
      },
    },
  },
  plugins: [],
}
