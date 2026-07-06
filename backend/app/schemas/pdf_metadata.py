"""
Metadata schema for a PDF-generation attempt.
Mirrors the `generated_pdfs` table (backend/sql/011_generated_pdfs.sql)
and `shared/src/types/index.ts` on the frontend — keep all three in sync.
"""

from datetime import datetime

from pydantic import BaseModel


class PDFMetadata(BaseModel):
    id: str
    company_id: str
    file_id: str
    source_template_id: str
    version: int
    schema_version: str
    generator_version: str
    status: str
    storage_path: str | None = None
    page_count: int | None = None
    size_bytes: int | None = None
    duration_ms: float | None = None
    error_message: str | None = None
    created_at: datetime
