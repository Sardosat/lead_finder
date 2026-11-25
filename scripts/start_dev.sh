#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

API_PID=""
WEB_PID=""

cleanup() {
  echo ""
  echo "Arresto server Lead Intelligence Engine..."
  [[ -n "$WEB_PID" ]] && kill "$WEB_PID" 2>/dev/null || true
  [[ -n "$API_PID" ]] && kill "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Avvio FastAPI backend su http://127.0.0.1:8000 ..."
"$ROOT_DIR/.venv/bin/uvicorn" api.server:app --host 127.0.0.1 --port 8000 &
API_PID=$!

echo "Avvio Web App Next.js su http://127.0.0.1:3000 ..."
cd "$ROOT_DIR/web"
npm run dev -- --port 3000 &
WEB_PID=$!

echo ""
echo "Console operativa pronta:"
echo "  Web App : http://localhost:3000"
echo "  API Docs: http://127.0.0.1:8000/docs"
echo ""

wait "$API_PID" "$WEB_PID"
