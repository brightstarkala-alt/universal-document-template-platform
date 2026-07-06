"""
Aggregates all v1 feature routers into a single APIRouter mounted at
`settings.API_V1_PREFIX` in `app.main`. Each new feature module should add
its router here rather than registering directly on the FastAPI app.
"""

from fastapi import APIRouter

from app.api.v1 import ai_extraction, auth, company, files, health, parsing

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(company.router)
api_router.include_router(files.router)
api_router.include_router(parsing.router)
api_router.include_router(ai_extraction.router)
