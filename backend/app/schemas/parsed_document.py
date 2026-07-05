"""
Metadata schema for a parse attempt.
Mirrors the `parsed_documents` table (backend/sql/008_parsed_documents.sql)
and `shared/src/types/index.ts` on the frontend — keep all three in sync.
"""

from datetime import datetime

from pydantic import BaseModel


class ParsedDocumentMetadata(BaseModel):
    id: str
    company_id: str
    file_id: str
    schema_version: str
    parser_name: str
    parser_version: str
    status: str
    storage_path: str | None = None
    unit_count: int | None = None
    text_block_count: int | None = None
    image_count: int | None = None
    cell_grid_count: int | None = None
    cell_count: int | None = None
    character_count: int | None = None
    duration_ms: float | None = None
    error_message: str | None = None
    created_at: datetime
