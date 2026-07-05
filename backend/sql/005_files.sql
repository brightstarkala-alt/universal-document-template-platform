-- Module 4: Storage Foundation
-- File metadata for objects stored in Supabase Storage. One row per stored
-- object, always scoped to a company. The `storage_path` is the full
-- object key within `storage_bucket` (see backend/sql/006_storage_bucket.sql
-- for the bucket + folder-based RLS): `{company_id}/{file_id}{extension}`.
--
-- Review and apply manually. Do not run automatically.

create table if not exists public.files (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references public.companies (id) on delete cascade,
    storage_bucket text not null default 'documents',
    storage_path text not null unique,
    original_filename text not null,
    content_type text not null,
    size_bytes bigint not null check (size_bytes > 0),
    checksum_sha256 text,
    uploaded_by uuid references auth.users (id) on delete set null,
    created_at timestamptz not null default now()
);

create index if not exists idx_files_company_id_created_at
    on public.files (company_id, created_at desc);

alter table public.files enable row level security;

-- A user may see file metadata only for companies they belong to.
create policy "files_select_own_company" on public.files
    for select
    using (
        exists (
            select 1
            from public.company_members m
            where m.company_id = files.company_id
              and m.user_id = auth.uid()
        )
    );

-- No insert/update/delete policies: file rows are written exclusively by
-- the backend's service-role client (app/services/file_service.py).
