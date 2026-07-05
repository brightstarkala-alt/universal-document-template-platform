"""
File metadata schemas.
Mirrors the `files` table (backend/sql/005_files.sql) and
`shared/src/types/index.ts` on the frontend — keep all three in sync.
"""

from datetime import datetime

from pydantic import BaseModel


class FileMetadata(BaseModel):
    id: str
    company_id: str
    storage_bucket: str
    storage_path: str
    original_filename: str
    content_type: str
    size_bytes: int
    checksum_sha256: str | None = None
    uploaded_by: str | None = None
    created_at: datetime


class SignedUrlResponse(BaseModel):
    url: str
    expires_in: int
