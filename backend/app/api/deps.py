"""
FastAPI dependencies shared across API routes.

`get_current_user` is the single seam every protected route depends on to
verify a Supabase-issued JWT. It never decodes the token locally — it asks
Supabase's Auth server to validate it, so the backend does not need to
manage a JWT signing secret.
"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import UnauthorizedError
from app.core.supabase import get_supabase_admin
from app.schemas.auth import CurrentUser

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise UnauthorizedError("Missing bearer token.")

    try:
        response = get_supabase_admin().auth.get_user(credentials.credentials)
    except Exception as exc:
        raise UnauthorizedError("Invalid or expired session.") from exc

    user = response.user if response else None
    if user is None:
        raise UnauthorizedError("Invalid or expired session.")

    return CurrentUser(id=user.id, email=user.email)
