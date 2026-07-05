# Installation Guide

This guide walks through setting up the Universal Document Template
Platform for local development, either natively or via Docker.

## Prerequisites

| Tool    | Version  | Notes                                   |
|---------|----------|------------------------------------------|
| Node.js | >= 20.x  | Frontend + shared package                |
| npm     | >= 10.x  | Ships with Node 20                       |
| Python  | >= 3.11  | Backend                                  |
| Docker  | >= 24.x  | Optional, but recommended for parity     |
| Docker Compose | v2 (plugin) | `docker compose ...` (no hyphen) |

You will also need:
- A Supabase project (URL + anon key + service role key) — used starting
  from the Authentication/Database modules, but the config placeholders
  exist from Module 1 onward.
- An OpenAI API key — used starting from the AI module.

---

## Option A — Native (no Docker)

### 1. Clone the repository

```bash
git clone <repo-url>
cd universal-doc-template-platform
```

### 2. Run the automated setup script

```bash
bash scripts/setup.sh
```

This will:
- Verify Node and Python are installed
- Copy `.env.example` → `.env` (root, frontend, backend) if they don't exist yet
- Install root + frontend + shared npm dependencies
- Build the shared TypeScript package
- Create a Python virtual environment in `backend/.venv` and install dependencies

### 3. Fill in environment variables

Edit:
- `.env` — shared/root-level values used by Docker Compose
- `frontend/.env` — `VITE_API_BASE_URL`, Supabase public keys
- `backend/.env` — Supabase service role key, OpenAI key, CORS origins

### 4. Start the app

```bash
make dev
```

This runs the FastAPI backend (`:8000`, hot reload) and the Vite frontend
(`:5173`, hot reload) concurrently.

Visit:
- Frontend: http://localhost:5173
- API docs (Swagger UI): http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

---

## Option B — Docker

### 1. Clone and configure environment files

```bash
git clone <repo-url>
cd universal-doc-template-platform
cp .env.example .env
cp frontend/.env.example frontend/.env
cp backend/.env.example backend/.env
```

Fill in real values as needed.

### 2. Start the stack

```bash
make docker-up
# equivalent to: docker compose up --build
```

This starts:
- `frontend` — Vite dev server (hot reload via bind mount)
- `backend` — FastAPI with `--reload`
- `postgres` — OPTIONAL local Postgres, only started if you explicitly enable
  the `local-db` profile:
  ```bash
  docker compose --profile local-db up --build
  ```
  Not needed if you're pointing at a cloud Supabase project (recommended).

### 3. Stop the stack

```bash
make docker-down
```

---

## Running tests

```bash
make test              # both frontend + backend
make test-frontend     # vitest only
make test-backend      # pytest only
```

## Linting & formatting

```bash
make lint       # eslint (frontend) + ruff & black --check (backend)
make format     # prettier (frontend) + ruff --fix & black (backend)
```

## Production build

```bash
make build
# or, for full container images:
docker compose -f docker-compose.prod.yml --env-file .env.production up --build -d
```

## Troubleshooting

- **`ModuleNotFoundError` in backend** — make sure you activated the virtualenv:
  `source backend/.venv/bin/activate`.
- **Frontend can't reach backend** — confirm `VITE_API_BASE_URL` in
  `frontend/.env` matches where the backend is actually running.
- **WeasyPrint import errors (future PDF module)** — WeasyPrint needs native
  system libraries (Pango, Cairo). These are pre-installed in the backend
  Docker image; for native installs see
  https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation.
- **Port already in use** — change `FRONTEND_PORT` / `BACKEND_PORT` in `.env`.
