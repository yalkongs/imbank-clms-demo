#!/bin/bash
# CLMS 사내 경진대회 아이디어 제안서 PDF 생성 (A4 1페이지)
#   사용법: ./make_proposal_pdf.sh
#   원본: contest_proposal.html / 이미지: proposal_assets/
set -e
cd "$(dirname "$0")"

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUT="$(pwd)/CLMS_Contest_Proposal.pdf"

"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --virtual-time-budget=5000 --run-all-compositor-stages-before-draw \
  --print-to-pdf="$OUT" "file://$(pwd)/contest_proposal.html" 2>&1 | tail -1

echo "생성 완료: $OUT"
