"""
File endpoints: upload a new file, list metadata, fetch a single file's
metadata, and request a signed download URL. All are company-scoped via
`get_current_company`.

`POST /files` is the Upload Engine endpoint (Module 5). It rejects an
oversized request early based on the declared `Content-Length`, then
delegates entirely to `file_service.register_file`, which independently
validates the actual bytes read, computes the file's SHA-256, and only
records metadata after the object has been written to storage.
"""

from fastapi import APIRouter, Depends, File, Request, UploadFile, status

from app.api.deps import get_current_company, get_current_user
from app.core.config import settings
from app.core.exceptions import ValidationAppError
from app.schemas.auth import CurrentUser
from app.schemas.company import CurrentCompany
from app.schemas.file import FileMetadata, SignedUrlResponse
from app.services import audit_service, file_service

router = APIRouter(prefix="/files", tags=["files"])


def _check_declared_content_length(content_length_header: str | None) -> None:
    """Fast-fail on an oversized request before its body is read into memory.

    Independent of the actual-size check `file_validation_service` performs
    on the bytes once read — a client could omit or understate this header,
    so both checks matter.
    """
    if content_length_header is None:
        return

    try:
        declared_size = int(content_length_header)
    except ValueError:
        return

    if declared_size > settings.MAX_UPLOAD_FILE_SIZE_BYTES:
        raise ValidationAppError(
            f"File exceeds the maximum allowed size of "
            f"{settings.MAX_UPLOAD_FILE_SIZE_BYTES} bytes.",
            code="FILE_TOO_LARGE",
        )


@router.post("", response_model=FileMetadata, status_code=status.HTTP_201_CREATED)
async def upload_file(
    request: Request,
    upload: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    current_company: CurrentCompany = Depends(get_current_company),
) -> FileMetadata:
    _check_declared_content_length(request.headers.get("content-length"))

    content = await upload.read()

    file_metadata = file_service.register_file(
        company_id=current_company.id,
        uploaded_by=current_user.id,
        original_filename=upload.filename or "unnamed",
        content_type=upload.content_type or "application/octet-stream",
        content=content,
    )

    audit_service.record_event(
        company_id=current_company.id,
        user_id=current_user.id,
        action="file.uploaded",
        entity_type="file",
        entity_id=file_metadata.id,
    )

    return file_metadata


@router.get("", response_model=list[FileMetadata])
async def list_files(
    current_company: CurrentCompany = Depends(get_current_company),
) -> list[FileMetadata]:
    return file_service.list_files(company_id=current_company.id)


@router.get("/{file_id}", response_model=FileMetadata)
async def read_file(
    file_id: str,
    current_company: CurrentCompany = Depends(get_current_company),
) -> FileMetadata:
    return file_service.get_file(company_id=current_company.id, file_id=file_id)


@router.get("/{file_id}/signed-url", response_model=SignedUrlResponse)
async def read_file_signed_url(
    file_id: str,
    current_company: CurrentCompany = Depends(get_current_company),
) -> SignedUrlResponse:
    return file_service.get_download_url(company_id=current_company.id, file_id=file_id)
