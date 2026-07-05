-- Module 3: Company & Multi-Tenant Foundation
-- Creates the `companies` table — the root tenant entity every future
-- resource (templates, documents, api keys, audit logs) will belong to.
--
-- Review and apply manually. Do not run automatically.

create table if not exists public.companies (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    slug text not null unique,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_companies_slug on public.companies (slug);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists trg_companies_updated_at on public.companies;
create trigger trg_companies_updated_at
    before update on public.companies
    for each row
    execute function public.set_updated_at();
