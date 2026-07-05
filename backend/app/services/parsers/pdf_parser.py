"""
PDF adapter — Module 6: Parser Engine.

Uses pdfplumber (pdfminer.six under the hood, MIT-licensed) rather than
PyMuPDF specifically to avoid PyMuPDF's AGPL/commercial licensing in a
commercial SaaS product.

Known limitation (deliberate scope cut, not a bug): embedded images inside
a PDF are not extracted in this version — only text and cell grids are.
Extracting embedded PDF image streams reliably across color spaces and
filters needs either a new system dependency (for rasterizing) or fragile
low-level stream decoding; both are deferred rather than shipped
half-working. Standalone image uploads are fully supported via
`image_parser.py`, and the schema (`ImageBlock`) is already ready for a
future version of this adapter to populate.

Page-level `confidence` is a deterministic, rule-based heuristic — not a
model output — reflecting how much of a page's text extracted cleanly:
0.0 for a page with no extractable text at all (likely scanned; OCR is a
later module's job), and otherwise 1.0 minus the fraction of characters
that came back as Unicode replacement characters.
"""

import io
import re
from typing import Any

import pdfplumber

from app.schemas.document_model import (
    AdapterStats,
    Block,
    BoundingBox,
    Cell,
    CellGridBlock,
    Dimensions,
    ParsedContent,
    TextBlock,
    TextRun,
    Unit,
)

_REPLACEMENT_CHAR = "�"
_BOLD_HINT = re.compile(r"bold", re.IGNORECASE)
_ITALIC_HINT = re.compile(r"italic|oblique", re.IGNORECASE)


class PdfParser:
    name = "pdf_parser"
    version = "1.0.0"

    def parse(self, content: bytes) -> ParsedContent:
        units: list[Unit] = []
        text_block_count = 0
        image_count = 0
        cell_grid_count = 0
        cell_count = 0
        character_count = 0

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for index, page in enumerate(pdf.pages):
                try:
                    blocks, unit_char_count = self._parse_page(page)
                    confidence = self._confidence(page)

                    for block in blocks:
                        if isinstance(block, TextBlock):
                            text_block_count += 1
                        elif isinstance(block, CellGridBlock):
                            cell_grid_count += 1
                            cell_count += len(block.cells)

                    character_count += unit_char_count

                    units.append(
                        Unit(
                            index=index,
                            unit_type="page",
                            dimensions=Dimensions(width=page.width, height=page.height),
                            status="ok",
                            confidence=confidence,
                            blocks=blocks,
                        )
                    )
                except Exception as exc:  # noqa: BLE001 - untrusted third-party input
                    units.append(
                        Unit(
                            index=index,
                            unit_type="page",
                            dimensions=Dimensions(width=page.width, height=page.height),
                            status="error",
                            error=str(exc),
                            confidence=0.0,
                            blocks=[],
                        )
                    )

        return ParsedContent(
            units=units,
            stats=AdapterStats(
                unit_count=len(units),
                text_block_count=text_block_count,
                image_count=image_count,
                cell_grid_count=cell_grid_count,
                cell_count=cell_count,
                character_count=character_count,
            ),
        )

    def _parse_page(self, page: Any) -> tuple[list[Block], int]:
        blocks: list[Block] = []
        char_count = 0

        words = page.extract_words(extra_attrs=["fontname", "size"])
        for line_words in self._group_into_lines(words):
            runs = [
                TextRun(
                    text=word["text"],
                    font_family=word.get("fontname"),
                    font_size=word.get("size"),
                    bold=bool(_BOLD_HINT.search(word.get("fontname") or "")),
                    italic=bool(_ITALIC_HINT.search(word.get("fontname") or "")),
                )
                for word in line_words
            ]
            char_count += sum(len(run.text) for run in runs)
            blocks.append(TextBlock(bounding_box=self._line_bounding_box(line_words), runs=runs))

        for table in page.find_tables():
            grid = table.extract()
            cells = [
                Cell(row=row_idx, col=col_idx, text=value or "")
                for row_idx, row in enumerate(grid)
                for col_idx, value in enumerate(row)
            ]
            x0, top, x1, bottom = table.bbox
            blocks.append(
                CellGridBlock(
                    bounding_box=BoundingBox(x=x0, y=top, width=x1 - x0, height=bottom - top),
                    row_count=len(grid),
                    col_count=len(grid[0]) if grid else 0,
                    cells=cells,
                )
            )

        return blocks, char_count

    @staticmethod
    def _group_into_lines(words: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        lines: dict[int, list[dict[str, Any]]] = {}
        for word in words:
            key = round(word["top"])
            lines.setdefault(key, []).append(word)
        return [lines[key] for key in sorted(lines)]

    @staticmethod
    def _line_bounding_box(line_words: list[dict[str, Any]]) -> BoundingBox:
        x0 = min(w["x0"] for w in line_words)
        x1 = max(w["x1"] for w in line_words)
        top = min(w["top"] for w in line_words)
        bottom = max(w["bottom"] for w in line_words)
        return BoundingBox(x=x0, y=top, width=x1 - x0, height=bottom - top)

    @staticmethod
    def _confidence(page: Any) -> float:
        page_text = page.extract_text() or ""
        if not page_text.strip():
            return 0.0
        replacement_count = page_text.count(_REPLACEMENT_CHAR)
        return max(0.0, 1.0 - (replacement_count / len(page_text)))
