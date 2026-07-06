"""
Orchestrates template generation — Module 8.

Reads the latest completed `AIFieldExtractionResult` for a file (Module 7)
and the *exact* `UniversalDocumentModel` it was built from (Module 6,
fetched by id via `parser_service.get_parsed_document` — not "whatever is
latest now", since the file may have been re-parsed since that extraction
ran), runs it through Stage A (reading order), Stage B (field/table
indexing), Stage C (HTML marker emission), Stage D (CSS assembly), and
Stages E/F (manifest assembly + packaging), then persists one versioned
JSON artifact the same way Modules 6/7 persist their own output.

This is the only layer in Module 8 that touches Storage or the database —
every helper under app/services/template_engine/ is pure and knows nothing
about either. Never calls OpenAI, never re-parses, never fills a value
into a placeholder, never renders a preview or a PDF.

Every run is versioned: `templates` rows are append-only per
`file_id`/`version` and are never overwritten (backend/sql/010_templates.sql).
`generate_template` checks for an existing completed template with a
matching (source_ai_extraction_id, generator_version, schema_version)
before regenerating — pass `force=True` to always mint a new version.
"""

import time
from datetime import UTC, datetime
from typing import Any

from app.core.exceptions import NotFoundError, TemplateGenerationError, ValidationAppError
from app.core.logging import get_logger
from app.core.supabase import get_supabase_admin
from app.schemas.ai_extraction import AIFieldExtractionResult
from app.schemas.document_model import UniversalDocumentModel
from app.schemas.template import TemplateArtifact
from app.schemas.template_metadata import TemplateMetadata
from app.services import ai_extraction_service, file_service, parser_service, storage_service
from app.services.template_engine import field_index as field_index_module
from app.services.template_engine import section_naming
from app.services.template_engine.css import render_stylesheet
from app.services.template_engine.html_builder import UnitRenderResult, render_unit
from app.services.template_engine.manifest_builder import build_manifest
from app.services.template_engine.text_styles import collect_style_classes, median_font_size

logger = get_logger(__name__)

SCHEMA_VERSION = "1.0"
GENERATOR_VERSION = "1.0"

_ACCEPTABLE_EXTRACTION_STATUSES = {"completed", "completed_with_errors"}


def generate_template(*, company_id: str, file_id: str, force: bool = False) -> TemplateMetadata:
    extraction = ai_extraction_service.get_latest_extraction(company_id=company_id, file_id=file_id)
    if extraction.status not in _ACCEPTABLE_EXTRACTION_STATUSES or not extraction.storage_path:
        raise ValidationAppError(
            "This file has not been successfully extracted yet.", code="EXTRACTION_NOT_READY"
        )

    extraction_result = AIFieldExtractionResult.model_validate_json(
        storage_service.download_object(path=extraction.storage_path)
    )

    parsed = parser_service.get_parsed_document(
        company_id=company_id, parsed_document_id=extraction_result.source_parsed_document_id
    )
    if not parsed.storage_path:
        raise ValidationAppError(
            "The parsed document backing this extraction is missing its content.",
            code="PARSED_DOCUMENT_MISSING",
        )
    udm = UniversalDocumentModel.model_validate_json(
        storage_service.download_object(path=parsed.storage_path)
    )

    client = get_supabase_admin()

    if not force:
        cached = _find_cached_template(
            client,
            file_id=file_id,
            source_ai_extraction_id=extraction.id,
            generator_version=GENERATOR_VERSION,
        )
        if cached is not None:
            return cached

    version = _next_version(client, file_id=file_id)

    insert_response = (
        client.table("templates")
        .insert(
            {
                "company_id": company_id,
                "file_id": file_id,
                "source_ai_extraction_id": extraction.id,
                "source_parsed_document_id": parsed.id,
                "version": version,
                "schema_version": SCHEMA_VERSION,
                "generator_version": GENERATOR_VERSION,
                "status": "processing",
            }
        )
        .execute()
    )
    template_id: str = insert_response.data[0]["id"]

    start = time.perf_counter()
    try:
        artifact = _build_artifact(
            udm=udm,
            extraction_result=extraction_result,
            version=version,
            source_ai_extraction_id=extraction.id,
            source_parsed_document_id=parsed.id,
        )
    except (
        Exception
    ) as exc:  # noqa: BLE001 - malformed upstream data or an internal bug must not crash the request
        duration_ms = (time.perf_counter() - start) * 1000
        logger.error(
            "Template generation failed",
            extra={"file_id": file_id, "version": version, "error": str(exc)},
        )
        return _finalize(
            client,
            template_id,
            {"status": "failed", "error_message": str(exc), "duration_ms": duration_ms},
        )
    duration_ms = (time.perf_counter() - start) * 1000
    artifact = artifact.model_copy(
        update={
            "manifest": artifact.manifest.model_copy(
                update={
                    "metadata": artifact.manifest.metadata.model_copy(
                        update={"duration_ms": duration_ms}
                    )
                }
            )
        }
    )

    storage_path = _build_storage_path(company_id=company_id, file_id=file_id, version=version)
    storage_service.upload_object(
        path=storage_path,
        content=artifact.model_dump_json().encode("utf-8"),
        content_type="application/json",
    )

    status = "completed_with_errors" if artifact.manifest.metadata.warnings else "completed"

    return _finalize(
        client,
        template_id,
        {
            "status": status,
            "storage_path": storage_path,
            "field_count": artifact.manifest.metadata.field_count,
            "section_count": artifact.manifest.metadata.section_count,
            "asset_count": artifact.manifest.metadata.asset_count,
            "page_count": len(artifact.manifest.pages),
            "duration_ms": duration_ms,
        },
    )


def get_latest_template(*, company_id: str, file_id: str) -> TemplateMetadata:
    file_service.get_file(company_id=company_id, file_id=file_id)
    client = get_supabase_admin()
    response = (
        client.table("templates")
        .select("*")
        .eq("file_id", file_id)
        .order("version", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    row: dict[str, Any] | None = response.data if response else None
    if not row:
        raise NotFoundError("This file has no generated template yet.")
    return TemplateMetadata(**row)


def get_template_by_version(*, company_id: str, file_id: str, version: int) -> TemplateMetadata:
    file_service.get_file(company_id=company_id, file_id=file_id)
    client = get_supabase_admin()
    response = (
        client.table("templates")
        .select("*")
        .eq("file_id", file_id)
        .eq("version", version)
        .maybe_single()
        .execute()
    )
    row: dict[str, Any] | None = response.data if response else None
    if not row:
        raise NotFoundError(f"Template version {version} was not found for this file.")
    return TemplateMetadata(**row)


def list_templates(*, company_id: str, file_id: str) -> list[TemplateMetadata]:
    file_service.get_file(company_id=company_id, file_id=file_id)
    client = get_supabase_admin()
    response = (
        client.table("templates")
        .select("*")
        .eq("file_id", file_id)
        .order("version", desc=True)
        .execute()
    )
    rows: list[dict[str, Any]] = response.data or []
    return [TemplateMetadata(**row) for row in rows]


def _build_artifact(
    *,
    udm: UniversalDocumentModel,
    extraction_result: AIFieldExtractionResult,
    version: int,
    source_ai_extraction_id: str,
    source_parsed_document_id: str,
) -> TemplateArtifact:
    index = field_index_module.build_field_index(extraction_result)
    section_keys = section_naming.assign_section_keys(udm, extraction_result.tables)
    style_classes = collect_style_classes(udm)
    doc_median_font_size = median_font_size(udm)

    unit_results: dict[int, UnitRenderResult] = {}
    html_parts: list[str] = []
    for unit in udm.units:
        if unit.status == "error":
            continue
        unit_result = render_unit(
            unit=unit,
            field_index=index,
            style_classes=style_classes,
            median_font_size=doc_median_font_size,
            section_keys=section_keys,
        )
        unit_results[unit.index] = unit_result
        html_parts.append(unit_result.html)

    if not unit_results and udm.units:
        raise TemplateGenerationError(
            "No unit could be rendered — every unit failed during parsing."
        )

    manifest = build_manifest(
        udm=udm,
        extraction_result=extraction_result,
        field_index=index,
        unit_results=unit_results,
        section_keys=section_keys,
        duration_ms=0.0,
    )
    css = render_stylesheet(style_classes, manifest.pages)

    return TemplateArtifact(
        schema_version=SCHEMA_VERSION,
        generator_version=GENERATOR_VERSION,
        source_ai_extraction_id=source_ai_extraction_id,
        source_parsed_document_id=source_parsed_document_id,
        version=version,
        generated_at=datetime.now(UTC),
        html="\n".join(html_parts),
        css=css,
        manifest=manifest,
    )


def _find_cached_template(
    client: Any, *, file_id: str, source_ai_extraction_id: str, generator_version: str
) -> TemplateMetadata | None:
    response = (
        client.table("templates")
        .select("*")
        .eq("file_id", file_id)
        .eq("source_ai_extraction_id", source_ai_extraction_id)
        .eq("generator_version", generator_version)
        .eq("schema_version", SCHEMA_VERSION)
        .eq("status", "completed")
        .order("version", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    row: dict[str, Any] | None = response.data if response else None
    if not row:
        return None
    return TemplateMetadata(**row)


def _next_version(client: Any, *, file_id: str) -> int:
    response = (
        client.table("templates")
        .select("version")
        .eq("file_id", file_id)
        .order("version", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    row: dict[str, Any] | None = response.data if response else None
    if not row:
        return 1
    return int(row["version"]) + 1


def _build_storage_path(*, company_id: str, file_id: str, version: int) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    return f"{company_id}/{file_id}/templates/{SCHEMA_VERSION}/{GENERATOR_VERSION}-v{version}-{timestamp}.json"


def _finalize(client: Any, template_id: str, fields: dict[str, Any]) -> TemplateMetadata:
    response = client.table("templates").update(fields).eq("id", template_id).execute()
    row: dict[str, Any] = response.data[0]
    return TemplateMetadata(**row)
