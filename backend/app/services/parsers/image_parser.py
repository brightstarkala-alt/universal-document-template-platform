"""
Image adapter (PNG/JPG/JPEG/WEBP) — Module 6: Parser Engine.

Uses Pillow, already a dependency via WeasyPrint. Reads dimensions and
format only — no OCR, no text extraction. The whole file becomes a single
Unit containing a single ImageBlock whose `asset_type` is "source_file":
the asset it references *is* the original uploaded file (already in
Storage from Module 5), so nothing new is stored. `parser_service`
backfills `asset_path` with the original file's own storage path.
"""

import io
import uuid

from PIL import Image

from app.schemas.document_model import (
    AdapterStats,
    BoundingBox,
    Dimensions,
    ImageBlock,
    ParsedContent,
    Unit,
)


class ImageParser:
    name = "image_parser"
    version = "1.0.0"

    def parse(self, content: bytes) -> ParsedContent:
        with Image.open(io.BytesIO(content)) as img:
            width, height = img.size
            mime_type = Image.MIME.get(img.format or "", "application/octet-stream")

        block = ImageBlock(
            bounding_box=BoundingBox(x=0, y=0, width=width, height=height),
            asset_id=str(uuid.uuid4()),
            asset_type="source_file",
            asset_path="",
            mime_type=mime_type,
            width=width,
            height=height,
        )

        unit = Unit(
            index=0,
            unit_type="page",
            dimensions=Dimensions(width=width, height=height),
            status="ok",
            confidence=1.0,
            blocks=[block],
        )

        return ParsedContent(
            units=[unit],
            stats=AdapterStats(
                unit_count=1,
                text_block_count=0,
                image_count=1,
                cell_grid_count=0,
                cell_count=0,
                character_count=0,
            ),
        )
