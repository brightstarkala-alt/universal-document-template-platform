from app.schemas.ai_extraction import (
    AIFieldExtractionResult,
    ExtractedField,
    ExtractedTable,
    ExtractedTableColumn,
    SourceLocation,
)
from app.schemas.document_model import (
    BoundingBox,
    Cell,
    CellGridBlock,
    Dimensions,
    ImageBlock,
    ParserInfo,
    TextBlock,
    TextRun,
    Unit,
    UniversalDocumentModel,
)
from app.services.template_engine.field_index import build_field_index
from app.services.template_engine.html_builder import render_unit
from app.services.template_engine.manifest_builder import build_manifest
from app.services.template_engine.section_naming import assign_section_keys
from app.services.template_engine.text_styles import collect_style_classes, median_font_size

_BOX = BoundingBox(x=0, y=0, width=100, height=10)


def _build_udm() -> UniversalDocumentModel:
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=612, height=792),
        status="ok",
        confidence=1.0,
        blocks=[
            TextBlock(bounding_box=_BOX, runs=[TextRun(text="Invoice Number: INV-1001")]),
            CellGridBlock(
                bounding_box=_BOX,
                row_count=2,
                col_count=2,
                cells=[
                    Cell(row=0, col=0, text="Item"),
                    Cell(row=0, col=1, text="Qty"),
                    Cell(row=1, col=0, text="Widget"),
                    Cell(row=1, col=1, text="5"),
                ],
            ),
            ImageBlock(
                bounding_box=_BOX,
                asset_id="asset-1",
                asset_type="extracted_image",
                asset_path="company-1/file-1/parsed/assets/asset-1.png",
                mime_type="image/png",
                width=50,
                height=30,
            ),
        ],
    )
    return UniversalDocumentModel(
        schema_version="1.0",
        source_file_id="file-1",
        source_checksum_sha256="checksum-abc",
        source_format="pdf",
        parser=ParserInfo(name="pdf_parser", version="1.0.0"),
        extracted_at="2026-01-01T00:00:00Z",
        stats={
            "unit_count": 1,
            "text_block_count": 1,
            "image_count": 1,
            "cell_grid_count": 1,
            "cell_count": 4,
            "character_count": 30,
            "duration_ms": 1.0,
        },
        units=[unit],
    )


def _build_extraction_result() -> AIFieldExtractionResult:
    placeable_field = ExtractedField(
        field_id="f1",
        machine_key="invoice_number",
        display_label="Invoice Number",
        type="identifier",
        sample_value="INV-1001",
        source=SourceLocation(unit_index=0, block_index=0, run_index=0),
        confidence=0.9,
        confidence_tier="high",
        detection_method="llm",
    )
    unplaceable_field = ExtractedField(
        field_id="f2",
        machine_key="cell_field",
        display_label="Cell Field",
        type="text",
        sample_value="Widget",
        source=SourceLocation(unit_index=0, block_index=1, run_index=None),
        confidence=0.6,
        confidence_tier="medium",
        detection_method="heuristic",
    )
    repeating_table = ExtractedTable(
        table_id="t1",
        source_unit_index=0,
        source_block_index=1,
        header_row_indices=[0],
        columns=[
            ExtractedTableColumn(
                machine_key="item", display_label="Item", type="text", confidence=0.9
            ),
            ExtractedTableColumn(
                machine_key="qty", display_label="Qty", type="number", confidence=0.9
            ),
        ],
        is_repeating=True,
        row_count=1,
        confidence=0.9,
        confidence_tier="high",
    )
    non_grid_table = ExtractedTable(
        table_id="t2",
        source_unit_index=0,
        source_block_index=None,
        header_row_indices=[],
        columns=[
            ExtractedTableColumn(machine_key="x", display_label="X", type="text", confidence=0.5)
        ],
        is_repeating=True,
        row_count=3,
        confidence=0.5,
        confidence_tier="low",
    )
    return AIFieldExtractionResult(
        schema_version="1.0",
        source_parsed_document_id="parsed-1",
        source_checksum_sha256="checksum-abc",
        version=1,
        model="gpt-4o-mini",
        prompt_version="v1",
        extracted_at="2026-01-01T00:00:00Z",
        fields=[placeable_field, unplaceable_field],
        tables=[repeating_table, non_grid_table],
        stats={"field_count": 2, "table_count": 2, "low_confidence_count": 1, "duration_ms": 1.0},
    )


def test_build_manifest_end_to_end() -> None:
    udm = _build_udm()
    extraction_result = _build_extraction_result()

    field_idx = build_field_index(extraction_result)
    section_keys = assign_section_keys(udm, extraction_result.tables)
    style_classes = collect_style_classes(udm)
    doc_median = median_font_size(udm)

    unit_results = {
        udm.units[0].index: render_unit(
            unit=udm.units[0],
            field_index=field_idx,
            style_classes=style_classes,
            median_font_size=doc_median,
            section_keys=section_keys,
        )
    }

    manifest = build_manifest(
        udm=udm,
        extraction_result=extraction_result,
        field_index=field_idx,
        unit_results=unit_results,
        section_keys=section_keys,
        duration_ms=42.0,
    )

    assert len(manifest.pages) == 1
    assert manifest.pages[0].unit_system == "pt"

    assert [f.field_id for f in manifest.fields] == ["f1"]
    assert manifest.fields[0].machine_key == "invoice_number"

    assert [s.section_id for s in manifest.repeating_sections] == ["t1"]
    assert manifest.repeating_sections[0].sample_row_count == 1
    assert [c.column_key for c in manifest.repeating_sections[0].columns] == ["item", "qty"]

    assert [a.asset_id for a in manifest.assets] == ["asset-1"]
    assert manifest.assets[0].original_path == "company-1/file-1/parsed/assets/asset-1.png"
    assert manifest.assets[0].role == "content_image"

    assert manifest.metadata.field_count == 1
    assert manifest.metadata.section_count == 1
    assert manifest.metadata.asset_count == 1
    assert manifest.metadata.unmapped_field_count == 1
    assert manifest.metadata.unmapped_section_count == 1
    assert manifest.metadata.duration_ms == 42.0
    assert any("cell_field" in w or "f2" in w for w in manifest.metadata.warnings)
    assert any("t2" in w for w in manifest.metadata.warnings)
