"""
Orchestrates PDF generation — Module 10.

Consumes the latest completed `TemplateArtifact` (Module 8) exactly as
Preview (Module 9) does — via `template_engine_service` — and renders it
through the exact same shared `document_renderer.render_html` Preview
uses. There is exactly one HTML-rendering implementation in this
codebase; this module adds no rendering or marker-substitution logic of
its own. Its only added responsibilities are:

  * inlining assets as base64 data URIs (`pdf_generation.asset_inliner`),
    since WeasyPrint has no browser-side JS to resolve a signed URL
    against, and a signed URL could expire mid-render;
  * synthesizing a print-only pagination stylesheet
    (`pdf_generation.print_css`), kept entirely separate from — never
    merged into — the artifact's own `css`;
  * invoking WeasyPrint (`pdf_generation.weasyprint_renderer`, the only
    place that imports it).

Every run is versioned exactly like `templates`/`ai_extractions`: rows in
`generated_pdfs` are append-only per `file_id`/`version` and never
overwritten. `generate_pdf` checks for an existing completed PDF built
from the same (source_template_id, generator_version) before
regenerating — pass `force=True` to always mint a new version.

A missing or undownloadable asset degrades the result to
`completed_with_errors` (the PDF is still produced, just without that
image) rather than failing the whole generation — the same philosophy
Module 8 already applies to its own warnings.
"""

import time
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings
from app.core.exceptions import NotFoundError, PDFGenerationError, ValidationAppError
from app.core.logging import get_logger
from app.core.supabase import get_supabase_admin
from app.schemas.file import SignedUrlResponse
from app.schemas.pdf_metadata import PDFMetadata
from app.schemas.template import TemplateArtifact
from app.services import document_renderer, file_service, storage_service, template_engine_service
from app.services.pdf_generation import asset_inliner, print_css, weasyprint_renderer

logger = get_logger(__name__)

SCHEMA_VERSION = "1.0"
GENERATOR_VERSION = "1.0"

_ACCEPTABLE_TEMPLATE_STATUSES = {"completed", "completed_with_errors"}
_ACCEPTABLE_PDF_STATUSES = {"completed", "completed_with_errors"}


def generate_pdf(*, company_id: str, file_id: str, force: bool = False) -> PDFMetadata:
    template = template_engine_service.get_latest_template(company_id=company_id, file_id=file_id)
    if template.status not in _ACCEPTABLE_TEMPLATE_STATUSES or not template.storage_path:
        raise ValidationAppError(
            "This file's template has not finished generating yet.", code="TEMPLATE_NOT_READY"
        )

    client = get_supabase_admin()

    if not force:
        cached = _find_cached_pdf(
            client,
            file_id=file_id,
            source_template_id=template.id,
            generator_version=GENERATOR_VERSION,
        )
        if cached is not None:
            return cached

    artifact = TemplateArtifact.model_validate_json(
        storage_service.download_object(path=template.storage_path)
    )

    version = _next_version(client, file_id=file_id)

    insert_response = (
        client.table("generated_pdfs")
        .insert(
            {
                "company_id": company_id,
                "file_id": file_id,
                "source_template_id": template.id,
                "version": version,
                "schema_version": SCHEMA_VERSION,
                "generator_version": GENERATOR_VERSION,
                "status": "processing",
            }
        )
        .execute()
    )
    pdf_id: str = insert_response.data[0]["id"]

    start = time.perf_counter()
    try:
        pdf_bytes, page_count, warnings = _render_pdf(artifact)
    except Exception as exc:  # noqa: BLE001 - malformed artifact or an internal bug must not crash the request
        duration_ms = (time.perf_counter() - start) * 1000
        logger.error(
            "PDF generation failed",
            extra={"file_id": file_id, "version": version, "error": str(exc)},
        )
        return _finalize(
            client,
            pdf_id,
            {"status": "failed", "error_message": str(exc), "duration_ms": duration_ms},
        )
    duration_ms = (time.perf_counter() - start) * 1000

    storage_path = _build_storage_path(company_id=company_id, file_id=file_id, version=version)
    storage_service.upload_object(
        path=storage_path, content=pdf_bytes, content_type="application/pdf"
    )

    status_value = "completed_with_errors" if warnings else "completed"
    if warnings:
        logger.warning(
            "PDF generated with warnings",
            extra={"file_id": file_id, "version": version, "warnings": warnings},
        )

    return _finalize(
        client,
        pdf_id,
        {
            "status": status_value,
            "storage_path": storage_path,
            "page_count": page_count,
            "size_bytes": len(pdf_bytes),
            "duration_ms": duration_ms,
        },
    )


def get_latest_pdf(*, company_id: str, file_id: str) -> PDFMetadata:
    file_service.get_file(company_id=company_id, file_id=file_id)
    client = get_supabase_admin()
    response = (
        client.table("generated_pdfs")
        .select("*")
        .eq("file_id", file_id)
        .order("version", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    row: dict[str, Any] | None = response.data if response else None
    if not row:
        raise NotFoundError("This file has no generated PDF yet.")
    return PDFMetadata(**row)


def get_pdf_by_version(*, company_id: str, file_id: str, version: int) -> PDFMetadata:
    file_service.get_file(company_id=company_id, file_id=file_id)
    client = get_supabase_admin()
    response = (
        client.table("generated_pdfs")
        .select("*")
        .eq("file_id", file_id)
        .eq("version", version)
        .maybe_single()
        .execute()
    )
    row: dict[str, Any] | None = response.data if response else None
    if not row:
        raise NotFoundError(f"PDF version {version} was not found for this file.")
    return PDFMetadata(**row)


def list_pdfs(*, company_id: str, file_id: str) -> list[PDFMetadata]:
    file_service.get_file(company_id=company_id, file_id=file_id)
    client = get_supabase_admin()
    response = (
        client.table("generated_pdfs")
        .select("*")
        .eq("file_id", file_id)
        .order("version", desc=True)
        .execute()
    )
    rows: list[dict[str, Any]] = response.data or []
    return [PDFMetadata(**row) for row in rows]


def get_download_url(
    *, company_id: str, file_id: str, version: int | None = None
) -> SignedUrlResponse:
    metadata = (
        get_pdf_by_version(company_id=company_id, file_id=file_id, version=version)
        if version is not None
        else get_latest_pdf(company_id=company_id, file_id=file_id)
    )
    if metadata.status not in _ACCEPTABLE_PDF_STATUSES or not metadata.storage_path:
        raise ValidationAppError(
            "This file's PDF has not finished generating yet.", code="PDF_NOT_READY"
        )
    expires_in = settings.SIGNED_URL_EXPIRES_IN_SECONDS
    url = storage_service.create_signed_url(path=metadata.storage_path, expires_in=expires_in)
    return SignedUrlResponse(url=url, expires_in=expires_in)


def _render_pdf(artifact: TemplateArtifact) -> tuple[bytes, int, list[str]]:
    value_map = document_renderer.build_default_value_map(artifact.manifest)
    asset_map = asset_inliner.build_asset_map(artifact.manifest)
    rendered_html = document_renderer.render_html(artifact.html, value_map, asset_map)

    missing_asset_ids = [
        asset.asset_id for asset in artifact.manifest.assets if asset.asset_id not in asset_map
    ]
    warnings = [f"asset '{asset_id}' could not be inlined" for asset_id in missing_asset_ids]

    stylesheets = [artifact.css, print_css.render_print_css(artifact.manifest.pages)]
    pdf_bytes, page_count = weasyprint_renderer.render_pdf(
        html=rendered_html, stylesheets=stylesheets
    )
    if page_count == 0:
        raise PDFGenerationError("WeasyPrint produced a PDF with no pages.")
    return pdf_bytes, page_count, warnings


def _find_cached_pdf(
    client: Any, *, file_id: str, source_template_id: str, generator_version: str
) -> PDFMetadata | None:
    response = (
        client.table("generated_pdfs")
        .select("*")
        .eq("file_id", file_id)
        .eq("source_template_id", source_template_id)
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
    return PDFMetadata(**row)


def _next_version(client: Any, *, file_id: str) -> int:
    response = (
        client.table("generated_pdfs")
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
    return f"{company_id}/{file_id}/pdfs/{GENERATOR_VERSION}-v{version}-{timestamp}.pdf"


def _finalize(client: Any, pdf_id: str, fields: dict[str, Any]) -> PDFMetadata:
    response = client.table("generated_pdfs").update(fields).eq("id", pdf_id).execute()
    row: dict[str, Any] = response.data[0]
    return PDFMetadata(**row)
