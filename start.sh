#!/bin/bash

# iM뱅크 CLMS 데모 시스템 시작 스크립트

echo "======================================"
echo "  iM뱅크 CLMS 데모 시스템 시작"
echo "======================================"

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 프로젝트 루트 디렉토리
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

# 1. 데이터베이스 확인
# 주의: 과거에는 잘못된 파일명(clms_demo.db)을 검사해 항상 seed_data.py 가 돌았고,
# 그 스크립트는 현행 86개 테이블 DB 를 삭제하고 구식 스키마로 재생성한다.
# 데모 DB 는 git 추적 배포 자산이므로 여기서는 절대 시드를 자동 실행하지 않는다.
if [ ! -f "$PROJECT_ROOT/database/imbank_demo.db" ]; then
    echo "[오류] database/imbank_demo.db 가 없습니다."
    echo "       git checkout database/imbank_demo.db 로 복원하세요."
    echo "       (seed 재생성이 정말 필요하면 database/*.py 파이프라인을 순서대로 실행)"
    exit 1
else
    echo -e "${GREEN}[1/3] 데이터베이스 확인 완료${NC}"
fi

# 2. 백엔드 서버 시작
echo -e "${BLUE}[2/3] 백엔드 서버 시작 (포트 8000)...${NC}"
cd "$PROJECT_ROOT/backend"
python run.py &
BACKEND_PID=$!
sleep 2
echo -e "${GREEN}      백엔드 서버 시작 완료 (PID: $BACKEND_PID)${NC}"

# 3. 프론트엔드 서버 시작
echo -e "${BLUE}[3/3] 프론트엔드 서버 시작 (포트 3000)...${NC}"
cd "$PROJECT_ROOT/frontend"
npm run dev &
FRONTEND_PID=$!
sleep 3
echo -e "${GREEN}      프론트엔드 서버 시작 완료 (PID: $FRONTEND_PID)${NC}"

echo ""
echo "======================================"
echo "  시스템 시작 완료!"
echo "======================================"
echo ""
echo -e "${GREEN}접속 URL:${NC}"
echo "  - 메인 대시보드: http://localhost:3000"
echo "  - API 문서:      http://localhost:8000/docs"
echo ""
echo "종료하려면 Ctrl+C를 누르세요."
echo ""

# 프로세스 대기
wait
