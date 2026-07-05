"""
Health check endpoint.

Used by: Docker healthchecks, load balancers, uptime monitors, and CI smoke
tests. Intentionally has zero dependencies on the database/auth so it always
reflects whether the API process itself is alive.
"""

from datetime import UTC, datetime

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.common import HealthCheckResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(
        status="ok",
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
        timestamp=datetime.now(UTC).isoformat(),
    )
