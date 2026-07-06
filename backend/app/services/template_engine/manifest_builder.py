"""
Manifest assembly — Module 8, Stages E/F.

Builds the formal `TemplateManifest` from what actually made it into the
rendered HTML (via each unit's `UnitRenderResult`), not just from what
Module 7 produced — a field or table that Module 7 detected but that
couldn't be placed (see `field_index.py`'s `unplaceable_*` sets, or one
skipped because its source unit failed to parse) is never silently
dropped: it is excluded from `manifest.fields`/`repeating_sections` but
counted in `unmapped_field_count`/`unmapped_section_count` and explained in
`warnings`.
"""

from typing import Literal

from app.schemas.ai_extraction import AIFieldExtractionResult, ExtractedField, ExtractedTable
from app.schemas.document_model import ImageBlock, Unit, UniversalDocumentModel
from app.schemas.template import (
    TemplateManifest,
    TemplateManifestAsset,
    TemplateManifestColumn,
    TemplateManifestField,
    TemplateManifestMetadata,
    TemplateManifestPage,
    TemplateManifestSection,
)
from app.services.template_engine.field_index import FieldIndex
from app.services.template_engine.html_builder import UnitRenderResult

_PHYSICAL_UNIT_FORMATS = {"pdf", "docx"}


def build_manifest(
    *,
    udm: UniversalDocumentModel,
    extraction_result: AIFieldExtractionResult,
    field_index: FieldIndex,
    unit_results: dict[int, UnitRenderResult],
    section_keys: dict[str, str],
    duration_ms: float,
) -> TemplateManifest:
    placed_field_ids: set[str] = set()
    placed_section_ids: set[str] = set()
    placed_asset_ids: set[str] = set()
    warnings: list[str] = []

    for unit_result in unit_results.values():
        placed_field_ids |= unit_result.placed_field_ids
        placed_section_ids |= unit_result.placed_section_ids
        placed_asset_ids |= unit_result.placed_asset_ids
        warnings.extend(unit_result.warnings)

    warnings.extend(_unplaceable_field_warnings(field_index, extraction_result))
    warnings.extend(_unplaceable_table_warnings(field_index))

    pages = [_build_page(unit, udm.source_format) for unit in udm.units]

    fields = [
        _build_manifest_field(extracted_field)
        for extracted_field in extraction_result.fields
        if extracted_field.field_id in placed_field_ids
    ]

    sections = [
        _build_manifest_section(table, section_keys)
        for table in extraction_result.tables
        if table.table_id in placed_section_ids
    ]

    assets_by_id = _index_assets(udm)
    assets = [
        _build_manifest_asset(assets_by_id[asset_id])
        for asset_id in sorted(placed_asset_ids)
        if asset_id in assets_by_id
    ]

    all_field_ids = {f.field_id for f in extraction_result.fields}
    all_table_ids = {t.table_id for t in extraction_result.tables}

    metadata = TemplateManifestMetadata(
        source_format=udm.source_format,
        page_count=sum(1 for unit in udm.units if unit.unit_type == "page"),
        sheet_count=sum(1 for unit in udm.units if unit.unit_type == "sheet"),
        field_count=len(fields),
        section_count=len(sections),
        asset_count=len(assets),
        unmapped_field_count=len(all_field_ids - placed_field_ids),
        unmapped_section_count=len(all_table_ids - placed_section_ids),
        duration_ms=duration_ms,
        warnings=warnings,
    )

    return TemplateManifest(
        pages=pages, fields=fields, repeating_sections=sections, assets=assets, metadata=metadata
    )


def _unplaceable_field_warnings(
    field_index: FieldIndex, extraction_result: AIFieldExtractionResult
) -> list[str]:
    fields_by_id = {f.field_id: f for f in extraction_result.fields}
    warnings = []
    for field_id in field_index.unplaceable_field_ids:
        machine_key = fields_by_id[field_id].machine_key if field_id in fields_by_id else field_id
        warnings.append(
            f"field '{machine_key}' has no run-level source location (cell-based fields "
            "aren't supported yet) and could not be placed"
        )
    return warnings


def _unplaceable_table_warnings(field_index: FieldIndex) -> list[str]:
    return [
        f"table {table_id} has no grid source block (non-grid repeating sections aren't "
        "supported yet) and was not templated as repeating"
        for table_id in field_index.unplaceable_table_ids
    ]


def _build_page(unit: Unit, source_format: str) -> TemplateManifestPage:
    if unit.unit_type == "sheet":
        return TemplateManifestPage(
            unit_index=unit.index,
            unit_type=unit.unit_type,
            unit_system="grid",
            row_count=unit.dimensions.row_count,
            col_count=unit.dimensions.col_count,
        )
    unit_system: Literal["pt", "px"] = "pt" if source_format in _PHYSICAL_UNIT_FORMATS else "px"
    return TemplateManifestPage(
        unit_index=unit.index,
        unit_type=unit.unit_type,
        unit_system=unit_system,
        width=unit.dimensions.width,
        height=unit.dimensions.height,
    )


def _build_manifest_field(extracted_field: ExtractedField) -> TemplateManifestField:
    return TemplateManifestField(
        field_id=extracted_field.field_id,
        machine_key=extracted_field.machine_key,
        display_label=extracted_field.display_label,
        type=extracted_field.type,
        sample_value=extracted_field.sample_value,
        confidence=extracted_field.confidence,
        confidence_tier=extracted_field.confidence_tier,
        unit_index=extracted_field.source.unit_index,
    )


def _build_manifest_section(
    table: ExtractedTable, section_keys: dict[str, str]
) -> TemplateManifestSection:
    return TemplateManifestSection(
        section_id=table.table_id,
        section_key=section_keys.get(table.table_id, table.table_id),
        unit_index=table.source_unit_index,
        columns=[
            TemplateManifestColumn(
                column_key=column.machine_key, display_label=column.display_label, type=column.type
            )
            for column in table.columns
        ],
        sample_row_count=table.row_count,
        confidence=table.confidence,
        confidence_tier=table.confidence_tier,
    )


def _index_assets(udm: UniversalDocumentModel) -> dict[str, ImageBlock]:
    return {
        block.asset_id: block
        for unit in udm.units
        for block in unit.blocks
        if isinstance(block, ImageBlock)
    }


def _build_manifest_asset(block: ImageBlock) -> TemplateManifestAsset:
    return TemplateManifestAsset(
        asset_id=block.asset_id,
        original_path=block.asset_path,
        mime_type=block.mime_type,
        width=block.width,
        height=block.height,
        role="content_image",
    )
