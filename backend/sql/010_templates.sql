-- Module 8: Template Engine
-- One row per template-generation attempt for a file. Rows are append-only
-- and versioned exactly like `ai_extractions` and `parsed_documents`:
-- `version` increments per `file_id`, and a row is never updated in place
-- once it reaches a terminal status — a re-run (new generator_version, or
-- a re-run against a newer AI extraction) always inserts a new row.
--
-- The full template artifact — `{ html, css, manifest }` as one JSON object
-- (see backend/app/schemas/template.py::TemplateArtifact) — lives in Storage
-- (`{company_id}/{file_id}/templates/{schema_version}/{generator_version}-v{version}-*.json`
-- in the existing `documents` bucket); this table is queryable metadata
-- only, mirroring how `parsed_documents`/`ai_extractions` store `storage_path`
-- rather than the blob itself.
--
-- Review and apply manually. Do not run automatically.

create table if not exists public.templates (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references public.companies (id) on delete cascade,
    file_id uuid not null references public.files (id) on delete cascade,
    source_ai_extraction_id uuid not null references public.ai_extractions (id) on delete cascade,
    source_parsed_document_id uuid not null references public.parsed_documents (id) on delete cascade,
    version integer not null check (version > 0),
    schema_version text not null,
    generator_version text not null,
    status text not null check (
        status in ('pending', 'processing', 'completed', 'completed_with_errors', 'failed')
    ),
    storage_path text,
    field_count integer,
    section_count integer,
    asset_count integer,
    page_count integer,
    duration_ms double precision,
    error_message text,
    created_at timestamptz not null default now(),
    unique (file_id, version)
);

create index if not exists idx_templates_file_id_version
    on public.templates (file_id, version desc);

-- Cache lookup: "has this exact AI extraction already been turned into a
-- template by this generator version?" — checked before regenerating.
create index if not exists idx_templates_cache_lookup
    on public.templates (file_id, source_ai_extraction_id, generator_version, schema_version)
    where status = 'completed';

alter table public.templates enable row level security;

-- A user may see templates only for companies they belong to.
create policy "templates_select_own_company" on public.templates
    for select
    using (
        exists (
            select 1
            from public.company_members m
            where m.company_id = templates.company_id
              and m.user_id = auth.uid()
        )
    );

-- No insert/update/delete policies: rows are written exclusively by the
-- backend's service-role client (app/services/template_engine_service.py).
