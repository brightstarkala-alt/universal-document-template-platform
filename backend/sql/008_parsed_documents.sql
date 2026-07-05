-- Module 6: Parser Engine
-- One row per parse attempt of a file into the Universal Document Model
-- (UDM). A file may be parsed more than once (parser upgrades, retries);
-- rows are append-only, never overwritten — the latest by `created_at` is
-- the current result. The UDM JSON itself lives in Storage
-- (`{company_id}/{file_id}/parsed/{schema_version}/{parser_version}-*.json`
-- in the existing `documents` bucket); this table is queryable metadata
-- only, mirroring how `files` stores `storage_path` rather than bytes.
--
-- `status` intentionally includes `pending` even though Module 6 always
-- writes `processing` directly (there is no job queue yet) — so that if
-- parsing later moves to a background-job model, no status values need
-- to change, only which code path writes them.
--
-- Review and apply manually. Do not run automatically.

create table if not exists public.parsed_documents (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references public.companies (id) on delete cascade,
    file_id uuid not null references public.files (id) on delete cascade,
    schema_version text not null,
    parser_name text not null,
    parser_version text not null,
    status text not null check (
        status in ('pending', 'processing', 'completed', 'completed_with_errors', 'failed')
    ),
    storage_path text,
    unit_count integer,
    text_block_count integer,
    image_count integer,
    cell_grid_count integer,
    cell_count integer,
    character_count integer,
    duration_ms double precision,
    error_message text,
    created_at timestamptz not null default now()
);

create index if not exists idx_parsed_documents_file_id_created_at
    on public.parsed_documents (file_id, created_at desc);

alter table public.parsed_documents enable row level security;

-- A user may see parse results only for companies they belong to.
create policy "parsed_documents_select_own_company" on public.parsed_documents
    for select
    using (
        exists (
            select 1
            from public.company_members m
            where m.company_id = parsed_documents.company_id
              and m.user_id = auth.uid()
        )
    );

-- No insert/update/delete policies: rows are written exclusively by the
-- backend's service-role client (app/services/parser_service.py).
