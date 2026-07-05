"""
Auth-related schemas.
Mirrors `shared/src/types/index.ts` on the frontend — keep both in sync.
"""

from pydantic import BaseModel


class CurrentUser(BaseModel):
    """Authenticated user identity derived from a verified Supabase JWT."""

    id: str
    email: str | None = None
