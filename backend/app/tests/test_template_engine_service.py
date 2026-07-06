from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError, ValidationAppError
from app.schemas.ai_extraction import AIFieldExtractionResult, ExtractedField, SourceLocation
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
from app.schemas.template_metadata import TemplateMetadata
from app.services import template_engine_service

FAKE_EXTRACTION = AIExtractionMetadata(
    id="extraction-1",
    company_id="company-1",
    file_id="file-1",
    parsed_document_id="parsed-1",
    version=1,
    schema_version="1.0",
    source_checksum_sha256="checksum-abc",
    model="gpt-4o-mini",
    prompt_version="v1",
    status="completed",
    storage_path="company-1/file-1/extracted/1.0/v1-x.json",
    field_count=1,
    table_count=0,
    low_confidence_count=0,
    prompt_tokens=10,
    completion_tokens=5,
    duration_ms=5.0,
    error_message=None,
    created_at="2026-01-01T00:00:00Z",
)

FAKE_PARSED_DOCUMENT = ParsedDocumentMetadata(
    id="parsed-1",
    company_id="company-1",
    file_id="file-1",
    schema_version="1.0",
    parser_name="pdf_parser",
    parser_version="1.0.0",
    status="completed",
    storage_path="company-1/file-1/parsed/1.0/x.json",
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


def _udm_bytes() -> bytes:
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=612, height=792),
        status="ok",
        confidence=1.0,
        blocks=[
            TextBlock(
                bounding_box=BoundingBox(x=0, y=0, width=100, height=10),
                runs=[TextRun(text="Invoice Number: INV-1001")],
            )
        ],
    )
    udm = UniversalDocumentModel(
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
    return udm.model_dump_json().encode("utf-8")


def _extraction_result_bytes() -> bytes:
    result = AIFieldExtractionResult(
        schema_version="1.0",
        source_parsed_document_id="parsed-1",
        source_checksum_sha256="checksum-abc",
        version=1,
        model="gpt-4o-mini",
        prompt_version="v1",
        extracted_at=datetime.now(UTC),
        fields=[
            ExtractedField(
                field_id="f1",
                machine_key="invoice_number",
                display_label="Invoice Number",
                type="identifier",
                sample_value="INV-1001",
                source=SourceLocation(unit_index=0, block_index=0, run_index=0),
                confidence=0.9,
                confidence_tier="high",
                detection_method="llm",
            )
        ],
        tables=[],
        stats={"field_count": 1, "table_count": 0, "low_confidence_count": 0, "duration_ms": 1.0},
    )
    return result.model_dump_json().encode("utf-8")


def _template_row(**overrides: Any) -> dict[str, Any]:
    base = {
        "id": "template-1",
        "company_id": "company-1",
        "file_id": "file-1",
        "source_ai_extraction_id": "extraction-1",
        "source_parsed_document_id": "parsed-1",
        "version": 1,
        "schema_version": "1.0",
        "generator_version": "1.0",
        "status": "processing",
        "storage_path": None,
        "field_count": None,
        "section_count": None,
        "asset_count": None,
        "page_count": None,
        "duration_ms": None,
        "error_message": None,
        "created_at": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return base


def _mock_client_for_insert() -> MagicMock:
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "template-1"}
    ]
    return mock_client


def test_generate_template_completes_successfully() -> None:
    mock_client = _mock_client_for_insert()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        _template_row(
            status="completed",
            storage_path="x.json",
            field_count=1,
            section_count=0,
            asset_count=0,
            page_count=1,
        )
    ]

    with (
        patch(
            "app.services.template_engine_service.ai_extraction_service.get_latest_extraction",
            return_value=FAKE_EXTRACTION,
        ),
        patch(
            "app.services.template_engine_service.parser_service.get_parsed_document",
            return_value=FAKE_PARSED_DOCUMENT,
        ),
        patch(
            "app.services.template_engine_service.storage_service.download_object",
            side_effect=[_extraction_result_bytes(), _udm_bytes()],
        ),
        patch("app.services.template_engine_service.storage_service.upload_object") as mock_upload,
        patch("app.services.template_engine_service.get_supabase_admin", return_value=mock_client),
        patch("app.services.template_engine_service._find_cached_template", return_value=None),
        patch("app.services.template_engine_service._next_version", return_value=1),
    ):
        result = template_engine_service.generate_template(company_id="company-1", file_id="file-1")

    assert result.status == "completed"
    mock_upload.assert_called_once()
    uploaded_path = mock_upload.call_args.kwargs["path"]
    assert uploaded_path.startswith("company-1/file-1/templates/1.0/")

    update_fields = mock_client.table.return_value.update.call_args.args[0]
    assert update_fields["status"] == "completed"
    assert update_fields["field_count"] == 1
    assert update_fields["page_count"] == 1

    uploaded_json = mock_upload.call_args.kwargs["content"].decode("utf-8")
    assert '"machine_key":"invoice_number"' in uploaded_json.replace(" ", "").replace("\n", "")
    assert "data-field-id" in uploaded_json


def test_generate_template_returns_cached_result_without_rebuilding() -> None:
    cached = TemplateMetadata(**_template_row(status="completed", storage_path="cached.json"))

    with (
        patch(
            "app.services.template_engine_service.ai_extraction_service.get_latest_extraction",
            return_value=FAKE_EXTRACTION,
        ),
        patch(
            "app.services.template_engine_service.parser_service.get_parsed_document",
            return_value=FAKE_PARSED_DOCUMENT,
        ),
        patch(
            "app.services.template_engine_service.storage_service.download_object",
            side_effect=[_extraction_result_bytes(), _udm_bytes()],
        ),
        patch("app.services.template_engine_service.storage_service.upload_object") as mock_upload,
        patch("app.services.template_engine_service.get_supabase_admin") as mock_get_admin,
        patch("app.services.template_engine_service._find_cached_template", return_value=cached),
    ):
        result = template_engine_service.generate_template(company_id="company-1", file_id="file-1")

    assert result.storage_path == "cached.json"
    mock_upload.assert_not_called()
    mock_get_admin.return_value.table.return_value.insert.assert_not_called()


def test_generate_template_force_skips_cache_lookup() -> None:
    mock_client = _mock_client_for_insert()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        _template_row(status="completed", storage_path="x.json", field_count=1)
    ]

    with (
        patch(
            "app.services.template_engine_service.ai_extraction_service.get_latest_extraction",
            return_value=FAKE_EXTRACTION,
        ),
        patch(
            "app.services.template_engine_service.parser_service.get_parsed_document",
            return_value=FAKE_PARSED_DOCUMENT,
        ),
        patch(
            "app.services.template_engine_service.storage_service.download_object",
            side_effect=[_extraction_result_bytes(), _udm_bytes()],
        ),
        patch("app.services.template_engine_service.storage_service.upload_object"),
        patch("app.services.template_engine_service.get_supabase_admin", return_value=mock_client),
        patch("app.services.template_engine_service._find_cached_template") as mock_find_cached,
        patch("app.services.template_engine_service._next_version", return_value=1),
    ):
        template_engine_service.generate_template(
            company_id="company-1", file_id="file-1", force=True
        )

    mock_find_cached.assert_not_called()


def test_generate_template_raises_when_extraction_not_ready() -> None:
    not_ready = FAKE_EXTRACTION.model_copy(update={"status": "processing", "storage_path": None})

    with (
        patch(
            "app.services.template_engine_service.ai_extraction_service.get_latest_extraction",
            return_value=not_ready,
        ),
        pytest.raises(ValidationAppError),
    ):
        template_engine_service.generate_template(company_id="company-1", file_id="file-1")


def test_generate_template_marks_failed_on_unexpected_error() -> None:
    mock_client = _mock_client_for_insert()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        _template_row(status="failed", error_message="boom")
    ]

    with (
        patch(
            "app.services.template_engine_service.ai_extraction_service.get_latest_extraction",
            return_value=FAKE_EXTRACTION,
        ),
        patch(
            "app.services.template_engine_service.parser_service.get_parsed_document",
            return_value=FAKE_PARSED_DOCUMENT,
        ),
        patch(
            "app.services.template_engine_service.storage_service.download_object",
            side_effect=[_extraction_result_bytes(), _udm_bytes()],
        ),
        patch("app.services.template_engine_service.get_supabase_admin", return_value=mock_client),
        patch("app.services.template_engine_service._find_cached_template", return_value=None),
        patch("app.services.template_engine_service._next_version", return_value=1),
        patch(
            "app.services.template_engine_service._build_artifact", side_effect=RuntimeError("boom")
        ),
    ):
        result = template_engine_service.generate_template(company_id="company-1", file_id="file-1")

    assert result.status == "failed"
    update_fields = mock_client.table.return_value.update.call_args.args[0]
    assert update_fields["status"] == "failed"
    assert update_fields["error_message"] == "boom"


def test_get_latest_template_returns_metadata() -> None:
    mock_client = MagicMock()
    query = mock_client.table.return_value.select.return_value.eq.return_value.order.return_value
    query.limit.return_value.maybe_single.return_value.execute.return_value.data = _template_row(
        status="completed"
    )

    with (
        patch(
            "app.services.template_engine_service.file_service.get_file", return_value=MagicMock()
        ),
        patch("app.services.template_engine_service.get_supabase_admin", return_value=mock_client),
    ):
        result = template_engine_service.get_latest_template(
            company_id="company-1", file_id="file-1"
        )

    assert result.id == "template-1"


def test_get_latest_template_raises_not_found_when_never_generated() -> None:
    mock_client = MagicMock()
    query = mock_client.table.return_value.select.return_value.eq.return_value.order.return_value
    query.limit.return_value.maybe_single.return_value.execute.return_value.data = None

    with (
        patch(
            "app.services.template_engine_service.file_service.get_file", return_value=MagicMock()
        ),
        patch("app.services.template_engine_service.get_supabase_admin", return_value=mock_client),
        pytest.raises(NotFoundError),
    ):
        template_engine_service.get_latest_template(company_id="company-1", file_id="file-1")


def test_get_template_by_version_returns_metadata() -> None:
    mock_client = MagicMock()
    query = mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value
    query.maybe_single.return_value.execute.return_value.data = _template_row(
        version=2, id="template-2"
    )

    with (
        patch(
            "app.services.template_engine_service.file_service.get_file", return_value=MagicMock()
        ),
        patch("app.services.template_engine_service.get_supabase_admin", return_value=mock_client),
    ):
        result = template_engine_service.get_template_by_version(
            company_id="company-1", file_id="file-1", version=2
        )

    assert result.id == "template-2"


def test_list_templates_returns_all_versions_desc() -> None:
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
        _template_row(version=2, id="template-2"),
        _template_row(version=1, id="template-1"),
    ]

    with (
        patch(
            "app.services.template_engine_service.file_service.get_file", return_value=MagicMock()
        ),
        patch("app.services.template_engine_service.get_supabase_admin", return_value=mock_client),
    ):
        results = template_engine_service.list_templates(company_id="company-1", file_id="file-1")

    assert [r.version for r in results] == [2, 1]
