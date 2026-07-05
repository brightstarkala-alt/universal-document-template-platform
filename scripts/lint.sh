#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Linting frontend (eslint)..."
npm run lint:frontend

echo "==> Linting backend (ruff)..."
cd backend
# shellcheck disable=SC1091
source .venv/bin/activate 2>/dev/null || true
ruff check .
black --check .
