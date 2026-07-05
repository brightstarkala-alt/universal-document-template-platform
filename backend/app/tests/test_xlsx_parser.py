from app.services.parsers.xlsx_parser import XlsxParser
from app.tests.parser_fixtures import make_xlsx_bytes


def test_parses_sheet_into_single_cell_grid_unit() -> None:
    result = XlsxParser().parse(make_xlsx_bytes())

    assert len(result.units) == 1
    unit = result.units[0]
    assert unit.unit_type == "sheet"
    assert unit.status == "ok"
    assert unit.confidence == 1.0

    assert len(unit.blocks) == 1
    block = unit.blocks[0]
    assert block.type == "cell_grid"
    assert block.row_count == 2
    assert block.col_count == 2

    texts = {(cell.row, cell.col): cell.text for cell in block.cells}
    assert texts[(0, 0)] == "Name"
    assert texts[(0, 1)] == "Qty"
    assert texts[(1, 0)] == "Widget"
    assert texts[(1, 1)] == "5"

    assert result.stats.unit_count == 1
    assert result.stats.cell_grid_count == 1
    assert result.stats.cell_count == 4
    assert result.stats.image_count == 0
    assert result.assets == []
