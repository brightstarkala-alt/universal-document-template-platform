"""
Metadata schema for a template-generation attempt.
Mirrors the `templates` table (backend/sql/010_templates.sql) and
`shared/src/types/index.ts` on the frontend — keep all three in sync.
"""

from datetime import datetime

from pydantic import BaseModel


class TemplateMetadata(BaseModel):
    id: str
    company_id: str
    file_id: str
    source_ai_extraction_id: str
    source_parsed_document_id: str
    version: int
    schema_version: str
    generator_version: str
    status: str
    storage_path: str | None = None
    field_count: int | None = None
    section_count: int | None = None
    asset_count: int | None = None
    page_count: int | None = None
    duration_ms: float | None = None
    error_message: str | None = None
    created_at: datetime
