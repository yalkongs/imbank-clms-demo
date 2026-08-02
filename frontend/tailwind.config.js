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
      },
    },
  },
  plugins: [],
}
