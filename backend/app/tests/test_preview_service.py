from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from app.core.exceptions import NotFoundError, ValidationAppError
from app.schemas.template import (
    TemplateArtifact,
    TemplateManifest,
    TemplateManifestAsset,
    TemplateManifestField,
    TemplateManifestMetadata,
    TemplateManifestPage,
)
from app.schemas.template_metadata import TemplateMetadata
from app.services import preview_service

FAKE_TEMPLATE_METADATA = TemplateMetadata(
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
        html='<section class="page"><span data-field-id="f1" data-machine-key="invoice_number">INV-1001</span>'
        '<img data-asset-id="asset-1"></section>',
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


def test_get_latest_preview_returns_artifact_and_asset_urls() -> None:
    with (
        patch(
            "app.services.preview_service.template_engine_service.get_latest_template",
            return_value=FAKE_TEMPLATE_METADATA,
        ),
        patch(
            "app.services.preview_service.storage_service.download_object",
            return_value=_artifact_bytes(),
        ),
        patch(
            "app.services.preview_service.storage_service.create_signed_url",
            return_value="https://signed.example/asset-1.png",
        ) as mock_sign,
    ):
        result = preview_service.get_latest_preview(company_id="company-1", file_id="file-1")

    assert result.artifact.manifest.fields[0].field_id == "f1"
    assert result.asset_urls == {"asset-1": "https://signed.example/asset-1.png"}
    mock_sign.assert_called_once_with(
        path="company-1/file-1/parsed/assets/asset-1.png", expires_in=300
    )


def test_get_preview_by_version_delegates_to_specific_version() -> None:
    with (
        patch(
            "app.services.preview_service.template_engine_service.get_template_by_version",
            return_value=FAKE_TEMPLATE_METADATA,
        ) as mock_get_version,
        patch(
            "app.services.preview_service.storage_service.download_object",
            return_value=_artifact_bytes(),
        ),
        patch(
            "app.services.preview_service.storage_service.create_signed_url",
            return_value="https://signed.example/asset-1.png",
        ),
    ):
        result = preview_service.get_preview_by_version(
            company_id="company-1", file_id="file-1", version=1
        )

    mock_get_version.assert_called_once_with(company_id="company-1", file_id="file-1", version=1)
    assert result.artifact.version == 1


def test_get_latest_preview_raises_when_template_not_ready() -> None:
    not_ready = FAKE_TEMPLATE_METADATA.model_copy(
        update={"status": "processing", "storage_path": None}
    )

    with (
        patch(
            "app.services.preview_service.template_engine_service.get_latest_template",
            return_value=not_ready,
        ),
        pytest.raises(ValidationAppError),
    ):
        preview_service.get_latest_preview(company_id="company-1", file_id="file-1")


def test_refresh_asset_url_returns_fresh_url_for_latest_template() -> None:
    with (
        patch(
            "app.services.preview_service.template_engine_service.get_latest_template",
            return_value=FAKE_TEMPLATE_METADATA,
        ) as mock_get_latest,
        patch(
            "app.services.preview_service.storage_service.download_object",
            return_value=_artifact_bytes(),
        ),
        patch(
            "app.services.preview_service.storage_service.create_signed_url",
            return_value="https://signed.example/refreshed.png",
        ),
    ):
        result = preview_service.refresh_asset_url(
            company_id="company-1", file_id="file-1", asset_id="asset-1"
        )

    mock_get_latest.assert_called_once()
    assert result.url == "https://signed.example/refreshed.png"
    assert result.expires_in == 300


def test_refresh_asset_url_uses_specific_version_when_given() -> None:
    with (
        patch(
            "app.services.preview_service.template_engine_service.get_template_by_version",
            return_value=FAKE_TEMPLATE_METADATA,
        ) as mock_get_version,
        patch(
            "app.services.preview_service.storage_service.download_object",
            return_value=_artifact_bytes(),
        ),
        patch(
            "app.services.preview_service.storage_service.create_signed_url",
            return_value="https://signed.example/refreshed.png",
        ),
    ):
        preview_service.refresh_asset_url(
            company_id="company-1", file_id="file-1", asset_id="asset-1", version=1
        )

    mock_get_version.assert_called_once_with(company_id="company-1", file_id="file-1", version=1)


def test_refresh_asset_url_raises_not_found_when_asset_missing_from_manifest() -> None:
    with (
        patch(
            "app.services.preview_service.template_engine_service.get_latest_template",
            return_value=FAKE_TEMPLATE_METADATA,
        ),
        patch(
            "app.services.preview_service.storage_service.download_object",
            return_value=_artifact_bytes(),
        ),
        pytest.raises(NotFoundError),
    ):
        preview_service.refresh_asset_url(
            company_id="company-1", file_id="file-1", asset_id="does-not-exist"
        )
