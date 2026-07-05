"""
Read-only file endpoints: list metadata, fetch a single file's metadata,
and request a signed download URL. All are company-scoped via
`get_current_company`.

There is no upload endpoint here by design — Module 4 is storage
foundation only. Writing files (`file_service.register_file`) is a
primitive the future Upload Engine module will call.
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_company
from app.schemas.company import CurrentCompany
from app.schemas.file import FileMetadata, SignedUrlResponse
from app.services import file_service

router = APIRouter(prefix="/files", tags=["files"])


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
