#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Running frontend tests (vitest)..."
npm run test:frontend

echo "==> Running backend tests (pytest)..."
cd backend
# shellcheck disable=SC1091
source .venv/bin/activate 2>/dev/null || true
pytest --cov=app --cov-report=term-missing
