#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "[stop_all] root: $ROOT_DIR"

cd "$ROOT_DIR"

echo "Stopping frontend (Vite / npm)..."
if command -v pkill >/dev/null 2>&1; then
  pkill -f "vite" || true
  pkill -f "npm run dev" || true
  sleep 1
  pkill -9 -f "vite" || true
  pkill -9 -f "npm run dev" || true
else
  echo "pkill not available; you may need to stop node processes manually."
fi

echo "Stopping backend (uvicorn/python)..."
if command -v pkill >/dev/null 2>&1; then
  pkill -f "uvicorn app.main:app" || true
  pkill -f "uvicorn" || true
  sleep 1
  pkill -9 -f "uvicorn app.main:app" || true
  pkill -9 -f "uvicorn" || true
fi

if command -v lsof >/dev/null 2>&1; then
  pids=$(lsof -ti :8000 || true)
  if [ -n "$pids" ]; then
    echo "Killing processes listening on port 8000: $pids"
    kill $pids || true
  fi
fi

echo "Stopped services (if running). Check backend.log and frontend.log for details."
