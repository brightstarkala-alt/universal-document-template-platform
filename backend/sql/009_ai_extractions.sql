-- Module 7: AI Field Extraction
-- One row per extraction attempt of a parsed document's Universal Document
-- Model (UDM) into semantic fields/tables. Rows are append-only and
-- versioned: `version` increments per `file_id` and a row is never updated
-- in place once it reaches a terminal status (`completed`,
-- `completed_with_errors`, `failed`) — a re-run (new prompt version, model
-- change, or explicit re-extraction) always inserts a new row with the next
-- version instead of overwriting an earlier result, so template authors can
-- always trace which extraction produced a given template's fields.
--
-- The full `AIFieldExtractionResult` JSON (fields + tables) lives in Storage
-- (`{company_id}/{file_id}/extracted/{schema_version}/{prompt_version}-v{version}-*.json`
-- in the existing `documents` bucket); this table is queryable metadata
-- only, mirroring `parsed_documents` (backend/sql/008_parsed_documents.sql).
--
-- Deliberately excluded: any calculated OpenAI dollar cost. Cost varies with
-- pricing that changes independently of this schema; storing a snapshot
-- would silently go stale. `model` + `prompt_tokens` + `completion_tokens`
-- are stored instead, which is enough to derive cost at read time against
-- current pricing if ever needed.
--
-- Review and apply manually. Do not run automatically.

create table if not exists public.ai_extractions (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references public.companies (id) on delete cascade,
    file_id uuid not null references public.files (id) on delete cascade,
    parsed_document_id uuid not null references public.parsed_documents (id) on delete cascade,
    version integer not null check (version > 0),
    schema_version text not null,
    source_checksum_sha256 text not null,
    model text not null,
    prompt_version text not null,
    status text not null check (
        status in ('pending', 'processing', 'completed', 'completed_with_errors', 'failed')
    ),
    storage_path text,
    field_count integer,
    table_count integer,
    low_confidence_count integer,
    prompt_tokens integer,
    completion_tokens integer,
    duration_ms double precision,
    error_message text,
    created_at timestamptz not null default now(),
    unique (file_id, version)
);

create index if not exists idx_ai_extractions_file_id_version
    on public.ai_extractions (file_id, version desc);

-- Cache lookup: "has this exact file content already been extracted with
-- this model/prompt?" — checked before spending any OpenAI tokens.
create index if not exists idx_ai_extractions_cache_lookup
    on public.ai_extractions (file_id, source_checksum_sha256, model, prompt_version, schema_version)
    where status = 'completed';

alter table public.ai_extractions enable row level security;

-- A user may see extraction results only for companies they belong to.
create policy "ai_extractions_select_own_company" on public.ai_extractions
    for select
    using (
        exists (
            select 1
            from public.company_members m
            where m.company_id = ai_extractions.company_id
              and m.user_id = auth.uid()
        )
    );

-- No insert/update/delete policies: rows are written exclusively by the
-- backend's service-role client (app/services/ai_extraction_service.py).
