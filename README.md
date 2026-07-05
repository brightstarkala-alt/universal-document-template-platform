# Universal Document Template Platform

A multi-tenant SaaS platform that turns any uploaded business document into a
reusable, editable template. The uploaded document **is** the template:
users edit only variable values from a left-side panel while a right-side
live preview stays pixel-identical to the original, and the downloaded PDF
matches that same preview exactly.

## Supported document types

PDF (text), PDF (scanned), DOCX, XLS, XLSX, PNG, JPG, JPEG, WEBP.

## Tech stack

| Layer          | Technology                                      |
|----------------|--------------------------------------------------|
| Frontend       | React, Vite, TypeScript, Tailwind CSS, TanStack Query |
| Backend        | FastAPI (Python)                                |
| Database       | Supabase PostgreSQL                             |
| Authentication | Supabase Auth                                   |
| Storage        | Supabase Storage                                |
| PDF rendering  | WeasyPrint                                      |
| AI             | OpenAI GPT                                      |

## Monorepo structure

```
.
├── frontend/          React + Vite + TypeScript app
├── backend/           FastAPI application
├── shared/            Shared TypeScript types/constants (npm workspace)
├── docker/            Local-only Docker assets (e.g. local Postgres init scripts)
├── scripts/           Dev/build/lint/test/setup shell scripts (wrapped by the Makefile)
├── .github/workflows/ CI pipelines
├── docker-compose.yml         Local development stack
├── docker-compose.prod.yml    Production stack
└── docs/              Additional documentation
```

See `INSTALLATION.md` for full setup instructions.

## Development model

This project is built **one module at a time** against an approved
architecture. Each module is implemented completely, reviewed, and approved
before the next begins. This repository currently contains:

- **Module 1 — Project Foundation** ✅
  Folder structure, frontend/backend scaffolding, shared package, Docker,
  Docker Compose, environment configuration, CI, logging, global error
  handling, linting/formatting, testing frameworks, and dev/prod scripts.
  Contains **no business logic, auth, database schema, upload, AI, template
  engine, rendering engine, preview, or PDF generation** — those are
  separate, upcoming modules.

## Quick start

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd universal-doc-template-platform

# 2. Bootstrap everything (installs deps, creates .env files from examples)
make setup

# 3. Fill in real secrets in .env, frontend/.env, backend/.env

# 4. Run the app
make dev            # runs frontend + backend locally, no Docker
# or
make docker-up      # runs everything in Docker
```

Frontend: http://localhost:5173
Backend docs: http://localhost:8000/docs
Health check: http://localhost:8000/api/v1/health

## Common commands

All available via `make help`-style discovery (open the `Makefile`), the
most common ones:

```bash
make dev             # run frontend + backend dev servers
make test            # run all tests (frontend + backend)
make lint            # lint frontend + backend
make format          # auto-format frontend + backend
make docker-up       # start full stack in Docker
make docker-down     # stop Docker stack
make build           # production build (frontend + shared)
```

## Contributing

- One module per pull request. See `.github/pull_request_template.md`.
- All code must pass `make lint` and `make test` before review.
- Do not introduce business logic outside the module currently being built.

## License

Proprietary — All rights reserved.
