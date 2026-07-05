# Universal Document Template Platform (UDTP)

Version: 1.0

---

# Vision

Build a production-grade SaaS platform that allows any business document to become a reusable template.

Workflow

Upload Document

↓

Extract Variables

↓

Generate HTML Template

↓

Live Preview

↓

Generate Identical PDF

↓

REST API

The uploaded document, preview and generated PDF must look visually identical.

Only variable values may change.

Nothing else should move.

---

# Supported Input Formats

- PDF
- DOCX
- XLS
- XLSX
- PNG
- JPG
- JPEG
- WEBP

Future

- TIFF

No PowerPoint.

No CAD.

No SVG.

---

# Technology Stack

Frontend

- React
- Vite
- TypeScript
- Tailwind CSS
- TanStack Query

Backend

- FastAPI

Database

- Existing Supabase Project

Authentication

- Existing Supabase Auth

Storage

- Existing Supabase Storage

PDF Engine

- WeasyPrint

AI

- OpenAI

---

# Golden Rule

The uploaded document becomes the template.

Never recreate the design.

Never approximate the layout.

Never redraw the document.

The generated HTML template is the single source of truth.

Preview and PDF must always render from the same HTML template.

---

# Product Architecture

Frontend

Authentication

↓

Dashboard

↓

Template Management

↓

Document Preview

↓

Generated Documents

↓

Settings

↓

REST API

Backend

Authentication

↓

Upload

↓

Parser

↓

AI Extraction

↓

Template Engine

↓

Renderer

↓

PDF Generator

↓

Storage

↓

REST API

---

# Multi Tenant

Company

↓

Users

↓

Templates

↓

Generated Documents

↓

API Keys

↓

Audit Logs

Every company only sees its own data.

No shared records.

All queries must be tenant-aware.

---

# Authentication

Use the EXISTING Supabase project.

Never create another Supabase project.

Never create another authentication provider.

Authentication uses Supabase Auth.

---

# Storage

All uploaded documents are stored in Existing Supabase Storage.

Generated PDFs are also stored there.

No local storage.

---

# Template Engine

Every uploaded document becomes

HTML

+

CSS

+

Variables

Never use coordinate overlays.

Never edit the uploaded PDF directly.

Never rely on OCR coordinates for rendering.

HTML is the template.

---

# Variable Extraction

AI identifies

- Text fields
- Dates
- Numbers
- Currency
- Tables
- Repeating sections
- Images
- Checkboxes

Code stores them.

---

# Preview Engine

Preview renders HTML.

Nothing else.

---

# PDF Engine

Generate PDF from exactly the same HTML used by Preview.

There must never be separate Preview and PDF templates.

One HTML.

One CSS.

Two outputs.

---

# API

Future API

POST

/generate

Input

Template ID

JSON values

Output

Generated PDF

The API must not depend on the UI.

---

# Database Rules

Use the EXISTING Supabase project.

Claude must never create another project.

Whenever database changes are required

Generate SQL migration files only.

Never execute SQL.

The developer will execute migrations manually.

---

# Coding Rules

One module at a time.

No partial implementations.

No placeholder business logic.

Every module must pass

- Build
- Typecheck
- Lint
- Tests

before moving to the next module.

---

# Folder Responsibilities

frontend/

React application.

backend/

FastAPI services.

shared/

Shared types and constants.

docs/

Architecture and module documentation.

scripts/

Development scripts.

docker/

Containers.

.github/

CI/CD.

---

# Module Order

Module 1

Foundation

✅ Completed

Module 2

Authentication + Multi Tenant

Module 3

Database + RLS

Module 4

Upload Engine

Module 5

Parser Engine

Module 6

AI Variable Extraction

Module 7

Template Engine

Module 8

Live Preview

Module 9

PDF Generation

Module 10

Template Management

Module 11

Generated Documents

Module 12

REST API

Module 13

Settings

Module 14

Performance & Optimization

---

# Development Rules

Claude is the developer.

Architecture is defined by this document.

Claude must not redesign the project.

Claude must not change the technology stack.

Claude must not introduce new frameworks.

Claude must stop after completing each module and wait for approval.

---

# End Goal

A Universal Document Template Platform where users can upload any supported business document, automatically convert it into a reusable template, preview it with different data, generate visually identical PDFs, and expose the same functionality through secure REST APIs.