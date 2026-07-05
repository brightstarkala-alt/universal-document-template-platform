"""
Cross-cutting Pydantic schemas shared by multiple endpoints.
Mirrors `shared/src/types/index.ts` on the frontend — keep both in sync.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class HealthCheckResponse(BaseModel):
    status: str
    environment: str
    version: str
    timestamp: str


class ApiSuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T


class ApiErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, object] | None = None
    requestId: str | None = None


class ApiErrorResponse(BaseModel):
    success: bool = False
    error: ApiErrorDetail
