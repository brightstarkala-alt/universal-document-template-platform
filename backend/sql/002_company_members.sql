-- Module 3: Company & Multi-Tenant Foundation
-- Links a Supabase-authenticated user to exactly one company.
--
-- UNIQUE(user_id) is what enforces "every user belongs to exactly one
-- company" at the database level — a second membership row for the same
-- user is rejected by the constraint, not just by application code.
--
-- Review and apply manually. Do not run automatically.

create table if not exists public.company_members (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references public.companies (id) on delete cascade,
    user_id uuid not null references auth.users (id) on delete cascade,
    role text not null default 'owner' check (role in ('owner', 'admin', 'member')),
    created_at timestamptz not null default now(),
    unique (user_id)
);

create index if not exists idx_company_members_company_id on public.company_members (company_id);
