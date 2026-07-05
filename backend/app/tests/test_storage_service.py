from unittest.mock import MagicMock, patch

from app.services import storage_service


def test_upload_object_calls_storage_api() -> None:
    mock_client = MagicMock()

    with patch("app.services.storage_service.get_supabase_admin", return_value=mock_client):
        storage_service.upload_object(
            path="company-1/file-1.pdf", content=b"hi", content_type="application/pdf"
        )

    mock_client.storage.from_.assert_called_once_with(storage_service.BUCKET_NAME)
    mock_client.storage.from_.return_value.upload.assert_called_once_with(
        "company-1/file-1.pdf", b"hi", {"content-type": "application/pdf"}
    )


def test_create_signed_url_returns_url() -> None:
    mock_client = MagicMock()
    mock_client.storage.from_.return_value.create_signed_url.return_value = {
        "signedURL": "https://example.supabase.co/signed/company-1/file-1.pdf"
    }

    with patch("app.services.storage_service.get_supabase_admin", return_value=mock_client):
        url = storage_service.create_signed_url(path="company-1/file-1.pdf", expires_in=300)

    assert url == "https://example.supabase.co/signed/company-1/file-1.pdf"
    mock_client.storage.from_.return_value.create_signed_url.assert_called_once_with(
        "company-1/file-1.pdf", 300
    )


def test_delete_object_calls_remove() -> None:
    mock_client = MagicMock()

    with patch("app.services.storage_service.get_supabase_admin", return_value=mock_client):
        storage_service.delete_object(path="company-1/file-1.pdf")

    mock_client.storage.from_.return_value.remove.assert_called_once_with(["company-1/file-1.pdf"])
