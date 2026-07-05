# =============================================================================
# Universal Document Template Platform — Developer Makefile
# Thin wrappers around scripts/*.sh so the whole team uses one entrypoint.
# =============================================================================

.PHONY: setup dev dev-frontend dev-backend build lint format test test-frontend test-backend \
        docker-up docker-down docker-build docker-logs clean

## Install all dependencies for frontend, backend, and shared packages
setup:
	bash scripts/setup.sh

## Run frontend + backend concurrently for local development (no Docker)
dev:
	bash scripts/dev.sh

## Run only the frontend dev server
dev-frontend:
	npm run dev:frontend

## Run only the backend dev server
dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

## Production build for frontend + shared
build:
	bash scripts/build.sh

## Lint frontend (eslint) and backend (ruff)
lint:
	bash scripts/lint.sh

## Auto-format frontend (prettier) and backend (black + ruff --fix)
format:
	bash scripts/format.sh

## Run full test suite (frontend + backend)
test:
	bash scripts/test.sh

## Run only frontend tests (vitest)
test-frontend:
	npm run test:frontend

## Run only backend tests (pytest)
test-backend:
	cd backend && pytest

## Build and start all containers (dev compose)
docker-up:
	docker compose up --build

## Stop and remove containers
docker-down:
	docker compose down

## Build images without starting
docker-build:
	docker compose build

## Tail logs from all services
docker-logs:
	docker compose logs -f

## Remove build artifacts, caches, and node_modules
clean:
	rm -rf frontend/node_modules frontend/dist shared/node_modules shared/dist \
	       backend/.pytest_cache backend/.ruff_cache backend/.mypy_cache backend/**/__pycache__ \
	       node_modules
