"""
Verifies TenantContextMiddleware's defense-in-depth guarantee: a route
under the API prefix that never populates `request.state.company_id`
(i.e. it forgot to depend on `get_current_company`) has its response
replaced with a 500 instead of reaching the client.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.middleware import TenantContextMiddleware


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(TenantContextMiddleware)

    @app.get("/api/v1/unsafe-route")
    async def unsafe_route() -> dict[str, str]:
        return {"ok": "true"}

    @app.get("/api/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def test_blocks_protected_route_missing_company_context() -> None:
    client = TestClient(_build_test_app())
    response = client.get("/api/v1/unsafe-route")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "TENANT_CONTEXT_MISSING"


def test_allows_exempt_health_route_without_company_context() -> None:
    client = TestClient(_build_test_app())
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
