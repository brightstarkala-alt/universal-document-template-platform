-- Module 5: Upload Engine
-- Hardens `public.files` (created in backend/sql/005_files.sql) now that
-- the Upload Engine is its first real writer.
--
--   - `created_at` -> `uploaded_at`: matches the upload domain language
--     used throughout this module. The column's default `now()` and
--     semantics are unchanged, only the name.
--   - `extension`: stored explicitly at upload time instead of being
--     re-derived from `original_filename` on every read.
--   - `checksum_sha256` is now NOT NULL: every upload computes and stores
--     a SHA-256 digest of the file's bytes, so the column no longer needs
--     to tolerate nulls.
--
-- No upload endpoint existed before this module, so there is no existing
-- data to backfill.
--
-- Review and apply manually. Do not run automatically.

alter table public.files rename column created_at to uploaded_at;

alter index if exists public.idx_files_company_id_created_at
    rename to idx_files_company_id_uploaded_at;

alter table public.files add column extension text not null;

alter table public.files alter column checksum_sha256 set not null;
