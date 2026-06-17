#!/bin/bash
# 홍채 AI 분석 시스템 실행 스크립트

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== 홍채 AI 분석 시스템 ==="

# 가상환경 체크 및 생성
if [ ! -d "venv" ]; then
  echo "[1/3] 가상환경 생성 중..."
  python3 -m venv venv
fi

echo "[2/3] 패키지 설치 중..."
source venv/bin/activate
pip install -q -r requirements.txt

echo "[3/3] 서버 시작..."
echo ""
echo "  브라우저에서 열기: http://localhost:5050"
echo "  종료: Ctrl+C"
echo ""
python app.py
