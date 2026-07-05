from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import ForbiddenError, NotFoundError
from app.services import file_service


def test_build_storage_path_is_company_scoped_folder() -> None:
    path = file_service.build_storage_path(
        company_id="company-1", file_id="file-1", extension=".pdf"
    )
    assert path == "company-1/file-1.pdf"


def test_register_file_validates_uploads_and_inserts_metadata() -> None:
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [
        {
            "id": "file-1",
            "company_id": "company-1",
            "storage_bucket": "documents",
            "storage_path": "company-1/file-1.pdf",
            "original_filename": "invoice.pdf",
            "content_type": "application/pdf",
            "size_bytes": 2,
            "checksum_sha256": None,
            "uploaded_by": "user-1",
            "created_at": "2026-01-01T00:00:00Z",
        }
    ]

    with (
        patch("app.services.file_service.get_supabase_admin", return_value=mock_client),
        patch("app.services.file_service.storage_service.upload_object") as mock_upload,
        patch("app.services.file_service.uuid.uuid4", return_value="file-1"),
    ):
        result = file_service.register_file(
            company_id="company-1",
            uploaded_by="user-1",
            original_filename="invoice.pdf",
            content_type="application/pdf",
            content=b"hi",
        )

    mock_upload.assert_called_once_with(
        path="company-1/file-1.pdf", content=b"hi", content_type="application/pdf"
    )
    assert result.id == "file-1"
    assert result.storage_path == "company-1/file-1.pdf"


def test_get_file_returns_metadata_for_owning_company() -> None:
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "id": "file-1",
        "company_id": "company-1",
        "storage_bucket": "documents",
        "storage_path": "company-1/file-1.pdf",
        "original_filename": "invoice.pdf",
        "content_type": "application/pdf",
        "size_bytes": 2,
        "checksum_sha256": None,
        "uploaded_by": "user-1",
        "created_at": "2026-01-01T00:00:00Z",
    }

    with patch("app.services.file_service.get_supabase_admin", return_value=mock_client):
        result = file_service.get_file(company_id="company-1", file_id="file-1")

    assert result.id == "file-1"


def test_get_file_raises_not_found_when_missing() -> None:
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = (
        None
    )

    with (
        patch("app.services.file_service.get_supabase_admin", return_value=mock_client),
        pytest.raises(NotFoundError),
    ):
        file_service.get_file(company_id="company-1", file_id="missing")


def test_get_file_raises_forbidden_for_other_company() -> None:
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "id": "file-1",
        "company_id": "company-other",
        "storage_bucket": "documents",
        "storage_path": "company-other/file-1.pdf",
        "original_filename": "invoice.pdf",
        "content_type": "application/pdf",
        "size_bytes": 2,
        "checksum_sha256": None,
        "uploaded_by": "user-1",
        "created_at": "2026-01-01T00:00:00Z",
    }

    with (
        patch("app.services.file_service.get_supabase_admin", return_value=mock_client),
        pytest.raises(ForbiddenError),
    ):
        file_service.get_file(company_id="company-1", file_id="file-1")


def test_list_files_scopes_query_to_company() -> None:
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = (
        []
    )

    with patch("app.services.file_service.get_supabase_admin", return_value=mock_client):
        result = file_service.list_files(company_id="company-1")

    mock_client.table.return_value.select.return_value.eq.assert_called_once_with(
        "company_id", "company-1"
    )
    assert result == []


def test_get_download_url_uses_signed_url_from_storage_service() -> None:
    fake_file = MagicMock(storage_path="company-1/file-1.pdf")

    with (
        patch("app.services.file_service.get_file", return_value=fake_file),
        patch(
            "app.services.file_service.storage_service.create_signed_url",
            return_value="https://example.supabase.co/signed/company-1/file-1.pdf",
        ) as mock_signed_url,
    ):
        result = file_service.get_download_url(company_id="company-1", file_id="file-1")

    mock_signed_url.assert_called_once_with(
        path="company-1/file-1.pdf", expires_in=file_service.settings.SIGNED_URL_EXPIRES_IN_SECONDS
    )
    assert result.url == "https://example.supabase.co/signed/company-1/file-1.pdf"
    assert result.expires_in == file_service.settings.SIGNED_URL_EXPIRES_IN_SECONDS
