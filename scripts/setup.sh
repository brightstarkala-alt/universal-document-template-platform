#!/usr/bin/env bash
# Bootstraps a fresh local development environment.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Checking required tools..."
command -v node >/dev/null || { echo "Node.js is required (>=20). Aborting."; exit 1; }
command -v python3 >/dev/null || { echo "Python 3.11+ is required. Aborting."; exit 1; }

echo "==> Creating env files from examples (skipping any that already exist)..."
for f in .env frontend/.env backend/.env; do
  example="${f}.example"
  if [ ! -f "$f" ] && [ -f "$example" ]; then
    cp "$example" "$f"
    echo "    created $f"
  fi
done

echo "==> Installing Node dependencies (frontend + shared workspaces)..."
npm install

echo "==> Building shared package..."
npm run build:shared

echo "==> Creating Python virtual environment for backend..."
cd backend
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
cd "$ROOT_DIR"

echo ""
echo "Setup complete."
echo "Next steps:"
echo "  1. Fill in real values in .env, frontend/.env, backend/.env"
echo "  2. Run 'make dev' to start both frontend and backend"
echo "     (or 'make docker-up' to run everything in Docker)"
