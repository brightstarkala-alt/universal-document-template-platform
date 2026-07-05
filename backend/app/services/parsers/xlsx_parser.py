"""
XLSX adapter — Module 6: Parser Engine.

Uses openpyxl (MIT), in `read_only` mode to bound memory use on large
workbooks. One Unit per worksheet — a sheet is already a single grid, so
it becomes exactly one CellGridBlock with no separate "table" concept
layered on top.

Known limitation (deliberate scope cut, not a bug): embedded images inside
a workbook are not extracted in this version — cell values only. openpyxl
only exposes worksheet images via a semi-private `_images` attribute,
which was judged too fragile to rely on for a foundation module.
"""

import io

import openpyxl

from app.schemas.document_model import (
    AdapterStats,
    BoundingBox,
    Cell,
    CellGridBlock,
    Dimensions,
    ParsedContent,
    Unit,
)


class XlsxParser:
    name = "xlsx_parser"
    version = "1.0.0"

    def parse(self, content: bytes) -> ParsedContent:
        workbook = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)

        units: list[Unit] = []
        cell_grid_count = 0
        cell_count = 0
        character_count = 0

        try:
            for index, worksheet in enumerate(workbook.worksheets):
                try:
                    cells: list[Cell] = []
                    max_row = 0
                    max_col = 0
                    for row_idx, row in enumerate(worksheet.iter_rows()):
                        for col_idx, cell in enumerate(row):
                            if cell.value is None:
                                continue
                            text = str(cell.value)
                            cells.append(Cell(row=row_idx, col=col_idx, text=text))
                            character_count += len(text)
                            max_row = max(max_row, row_idx + 1)
                            max_col = max(max_col, col_idx + 1)

                    cell_grid_count += 1
                    cell_count += len(cells)

                    units.append(
                        Unit(
                            index=index,
                            unit_type="sheet",
                            dimensions=Dimensions(row_count=max_row, col_count=max_col),
                            status="ok",
                            confidence=1.0,
                            blocks=[
                                CellGridBlock(
                                    bounding_box=BoundingBox(
                                        x=0, y=0, width=max_col, height=max_row
                                    ),
                                    row_count=max_row,
                                    col_count=max_col,
                                    cells=cells,
                                )
                            ],
                        )
                    )
                except Exception as exc:  # noqa: BLE001 - untrusted third-party input
                    units.append(
                        Unit(
                            index=index,
                            unit_type="sheet",
                            dimensions=Dimensions(),
                            status="error",
                            error=str(exc),
                            confidence=0.0,
                            blocks=[],
                        )
                    )
        finally:
            workbook.close()

        return ParsedContent(
            units=units,
            stats=AdapterStats(
                unit_count=len(units),
                text_block_count=0,
                image_count=0,
                cell_grid_count=cell_grid_count,
                cell_count=cell_count,
                character_count=character_count,
            ),
        )
