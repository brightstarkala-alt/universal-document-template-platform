"""
Resolves the authenticated user's company membership.

Every user belongs to exactly one company, enforced by UNIQUE(user_id) on
`company_members` (see backend/sql/002_company_members.sql). This is the
only place that queries that relationship — `get_current_company` in
app/api/deps.py is the sole caller.
"""

from app.core.supabase import get_supabase_admin
from app.schemas.company import CurrentCompany


def get_company_for_user(user_id: str) -> CurrentCompany | None:
    client = get_supabase_admin()
    response = (
        client.table("company_members")
        .select("role, companies(id, name, slug)")
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )

    row: dict[str, object] | None = response.data if response else None
    if not row:
        return None

    company = row.get("companies")
    if not isinstance(company, dict):
        return None

    return CurrentCompany(
        id=str(company["id"]),
        name=str(company["name"]),
        slug=str(company["slug"]),
        role=str(row["role"]),
    )
