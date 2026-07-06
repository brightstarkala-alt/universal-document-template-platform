from app.schemas.document_model import BoundingBox, Dimensions, TextBlock, TextRun, Unit
from app.services.template_engine.layout import reading_order


def _text_block(x: float, y: float, text: str = "x") -> TextBlock:
    return TextBlock(
        bounding_box=BoundingBox(x=x, y=y, width=10, height=10), runs=[TextRun(text=text)]
    )


def test_reading_order_sorts_by_position_when_positions_are_real() -> None:
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        blocks=[
            _text_block(x=0, y=50, text="second"),
            _text_block(x=0, y=0, text="first"),
            _text_block(x=0, y=100, text="third"),
        ],
    )

    assert reading_order(unit) == [1, 0, 2]


def test_reading_order_fixes_pdf_table_ordering_quirk() -> None:
    """Regression guard for the exact bug found in pdf_parser.py: it
    appends every text line first, then every table afterward, even when
    the table visually sits above some text. A table block at y=10 must be
    read before a text block at y=200."""
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=300),
        blocks=[
            _text_block(x=0, y=0, text="heading"),
            _text_block(x=0, y=200, text="footer text"),
            _text_block(x=0, y=10, text="table-like block appended late"),
        ],
    )

    assert reading_order(unit) == [0, 2, 1]


def test_reading_order_preserves_array_order_when_positions_are_degenerate() -> None:
    """Regression guard for docx_parser.py: every block gets
    BoundingBox(0,0,0,0) — sorting by a uniformly-zero position must be a
    no-op, and array order (real DOCX document order) must be trusted."""
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        blocks=[
            _text_block(x=0, y=0, text="third-in-array-but-first-in-docs"),
            _text_block(x=0, y=0, text="second"),
            _text_block(x=0, y=0, text="first"),
        ],
    )

    assert reading_order(unit) == [0, 1, 2]


def test_reading_order_handles_empty_unit() -> None:
    unit = Unit(index=0, unit_type="page", dimensions=Dimensions(width=100, height=100), blocks=[])

    assert reading_order(unit) == []
