from unittest.mock import MagicMock, patch

from app.schemas.ai_extraction_metadata import AIExtractionMetadata
from app.schemas.company import CurrentCompany

FAKE_COMPANY = CurrentCompany(id="company-1", name="Acme Inc", slug="acme", role="owner")

FAKE_EXTRACTION = AIExtractionMetadata(
    id="extraction-1",
    company_id="company-1",
    file_id="file-1",
    parsed_document_id="parsed-1",
    version=1,
    schema_version="1.0",
    source_checksum_sha256="checksum-abc",
    model="gpt-4o-mini",
    prompt_version="2026-07-06.1",
    status="completed",
    storage_path="company-1/file-1/extracted/1.0/2026-07-06.1-v1-x.json",
    field_count=3,
    table_count=1,
    low_confidence_count=0,
    prompt_tokens=120,
    completion_tokens=40,
    duration_ms=850.0,
    error_message=None,
    created_at="2026-01-01T00:00:00Z",
)


def _mock_authenticated_user() -> MagicMock:
    fake_user = MagicMock(id="user-1", email="test@example.com")
    return MagicMock(user=fake_user)


def test_extract_fields_requires_authentication(client):
    response = client.post("/api/v1/files/file-1/extract")
    assert response.status_code == 401


def test_extract_fields_returns_extraction_metadata(client):
    fake_auth_response = _mock_authenticated_user()

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.ai_extraction.ai_extraction_service.extract_fields",
            return_value=FAKE_EXTRACTION,
        ) as mock_extract,
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.post(
            "/api/v1/files/file-1/extract", headers={"Authorization": "Bearer good-token"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "extraction-1"
    assert body["version"] == 1
    mock_extract.assert_called_once_with(company_id="company-1", file_id="file-1", force=False)


def test_extract_fields_passes_force_query_param(client):
    fake_auth_response = _mock_authenticated_user()

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.ai_extraction.ai_extraction_service.extract_fields",
            return_value=FAKE_EXTRACTION,
        ) as mock_extract,
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.post(
            "/api/v1/files/file-1/extract?force=true",
            headers={"Authorization": "Bearer good-token"},
        )

    assert response.status_code == 200
    mock_extract.assert_called_once_with(company_id="company-1", file_id="file-1", force=True)


def test_read_latest_extraction_requires_authentication(client):
    response = client.get("/api/v1/files/file-1/extracted")
    assert response.status_code == 401


def test_read_latest_extraction_returns_metadata(client):
    fake_auth_response = _mock_authenticated_user()

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.ai_extraction.ai_extraction_service.get_latest_extraction",
            return_value=FAKE_EXTRACTION,
        ),
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get(
            "/api/v1/files/file-1/extracted", headers={"Authorization": "Bearer good-token"}
        )

    assert response.status_code == 200
    assert response.json()["id"] == "extraction-1"


def test_read_extraction_versions_returns_list(client):
    fake_auth_response = _mock_authenticated_user()

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.ai_extraction.ai_extraction_service.list_extractions",
            return_value=[FAKE_EXTRACTION],
        ),
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get(
            "/api/v1/files/file-1/extracted/versions",
            headers={"Authorization": "Bearer good-token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body[0]["id"] == "extraction-1"


def test_read_extraction_version_returns_metadata(client):
    fake_auth_response = _mock_authenticated_user()

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.ai_extraction.ai_extraction_service.get_extraction_by_version",
            return_value=FAKE_EXTRACTION,
        ) as mock_get_version,
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get(
            "/api/v1/files/file-1/extracted/1", headers={"Authorization": "Bearer good-token"}
        )

    assert response.status_code == 200
    assert response.json()["version"] == 1
    mock_get_version.assert_called_once_with(company_id="company-1", file_id="file-1", version=1)
