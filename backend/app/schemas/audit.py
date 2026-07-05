"""
Audit log schemas.
Mirrors the `audit_logs` table (backend/sql/004_audit_logs.sql).
Foundation only — no endpoint exposes these yet.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogEntry(BaseModel):
    id: str
    company_id: str
    user_id: str | None = None
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime
