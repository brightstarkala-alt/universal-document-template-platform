"""
Authentication-protected endpoints.

`/auth/me` proves `get_current_user` actually gates access — the first real
protected route. Feature modules add their own routers behind the same
dependency rather than duplicating verification logic.
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.schemas.auth import CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=CurrentUser)
async def read_current_user(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    return current_user
