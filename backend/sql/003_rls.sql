-- Module 3: Company & Multi-Tenant Foundation
-- Row Level Security for `companies` and `company_members`.
--
-- The backend verifies the caller's identity itself (Supabase Auth JWT
-- verification in backend/app/api/deps.py) and reads/writes through the
-- service-role key, which bypasses RLS by design. These policies are the
-- last line of defense in case either table is ever queried directly with
-- a user's anon/authenticated JWT (e.g. a future direct-to-Supabase code
-- path from the frontend).
--
-- Review and apply manually. Do not run automatically.

alter table public.companies enable row level security;
alter table public.company_members enable row level security;

-- A user may see a company only if they have a membership row for it.
create policy "companies_select_own" on public.companies
    for select
    using (
        exists (
            select 1
            from public.company_members m
            where m.company_id = companies.id
              and m.user_id = auth.uid()
        )
    );

-- A user may see only their own membership row.
create policy "company_members_select_own" on public.company_members
    for select
    using (user_id = auth.uid());

-- No insert/update/delete policies are defined for either table: writes
-- happen exclusively through the backend's service-role client, never
-- directly from a user's session.
