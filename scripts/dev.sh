#!/usr/bin/env bash
# Runs frontend + backend dev servers concurrently (non-Docker workflow).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

cleanup() {
  echo ""
  echo "Shutting down dev servers..."
  kill 0
}
trap cleanup EXIT INT TERM

echo "==> Starting backend (FastAPI) on :8000..."
(
  cd backend
  # shellcheck disable=SC1091
  source .venv/bin/activate
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
) &

echo "==> Starting frontend (Vite) on :5173..."
(
  npm run dev:frontend
) &

wait
