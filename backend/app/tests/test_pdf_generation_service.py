from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError, PDFGenerationError, ValidationAppError
from app.schemas.pdf_metadata import PDFMetadata
from app.schemas.template import (
    TemplateArtifact,
    TemplateManifest,
    TemplateManifestAsset,
    TemplateManifestField,
    TemplateManifestMetadata,
    TemplateManifestPage,
)
from app.schemas.template_metadata import TemplateMetadata
from app.services import document_renderer, pdf_generation_service

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
    field_count=1,
    section_count=0,
    asset_count=1,
    page_count=1,
    duration_ms=10.0,
    error_message=None,
    created_at="2026-01-01T00:00:00Z",
)


def _artifact() -> TemplateArtifact:
    return TemplateArtifact(
        schema_version="1.0",
        generator_version="1.0",
        source_ai_extraction_id="extraction-1",
        source_parsed_document_id="parsed-1",
        version=1,
        generated_at=datetime.now(UTC),
        html=(
            '<section class="page" data-unit-index="0">'
            '<span data-field-id="f1" data-machine-key="invoice_number">INV-1001</span>'
            '<img data-asset-id="asset-1" alt="" width="50" height="30">'
            "</section>"
        ),
        css="body { margin: 0; }",
        manifest=TemplateManifest(
            pages=[
                TemplateManifestPage(
                    unit_index=0, unit_type="page", unit_system="pt", width=612, height=792
                )
            ],
            fields=[
                TemplateManifestField(
                    field_id="f1",
                    machine_key="invoice_number",
                    display_label="Invoice Number",
                    type="identifier",
                    sample_value="INV-1001",
                    confidence=0.9,
                    confidence_tier="high",
                    unit_index=0,
                )
            ],
            repeating_sections=[],
            assets=[
                TemplateManifestAsset(
                    asset_id="asset-1",
                    original_path="company-1/file-1/parsed/assets/asset-1.png",
                    mime_type="image/png",
                    width=50,
                    height=30,
                    role="content_image",
                )
            ],
            metadata=TemplateManifestMetadata(
                source_format="pdf",
                page_count=1,
                sheet_count=0,
                field_count=1,
                section_count=0,
                asset_count=1,
                unmapped_field_count=0,
                unmapped_section_count=0,
                duration_ms=10.0,
            ),
        ),
    )


def _artifact_bytes() -> bytes:
    return _artifact().model_dump_json().encode("utf-8")


def _pdf_row(**overrides: Any) -> dict[str, Any]:
    base = {
        "id": "pdf-1",
        "company_id": "company-1",
        "file_id": "file-1",
        "source_template_id": "template-1",
        "version": 1,
        "schema_version": "1.0",
        "generator_version": "1.0",
        "status": "processing",
        "storage_path": None,
        "page_count": None,
        "size_bytes": None,
        "duration_ms": None,
        "error_message": None,
        "created_at": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return base


def _mock_client_for_insert() -> MagicMock:
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "pdf-1"}
    ]
    return mock_client


def test_generate_pdf_completes_successfully() -> None:
    mock_client = _mock_client_for_insert()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        _pdf_row(status="completed", storage_path="x.pdf", page_count=1, size_bytes=9)
    ]

    with (
        patch(
            "app.services.pdf_generation_service.template_engine_service.get_latest_template",
            return_value=FAKE_TEMPLATE,
        ),
        patch(
            "app.services.pdf_generation_service.storage_service.download_object",
            return_value=_artifact_bytes(),
        ),
        patch("app.services.pdf_generation_service.storage_service.upload_object"),
        patch(
            "app.services.pdf_generation_service.asset_inliner.build_asset_map",
            return_value={"asset-1": "data:image/png;base64,QQ=="},
        ),
        patch(
            "app.services.pdf_generation_service.weasyprint_renderer.render_pdf",
            return_value=(b"%PDF-FAKE", 1),
        ),
        patch("app.services.pdf_generation_service.get_supabase_admin", return_value=mock_client),
        patch("app.services.pdf_generation_service._find_cached_pdf", return_value=None),
        patch("app.services.pdf_generation_service._next_version", return_value=1),
    ):
        result = pdf_generation_service.generate_pdf(company_id="company-1", file_id="file-1")

    assert result.status == "completed"
    assert result.storage_path == "x.pdf"


def test_generate_pdf_uploads_bytes_produced_by_weasyprint_to_the_correct_path() -> None:
    mock_client = _mock_client_for_insert()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        _pdf_row(status="completed", storage_path="x.pdf")
    ]

    with (
        patch(
            "app.services.pdf_generation_service.template_engine_service.get_latest_template",
            return_value=FAKE_TEMPLATE,
        ),
        patch(
            "app.services.pdf_generation_service.storage_service.download_object",
            return_value=_artifact_bytes(),
        ),
        patch("app.services.pdf_generation_service.storage_service.upload_object") as mock_upload,
        patch(
            "app.services.pdf_generation_service.asset_inliner.build_asset_map",
            return_value={"asset-1": "data:image/png;base64,QQ=="},
        ),
        patch(
            "app.services.pdf_generation_service.weasyprint_renderer.render_pdf",
            return_value=(b"%PDF-1.4-fake-bytes", 1),
        ),
        patch("app.services.pdf_generation_service.get_supabase_admin", return_value=mock_client),
        patch("app.services.pdf_generation_service._find_cached_pdf", return_value=None),
        patch("app.services.pdf_generation_service._next_version", return_value=1),
    ):
        pdf_generation_service.generate_pdf(company_id="company-1", file_id="file-1")

    mock_upload.assert_called_once()
    assert mock_upload.call_args.kwargs["path"].startswith("company-1/file-1/pdfs/1.0-v1-")
    assert mock_upload.call_args.kwargs["content"] == b"%PDF-1.4-fake-bytes"
    assert mock_upload.call_args.kwargs["content_type"] == "application/pdf"

    update_fields = mock_client.table.return_value.update.call_args.args[0]
    assert update_fields["size_bytes"] == len(b"%PDF-1.4-fake-bytes")
    assert update_fields["page_count"] == 1


def test_generate_pdf_renders_through_the_shared_document_renderer_exactly_once() -> None:
    """Regression guard: PDF generation must call the one shared renderer
    (never a second, independent rendering implementation), and the HTML
    actually handed to WeasyPrint must be that renderer's real output."""
    mock_client = _mock_client_for_insert()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        _pdf_row(status="completed", storage_path="x.pdf")
    ]

    with (
        patch(
            "app.services.pdf_generation_service.template_engine_service.get_latest_template",
            return_value=FAKE_TEMPLATE,
        ),
        patch(
            "app.services.pdf_generation_service.storage_service.download_object",
            return_value=_artifact_bytes(),
        ),
        patch("app.services.pdf_generation_service.storage_service.upload_object"),
        patch(
            "app.services.pdf_generation_service.asset_inliner.build_asset_map",
            return_value={"asset-1": "data:image/png;base64,QQ=="},
        ),
        patch(
            "app.services.pdf_generation_service.weasyprint_renderer.render_pdf",
            return_value=(b"%PDF-FAKE", 1),
        ) as mock_render_pdf,
        patch("app.services.pdf_generation_service.get_supabase_admin", return_value=mock_client),
        patch("app.services.pdf_generation_service._find_cached_pdf", return_value=None),
        patch("app.services.pdf_generation_service._next_version", return_value=1),
        patch(
            "app.services.pdf_generation_service.document_renderer.render_html",
            wraps=document_renderer.render_html,
        ) as mock_render_html,
    ):
        pdf_generation_service.generate_pdf(company_id="company-1", file_id="file-1")

    mock_render_html.assert_called_once()

    rendered_html = mock_render_pdf.call_args.kwargs["html"]
    assert 'data-field-id="f1"' in rendered_html
    assert "INV-1001" in rendered_html
    assert 'src="data:image/png;base64,QQ=="' in rendered_html


def test_generate_pdf_returns_cached_result_without_rebuilding() -> None:
    cached = PDFMetadata(**_pdf_row(status="completed", storage_path="cached.pdf"))

    with (
        patch(
            "app.services.pdf_generation_service.template_engine_service.get_latest_template",
            return_value=FAKE_TEMPLATE,
        ),
        patch("app.services.pdf_generation_service.storage_service.download_object") as mock_download,
        patch("app.services.pdf_generation_service.storage_service.upload_object") as mock_upload,
        patch("app.services.pdf_generation_service.get_supabase_admin") as mock_get_admin,
        patch("app.services.pdf_generation_service._find_cached_pdf", return_value=cached),
    ):
        result = pdf_generation_service.generate_pdf(company_id="company-1", file_id="file-1")

    assert result.storage_path == "cached.pdf"
    mock_download.assert_not_called()
    mock_upload.assert_not_called()
    mock_get_admin.return_value.table.return_value.insert.assert_not_called()


def test_generate_pdf_force_skips_cache_lookup() -> None:
    mock_client = _mock_client_for_insert()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        _pdf_row(status="completed", storage_path="x.pdf")
    ]

    with (
        patch(
            "app.services.pdf_generation_service.template_engine_service.get_latest_template",
            return_value=FAKE_TEMPLATE,
        ),
        patch(
            "app.services.pdf_generation_service.storage_service.download_object",
            return_value=_artifact_bytes(),
        ),
        patch("app.services.pdf_generation_service.storage_service.upload_object"),
        patch(
            "app.services.pdf_generation_service.asset_inliner.build_asset_map",
            return_value={"asset-1": "data:image/png;base64,QQ=="},
        ),
        patch(
            "app.services.pdf_generation_service.weasyprint_renderer.render_pdf",
            return_value=(b"%PDF-FAKE", 1),
        ),
        patch("app.services.pdf_generation_service.get_supabase_admin", return_value=mock_client),
        patch("app.services.pdf_generation_service._find_cached_pdf") as mock_find_cached,
        patch("app.services.pdf_generation_service._next_version", return_value=1),
    ):
        pdf_generation_service.generate_pdf(company_id="company-1", file_id="file-1", force=True)

    mock_find_cached.assert_not_called()


def test_generate_pdf_raises_when_template_not_ready() -> None:
    not_ready = FAKE_TEMPLATE.model_copy(update={"status": "processing", "storage_path": None})

    with (
        patch(
            "app.services.pdf_generation_service.template_engine_service.get_latest_template",
            return_value=not_ready,
        ),
        pytest.raises(ValidationAppError),
    ):
        pdf_generation_service.generate_pdf(company_id="company-1", file_id="file-1")


def test_generate_pdf_marks_completed_with_errors_when_asset_cannot_be_inlined() -> None:
    mock_client = _mock_client_for_insert()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        _pdf_row(status="completed_with_errors", storage_path="x.pdf")
    ]

    with (
        patch(
            "app.services.pdf_generation_service.template_engine_service.get_latest_template",
            return_value=FAKE_TEMPLATE,
        ),
        patch(
            "app.services.pdf_generation_service.storage_service.download_object",
            return_value=_artifact_bytes(),
        ),
        patch("app.services.pdf_generation_service.storage_service.upload_object"),
        patch(
            "app.services.pdf_generation_service.asset_inliner.build_asset_map",
            return_value={},  # asset-1 could not be inlined
        ),
        patch(
            "app.services.pdf_generation_service.weasyprint_renderer.render_pdf",
            return_value=(b"%PDF-FAKE", 1),
        ),
        patch("app.services.pdf_generation_service.get_supabase_admin", return_value=mock_client),
        patch("app.services.pdf_generation_service._find_cached_pdf", return_value=None),
        patch("app.services.pdf_generation_service._next_version", return_value=1),
    ):
        result = pdf_generation_service.generate_pdf(company_id="company-1", file_id="file-1")

    assert result.status == "completed_with_errors"


def test_generate_pdf_marks_failed_on_unexpected_error() -> None:
    mock_client = _mock_client_for_insert()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        _pdf_row(status="failed", error_message="boom")
    ]

    with (
        patch(
            "app.services.pdf_generation_service.template_engine_service.get_latest_template",
            return_value=FAKE_TEMPLATE,
        ),
        patch(
            "app.services.pdf_generation_service.storage_service.download_object",
            return_value=_artifact_bytes(),
        ),
        patch(
            "app.services.pdf_generation_service.asset_inliner.build_asset_map",
            return_value={"asset-1": "data:image/png;base64,QQ=="},
        ),
        patch(
            "app.services.pdf_generation_service.weasyprint_renderer.render_pdf",
            side_effect=RuntimeError("boom"),
        ),
        patch("app.services.pdf_generation_service.get_supabase_admin", return_value=mock_client),
        patch("app.services.pdf_generation_service._find_cached_pdf", return_value=None),
        patch("app.services.pdf_generation_service._next_version", return_value=1),
    ):
        result = pdf_generation_service.generate_pdf(company_id="company-1", file_id="file-1")

    assert result.status == "failed"
    update_fields = mock_client.table.return_value.update.call_args.args[0]
    assert update_fields["status"] == "failed"
    assert update_fields["error_message"] == "boom"


def test_render_pdf_raises_when_weasyprint_produces_zero_pages() -> None:
    """Unit test of `_render_pdf` in isolation — only the two collaborators
    it actually calls (`asset_inliner`, `weasyprint_renderer`) are mocked."""
    with (
        patch(
            "app.services.pdf_generation_service.asset_inliner.build_asset_map",
            return_value={"asset-1": "data:image/png;base64,QQ=="},
        ),
        patch(
            "app.services.pdf_generation_service.weasyprint_renderer.render_pdf",
            return_value=(b"%PDF-EMPTY", 0),
        ),
        pytest.raises(PDFGenerationError),
    ):
        pdf_generation_service._render_pdf(_artifact())


def test_generate_pdf_marks_failed_when_weasyprint_produces_zero_pages() -> None:
    """End-to-end: a zero-page WeasyPrint result must surface as a
    `status="failed"` row through the real `generate_pdf` flow, exactly
    like any other exception raised inside `_render_pdf`."""
    mock_client = _mock_client_for_insert()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        _pdf_row(status="failed", error_message="WeasyPrint produced a PDF with no pages.")
    ]

    with (
        patch(
            "app.services.pdf_generation_service.template_engine_service.get_latest_template",
            return_value=FAKE_TEMPLATE,
        ),
        patch(
            "app.services.pdf_generation_service.storage_service.download_object",
            return_value=_artifact_bytes(),
        ),
        patch(
            "app.services.pdf_generation_service.asset_inliner.build_asset_map",
            return_value={"asset-1": "data:image/png;base64,QQ=="},
        ),
        patch(
            "app.services.pdf_generation_service.weasyprint_renderer.render_pdf",
            return_value=(b"%PDF-EMPTY", 0),
        ),
        patch("app.services.pdf_generation_service.get_supabase_admin", return_value=mock_client),
        patch("app.services.pdf_generation_service._find_cached_pdf", return_value=None),
        patch("app.services.pdf_generation_service._next_version", return_value=1),
    ):
        result = pdf_generation_service.generate_pdf(company_id="company-1", file_id="file-1")

    assert result.status == "failed"
    assert result.error_message == "WeasyPrint produced a PDF with no pages."


def test_get_latest_pdf_returns_metadata() -> None:
    mock_client = MagicMock()
    query = mock_client.table.return_value.select.return_value.eq.return_value.order.return_value
    query.limit.return_value.maybe_single.return_value.execute.return_value.data = _pdf_row(
        status="completed"
    )

    with (
        patch("app.services.pdf_generation_service.file_service.get_file", return_value=MagicMock()),
        patch("app.services.pdf_generation_service.get_supabase_admin", return_value=mock_client),
    ):
        result = pdf_generation_service.get_latest_pdf(company_id="company-1", file_id="file-1")

    assert result.id == "pdf-1"


def test_get_latest_pdf_raises_not_found_when_never_generated() -> None:
    mock_client = MagicMock()
    query = mock_client.table.return_value.select.return_value.eq.return_value.order.return_value
    query.limit.return_value.maybe_single.return_value.execute.return_value.data = None

    with (
        patch("app.services.pdf_generation_service.file_service.get_file", return_value=MagicMock()),
        patch("app.services.pdf_generation_service.get_supabase_admin", return_value=mock_client),
        pytest.raises(NotFoundError),
    ):
        pdf_generation_service.get_latest_pdf(company_id="company-1", file_id="file-1")


def test_get_pdf_by_version_returns_metadata() -> None:
    mock_client = MagicMock()
    query = mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value
    query.maybe_single.return_value.execute.return_value.data = _pdf_row(version=2, id="pdf-2")

    with (
        patch("app.services.pdf_generation_service.file_service.get_file", return_value=MagicMock()),
        patch("app.services.pdf_generation_service.get_supabase_admin", return_value=mock_client),
    ):
        result = pdf_generation_service.get_pdf_by_version(
            company_id="company-1", file_id="file-1", version=2
        )

    assert result.id == "pdf-2"


def test_list_pdfs_returns_all_versions_desc() -> None:
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
        _pdf_row(version=2, id="pdf-2"),
        _pdf_row(version=1, id="pdf-1"),
    ]

    with (
        patch("app.services.pdf_generation_service.file_service.get_file", return_value=MagicMock()),
        patch("app.services.pdf_generation_service.get_supabase_admin", return_value=mock_client),
    ):
        results = pdf_generation_service.list_pdfs(company_id="company-1", file_id="file-1")

    assert [r.version for r in results] == [2, 1]


def test_get_download_url_returns_signed_url_for_latest() -> None:
    with (
        patch(
            "app.services.pdf_generation_service.get_latest_pdf",
            return_value=PDFMetadata(
                **_pdf_row(status="completed", storage_path="x.pdf")
            ),
        ),
        patch(
            "app.services.pdf_generation_service.storage_service.create_signed_url",
            return_value="https://signed.example/x.pdf",
        ) as mock_sign,
    ):
        result = pdf_generation_service.get_download_url(company_id="company-1", file_id="file-1")

    assert result.url == "https://signed.example/x.pdf"
    assert result.expires_in == 300
    mock_sign.assert_called_once_with(path="x.pdf", expires_in=300)


def test_get_download_url_uses_specific_version_when_given() -> None:
    with (
        patch(
            "app.services.pdf_generation_service.get_pdf_by_version",
            return_value=PDFMetadata(
                **_pdf_row(status="completed", storage_path="v2.pdf", version=2)
            ),
        ) as mock_get_version,
        patch(
            "app.services.pdf_generation_service.storage_service.create_signed_url",
            return_value="https://signed.example/v2.pdf",
        ),
    ):
        pdf_generation_service.get_download_url(
            company_id="company-1", file_id="file-1", version=2
        )

    mock_get_version.assert_called_once_with(company_id="company-1", file_id="file-1", version=2)


def test_get_download_url_raises_when_pdf_not_ready() -> None:
    with (
        patch(
            "app.services.pdf_generation_service.get_latest_pdf",
            return_value=PDFMetadata(
                **_pdf_row(status="processing", storage_path=None)
            ),
        ),
        pytest.raises(ValidationAppError),
    ):
        pdf_generation_service.get_download_url(company_id="company-1", file_id="file-1")
