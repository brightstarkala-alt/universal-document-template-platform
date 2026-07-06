from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import OpenAIUnavailableError, ValidationAppError
from app.schemas.ai_extraction_metadata import AIExtractionMetadata
from app.schemas.document_model import (
    BoundingBox,
    Dimensions,
    ParserInfo,
    ParserStats,
    TextBlock,
    TextRun,
    Unit,
    UniversalDocumentModel,
)
from app.schemas.parsed_document import ParsedDocumentMetadata
from app.services import ai_extraction_service
from app.services.ai_extraction.openai_client import BatchExtractionResult
from app.services.ai_extraction.prompts import LLMBatchResponse

FAKE_PARSED_DOCUMENT = ParsedDocumentMetadata(
    id="parsed-1",
    company_id="company-1",
    file_id="file-1",
    schema_version="1.0",
    parser_name="pdf_parser",
    parser_version="1.0.0",
    status="completed",
    storage_path="company-1/file-1/parsed/1.0/1.0.0-x.json",
    unit_count=1,
    text_block_count=1,
    image_count=0,
    cell_grid_count=0,
    cell_count=0,
    character_count=24,
    duration_ms=5.0,
    error_message=None,
    created_at="2026-01-01T00:00:00Z",
)


def _udm() -> UniversalDocumentModel:
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        status="ok",
        confidence=1.0,
        blocks=[
            TextBlock(
                bounding_box=BoundingBox(x=0, y=0, width=100, height=10),
                runs=[TextRun(text="Invoice Number: INV-1001")],
            )
        ],
    )
    return UniversalDocumentModel(
        schema_version="1.0",
        source_file_id="file-1",
        source_checksum_sha256="checksum-abc",
        source_format="pdf",
        parser=ParserInfo(name="pdf_parser", version="1.0.0"),
        extracted_at=datetime.now(UTC),
        stats=ParserStats(
            unit_count=1,
            text_block_count=1,
            image_count=0,
            cell_grid_count=0,
            cell_count=0,
            character_count=24,
            duration_ms=5.0,
        ),
        units=[unit],
    )


def _valid_batch_result() -> BatchExtractionResult:
    response = LLMBatchResponse.model_validate(
        {
            "fields": [
                {
                    "unit_index": 0,
                    "block_index": 0,
                    "run_index": 0,
                    "display_label": "Invoice Number",
                    "machine_key": "invoice_number",
                    "type": "identifier",
                    "sample_value": "INV-1001",
                    "confidence": 0.9,
                    "accepted": True,
                }
            ],
            "tables": [],
        }
    )
    return BatchExtractionResult(response, prompt_tokens=50, completion_tokens=20)


def _extraction_row(**overrides: Any) -> dict[str, Any]:
    base = {
        "id": "extraction-1",
        "company_id": "company-1",
        "file_id": "file-1",
        "parsed_document_id": "parsed-1",
        "version": 1,
        "schema_version": "1.0",
        "source_checksum_sha256": "checksum-abc",
        "model": "gpt-4o-mini",
        "prompt_version": "2026-07-06.1",
        "status": "processing",
        "storage_path": None,
        "field_count": None,
        "table_count": None,
        "low_confidence_count": None,
        "prompt_tokens": None,
        "completion_tokens": None,
        "duration_ms": None,
        "error_message": None,
        "created_at": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return base


def _mock_client_for_insert() -> MagicMock:
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "extraction-1"}
    ]
    return mock_client


def test_extract_fields_completes_successfully() -> None:
    mock_client = _mock_client_for_insert()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        _extraction_row(status="completed", storage_path="x.json", field_count=1, table_count=0)
    ]

    with (
        patch(
            "app.services.ai_extraction_service.parser_service.get_latest_parsed_document",
            return_value=FAKE_PARSED_DOCUMENT,
        ),
        patch(
            "app.services.ai_extraction_service.storage_service.download_object",
            return_value=_udm().model_dump_json().encode("utf-8"),
        ),
        patch("app.services.ai_extraction_service.storage_service.upload_object") as mock_upload,
        patch("app.services.ai_extraction_service.get_supabase_admin", return_value=mock_client),
        patch("app.services.ai_extraction_service._find_cached_extraction", return_value=None),
        patch("app.services.ai_extraction_service._next_version", return_value=1),
        patch("app.services.ai_extraction_service.get_openai_client"),
        patch(
            "app.services.ai_extraction_service.extract_batch",
            return_value=_valid_batch_result(),
        ),
    ):
        result = ai_extraction_service.extract_fields(company_id="company-1", file_id="file-1")

    assert result.status == "completed"
    mock_upload.assert_called_once()
    uploaded_path = mock_upload.call_args.kwargs["path"]
    assert uploaded_path.startswith("company-1/file-1/extracted/1.0/")

    update_fields = mock_client.table.return_value.update.call_args.args[0]
    assert update_fields["status"] == "completed"
    assert update_fields["field_count"] == 1

    uploaded_json = mock_upload.call_args.kwargs["content"].decode("utf-8")
    assert '"machine_key":"invoice_number"' in uploaded_json.replace(" ", "").replace("\n", "")
    assert '"display_label":"InvoiceNumber"' in uploaded_json.replace(" ", "").replace("\n", "")


def test_extract_fields_returns_cached_result_without_calling_openai() -> None:
    cached = AIExtractionMetadata(**_extraction_row(status="completed", storage_path="cached.json"))

    with (
        patch(
            "app.services.ai_extraction_service.parser_service.get_latest_parsed_document",
            return_value=FAKE_PARSED_DOCUMENT,
        ),
        patch(
            "app.services.ai_extraction_service.storage_service.download_object",
            return_value=_udm().model_dump_json().encode("utf-8"),
        ),
        patch("app.services.ai_extraction_service.storage_service.upload_object") as mock_upload,
        patch("app.services.ai_extraction_service.get_supabase_admin") as mock_get_admin,
        patch("app.services.ai_extraction_service._find_cached_extraction", return_value=cached),
        patch("app.services.ai_extraction_service.extract_batch") as mock_extract_batch,
    ):
        result = ai_extraction_service.extract_fields(company_id="company-1", file_id="file-1")

    assert result.storage_path == "cached.json"
    mock_extract_batch.assert_not_called()
    mock_upload.assert_not_called()
    mock_get_admin.return_value.table.return_value.insert.assert_not_called()


def test_extract_fields_force_skips_cache_lookup() -> None:
    mock_client = _mock_client_for_insert()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        _extraction_row(status="completed", storage_path="x.json", field_count=1)
    ]

    with (
        patch(
            "app.services.ai_extraction_service.parser_service.get_latest_parsed_document",
            return_value=FAKE_PARSED_DOCUMENT,
        ),
        patch(
            "app.services.ai_extraction_service.storage_service.download_object",
            return_value=_udm().model_dump_json().encode("utf-8"),
        ),
        patch("app.services.ai_extraction_service.storage_service.upload_object"),
        patch("app.services.ai_extraction_service.get_supabase_admin", return_value=mock_client),
        patch("app.services.ai_extraction_service._find_cached_extraction") as mock_find_cached,
        patch("app.services.ai_extraction_service._next_version", return_value=1),
        patch("app.services.ai_extraction_service.get_openai_client"),
        patch(
            "app.services.ai_extraction_service.extract_batch",
            return_value=_valid_batch_result(),
        ),
    ):
        ai_extraction_service.extract_fields(company_id="company-1", file_id="file-1", force=True)

    mock_find_cached.assert_not_called()


def test_extract_fields_raises_when_parse_not_ready() -> None:
    not_ready = FAKE_PARSED_DOCUMENT.model_copy(
        update={"status": "processing", "storage_path": None}
    )

    with (
        patch(
            "app.services.ai_extraction_service.parser_service.get_latest_parsed_document",
            return_value=not_ready,
        ),
        pytest.raises(ValidationAppError),
    ):
        ai_extraction_service.extract_fields(company_id="company-1", file_id="file-1")


def test_extract_fields_marks_completed_with_errors_when_batch_fails() -> None:
    mock_client = _mock_client_for_insert()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        _extraction_row(status="completed_with_errors", field_count=0)
    ]

    with (
        patch(
            "app.services.ai_extraction_service.parser_service.get_latest_parsed_document",
            return_value=FAKE_PARSED_DOCUMENT,
        ),
        patch(
            "app.services.ai_extraction_service.storage_service.download_object",
            return_value=_udm().model_dump_json().encode("utf-8"),
        ),
        patch("app.services.ai_extraction_service.storage_service.upload_object"),
        patch("app.services.ai_extraction_service.get_supabase_admin", return_value=mock_client),
        patch("app.services.ai_extraction_service._find_cached_extraction", return_value=None),
        patch("app.services.ai_extraction_service._next_version", return_value=1),
        patch("app.services.ai_extraction_service.get_openai_client"),
        patch(
            "app.services.ai_extraction_service.extract_batch",
            side_effect=OpenAIUnavailableError("OpenAI is down"),
        ),
    ):
        result = ai_extraction_service.extract_fields(company_id="company-1", file_id="file-1")

    assert result.status == "completed_with_errors"
    update_fields = mock_client.table.return_value.update.call_args.args[0]
    assert update_fields["field_count"] == 0
    assert update_fields["status"] == "completed_with_errors"


def test_extract_fields_marks_failed_on_unexpected_error() -> None:
    mock_client = _mock_client_for_insert()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        _extraction_row(status="failed", error_message="boom")
    ]

    with (
        patch(
            "app.services.ai_extraction_service.parser_service.get_latest_parsed_document",
            return_value=FAKE_PARSED_DOCUMENT,
        ),
        patch(
            "app.services.ai_extraction_service.storage_service.download_object",
            return_value=_udm().model_dump_json().encode("utf-8"),
        ),
        patch("app.services.ai_extraction_service.get_supabase_admin", return_value=mock_client),
        patch("app.services.ai_extraction_service._find_cached_extraction", return_value=None),
        patch("app.services.ai_extraction_service._next_version", return_value=1),
        patch(
            "app.services.ai_extraction_service._run_extraction",
            side_effect=RuntimeError("boom"),
        ),
    ):
        result = ai_extraction_service.extract_fields(company_id="company-1", file_id="file-1")

    assert result.status == "failed"
    update_fields = mock_client.table.return_value.update.call_args.args[0]
    assert update_fields["status"] == "failed"
    assert update_fields["error_message"] == "boom"


def test_get_latest_extraction_returns_metadata() -> None:
    mock_client = MagicMock()
    query = mock_client.table.return_value.select.return_value.eq.return_value.order.return_value
    query.limit.return_value.maybe_single.return_value.execute.return_value.data = _extraction_row(
        status="completed"
    )

    with (
        patch(
            "app.services.ai_extraction_service.file_service.get_file",
            return_value=MagicMock(),
        ),
        patch("app.services.ai_extraction_service.get_supabase_admin", return_value=mock_client),
    ):
        result = ai_extraction_service.get_latest_extraction(
            company_id="company-1", file_id="file-1"
        )

    assert result.id == "extraction-1"


def test_get_latest_extraction_raises_not_found_when_never_extracted() -> None:
    from app.core.exceptions import NotFoundError

    mock_client = MagicMock()
    query = mock_client.table.return_value.select.return_value.eq.return_value.order.return_value
    query.limit.return_value.maybe_single.return_value.execute.return_value.data = None

    with (
        patch(
            "app.services.ai_extraction_service.file_service.get_file",
            return_value=MagicMock(),
        ),
        patch("app.services.ai_extraction_service.get_supabase_admin", return_value=mock_client),
        pytest.raises(NotFoundError),
    ):
        ai_extraction_service.get_latest_extraction(company_id="company-1", file_id="file-1")


def test_list_extractions_returns_all_versions_desc() -> None:
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
        _extraction_row(version=2, id="extraction-2"),
        _extraction_row(version=1, id="extraction-1"),
    ]

    with (
        patch(
            "app.services.ai_extraction_service.file_service.get_file",
            return_value=MagicMock(),
        ),
        patch("app.services.ai_extraction_service.get_supabase_admin", return_value=mock_client),
    ):
        results = ai_extraction_service.list_extractions(company_id="company-1", file_id="file-1")

    assert [r.version for r in results] == [2, 1]
