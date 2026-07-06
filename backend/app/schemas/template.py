"""
Template Engine domain schemas — Module 8.

Consumes `UniversalDocumentModel` (Module 6) and `AIFieldExtractionResult`
(Module 7); produces one versioned `TemplateArtifact`: semantic HTML, a
stylesheet, and a formal manifest — never Jinja or any other templating
engine's syntax. HTML markers carry only stable, immutable IDs
(`field_id`, `section_id`, `asset_id` — the same IDs already assigned by
Modules 6/7, never invented fresh) plus editable, human-readable names
(`machine_key`, `section_key`) for legibility. The IDs are the only
authoritative binding a renderer should use; the editable names may go
stale after a rename and that is by design — nothing should depend on them.

Repeating sections are marked structurally (one sample row tagged as the
clonable template row) rather than expressed as a loop — cloning/iteration
is a later rendering module's responsibility, not stored here. Likewise,
asset references store only a stable `asset_id` — resolving it to a
fetchable URL happens downstream, never in this module.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.ai_extraction import ConfidenceTier, FieldType


class TemplateManifestPage(BaseModel):
    """One entry per `Unit` (Module 6). `unit_system` records which
    physical-sizing rule applies, since Module 6 emits genuinely different
    kinds of `Dimensions` per format: real points for PDF/DOCX, pixels for
    a standalone image, and row/col extents (not a physical size at all)
    for an XLSX sheet."""

    unit_index: int
    unit_type: Literal["page", "sheet"]
    unit_system: Literal["pt", "px", "grid"]
    width: float | None = None
    height: float | None = None
    row_count: int | None = None
    col_count: int | None = None


class TemplateManifestField(BaseModel):
    field_id: str
    """Immutable — identical to the `ExtractedField.field_id` this came
    from. The authoritative key for `data-field-id` markers in the HTML."""
    machine_key: str
    """Editable, human-readable. May be renamed without touching the HTML."""
    display_label: str
    type: FieldType
    sample_value: str
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_tier: ConfidenceTier
    unit_index: int


class TemplateManifestColumn(BaseModel):
    column_key: str
    display_label: str
    type: FieldType


class TemplateManifestSection(BaseModel):
    section_id: str
    """Immutable — identical to the `ExtractedTable.table_id` this came
    from. The authoritative key for `data-section-id` markers in the HTML."""
    section_key: str
    """Editable, human-readable (derived from a nearby heading, or a
    positional fallback). May be renamed without touching the HTML."""
    unit_index: int
    columns: list[TemplateManifestColumn]
    sample_row_count: int
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_tier: ConfidenceTier


class TemplateManifestAsset(BaseModel):
    asset_id: str
    """Immutable — identical to `ImageBlock.asset_id` from Module 6. The
    authoritative key for `data-asset-id` markers in the HTML."""
    original_path: str
    mime_type: str
    width: int
    height: int
    role: Literal["content_image", "signature"]
    """`signature` is reserved for when Module 7 gains the ability to
    detect signature fields (it currently cannot — see ai_extraction design
    notes); no asset carries this role yet."""


class TemplateManifestMetadata(BaseModel):
    source_format: str
    page_count: int
    sheet_count: int
    field_count: int
    section_count: int
    asset_count: int
    unmapped_field_count: int
    """Fields Module 7 produced that could not be placed as a marker (e.g.
    a cell-based source location, which Module 7 never populates today).
    Tracked, never silently dropped."""
    unmapped_section_count: int
    """Tables Module 7 detected that render as static content instead of a
    repeating-section marker (non-grid tables, or grids marked
    `is_repeating=False`) — a documented scope boundary, not a bug."""
    duration_ms: float
    warnings: list[str] = Field(default_factory=list)


class TemplateManifest(BaseModel):
    pages: list[TemplateManifestPage]
    fields: list[TemplateManifestField]
    repeating_sections: list[TemplateManifestSection]
    assets: list[TemplateManifestAsset]
    metadata: TemplateManifestMetadata


class TemplateArtifact(BaseModel):
    """The full, persisted template — assembled by `template_engine_service`.
    `html` is body-level markup only (one `<section class="page">` per
    unit); combining it with `css` into a standalone document is a fixed,
    trivial concatenation any consumer performs identically:
    `<html><head><style>{css}</style></head><body>{html}</body></html>` —
    which is what keeps this "one template" even though the two are stored
    as separate strings alongside the manifest in one JSON object."""

    schema_version: str
    generator_version: str
    source_ai_extraction_id: str
    source_parsed_document_id: str
    version: int
    generated_at: datetime
    html: str
    css: str
    manifest: TemplateManifest
