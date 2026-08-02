/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // iM뱅크 브랜드 (민트 주색 + 라임 강조색)
        'imbank': {
          primary: '#00BFA5',
          secondary: '#00A892',
          deep: '#00897B',
          accent: '#AEEA00',   // 라임 포인트
          ink: '#0F2E2A',
          success: '#16A34A',
          warning: '#F59E0B',
          danger: '#EF4444',
          dark: '#0F2E2A',
          light: '#F1F5F4',
        },
        // 라임 강조 스케일
        'lime-accent': {
          DEFAULT: '#AEEA00',
          soft: '#DDF88A',
          deep: '#84CC16',
        },
        // Tailwind 기본 blue 스케일을 iM 민트 틴트로 리매핑
        // → 기존 페이지의 blue-600 등 하드코딩이 파일 수정 없이 민트로 전환
        blue: {
          50:  '#E6FAF6',
          100: '#C7F2EA',
          200: '#93E7D8',
          300: '#57D7C2',
          400: '#1FC6AC',
          500: '#00BFA5',
          600: '#00A892',
          700: '#00897B',
          800: '#00695C',
          900: '#0F2E2A',
          950: '#082019',
        },
        // gray 스케일도 브랜드 값으로 리매핑한다.
        // 설계 문서의 Ink(#0F2E2A, 제목) 와 Surface(#F1F5F4, 배경)는 토큰만 정의돼 있고
        // 실제로는 text-gray-900 163곳 · bg-gray-50 247곳이 중립 회색 그대로였다.
        // 개별 파일을 고치는 대신 blue 와 같은 방식으로 스케일을 바꿔 전역 반영한다.
        // 중간 단계는 민트 쪽으로 아주 옅게 틴트만 넣어 본문 가독성을 유지한다.
        gray: {
          50:  '#F1F5F4',   // Surface — 앱 배경
          100: '#E7EDEB',
          200: '#D6DEDC',
          300: '#BAC5C2',
          400: '#8B9895',
          500: '#67736F',
          600: '#4D5956',
          700: '#3A4643',
          800: '#243230',
          900: '#0F2E2A',   // Ink — 제목 텍스트
          950: '#081C19',
        },
      },
    },
  },
  plugins: [],
}
