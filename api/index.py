import sys
import os

# backend 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.main import app  # noqa: F401 — Vercel ASGI entry point (must be named 'app')
