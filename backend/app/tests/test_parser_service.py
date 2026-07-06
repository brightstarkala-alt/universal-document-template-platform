import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import ForbiddenError, NotFoundError
from app.schemas.file import FileMetadata
from app.services import parser_service
from app.tests.parser_fixtures import make_png_bytes

FAKE_FILE = FileMetadata(
    id="file-1",
    company_id="company-1",
    storage_bucket="documents",
    storage_path="company-1/file-1.png",
    original_filename="photo.png",
    extension=".png",
    content_type="image/png",
    size_bytes=100,
    checksum_sha256="deadbeef",
    uploaded_by="user-1",
    uploaded_at="2026-01-01T00:00:00Z",
)


def _row(**overrides: Any) -> dict[str, Any]:
    base = {
        "id": "parsed-1",
        "company_id": "company-1",
        "file_id": "file-1",
        "schema_version": "1.0",
        "parser_name": "image_parser",
        "parser_version": "1.0.0",
        "status": "processing",
        "storage_path": None,
        "unit_count": None,
        "text_block_count": None,
        "image_count": None,
        "cell_grid_count": None,
        "cell_count": None,
        "character_count": None,
        "duration_ms": None,
        "error_message": None,
        "created_at": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return base


def _mock_client_for_insert() -> MagicMock:
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "parsed-1"}
    ]
    return mock_client


def test_parse_file_completes_successfully_for_image() -> None:
    mock_client = _mock_client_for_insert()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        _row(
            status="completed", storage_path="x.json", unit_count=1, image_count=1, duration_ms=1.2
        )
    ]

    with (
        patch("app.services.parser_service.file_service.get_file", return_value=FAKE_FILE),
        patch("app.services.parser_service.get_supabase_admin", return_value=mock_client),
        patch(
            "app.services.parser_service.storage_service.download_object",
            return_value=make_png_bytes(),
        ),
        patch("app.services.parser_service.storage_service.upload_object") as mock_upload,
    ):
        result = parser_service.parse_file(company_id="company-1", file_id="file-1")

    assert result.status == "completed"
    assert result.id == "parsed-1"
    mock_upload.assert_called_once()
    uploaded_path = mock_upload.call_args.kwargs["path"]
    assert uploaded_path.startswith("company-1/file-1/parsed/1.0/")
    assert uploaded_path.endswith(".json")


def test_parse_file_backfills_source_file_asset_path() -> None:
    mock_client = _mock_client_for_insert()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        _row(status="completed", storage_path="x.json")
    ]

    uploaded_json: dict[str, bytes] = {}

    def _capture_upload(*, path: str, content: bytes, content_type: str) -> None:
        if path.endswith(".json"):
            uploaded_json["content"] = content

    with (
        patch("app.services.parser_service.file_service.get_file", return_value=FAKE_FILE),
        patch("app.services.parser_service.get_supabase_admin", return_value=mock_client),
        patch(
            "app.services.parser_service.storage_service.download_object",
            return_value=make_png_bytes(),
        ),
        patch(
            "app.services.parser_service.storage_service.upload_object",
            side_effect=_capture_upload,
        ),
    ):
        parser_service.parse_file(company_id="company-1", file_id="file-1")

    udm = json.loads(uploaded_json["content"])
    image_block = udm["units"][0]["blocks"][0]
    assert image_block["asset_type"] == "source_file"
    assert image_block["asset_path"] == FAKE_FILE.storage_path


def test_parse_file_marks_failed_when_adapter_raises() -> None:
    mock_client = _mock_client_for_insert()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        _row(status="failed", error_message="cannot identify image file")
    ]

    with (
        patch("app.services.parser_service.file_service.get_file", return_value=FAKE_FILE),
        patch("app.services.parser_service.get_supabase_admin", return_value=mock_client),
        patch(
            "app.services.parser_service.storage_service.download_object",
            return_value=b"not an image",
        ),
    ):
        result = parser_service.parse_file(company_id="company-1", file_id="file-1")

    assert result.status == "failed"
    assert result.error_message is not None


def test_get_latest_parsed_document_returns_metadata() -> None:
    mock_client = MagicMock()
    query = mock_client.table.return_value.select.return_value.eq.return_value.order.return_value
    query.limit.return_value.maybe_single.return_value.execute.return_value.data = _row(
        status="completed"
    )

    with (
        patch("app.services.parser_service.file_service.get_file", return_value=FAKE_FILE),
        patch("app.services.parser_service.get_supabase_admin", return_value=mock_client),
    ):
        result = parser_service.get_latest_parsed_document(company_id="company-1", file_id="file-1")

    assert result.id == "parsed-1"


def test_get_latest_parsed_document_raises_not_found_when_never_parsed() -> None:
    mock_client = MagicMock()
    query = mock_client.table.return_value.select.return_value.eq.return_value.order.return_value
    query.limit.return_value.maybe_single.return_value.execute.return_value.data = None

    with (
        patch("app.services.parser_service.file_service.get_file", return_value=FAKE_FILE),
        patch("app.services.parser_service.get_supabase_admin", return_value=mock_client),
        pytest.raises(NotFoundError),
    ):
        parser_service.get_latest_parsed_document(company_id="company-1", file_id="file-1")


def test_get_parsed_document_returns_metadata_by_id() -> None:
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = _row(
        status="completed"
    )

    with patch("app.services.parser_service.get_supabase_admin", return_value=mock_client):
        result = parser_service.get_parsed_document(
            company_id="company-1", parsed_document_id="parsed-1"
        )

    assert result.id == "parsed-1"


def test_get_parsed_document_raises_not_found_when_missing() -> None:
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = (
        None
    )

    with (
        patch("app.services.parser_service.get_supabase_admin", return_value=mock_client),
        pytest.raises(NotFoundError),
    ):
        parser_service.get_parsed_document(company_id="company-1", parsed_document_id="missing")


def test_get_parsed_document_raises_forbidden_when_different_company() -> None:
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = _row(
        company_id="company-other"
    )

    with (
        patch("app.services.parser_service.get_supabase_admin", return_value=mock_client),
        pytest.raises(ForbiddenError),
    ):
        parser_service.get_parsed_document(company_id="company-1", parsed_document_id="parsed-1")
