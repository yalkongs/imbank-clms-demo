# iM뱅크 CLMS — UI 개편 설계

- 작성일: 2026-08-02
- 상태: 승인됨 (구현 진행)

## 목표

현재의 일반 블루 UI를 iM뱅크 브랜드(민트+라임) 기반으로 재작업하고,
최초 접속 시 프로젝트를 소개하는 온보딩 팝업을 띄우며,
전체 UI에 Gradient Mesh 스타일을 "선택 가능한 테마"로 추가한다.

## 브랜드 팔레트 (iM 민트+라임)

공식 hex는 비공개(브랜드 가이드 미공개, 공식 사이트 JS 렌더링)이므로
iM뱅크 리브랜딩 정체성(민트 주색 + 라임 강조색, 2024)에 충실하게 도출한다.

| 토큰 | Hex | 용도 |
|------|-----|------|
| Primary | #00BFA5 | iM 민트 주색 |
| Primary(600) | #00A892 | 버튼/아바타 등 주 사용 |
| Deep(700) | #00897B | 사이드바/hover/활성 텍스트 |
| Ink | #0F2E2A | 제목 텍스트 |
| Accent(Lime) | #AEEA00 | 강조 CTA/하이라이트 (절제) |
| Surface | #F1F5F4 | 배경 |
| 성공/경고/위험 | #16A34A / #F59E0B / #EF4444 | 시맨틱(유지) |

Tailwind `blue` 스케일(50~900)을 민트 틴트로 리매핑 → 21개 페이지의
`blue-600` 하드코딩이 파일 수정 없이 자동 민트 전환. 부작용으로 info-블루는
민트 계열로 흡수됨(의도된 트레이드오프).

## 테마 시스템 (Classic vs Gradient Mesh)

- `ThemeProvider`(React Context) + 루트 `data-theme="classic|mesh"`
- `localStorage("clms-theme")` 영속화, 기본값 **classic**
- Classic: 깔끔한 플랫(민트 브랜딩 적용)
- Mesh: 앱 배경에 민트·라임·틸 소프트 radial 메시 + 셸/카드 프로스티드(반투명+blur).
  `[data-theme="mesh"]` CSS로만 구동, 컴포넌트 로직 불변. 명암비 AA 유지
- 헤더에 테마 토글 → 팝업 이후에도 전환 가능

## 최초 접속 온보딩 팝업

- `localStorage("clms-onboarded")` 없으면 최초 1회 표시
- 내용: 프로젝트 소개, 모듈 그룹(전략·전술·분석·운영), 핵심 기능
  (RAROC·EWS 5채널·스트레스테스트·IFRS9 ECL 등)
- 하단 테마 선택 카드 2개(Classic/Mesh, 미니 프리뷰) → 선택 후 "시작하기"
- 헤더 정보(ⓘ) 버튼으로 재열람

## 파일

- 신규: `context/ThemeProvider.tsx`, `components/OnboardingModal.tsx`,
  `components/ThemeToggle.tsx`
- 수정: `tailwind.config.js`, `index.css`(메시/프로스티드 CSS),
  `components/Layout.tsx`, `main.tsx`

## 검증

`npm run build`(tsc+vite) 통과 + 로컬에서 팝업/테마 전환 동작 확인.

## 비고

이 UI 작업 완료 후 리스크 산식 정합성 개선("C" 방향: 6건 수정 + 회귀 테스트)을 진행한다.
