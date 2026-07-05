from unittest.mock import MagicMock, patch

from app.schemas.company import CurrentCompany
from app.schemas.parsed_document import ParsedDocumentMetadata

FAKE_COMPANY = CurrentCompany(id="company-1", name="Acme Inc", slug="acme", role="owner")

FAKE_PARSED_DOCUMENT = ParsedDocumentMetadata(
    id="parsed-1",
    company_id="company-1",
    file_id="file-1",
    schema_version="1.0",
    parser_name="image_parser",
    parser_version="1.0.0",
    status="completed",
    storage_path="company-1/file-1/parsed/1.0/1.0.0-x.json",
    unit_count=1,
    text_block_count=0,
    image_count=1,
    cell_grid_count=0,
    cell_count=0,
    character_count=0,
    duration_ms=12.3,
    error_message=None,
    created_at="2026-01-01T00:00:00Z",
)


def _mock_authenticated_user() -> MagicMock:
    fake_user = MagicMock(id="user-1", email="test@example.com")
    return MagicMock(user=fake_user)


def test_parse_file_requires_authentication(client):
    response = client.post("/api/v1/files/file-1/parse")
    assert response.status_code == 401


def test_parse_file_returns_parsed_document_metadata(client):
    fake_auth_response = _mock_authenticated_user()

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch("app.api.v1.parsing.parser_service.parse_file", return_value=FAKE_PARSED_DOCUMENT),
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.post(
            "/api/v1/files/file-1/parse", headers={"Authorization": "Bearer good-token"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "parsed-1"
    assert body["status"] == "completed"


def test_read_latest_parsed_document_requires_authentication(client):
    response = client.get("/api/v1/files/file-1/parsed")
    assert response.status_code == 401


def test_read_latest_parsed_document_returns_metadata(client):
    fake_auth_response = _mock_authenticated_user()

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.parsing.parser_service.get_latest_parsed_document",
            return_value=FAKE_PARSED_DOCUMENT,
        ),
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get(
            "/api/v1/files/file-1/parsed", headers={"Authorization": "Bearer good-token"}
        )

    assert response.status_code == 200
    assert response.json()["id"] == "parsed-1"
