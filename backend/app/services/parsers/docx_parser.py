"""
DOCX adapter — Module 6: Parser Engine.

Uses python-docx (MIT). DOCX has no native pagination in its XML — page
breaks are a rendering-time concern determined by fonts/margins, not
stored data. Rather than approximate layout (against the Golden Rule),
this adapter treats the whole document as a single Unit: paragraphs and
tables in document order, using the first section's page dimensions if
present. Splitting on explicit section boundaries is a documented future
enhancement, not attempted here.

Embedded images ARE extracted (unlike the PDF adapter): python-docx
exposes each image relationship's raw bytes directly
(`rel.target_part.blob`), so there is no fragile stream-decoding involved.
Extracted bytes travel back via `ParsedContent.assets`; this adapter never
uploads them itself (see app/services/parsers/base.py) — `parser_service`
uploads them and backfills `ImageBlock.asset_path` afterward.
"""

import io
import uuid

import docx
from docx.table import Table as DocxTable
from docx.text.paragraph import Paragraph as DocxParagraph
from PIL import Image

from app.schemas.document_model import (
    AdapterStats,
    BoundingBox,
    Cell,
    CellGridBlock,
    Dimensions,
    ExtractedAsset,
    ImageBlock,
    ParsedContent,
    TextBlock,
    TextRun,
    Unit,
)

_EMU_PER_POINT = 12700


class DocxParser:
    name = "docx_parser"
    version = "1.0.0"

    def parse(self, content: bytes) -> ParsedContent:
        document = docx.Document(io.BytesIO(content))

        blocks: list[TextBlock | CellGridBlock | ImageBlock] = []
        assets: list[ExtractedAsset] = []
        text_block_count = 0
        image_count = 0
        cell_grid_count = 0
        cell_count = 0
        character_count = 0

        for child in document.element.body.iterchildren():
            if child.tag.endswith("}p"):
                paragraph = DocxParagraph(child, document)
                runs = [
                    TextRun(
                        text=run.text,
                        font_family=run.font.name,
                        font_size=(run.font.size.pt if run.font.size else None),
                        bold=bool(run.bold),
                        italic=bool(run.italic),
                    )
                    for run in paragraph.runs
                    if run.text
                ]
                if not runs:
                    continue
                character_count += sum(len(run.text) for run in runs)
                blocks.append(
                    TextBlock(bounding_box=BoundingBox(x=0, y=0, width=0, height=0), runs=runs)
                )
                text_block_count += 1
            elif child.tag.endswith("}tbl"):
                table = DocxTable(child, document)
                grid = [[cell.text for cell in row.cells] for row in table.rows]
                cells = [
                    Cell(row=row_idx, col=col_idx, text=value)
                    for row_idx, row in enumerate(grid)
                    for col_idx, value in enumerate(row)
                ]
                cell_count += len(cells)
                blocks.append(
                    CellGridBlock(
                        bounding_box=BoundingBox(x=0, y=0, width=0, height=0),
                        row_count=len(grid),
                        col_count=len(grid[0]) if grid else 0,
                        cells=cells,
                    )
                )
                cell_grid_count += 1

        for rel in document.part.rels.values():
            if "image" not in rel.reltype:
                continue
            blob = rel.target_part.blob
            try:
                with Image.open(io.BytesIO(blob)) as img:
                    width, height = img.size
            except Exception:  # noqa: BLE001 - untrusted embedded asset
                width, height = 0, 0

            asset_id = str(uuid.uuid4())
            assets.append(
                ExtractedAsset(
                    asset_id=asset_id, content=blob, mime_type=rel.target_part.content_type
                )
            )
            blocks.append(
                ImageBlock(
                    bounding_box=BoundingBox(x=0, y=0, width=width, height=height),
                    asset_id=asset_id,
                    asset_type="extracted_image",
                    asset_path="",
                    mime_type=rel.target_part.content_type,
                    width=width,
                    height=height,
                )
            )
            image_count += 1

        section = document.sections[0] if document.sections else None
        dimensions = Dimensions(
            width=(section.page_width / _EMU_PER_POINT if section and section.page_width else None),
            height=(
                section.page_height / _EMU_PER_POINT if section and section.page_height else None
            ),
        )

        unit = Unit(
            index=0,
            unit_type="page",
            dimensions=dimensions,
            status="ok",
            confidence=1.0,
            blocks=blocks,
        )

        return ParsedContent(
            units=[unit],
            stats=AdapterStats(
                unit_count=1,
                text_block_count=text_block_count,
                image_count=image_count,
                cell_grid_count=cell_grid_count,
                cell_count=cell_count,
                character_count=character_count,
            ),
            assets=assets,
        )
