"""
Metadata schema for an AI extraction attempt.
Mirrors the `ai_extractions` table (backend/sql/009_ai_extractions.sql)
and `shared/src/types/index.ts` on the frontend — keep all three in sync.
"""

from datetime import datetime

from pydantic import BaseModel


class AIExtractionMetadata(BaseModel):
    id: str
    company_id: str
    file_id: str
    parsed_document_id: str
    version: int
    schema_version: str
    source_checksum_sha256: str
    model: str
    prompt_version: str
    status: str
    storage_path: str | None = None
    field_count: int | None = None
    table_count: int | None = None
    low_confidence_count: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    duration_ms: float | None = None
    error_message: str | None = None
    created_at: datetime
