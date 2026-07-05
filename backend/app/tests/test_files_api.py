import hashlib
from unittest.mock import MagicMock, patch

import pytest

from app.api.v1.files import _check_declared_content_length
from app.core.config import settings
from app.core.exceptions import ValidationAppError
from app.schemas.company import CurrentCompany
from app.schemas.file import FileMetadata, SignedUrlResponse

FAKE_COMPANY = CurrentCompany(id="company-1", name="Acme Inc", slug="acme", role="owner")

FAKE_FILE = FileMetadata(
    id="file-1",
    company_id="company-1",
    storage_bucket="documents",
    storage_path="company-1/file-1.pdf",
    original_filename="invoice.pdf",
    extension=".pdf",
    content_type="application/pdf",
    size_bytes=2,
    checksum_sha256=hashlib.sha256(b"hi").hexdigest(),
    uploaded_by="user-1",
    uploaded_at="2026-01-01T00:00:00Z",
)


def _mock_authenticated_user() -> MagicMock:
    fake_user = MagicMock(id="user-1", email="test@example.com")
    return MagicMock(user=fake_user)


def test_check_declared_content_length_allows_missing_header() -> None:
    _check_declared_content_length(None)


def test_check_declared_content_length_allows_within_limit() -> None:
    _check_declared_content_length(str(settings.MAX_UPLOAD_FILE_SIZE_BYTES - 1))


def test_check_declared_content_length_ignores_malformed_header() -> None:
    _check_declared_content_length("not-a-number")


def test_check_declared_content_length_rejects_oversized() -> None:
    with pytest.raises(ValidationAppError) as exc_info:
        _check_declared_content_length(str(settings.MAX_UPLOAD_FILE_SIZE_BYTES + 1))
    assert exc_info.value.code == "FILE_TOO_LARGE"


def test_list_files_requires_authentication(client):
    response = client.get("/api/v1/files")
    assert response.status_code == 401


def test_list_files_returns_company_scoped_files(client):
    fake_auth_response = _mock_authenticated_user()

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
    fake_auth_response = _mock_authenticated_user()

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
    fake_auth_response = _mock_authenticated_user()
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


def test_upload_file_requires_authentication(client):
    response = client.post(
        "/api/v1/files", files={"upload": ("invoice.pdf", b"fake pdf", "application/pdf")}
    )
    assert response.status_code == 401


def test_upload_file_returns_created_metadata(client):
    fake_auth_response = _mock_authenticated_user()

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.files.file_service.register_file", return_value=FAKE_FILE
        ) as mock_register,
        patch("app.api.v1.files.audit_service.record_event") as mock_audit,
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.post(
            "/api/v1/files",
            files={"upload": ("invoice.pdf", b"fake pdf", "application/pdf")},
            headers={"Authorization": "Bearer good-token"},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == "file-1"

    mock_register.assert_called_once_with(
        company_id="company-1",
        uploaded_by="user-1",
        original_filename="invoice.pdf",
        content_type="application/pdf",
        content=b"fake pdf",
    )
    mock_audit.assert_called_once_with(
        company_id="company-1",
        user_id="user-1",
        action="file.uploaded",
        entity_type="file",
        entity_id="file-1",
    )
