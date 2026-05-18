#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "[start_all] root: $ROOT_DIR"

STEP_DESC="init"
on_error() {
  rc=$?
  echo "[start_all] ERROR: step='$STEP_DESC' exited with code $rc"
  echo "Check $ROOT_DIR/backend.log and $ROOT_DIR/frontend.log for details."
  exit $rc
}
trap 'on_error' ERR

# --- Backend: prepare Python .venv and install deps
STEP_DESC="check_python"
cd "$ROOT_DIR/backend"
echo "[start_all] Step: $STEP_DESC - verifying Python"
if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
  echo "[start_all] Python not found. Please install Python first (see README.md)."
  exit 1
fi
PY=python3
if ! command -v python3 >/dev/null 2>&1; then PY=python; fi

STEP_DESC="create_venv"
if [ ! -d ".venv" ]; then
  echo "[start_all] Step: $STEP_DESC - creating Python virtual environment (.venv)"
  $PY -m venv .venv
fi
# shellcheck source=/dev/null
STEP_DESC="activate_venv"
source .venv/bin/activate
STEP_DESC="pip_update"
echo "[start_all] Step: $STEP_DESC - upgrading pip and installing Python deps"
python -m pip install -U pip
if [ -f requirements.txt ]; then
  echo "[start_all] Installing dependencies from requirements.txt (this may take a few minutes for torch/torch-geometric)..."
  if ! pip install -r requirements.txt; then
    echo "[start_all] ERROR: Failed to install Python dependencies."
    echo "[start_all] If you see errors about torch or torch-geometric, try installing them separately:"
    echo "[start_all]   pip install torch  # CPU or GPU version based on your system"
    echo "[start_all]   pip install torch-geometric"
    exit 1
  fi
fi

# --- Frontend: install npm deps
STEP_DESC="check_npm"
cd "$ROOT_DIR/frontend"
echo "[start_all] Step: $STEP_DESC - verifying npm"
if ! command -v npm >/dev/null 2>&1; then
  echo "[start_all] npm not found. Please install Node.js/npm (see README.md)."
  exit 1
fi
STEP_DESC="npm_install"
echo "[start_all] Step: $STEP_DESC - installing npm dependencies"
npm install

# --- Start services (background)
cd "$ROOT_DIR"

# read frontend port from vite.config.js if possible (fallback 5173)
FRONTEND_PORT=5173
if [ -f "$ROOT_DIR/frontend/vite.config.js" ]; then
  grep -E "port\s*:\s*[0-9]+" "$ROOT_DIR/frontend/vite.config.js" | sed -E 's/.*port\s*:\s*([0-9]+).*/\1/' | head -n1 | read pf || true
  if [ -n "${pf:-}" ]; then
    FRONTEND_PORT=$pf
  fi
fi

STEP_DESC="start_backend"
echo "[start_all] Step: $STEP_DESC - starting backend (uvicorn) on port 8000"
cd backend
source .venv/bin/activate
nohup uvicorn app.main:app --reload --port 8000 > "$ROOT_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
sleep 1
if command -v lsof >/dev/null 2>&1; then
  if lsof -i :8000 >/dev/null 2>&1; then
    echo "[start_all] Backend appears to be listening on port 8000 (PID $BACKEND_PID)"
  else
    echo "[start_all] Warning: backend did not start listening on port 8000 yet (check backend.log)"
  fi
fi

STEP_DESC="start_frontend"
echo "[start_all] Step: $STEP_DESC - starting frontend (Vite) on port $FRONTEND_PORT"
cd "$ROOT_DIR/frontend"
nohup npm run dev > "$ROOT_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
sleep 1
if command -v lsof >/dev/null 2>&1; then
  if lsof -i :$FRONTEND_PORT >/dev/null 2>&1; then
    echo "[start_all] Frontend appears to be listening on port $FRONTEND_PORT (PID $FRONTEND_PID)"
  else
    echo "[start_all] Warning: frontend did not start listening on port $FRONTEND_PORT yet (check frontend.log)"
  fi
fi

echo "[start_all] Started: backend -> http://127.0.0.1:8000; frontend -> http://localhost:$FRONTEND_PORT"
STEP_DESC="done"
