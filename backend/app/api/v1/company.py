"""
Company-scoped endpoints.

`/companies/me` is the first endpoint gated by `get_current_company` rather
than just `get_current_user` — it proves the full
Current User -> Current Company -> Business Logic chain end-to-end.
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_company
from app.schemas.company import CurrentCompany

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/me", response_model=CurrentCompany)
async def read_current_company(
    current_company: CurrentCompany = Depends(get_current_company),
) -> CurrentCompany:
    return current_company
