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

# 1. 데이터베이스 초기화 (필요한 경우)
if [ ! -f "$PROJECT_ROOT/database/clms_demo.db" ]; then
    echo -e "${BLUE}[1/3] 데이터베이스 초기화...${NC}"
    cd "$PROJECT_ROOT/backend"
    python data/seed_data.py
    echo -e "${GREEN}      데이터베이스 초기화 완료${NC}"
else
    echo -e "${GREEN}[1/3] 데이터베이스 이미 존재${NC}"
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
