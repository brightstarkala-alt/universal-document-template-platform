"""
Ties file metadata (the `files` table) to objects in Supabase Storage.

This is the layer future modules (Parser, Template Engine) build on:

- `build_storage_path` owns the folder strategy —
  `{company_id}/{file_id}{extension}` — which is also what the
  `storage.objects` RLS policy in backend/sql/006_storage_bucket.sql relies
  on for tenant isolation.
- `register_file` is the write primitive `app/api/v1/files.py`'s
  `POST /files` (Upload Engine) calls: it validates, uploads to storage,
  then inserts metadata — in that order, so a failed metadata insert never
  leaves storage and the `files` table disagreeing about what exists.
- `get_file` / `list_files` / `get_download_url` are read-only and every
  read enforces the company_id ownership check.
"""

import hashlib
import uuid

from app.core.config import settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.core.supabase import get_supabase_admin
from app.schemas.file import FileMetadata, SignedUrlResponse
from app.services import storage_service
from app.services.file_validation_service import validate_file

logger = get_logger(__name__)


def build_storage_path(*, company_id: str, file_id: str, extension: str) -> str:
    return f"{company_id}/{file_id}{extension}"


def register_file(
    *,
    company_id: str,
    uploaded_by: str,
    original_filename: str,
    content_type: str,
    content: bytes,
) -> FileMetadata:
    """Validates, uploads, and records metadata for a new file.

    The object is written to storage before the metadata row is inserted.
    If the insert fails, the just-uploaded object is removed so storage and
    the `files` table never disagree about what exists.
    """
    extension = validate_file(
        filename=original_filename, content_type=content_type, size_bytes=len(content)
    )
    checksum_sha256 = hashlib.sha256(content).hexdigest()

    file_id = str(uuid.uuid4())
    storage_path = build_storage_path(company_id=company_id, file_id=file_id, extension=extension)

    storage_service.upload_object(path=storage_path, content=content, content_type=content_type)

    try:
        client = get_supabase_admin()
        response = (
            client.table("files")
            .insert(
                {
                    "id": file_id,
                    "company_id": company_id,
                    "storage_bucket": storage_service.BUCKET_NAME,
                    "storage_path": storage_path,
                    "original_filename": original_filename,
                    "extension": extension,
                    "content_type": content_type,
                    "size_bytes": len(content),
                    "checksum_sha256": checksum_sha256,
                    "uploaded_by": uploaded_by,
                }
            )
            .execute()
        )
    except Exception:
        logger.error(
            "Failed to record file metadata after upload; removing orphaned object",
            extra={"storage_path": storage_path},
        )
        storage_service.delete_object(path=storage_path)
        raise

    row: dict[str, object] = response.data[0]
    return FileMetadata(**row)  # type: ignore[arg-type]


def get_file(*, company_id: str, file_id: str) -> FileMetadata:
    client = get_supabase_admin()
    response = client.table("files").select("*").eq("id", file_id).maybe_single().execute()

    row: dict[str, object] | None = response.data if response else None
    if not row:
        raise NotFoundError("File not found.")
    if row["company_id"] != company_id:
        raise ForbiddenError("This file does not belong to your company.")

    return FileMetadata(**row)  # type: ignore[arg-type]


def list_files(*, company_id: str) -> list[FileMetadata]:
    client = get_supabase_admin()
    response = (
        client.table("files")
        .select("*")
        .eq("company_id", company_id)
        .order("uploaded_at", desc=True)
        .execute()
    )
    rows: list[dict[str, object]] = response.data or []
    return [FileMetadata(**row) for row in rows]  # type: ignore[arg-type]


def get_download_url(*, company_id: str, file_id: str) -> SignedUrlResponse:
    """Download service foundation: resolves ownership, then delegates the
    actual signed-URL creation to `storage_service`."""
    file = get_file(company_id=company_id, file_id=file_id)
    expires_in = settings.SIGNED_URL_EXPIRES_IN_SECONDS
    url = storage_service.create_signed_url(path=file.storage_path, expires_in=expires_in)
    return SignedUrlResponse(url=url, expires_in=expires_in)
