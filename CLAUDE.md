# Universal Document Template Platform

## Product Vision

Build a production-ready SaaS platform that converts uploaded business documents into reusable templates.

## Tech Stack

Frontend
- React
- Vite
- TypeScript
- Tailwind CSS

Backend
- FastAPI

Database
- Existing Supabase Project

Authentication
- Existing Supabase Auth

Storage
- Existing Supabase Storage

PDF
- WeasyPrint

AI
- OpenAI

## Rules

- Never create a new GitHub repository.
- Never create a new Supabase project.
- Always use the existing project.
- Read secrets only from environment variables.
- Generate SQL migration files only.
- Never execute SQL automatically.
- Build one approved module at a time.
- Stop after each module and wait for approval.

## Golden Rule

Uploaded Document

↓

HTML Template

↓

Live Preview

↓

Generated PDF

All must be visually identical.

Only variable values may change.

Nothing else moves.

## Supported Formats

- PDF
- DOCX
- XLS
- XLSX
- PNG
- JPG
- JPEG
- WEBP

## Development Standard

Every module must pass:

- Build
- Lint
- Typecheck
- Tests

before completion.