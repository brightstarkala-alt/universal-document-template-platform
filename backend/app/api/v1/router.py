"""
Aggregates all v1 feature routers into a single APIRouter mounted at
`settings.API_V1_PREFIX` in `app.main`. Each new feature module should add
its router here rather than registering directly on the FastAPI app.
"""

from fastapi import APIRouter

from app.api.v1 import auth, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
