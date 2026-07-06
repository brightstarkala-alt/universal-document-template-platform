from app.schemas.ai_extraction import (
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
    TextBlock,
    TextRun,
    Unit,
)
from app.services.template_engine.field_index import FieldIndex
from app.services.template_engine.html_builder import render_unit

_BOX = BoundingBox(x=0, y=0, width=100, height=10)


def _field(
    field_id: str,
    machine_key: str,
    unit_index: int,
    block_index: int,
    run_index: int,
    sample_value: str,
) -> ExtractedField:
    return ExtractedField(
        field_id=field_id,
        machine_key=machine_key,
        display_label=machine_key,
        type="text",
        sample_value=sample_value,
        source=SourceLocation(unit_index=unit_index, block_index=block_index, run_index=run_index),
        confidence=0.9,
        confidence_tier="high",
        detection_method="llm",
    )


def test_render_unit_wraps_only_the_matched_substring_within_a_run() -> None:
    """Regression guard for the inline "Label: Value" case: the label text
    sharing a run with the value must survive untouched."""
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        blocks=[TextBlock(bounding_box=_BOX, runs=[TextRun(text="Invoice Number: INV-1001")])],
    )
    field = _field("f1", "invoice_number", 0, 0, 0, "INV-1001")
    index = FieldIndex(by_run={(0, 0, 0): field})

    result = render_unit(
        unit=unit, field_index=index, style_classes={}, median_font_size=None, section_keys={}
    )

    assert "Invoice Number: " in result.html
    assert (
        '<span data-field-id="f1" data-machine-key="invoice_number">INV-1001</span>' in result.html
    )
    assert result.placed_field_ids == {"f1"}


def test_render_unit_escapes_literal_text() -> None:
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        blocks=[TextBlock(bounding_box=_BOX, runs=[TextRun(text="A & B <tag>")])],
    )
    index = FieldIndex()

    result = render_unit(
        unit=unit, field_index=index, style_classes={}, median_font_size=None, section_keys={}
    )

    assert "A &amp; B &lt;tag&gt;" in result.html
    assert "<tag>" not in result.html


def test_render_unit_emits_heading_tag_for_font_size_outlier() -> None:
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        blocks=[
            TextBlock(bounding_box=_BOX, runs=[TextRun(text="Big Title", font_size=24.0)]),
            TextBlock(bounding_box=_BOX, runs=[TextRun(text="body text", font_size=10.0)]),
        ],
    )
    index = FieldIndex()

    result = render_unit(
        unit=unit, field_index=index, style_classes={}, median_font_size=10.0, section_keys={}
    )

    assert "<h2>Big Title</h2>" in result.html
    assert "<p>body text</p>" in result.html


def test_render_unit_joins_pdf_style_word_runs_with_spaces() -> None:
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        blocks=[
            TextBlock(
                bounding_box=_BOX,
                runs=[TextRun(text="Hello"), TextRun(text="World")],
            )
        ],
    )
    index = FieldIndex()

    result = render_unit(
        unit=unit, field_index=index, style_classes={}, median_font_size=None, section_keys={}
    )

    assert "<p>Hello World</p>" in result.html


def test_render_unit_does_not_double_space_docx_style_runs() -> None:
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        blocks=[
            TextBlock(
                bounding_box=_BOX,
                runs=[TextRun(text="Invoice Number: "), TextRun(text="INV-1001")],
            )
        ],
    )
    index = FieldIndex()

    result = render_unit(
        unit=unit, field_index=index, style_classes={}, median_font_size=None, section_keys={}
    )

    assert "Invoice Number: INV-1001" in result.html
    assert "Invoice Number:  INV-1001" not in result.html


def _grid_table(table_id: str, unit_index: int, block_index: int) -> ExtractedTable:
    return ExtractedTable(
        table_id=table_id,
        source_unit_index=unit_index,
        source_block_index=block_index,
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
        row_count=2,
        confidence=0.9,
        confidence_tier="high",
    )


def _grid_block() -> CellGridBlock:
    return CellGridBlock(
        bounding_box=_BOX,
        row_count=3,
        col_count=2,
        cells=[
            Cell(row=0, col=0, text="Item"),
            Cell(row=0, col=1, text="Qty"),
            Cell(row=1, col=0, text="Widget"),
            Cell(row=1, col=1, text="5"),
            Cell(row=2, col=0, text="Gadget"),
            Cell(row=2, col=1, text="9"),
        ],
    )


def test_render_unit_marks_exactly_one_template_row_for_repeating_table() -> None:
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        blocks=[_grid_block()],
    )
    table = _grid_table("t1", 0, 0)
    index = FieldIndex(tables_by_block={(0, 0): table})

    result = render_unit(
        unit=unit,
        field_index=index,
        style_classes={},
        median_font_size=None,
        section_keys={"t1": "line_items"},
    )

    assert result.html.count('data-repeating-row="true"') == 1
    assert 'data-section-id="t1"' in result.html
    assert 'data-section-key="line_items"' in result.html
    assert 'data-column-key="item"' in result.html
    assert "Gadget" not in result.html  # only the first data row is templated
    assert "Widget" in result.html
    assert result.placed_section_ids == {"t1"}


def test_render_unit_renders_static_table_when_not_repeating() -> None:
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        blocks=[_grid_block()],
    )
    table = _grid_table("t1", 0, 0)
    table.is_repeating = False
    index = FieldIndex(tables_by_block={(0, 0): table})

    result = render_unit(
        unit=unit, field_index=index, style_classes={}, median_font_size=None, section_keys={}
    )

    assert "data-repeating-row" not in result.html
    assert "data-section-id" not in result.html
    assert "Widget" in result.html
    assert "Gadget" in result.html
    assert result.placed_section_ids == set()


def test_render_unit_renders_static_table_when_no_table_matched() -> None:
    """With no `ExtractedTable` at all, Module 8 has no signal about which
    row is a header — everything renders as plain `<td>` rows."""
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        blocks=[_grid_block()],
    )
    index = FieldIndex()

    result = render_unit(
        unit=unit, field_index=index, style_classes={}, median_font_size=None, section_keys={}
    )

    assert "<th>" not in result.html
    assert "<td>Item</td>" in result.html
    assert "<td>Widget</td>" in result.html
    assert result.placed_section_ids == set()


def test_render_unit_falls_back_to_static_on_column_count_mismatch() -> None:
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        blocks=[_grid_block()],
    )
    table = _grid_table("t1", 0, 0)
    table.columns = table.columns[:1]  # now mismatched with the 2-column grid
    index = FieldIndex(tables_by_block={(0, 0): table})

    result = render_unit(
        unit=unit, field_index=index, style_classes={}, median_font_size=None, section_keys={}
    )

    assert "data-repeating-row" not in result.html
    assert any("column count mismatch" in warning for warning in result.warnings)


def test_render_unit_marks_every_image_with_its_asset_id() -> None:
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        blocks=[
            ImageBlock(
                bounding_box=_BOX,
                asset_id="asset-1",
                asset_type="extracted_image",
                asset_path="company-1/file-1/parsed/assets/asset-1.png",
                mime_type="image/png",
                width=50,
                height=30,
            )
        ],
    )
    index = FieldIndex()

    result = render_unit(
        unit=unit, field_index=index, style_classes={}, median_font_size=None, section_keys={}
    )

    assert '<img data-asset-id="asset-1" alt="" width="50" height="30">' in result.html
    assert result.placed_asset_ids == {"asset-1"}
