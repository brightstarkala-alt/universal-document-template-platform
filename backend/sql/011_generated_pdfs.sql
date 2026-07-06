-- Module 10: PDF Generation
-- One row per PDF-generation attempt for a file. Rows are append-only and
-- versioned exactly like `templates`/`ai_extractions`/`parsed_documents`:
-- `version` increments per `file_id`, and a row is never updated in place
-- once it reaches a terminal status — a re-run (new generator_version, or
-- a re-run against a newer template) always inserts a new row.
--
-- The generated PDF binary lives in Storage
-- (`{company_id}/{file_id}/pdfs/{generator_version}-v{version}-*.pdf` in
-- the existing `documents` bucket); this table is queryable metadata only,
-- mirroring how `templates` stores `storage_path` rather than the blob
-- itself.
--
-- Review and apply manually. Do not run automatically.

create table if not exists public.generated_pdfs (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references public.companies (id) on delete cascade,
    file_id uuid not null references public.files (id) on delete cascade,
    source_template_id uuid not null references public.templates (id) on delete cascade,
    version integer not null check (version > 0),
    schema_version text not null,
    generator_version text not null,
    status text not null check (
        status in ('pending', 'processing', 'completed', 'completed_with_errors', 'failed')
    ),
    storage_path text,
    page_count integer,
    size_bytes integer,
    duration_ms double precision,
    error_message text,
    created_at timestamptz not null default now(),
    unique (file_id, version)
);

create index if not exists idx_generated_pdfs_file_id_version
    on public.generated_pdfs (file_id, version desc);

-- Cache lookup: "has this exact template already been turned into a PDF
-- by this generator version?" — checked before regenerating.
create index if not exists idx_generated_pdfs_cache_lookup
    on public.generated_pdfs (file_id, source_template_id, generator_version, schema_version)
    where status = 'completed';

alter table public.generated_pdfs enable row level security;

-- A user may see generated PDFs only for companies they belong to.
create policy "generated_pdfs_select_own_company" on public.generated_pdfs
    for select
    using (
        exists (
            select 1
            from public.company_members m
            where m.company_id = generated_pdfs.company_id
              and m.user_id = auth.uid()
        )
    );

-- No insert/update/delete policies: rows are written exclusively by the
-- backend's service-role client (app/services/pdf_generation_service.py).
