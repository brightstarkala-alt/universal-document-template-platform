import pytest

from app.services.parsers.pdf_parser import PdfParser
from app.tests.parser_fixtures import make_corrupt_pdf_bytes, make_pdf_bytes


def test_parses_pdf_page_with_text_and_table() -> None:
    result = PdfParser().parse(make_pdf_bytes("Invoice #1042"))

    assert len(result.units) == 1
    unit = result.units[0]
    assert unit.unit_type == "page"
    assert unit.status == "ok"
    assert unit.confidence == 1.0
    assert unit.dimensions.width is not None
    assert unit.dimensions.height is not None

    block_types = [block.type for block in unit.blocks]
    assert "text" in block_types
    assert "cell_grid" in block_types

    cell_grid = next(block for block in unit.blocks if block.type == "cell_grid")
    assert cell_grid.row_count == 2
    assert cell_grid.col_count == 2

    assert result.stats.unit_count == 1
    assert result.stats.text_block_count >= 1
    assert result.stats.cell_grid_count == 1
    assert result.stats.cell_count == 4
    assert result.stats.character_count > 0
    assert result.assets == []


def test_corrupt_pdf_raises_for_orchestrator_to_catch() -> None:
    with pytest.raises(Exception):  # noqa: B017 - pdfminer raises its own exception type
        PdfParser().parse(make_corrupt_pdf_bytes())
