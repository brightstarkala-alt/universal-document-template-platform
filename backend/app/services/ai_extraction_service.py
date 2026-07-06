"""
Orchestrates an AI field extraction — Module 7.

Reads the latest completed `UniversalDocumentModel` for a file (Module 6's
output — app/services/parser_service.py), runs it through Stage A
(deterministic candidates, ai_extraction/candidates.py), Stage B (batching),
Stage C (OpenAI structured extraction, ai_extraction/openai_client.py),
Stage D (cross-unit merge), and Stage E (anti-hallucination check plus
confidence scoring, ai_extraction/scoring.py), then persists the result the
same way Module 6 persists a parse: a JSON blob in Storage plus a queryable
metadata row.

This is the only layer in Module 7 that touches Storage or the database —
every helper under app/services/ai_extraction/ is pure and knows nothing
about either. Never touches the original file or re-parses anything: its
only input is the UDM already produced by `parser_service`.

Every run is versioned: `ai_extractions` rows are append-only per
`file_id`/`version` and are never overwritten (backend/sql/009_ai_extractions.sql).
`extract_fields` checks for an existing completed extraction with a matching
(source_checksum_sha256, model, prompt_version, schema_version) before
calling OpenAI at all — an identical re-run of an unchanged file under an
unchanged prompt/model costs nothing. Pass `force=True` to always mint a new
version regardless of that cache.
"""

import json
import time
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings
from app.core.exceptions import AIExtractionError, NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.core.supabase import get_supabase_admin
from app.schemas.ai_extraction import (
    AIFieldExtractionResult,
    DetectionMethod,
    ExtractedField,
    ExtractedTable,
    ExtractedTableColumn,
    ExtractionStats,
    SourceLocation,
)
from app.schemas.ai_extraction_metadata import AIExtractionMetadata
from app.schemas.document_model import CellGridBlock, TextBlock, Unit, UniversalDocumentModel
from app.services import file_service, parser_service, storage_service
from app.services.ai_extraction import candidates as candidate_detection
from app.services.ai_extraction import keys, scoring
from app.services.ai_extraction.candidates import (
    ExtractionCandidates,
    FieldCandidate,
    GridCandidate,
)
from app.services.ai_extraction.openai_client import extract_batch, get_openai_client
from app.services.ai_extraction.prompts import (
    PROMPT_VERSION,
    LLMFieldResult,
    LLMTableResult,
    build_batch_payload,
    build_unit_payload,
)

logger = get_logger(__name__)

SCHEMA_VERSION = "1.0"

_ACCEPTABLE_PARSE_STATUSES = {"completed", "completed_with_errors"}


def extract_fields(*, company_id: str, file_id: str, force: bool = False) -> AIExtractionMetadata:
    parsed = parser_service.get_latest_parsed_document(company_id=company_id, file_id=file_id)
    if parsed.status not in _ACCEPTABLE_PARSE_STATUSES or not parsed.storage_path:
        raise ValidationAppError(
            "This file has not been successfully parsed yet.", code="PARSE_NOT_READY"
        )

    udm_bytes = storage_service.download_object(path=parsed.storage_path)
    udm = UniversalDocumentModel.model_validate_json(udm_bytes)

    client = get_supabase_admin()
    model = settings.OPENAI_MODEL

    if not force:
        cached = _find_cached_extraction(
            client, file_id=file_id, source_checksum_sha256=udm.source_checksum_sha256, model=model
        )
        if cached is not None:
            return cached

    version = _next_version(client, file_id=file_id)

    insert_response = (
        client.table("ai_extractions")
        .insert(
            {
                "company_id": company_id,
                "file_id": file_id,
                "parsed_document_id": parsed.id,
                "version": version,
                "schema_version": SCHEMA_VERSION,
                "source_checksum_sha256": udm.source_checksum_sha256,
                "model": model,
                "prompt_version": PROMPT_VERSION,
                "status": "processing",
            }
        )
        .execute()
    )
    extraction_id: str = insert_response.data[0]["id"]

    start = time.perf_counter()
    try:
        result = _run_extraction(
            udm=udm, model=model, version=version, parsed_document_id=parsed.id
        )
    except Exception as exc:  # noqa: BLE001 - upstream/model failures must not crash the request
        duration_ms = (time.perf_counter() - start) * 1000
        logger.error(
            "AI extraction failed",
            extra={"file_id": file_id, "version": version, "error": str(exc)},
        )
        return _finalize(
            client,
            extraction_id,
            {"status": "failed", "error_message": str(exc), "duration_ms": duration_ms},
        )
    duration_ms = (time.perf_counter() - start) * 1000
    result = result.model_copy(
        update={"stats": result.stats.model_copy(update={"duration_ms": duration_ms})}
    )

    storage_path = _build_storage_path(company_id=company_id, file_id=file_id, version=version)
    storage_service.upload_object(
        path=storage_path,
        content=result.model_dump_json().encode("utf-8"),
        content_type="application/json",
    )

    status = "completed_with_errors" if result.warnings else "completed"

    return _finalize(
        client,
        extraction_id,
        {
            "status": status,
            "storage_path": storage_path,
            "field_count": result.stats.field_count,
            "table_count": result.stats.table_count,
            "low_confidence_count": result.stats.low_confidence_count,
            "prompt_tokens": result.stats.prompt_tokens,
            "completion_tokens": result.stats.completion_tokens,
            "duration_ms": duration_ms,
        },
    )


def get_latest_extraction(*, company_id: str, file_id: str) -> AIExtractionMetadata:
    file_service.get_file(company_id=company_id, file_id=file_id)
    client = get_supabase_admin()
    response = (
        client.table("ai_extractions")
        .select("*")
        .eq("file_id", file_id)
        .order("version", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    row: dict[str, Any] | None = response.data if response else None
    if not row:
        raise NotFoundError("This file has not been extracted yet.")
    return AIExtractionMetadata(**row)


def get_extraction_by_version(
    *, company_id: str, file_id: str, version: int
) -> AIExtractionMetadata:
    file_service.get_file(company_id=company_id, file_id=file_id)
    client = get_supabase_admin()
    response = (
        client.table("ai_extractions")
        .select("*")
        .eq("file_id", file_id)
        .eq("version", version)
        .maybe_single()
        .execute()
    )
    row: dict[str, Any] | None = response.data if response else None
    if not row:
        raise NotFoundError(f"Extraction version {version} was not found for this file.")
    return AIExtractionMetadata(**row)


def list_extractions(*, company_id: str, file_id: str) -> list[AIExtractionMetadata]:
    file_service.get_file(company_id=company_id, file_id=file_id)
    client = get_supabase_admin()
    response = (
        client.table("ai_extractions")
        .select("*")
        .eq("file_id", file_id)
        .order("version", desc=True)
        .execute()
    )
    rows: list[dict[str, Any]] = response.data or []
    return [AIExtractionMetadata(**row) for row in rows]


def _run_extraction(
    *, udm: UniversalDocumentModel, model: str, version: int, parsed_document_id: str
) -> AIFieldExtractionResult:
    client = get_openai_client()
    units_by_index = {unit.index: unit for unit in udm.units}
    candidates_by_unit = candidate_detection.build_candidates(udm)

    all_fields: list[ExtractedField] = []
    all_tables: list[ExtractedTable] = []
    warnings: list[str] = []
    total_prompt_tokens = 0
    total_completion_tokens = 0

    for batch in _batch_units(udm.units, candidates_by_unit):
        unit_payloads = [
            build_unit_payload(unit, candidates_by_unit.get(unit.index, ExtractionCandidates()))
            for unit in batch
        ]
        try:
            batch_result = extract_batch(
                client=client, model=model, user_payload=build_batch_payload(unit_payloads)
            )
        except AIExtractionError as exc:
            unit_indices = ", ".join(str(u.index) for u in batch)
            warnings.append(f"units {unit_indices} skipped: {exc.message}")
            continue

        total_prompt_tokens += batch_result.prompt_tokens
        total_completion_tokens += batch_result.completion_tokens

        fields, field_warnings = _resolve_fields(
            batch_result.response.fields, units_by_index, candidates_by_unit
        )
        tables, table_warnings = _resolve_tables(
            batch_result.response.tables, units_by_index, candidates_by_unit
        )
        all_fields.extend(fields)
        all_tables.extend(tables)
        warnings.extend(field_warnings)
        warnings.extend(table_warnings)

    all_fields, field_merge_warnings = _dedupe_fields_across_units(all_fields)
    all_tables, table_merge_warnings = _merge_tables_across_units(all_tables)
    warnings.extend(field_merge_warnings)
    warnings.extend(table_merge_warnings)

    _assign_unique_machine_keys(all_fields)

    low_confidence_count = sum(1 for f in all_fields if f.confidence_tier == "low") + sum(
        1 for t in all_tables if t.confidence_tier == "low"
    )

    stats = ExtractionStats(
        field_count=len(all_fields),
        table_count=len(all_tables),
        low_confidence_count=low_confidence_count,
        prompt_tokens=total_prompt_tokens or None,
        completion_tokens=total_completion_tokens or None,
        duration_ms=0.0,  # overwritten by the caller once total wall time is known
    )

    return AIFieldExtractionResult(
        schema_version=SCHEMA_VERSION,
        source_parsed_document_id=parsed_document_id,
        source_checksum_sha256=udm.source_checksum_sha256,
        version=version,
        model=model,
        prompt_version=PROMPT_VERSION,
        extracted_at=datetime.now(UTC),
        fields=all_fields,
        tables=all_tables,
        stats=stats,
        warnings=warnings,
    )


def _batch_units(
    units: list[Unit], candidates_by_unit: dict[int, ExtractionCandidates]
) -> list[list[Unit]]:
    """Stage B: greedily packs consecutive units into one OpenAI call until
    their serialized payload would exceed the configured character budget —
    a token-budget proxy, not a fixed page count, so a large document is
    chunked while a small one still costs a single call."""
    budget = settings.AI_EXTRACTION_UNIT_BATCH_CHAR_BUDGET
    batches: list[list[Unit]] = []
    current_batch: list[Unit] = []
    current_size = 0

    for unit in units:
        if unit.status == "error":
            continue
        payload = build_unit_payload(
            unit, candidates_by_unit.get(unit.index, ExtractionCandidates())
        )
        size = len(json.dumps(payload))
        if current_batch and current_size + size > budget:
            batches.append(current_batch)
            current_batch = []
            current_size = 0
        current_batch.append(unit)
        current_size += size

    if current_batch:
        batches.append(current_batch)

    return batches


def _resolve_fields(
    llm_fields: list[LLMFieldResult],
    units_by_index: dict[int, Unit],
    candidates_by_unit: dict[int, ExtractionCandidates],
) -> tuple[list[ExtractedField], list[str]]:
    resolved: list[ExtractedField] = []
    warnings: list[str] = []

    for llm_field in llm_fields:
        if not llm_field.accepted:
            continue

        unit = units_by_index.get(llm_field.unit_index)
        if unit is None:
            warnings.append(
                f"field '{llm_field.display_label}' referenced unknown unit {llm_field.unit_index}"
            )
            continue

        if not _value_present_in_unit(unit, llm_field.sample_value):
            warnings.append(
                f"field '{llm_field.display_label}' rejected: sample_value not found "
                f"verbatim in unit {llm_field.unit_index}"
            )
            continue

        candidate = _find_matching_field_candidate(
            candidates_by_unit.get(llm_field.unit_index), llm_field
        )
        heuristic_confidence = candidate.heuristic_confidence if candidate else 0.5
        agree = candidate.provisional_type == llm_field.type if candidate else True
        detection_method: DetectionMethod = "heuristic_llm" if candidate else "llm"

        confidence = scoring.compute_composite_confidence(
            heuristic_confidence=heuristic_confidence,
            llm_confidence=max(0.0, min(1.0, llm_field.confidence)),
            heuristic_and_llm_agree=agree,
            unit_confidence=unit.confidence,
        )

        run_suffix = llm_field.run_index if llm_field.run_index is not None else "x"
        resolved.append(
            ExtractedField(
                field_id=f"f_{llm_field.unit_index}_{llm_field.block_index}_{run_suffix}",
                machine_key=keys.normalize_machine_key(llm_field.machine_key),
                display_label=llm_field.display_label,
                type=llm_field.type,
                sample_value=llm_field.sample_value,
                source=SourceLocation(
                    unit_index=llm_field.unit_index,
                    block_index=llm_field.block_index,
                    run_index=llm_field.run_index,
                ),
                confidence=confidence,
                confidence_tier=scoring.confidence_tier(confidence),
                detection_method=detection_method,
            )
        )

    return resolved, warnings


def _resolve_tables(
    llm_tables: list[LLMTableResult],
    units_by_index: dict[int, Unit],
    candidates_by_unit: dict[int, ExtractionCandidates],
) -> tuple[list[ExtractedTable], list[str]]:
    resolved: list[ExtractedTable] = []
    warnings: list[str] = []

    for llm_table in llm_tables:
        unit = units_by_index.get(llm_table.unit_index)
        if unit is None:
            warnings.append(f"table referenced unknown unit {llm_table.unit_index}")
            continue

        if llm_table.block_index is not None:
            if llm_table.block_index >= len(unit.blocks):
                warnings.append(
                    f"table referenced out-of-range block {llm_table.block_index} in unit "
                    f"{llm_table.unit_index}; skipped"
                )
                continue
            grid_block = unit.blocks[llm_table.block_index]
            if not isinstance(grid_block, CellGridBlock):
                warnings.append(
                    f"table referenced block {llm_table.block_index} in unit "
                    f"{llm_table.unit_index}, which is not a grid; skipped"
                )
                continue
            row_count = max(grid_block.row_count - len(llm_table.header_row_indices), 0)
        else:
            row_count = llm_table.row_count or 0

        grid_candidate = _find_matching_grid_candidate(
            candidates_by_unit.get(llm_table.unit_index), llm_table
        )
        heuristic_confidence = grid_candidate.heuristic_confidence if grid_candidate else 0.5
        agree = grid_candidate.is_repeating == llm_table.is_repeating if grid_candidate else True
        confidence = scoring.compute_composite_confidence(
            heuristic_confidence=heuristic_confidence,
            llm_confidence=max(0.0, min(1.0, llm_table.confidence)),
            heuristic_and_llm_agree=agree,
            unit_confidence=unit.confidence,
        )

        column_keys = keys.dedupe_machine_keys(
            [keys.normalize_machine_key(c.machine_key) for c in llm_table.columns]
        )
        columns = [
            ExtractedTableColumn(
                machine_key=column_key,
                display_label=column.display_label,
                type=column.type,
                confidence=confidence,
            )
            for column, column_key in zip(llm_table.columns, column_keys, strict=True)
        ]

        block_suffix = llm_table.block_index if llm_table.block_index is not None else "x"
        resolved.append(
            ExtractedTable(
                table_id=f"t_{llm_table.unit_index}_{block_suffix}",
                source_unit_index=llm_table.unit_index,
                source_block_index=llm_table.block_index,
                header_row_indices=llm_table.header_row_indices,
                columns=columns,
                is_repeating=llm_table.is_repeating,
                row_count=row_count,
                confidence=confidence,
                confidence_tier=scoring.confidence_tier(confidence),
            )
        )

    return resolved, warnings


def _value_present_in_unit(unit: Unit, value: str) -> bool:
    needle = value.strip()
    if not needle:
        return False
    for block in unit.blocks:
        if isinstance(block, TextBlock):
            haystack = " ".join(run.text for run in block.runs)
            if needle in haystack:
                return True
        elif isinstance(block, CellGridBlock):
            for cell in block.cells:
                if needle in cell.text:
                    return True
    return False


def _find_matching_field_candidate(
    unit_candidates: ExtractionCandidates | None, llm_field: LLMFieldResult
) -> FieldCandidate | None:
    if unit_candidates is None:
        return None
    for candidate in unit_candidates.fields:
        if (
            candidate.block_index == llm_field.block_index
            and candidate.run_index == llm_field.run_index
        ):
            return candidate
    return None


def _find_matching_grid_candidate(
    unit_candidates: ExtractionCandidates | None, llm_table: LLMTableResult
) -> GridCandidate | None:
    if unit_candidates is None or llm_table.block_index is None:
        return None
    for candidate in unit_candidates.grids:
        if candidate.block_index == llm_table.block_index:
            return candidate
    return None


def _dedupe_fields_across_units(
    fields: list[ExtractedField],
) -> tuple[list[ExtractedField], list[str]]:
    """Stage D: identical text on multiple pages (a letterhead field
    repeated on every page) collapses to one field, keeping the first
    occurrence. Pure code, no LLM call — matching is unambiguous."""
    seen: dict[tuple[str, str], ExtractedField] = {}
    deduped: list[ExtractedField] = []
    warnings: list[str] = []
    for candidate_field in fields:
        dedup_key = (
            candidate_field.display_label.strip().lower(),
            candidate_field.sample_value.strip(),
        )
        existing = seen.get(dedup_key)
        if existing is None:
            seen[dedup_key] = candidate_field
            deduped.append(candidate_field)
        else:
            warnings.append(
                f"field '{candidate_field.display_label}' on unit {candidate_field.source.unit_index} "
                f"duplicates unit {existing.source.unit_index}; merged"
            )
    return deduped, warnings


def _merge_tables_across_units(
    tables: list[ExtractedTable],
) -> tuple[list[ExtractedTable], list[str]]:
    """Stage D: a repeating line-item table that continues across pages
    (matching column signature) merges into one table with a combined row
    count, keeping the first page's table as canonical."""
    merged: list[ExtractedTable] = []
    warnings: list[str] = []
    by_signature: dict[tuple[str, ...], ExtractedTable] = {}

    for table in tables:
        if not table.is_repeating:
            merged.append(table)
            continue
        signature = tuple(c.machine_key for c in table.columns)
        existing = by_signature.get(signature)
        if existing is None:
            by_signature[signature] = table
            merged.append(table)
        else:
            existing.row_count += table.row_count
            warnings.append(
                f"table on unit {table.source_unit_index} merged into table on unit "
                f"{existing.source_unit_index} (matching columns, continued table)"
            )

    return merged, warnings


def _assign_unique_machine_keys(fields: list[ExtractedField]) -> None:
    deduped_keys = keys.dedupe_machine_keys([f.machine_key for f in fields])
    for resolved_field, new_key in zip(fields, deduped_keys, strict=True):
        resolved_field.machine_key = new_key


def _find_cached_extraction(
    client: Any, *, file_id: str, source_checksum_sha256: str, model: str
) -> AIExtractionMetadata | None:
    response = (
        client.table("ai_extractions")
        .select("*")
        .eq("file_id", file_id)
        .eq("source_checksum_sha256", source_checksum_sha256)
        .eq("model", model)
        .eq("prompt_version", PROMPT_VERSION)
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
    return AIExtractionMetadata(**row)


def _next_version(client: Any, *, file_id: str) -> int:
    response = (
        client.table("ai_extractions")
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
    return f"{company_id}/{file_id}/extracted/{SCHEMA_VERSION}/{PROMPT_VERSION}-v{version}-{timestamp}.json"


def _finalize(client: Any, extraction_id: str, fields: dict[str, Any]) -> AIExtractionMetadata:
    response = client.table("ai_extractions").update(fields).eq("id", extraction_id).execute()
    row: dict[str, Any] = response.data[0]
    return AIExtractionMetadata(**row)
