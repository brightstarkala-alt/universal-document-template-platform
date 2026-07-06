from app.schemas.ai_extraction import ExtractedTable
from app.schemas.document_model import (
    BoundingBox,
    Cell,
    CellGridBlock,
    Dimensions,
    TextBlock,
    TextRun,
    Unit,
    UniversalDocumentModel,
)
from app.services.template_engine.section_naming import assign_section_keys

_BOX = BoundingBox(x=0, y=0, width=100, height=10)


def _grid_block(row_count: int = 2, col_count: int = 2) -> CellGridBlock:
    return CellGridBlock(
        bounding_box=_BOX,
        row_count=row_count,
        col_count=col_count,
        cells=[
            Cell(row=r, col=c, text=f"{r}-{c}") for r in range(row_count) for c in range(col_count)
        ],
    )


def _udm(units: list[Unit]) -> UniversalDocumentModel:
    return UniversalDocumentModel(
        schema_version="1.0",
        source_file_id="file-1",
        source_checksum_sha256="abc",
        source_format="pdf",
        parser={"name": "pdf_parser", "version": "1.0.0"},
        extracted_at="2026-01-01T00:00:00Z",
        stats={
            "unit_count": len(units),
            "text_block_count": 0,
            "image_count": 0,
            "cell_grid_count": 0,
            "cell_count": 0,
            "character_count": 0,
            "duration_ms": 1.0,
        },
        units=units,
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


def test_uses_preceding_heading_text_as_section_key() -> None:
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        blocks=[
            TextBlock(bounding_box=_BOX, runs=[TextRun(text="Line Items")]),
            _grid_block(),
        ],
    )
    table = _table("t1", unit_index=0, block_index=1)

    keys = assign_section_keys(_udm([unit]), [table])

    assert keys["t1"] == "line_items"


def test_falls_back_to_positional_name_when_no_heading() -> None:
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        blocks=[_grid_block()],
    )
    table = _table("t1", unit_index=0, block_index=0)

    keys = assign_section_keys(_udm([unit]), [table])

    assert keys["t1"] == "table_0_0"


def test_falls_back_when_preceding_block_is_too_long_to_be_a_heading() -> None:
    long_text = "x" * 100
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        blocks=[
            TextBlock(bounding_box=_BOX, runs=[TextRun(text=long_text)]),
            _grid_block(),
        ],
    )
    table = _table("t1", unit_index=0, block_index=1)

    keys = assign_section_keys(_udm([unit]), [table])

    assert keys["t1"] == "table_0_1"


def test_non_grid_table_gets_a_positional_name_without_crashing() -> None:
    unit = Unit(index=0, unit_type="page", dimensions=Dimensions(width=100, height=100), blocks=[])
    table = _table("t1", unit_index=0, block_index=None)

    keys = assign_section_keys(_udm([unit]), [table])

    assert keys["t1"] == "table_0_x"


def test_dedupes_identical_names_across_tables() -> None:
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        blocks=[
            TextBlock(bounding_box=_BOX, runs=[TextRun(text="Items")]),
            _grid_block(),
            TextBlock(bounding_box=_BOX, runs=[TextRun(text="Items")]),
            _grid_block(),
        ],
    )
    table_1 = _table("t1", unit_index=0, block_index=1)
    table_2 = _table("t2", unit_index=0, block_index=3)

    keys = assign_section_keys(_udm([unit]), [table_1, table_2])

    assert keys["t1"] == "items"
    assert keys["t2"] == "items_2"
