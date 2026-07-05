-- Module 4: Storage Foundation
-- Creates the single private `documents` bucket every stored file lives in,
-- and RLS policies on `storage.objects` that mirror the Company -> Folder ->
-- File isolation used everywhere else: the first path segment of an object's
-- name must be a company_id the requesting user belongs to.
--
-- Path convention (see backend/app/services/file_service.py):
--   {company_id}/{file_id}{extension}
--
-- This migration does not create the bucket via the Supabase Storage API —
-- it is a SQL migration file only. Review and apply manually. Do not run
-- automatically.

insert into storage.buckets (id, name, public)
values ('documents', 'documents', false)
on conflict (id) do nothing;

-- A user may read an object only if its first path segment (the company_id
-- folder) matches a company they belong to.
create policy "documents_select_own_company_folder" on storage.objects
    for select
    using (
        bucket_id = 'documents'
        and exists (
            select 1
            from public.company_members m
            where m.user_id = auth.uid()
              and m.company_id::text = (storage.foldername(name))[1]
        )
    );

-- No insert/update/delete policies: objects are written and removed
-- exclusively by the backend's service-role client
-- (app/services/storage_service.py), never directly from a user's session.
