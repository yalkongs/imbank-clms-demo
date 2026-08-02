#!/bin/sh
# git 훅 활성화 — 클론 후 한 번만 실행하면 된다.
#
# .git/hooks 는 git 이 추적하지 않으므로 훅을 .githooks/ 에 두고
# core.hooksPath 로 가리킨다. 그래야 훅이 리포와 함께 버전 관리된다.

set -e
ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"

chmod +x .githooks/*
git config core.hooksPath .githooks

echo "git 훅 활성화 완료 (core.hooksPath=.githooks)"
echo "  pre-commit : 프론트 소스 변경 시 자동 빌드 + dist 스테이징"
echo "  pre-push   : 배포 산출물 정합성 검증 (번들 존재·추적, 데모 DB 추적)"
