#!/bin/zsh
set -e

PROJECT_DIR="${0:A:h}"
cd "$PROJECT_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Missing .venv. Create the Python 3.12 environment and install requirements first."
  exit 1
fi

if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port 8000 is already in use."
  echo "If Portfolio Analyzer is already open, use http://localhost:3001."
  echo "Otherwise stop the old process with: lsof -ti tcp:8000 | xargs kill"
  exit 1
fi

if lsof -nP -iTCP:3001 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port 3001 is already in use."
  echo "If Portfolio Analyzer is already open, use http://localhost:3001."
  echo "Otherwise stop the old process with: lsof -ti tcp:3001 | xargs kill"
  exit 1
fi

cleanup() {
  [[ -n "${API_PID:-}" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "${WEB_PID:-}" ]] && kill "$WEB_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

.venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!

npm --prefix web run dev -- --port 3001 &
WEB_PID=$!

echo "Portfolio Analyzer UI: http://localhost:3001"
echo "Portfolio Analyzer API: http://localhost:8000/docs"
wait
