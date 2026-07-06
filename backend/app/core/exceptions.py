"""
Global exception hierarchy + FastAPI exception handlers.

Every error response returned by the API — expected or unexpected — follows
the same envelope shape (see `shared/src/types/index.ts::ApiErrorResponse`
on the frontend side, which this mirrors):

    {
        "success": false,
        "error": {
            "code": "SOME_ERROR_CODE",
            "message": "Human readable message",
            "details": { ... } | null,
            "requestId": "..."
        }
    }

Feature modules should raise `AppException` subclasses instead of generic
`HTTPException` so error codes stay consistent and machine-readable for the
frontend.
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppException(Exception):
    """Base class for all expected, application-raised errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "APP_ERROR"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = details
        super().__init__(message)


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"


class ValidationAppError(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "VALIDATION_ERROR"


class UnauthorizedError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHORIZED"


class ForbiddenError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"


class AIExtractionError(AppException):
    """Base class for Module 7 (AI Field Extraction) errors — the failure
    is upstream (OpenAI) or in reconciling its response, not the caller's
    request, so it maps to 502 rather than a 4xx."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "AI_EXTRACTION_ERROR"


class OpenAIUnavailableError(AIExtractionError):
    code = "OPENAI_UNAVAILABLE"


class ExtractionValidationError(AIExtractionError):
    code = "EXTRACTION_VALIDATION_ERROR"


class TemplateGenerationError(AppException):
    """Raised for internal Module 8 (Template Engine) failures. Unlike
    Module 7, there is no external dependency here (no OpenAI call, no
    re-parsing) — a failure is either malformed upstream data or a genuine
    bug, not something to retry, so it maps to 500 rather than 502."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "TEMPLATE_GENERATION_ERROR"


class PDFGenerationError(AppException):
    """Raised for internal Module 10 (PDF Generation) failures. Like
    `TemplateGenerationError`, there is no external dependency to retry
    against (WeasyPrint runs locally) — a failure is either a malformed
    `TemplateArtifact` or a genuine bug, so it maps to 500 rather than 502."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "PDF_GENERATION_ERROR"


def build_error_body(
    request: Request, code: str, message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Shared error envelope builder — also used by TenantContextMiddleware."""
    request_id = getattr(request.state, "request_id", None)
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "requestId": request_id,
        },
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            "Handled application exception",
            extra={"code": exc.code, "status_code": exc.status_code, "path": request.url.path},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_body(request, exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.info(
            "Request validation failed", extra={"errors": exc.errors(), "path": request.url.path}
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=build_error_body(
                request,
                "VALIDATION_ERROR",
                "The request payload failed validation.",
                {"errors": exc.errors()},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_body(request, "HTTP_ERROR", str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception",
            exc_info=exc,
            extra={"path": request.url.path},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=build_error_body(
                request,
                "INTERNAL_SERVER_ERROR",
                "An unexpected error occurred. Please try again later.",
            ),
        )
