from unittest.mock import MagicMock, patch

from app.schemas.company import CurrentCompany
from app.schemas.file import FileMetadata, SignedUrlResponse

FAKE_COMPANY = CurrentCompany(id="company-1", name="Acme Inc", slug="acme", role="owner")

FAKE_FILE = FileMetadata(
    id="file-1",
    company_id="company-1",
    storage_bucket="documents",
    storage_path="company-1/file-1.pdf",
    original_filename="invoice.pdf",
    content_type="application/pdf",
    size_bytes=2,
    checksum_sha256=None,
    uploaded_by="user-1",
    created_at="2026-01-01T00:00:00Z",
)


def test_list_files_requires_authentication(client):
    response = client.get("/api/v1/files")
    assert response.status_code == 401


def test_list_files_returns_company_scoped_files(client):
    fake_user = MagicMock(id="user-1", email="test@example.com")
    fake_auth_response = MagicMock(user=fake_user)

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch("app.api.v1.files.file_service.list_files", return_value=[FAKE_FILE]),
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get("/api/v1/files", headers={"Authorization": "Bearer good-token"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == "file-1"


def test_read_file_returns_metadata(client):
    fake_user = MagicMock(id="user-1", email="test@example.com")
    fake_auth_response = MagicMock(user=fake_user)

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch("app.api.v1.files.file_service.get_file", return_value=FAKE_FILE),
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get(
            "/api/v1/files/file-1", headers={"Authorization": "Bearer good-token"}
        )

    assert response.status_code == 200
    assert response.json()["id"] == "file-1"


def test_read_file_signed_url_returns_url(client):
    fake_user = MagicMock(id="user-1", email="test@example.com")
    fake_auth_response = MagicMock(user=fake_user)
    fake_signed_url = SignedUrlResponse(
        url="https://example.supabase.co/signed/file-1.pdf", expires_in=300
    )

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch("app.api.v1.files.file_service.get_download_url", return_value=fake_signed_url),
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get(
            "/api/v1/files/file-1/signed-url", headers={"Authorization": "Bearer good-token"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["url"] == "https://example.supabase.co/signed/file-1.pdf"
    assert body["expires_in"] == 300
