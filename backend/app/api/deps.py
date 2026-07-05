"""
FastAPI dependencies shared across API routes.

`get_current_user` is the single seam every protected route depends on to
verify a Supabase-issued JWT. It never decodes the token locally — it asks
Supabase's Auth server to validate it, so the backend does not need to
manage a JWT signing secret.

`get_current_company` builds on top of it to resolve the caller's tenant:
Current User -> Current Company -> Business Logic. Every tenant-scoped
route should depend on `get_current_company` rather than `get_current_user`
directly, since it is what stamps `request.state.company_id` — the signal
`TenantContextMiddleware` (app/core/middleware.py) checks for as a
defense-in-depth backstop against a future endpoint skipping tenant
validation.
"""

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.supabase import get_supabase_admin
from app.schemas.auth import CurrentUser
from app.schemas.company import CurrentCompany
from app.services import company_service

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


async def get_current_company(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentCompany:
    company = company_service.get_company_for_user(current_user.id)
    if company is None:
        raise ForbiddenError(
            "This account is not linked to a company.",
            code="NO_COMPANY_MEMBERSHIP",
        )

    request.state.company_id = company.id
    return company
