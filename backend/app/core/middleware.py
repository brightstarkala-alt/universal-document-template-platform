"""
Cross-cutting HTTP middleware.

- RequestIdMiddleware: attaches a unique request ID to every request/response
  so a single request can be traced through logs end-to-end. Available to
  exception handlers via `request.state.request_id`.
- AccessLogMiddleware: logs one structured line per request with method,
  path, status code, and duration.
- TenantContextMiddleware: defense-in-depth backstop for multi-tenancy.
"""

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exceptions import build_error_body
from app.core.logging import get_logger

logger = get_logger("app.access")

REQUEST_ID_HEADER = "X-Request-ID"

# Routes that legitimately have no company to resolve — auth itself and
# infra endpoints. Everything else under the API prefix is tenant-scoped.
TENANT_EXEMPT_PATH_PREFIXES: tuple[str, ...] = (
    f"{settings.API_V1_PREFIX}/health",
    f"{settings.API_V1_PREFIX}/auth",
)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER, str(uuid.uuid4()))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return response


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Defense-in-depth guard for the Current User -> Current Company ->
    Business Logic flow.

    `get_current_company` (app/api/deps.py) is what actually resolves and
    validates a request's company; on success it stamps
    `request.state.company_id`. This middleware does not repeat that
    lookup — it only checks, once the route has run, that any endpoint
    outside the exempt prefixes actually populated that state. A future
    endpoint wired up without `get_current_company` would otherwise
    silently serve a response with no tenant validation; this turns that
    into a 500 instead of letting it reach the client.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        requires_tenant = path.startswith(settings.API_V1_PREFIX) and not any(
            path.startswith(prefix) for prefix in TENANT_EXEMPT_PATH_PREFIXES
        )

        response = await call_next(request)

        if (
            requires_tenant
            and response.status_code < 400
            and getattr(request.state, "company_id", None) is None
        ):
            logger.error(
                "Tenant context missing on a protected route; blocking response",
                extra={"path": path},
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=build_error_body(
                    request,
                    "TENANT_CONTEXT_MISSING",
                    "Tenant context was not established for this request.",
                ),
            )

        return response
