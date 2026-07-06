"""
Field/table lookup indices — Module 8, Stage B.

Keys mirror `SourceLocation` exactly so a block/run walk (html_builder.py)
can check "is there a field here?" in O(1). Fields/tables Module 7 produced
but that have no placeable source location are recorded separately rather
than silently dropped — `manifest_builder.py` surfaces them as
`unmapped_field_count`/`unmapped_section_count`.
"""

from dataclasses import dataclass, field

from app.schemas.ai_extraction import AIFieldExtractionResult, ExtractedField, ExtractedTable


@dataclass
class FieldIndex:
    by_run: dict[tuple[int, int, int], ExtractedField] = field(default_factory=dict)
    tables_by_block: dict[tuple[int, int], ExtractedTable] = field(default_factory=dict)
    unplaceable_field_ids: set[str] = field(default_factory=set)
    unplaceable_table_ids: set[str] = field(default_factory=set)


def build_field_index(result: AIFieldExtractionResult) -> FieldIndex:
    index = FieldIndex()

    for extracted_field in result.fields:
        if extracted_field.source.run_index is None:
            # Cell-based source locations are never populated by Module 7
            # today (see ai_extraction design notes) — nothing to key on.
            index.unplaceable_field_ids.add(extracted_field.field_id)
            continue
        key = (
            extracted_field.source.unit_index,
            extracted_field.source.block_index,
            extracted_field.source.run_index,
        )
        index.by_run[key] = extracted_field

    for table in result.tables:
        if table.source_block_index is None:
            # Non-grid repeating sections have no per-row source data in
            # Module 7's schema — can't be structurally placed.
            index.unplaceable_table_ids.add(table.table_id)
            continue
        index.tables_by_block[(table.source_unit_index, table.source_block_index)] = table

    return index
