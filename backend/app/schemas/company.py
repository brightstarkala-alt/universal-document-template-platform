"""
Company schemas.
Mirrors `shared/src/types/index.ts` on the frontend — keep both in sync.
"""

from pydantic import BaseModel


class CurrentCompany(BaseModel):
    """The authenticated user's company, resolved from `company_members`."""

    id: str
    name: str
    slug: str
    role: str
