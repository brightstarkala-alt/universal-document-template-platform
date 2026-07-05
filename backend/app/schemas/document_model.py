"""
Universal Document Model (UDM) — Module 6: Parser Engine.

One schema for every supported format (pdf, docx, xlsx, png, jpg, jpeg,
webp). Parser adapters (app/services/parsers/*.py) only ever produce
`ParsedContent`; nothing in this file — and nothing any adapter imports —
knows about Storage, the database, or HTTP. `app/services/parser_service.py`
is the only layer that assembles a full `UniversalDocumentModel` (adding the
file-identity and timing envelope an adapter can't know about itself) and
persists it.

Block types are deliberately structural, not semantic: `CellGridBlock`
records a raw grid of cells (row/col position, span, text) rather than a
"table" with headers/data rows — deciding what a grid of cells *means* is
AI Extraction's job (a later module), not the parser's.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class Dimensions(BaseModel):
    """Populated fields depend on `Unit.unit_type`: width/height for a
    page, row_count/col_count for a sheet."""

    width: float | None = None
    height: float | None = None
    row_count: int | None = None
    col_count: int | None = None


class TextRun(BaseModel):
    text: str
    font_family: str | None = None
    font_size: float | None = None
    bold: bool = False
    italic: bool = False
    color: str | None = None


class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    bounding_box: BoundingBox
    runs: list[TextRun]


class ImageBlock(BaseModel):
    type: Literal["image"] = "image"
    bounding_box: BoundingBox
    asset_id: str
    asset_type: Literal["source_file", "extracted_image"]
    asset_path: str
    mime_type: str
    width: int
    height: int


class Cell(BaseModel):
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    text: str
    font_family: str | None = None
    font_size: float | None = None
    bold: bool = False


class CellGridBlock(BaseModel):
    """A raw grid of cells — structural, not a semantically interpreted
    "table" (no header/data-row distinction; that's AI's job)."""

    type: Literal["cell_grid"] = "cell_grid"
    bounding_box: BoundingBox
    row_count: int
    col_count: int
    cells: list[Cell]


Block = Annotated[TextBlock | ImageBlock | CellGridBlock, Field(discriminator="type")]


class Unit(BaseModel):
    """One page (pdf, docx, image) or one sheet (xlsx)."""

    index: int
    unit_type: Literal["page", "sheet"]
    dimensions: Dimensions
    status: Literal["ok", "error"] = "ok"
    error: str | None = None
    confidence: float | None = None
    """Deterministic, rule-based extraction-quality heuristic in [0, 1] —
    not a model output. None when a confidence signal isn't meaningful for
    this unit (kept for adapters that have nothing to say about it)."""
    blocks: list[Block] = Field(default_factory=list)


class ParserInfo(BaseModel):
    name: str
    version: str


class AdapterStats(BaseModel):
    """Structural counts an adapter can compute about its own output.
    Does not include `duration_ms` — timing wraps the adapter call and is
    only known to the orchestrator (app/services/parser_service.py)."""

    unit_count: int
    text_block_count: int
    image_count: int
    cell_grid_count: int
    cell_count: int
    character_count: int


class ParserStats(AdapterStats):
    duration_ms: float


class ExtractedAsset(BaseModel):
    """Raw bytes for an embedded image an adapter extracted (e.g. a logo
    inside a DOCX). Never persisted directly — `parser_service` uploads
    `content` to Storage and backfills the matching `ImageBlock.asset_path`
    before the final `UniversalDocumentModel` is built."""

    asset_id: str
    content: bytes
    mime_type: str


class ParsedContent(BaseModel):
    """What a parser adapter returns: `bytes -> ParsedContent`. This is the
    full adapter contract — no storage, database, or HTTP concerns appear
    anywhere in this shape or in the adapters that produce it."""

    units: list[Unit]
    stats: AdapterStats
    assets: list[ExtractedAsset] = Field(default_factory=list)


class UniversalDocumentModel(BaseModel):
    """The full, persisted document model — assembled by `parser_service`
    from a `ParsedContent` plus the file-identity/timing envelope."""

    schema_version: str
    source_file_id: str
    source_checksum_sha256: str
    source_format: str
    parser: ParserInfo
    extracted_at: datetime
    stats: ParserStats
    units: list[Unit]
