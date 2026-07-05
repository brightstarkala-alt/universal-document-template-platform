-- Module 3: Company & Multi-Tenant Foundation
-- Audit log foundation only — no audit UI and no write call sites yet.
-- Future modules that mutate company-scoped resources record events here
-- via backend/app/services/audit_service.py.
--
-- Review and apply manually. Do not run automatically.

create table if not exists public.audit_logs (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references public.companies (id) on delete cascade,
    user_id uuid references auth.users (id) on delete set null,
    action text not null,
    entity_type text,
    entity_id text,
    metadata jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_audit_logs_company_id_created_at
    on public.audit_logs (company_id, created_at desc);

alter table public.audit_logs enable row level security;

-- A user may see audit rows only for a company they belong to.
create policy "audit_logs_select_own_company" on public.audit_logs
    for select
    using (
        exists (
            select 1
            from public.company_members m
            where m.company_id = audit_logs.company_id
              and m.user_id = auth.uid()
        )
    );

-- No insert/update/delete policies: audit rows are written exclusively by
-- the backend's service-role client (app/services/audit_service.py).
