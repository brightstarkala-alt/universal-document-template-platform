from unittest.mock import MagicMock, patch

from app.schemas.company import CurrentCompany
from app.schemas.template_metadata import TemplateMetadata

FAKE_COMPANY = CurrentCompany(id="company-1", name="Acme Inc", slug="acme", role="owner")

FAKE_TEMPLATE = TemplateMetadata(
    id="template-1",
    company_id="company-1",
    file_id="file-1",
    source_ai_extraction_id="extraction-1",
    source_parsed_document_id="parsed-1",
    version=1,
    schema_version="1.0",
    generator_version="1.0",
    status="completed",
    storage_path="company-1/file-1/templates/1.0/1.0-v1-x.json",
    field_count=3,
    section_count=1,
    asset_count=1,
    page_count=1,
    duration_ms=15.0,
    error_message=None,
    created_at="2026-01-01T00:00:00Z",
)


def _mock_authenticated_user() -> MagicMock:
    fake_user = MagicMock(id="user-1", email="test@example.com")
    return MagicMock(user=fake_user)


def test_generate_template_requires_authentication(client):
    response = client.post("/api/v1/files/file-1/template")
    assert response.status_code == 401


def test_generate_template_returns_template_metadata(client):
    fake_auth_response = _mock_authenticated_user()

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.template_engine.template_engine_service.generate_template",
            return_value=FAKE_TEMPLATE,
        ) as mock_generate,
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.post(
            "/api/v1/files/file-1/template", headers={"Authorization": "Bearer good-token"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "template-1"
    assert body["version"] == 1
    mock_generate.assert_called_once_with(company_id="company-1", file_id="file-1", force=False)


def test_generate_template_passes_force_query_param(client):
    fake_auth_response = _mock_authenticated_user()

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.template_engine.template_engine_service.generate_template",
            return_value=FAKE_TEMPLATE,
        ) as mock_generate,
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.post(
            "/api/v1/files/file-1/template?force=true",
            headers={"Authorization": "Bearer good-token"},
        )

    assert response.status_code == 200
    mock_generate.assert_called_once_with(company_id="company-1", file_id="file-1", force=True)


def test_read_latest_template_requires_authentication(client):
    response = client.get("/api/v1/files/file-1/template")
    assert response.status_code == 401


def test_read_latest_template_returns_metadata(client):
    fake_auth_response = _mock_authenticated_user()

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.template_engine.template_engine_service.get_latest_template",
            return_value=FAKE_TEMPLATE,
        ),
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get(
            "/api/v1/files/file-1/template", headers={"Authorization": "Bearer good-token"}
        )

    assert response.status_code == 200
    assert response.json()["id"] == "template-1"


def test_read_template_versions_returns_list(client):
    fake_auth_response = _mock_authenticated_user()

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.template_engine.template_engine_service.list_templates",
            return_value=[FAKE_TEMPLATE],
        ),
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get(
            "/api/v1/files/file-1/template/versions",
            headers={"Authorization": "Bearer good-token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body[0]["id"] == "template-1"


def test_read_template_version_returns_metadata(client):
    fake_auth_response = _mock_authenticated_user()

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.template_engine.template_engine_service.get_template_by_version",
            return_value=FAKE_TEMPLATE,
        ) as mock_get_version,
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get(
            "/api/v1/files/file-1/template/1", headers={"Authorization": "Bearer good-token"}
        )

    assert response.status_code == 200
    assert response.json()["version"] == 1
    mock_get_version.assert_called_once_with(company_id="company-1", file_id="file-1", version=1)
