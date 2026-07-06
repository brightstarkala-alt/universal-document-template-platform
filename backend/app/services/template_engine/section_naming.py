"""
Repeating-section naming — Module 8.

`ExtractedTable` (Module 7) has no table-level label, only per-column
labels — Module 8 must invent a name for the section itself
(`section_key`, editable). `section_id` (immutable) is just the table's own
`table_id`, reused verbatim — no new identifier scheme invented there.

`section_key` is derived from the nearest preceding heading-like TextBlock
in the same unit, normalized the same way Module 7 normalizes
`machine_key`s; falls back to a deterministic positional name when no
heading is found. Deduplicated across the whole document the same way
Module 7 dedupes `machine_key`s, so two tables never collide.
"""

from app.schemas.ai_extraction import ExtractedTable
from app.schemas.document_model import TextBlock, Unit, UniversalDocumentModel
from app.services.ai_extraction.keys import dedupe_machine_keys, normalize_machine_key

_MAX_HEADING_LENGTH = 60


def assign_section_keys(
    udm: UniversalDocumentModel, tables: list[ExtractedTable]
) -> dict[str, str]:
    """Returns `{table_id: section_key}` — unique within this document."""
    units_by_index = {unit.index: unit for unit in udm.units}

    raw_names: list[str] = []
    for table in tables:
        raw_names.append(_candidate_name(units_by_index, table))

    deduped = dedupe_machine_keys([normalize_machine_key(name) for name in raw_names])
    return {table.table_id: key for table, key in zip(tables, deduped, strict=True)}


def _candidate_name(units_by_index: dict[int, Unit], table: ExtractedTable) -> str:
    if table.source_block_index is None:
        return f"table_{table.source_unit_index}_x"

    unit = units_by_index.get(table.source_unit_index)
    heading = _find_preceding_heading(unit, table.source_block_index) if unit else None
    if heading:
        return heading
    return f"table_{table.source_unit_index}_{table.source_block_index}"


def _find_preceding_heading(unit: Unit, block_index: int) -> str | None:
    if block_index == 0:
        return None
    previous_block = unit.blocks[block_index - 1]
    if not isinstance(previous_block, TextBlock):
        return None
    text = " ".join(run.text for run in previous_block.runs).strip()
    if text and len(text) <= _MAX_HEADING_LENGTH:
        return text
    return None
