"""
AI Field Extraction domain schemas — Module 7.

Consumes only `UniversalDocumentModel` (Module 6, app/schemas/document_model.py).
Nothing here knows about HTML, templates, previews, or PDFs — this module's
output is semantic field and table definitions, never markup. Deciding *what
a grid of cells means* (Module 6's own words) happens here; deciding how it
becomes a template does not.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

FieldType = Literal[
    "text",
    "long_text",
    "number",
    "currency",
    "date",
    "boolean",
    "email",
    "phone",
    "identifier",
    "address",
    "signature_image",
    "percentage",
]

ConfidenceTier = Literal["high", "medium", "low"]

DetectionMethod = Literal["heuristic", "llm", "heuristic_llm"]


class CellLocation(BaseModel):
    row: int
    col: int


class SourceLocation(BaseModel):
    """Traces an extracted field/column back to its origin in the UDM so a
    later module (Template Engine) can find where a placeholder belongs
    without this module ever touching HTML."""

    unit_index: int
    block_index: int
    run_index: int | None = None
    cell: CellLocation | None = None


class ExtractedField(BaseModel):
    field_id: str
    machine_key: str
    """Normalized snake_case identifier, unique within the extraction result."""
    display_label: str
    """Exact label text as it appears in the source document."""
    type: FieldType
    sample_value: str
    """Literal text found in the document — never a value invented by the model."""
    source: SourceLocation
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_tier: ConfidenceTier
    detection_method: DetectionMethod


class ExtractedTableColumn(BaseModel):
    machine_key: str
    display_label: str
    type: FieldType
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractedTable(BaseModel):
    table_id: str
    source_unit_index: int
    source_block_index: int | None = None
    """None for a repeating section detected from stacked text blocks rather
    than a single `CellGridBlock`."""
    header_row_indices: list[int] = Field(default_factory=list)
    columns: list[ExtractedTableColumn]
    is_repeating: bool
    row_count: int
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_tier: ConfidenceTier


class ExtractionStats(BaseModel):
    field_count: int
    table_count: int
    low_confidence_count: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    duration_ms: float


class AIFieldExtractionResult(BaseModel):
    """The full, persisted extraction result — assembled by
    `ai_extraction_service` from OpenAI responses plus the versioning
    envelope. Mirrors `UniversalDocumentModel`'s role in Module 6."""

    schema_version: str
    source_parsed_document_id: str
    source_checksum_sha256: str
    version: int
    model: str
    prompt_version: str
    extracted_at: datetime
    fields: list[ExtractedField]
    tables: list[ExtractedTable]
    stats: ExtractionStats
    warnings: list[str] = Field(default_factory=list)
