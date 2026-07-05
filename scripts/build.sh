#!/usr/bin/env bash
# Production build for frontend + shared package.
# Backend has no build step (it ships as source inside its Docker image).
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Building shared package..."
npm run build:shared

echo "==> Building frontend..."
npm run build:frontend

echo "==> Build complete. Output: frontend/dist"
