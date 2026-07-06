"""
Orchestrates a parse: fetches a file's bytes via storage, times and
dispatches to the right adapter (parser_registry), uploads any extracted
embedded assets, and persists the result.

This is the only layer in Module 6 that touches Storage or the database —
every adapter under app/services/parsers/ is a pure `bytes -> ParsedContent`
function with no knowledge of either.

Designed to evolve into a background-job model without changing its public
shape: `parse_file` already returns the same `ParsedDocumentMetadata` a
future queue-backed worker would produce; only *when* the terminal status
is written would change (a worker would flip a `pending` row to a terminal
state later, instead of this function doing it inline).
"""

import mimetypes
import time
from datetime import UTC, datetime
from typing import Any

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.core.supabase import get_supabase_admin
from app.schemas.document_model import (
    ImageBlock,
    ParserInfo,
    ParserStats,
    UniversalDocumentModel,
)
from app.schemas.parsed_document import ParsedDocumentMetadata
from app.services import file_service, storage_service
from app.services.parser_registry import resolve_parser

logger = get_logger(__name__)

SCHEMA_VERSION = "1.0"


def parse_file(*, company_id: str, file_id: str) -> ParsedDocumentMetadata:
    file = file_service.get_file(company_id=company_id, file_id=file_id)
    adapter = resolve_parser(file.extension)
    client = get_supabase_admin()

    insert_response = (
        client.table("parsed_documents")
        .insert(
            {
                "company_id": company_id,
                "file_id": file_id,
                "schema_version": SCHEMA_VERSION,
                "parser_name": adapter.name,
                "parser_version": adapter.version,
                "status": "processing",
            }
        )
        .execute()
    )
    parsed_document_id: str = insert_response.data[0]["id"]

    content = storage_service.download_object(path=file.storage_path)

    start = time.perf_counter()
    try:
        parsed_content = adapter.parse(content)
    except Exception as exc:  # noqa: BLE001 - untrusted third-party input
        duration_ms = (time.perf_counter() - start) * 1000
        logger.error(
            "Parsing failed",
            extra={"file_id": file_id, "parser": adapter.name, "error": str(exc)},
        )
        return _finalize(
            client,
            parsed_document_id,
            {"status": "failed", "error_message": str(exc), "duration_ms": duration_ms},
        )
    duration_ms = (time.perf_counter() - start) * 1000

    asset_path_by_id = {
        asset.asset_id: _upload_extracted_asset(
            company_id=company_id,
            file_id=file_id,
            asset_id=asset.asset_id,
            content=asset.content,
            mime_type=asset.mime_type,
        )
        for asset in parsed_content.assets
    }

    for unit in parsed_content.units:
        for block in unit.blocks:
            if not isinstance(block, ImageBlock):
                continue
            if block.asset_type == "source_file":
                block.asset_path = file.storage_path
            elif block.asset_id in asset_path_by_id:
                block.asset_path = asset_path_by_id[block.asset_id]
            else:
                logger.warning(
                    "Extracted image asset has no storage path after upload",
                    extra={"file_id": file_id, "asset_id": block.asset_id},
                )

    stats = ParserStats(**parsed_content.stats.model_dump(), duration_ms=duration_ms)
    udm = UniversalDocumentModel(
        schema_version=SCHEMA_VERSION,
        source_file_id=file.id,
        source_checksum_sha256=file.checksum_sha256,
        source_format=file.extension.lstrip("."),
        parser=ParserInfo(name=adapter.name, version=adapter.version),
        extracted_at=datetime.now(UTC),
        stats=stats,
        units=parsed_content.units,
    )

    storage_path = _build_parsed_json_path(
        company_id=company_id, file_id=file_id, parser_version=adapter.version
    )
    storage_service.upload_object(
        path=storage_path,
        content=udm.model_dump_json().encode("utf-8"),
        content_type="application/json",
    )

    has_unit_errors = any(unit.status == "error" for unit in udm.units)
    status = "completed_with_errors" if has_unit_errors else "completed"

    return _finalize(
        client,
        parsed_document_id,
        {
            "status": status,
            "storage_path": storage_path,
            "unit_count": stats.unit_count,
            "text_block_count": stats.text_block_count,
            "image_count": stats.image_count,
            "cell_grid_count": stats.cell_grid_count,
            "cell_count": stats.cell_count,
            "character_count": stats.character_count,
            "duration_ms": duration_ms,
        },
    )


def get_latest_parsed_document(*, company_id: str, file_id: str) -> ParsedDocumentMetadata:
    file_service.get_file(company_id=company_id, file_id=file_id)

    client = get_supabase_admin()
    response = (
        client.table("parsed_documents")
        .select("*")
        .eq("file_id", file_id)
        .order("created_at", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    row: dict[str, Any] | None = response.data if response else None
    if not row:
        raise NotFoundError("This file has not been parsed yet.")
    return ParsedDocumentMetadata(**row)


def get_parsed_document(*, company_id: str, parsed_document_id: str) -> ParsedDocumentMetadata:
    """Fetches one specific parse attempt by id — not just "whatever is
    latest right now". Needed by later modules (AI Extraction, Template
    Engine) that must keep using the exact `UniversalDocumentModel` an
    earlier stage was built from, even if the file has since been re-parsed
    and a newer `parsed_documents` row now exists."""
    client = get_supabase_admin()
    response = (
        client.table("parsed_documents")
        .select("*")
        .eq("id", parsed_document_id)
        .maybe_single()
        .execute()
    )
    row: dict[str, Any] | None = response.data if response else None
    if not row:
        raise NotFoundError("Parsed document not found.")
    if row["company_id"] != company_id:
        raise ForbiddenError("This parsed document does not belong to your company.")
    return ParsedDocumentMetadata(**row)


def _upload_extracted_asset(
    *, company_id: str, file_id: str, asset_id: str, content: bytes, mime_type: str
) -> str:
    extension = mimetypes.guess_extension(mime_type) or ""
    path = f"{company_id}/{file_id}/parsed/assets/{asset_id}{extension}"
    storage_service.upload_object(path=path, content=content, content_type=mime_type)
    return path


def _build_parsed_json_path(*, company_id: str, file_id: str, parser_version: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    return f"{company_id}/{file_id}/parsed/{SCHEMA_VERSION}/{parser_version}-{timestamp}.json"


def _finalize(
    client: Any, parsed_document_id: str, fields: dict[str, Any]
) -> ParsedDocumentMetadata:
    response = (
        client.table("parsed_documents").update(fields).eq("id", parsed_document_id).execute()
    )
    row: dict[str, Any] = response.data[0]
    return ParsedDocumentMetadata(**row)
