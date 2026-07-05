"""
Audit log foundation.

Writes rows to `public.audit_logs` (see backend/sql/004_audit_logs.sql).
This module only provides the write primitive — no other module in this
codebase calls it yet, and no audit UI exists. Future modules that mutate
company-scoped resources should call `record_event` after the mutation
succeeds.
"""

from typing import Any

from app.core.supabase import get_supabase_admin


def record_event(
    *,
    company_id: str,
    user_id: str | None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    client = get_supabase_admin()
    client.table("audit_logs").insert(
        {
            "company_id": company_id,
            "user_id": user_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "metadata": metadata,
        }
    ).execute()
