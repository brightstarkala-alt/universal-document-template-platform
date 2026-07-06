from app.schemas.ai_extraction import (
    AIFieldExtractionResult,
    ExtractedField,
    ExtractedTable,
    SourceLocation,
)
from app.services.template_engine.field_index import build_field_index


def _field(
    field_id: str, unit_index: int, block_index: int, run_index: int | None
) -> ExtractedField:
    return ExtractedField(
        field_id=field_id,
        machine_key=f"key_{field_id}",
        display_label="Label",
        type="text",
        sample_value="value",
        source=SourceLocation(unit_index=unit_index, block_index=block_index, run_index=run_index),
        confidence=0.9,
        confidence_tier="high",
        detection_method="llm",
    )


def _table(table_id: str, unit_index: int, block_index: int | None) -> ExtractedTable:
    return ExtractedTable(
        table_id=table_id,
        source_unit_index=unit_index,
        source_block_index=block_index,
        header_row_indices=[0],
        columns=[],
        is_repeating=True,
        row_count=1,
        confidence=0.9,
        confidence_tier="high",
    )


def _result(fields: list[ExtractedField], tables: list[ExtractedTable]) -> AIFieldExtractionResult:
    return AIFieldExtractionResult(
        schema_version="1.0",
        source_parsed_document_id="parsed-1",
        source_checksum_sha256="abc",
        version=1,
        model="gpt-4o-mini",
        prompt_version="v1",
        extracted_at="2026-01-01T00:00:00Z",
        fields=fields,
        tables=tables,
        stats={
            "field_count": len(fields),
            "table_count": len(tables),
            "low_confidence_count": 0,
            "duration_ms": 1.0,
        },
    )


def test_build_field_index_keys_fields_by_source_location() -> None:
    field = _field("f1", unit_index=0, block_index=2, run_index=1)
    index = build_field_index(_result([field], []))

    assert index.by_run[(0, 2, 1)] is field
    assert index.unplaceable_field_ids == set()


def test_build_field_index_marks_fields_without_run_index_unplaceable() -> None:
    field = _field("f1", unit_index=0, block_index=2, run_index=None)
    index = build_field_index(_result([field], []))

    assert index.by_run == {}
    assert index.unplaceable_field_ids == {"f1"}


def test_build_field_index_keys_grid_tables_by_block() -> None:
    table = _table("t1", unit_index=0, block_index=3)
    index = build_field_index(_result([], [table]))

    assert index.tables_by_block[(0, 3)] is table
    assert index.unplaceable_table_ids == set()


def test_build_field_index_marks_non_grid_tables_unplaceable() -> None:
    table = _table("t1", unit_index=0, block_index=None)
    index = build_field_index(_result([], [table]))

    assert index.tables_by_block == {}
    assert index.unplaceable_table_ids == {"t1"}
